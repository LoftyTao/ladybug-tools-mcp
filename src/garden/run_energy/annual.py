"""Annual energy-use recipe execution services."""

from __future__ import annotations

from contextlib import contextmanager, redirect_stderr, redirect_stdout
import json
import logging
from pathlib import Path
import os
import subprocess
import sys
from threading import Thread, get_ident
from typing import Any

from ladybug.ddy import DDY
from ladybug.epw import EPW
from lbt_recipes.recipe import Recipe
from lbt_recipes.settings import RecipeSettings

from ladybug_tools_mcp.contracts.report import make_report
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from garden.honeybee_core.model_io import resolve_model_target
from garden.run_energy.output_requests import (
    simulation_parameter_with_output_request,
)

ENERGY_RUN_TARGET_TYPE = "energy_run"
ENERGY_RUN_DOMAIN = "honeybee_energy"
ENERGY_RUN_RECIPE = "annual_energy_use"
ENERGY_RUN_RECIPES = {
    ENERGY_RUN_RECIPE,
    "energyplus_idf",
    "openstudio_osm",
}
ENERGY_RUNS_DIR = Path("runs") / "energy"
ENERGY_RUN_INDEX = ENERGY_RUNS_DIR / "index.json"
OUTPUT_NAMES = ("err", "eui", "html", "result-report", "sql", "visual-report", "zsz")
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class _DaemonBackgroundExecutor:
    """Submit long recipe work without keeping stdio Agent sessions alive."""

    def submit(self, fn, **kwargs):
        thread = Thread(target=fn, kwargs=kwargs, name="lbt-energy-run", daemon=True)
        thread.start()
        return thread


class _SubprocessBackgroundExecutor:
    """Run background recipes outside the stdio MCP server process."""

    def submit(self, fn, **kwargs):
        if fn is not run_energy:
            return _DaemonBackgroundExecutor().submit(fn, **kwargs)
        garden_root = Path(str(kwargs["garden_root"])).expanduser().resolve()
        run_id = str(kwargs["run_id"])
        run_dir = (garden_root / ENERGY_RUNS_DIR / run_id).resolve()
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
                    "garden.run_energy.worker",
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
    return garden_root / ENERGY_RUN_INDEX


@contextmanager
def _energy_index_lock(garden_root: Path):
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
    with _energy_index_lock(garden_root):
        return _read_index_unlocked(garden_root)


def _write_index(garden_root: Path, records: list[dict[str, Any]]) -> None:
    with _energy_index_lock(garden_root):
        _write_index_unlocked(garden_root, records)


def _run_target(
    garden_id: str,
    run_id: str,
    *,
    recipe: str = ENERGY_RUN_RECIPE,
) -> dict[str, str]:
    return {
        "target_type": ENERGY_RUN_TARGET_TYPE,
        "garden_id": garden_id,
        "domain": ENERGY_RUN_DOMAIN,
        "recipe": recipe,
        "run_id": run_id,
    }


def _normalize_run_id(value: str | None) -> str:
    if value:
        return slugify_name(value)
    return f"energy_{utc_now_iso().replace(':', '').replace('-', '').replace('Z', '').lower()}"


def _validate_weather_path(value: str, *, field_name: str, suffix: str) -> str:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"{field_name} must reference an existing {suffix} file.")
    if path.suffix.lower() != suffix:
        raise ValueError(f"{field_name} must reference a {suffix} file.")
    return str(path)


def _resolve_garden_path(
    garden_root: Path,
    value: str | None,
    *,
    field_name: str,
    kind: str,
    suffix: str | None = None,
) -> Path | None:
    if value is None:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = garden_root / path
    path = path.resolve()
    try:
        path.relative_to(garden_root)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be inside the Garden root.") from exc
    if kind == "file":
        if not path.is_file():
            raise ValueError(f"{field_name} must reference an existing file.")
        if suffix is not None and path.suffix.lower() != suffix:
            raise ValueError(f"{field_name} must reference a {suffix} file.")
    elif kind == "directory":
        if not path.is_dir():
            raise ValueError(f"{field_name} must reference an existing directory.")
    else:  # pragma: no cover - internal guard
        raise ValueError(f"Unsupported path kind: {kind}")
    return path


