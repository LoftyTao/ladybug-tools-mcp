"""Radiance recipe run services."""

from __future__ import annotations

from contextlib import contextmanager, redirect_stderr, redirect_stdout
from calendar import month_abbr
import json
import logging
import os
from pathlib import Path
import shlex
import subprocess
import sys
from threading import Thread, get_ident
from typing import Any

from lbt_recipes.recipe import Recipe
from lbt_recipes.settings import RecipeSettings

from garden.honeybee_core.model_io import resolve_model_target
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import PROJECT_ROOT, slugify_name, to_posix_relative
from garden.radiance.sky import RADIANCE_SKY_FILE_TARGET_TYPE, WEA_TARGET_TYPE
from ladybug_tools_mcp.contracts.report import make_report

RADIANCE_RUN_TARGET_TYPE = "radiance_run"
RADIANCE_RUN_DOMAIN = "honeybee_radiance"
RADIANCE_RUNS_DIR = Path("runs") / "radiance"
RADIANCE_RUN_INDEX = RADIANCE_RUNS_DIR / "index.json"

OUTPUT_NAMES_BY_RECIPE = {
    "point-in-time-grid": ("results",),
    "point-in-time-view": ("results",),
    "daylight-factor": ("grid-summary", "results"),
    "annual-daylight": (
        "cda",
        "da",
        "grid-summary",
        "metrics",
        "results",
        "udi",
        "udi-lower",
        "udi-upper",
    ),
    "annual-irradiance": (
        "average-irradiance",
        "cumulative-radiation",
        "peak-irradiance",
        "results",
        "results-direct",
    ),
    "cumulative-radiation": ("average-irradiance", "cumulative-radiation"),
}

GRID_CALCULATION_TYPES = {
    "point-in-time": ("point-in-time-grid", "rtrace"),
    "point_in_time": ("point-in-time-grid", "rtrace"),
    "point-in-time-grid": ("point-in-time-grid", "rtrace"),
    "point_in_time_grid": ("point-in-time-grid", "rtrace"),
    "daylight-factor": ("daylight-factor", "rtrace"),
    "daylight_factor": ("daylight-factor", "rtrace"),
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
}
_GENSKY_FLAG_TO_CIE_TYPE = {
    "+s": 0,
    "-s": 1,
    "+i": 2,
    "-i": 3,
    "-c": 4,
    "-u": 5,
}


class _DaemonBackgroundExecutor:
    """Submit long recipe work without keeping stdio Agent sessions alive."""

    def submit(self, fn, **kwargs):
        thread = Thread(target=fn, kwargs=kwargs, name="lbt-radiance-run", daemon=True)
        thread.start()
        return thread


class _SubprocessBackgroundExecutor:
    """Run background recipes outside the stdio MCP server process."""

    def submit(self, fn, **kwargs):
        if fn is not run_radiance_recipe:
            return _DaemonBackgroundExecutor().submit(fn, **kwargs)
        garden_root = Path(str(kwargs["garden_root"])).expanduser().resolve()
        run_id = str(kwargs["run_id"])
        run_dir = (garden_root / RADIANCE_RUNS_DIR / run_id).resolve()
        run_dir.relative_to(garden_root)
        run_dir.mkdir(parents=True, exist_ok=True)
        request_path = run_dir / "background_request.json"
        request_path.write_text(
            json.dumps(kwargs, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        log_path = run_dir / "background_stdio.log"
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        with log_path.open("ab") as log_file:
            return subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "garden.radiance.worker",
                    str(request_path),
                ],
                cwd=str(PROJECT_ROOT),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                close_fds=True,
            )


_BACKGROUND_EXECUTOR = _SubprocessBackgroundExecutor()


