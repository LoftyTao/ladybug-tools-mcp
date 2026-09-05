"""Radiance recipe run services."""

from __future__ import annotations

from contextlib import contextmanager, redirect_stderr, redirect_stdout
from calendar import month_abbr
from functools import lru_cache
import json
import logging
import os
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Any

import lbt_recipes
from honeybee_radiance.writer import _filter_by_pattern
from lbt_recipes.recipe import Recipe
from lbt_recipes.settings import RecipeSettings

from garden.background import submit_worker_process
from garden.honeybee_core.model_io import load_honeybee_model, resolve_model_target
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import PROJECT_ROOT, simulation_folder_name, to_posix_relative
from garden.radiance.sky import RADIANCE_SKY_FILE_TARGET_TYPE, WEA_TARGET_TYPE
from garden.run_ledger import (
    RunLedger,
    make_run_target,
    normalize_run_id,
    project_run,
    serialized_run_start,
)
from garden.run_ledger import run_id_from_target_or_value
from ladybug_tools_mcp.contracts.report import make_report

RADIANCE_RUN_TARGET_TYPE = "radiance_run"
RADIANCE_RUN_DOMAIN = "honeybee_radiance"
RADIANCE_RUNS_DIR = Path("runs") / "radiance"
RADIANCE_RUN_INDEX = RADIANCE_RUNS_DIR / "index.json"

SUPPORTED_RECIPES = {
    "point-in-time-grid",
    "point-in-time-view",
    "daylight-factor",
    "annual-daylight",
    "annual-daylight-enhanced",
    "annual-irradiance",
    "cumulative-radiation",
    "direct-sun-hours",
    "sky-view",
    "leed-daylight-option-two",
    "annual-daylight-en17037",
    "leed-daylight-option-one",
    "well-daylight",
    "breeam-daylight-4b",
    "imageless-annual-glare",
}
GRID_CALCULATION_TYPES = {
    "point-in-time": ("point-in-time-grid", "rtrace"),
    "point_in_time": ("point-in-time-grid", "rtrace"),
    "point-in-time-grid": ("point-in-time-grid", "rtrace"),
    "point_in_time_grid": ("point-in-time-grid", "rtrace"),
    "daylight-factor": ("daylight-factor", "rtrace"),
    "daylight_factor": ("daylight-factor", "rtrace"),
    "sky-view": ("sky-view", "rtrace"),
    "sky_view": ("sky-view", "rtrace"),
}
VIEW_CALCULATION_TYPES = {
    "point-in-time": ("point-in-time-view", "rpict"),
    "point_in_time": ("point-in-time-view", "rpict"),
}
MATRIX_CALCULATION_TYPES = {
    "annual-daylight": ("annual-daylight", "rfluxmtx"),
    "annual_daylight": ("annual-daylight", "rfluxmtx"),
    "annual-irradiance": ("annual-irradiance", "rfluxmtx"),
    "annual_irradiance": ("annual-irradiance", "rfluxmtx"),
    "cumulative-radiation": ("cumulative-radiation", "rfluxmtx"),
    "cumulative_radiation": ("cumulative-radiation", "rfluxmtx"),
    "direct-sun-hours": ("direct-sun-hours", "rfluxmtx"),
    "direct_sun_hours": ("direct-sun-hours", "rfluxmtx"),
}
_ANNUAL_DAYLIGHT_RECIPES = {"annual-daylight", "annual-daylight-enhanced"}
_GENSKY_FLAG_TO_CIE_TYPE = {
    "+s": 0,
    "-s": 1,
    "+i": 2,
    "-i": 3,
    "-c": 4,
    "-u": 5,
}


def _submit_radiance_background(**kwargs: Any) -> subprocess.Popen:
    garden_root = Path(str(kwargs["garden_root"])).expanduser().resolve()
    run_id = str(kwargs["run_id"])
    record = _run_record_by_id(garden_root, run_id)
    run_folder = record.get("run_folder")
    if not isinstance(run_folder, str) or not run_folder:
        raise ValueError(f"Radiance run has no valid run folder: {run_id}")
    run_dir = (garden_root / run_folder).resolve()
    run_dir.relative_to(garden_root)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    temp_dir = garden_root / "tmp" / run_dir.name
    temp_dir.mkdir(parents=True, exist_ok=True)
    env["TEMP"] = str(temp_dir)
    env["TMP"] = str(temp_dir)
    return submit_worker_process(
        garden_root=garden_root,
        run_dir=run_dir,
        worker_module="garden.radiance.worker",
        request=kwargs,
        cwd=PROJECT_ROOT,
        environment=env,
    )