def _weather_paths_from_inputs(
    *,
    garden_root: Path,
    garden_id: str,
    epw_path: str | None,
    ddy_path: str | None,
    weather_target: dict[str, Any] | None,
) -> tuple[str, str]:
    if weather_target is not None:
        if weather_target.get("target_type") != "weather_file":
            raise ValueError("weather_target must be a weather_file target.")
        target_garden_id = weather_target.get("garden_id")
        if target_garden_id != garden_id:
            raise ValueError("weather_target belongs to a different Garden.")
        epw_path = str(weather_target.get("epw_path") or epw_path or "")
        ddy_path = str(weather_target.get("ddy_path") or ddy_path or "")
    if not epw_path or not ddy_path:
        raise ValueError(
            "Provide epw_path and ddy_path, or provide weather_target with both paths."
        )
    epw = Path(epw_path).expanduser()
    ddy = Path(ddy_path).expanduser()
    if not epw.is_absolute():
        epw = garden_root / epw
    if not ddy.is_absolute():
        ddy = garden_root / ddy
    epw = epw.resolve()
    ddy = ddy.resolve()
    try:
        epw.relative_to(garden_root)
        ddy.relative_to(garden_root)
    except ValueError as exc:
        raise ValueError("Weather files must be inside the Garden root.") from exc
    return str(epw), str(ddy)


def _preflight_weather(epw_path: str, ddy_path: str) -> dict[str, Any]:
    issues: list[str] = []
    try:
        epw = EPW(epw_path)
        _ = epw.location.city
    except Exception as exc:
        issues.append(f"EPW could not be parsed by Ladybug SDK: {exc}")
    try:
        ddy = DDY.from_ddy_file(ddy_path)
        if not ddy.design_days:
            issues.append("DDY contains no design days.")
    except Exception as exc:
        issues.append(f"DDY could not be parsed by Ladybug SDK: {exc}")
    return {
        "status": "ok" if not issues else "failed",
        "issues": issues,
    }


def _model_path_from_target(garden_root: Path, model_target: dict[str, Any]) -> Path:
    path_value = model_target.get("path")
    if not path_value:
        raise ValueError(
            "Energy simulation requires a model target with a Garden-relative path."
        )
    model_path = (garden_root / str(path_value)).resolve()
    model_path.relative_to(garden_root)
    if not model_path.is_file():
        raise ValueError("Honeybee model file for energy simulation was not found.")
    return model_path


def _write_json_input(
    run_dir: Path, name: str, data: dict[str, Any] | None
) -> str | None:
    if data is None:
        return None
    input_dir = run_dir / "inputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    path = input_dir / name
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return str(path)


def _write_text_input(run_dir: Path, name: str, text: str) -> Path:
    input_dir = run_dir / "inputs"
    input_dir.mkdir(parents=True, exist_ok=True)
    path = input_dir / name
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def _resolve_additional_idf_input(
    *,
    garden_root: Path,
    run_dir: Path,
    additional_idf_path: str | None,
    additional_idf_text: str | None,
) -> tuple[Path | None, str | None]:
    if additional_idf_path is not None and additional_idf_text is not None:
        raise ValueError(
            "Provide either additional_idf_path or additional_idf_text, not both."
        )
    if additional_idf_text is not None:
        if not additional_idf_text.strip():
            raise ValueError("additional_idf_text must not be empty.")
        return _write_text_input(
            run_dir, "additional_idf.idf", additional_idf_text
        ), "text"
    path = _resolve_garden_path(
        garden_root,
        additional_idf_path,
        field_name="additional_idf_path",
        kind="file",
        suffix=".idf",
    )
    return path, "path" if path is not None else None


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


def _parse_key_value_lines(values: list[Any]) -> dict[str, Any] | None:
    parsed: dict[str, Any] = {}
    for value in values:
        if not isinstance(value, str) or ":" not in value:
            return None
        key, raw_value = value.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key:
            return None
        try:
            parsed[key] = float(raw_value)
        except ValueError:
            parsed[key] = raw_value
    return parsed


def _write_inline_output(run_dir: Path, output_name: str, value: Any) -> Path:
    output_dir = run_dir / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    payload: Any = value
    if isinstance(value, list):
        payload = _parse_key_value_lines(value) or value
    path = output_dir / f"{output_name}.json"
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path


