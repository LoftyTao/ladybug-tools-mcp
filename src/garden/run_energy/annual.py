"""Annual energy-use recipe execution services."""

from __future__ import annotations

from contextlib import contextmanager, redirect_stderr, redirect_stdout
import json
import logging
from pathlib import Path
import os
import shutil
import subprocess
import sys
from typing import Any

from ladybug.ddy import DDY
from ladybug.epw import EPW

from ladybug_tools_mcp.contracts.report import make_report
from garden.background import submit_worker_process
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import simulation_folder_name, to_posix_relative
from garden.run_ledger import (
    RunLedger,
    make_run_target,
    normalize_run_id,
    project_run,
    serialized_run_start,
)
from garden.run_ledger import run_id_from_target_or_value
from garden.honeybee_core.model_io import resolve_model_target
from garden.ironbug_console.energy_runtime import (
    PYTHON_ONLY_ENV,
    PythonIronbugRuntimeUnsupported,
    prepare_python_only_energy_model,
)
from garden.run_energy.output_requests import (
    simulation_parameter_with_output_request,
)
from garden.run_energy.parameters import (
    load_simulation_parameter,
    resolve_simulation_parameter_design_days,
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
GARDEN_VERSION_NEXT_TOOL = "GD_create_version"


def _recipe_cli_path(path_value: str | None = None) -> str:
    """Ensure recipe subprocesses can find CLIs installed in the active venv."""
    scripts_dir = Path(sys.executable).resolve().parent
    path_parts = [
        part
        for part in (path_value or os.environ.get("PATH") or "").split(os.pathsep)
        if part
    ]
    normalized = {str(Path(part).resolve()).lower() for part in path_parts}
    scripts_value = str(scripts_dir)
    if scripts_value.lower() not in normalized:
        path_parts.insert(0, scripts_value)
    return os.pathsep.join(path_parts)


def _ensure_windows_install_env(env: dict[str, str]) -> None:
    if os.name != "nt":
        return
    env.setdefault("PROGRAMFILES", r"C:\Program Files")
    env.setdefault("ProgramFiles", env["PROGRAMFILES"])
    env.setdefault("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    env.setdefault("ProgramFiles(x86)", env["PROGRAMFILES(X86)"])


def _console_executable(name: str) -> str:
    executable_name = f"{name}.exe" if os.name == "nt" else name
    return str(Path(sys.executable).resolve().parent / executable_name)


@contextmanager
def _recipe_cli_environment():
    previous_path = os.environ.get("PATH")
    os.environ["PATH"] = _recipe_cli_path(previous_path)
    try:
        yield
    finally:
        if previous_path is None:
            os.environ.pop("PATH", None)
        else:
            os.environ["PATH"] = previous_path


def _submit_energy_background(**kwargs: Any) -> subprocess.Popen:
    garden_root = Path(str(kwargs["garden_root"])).expanduser().resolve()
    run_id = str(kwargs["run_id"])
    record = _run_record_by_id(garden_root, run_id)
    run_folder = record.get("run_folder")
    if not isinstance(run_folder, str) or not run_folder:
        raise ValueError(f"Energy run has no valid run folder: {run_id}")
    run_dir = (garden_root / run_folder).resolve()
    run_dir.relative_to(garden_root)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["PATH"] = _recipe_cli_path(env.get("PATH"))
    _ensure_windows_install_env(env)
    temp_dir = (garden_root / "tmp" / run_dir.name).resolve()
    temp_dir.relative_to(garden_root)
    temp_dir.mkdir(parents=True, exist_ok=True)
    env["TEMP"] = str(temp_dir)
    env["TMP"] = str(temp_dir)
    return submit_worker_process(
        garden_root=garden_root,
        run_dir=run_dir,
        worker_module="garden.run_energy.worker",
        request={"garden_root": str(garden_root), "run_id": run_id},
        cwd=PROJECT_ROOT,
        environment=env,
    )


def _garden_root(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _run_index_path(garden_root: Path) -> Path:
    return garden_root / ENERGY_RUN_INDEX


_ENERGY_RUN_LEDGER = RunLedger(
    lock="file",
    atomic=True,
    recover_trailing_json=True,
    sort_by_created_at=True,
)


def _read_index(garden_root: Path) -> list[dict[str, Any]]:
    return _ENERGY_RUN_LEDGER.list(_run_index_path(garden_root))


def _run_target(
    garden_id: str,
    run_id: str,
    *,
    recipe: str = ENERGY_RUN_RECIPE,
) -> dict[str, str]:
    return make_run_target(
        target_type=ENERGY_RUN_TARGET_TYPE,
        garden_id=garden_id,
        domain=ENERGY_RUN_DOMAIN,
        recipe=recipe,
        run_id=run_id,
    )


def _normalize_run_id(value: str | None) -> str:
    return normalize_run_id(
        value,
        value
        or f"energy_{utc_now_iso().replace(':', '').replace('-', '').replace('Z', '').lower()}",
    )


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


def _matches_registered_weather_target(
    requested: dict[str, Any], registered: dict[str, Any]
) -> bool:
    if registered.get("target_type") != "weather_file":
        return False
    for key in ("identifier", "path", "epw_path", "ddy_path", "stat_path"):
        requested_value = requested.get(key)
        registered_value = registered.get(key)
        if requested_value and registered_value and requested_value == registered_value:
            return True
    return False


def _complete_weather_target_from_manifest(
    *,
    weather_target: dict[str, Any] | None,
    manifest: GardenManifest,
) -> dict[str, Any] | None:
    if weather_target is None:
        return None
    if weather_target.get("target_type") != "weather_file":
        return dict(weather_target)
    if weather_target.get("garden_id") != manifest.garden_id:
        return dict(weather_target)
    if weather_target.get("epw_path") and weather_target.get("ddy_path"):
        return dict(weather_target)
    for registered in manifest.weather_files:
        if _matches_registered_weather_target(weather_target, registered):
            completed = dict(registered)
            completed.update(
                {key: value for key, value in weather_target.items() if value is not None}
            )
            return completed
    return dict(weather_target)


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
            "Provide epw_path and ddy_path, or provide a complete weather_target "
            "with both epw_path and ddy_path. If you only have an identifier/path "
                "for a registered Garden weather file, call EP_search_weather_files with "
            "require_ddy=true and pass matches[i].target."
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


def _run_dir_from_record(garden_root: Path, record: dict[str, Any]) -> Path:
    run_folder = record.get("run_folder")
    if not isinstance(run_folder, str) or not run_folder:
        raise ValueError(f"Energy run has no valid run folder: {record.get('run_id')}")
    run_dir = (garden_root / run_folder).resolve()
    run_dir.relative_to(garden_root)
    return run_dir


def _record_path(
    garden_root: Path,
    value: Any,
    *,
    field_name: str,
    kind: str = "file",
) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Energy run record has no valid {field_name}.")
    return _resolve_garden_path(garden_root, value, field_name=field_name, kind=kind)


def _clear_native_recipe_dir(
    garden_root: Path,
    recipe_dir: Path,
) -> None:
    """Clear one native calculation directory after checking its Garden scope."""
    garden_root = garden_root.resolve()
    recipe_dir = recipe_dir.resolve()
    recipe_dir.relative_to(garden_root)
    if recipe_dir == garden_root:
        raise ValueError("Energy native calculation directory cannot be the Garden root.")
    if recipe_dir.is_symlink() or recipe_dir.is_file():
        recipe_dir.unlink()
    elif recipe_dir.is_dir():
        for child in recipe_dir.iterdir():
            if child.is_symlink() or child.is_file():
                child.unlink()
            else:
                shutil.rmtree(child)
    recipe_dir.mkdir(parents=True, exist_ok=True)


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
    is_path_like_output = isinstance(output_value, (str, Path)) or (
        isinstance(output_value, (list, tuple))
        and all(isinstance(item, (str, Path)) for item in output_value)
    )
    if not existing_paths and output_name == "eui" and not is_path_like_output:
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
    _ENERGY_RUN_LEDGER.upsert(_run_index_path(garden_root), record)


def _run_record_by_id(garden_root: Path, run_id: str) -> dict[str, Any]:
    record = _ENERGY_RUN_LEDGER.get(_run_index_path(garden_root), run_id)
    if record is not None:
        return record
    raise ValueError(f"Energy run was not found: {run_id}")


def _run_id_from_target_or_value(
    *,
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> str:
    return run_id_from_target_or_value(
        run_target,
        run_id,
        target_type=ENERGY_RUN_TARGET_TYPE,
        domain=ENERGY_RUN_DOMAIN,
        allowed_recipes=ENERGY_RUN_RECIPES,
        target_run_id_required=False,
    )


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


def _output_exists(record: dict[str, Any], output_name: str) -> bool:
    output = _outputs_map(record).get(output_name)
    return bool(output and output.get("exists") and output.get("path"))


def _err_summary(
    *,
    garden_root: Path,
    record: dict[str, Any],
    max_chars: int = 12000,
) -> dict[str, Any]:
    err_path = _absolute_output_path(garden_root, record, "err")
    text = err_path.read_text(encoding="utf-8", errors="replace")
    truncated = len(text) > max_chars
    visible_text = text[:max_chars]
    lines = text.splitlines()
    lower_lines = [line.lower() for line in lines]
    normalized_lines = [" ".join(line.split()) for line in lower_lines]
    warning_count = sum("** warning **" in line for line in normalized_lines)
    severe_count = sum("** severe" in line for line in normalized_lines)
    fatal_count = sum("** fatal" in line for line in normalized_lines)
    severe_errors = [
        lines[index].strip()
        for index, line in enumerate(normalized_lines)
        if "** severe" in line
    ]
    fatal_errors = [
        lines[index].strip()
        for index, line in enumerate(normalized_lines)
        if "** fatal" in line
    ]
    last_severe_error = next(
        (
            lines[index].partition("Last severe error=")[2].strip()
            for index, line in enumerate(lower_lines)
            if "last severe error=" in line
        ),
        None,
    )
    return {
        "text": visible_text,
        "path": to_posix_relative(err_path, garden_root),
        "truncated": truncated,
        "warning_count": warning_count,
        "severe_count": severe_count,
        "fatal_count": fatal_count,
        "last_severe_error": last_severe_error,
        "severe_errors": severe_errors,
        "fatal_errors": fatal_errors,
    }


def _err_repair_hints(text: str) -> list[dict[str, str]]:
    normalized = " ".join(text.lower().split())
    if (
        "autosizing of heating coil ua failed" in normalized
        or ("coil:heating:water" in normalized and " ua " in f" {normalized} ")
    ):
        return [
            {
                "code": "ironbug_heating_water_coil_ua_or_flow_not_numeric",
                "message": (
                    "For Ironbug IB_CoilHeatingWater, set numeric "
                    "u_factor_times_area_value and numeric maximum_water_flow_rate, "
                    "then rebuild the owning FCU, unit-heater, reheat terminal, or "
                    "HVAC graph before applying DetailedHVAC again."
                ),
                "recommended_tool": "IB_coil_heating_water",
            }
        ]
    return []


def _energy_run_result_evidence(
    *,
    garden_root: Path,
    run_id: str,
    record: dict[str, Any],
) -> dict[str, Any]:
    status = str(record.get("status") or "unknown")
    output_names = [
        str(output.get("name"))
        for output in list(record.get("outputs", []))
        if output.get("name") and output.get("exists")
    ]
    eui_exists = _output_exists(record, "eui")
    err_exists = _output_exists(record, "err")
    sql_exists = _output_exists(record, "sql")
    err_summary: dict[str, Any] | None = None
    if err_exists:
        err_summary = {
            key: value
            for key, value in _err_summary(garden_root=garden_root, record=record).items()
            if key != "text"
        }
    severe_count = int((err_summary or {}).get("severe_count") or 0)
    fatal_count = int((err_summary or {}).get("fatal_count") or 0)
    completed_with_diagnostics = bool(
        status == "completed" and eui_exists and err_exists and sql_exists
    )
    final_answer_ready = bool(
        completed_with_diagnostics and not severe_count and not fatal_count
    )
    if status in {"queued", "running"}:
        recommended_next_tools = ["EP_poll_simulation"]
        final_answer_guidance = (
            "This Energy run is already in progress. Poll this run_target with "
            "EP_poll_simulation; do not start another Energy run with the same run_id."
        )
    elif final_answer_ready:
        recommended_next_tools = ["EP_read_eui", GARDEN_VERSION_NEXT_TOOL]
        final_answer_guidance = (
            "The Energy run is completed and EUI, SQL, and clean ERR evidence "
            "are present. Call EP_read_eui, report the result, create a "
            "Garden version checkpoint if this is the final accepted scenario, "
            "and do not start another Energy run unless the user asks for a new scenario."
        )
    elif completed_with_diagnostics:
        recommended_next_tools = ["EP_read_eui", "EP_read_errors"]
        final_answer_guidance = (
            "The Energy run is completed and EUI, SQL, and ERR evidence are "
            "present, but ERR diagnostics contain severe or fatal entries. "
            "Report the EUI together with the ERR status or precise blocker; "
            "do not start another Energy run unless the user explicitly asks "
            "to repair and rerun."
        )
    elif status == "completed":
        recommended_next_tools = ["EP_list_run_outputs", "EP_read_errors"]
        final_answer_guidance = (
            "The Energy run is completed but complete EUI/SQL/ERR evidence is "
            "not present. Inspect outputs and diagnostics for a precise blocker; "
            "do not start another Energy run unless repairing a known issue."
        )
    else:
        recommended_next_tools = ["EP_list_run_outputs", "EP_read_errors"]
        final_answer_guidance = (
            "The Energy run is not completed successfully. Read outputs and ERR "
            "diagnostics to report the blocker before considering a rerun."
        )
    return {
        "run_id": run_id,
        "run_status": status,
        "eui_exists": eui_exists,
        "err_exists": err_exists,
        "sql_exists": sql_exists,
        "completed_with_diagnostics": completed_with_diagnostics,
        "available_output_names": output_names,
        "err_summary": err_summary,
        "severe_count": severe_count,
        "fatal_count": fatal_count,
        "final_answer_ready": final_answer_ready,
        "should_start_another_run": False,
        "final_answer_guidance": final_answer_guidance,
        "recommended_next_tools": recommended_next_tools,
    }


def _public_run(record: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "run_id",
        "target",
        "recipe",
        "status",
        "created_at",
        "completed_at",
        "model_target",
        "model_display_name",
        "model_path",
        "weather_target",
        "epw_path",
        "ddy_path",
        "run_folder",
        "outputs",
        "units",
        "workers",
        "preflight",
        "simulation_parameter_target",
        "design_day_resolution",
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
        "python_ironbug_console_runtime",
    )
    return project_run(record, keys)


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
            "simulation_parameter_target": record.get("simulation_parameter_target"),
            "design_day_resolution": record.get("design_day_resolution"),
            "python_ironbug_console_runtime": record.get(
                "python_ironbug_console_runtime"
            ),
            "reloaded": True,
            "result_evidence": _energy_run_result_evidence(
                garden_root=garden_root,
                run_id=run_id,
                record=record,
            ),
            "poll_next": {
                "tool": "EP_poll_simulation",
                "arguments": poll_arguments,
            },
        },
        "result_evidence": _energy_run_result_evidence(
            garden_root=garden_root,
            run_id=run_id,
            record=record,
        ),
        "report": make_report(
            status="ok",
            message="Existing completed annual energy-use simulation returned.",
        ),
    }


def _existing_run_response(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    record: dict[str, Any],
) -> dict[str, Any]:
    run_id = str(record["run_id"])
    target = record.get("target") or _run_target(manifest.garden_id, run_id)
    status = str(record.get("status") or "unknown")
    evidence = _energy_run_result_evidence(
        garden_root=garden_root,
        run_id=run_id,
        record=record,
    )
    poll_arguments = {"garden_root": str(garden_root), "run_target": target}
    return {
        "target": target,
        "energy_run_target": target,
        "run_target": target,
        "status": status,
        "run_id": run_id,
        "result_evidence": evidence,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "run_id": run_id,
            "status": status,
            "recipe": record.get("recipe", ENERGY_RUN_RECIPE),
            "run_folder": record.get("run_folder"),
            "outputs": _outputs_map(record),
            "preflight": record.get("preflight"),
            "simulation_parameter_target": record.get("simulation_parameter_target"),
            "design_day_resolution": record.get("design_day_resolution"),
            "python_ironbug_console_runtime": record.get(
                "python_ironbug_console_runtime"
            ),
            "result_evidence": evidence,
            "poll_next": {
                "tool": "EP_poll_simulation",
                "arguments": poll_arguments,
            },
        },
        "report": make_report(
            status="ok",
            message=(
                f"Existing Energy run returned: {run_id}. "
                "Poll or read outputs instead of starting another run with the same run_id."
            ),
        ),
    }


def _recipe_outputs(
    *,
    garden_root_path: Path,
    run_dir: Path,
    warnings: list[str],
) -> list[dict[str, Any]]:
    outputs = []
    recipe_dir = run_dir / "openstudio"
    direct_outputs = {
        "err": recipe_dir / "run" / "eplusout.err",
        "eui": recipe_dir / "eui.json",
        "html": recipe_dir / "run" / "eplustbl.htm",
        "result-report": recipe_dir / "reports" / "openstudio_results_report.html",
        "sql": recipe_dir / "run" / "eplusout.sql",
        "visual-report": recipe_dir / "reports" / "view_data_report.html",
        "zsz": recipe_dir / "run" / "epluszsz.csv",
    }
    for name in OUTPUT_NAMES:
        output_path = direct_outputs.get(name)
        outputs.append(_output_record(garden_root_path, run_dir, name, output_path))
    return outputs


def _run_honeybee_energy_cli(
    *,
    model_path: Path,
    epw_path: str,
    run_dir: Path,
    sim_par_path: str | None,
    additional_idf_file: Path | None,
    measures_folder: Path | None,
    units: str,
    silent: bool,
) -> tuple[int, int]:
    recipe_dir = run_dir / "openstudio"
    recipe_dir.mkdir(parents=True, exist_ok=True)
    command = [
        _console_executable("honeybee-energy"),
        "simulate",
        "model",
        str(model_path),
        epw_path,
        "--report-units",
        units,
        "--folder",
        str(recipe_dir),
    ]
    if sim_par_path is not None:
        command.extend(["--sim-par-json", sim_par_path])
    if measures_folder is not None:
        command.extend(["--measures", str(measures_folder)])
    if additional_idf_file is not None:
        command.extend(["--additional-idf", str(additional_idf_file)])
    if silent:
        command.append("--log-file")
        command.append("-")

    with _recipe_cli_environment(), _capture_recipe_stdio(run_dir):
        env = os.environ.copy()
        env["PATH"] = _recipe_cli_path(env.get("PATH"))
        _ensure_windows_install_env(env)
        simulate = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            env=env,
            check=False,
        )
        eui_status = 1
        sql_path = recipe_dir / "run" / "eplusout.sql"
        if sql_path.is_file():
            eui_path = recipe_dir / "eui.json"
            eui_command = [
                _console_executable("honeybee-energy"),
                "result",
                "energy-use-intensity",
                str(recipe_dir / "run"),
                f"--{units}",
                "--output-file",
                str(eui_path),
            ]
            eui = subprocess.run(
                eui_command,
                cwd=str(PROJECT_ROOT),
                env=env,
                check=False,
            )
            eui_status = int(eui.returncode)
        return int(simulate.returncode), eui_status