def _garden_root(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _run_index_path(garden_root: Path) -> Path:
    return garden_root / RADIANCE_RUN_INDEX


_RADIANCE_RUN_LEDGER = RunLedger(
    lock="file",
    atomic=True,
    recover_trailing_json=True,
    sort_by_created_at=True,
)


def _read_index(garden_root: Path) -> list[dict[str, Any]]:
    return _RADIANCE_RUN_LEDGER.list(_run_index_path(garden_root))


def _run_target(garden_id: str, run_id: str, recipe_name: str) -> dict[str, str]:
    return make_run_target(
        target_type=RADIANCE_RUN_TARGET_TYPE,
        garden_id=garden_id,
        domain=RADIANCE_RUN_DOMAIN,
        recipe=recipe_name,
        run_id=run_id,
    )


def _normalize_run_id(value: str | None) -> str:
    return normalize_run_id(
        value,
        value
        or f"radiance_{utc_now_iso().replace(':', '').replace('-', '').replace('Z', '').lower()}",
    )


def _validate_target_garden(
    *,
    target: dict[str, Any],
    manifest: GardenManifest,
    field_name: str,
) -> None:
    garden_id = target.get("garden_id")
    if garden_id != manifest.garden_id:
        raise ValueError(f"{field_name} belongs to a different Garden.")


def _model_path_from_target(garden_root: Path, model_target: dict[str, Any]) -> Path:
    path_value = model_target.get("path")
    if not path_value:
        raise ValueError("Radiance simulation requires a model target with a Garden-relative path.")
    model_path = (garden_root / str(path_value)).resolve()
    model_path.relative_to(garden_root)
    if not model_path.is_file():
        raise ValueError("Honeybee model file for Radiance simulation was not found.")
    return model_path


def _garden_file_from_target(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    target: dict[str, Any],
    target_type: str,
    field_name: str,
) -> Path:
    if target.get("target_type") != target_type:
        raise ValueError(f"{field_name} must be a {target_type} target.")
    _validate_target_garden(target=target, manifest=manifest, field_name=field_name)
    path_value = target.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError(f"{field_name} requires a Garden-relative path.")
    path = (garden_root / path_value).resolve()
    path.relative_to(garden_root)
    if not path.is_file():
        raise ValueError(f"{field_name} file was not found inside the Garden.")
    return path


def _resolve_sky_string(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    sky_file_target: dict[str, Any] | None,
    sky: str | None,
) -> str:
    if (sky_file_target is None) == (sky is None):
        raise ValueError("Provide exactly one of sky_file_target or sky.")
    if sky_file_target is not None:
        recipe_sky = sky_file_target.get("recipe_sky")
        if isinstance(recipe_sky, str) and recipe_sky.strip():
            return recipe_sky.strip()
        sky_path = _garden_file_from_target(
            garden_root=garden_root,
            manifest=manifest,
            target=sky_file_target,
            target_type=RADIANCE_SKY_FILE_TARGET_TYPE,
            field_name="sky_file_target",
        )
        artifact_recipe_sky = _recipe_sky_from_manifest_artifact(
            manifest=manifest,
            path=to_posix_relative(sky_path, garden_root),
        )
        if artifact_recipe_sky:
            return artifact_recipe_sky
        return _recipe_sky_from_include(sky_path.read_text(encoding="utf-8").strip())
    return str(sky).strip()


def _recipe_sky_from_manifest_artifact(
    *,
    manifest: GardenManifest,
    path: str,
) -> str | None:
    for artifact in manifest.artifacts:
        if artifact.get("artifact_type") != RADIANCE_SKY_FILE_TARGET_TYPE:
            continue
        if artifact.get("path") != path:
            continue
        source = artifact.get("source") or {}
        recipe_sky = source.get("recipe_sky") if isinstance(source, dict) else None
        if isinstance(recipe_sky, str) and recipe_sky.strip():
            return recipe_sky.strip()
    return None


def _recipe_sky_from_include(text: str) -> str:
    line = next((item.strip() for item in text.splitlines() if item.strip()), "")
    if not line.startswith("!"):
        return text.strip()
    tokens = shlex.split(line[1:])
    if not tokens:
        return text.strip()
    command = tokens[0].lower()
    if command == "gensky":
        return _recipe_sky_from_gensky_tokens(tokens[1:])
    if command == "gendaylit":
        return _recipe_sky_from_gendaylit_tokens(tokens[1:])
    raise ValueError(
        "sky_file_target uses a Radiance include command that cannot be converted "
        "to a honeybee-radiance recipe sky string."
    )


def _extract_flag(tokens: list[str], *flags: str) -> str | None:
    for index, token in enumerate(tokens):
        if token in flags and index + 1 < len(tokens):
            return tokens[index + 1]
    return None


def _append_option(parts: list[str], flag: str, value: Any | None) -> None:
    if value is not None:
        parts.extend([flag, str(value)])


def _recipe_sky_from_gensky_tokens(tokens: list[str]) -> str:
    sky_type = 0
    values = []
    for token in tokens:
        if token in _GENSKY_FLAG_TO_CIE_TYPE:
            sky_type = _GENSKY_FLAG_TO_CIE_TYPE[token]
            continue
        if token.startswith("-"):
            break
        values.append(token)
    if len(values) >= 3:
        month_value = int(values[0])
        parts = ["cie", values[1], month_abbr[month_value], values[2]]
    else:
        altitude = _extract_flag(tokens, "-ang", "-alt")
        azimuth = _extract_flag(tokens, "-az")
        if altitude is None or azimuth is None:
            raise ValueError("Could not convert gensky include to recipe sky string.")
        parts = ["cie"]
        _append_option(parts, "-alt", altitude)
        _append_option(parts, "-az", azimuth)
    _append_option(parts, "-lat", _extract_flag(tokens, "-a"))
    _append_option(parts, "-lon", _extract_flag(tokens, "-o"))
    _append_option(parts, "-type", sky_type)
    _append_option(parts, "-g", _extract_flag(tokens, "-g"))
    return " ".join(parts)


def _recipe_sky_from_gendaylit_tokens(tokens: list[str]) -> str:
    values = []
    for token in tokens:
        if token.startswith("-"):
            break
        values.append(token)
    if len(values) >= 3:
        month_value = int(values[0])
        parts = ["climate-based", values[1], month_abbr[month_value], values[2]]
    else:
        altitude = _extract_flag(tokens, "-ang", "-alt")
        azimuth = _extract_flag(tokens, "-az")
        if altitude is None or azimuth is None:
            raise ValueError("Could not convert gendaylit include to recipe sky string.")
        parts = ["climate-based"]
        _append_option(parts, "-alt", altitude)
        _append_option(parts, "-az", azimuth)
    _append_option(parts, "-lat", _extract_flag(tokens, "-a"))
    _append_option(parts, "-lon", _extract_flag(tokens, "-o"))
    _append_option(parts, "-dni", _extract_flag(tokens, "-W"))
    _append_option(parts, "-dhi", _extract_flag(tokens, "-W"))
    _append_option(parts, "-g", _extract_flag(tokens, "-g"))
    return " ".join(parts)


def _resolve_wea_path(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    wea_target: dict[str, Any] | None,
    wea_path: str | None,
) -> str:
    if (wea_target is None) == (wea_path is None):
        raise ValueError("Provide exactly one of wea_target or wea_path.")
    if wea_target is not None:
        path = _garden_file_from_target(
            garden_root=garden_root,
            manifest=manifest,
            target=wea_target,
            target_type=WEA_TARGET_TYPE,
            field_name="wea_target",
        )
        return str(path)
    path = (garden_root / str(wea_path)).resolve()
    path.relative_to(garden_root)
    if not path.is_file():
        raise ValueError("wea_path file was not found inside the Garden.")
    return str(path)


def _radiance_parameters_from_input(value: str | dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        rad_par = value.get("radiance_parameters")
        if isinstance(rad_par, str):
            return rad_par
    raise ValueError("radiance_parameters must be a string or create_radiance_parameters result.")


def _normalize_grid_filter(value: str) -> str:
    stripped = value.strip()
    if stripped != "*" and stripped.startswith("*") and stripped.endswith("*"):
        inner = stripped.strip("*").strip()
        if inner and "*" not in inner and "?" not in inner:
            return inner
    return stripped


def _write_text_input(run_dir: Path, name: str, text: str | None) -> str | None:
    if text is None:
        return None
    input_dir = run_dir / "inputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    path = input_dir / name
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")
    return str(path)


def _recipe_status_path(run_dir: Path, recipe_name: str) -> Path:
    return run_dir / recipe_name.replace("-", "_") / "__logs__" / "status.json"


def _clear_recipe_status_logs(run_dir: Path, recipe_name: str) -> None:
    log_dir = _recipe_status_path(run_dir, recipe_name).parent
    for name in ("status.json", "logs.log"):
        (log_dir / name).unlink(missing_ok=True)


def _upsert_record(garden_root: Path, record: dict[str, Any]) -> None:
    _RADIANCE_RUN_LEDGER.upsert(_run_index_path(garden_root), record)


def _run_record_by_id(garden_root: Path, run_id: str) -> dict[str, Any]:
    record = _RADIANCE_RUN_LEDGER.get(_run_index_path(garden_root), run_id)
    if record is not None:
        return record
    raise ValueError(f"Radiance run was not found: {run_id}")


def _run_id_from_target_or_value(
    *,
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> str:
    return run_id_from_target_or_value(
        run_target,
        run_id,
        target_type=RADIANCE_RUN_TARGET_TYPE,
        domain=RADIANCE_RUN_DOMAIN,
        target_run_id_required=False,
    )


def _outputs_map(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): item for item in record.get("outputs", [])}


@lru_cache(maxsize=None)
def _recipe_output_specs(recipe_name: str) -> tuple[dict[str, Any], ...]:
    """Read native output paths without running Grasshopper value handlers."""
    if recipe_name not in SUPPORTED_RECIPES:
        raise ValueError(f"Unsupported Radiance recipe: {recipe_name}")
    package_path = (
        Path(lbt_recipes.__file__).parent
        / recipe_name.replace("-", "_")
        / "package.json"
    )
    return tuple(json.loads(package_path.read_text(encoding="utf-8"))["outputs"])


def _missing_outputs(recipe_name: str) -> list[dict[str, Any]]:
    return [
        {"name": spec["name"], "path": None, "exists": False}
        for spec in _recipe_output_specs(recipe_name)
    ]


def _recipe_log_status(
    *,
    run_dir: Path,
    recipe_name: str,
) -> tuple[str | None, str | None]:
    status_path = _recipe_status_path(run_dir, recipe_name)
    if not status_path.is_file():
        return None, None
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - corrupt SDK log file
        return None, f"Could not read recipe status log: {exc}"
    status_payload = payload.get("status")
    raw_status = (
        status_payload.get("status")
        if isinstance(status_payload, dict)
        else status_payload
    )
    message = payload.get("message")
    if not message and isinstance(status_payload, dict):
        message = status_payload.get("message")
    normalized_status = str(raw_status).strip().lower() if raw_status is not None else None
    if not message and normalized_status == "failed":
        log_path = status_path.with_name("logs.log")
        try:
            with log_path.open("r", encoding="utf-8", errors="replace") as log_file:
                for line in log_file:
                    line = line.strip()
                    if "Error:" in line or "Exception:" in line:
                        message = line[:500]
        except OSError:
            pass
    if raw_status is None:
        return None, str(message) if message else None
    return normalized_status, str(message) if message else None


def _recipe_outputs(
    *,
    garden_root_path: Path,
    recipe_name: str,
    run_dir: Path,
) -> list[dict[str, Any]]:
    outputs = []
    recipe_folder = run_dir / recipe_name.replace("-", "_")
    for spec in _recipe_output_specs(recipe_name):
        output_path = recipe_folder / spec["from"]["path"]
        record = {
            "name": spec["name"],
            "path": to_posix_relative(output_path, garden_root_path),
            "required": spec.get("required", True),
            "size_bytes": output_path.stat().st_size if output_path.is_file() else 0,
        }
        if spec["from"]["type"] == "FolderReference":
            record["exists"] = output_path.is_dir() and any(
                path.is_file() for path in output_path.rglob("*")
            )
        else:
            record["exists"] = output_path.is_file() and output_path.stat().st_size > 0
        outputs.append(record)
    return outputs


def _refresh_en17037_results(*, recipe_folder: Path, grid_filter: str) -> None:
    """Re-run native EN 17037 post-processing with the model beside results."""
    # ponytail: repeat post-processing until the upstream task copies the mesh model.
    schedule = json.loads(
        (recipe_folder / "daylight_hours.json").read_text(encoding="utf-8")
    ).get("values")
    if not isinstance(schedule, list):
        raise ValueError("EN 17037 daylight hours schedule must contain a values list.")
    from honeybee_radiance_postprocess.en17037 import en17037_to_folder

    en17037_to_folder(
        recipe_folder / "results",
        schedule,
        grids_filter=grid_filter or "*",
        sub_folder=str(recipe_folder / "en17037"),
    )


def _missing_required_outputs(outputs: list[dict[str, Any]]) -> list[str]:
    return [
        str(output.get("name"))
        for output in outputs
        if output.get("required", True) and not output.get("exists")
    ]


def _public_run(record: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "target",
        "run_id",
        "recipe",
        "calculation_family",
        "calculation_type",
        "command_name",
        "status",
        "created_at",
        "completed_at",
        "model_target",
        "model_display_name",
        "model_path",
        "run_folder",
        "outputs",
        "workers",
        "warnings",
        "radiance_parameters_path",
    )
    return project_run(record, keys)


def _reconcile_running_record(
    *,
    garden_root_path: Path,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Repair stale running records when a background recipe wrote final outputs."""
    if record.get("status") != "running":
        return record
    recipe_name = str(record.get("recipe") or "")
    if recipe_name not in SUPPORTED_RECIPES:
        return record
    run_folder = record.get("run_folder")
    if not isinstance(run_folder, str) or not run_folder:
        return record
    run_dir = (garden_root_path / run_folder).resolve()
    try:
        run_dir.relative_to(garden_root_path)
    except ValueError:
        return record
    warnings = list(record.get("warnings") or [])
    outputs = _recipe_outputs(
        garden_root_path=garden_root_path,
        recipe_name=recipe_name,
        run_dir=run_dir,
    )
    missing_outputs = _missing_required_outputs(outputs)
    logged_status, logged_message = _recipe_log_status(
        run_dir=run_dir,
        recipe_name=recipe_name,
    )
    if logged_status == "failed":
        record.update(
            {
                "status": "failed",
                "completed_at": record.get("completed_at") or utc_now_iso(),
                "outputs": outputs,
                "warnings": [
                    *warnings,
                    f"Recipe status log reported failure: {logged_message or 'no message'}",
                ],
            }
        )
        _upsert_record(garden_root_path, record)
        return record
    # EN 17037 still needs the worker's area-weighted post-processing.
    if recipe_name == "annual-daylight-en17037":
        return record
    completed_in_log = logged_status in {
        "completed", "complete", "done", "success", "succeeded",
    }
    if completed_in_log and missing_outputs:
        record.update(
            {
                "status": "failed",
                "completed_at": record.get("completed_at") or utc_now_iso(),
                "outputs": outputs,
                "warnings": [
                    *warnings,
                    "Radiance recipe finished without required outputs: "
                    + ", ".join(missing_outputs),
                ],
            }
        )
        _upsert_record(garden_root_path, record)
        return record
    if outputs and not missing_outputs and completed_in_log:
        record.update(
            {
                "status": "completed",
                "completed_at": record.get("completed_at") or utc_now_iso(),
                "outputs": outputs,
                "warnings": warnings,
            }
        )
        _upsert_record(garden_root_path, record)
    return record


def _run_response(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    record: dict[str, Any],
    message: str,
    report_status: str = "ok",
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    public = _public_run(record)
    target = record.get("target") or public.get("target")
    run_id = public.get("run_id")
    status = public.get("status")
    recipe = public.get("recipe")
    result = {
        "target": target,
        "radiance_run_target": target,
        "run_target": target,
        "run_id": run_id,
        "status": status,
        "recipe": recipe,
        "outputs": public.get("outputs", []),
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "run_id": run_id,
            "status": status,
            "recipe": recipe,
            "run": public,
        },
        "report": make_report(
            status=report_status,
            message=message,
            warnings=warnings or public.get("warnings", []),
        ),
    }
    if status == "running":
        result["summary_view"]["poll_next"] = {
            "tool": "RAD_poll_simulation",
            "arguments": {
                "garden_root": str(garden_root_path),
                "run_target": target,
            },
        }
    return result


@contextmanager
def _capture_recipe_stdio(run_dir: Path):
    """Keep recipe logs out of stdio-based MCP JSON-RPC."""
    log_path = run_dir / "recipe_stdio.log"
    previous_streams: list[tuple[logging.StreamHandler, Any]] = []
    saved_fds: list[tuple[int, int]] = []
    with log_path.open("a", encoding="utf-8", errors="replace") as log_file:
        for stream in (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__):
            try:
                stream.flush()
            except Exception:
                pass
        for fd in (1, 2):
            try:
                saved_fd = os.dup(fd)
                os.dup2(log_file.fileno(), fd)
            except OSError:
                continue
            saved_fds.append((fd, saved_fd))
        for logger in [
            logging.getLogger(),
            *(
                logger
                for logger in logging.Logger.manager.loggerDict.values()
                if isinstance(logger, logging.Logger)
            ),
        ]:
            for handler in logger.handlers:
                if isinstance(handler, logging.StreamHandler) and handler.stream in {
                    sys.stdout,
                    sys.stderr,
                    sys.__stdout__,
                    sys.__stderr__,
                }:
                    previous_streams.append((handler, handler.stream))
                    handler.setStream(log_file)
        try:
            with redirect_stdout(log_file), redirect_stderr(log_file):
                yield log_path
        finally:
            for stream in (sys.stdout, sys.stderr):
                try:
                    stream.flush()
                except Exception:
                    pass
            log_file.flush()
            for fd, saved_fd in reversed(saved_fds):
                try:
                    os.dup2(saved_fd, fd)
                finally:
                    os.close(saved_fd)
            for handler, stream in previous_streams:
                handler.setStream(stream)


def run_radiance_recipe(
    *,
    garden_root: str,
    recipe_name: str,
    inputs: dict[str, Any],
    run_id: str,
    model_target: dict[str, Any],
    calculation_family: str,
    calculation_type: str,
    command_name: str,
    workers: int | None = None,
    reload_old: bool = False,
    silent: bool = True,
) -> dict[str, Any]:
    """Run one Honeybee Radiance recipe and update the Garden run ledger."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    record = _run_record_by_id(garden_root_path, run_id)
    run_folder = record.get("run_folder")
    if not isinstance(run_folder, str) or not run_folder:
        raise ValueError(f"Radiance run has no valid run folder: {run_id}")
    run_dir = (garden_root_path / run_folder).resolve()
    run_dir.relative_to(garden_root_path)
    run_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = garden_root_path / "tmp" / run_dir.name
    temp_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = str(temp_dir)
    os.environ["TMP"] = str(temp_dir)
    warnings: list[str] = []
    status = "completed"
    try:
        with _capture_recipe_stdio(run_dir):
            recipe = Recipe(recipe_name)
            for name, value in inputs.items():
                if value is not None:
                    recipe.input_value_by_name(name, value)
            settings = RecipeSettings(
                folder=str(run_dir),
                workers=workers,
                reload_old=reload_old,
                report_out=False,
            )
            recipe.run(
                settings=settings,
                radiance_check=True,
                queenbee_path=str(
                    Path(sys.executable).resolve().parent
                    / ("queenbee.exe" if os.name == "nt" else "queenbee")
                ),
                silent=silent,
            )
    except Exception as exc:  # pragma: no cover - exercised by real engines
        status = "failed"
        warnings.append(str(exc))
    logged_status, logged_message = _recipe_log_status(
        run_dir=run_dir,
        recipe_name=recipe_name,
    )
    if logged_status == "failed":
        status = "failed"
        warnings.append(
            f"Recipe status log reported failure: {logged_message or 'no message'}"
        )
    if status == "completed" and recipe_name == "annual-daylight-en17037":
        try:
            with _capture_recipe_stdio(run_dir):
                _refresh_en17037_results(
                    recipe_folder=run_dir / recipe_name.replace("-", "_"),
                    grid_filter=str(inputs.get("grid-filter") or "*"),
                )
        except Exception as exc:  # pragma: no cover - exercised by real engines
            status = "failed"
            warnings.append(f"Could not refresh EN 17037 results: {exc}")

    outputs = _recipe_outputs(
        garden_root_path=garden_root_path,
        recipe_name=recipe_name,
        run_dir=run_dir,
    )
    missing_outputs = _missing_required_outputs(outputs)
    if status == "completed" and missing_outputs:
        status = "failed"
        warnings.append(
            "Radiance recipe finished without required outputs: "
            + ", ".join(missing_outputs)
        )
    record.update(
        {
            "status": status,
            "completed_at": utc_now_iso(),
            "outputs": outputs,
            "warnings": warnings,
        }
    )
    _upsert_record(garden_root_path, record)
    return {
        "target": _run_target(manifest.garden_id, run_id, recipe_name),
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": run_id,
            "status": status,
            "recipe": recipe_name,
            "calculation_family": calculation_family,
            "calculation_type": calculation_type,
            "command_name": command_name,
            "outputs": _outputs_map(record),
        },
        "report": make_report(
            status="ok" if status == "completed" else "error",
            message=(
                "Radiance recipe completed."
                if status == "completed"
                else "Radiance recipe failed; run record was saved."
            ),
            warnings=warnings,
        ),
    }


@serialized_run_start
def _start_radiance_run(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None,
    recipe_name: str,
    calculation_family: str,
    calculation_type: str,
    command_name: str,
    inputs: dict[str, Any],
    radiance_parameters: str | None,
    run_id: str | None,
    workers: int | None,
    reload_old: bool,
    silent: bool,
) -> dict[str, Any]:
    garden_root_path = _garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(
        garden_root_path,
        model_target,
    )
    model_path = _model_path_from_target(garden_root_path, resolved_model_target)
    model = load_honeybee_model(garden_root_path, resolved_model_target)
    model_display_name = getattr(model, "display_name", None)
    if not isinstance(model_display_name, str) or not model_display_name.strip():
        raise ValueError("Radiance simulation requires the Honeybee model display_name.")
    run_id = _normalize_run_id(run_id)
    for record in _read_index(garden_root_path):
        if record.get("run_id") == run_id:
            existing_status = str(record.get("status", "unknown"))
            return _run_response(
                garden_root_path=garden_root_path,
                manifest=manifest,
                record=record,
                message=(
                    f"Radiance run already exists with status {existing_status}; "
                    "returning the existing radiance_run target."
                ),
                report_status="ok" if existing_status in {"running", "completed"} else "warning",
                warnings=[
                    "No new recipe was started because run_id already exists. "
                    "Use a different run_id for a fresh run."
                ],
            )

    run_dir = (
        garden_root_path
        / RADIANCE_RUNS_DIR
        / simulation_folder_name(model_display_name)
    ).resolve()
    run_dir.relative_to(garden_root_path)
    run_folder = to_posix_relative(run_dir, garden_root_path)
    _RADIANCE_RUN_LEDGER.prepare_folder(
        _run_index_path(garden_root_path),
        run_folder,
        recipe=recipe_name,
        model_target=resolved_model_target,
        preserve_other_recipes=True,
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    _clear_recipe_status_logs(run_dir, recipe_name)
    radiance_parameters_path = _write_text_input(
        run_dir,
        "radiance_parameters.txt",
        radiance_parameters,
    )
    target = _run_target(manifest.garden_id, run_id, recipe_name)
    recipe_inputs = dict(inputs)
    recipe_inputs["model"] = str(model_path)
    if radiance_parameters:
        recipe_inputs["radiance-parameters"] = radiance_parameters
    if workers is not None:
        recipe_inputs["cpu-count"] = workers

    record: dict[str, Any] = {
        "run_id": run_id,
        "target": target,
        "recipe": recipe_name,
        "calculation_family": calculation_family,
        "calculation_type": calculation_type,
        "command_name": command_name,
        "status": "running",
        "created_at": utc_now_iso(),
        "model_target": resolved_model_target,
        "model_display_name": model_display_name,
        "model_path": to_posix_relative(model_path, garden_root_path),
        "run_folder": run_folder,
        "outputs": _missing_outputs(recipe_name),
        "workers": workers,
        "warnings": [],
    }
    if radiance_parameters_path:
        record["radiance_parameters_path"] = to_posix_relative(
            Path(radiance_parameters_path),
            garden_root_path,
        )
    _upsert_record(garden_root_path, record)

    try:
        _submit_radiance_background(
            garden_root=str(garden_root_path),
            recipe_name=recipe_name,
            inputs=recipe_inputs,
            run_id=run_id,
            model_target=resolved_model_target,
            calculation_family=calculation_family,
            calculation_type=calculation_type,
            command_name=command_name,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
        )
    except Exception as exc:
        record.update(
            {
                "status": "failed",
                "completed_at": utc_now_iso(),
                "outputs": _missing_outputs(recipe_name),
                "warnings": [f"Radiance recipe could not be started: {exc}"],
            }
        )
        _upsert_record(garden_root_path, record)
        return _run_response(
            garden_root_path=garden_root_path,
            manifest=manifest,
            record=record,
            message="Radiance recipe could not be started; run record was saved.",
            report_status="error",
        )

    poll_arguments = {"garden_root": str(garden_root_path), "run_target": target}
    return {
        "target": target,
        "radiance_run_target": target,
        "run_target": target,
        "run_id": run_id,
        "status": "running",
        "recipe": recipe_name,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "run_id": run_id,
            "status": "running",
            "recipe": recipe_name,
            "calculation_family": calculation_family,
            "calculation_type": calculation_type,
            "command_name": command_name,
            "run_folder": run_folder,
            "outputs": _outputs_map(record),
            "poll_next": {
                "tool": "RAD_poll_simulation",
                "arguments": poll_arguments,
            },
        },
        "report": make_report(
            status="ok",
            message="Radiance recipe started; poll the radiance_run target for status.",
        ),
    }


def start_radiance_grid_run(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    calculation_type: str = "point_in_time",
    sky_file_target: dict[str, Any] | None = None,
    sky: str | None = None,
    grid_filter: str = "*",
    metric: str = "illuminance",
    min_sensor_count: int | None = 1,
    grid_metrics: dict[str, Any] | None = None,
    cloudy_sky: str = "uniform",
    radiance_parameters: str | dict[str, Any] | None = None,
    run_id: str | None = None,
    workers: int | None = None,
    reload_old: bool = False,
    silent: bool = True,
) -> dict[str, Any]:
    """Start a grid-based Radiance recipe in the background."""
    normalized = calculation_type.strip().lower().replace(" ", "_")
    if normalized not in GRID_CALCULATION_TYPES:
        raise ValueError("calculation_type must be point_in_time, daylight_factor, or sky_view.")
    recipe_name, command_name = GRID_CALCULATION_TYPES[normalized]
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    inputs: dict[str, Any] = {"grid-filter": _normalize_grid_filter(grid_filter)}
    if min_sensor_count is not None:
        inputs["min-sensor-count"] = min_sensor_count
    if recipe_name == "point-in-time-grid":
        inputs["sky"] = _resolve_sky_string(
            garden_root=garden_root_path,
            manifest=manifest,
            sky_file_target=sky_file_target,
            sky=sky,
        )
        inputs["metric"] = metric
    elif grid_metrics is not None:
        inputs["grid-metrics"] = grid_metrics
    elif recipe_name == "sky-view":
        if cloudy_sky not in {"uniform", "cloudy"}:
            raise ValueError("cloudy_sky must be uniform or cloudy.")
        inputs["cloudy-sky"] = cloudy_sky
    return _start_radiance_run(
        garden_root=garden_root,
        model_target=model_target,
        recipe_name=recipe_name,
        calculation_family="grid",
        calculation_type=normalized,
        command_name=command_name,
        inputs=inputs,
        radiance_parameters=_radiance_parameters_from_input(radiance_parameters),
        run_id=run_id,
        workers=workers,
        reload_old=reload_old,
        silent=silent,
    )


def start_radiance_view_run(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    calculation_type: str = "point_in_time",
    sky_file_target: dict[str, Any] | None = None,
    sky: str | None = None,
    view_filter: str = "*",
    metric: str = "luminance",
    resolution: int | None = None,
    skip_overture: bool | None = None,
    radiance_parameters: str | dict[str, Any] | None = None,
    run_id: str | None = None,
    workers: int | None = None,
    reload_old: bool = False,
    silent: bool = True,
) -> dict[str, Any]:
    """Start a view-based Radiance recipe in the background."""
    normalized = calculation_type.strip().lower().replace(" ", "_")
    if normalized not in VIEW_CALCULATION_TYPES:
        raise ValueError("calculation_type must be point_in_time.")
    recipe_name, command_name = VIEW_CALCULATION_TYPES[normalized]
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    inputs: dict[str, Any] = {
        "sky": _resolve_sky_string(
            garden_root=garden_root_path,
            manifest=manifest,
            sky_file_target=sky_file_target,
            sky=sky,
        ),
        "view-filter": view_filter,
        "metric": metric,
    }
    if resolution is not None:
        inputs["resolution"] = resolution
    if skip_overture is not None:
        inputs["skip-overture"] = skip_overture
    return _start_radiance_run(
        garden_root=garden_root,
        model_target=model_target,
        recipe_name=recipe_name,
        calculation_family="view",
        calculation_type=normalized,
        command_name=command_name,
        inputs=inputs,
        radiance_parameters=_radiance_parameters_from_input(radiance_parameters),
        run_id=run_id,
        workers=workers,
        reload_old=reload_old,
        silent=silent,
    )


def start_radiance_matrix_run(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    calculation_type: str = "annual_daylight",
    enhanced: bool = True,
    wea_target: dict[str, Any] | None = None,
    wea_path: str | None = None,
    grid_filter: str = "*",
    north: float | None = None,
    timestep: int | None = None,
    schedule: str | None = None,
    thresholds: str | None = None,
    output_type: str | None = None,
    sky_density: int | None = None,
    min_sensor_count: int | None = 1,
    grid_metrics: dict[str, Any] | None = None,
    radiance_parameters: str | dict[str, Any] | None = None,
    run_id: str | None = None,
    workers: int | None = None,
    reload_old: bool = False,
    silent: bool = True,
) -> dict[str, Any]:
    """Start an annual/matrix Radiance recipe in the background."""
    normalized = calculation_type.strip().lower().replace(" ", "_")
    if normalized not in MATRIX_CALCULATION_TYPES:
        raise ValueError(
            "calculation_type must be annual_daylight, annual_irradiance, cumulative_radiation, or direct_sun_hours."
        )
    recipe_name, command_name = MATRIX_CALCULATION_TYPES[normalized]
    if recipe_name == "annual-daylight" and enhanced:
        recipe_name = "annual-daylight-enhanced"
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    inputs: dict[str, Any] = {
        "wea": _resolve_wea_path(
            garden_root=garden_root_path,
            manifest=manifest,
            wea_target=wea_target,
            wea_path=wea_path,
        ),
        "grid-filter": grid_filter,
    }
    if north is not None:
        inputs["north"] = north
    if timestep is not None:
        inputs["timestep"] = timestep
    if min_sensor_count is not None:
        inputs["min-sensor-count"] = min_sensor_count
    if grid_metrics is not None and recipe_name in _ANNUAL_DAYLIGHT_RECIPES:
        inputs["grid-metrics"] = grid_metrics
    if schedule is not None and recipe_name in _ANNUAL_DAYLIGHT_RECIPES:
        inputs["schedule"] = schedule
    if thresholds is not None and recipe_name in _ANNUAL_DAYLIGHT_RECIPES:
        inputs["thresholds"] = thresholds
    if output_type is not None and recipe_name == "annual-irradiance":
        inputs["output-type"] = output_type
    if sky_density is not None and recipe_name == "cumulative-radiation":
        inputs["sky-density"] = sky_density
    return _start_radiance_run(
        garden_root=garden_root,
        model_target=model_target,
        recipe_name=recipe_name,
        calculation_family="matrix",
        calculation_type=normalized,
        command_name=command_name,
        inputs=inputs,
        radiance_parameters=_radiance_parameters_from_input(radiance_parameters),
        run_id=run_id,
        workers=workers,
        reload_old=reload_old,
        silent=silent,
    )


def start_radiance_imageless_annual_glare(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    wea_target: dict[str, Any] | None = None,
    wea_path: str | None = None,
    view_filter: str = "*",
    grid_filter: str = "*",
    north: float | None = None,
    schedule: str | None = None,
    dgp_threshold: float = 0.4,
    luminance_factor: float = 2000.0,
    min_sensor_count: int = 1,
    radiance_parameters: str | dict[str, Any] | None = None,
    run_id: str | None = None,
    workers: int | None = None,
    reload_old: bool = False,
    silent: bool = True,
) -> dict[str, Any]:
    """Start the native imageless annual glare recipe in the background."""
    if not 0 <= dgp_threshold <= 1:
        raise ValueError("dgp_threshold must be between 0 and 1.")
    if luminance_factor <= 0:
        raise ValueError("luminance_factor must be positive.")
    if min_sensor_count < 1 or (workers is not None and workers < 1):
        raise ValueError("min_sensor_count and workers must be positive integers.")
    try:
        _recipe_output_specs("imageless-annual-glare")
    except Exception as exc:
        raise ValueError(
            "The installed lbt_recipes package does not provide the "
            "imageless-annual-glare recipe."
        ) from exc

    garden_root_path = _garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(
        garden_root_path,
        model_target,
    )
    model = load_honeybee_model(garden_root_path, resolved_model_target)
    normalized_view_filter = _normalize_grid_filter(view_filter)
    normalized_grid_filter = _normalize_grid_filter(grid_filter)
    views = _filter_by_pattern(
        model.properties.radiance.views,
        normalized_view_filter,
    )
    if not views:
        raise ValueError(
            "The model must have an attached Radiance View matching view_filter."
        )
    sensor_grids = _filter_by_pattern(
        model.properties.radiance.sensor_grids,
        normalized_grid_filter,
    )
    if not sensor_grids:
        raise ValueError(
            "The model must have attached SensorGrids matching grid_filter."
        )

    inputs: dict[str, Any] = {
        "wea": _resolve_wea_path(
            garden_root=garden_root_path,
            manifest=manifest,
            wea_target=wea_target,
            wea_path=wea_path,
        ),
        "grid-filter": normalized_grid_filter,
        "glare-threshold": dgp_threshold,
        "luminance-factor": luminance_factor,
        "min-sensor-count": min_sensor_count,
    }
    if north is not None:
        inputs["north"] = north
    if schedule is not None:
        inputs["schedule"] = schedule
    result = _start_radiance_run(
        garden_root=garden_root,
        model_target=resolved_model_target,
        recipe_name="imageless-annual-glare",
        calculation_family="glare",
        calculation_type="imageless_annual_glare",
        command_name="rfluxmtx",
        inputs=inputs,
        radiance_parameters=_radiance_parameters_from_input(radiance_parameters),
        run_id=run_id,
        workers=workers,
        reload_old=reload_old,
        silent=silent,
    )
    result["summary_view"].update(
        {
            "view_filter": normalized_view_filter,
            "view_identifiers": [view.full_identifier for view in views],
            "grid_filter": normalized_grid_filter,
            "sensor_grid_identifiers": [
                grid.full_identifier for grid in sensor_grids
            ],
            "dgp_threshold": dgp_threshold,
            "luminance_factor": luminance_factor,
        }
    )
    return result


def list_radiance_runs(
    *,
    garden_root: str,
    status: str | None = None,
) -> dict[str, Any]:
    """List Radiance simulation runs registered in a Garden."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    records = [
        _public_run(
            _reconcile_running_record(garden_root_path=garden_root_path, record=record)
        )
        for record in _read_index(garden_root_path)
    ]
    if status:
        records = [record for record in records if record.get("status") == status]
    return {
        "matches": records,
        "summary_view": {
            "garden_target": manifest.target(),
            "count": len(records),
            "status": status or "all",
        },
        "report": make_report(
            status="ok", message=f"Found {len(records)} Radiance run(s)."
        ),
    }


def get_radiance_run(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Get one Radiance simulation run record."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_run_id = _run_id_from_target_or_value(run_target=run_target, run_id=run_id)
    record = _run_record_by_id(garden_root_path, resolved_run_id)
    record = _reconcile_running_record(garden_root_path=garden_root_path, record=record)
    return _run_response(
        garden_root_path=garden_root_path,
        manifest=manifest,
        record=record,
        message=f"Radiance run returned: {resolved_run_id}",
    )


def list_radiance_run_outputs(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """List output files for one Radiance simulation run."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_run_id = _run_id_from_target_or_value(run_target=run_target, run_id=run_id)
    record = _run_record_by_id(garden_root_path, resolved_run_id)
    record = _reconcile_running_record(garden_root_path=garden_root_path, record=record)
    outputs = list(record.get("outputs", []))
    return {
        "matches": outputs,
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": resolved_run_id,
            "count": len(outputs),
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(outputs)} output(s) for Radiance run {resolved_run_id}.",
        ),
    }