def _output_record(
    garden_root: Path,
    run_dir: Path,
    output_name: str,
    output_value: Any,
) -> dict[str, Any]:
    if output_value is None:
        return {"name": output_name, "path": None, "exists": False}
    output_paths = (
        list(output_value)
        if isinstance(output_value, (list, tuple))
        else [output_value]
    )
    resolved_paths = [
        Path(item).expanduser().resolve()
        for item in output_paths
        if isinstance(item, (str, Path)) and item
    ]
    existing_paths = [path for path in resolved_paths if path.is_file()]
    if not existing_paths and output_name == "eui":
        existing_paths = [
            _write_inline_output(run_dir, output_name, output_value).resolve()
        ]
        resolved_paths = existing_paths
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
            to_posix_relative(path, garden_root) if path.is_file() else str(path)
            for path in resolved_paths
        ]
    if existing_paths:
        record["size_bytes"] = sum(path.stat().st_size for path in existing_paths)
    return record


def _upsert_record(garden_root: Path, record: dict[str, Any]) -> None:
    with _energy_index_lock(garden_root):
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
    raise ValueError(f"Energy run was not found: {run_id}")


def _run_id_from_target_or_value(
    *,
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> str:
    if run_target is not None:
        if run_target.get("target_type") != ENERGY_RUN_TARGET_TYPE:
            raise ValueError("run_target must be an energy_run target.")
        if run_target.get("domain") != ENERGY_RUN_DOMAIN:
            raise ValueError("run_target must reference honeybee_energy.")
        if run_target.get("recipe") not in ENERGY_RUN_RECIPES:
            allowed = ", ".join(sorted(ENERGY_RUN_RECIPES))
            raise ValueError(f"run_target must reference one of: {allowed}.")
        return str(run_target["run_id"])
    if run_id:
        return run_id
    raise ValueError("Provide run_target or run_id.")


def _outputs_map(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): item for item in record.get("outputs", [])}


def _absolute_output_path(
    garden_root: Path, record: dict[str, Any], output_name: str
) -> Path:
    output = _outputs_map(record).get(output_name)
    if not output or not output.get("path"):
        raise ValueError(f"Energy run has no {output_name} output.")
    path = (garden_root / str(output["path"])).resolve()
    path.relative_to(garden_root)
    if not path.is_file():
        raise ValueError(f"Energy run {output_name} output file is missing.")
    return path


def _public_run(record: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "run_id",
        "recipe",
        "status",
        "created_at",
        "completed_at",
        "model_target",
        "model_path",
        "weather_target",
        "epw_path",
        "ddy_path",
        "run_folder",
        "outputs",
        "units",
        "workers",
        "preflight",
        "output_request_target",
        "sim_par_path",
        "additional_idf_path",
        "additional_idf_source",
        "measures_path",
        "input_file_path",
        "workflow_path",
        "source_file_path",
        "run_input_path",
        "expand_objects",
    )
    return {key: record.get(key) for key in keys if key in record}


def _completed_reload_response(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    record: dict[str, Any],
) -> dict[str, Any]:
    run_id = str(record["run_id"])
    target = record.get("target") or _run_target(manifest.garden_id, run_id)
    poll_arguments = {"garden_root": str(garden_root), "run_target": target}
    return {
        "target": target,
        "energy_run_target": target,
        "run_target": target,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "run_id": run_id,
            "status": "completed",
            "recipe": record.get("recipe", ENERGY_RUN_RECIPE),
            "run_folder": record.get("run_folder"),
            "outputs": _outputs_map(record),
            "preflight": record.get("preflight"),
            "reloaded": True,
            "poll_next": {
                "tool": "get_energy_run",
                "arguments": poll_arguments,
            },
        },
        "report": make_report(
            status="ok",
            message="Existing completed annual energy-use simulation returned.",
        ),
    }


def _recipe_outputs(
    *,
    garden_root_path: Path,
    recipe: Recipe | None,
    run_dir: Path,
    warnings: list[str],
) -> list[dict[str, Any]]:
    outputs = []
    for name in OUTPUT_NAMES:
        try:
            output_path = (
                recipe.output_value_by_name(name, str(run_dir)) if recipe else None
            )
        except Exception as exc:  # pragma: no cover - depends on recipe failure mode
            output_path = None
            warnings.append(f"Could not resolve recipe output {name}: {exc}")
        outputs.append(_output_record(garden_root_path, run_dir, name, output_path))
    return outputs