def _garden_root(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _run_index_path(garden_root: Path) -> Path:
    return garden_root / RADIANCE_RUN_INDEX


@contextmanager
def _radiance_index_lock(garden_root: Path):
    path = _run_index_path(garden_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    with lock_path.open("a+b") as lock_file:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _decode_index_payload(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        if exc.msg != "Extra data":
            raise
        payload, _ = json.JSONDecoder().raw_decode(raw)
        if not isinstance(payload, dict):
            raise
        return payload


def _read_index_unlocked(garden_root: Path) -> list[dict[str, Any]]:
    path = _run_index_path(garden_root)
    if not path.is_file():
        return []
    return list(_decode_index_payload(path.read_text(encoding="utf-8")).get("runs", []))


def _write_index_unlocked(garden_root: Path, records: list[dict[str, Any]]) -> None:
    path = _run_index_path(garden_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{get_ident()}.tmp")
    try:
        tmp_path.write_text(
            json.dumps({"runs": records}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _read_index(garden_root: Path) -> list[dict[str, Any]]:
    with _radiance_index_lock(garden_root):
        return _read_index_unlocked(garden_root)


def _write_index(garden_root: Path, records: list[dict[str, Any]]) -> None:
    with _radiance_index_lock(garden_root):
        _write_index_unlocked(garden_root, records)


def _run_target(garden_id: str, run_id: str, recipe_name: str) -> dict[str, str]:
    return {
        "target_type": RADIANCE_RUN_TARGET_TYPE,
        "garden_id": garden_id,
        "domain": RADIANCE_RUN_DOMAIN,
        "recipe": recipe_name,
        "run_id": run_id,
    }


def _normalize_run_id(value: str | None) -> str:
    if value:
        return slugify_name(value)
    timestamp = utc_now_iso().replace(":", "").replace("-", "").replace("Z", "").lower()
    return f"radiance_{timestamp}"


def _unwrap_target(target: dict[str, Any] | None) -> dict[str, Any] | None:
    if isinstance(target, dict) and isinstance(target.get("target"), dict):
        return target["target"]
    return target


def _validate_target_garden(
    *,
    target: dict[str, Any],
    manifest: GardenManifest,
    field_name: str,
) -> None:
    garden_id = target.get("garden_id")
    if garden_id and garden_id != manifest.garden_id:
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
    sky_file_target = _unwrap_target(sky_file_target)
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
    wea_target = _unwrap_target(wea_target)
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
        rad_par = value.get("radiance_parameters") or value.get("rad_par")
        if not isinstance(rad_par, str) and isinstance(value.get("target"), dict):
            target = value["target"]
            rad_par = target.get("radiance_parameters") or target.get("value")
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


def _upsert_record(garden_root: Path, record: dict[str, Any]) -> None:
    with _radiance_index_lock(garden_root):
        records = [
            item
            for item in _read_index_unlocked(garden_root)
            if item.get("run_id") != record.get("run_id")
        ]
        records.append(record)
        records.sort(key=lambda item: str(item.get("created_at", "")))
        _write_index_unlocked(garden_root, records)


def _run_record_by_id(garden_root: Path, run_id: str) -> dict[str, Any]:
    for record in _read_index(garden_root):
        if record.get("run_id") == run_id:
            return record
    raise ValueError(f"Radiance run was not found: {run_id}")


def _run_id_from_target_or_value(
    *,
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> str:
    run_target = _unwrap_target(run_target)
    if run_target is not None:
        if run_target.get("target_type") != RADIANCE_RUN_TARGET_TYPE:
            raise ValueError("run_target must be a radiance_run target.")
        if run_target.get("domain") != RADIANCE_RUN_DOMAIN:
            raise ValueError("run_target must reference honeybee_radiance.")
        return str(run_target["run_id"])
    if run_id:
        return run_id
    raise ValueError("Provide run_target or run_id.")


def _outputs_map(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): item for item in record.get("outputs", [])}


def _missing_outputs(recipe_name: str) -> list[dict[str, Any]]:
    return [
        {"name": name, "path": None, "exists": False}
        for name in OUTPUT_NAMES_BY_RECIPE[recipe_name]
    ]


def _recipe_log_status(
    *,
    run_dir: Path,
    recipe_name: str,
) -> tuple[str | None, str | None]:
    status_path = (
        run_dir
        / recipe_name.replace("-", "_")
        / "__logs__"
        / "status.json"
    )
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
    if raw_status is None:
        return None, str(message) if message else None
    return str(raw_status).strip().lower(), str(message) if message else None


def _recipe_log_progress_complete(
    *,
    run_dir: Path,
    recipe_name: str,
) -> bool:
    status_path = (
        run_dir
        / recipe_name.replace("-", "_")
        / "__logs__"
        / "status.json"
    )
    if not status_path.is_file():
        return False
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except Exception:  # pragma: no cover - corrupt SDK log file
        return False
    progress = payload.get("meta", {}).get("progress")
    if not isinstance(progress, dict):
        return False
    try:
        completed = int(progress.get("completed", 0))
        running = int(progress.get("running", 0))
        total = int(progress.get("total", 0))
    except (TypeError, ValueError):
        return False
    return total > 0 and completed >= total and running == 0


def _output_record(
    garden_root: Path,
    output_name: str,
    output_value: Any,
) -> dict[str, Any]:
    if output_value is None:
        return {"name": output_name, "path": None, "exists": False}
    values = (
        list(output_value)
        if isinstance(output_value, (list, tuple))
        else [output_value]
    )
    resolved_paths = [
        Path(item).expanduser().resolve()
        for item in values
        if isinstance(item, (str, Path)) and item
    ]
    existing_paths = [path for path in resolved_paths if path.exists()]
    primary_path = (
        existing_paths[0]
        if existing_paths
        else (resolved_paths[0] if resolved_paths else None)
    )
    if primary_path is None:
        return {"name": output_name, "path": None, "exists": False}
    exists = bool(existing_paths)
    record: dict[str, Any] = {
        "name": output_name,
        "path": (
            to_posix_relative(primary_path, garden_root)
            if exists
            else str(primary_path)
        ),
        "exists": exists,
    }
    if len(resolved_paths) > 1:
        record["paths"] = [
            to_posix_relative(path, garden_root) if path.exists() else str(path)
            for path in resolved_paths
        ]
    if existing_paths:
        record["size_bytes"] = sum(
            path.stat().st_size for path in existing_paths if path.is_file()
        )
    return record


def _fallback_output_record(
    *,
    garden_root: Path,
    run_dir: Path,
    recipe_name: str,
    output_name: str,
) -> dict[str, Any] | None:
    recipe_folder = run_dir / recipe_name.replace("-", "_")
    if not recipe_folder.is_dir():
        return None
    candidate_roots = [recipe_folder / output_name, recipe_folder / "results"]
    for root in candidate_roots:
        if not root.exists():
            continue
        grid_info = sorted(root.rglob("grids_info.json"))
        if grid_info:
            return _output_record(garden_root, output_name, grid_info[0].parent)
        if root.is_dir() and any(path.is_file() for path in root.rglob("*")):
            return _output_record(garden_root, output_name, root)
    return None


def _recipe_outputs(
    *,
    garden_root_path: Path,
    recipe: Recipe | None,
    recipe_name: str,
    run_dir: Path,
    warnings: list[str],
) -> list[dict[str, Any]]:
    outputs = []
    for name in OUTPUT_NAMES_BY_RECIPE[recipe_name]:
        try:
            output_value = (
                recipe.output_value_by_name(name, str(run_dir)) if recipe else None
            )
        except Exception as exc:  # pragma: no cover - depends on recipe failure mode
            output_value = None
            warnings.append(f"Could not resolve recipe output {name}: {exc}")
        record = _output_record(garden_root_path, name, output_value)
        if not record["exists"]:
            fallback = _fallback_output_record(
                garden_root=garden_root_path,
                run_dir=run_dir,
                recipe_name=recipe_name,
                output_name=name,
            )
            if fallback is not None:
                record = fallback
        outputs.append(record)
    return outputs


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
        "model_path",
        "run_folder",
        "outputs",
        "workers",
        "warnings",
        "radiance_parameters_path",
    )
    return {key: record.get(key) for key in keys if key in record}


def _reconcile_running_record(
    *,
    garden_root_path: Path,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Repair stale running records when a background recipe wrote final outputs."""
    if record.get("status") != "running":
        return record
    recipe_name = str(record.get("recipe") or "")
    if recipe_name not in OUTPUT_NAMES_BY_RECIPE:
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
        recipe=None,
        recipe_name=recipe_name,
        run_dir=run_dir,
        warnings=warnings,
    )
    outputs_exist = bool(outputs) and all(output.get("exists") for output in outputs)
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
    if outputs_exist and (
        logged_status in {"completed", "complete", "done", "success", "succeeded"}
        or _recipe_log_progress_complete(run_dir=run_dir, recipe_name=recipe_name)
    ):
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
            "tool": "get_radiance_run",
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
    run_dir = (garden_root_path / RADIANCE_RUNS_DIR / run_id).resolve()
    run_dir.relative_to(garden_root_path)
    run_dir.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    status = "completed"
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
    try:
        with _capture_recipe_stdio(run_dir):
            recipe.run(settings=settings, radiance_check=True, silent=silent)
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

    outputs = _recipe_outputs(
        garden_root_path=garden_root_path,
        recipe=recipe,
        recipe_name=recipe_name,
        run_dir=run_dir,
        warnings=warnings,
    )
    record = _run_record_by_id(garden_root_path, run_id)
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
        _unwrap_target(model_target),
    )
    model_path = _model_path_from_target(garden_root_path, resolved_model_target)
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

    run_dir = (garden_root_path / RADIANCE_RUNS_DIR / run_id).resolve()
    run_dir.relative_to(garden_root_path)
    run_dir.mkdir(parents=True, exist_ok=True)
    run_folder = to_posix_relative(run_dir, garden_root_path)
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

    _BACKGROUND_EXECUTOR.submit(
        run_radiance_recipe,
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
                "tool": "get_radiance_run",
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
    radiance_parameters: str | dict[str, Any] | None = None,
    run_id: str | None = None,
    workers: int | None = None,
    reload_old: bool = False,
    silent: bool = True,
) -> dict[str, Any]:
    """Start a grid-based Radiance recipe in the background."""
    normalized = calculation_type.strip().lower().replace(" ", "_")
    if normalized not in GRID_CALCULATION_TYPES:
        raise ValueError("calculation_type must be point_in_time or daylight_factor.")
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
            "calculation_type must be annual_daylight, annual_irradiance, or cumulative_radiation."
        )
    recipe_name, command_name = MATRIX_CALCULATION_TYPES[normalized]
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
    if grid_metrics is not None and recipe_name == "annual-daylight":
        inputs["grid-metrics"] = grid_metrics
    if schedule is not None and recipe_name == "annual-daylight":
        inputs["schedule"] = schedule
    if thresholds is not None and recipe_name == "annual-daylight":
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