def _missing_outputs() -> list[dict[str, Any]]:
    return [{"name": name, "path": None, "exists": False} for name in OUTPUT_NAMES]


def _should_prepare_python_ironbug_runtime(model_path: Path) -> bool:
    """Return True when a Honeybee model needs Python Ironbug translation."""

    if os.environ.get(PYTHON_ONLY_ENV) == "1":
        return True
    try:
        text = model_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return '"type": "DetailedHVAC"' in text


def _energy_response(
    *,
    manifest: GardenManifest,
    record: dict[str, Any],
    message: str,
    report_status: str | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    status = str(record.get("status") or "unknown")
    target = record.get("target") or _run_target(
        manifest.garden_id,
        str(record["run_id"]),
        recipe=str(record.get("recipe") or ENERGY_RUN_RECIPE),
    )
    return {
        "target": target,
        "energy_run_target": target,
        "run_target": target,
        "status": status,
        "run_id": record.get("run_id"),
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "run_id": record.get("run_id"),
            "status": status,
            "recipe": record.get("recipe", ENERGY_RUN_RECIPE),
            "run_folder": record.get("run_folder"),
            "outputs": _outputs_map(record),
            "preflight": record.get("preflight"),
            "simulation_parameter_target": record.get("simulation_parameter_target"),
            "design_day_resolution": record.get("design_day_resolution"),
            "python_ironbug_console_runtime": record.get(
                "python_ironbug_console_runtime"
            ),
        },
        "report": make_report(
            status=report_status or ("ok" if status in {"running", "completed"} else "error"),
            message=message,
            warnings=warnings or list(record.get("warnings") or []),
        ),
    }