def _missing_outputs() -> list[dict[str, Any]]:
    return [{"name": name, "path": None, "exists": False} for name in OUTPUT_NAMES]


def run_energy(
    *,
    garden_root: str,
    epw_path: str | None = None,
    ddy_path: str | None = None,
    weather_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
    sim_par: dict[str, Any] | None = None,
    output_request_target: dict[str, Any] | None = None,
    additional_idf_path: str | None = None,
    additional_idf_text: str | None = None,
    measures_path: str | None = None,
    run_id: str | None = None,
    units: str = "si",
    workers: int | None = None,
    reload_old: bool = False,
    silent: bool = True,
    validate_weather: bool = True,
) -> dict[str, Any]:
    """Run the annual-energy-use recipe for a Honeybee model in a Garden."""
    garden_root_path = _garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(
        garden_root_path, model_target
    )
    sim_par, resolved_output_request_target = simulation_parameter_with_output_request(
        garden_root=garden_root_path,
        output_request_target=output_request_target,
        sim_par=sim_par,
    )
    model_path = _model_path_from_target(garden_root_path, resolved_model_target)
    epw_path, ddy_path = _weather_paths_from_inputs(
        garden_root=garden_root_path,
        garden_id=manifest.garden_id,
        epw_path=epw_path,
        ddy_path=ddy_path,
        weather_target=weather_target,
    )
    epw_path = _validate_weather_path(epw_path, field_name="epw_path", suffix=".epw")
    ddy_path = _validate_weather_path(ddy_path, field_name="ddy_path", suffix=".ddy")
    measures_folder = _resolve_garden_path(
        garden_root_path,
        measures_path,
        field_name="measures_path",
        kind="directory",
    )
    units = units.lower().strip()
    if units not in {"si", "ip"}:
        raise ValueError("units must be either 'si' or 'ip'.")

    run_id = _normalize_run_id(run_id)
    run_dir = (garden_root_path / ENERGY_RUNS_DIR / run_id).resolve()
    run_dir.relative_to(garden_root_path)
    run_dir.mkdir(parents=True, exist_ok=True)
    sim_par_path = _write_json_input(run_dir, "simulation_parameter.json", sim_par)
    additional_idf_file, additional_idf_source = _resolve_additional_idf_input(
        garden_root=garden_root_path,
        run_dir=run_dir,
        additional_idf_path=additional_idf_path,
        additional_idf_text=additional_idf_text,
    )
    run_folder = to_posix_relative(run_dir, garden_root_path)

    started_at = utc_now_iso()
    target = _run_target(manifest.garden_id, run_id)
    warnings: list[str] = []
    preflight = (
        _preflight_weather(epw_path, ddy_path)
        if validate_weather
        else {"status": "skipped", "issues": []}
    )
    if preflight["status"] == "failed":
        warnings.extend(preflight["issues"])
        outputs = _recipe_outputs(
            garden_root_path=garden_root_path,
            recipe=None,
            run_dir=run_dir,
            warnings=warnings,
        )
        completed_at = utc_now_iso()
        record = {
            "run_id": run_id,
            "target": target,
            "recipe": ENERGY_RUN_RECIPE,
            "status": "failed",
            "created_at": started_at,
            "completed_at": completed_at,
            "model_target": resolved_model_target,
            "model_path": to_posix_relative(model_path, garden_root_path),
            "weather_target": weather_target,
            "epw_path": epw_path,
            "ddy_path": ddy_path,
            "run_folder": run_folder,
            "outputs": outputs,
            "units": units,
            "workers": workers,
            "warnings": warnings,
            "preflight": preflight,
        }
        if additional_idf_file is not None:
            record["additional_idf_path"] = to_posix_relative(
                additional_idf_file, garden_root_path
            )
            record["additional_idf_source"] = additional_idf_source
        if measures_folder is not None:
            record["measures_path"] = to_posix_relative(
                measures_folder, garden_root_path
            )
        if sim_par_path is not None:
            record["sim_par_path"] = to_posix_relative(
                Path(sim_par_path), garden_root_path
            )
        if resolved_output_request_target is not None:
            record["output_request_target"] = resolved_output_request_target
        _upsert_record(garden_root_path, record)
        return {
            "target": target,
            "summary_view": {
                "garden_target": manifest.target(),
                "target": target,
                "run_id": run_id,
                "status": "failed",
                "recipe": ENERGY_RUN_RECIPE,
                "run_folder": run_folder,
                "outputs": _outputs_map(record),
                "preflight": preflight,
            },
            "report": make_report(
                status="error",
                message="Annual energy-use simulation preflight failed; run record was saved.",
                warnings=warnings,
            ),
        }

    recipe = Recipe("annual-energy-use")
    recipe.input_value_by_name("model", str(model_path))
    recipe.input_value_by_name("epw", epw_path)
    recipe.input_value_by_name("ddy", ddy_path)
    recipe.input_value_by_name("units", units)
    if sim_par_path is not None:
        recipe.input_value_by_name("sim-par", sim_par_path)
    if additional_idf_file is not None:
        recipe.input_value_by_name("additional-idf", str(additional_idf_file))
    if measures_folder is not None:
        recipe.input_value_by_name("measures", str(measures_folder))

    settings = RecipeSettings(
        folder=str(run_dir),
        workers=workers,
        reload_old=reload_old,
        report_out=False,
    )
    status = "completed"
    try:
        with _capture_recipe_stdio(run_dir):
            recipe.run(
                settings=settings,
                openstudio_check=True,
                energyplus_check=True,
                silent=silent,
            )
    except Exception as exc:  # pragma: no cover - exercised by real engines
        status = "failed"
        warnings.append(str(exc))

    outputs = _recipe_outputs(
        garden_root_path=garden_root_path,
        recipe=recipe,
        run_dir=run_dir,
        warnings=warnings,
    )
    if status == "completed" and not _outputs_map({"outputs": outputs}).get(
        "eui", {}
    ).get("exists"):
        status = "failed"
        warnings.append("Recipe finished without an EUI output; marking run as failed.")
    completed_at = utc_now_iso()
    record = {
        "run_id": run_id,
        "target": target,
        "recipe": ENERGY_RUN_RECIPE,
        "status": status,
        "created_at": started_at,
        "completed_at": completed_at,
        "model_target": resolved_model_target,
        "model_path": to_posix_relative(model_path, garden_root_path),
        "weather_target": weather_target,
        "epw_path": epw_path,
        "ddy_path": ddy_path,
        "run_folder": run_folder,
        "outputs": outputs,
        "units": units,
        "workers": workers,
        "warnings": warnings,
        "preflight": preflight,
    }
    if additional_idf_file is not None:
        record["additional_idf_path"] = to_posix_relative(
            additional_idf_file, garden_root_path
        )
        record["additional_idf_source"] = additional_idf_source
    if measures_folder is not None:
        record["measures_path"] = to_posix_relative(measures_folder, garden_root_path)
    if sim_par_path is not None:
        record["sim_par_path"] = to_posix_relative(Path(sim_par_path), garden_root_path)
    if resolved_output_request_target is not None:
        record["output_request_target"] = resolved_output_request_target
    _upsert_record(garden_root_path, record)

    return {
        "target": target,
        "energy_run_target": target,
        "run_target": target,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "run_id": run_id,
            "status": status,
            "recipe": ENERGY_RUN_RECIPE,
            "run_folder": run_folder,
            "outputs": _outputs_map(record),
            "preflight": preflight,
        },
        "report": make_report(
            status="ok" if status == "completed" else "error",
            message=(
                "Annual energy-use simulation completed."
                if status == "completed"
                else "Annual energy-use simulation failed; run record was saved."
            ),
            warnings=warnings,
        ),
    }


def start_energy_run(
    *,
    garden_root: str,
    epw_path: str | None = None,
    ddy_path: str | None = None,
    weather_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
    sim_par: dict[str, Any] | None = None,
    output_request_target: dict[str, Any] | None = None,
    additional_idf_path: str | None = None,
    additional_idf_text: str | None = None,
    measures_path: str | None = None,
    run_id: str | None = None,
    units: str = "si",
    workers: int | None = None,
    reload_old: bool = False,
    silent: bool = True,
    validate_weather: bool = True,
) -> dict[str, Any]:
    """Start an annual-energy-use recipe in the background and return a run target."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    if reload_old and run_id:
        normalized_run_id = _normalize_run_id(run_id)
        for record in _read_index(garden_root_path):
            if (
                record.get("run_id") == normalized_run_id
                and record.get("status") == "completed"
            ):
                return _completed_reload_response(
                    garden_root=garden_root_path,
                    manifest=manifest,
                    record=record,
                )

    manifest, resolved_model_target = resolve_model_target(
        garden_root_path, model_target
    )
    sim_par, resolved_output_request_target = simulation_parameter_with_output_request(
        garden_root=garden_root_path,
        output_request_target=output_request_target,
        sim_par=sim_par,
    )
    model_path = _model_path_from_target(garden_root_path, resolved_model_target)
    epw_path, ddy_path = _weather_paths_from_inputs(
        garden_root=garden_root_path,
        garden_id=manifest.garden_id,
        epw_path=epw_path,
        ddy_path=ddy_path,
        weather_target=weather_target,
    )
    epw_path = _validate_weather_path(epw_path, field_name="epw_path", suffix=".epw")
    ddy_path = _validate_weather_path(ddy_path, field_name="ddy_path", suffix=".ddy")
    measures_folder = _resolve_garden_path(
        garden_root_path,
        measures_path,
        field_name="measures_path",
        kind="directory",
    )
    units = units.lower().strip()
    if units not in {"si", "ip"}:
        raise ValueError("units must be either 'si' or 'ip'.")

    run_id = _normalize_run_id(run_id)
    existing_records = _read_index(garden_root_path)
    for record in existing_records:
        if record.get("run_id") == run_id and record.get("status") == "running":
            raise ValueError(f"Energy run is already running: {run_id}")

    run_dir = (garden_root_path / ENERGY_RUNS_DIR / run_id).resolve()
    run_dir.relative_to(garden_root_path)
    run_dir.mkdir(parents=True, exist_ok=True)
    sim_par_path = _write_json_input(run_dir, "simulation_parameter.json", sim_par)
    additional_idf_file, additional_idf_source = _resolve_additional_idf_input(
        garden_root=garden_root_path,
        run_dir=run_dir,
        additional_idf_path=additional_idf_path,
        additional_idf_text=additional_idf_text,
    )
    run_folder = to_posix_relative(run_dir, garden_root_path)
    target = _run_target(manifest.garden_id, run_id)
    started_at = utc_now_iso()
    preflight = (
        _preflight_weather(epw_path, ddy_path)
        if validate_weather
        else {"status": "skipped", "issues": []}
    )
    warnings = list(preflight.get("issues", []))

    if preflight["status"] == "failed":
        record_status = "failed"
        report_status = "error"
        message = "Annual energy-use simulation preflight failed; run record was saved."
        completed_at = utc_now_iso()
    else:
        record_status = "running"
        report_status = "ok"
        message = "Annual energy-use simulation started; poll the energy_run target for status."
        completed_at = None

    record: dict[str, Any] = {
        "run_id": run_id,
        "target": target,
        "recipe": ENERGY_RUN_RECIPE,
        "status": record_status,
        "created_at": started_at,
        "model_target": resolved_model_target,
        "model_path": to_posix_relative(model_path, garden_root_path),
        "weather_target": weather_target,
        "epw_path": epw_path,
        "ddy_path": ddy_path,
        "run_folder": run_folder,
        "outputs": _missing_outputs(),
        "units": units,
        "workers": workers,
        "warnings": warnings,
        "preflight": preflight,
    }
    if additional_idf_file is not None:
        record["additional_idf_path"] = to_posix_relative(
            additional_idf_file, garden_root_path
        )
        record["additional_idf_source"] = additional_idf_source
    if measures_folder is not None:
        record["measures_path"] = to_posix_relative(measures_folder, garden_root_path)
    if completed_at is not None:
        record["completed_at"] = completed_at
    if sim_par_path is not None:
        record["sim_par_path"] = to_posix_relative(Path(sim_par_path), garden_root_path)
    if resolved_output_request_target is not None:
        record["output_request_target"] = resolved_output_request_target
    _upsert_record(garden_root_path, record)

    if record_status == "running":
        _BACKGROUND_EXECUTOR.submit(
            run_energy,
            garden_root=str(garden_root_path),
            epw_path=None if weather_target is not None else epw_path,
            ddy_path=None if weather_target is not None else ddy_path,
            weather_target=weather_target,
            model_target=resolved_model_target,
            sim_par=sim_par,
            output_request_target=resolved_output_request_target,
            additional_idf_path=(
                str(additional_idf_file) if additional_idf_file is not None else None
            ),
            additional_idf_text=None,
            measures_path=str(measures_folder) if measures_folder is not None else None,
            run_id=run_id,
            units=units,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            validate_weather=False,
        )

    poll_arguments = {"garden_root": str(garden_root_path), "run_target": target}
    return {
        "target": target,
        "energy_run_target": target,
        "run_target": target,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "run_id": run_id,
            "status": record_status,
            "recipe": ENERGY_RUN_RECIPE,
            "run_folder": run_folder,
            "outputs": _outputs_map(record),
            "preflight": preflight,
            "poll_next": {
                "tool": "get_energy_run",
                "arguments": poll_arguments,
            },
        },
        "report": make_report(status=report_status, message=message, warnings=warnings),
    }


def list_energy_runs(
    *,
    garden_root: str,
    status: str | None = None,
) -> dict[str, Any]:
    """List Energy simulation runs registered in a Garden."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    records = [_public_run(record) for record in _read_index(garden_root_path)]
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
            status="ok", message=f"Found {len(records)} energy run(s)."
        ),
    }