def _mark_energy_failed(
    garden_root: Path,
    run_id: str,
    error: str,
) -> dict[str, Any]:
    record = _run_record_by_id(garden_root, run_id)
    warnings = list(record.get("warnings") or [])
    if error not in warnings:
        warnings.append(error)
    record.update(
        {
            "status": "failed",
            "completed_at": utc_now_iso(),
            "warnings": warnings,
        }
    )
    try:
        run_dir = _run_dir_from_record(garden_root, record)
        record["outputs"] = _recipe_outputs(
            garden_root_path=garden_root,
            run_dir=run_dir,
            warnings=warnings,
        )
    except (OSError, ValueError):
        record["outputs"] = _missing_outputs()
    _upsert_record(garden_root, record)
    return record


@serialized_run_start
def _prepare_annual_energy_run(
    *,
    garden_root: str,
    epw_path: str | None = None,
    ddy_path: str | None = None,
    weather_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
    sim_par: dict[str, Any] | None = None,
    simulation_parameter_target: dict[str, Any] | None = None,
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
    """Prepare one annual run and register it before execution."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    normalized_run_id = _normalize_run_id(run_id)
    existing = _ENERGY_RUN_LEDGER.get(
        _run_index_path(garden_root_path), normalized_run_id
    )
    if existing is not None:
        return {"manifest": manifest, "record": existing, "reused": True}

    manifest, resolved_model_target = resolve_model_target(
        garden_root_path, model_target
    )
    parameter, resolved_parameter_target, sim_par = load_simulation_parameter(
        garden_root=garden_root_path,
        simulation_parameter_target=simulation_parameter_target,
        sim_par=sim_par,
    )
    model_path = _model_path_from_target(garden_root_path, resolved_model_target)
    model_data = json.loads(model_path.read_text(encoding="utf-8"))
    model_display_name = model_data.get("display_name") or model_data["identifier"]
    weather_target = _complete_weather_target_from_manifest(
        weather_target=weather_target,
        manifest=manifest,
    )
    epw_path, ddy_path = _weather_paths_from_inputs(
        garden_root=garden_root_path,
        garden_id=manifest.garden_id,
        epw_path=epw_path,
        ddy_path=ddy_path,
        weather_target=weather_target,
    )
    epw_path = _validate_weather_path(epw_path, field_name="epw_path", suffix=".epw")
    ddy_path = _validate_weather_path(ddy_path, field_name="ddy_path", suffix=".ddy")
    design_day_resolution = {"status": "not_requested", "resolved_count": 0}
    if parameter is not None:
        strategies = (resolved_parameter_target or {}).get("design_day_strategies") or []
        if strategies:
            try:
                parameter, design_day_resolution = resolve_simulation_parameter_design_days(
                    parameter,
                    design_day_strategies=strategies,
                    ddy_path=ddy_path,
                )
            except ValueError as exc:
                design_day_resolution = {
                    "status": "failed",
                    "strategies": list(strategies),
                    "resolved_count": 0,
                    "message": str(exc),
                }
        else:
            design_day_resolution = {
                "status": "embedded",
                "resolved_count": len(parameter.sizing_parameter.design_days),
            }
        sim_par = parameter.to_dict()
    sim_par, resolved_output_request_target = simulation_parameter_with_output_request(
        garden_root=garden_root_path,
        output_request_target=output_request_target,
        sim_par=sim_par,
    )
    if resolved_output_request_target is None and resolved_parameter_target is not None:
        target_output_request = resolved_parameter_target.get("output_request_target")
        if isinstance(target_output_request, dict):
            resolved_output_request_target = target_output_request
    measures_folder = _resolve_garden_path(
        garden_root_path,
        measures_path,
        field_name="measures_path",
        kind="directory",
    )
    units = units.lower().strip()
    if units not in {"si", "ip"}:
        raise ValueError("units must be either 'si' or 'ip'.")

    run_id = normalized_run_id
    run_dir = (
        garden_root_path / ENERGY_RUNS_DIR / simulation_folder_name(model_display_name)
    ).resolve()
    run_dir.relative_to(garden_root_path)
    if additional_idf_path is not None and additional_idf_text is not None:
        raise ValueError("Provide either additional_idf_path or additional_idf_text, not both.")
    if additional_idf_text is not None and not additional_idf_text.strip():
        raise ValueError("additional_idf_text must not be empty.")
    additional_source = _resolve_garden_path(
        garden_root_path, additional_idf_path,
        field_name="additional_idf_path", kind="file", suffix=".idf",
    )
    native_dir = (run_dir / "openstudio").resolve()
    for field, source in (
        ("model_path", model_path), ("epw_path", Path(epw_path)),
        ("ddy_path", Path(ddy_path)), ("measures_path", measures_folder),
        ("additional_idf_path", additional_source),
    ):
        if source is not None and source.resolve().is_relative_to(native_dir):
            raise ValueError(
                f"{field} must be outside the calculation folder being replaced: {native_dir}."
            )
    run_folder = to_posix_relative(run_dir, garden_root_path)
    _ENERGY_RUN_LEDGER.prepare_folder(
        _run_index_path(garden_root_path),
        run_folder,
        recipe=ENERGY_RUN_RECIPE,
        model_target=resolved_model_target,
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    _clear_native_recipe_dir(garden_root_path, native_dir)
    sim_par_path = _write_json_input(run_dir, "simulation_parameter.json", sim_par)
    additional_idf_file, additional_idf_source = _resolve_additional_idf_input(
        garden_root=garden_root_path,
        run_dir=run_dir,
        additional_idf_path=additional_idf_path,
        additional_idf_text=additional_idf_text,
    )
    started_at = utc_now_iso()
    target = _run_target(manifest.garden_id, run_id)
    preflight = (
        _preflight_weather(epw_path, ddy_path)
        if validate_weather
        else {"status": "skipped", "issues": []}
    )
    warnings = list(preflight.get("issues", []))
    if design_day_resolution.get("status") == "failed":
        preflight = {
            **preflight,
            "status": "failed",
            "issues": list(preflight.get("issues") or [])
            + [str(design_day_resolution.get("message"))],
        }
        warnings = list(preflight["issues"])
    status = "failed" if preflight["status"] == "failed" else "running"
    record: dict[str, Any] = {
        "run_id": run_id,
        "target": target,
        "recipe": ENERGY_RUN_RECIPE,
        "status": status,
        "created_at": started_at,
        "model_target": resolved_model_target,
        "model_display_name": model_display_name,
        "model_path": to_posix_relative(model_path, garden_root_path),
        "weather_target": weather_target,
        "epw_path": epw_path,
        "ddy_path": ddy_path,
        "run_folder": run_folder,
        "outputs": (
            _recipe_outputs(
                garden_root_path=garden_root_path,
                run_dir=run_dir,
                warnings=warnings,
            )
            if status == "failed"
            else _missing_outputs()
        ),
        "units": units,
        "workers": workers,
        "reload_old": reload_old,
        "silent": silent,
        "warnings": warnings,
        "preflight": preflight,
        "design_day_resolution": design_day_resolution,
    }
    if status == "failed":
        record["completed_at"] = utc_now_iso()
    if additional_idf_file is not None:
        record["additional_idf_path"] = to_posix_relative(
            additional_idf_file, garden_root_path
        )
        record["additional_idf_source"] = additional_idf_source
    if measures_folder is not None:
        record["measures_path"] = to_posix_relative(measures_folder, garden_root_path)
    if sim_par_path is not None:
        record["sim_par_path"] = to_posix_relative(
            Path(sim_par_path), garden_root_path
        )
    if resolved_parameter_target is not None:
        record["simulation_parameter_target"] = resolved_parameter_target
    if resolved_output_request_target is not None:
        record["output_request_target"] = resolved_output_request_target
    _upsert_record(garden_root_path, record)
    return {"manifest": manifest, "record": record, "reused": False}


def _execute_annual_energy_run(
    *,
    garden_root: Path,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Execute an already registered annual run without preparing its folder."""
    manifest = GardenManifest.read(garden_root)
    run_id = str(record["run_id"])
    warnings = list(record.get("warnings") or [])
    run_dir = _run_dir_from_record(garden_root, record)
    model_path = _record_path(
        garden_root,
        record.get("model_path"),
        field_name="model_path",
    )
    epw_path = _record_path(garden_root, record.get("epw_path"), field_name="epw_path")
    sim_par_path = (
        _record_path(garden_root, record["sim_par_path"], field_name="sim_par_path")
        if record.get("sim_par_path")
        else None
    )
    additional_idf_file = (
        _record_path(
            garden_root,
            record["additional_idf_path"],
            field_name="additional_idf_path",
        )
        if record.get("additional_idf_path")
        else None
    )
    measures_folder = (
        _record_path(
            garden_root,
            record["measures_path"],
            field_name="measures_path",
            kind="directory",
        )
        if record.get("measures_path")
        else None
    )
    python_runtime_translation = None
    if _should_prepare_python_ironbug_runtime(model_path):
        try:
            model_path, python_runtime_translation = prepare_python_only_energy_model(
                model_path=model_path,
                run_dir=run_dir,
                garden_root=garden_root,
                epw_path=str(epw_path),
                sim_par_path=(
                    str(sim_par_path) if sim_par_path is not None else None
                ),
            )
            if python_runtime_translation is not None:
                python_runtime_translation["run_id"] = run_id
        except PythonIronbugRuntimeUnsupported as exc:
            warnings.append(str(exc))
            python_runtime_translation = {
                "status": "blocked",
                "run_id": run_id,
                "csharp_ironbug_console_required": False,
                "python_console_parity_gap": True,
                "error": str(exc),
                "unsupported_graphs": exc.unsupported_graphs,
            }
            record.update(
                {
                    "status": "failed",
                    "completed_at": utc_now_iso(),
                    "outputs": _recipe_outputs(
                        garden_root_path=garden_root,
                        run_dir=run_dir,
                        warnings=warnings,
                    ),
                    "warnings": warnings,
                    "python_ironbug_console_runtime": python_runtime_translation,
                }
            )
            _upsert_record(garden_root, record)
            return _energy_response(
                manifest=manifest,
                record=record,
                message=(
                    "Python-only Ironbug Console runtime translation failed; "
                    "run record was saved."
                ),
                report_status="blocked",
                warnings=warnings,
            )
        except Exception as exc:
            warnings.append(str(exc))
            python_runtime_translation = {
                "status": "error",
                "run_id": run_id,
                "csharp_ironbug_console_required": False,
                "error": str(exc),
            }
            record.update(
                {
                    "status": "failed",
                    "completed_at": utc_now_iso(),
                    "outputs": _recipe_outputs(
                        garden_root_path=garden_root,
                        run_dir=run_dir,
                        warnings=warnings,
                    ),
                    "warnings": warnings,
                    "python_ironbug_console_runtime": python_runtime_translation,
                }
            )
            _upsert_record(garden_root, record)
            return _energy_response(
                manifest=manifest,
                record=record,
                message=(
                    "Python-only Ironbug Console runtime translation errored; "
                    "run record was saved."
                ),
                warnings=warnings,
            )

    status = "completed"
    simulate_status = 1
    eui_status = 1
    try:
        simulate_status, eui_status = _run_honeybee_energy_cli(
            model_path=model_path,
            epw_path=str(epw_path),
            run_dir=run_dir,
            sim_par_path=str(sim_par_path) if sim_par_path is not None else None,
            additional_idf_file=additional_idf_file,
            measures_folder=measures_folder,
            units=str(record.get("units") or "si"),
            silent=bool(record.get("silent", True)),
        )
    except Exception as exc:  # pragma: no cover - exercised by real engines
        status = "failed"
        warnings.append(str(exc))
    else:
        if simulate_status != 0:
            status = "failed"
            warnings.append(
                f"Honeybee Energy simulation command failed with exit code {simulate_status}."
            )
        elif eui_status != 0:
            status = "failed"
            warnings.append(
                f"Honeybee Energy EUI command failed with exit code {eui_status}."
            )

    outputs = _recipe_outputs(
        garden_root_path=garden_root,
        run_dir=run_dir,
        warnings=warnings,
    )
    if status == "completed" and not _outputs_map({"outputs": outputs}).get(
        "eui", {}
    ).get("exists"):
        status = "failed"
        warnings.append("Recipe finished without an EUI output; marking run as failed.")
    record.update(
        {
            "status": status,
            "completed_at": utc_now_iso(),
            "outputs": outputs,
            "warnings": warnings,
        }
    )
    if python_runtime_translation is not None:
        record["python_ironbug_console_runtime"] = python_runtime_translation
    _upsert_record(garden_root, record)
    return _energy_response(
        manifest=manifest,
        record=record,
        message=(
            "Annual energy-use simulation completed."
            if status == "completed"
            else "Annual energy-use simulation failed; run record was saved."
        ),
        warnings=warnings,
    )


def run_energy(
    *,
    garden_root: str,
    epw_path: str | None = None,
    ddy_path: str | None = None,
    weather_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
    sim_par: dict[str, Any] | None = None,
    simulation_parameter_target: dict[str, Any] | None = None,
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
    prepared = _prepare_annual_energy_run(
        garden_root=garden_root,
        epw_path=epw_path,
        ddy_path=ddy_path,
        weather_target=weather_target,
        model_target=model_target,
        sim_par=sim_par,
        simulation_parameter_target=simulation_parameter_target,
        output_request_target=output_request_target,
        additional_idf_path=additional_idf_path,
        additional_idf_text=additional_idf_text,
        measures_path=measures_path,
        run_id=run_id,
        units=units,
        workers=workers,
        reload_old=reload_old,
        silent=silent,
        validate_weather=validate_weather,
    )
    manifest = prepared["manifest"]
    record = prepared["record"]
    if prepared["reused"]:
        if record.get("status") == "completed":
            return _completed_reload_response(
                garden_root=_garden_root(garden_root),
                manifest=manifest,
                record=record,
            )
        return _existing_run_response(
            garden_root=_garden_root(garden_root),
            manifest=manifest,
            record=record,
        )
    if record.get("status") == "failed":
        return _energy_response(
            manifest=manifest,
            record=record,
            message="Annual energy-use simulation preflight failed; run record was saved.",
            warnings=list(record.get("warnings") or []),
        )
    return run_energy_worker(garden_root=garden_root, run_id=str(record["run_id"]))


def run_energy_worker(
    *,
    garden_root: str,
    run_id: str,
) -> dict[str, Any]:
    """Execute a registered annual run from its ledger folder."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    record = _run_record_by_id(garden_root_path, str(run_id))
    if record.get("status") != "running":
        if record.get("status") == "completed":
            return _completed_reload_response(
                garden_root=garden_root_path,
                manifest=manifest,
                record=record,
            )
        return _existing_run_response(
            garden_root=garden_root_path,
            manifest=manifest,
            record=record,
        )
    try:
        return _execute_annual_energy_run(
            garden_root=garden_root_path,
            record=record,
        )
    except Exception as exc:
        failed = _mark_energy_failed(garden_root_path, str(run_id), str(exc))
        return _energy_response(
            manifest=manifest,
            record=failed,
            message="Annual energy-use worker failed; run record was saved.",
        )


def start_energy_run(
    *,
    garden_root: str,
    epw_path: str | None = None,
    ddy_path: str | None = None,
    weather_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
    sim_par: dict[str, Any] | None = None,
    simulation_parameter_target: dict[str, Any] | None = None,
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
    prepared = _prepare_annual_energy_run(
        garden_root=garden_root,
        epw_path=epw_path,
        ddy_path=ddy_path,
        weather_target=weather_target,
        model_target=model_target,
        sim_par=sim_par,
        simulation_parameter_target=simulation_parameter_target,
        output_request_target=output_request_target,
        additional_idf_path=additional_idf_path,
        additional_idf_text=additional_idf_text,
        measures_path=measures_path,
        run_id=run_id,
        units=units,
        workers=workers,
        reload_old=reload_old,
        silent=silent,
        validate_weather=validate_weather,
    )
    garden_root_path = _garden_root(garden_root)
    manifest = prepared["manifest"]
    record = prepared["record"]
    if prepared["reused"]:
        if record.get("status") == "completed":
            return _completed_reload_response(
                garden_root=garden_root_path,
                manifest=manifest,
                record=record,
            )
        return _existing_run_response(
            garden_root=garden_root_path,
            manifest=manifest,
            record=record,
        )
    if record.get("status") == "failed":
        return _energy_response(
            manifest=manifest,
            record=record,
            message="Annual energy-use simulation preflight failed; run record was saved.",
            warnings=list(record.get("warnings") or []),
        )
    try:
        _submit_energy_background(
            garden_root=str(garden_root_path),
            run_id=str(record["run_id"]),
        )
    except Exception as exc:
        failed = _mark_energy_failed(
            garden_root_path,
            str(record["run_id"]),
            str(exc),
        )
        return _energy_response(
            manifest=manifest,
            record=failed,
            message="Annual energy-use simulation could not be started; run record was saved.",
        )
    result = _energy_response(
        manifest=manifest,
        record=record,
        message="Annual energy-use simulation started; poll the energy_run target for status.",
    )
    result["summary_view"]["poll_next"] = {
        "tool": "EP_poll_simulation",
        "arguments": {
            "garden_root": str(garden_root_path),
            "run_target": record["target"],
        },
    }
    return result


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
    evidence = _energy_run_result_evidence(
        garden_root=garden_root_path,
        run_id=resolved_run_id,
        record=record,
    )
    return {
        "status": status,
        "run_id": resolved_run_id,
        "outputs": outputs,
        "python_ironbug_console_runtime": record.get(
            "python_ironbug_console_runtime"
        ),
        "result_evidence": evidence,
        "final_answer_ready": evidence["final_answer_ready"],
        "summary_view": {
            "garden_target": manifest.target(),
            "run": record,
            "run_id": resolved_run_id,
            "status": status,
            "outputs": outputs,
            "python_ironbug_console_runtime": record.get(
                "python_ironbug_console_runtime"
            ),
            "result_evidence": evidence,
            "final_answer_ready": evidence["final_answer_ready"],
            "should_start_another_run": False,
            "final_answer_guidance": evidence["final_answer_guidance"],
            "recommended_next_tools": evidence["recommended_next_tools"],
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
        "outputs": outputs,
        "files": outputs,
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
    outputs = list(record.get("outputs", []))
    output_map = _outputs_map(record)
    eui_output = output_map.get("eui")
    eui_path: Path | None = None
    if eui_output and eui_output.get("path"):
        candidate = (garden_root_path / str(eui_output["path"])).resolve()
        candidate.relative_to(garden_root_path)
        if candidate.is_file():
            eui_path = candidate
    if eui_path is None:
        existing_output_names = [
            str(output.get("name"))
            for output in outputs
            if output.get("name") and output.get("exists")
        ]
        missing_path = str(eui_output.get("path")) if eui_output else None
        details = {
            "run_id": resolved_run_id,
            "run_status": record.get("status"),
            "missing_output": "eui",
            "missing_path": missing_path,
            "available_output_names": existing_output_names,
            "recommended_next_tools": [
                "EP_list_run_outputs",
                "EP_read_errors",
            ],
        }
        message = (
            f"Energy run {resolved_run_id} has no EUI output. "
            "Read ERR diagnostics for the precise EnergyPlus blocker."
        )
        return {
            "eui": None,
            "path": None,
            "python_ironbug_console_runtime": record.get(
                "python_ironbug_console_runtime"
            ),
            "energy_blocker": {
                "status": "missing_eui_output",
                "message": message,
                **details,
            },
            "summary_view": {
                "garden_target": manifest.target(),
                "run_id": resolved_run_id,
                "run_status": record.get("status"),
                "eui": None,
                "path": None,
                "available_outputs": outputs,
                "available_output_names": existing_output_names,
                "python_ironbug_console_runtime": record.get(
                    "python_ironbug_console_runtime"
                ),
                "recommended_next_tools": details["recommended_next_tools"],
            },
            "report": make_report(status="blocked", message=message, details=details),
        }
    eui = json.loads(eui_path.read_text(encoding="utf-8"))
    output_names = [
        str(output.get("name"))
        for output in outputs
        if output.get("name") and output.get("exists")
    ]
    err_exists = _output_exists(record, "err")
    sql_exists = _output_exists(record, "sql")
    err_summary: dict[str, Any] | None = None
    if err_exists:
        err_summary = {
            key: value
            for key, value in _err_summary(garden_root=garden_root_path, record=record).items()
            if key != "text"
        }
    severe_count = int((err_summary or {}).get("severe_count") or 0)
    fatal_count = int((err_summary or {}).get("fatal_count") or 0)
    completed_with_diagnostics = bool(eui and err_exists and sql_exists)
    final_answer_ready = bool(
        completed_with_diagnostics and not severe_count and not fatal_count
    )
    recommended_next_tools = [GARDEN_VERSION_NEXT_TOOL] if final_answer_ready else [
        "EP_list_run_outputs",
        "EP_read_errors",
    ]
    if final_answer_ready:
        final_answer_guidance = (
            "EUI, SQL, and clean ERR evidence are present. Report the result; "
            "create a Garden version checkpoint if this is the final accepted "
            "scenario; do not start another Energy run unless the user asks for "
            "a new scenario."
        )
    elif completed_with_diagnostics:
        final_answer_guidance = (
            "EUI, SQL, and ERR evidence are present, but ERR diagnostics contain "
            "severe or fatal entries. Report the EUI together with the ERR status "
            "or precise blocker; do not start another Energy run unless the user "
            "explicitly asks to repair and rerun."
        )
    else:
        final_answer_guidance = (
            "EUI exists, but SQL or ERR evidence is missing. Inspect the available "
            "outputs before reporting final Energy evidence."
        )
    result_evidence = {
        "run_id": resolved_run_id,
        "run_status": record.get("status"),
        "eui_exists": True,
        "err_exists": err_exists,
        "sql_exists": sql_exists,
        "completed_with_diagnostics": completed_with_diagnostics,
        "available_output_names": output_names,
        "err_summary": err_summary,
        "severe_count": severe_count,
        "fatal_count": fatal_count,
        "final_answer_ready": final_answer_ready,
        "should_start_another_run": False,
        "final_answer_guidance": final_answer_guidance,
        "recommended_next_tools": recommended_next_tools,
    }
    return {
        "eui": eui,
        "path": to_posix_relative(eui_path, garden_root_path),
        "result_evidence": result_evidence,
        "outputs": outputs,
        "files": outputs,
        "err_exists": err_exists,
        "sql_exists": sql_exists,
        "python_ironbug_console_runtime": record.get(
            "python_ironbug_console_runtime"
        ),
        "warning_count": int((err_summary or {}).get("warning_count") or 0),
        "severe_count": severe_count,
        "fatal_count": fatal_count,
        "final_answer_ready": final_answer_ready,
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": resolved_run_id,
            "run_status": record.get("status"),
            "eui": eui,
            "path": to_posix_relative(eui_path, garden_root_path),
            "err_exists": err_exists,
            "sql_exists": sql_exists,
            "python_ironbug_console_runtime": record.get(
                "python_ironbug_console_runtime"
            ),
            "warning_count": int((err_summary or {}).get("warning_count") or 0),
            "severe_count": severe_count,
            "fatal_count": fatal_count,
            "err_summary": err_summary,
            "completed_with_diagnostics": completed_with_diagnostics,
            "available_outputs": outputs,
            "available_output_names": output_names,
            "final_answer_ready": final_answer_ready,
            "should_start_another_run": False,
            "final_answer_guidance": final_answer_guidance,
            "recommended_next_tools": recommended_next_tools,
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
    try:
        err_summary = _err_summary(
            garden_root=garden_root_path,
            record=record,
            max_chars=max_chars,
        )
    except ValueError as exc:
        message = str(exc)
        if "err output" not in message:
            raise
        output_names = [
            name
            for name, output in _outputs_map(record).items()
            if output and output.get("exists")
        ]
        energy_blocker = {
            "status": "missing_err_output",
            "message": (
                f"Energy ERR output is missing for run {resolved_run_id}. "
                "Check the run status and available outputs before retrying."
            ),
            "run_id": resolved_run_id,
            "run_status": record.get("status"),
            "available_output_names": output_names,
            "recommended_next_tools": ["EP_poll_simulation", "EP_list_run_outputs"],
        }
        return {
            "text": "",
            "path": None,
            "truncated": False,
            "warning_count": 0,
            "severe_count": 0,
            "fatal_count": 0,
            "last_severe_error": None,
            "severe_errors": [],
            "fatal_errors": [],
            "energy_blocker": energy_blocker,
            "summary_view": {
                "garden_target": manifest.target(),
                "run_id": resolved_run_id,
                "run_status": record.get("status"),
                "path": None,
                "truncated": False,
                "warning_count": 0,
                "severe_count": 0,
                "fatal_count": 0,
                "last_severe_error": None,
                "severe_errors": [],
                "fatal_errors": [],
                "available_output_names": output_names,
                "energy_blocker": energy_blocker,
                "recommended_next_tools": ["EP_poll_simulation", "EP_list_run_outputs"],
            },
            "report": make_report(
                status="blocked",
                message=energy_blocker["message"],
                details=energy_blocker,
            ),
        }
    visible_text = str(err_summary["text"])
    truncated = bool(err_summary["truncated"])
    warning_count = int(err_summary["warning_count"])
    severe_count = int(err_summary["severe_count"])
    fatal_count = int(err_summary["fatal_count"])
    last_severe_error = err_summary["last_severe_error"]
    severe_errors = list(err_summary["severe_errors"])
    fatal_errors = list(err_summary["fatal_errors"])
    repair_hints = _err_repair_hints(visible_text)
    err_path = garden_root_path / str(err_summary["path"])
    report_status = "blocked" if severe_count or fatal_count else "ok"
    message = f"Energy ERR returned for run {resolved_run_id}."
    energy_blocker: dict[str, Any] | None = None
    if report_status == "blocked":
        blocker_status = "energyplus_fatal" if fatal_count else "energyplus_severe"
        blocker_message = (
            f"EnergyPlus ERR for run {resolved_run_id} contains "
            f"{fatal_count} fatal and {severe_count} severe error(s)."
        )
        if last_severe_error:
            blocker_message = f"{blocker_message} Last severe error: {last_severe_error}"
        energy_blocker = {
            "status": blocker_status,
            "message": blocker_message,
            "run_id": resolved_run_id,
            "fatal_count": fatal_count,
            "severe_count": severe_count,
            "warning_count": warning_count,
            "last_severe_error": last_severe_error,
            "fatal_errors": fatal_errors,
            "severe_errors": severe_errors,
            "path": to_posix_relative(err_path, garden_root_path),
            "repair_hints": repair_hints,
        }
        message = blocker_message
        if repair_hints:
            energy_blocker["repair_hints"] = repair_hints
    return {
        "text": visible_text,
        "path": to_posix_relative(err_path, garden_root_path),
        "truncated": truncated,
        "warning_count": warning_count,
        "severe_count": severe_count,
        "fatal_count": fatal_count,
        "last_severe_error": last_severe_error,
        "severe_errors": severe_errors,
        "fatal_errors": fatal_errors,
        "repair_hints": repair_hints,
        "energy_blocker": energy_blocker,
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": resolved_run_id,
            "path": to_posix_relative(err_path, garden_root_path),
            "truncated": truncated,
            "warning_count": warning_count,
            "severe_count": severe_count,
            "fatal_count": fatal_count,
            "last_severe_error": last_severe_error,
            "severe_errors": severe_errors,
            "fatal_errors": fatal_errors,
            "repair_hints": repair_hints,
            "energy_blocker": energy_blocker,
        },
        "report": make_report(
            status=report_status,
            message=message,
            warnings=["ERR output was truncated."] if truncated else [],
            details=energy_blocker or {},
        ),
    }