def get_energy_run(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Get one Energy simulation run record."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_run_id = _run_id_from_target_or_value(run_target=run_target, run_id=run_id)
    record = _public_run(_run_record_by_id(garden_root_path, resolved_run_id))
    outputs = list(record.get("outputs", []))
    status = record.get("status")
    return {
        "status": status,
        "run_id": resolved_run_id,
        "summary_view": {
            "garden_target": manifest.target(),
            "run": record,
            "run_id": resolved_run_id,
            "status": status,
            "outputs": outputs,
        },
        "report": make_report(
            status="ok", message=f"Energy run returned: {resolved_run_id}"
        ),
    }


def list_energy_run_outputs(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """List output files for one Energy simulation run."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_run_id = _run_id_from_target_or_value(run_target=run_target, run_id=run_id)
    record = _run_record_by_id(garden_root_path, resolved_run_id)
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
            message=f"Found {len(outputs)} output(s) for energy run {resolved_run_id}.",
        ),
    }


def read_energy_eui(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Read the EUI JSON output for one Energy simulation run."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_run_id = _run_id_from_target_or_value(run_target=run_target, run_id=run_id)
    record = _run_record_by_id(garden_root_path, resolved_run_id)
    eui_path = _absolute_output_path(garden_root_path, record, "eui")
    eui = json.loads(eui_path.read_text(encoding="utf-8"))
    return {
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": resolved_run_id,
            "eui": eui,
            "path": to_posix_relative(eui_path, garden_root_path),
        },
        "report": make_report(
            status="ok", message=f"Energy EUI returned for run {resolved_run_id}."
        ),
    }


def read_energy_errors(
    *,
    garden_root: str,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    max_chars: int = 12000,
) -> dict[str, Any]:
    """Read a bounded EnergyPlus ERR output for one Energy simulation run."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_run_id = _run_id_from_target_or_value(run_target=run_target, run_id=run_id)
    record = _run_record_by_id(garden_root_path, resolved_run_id)
    err_path = _absolute_output_path(garden_root_path, record, "err")
    text = err_path.read_text(encoding="utf-8", errors="replace")
    truncated = len(text) > max_chars
    visible_text = text[:max_chars]
    lower_lines = [line.lower() for line in text.splitlines()]
    warning_count = sum("** warning **" in line for line in lower_lines)
    severe_count = sum("** severe" in line for line in lower_lines)
    fatal_count = sum("** fatal" in line for line in lower_lines)
    return {
        "text": visible_text,
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": resolved_run_id,
            "path": to_posix_relative(err_path, garden_root_path),
            "truncated": truncated,
            "warning_count": warning_count,
            "severe_count": severe_count,
            "fatal_count": fatal_count,
        },
        "report": make_report(
            status="ok",
            message=f"Energy ERR returned for run {resolved_run_id}.",
            warnings=["ERR output was truncated."] if truncated else [],
        ),
    }
