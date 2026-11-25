"""Annual energy-use recipe execution services."""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import os
import shutil
import subprocess
import sys
from typing import Any

from honeybee_energy.config import folders as energy_folders
from honeybee_energy.measure import Measure
from ladybug.ddy import DDY
from ladybug.epw import EPW

from ladybug_tools_mcp.contracts import make_report
from garden.background import capture_recipe_stdio, submit_worker_process
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import (
    require_garden_root,
    resolve_existing_garden_path,
    simulation_folder_name,
    to_posix_relative,
    validate_portable_file_name,
)
from garden.run_ledger import RunManager, serialized_run_start
from garden.honeybee_core.model_io import resolve_model_target
from garden.ironbug.runtime import (
    resolve_ironbug_console_exe,
    resolve_ironbug_dir,
    resolve_openstudio_csharp_dir,
)
from garden.run_energy._schemas import normalize_simulation_units
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
OUTPUT_NAMES = (
    "eio",
    "err",
    "eui",
    "html",
    "osw",
    "rdd",
    "result-report",
    "sql",
    "visual-report",
    "zsz",
)
GARDEN_VERSION_NEXT_TOOL = "GD_Manage_Versions"


def _recipe_cli_path(path_value: str | None = None) -> str:
    """Ensure recipe subprocesses can find CLIs installed in the active venv."""
    scripts_dir = Path(sys.executable).absolute().parent
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
    return str(Path(sys.executable).absolute().parent / executable_name)


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
        worker_module="garden.run_energy.annual:run_energy_worker",
        request={"garden_root": str(garden_root), "run_id": run_id},
        cwd=garden_root,
        environment=env,
    )


_garden_root = require_garden_root
_capture_recipe_stdio = capture_recipe_stdio

ENERGY_RUN_PUBLIC_FIELDS = (
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
    "measures",
    "measures_only",
    "input_file_path",
    "workflow_path",
    "source_file_path",
    "run_input_path",
    "expand_objects",
    "worker_pid",
    "stage_statuses",
)

_ENERGY_RUNS = RunManager(
    domain=ENERGY_RUN_DOMAIN,
    target_type=ENERGY_RUN_TARGET_TYPE,
    runs_dir=ENERGY_RUNS_DIR,
    default_recipe=ENERGY_RUN_RECIPE,
    allowed_recipes=ENERGY_RUN_RECIPES,
    run_id_prefix="energy",
    use_uuid_fallback=True,
    target_run_id_required=False,
    not_found_label="Energy",
    public_fields=ENERGY_RUN_PUBLIC_FIELDS,
)
_ENERGY_RUN_LEDGER = _ENERGY_RUNS.ledger


def _run_index_path(garden_root: Path) -> Path:
    return _ENERGY_RUNS.index_path(garden_root)


def _read_index(garden_root: Path) -> list[dict[str, Any]]:
    return _ENERGY_RUNS.list(garden_root)


def _run_target(
    garden_id: str,
    run_id: str,
    *,
    recipe: str = ENERGY_RUN_RECIPE,
) -> dict[str, str]:
    return _ENERGY_RUNS.make_target(garden_id, run_id, recipe=recipe)


def _normalize_run_id(value: str | None) -> str:
    return _ENERGY_RUNS.normalize_run_id(value)


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
    return resolve_existing_garden_path(
        garden_root,
        value,
        kind=kind,
        suffix=suffix,
        label=field_name,
    )


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
            "for a registered Garden weather file, call LB_Manage_Weather with "
            "action='search' and require_ddy=true and pass matches[i].target."
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


_OUTPUT_FALLBACK_REL_PATHS: dict[str, tuple[str, ...]] = {
    "eio": ("openstudio/run/eplusout.eio", "run/eplusout.eio", "eplusout.eio"),
    "err": ("openstudio/run/eplusout.err", "run/eplusout.err", "eplusout.err"),
    "eui": ("openstudio/eui.json", "eui.json"),
    "html": ("openstudio/run/eplustbl.htm", "run/eplustbl.htm", "eplustbl.htm"),
    "osw": ("openstudio/out.osw", "openstudio/workflow.osw", "out.osw", "workflow.osw"),
    "rdd": ("openstudio/run/eplusout.rdd", "run/eplusout.rdd", "eplusout.rdd"),
    "result-report": ("openstudio/reports/openstudio_results_report.html",),
    "sql": ("openstudio/run/eplusout.sql", "run/eplusout.sql", "eplusout.sql"),
    "visual-report": ("openstudio/reports/view_data_report.html",),
    "zsz": ("openstudio/run/epluszsz.csv", "run/epluszsz.csv", "epluszsz.csv"),
}


def _run_dir_from_record(garden_root: Path, record: dict[str, Any]) -> Path:
    run_folder = record.get("run_folder") or record.get("run_dir")
    if isinstance(run_folder, str) and run_folder:
        run_dir = (garden_root / run_folder).resolve()
        run_dir.relative_to(garden_root)
        return run_dir

    run_id = str(record.get("run_id") or "").strip()
    candidates: list[Path] = []
    if run_id:
        candidates.append((garden_root / ENERGY_RUNS_DIR / run_id).resolve())
    model_display_name = record.get("model_display_name")
    if isinstance(model_display_name, str) and model_display_name.strip():
        candidates.append(
            (
                garden_root / ENERGY_RUNS_DIR / simulation_folder_name(model_display_name)
            ).resolve()
        )
    for candidate in candidates:
        candidate.relative_to(garden_root)
        if candidate.exists():
            return candidate
    raise ValueError(f"Energy run has no valid run folder: {record.get('run_id')}")


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
    _ENERGY_RUNS.upsert(garden_root, record)


def _run_record_by_id(garden_root: Path, run_id: str) -> dict[str, Any]:
    return _ENERGY_RUNS.require(garden_root, run_id)


def _run_id_from_target_or_value(
    *,
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> str:
    return _ENERGY_RUNS.resolve_run_id(run_target, run_id)


def _outputs_map(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): item for item in record.get("outputs", [])}


def _absolute_output_path(
    garden_root: Path, record: dict[str, Any], output_name: str
) -> Path:
    output = _outputs_map(record).get(output_name)
    if output and output.get("path"):
        path = (garden_root / str(output["path"])).resolve()
        path.relative_to(garden_root)
        if path.is_file():
            return path
    rel_candidates = _OUTPUT_FALLBACK_REL_PATHS.get(output_name, ())
    if rel_candidates:
        try:
            run_dir = _run_dir_from_record(garden_root, record)
        except ValueError:
            run_dir = None
        if run_dir is not None:
            for rel in rel_candidates:
                candidate = (run_dir / rel).resolve()
                try:
                    candidate.relative_to(garden_root)
                except ValueError:
                    continue
                if candidate.is_file():
                    return candidate
    if not output or not output.get("path"):
        raise ValueError(f"Energy run has no {output_name} output.")
    raise ValueError(f"Energy run {output_name} output file is missing.")


def _output_exists(record: dict[str, Any], output_name: str) -> bool:
    output = _outputs_map(record).get(output_name)
    return bool(output and output.get("exists") and output.get("path"))


def _err_text_stats(err_path: Path) -> dict[str, Any]:
    text = err_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    lower_lines = [line.lower() for line in lines]
    normalized_lines = [" ".join(line.split()) for line in lower_lines]
    warning_count = sum("** warning **" in line for line in normalized_lines)
    severe_count = sum("** severe" in line for line in normalized_lines)
    fatal_count = sum("** fatal" in line for line in normalized_lines)
    fatal_errors = [
        lines[index].strip()
        for index, line in enumerate(normalized_lines)
        if "** fatal" in line
    ]
    lower_text = text.lower()
    return {
        "warning_count": warning_count,
        "severe_count": severe_count,
        "fatal_count": fatal_count,
        "fatal_errors": fatal_errors,
        "completed_successfully": "energyplus completed successfully" in lower_text,
        "terminated": "energyplus terminated" in lower_text,
    }


def _classify_osw_measure_type(
    measure_dir_name: str,
    result: dict[str, Any],
    configured_types: dict[str, str],
) -> str | None:
    explicit = result.get("measure_type")
    if isinstance(explicit, str) and explicit:
        return explicit
    if measure_dir_name in configured_types:
        return configured_types[measure_dir_name]
    if measure_dir_name in {
        "from_honeybee_model",
        "from_honeybee_simulation_parameter",
        "honeybee_efficiency_standard",
    }:
        return "ModelMeasure"
    if measure_dir_name == "inject_idf":
        return "EnergyPlusMeasure"
    if measure_dir_name in {"openstudio_results", "view_data"}:
        return "ReportingMeasure"
    return None


def _derive_stage_statuses(
    *,
    garden_root: Path,
    record: dict[str, Any],
    run_dir: Path | None = None,
    simulate_status: int | None = None,
    eui_status: int | None = None,
) -> dict[str, dict[str, Any]]:
    """Derive explicit osm_load, forward_translator, energyplus, and reporting_measures statuses."""
    if run_dir is None:
        try:
            run_dir = _run_dir_from_record(garden_root, record)
        except ValueError:
            run_dir = None

    recipe = str(record.get("recipe") or ENERGY_RUN_RECIPE)
    run_status = str(record.get("status") or "unknown")
    measures_only = bool(record.get("measures_only", False))
    preflight_failed = (record.get("preflight") or {}).get("status") == "failed"

    if recipe == "energyplus_idf":
        sim_dir = run_dir
        osw_dir = None
    elif recipe == "openstudio_osm":
        sim_dir = run_dir
        osw_dir = run_dir.parent if run_dir is not None else None
    else:
        osw_dir = (run_dir / "openstudio") if run_dir is not None else None
        sim_dir = (osw_dir / "run") if osw_dir is not None else None

    in_osm = False
    if osw_dir is not None:
        in_osm = (osw_dir / "in.osm").is_file() or (
            sim_dir is not None and (sim_dir / "in.osm").is_file()
        )
    in_idf = False
    if sim_dir is not None:
        in_idf = (sim_dir / "in.idf").is_file() or (sim_dir / "pre-preprocess.idf").is_file()

    err_path = (sim_dir / "eplusout.err") if sim_dir is not None else None
    if (err_path is None or not err_path.is_file()) and _output_exists(record, "err"):
        try:
            err_path = _absolute_output_path(garden_root, record, "err")
        except ValueError:
            err_path = None
    sql_path = (sim_dir / "eplusout.sql") if sim_dir is not None else None
    if (sql_path is None or not sql_path.is_file()) and _output_exists(record, "sql"):
        try:
            sql_path = _absolute_output_path(garden_root, record, "sql")
        except ValueError:
            sql_path = None
    eui_path = (osw_dir / "eui.json") if osw_dir is not None else None
    if (eui_path is None or not eui_path.is_file()) and _output_exists(record, "eui"):
        try:
            eui_path = _absolute_output_path(garden_root, record, "eui")
        except ValueError:
            eui_path = None

    err_exists = bool(err_path is not None and err_path.is_file())
    sql_exists = bool(sql_path is not None and sql_path.is_file())
    eui_exists = bool(eui_path is not None and eui_path.is_file())
    report_html_exists = bool(
        osw_dir is not None
        and (
            (osw_dir / "reports" / "openstudio_results_report.html").is_file()
            or (osw_dir / "reports" / "view_data_report.html").is_file()
        )
    )

    configured_types: dict[str, str] = {}
    for item in list(record.get("measures") or []):
        if isinstance(item, dict) and item.get("type"):
            m_type = str(item["type"])
            if item.get("identifier"):
                configured_types[str(item["identifier"])] = m_type
            if item.get("folder"):
                configured_types[Path(str(item["folder"])).name] = m_type

    osw_data: dict[str, Any] = {}
    if osw_dir is not None:
        for candidate_name in ("out.osw", "workflow.osw"):
            candidate = osw_dir / candidate_name
            if candidate.is_file():
                try:
                    loaded = json.loads(candidate.read_text(encoding="utf-8", errors="replace"))
                    if isinstance(loaded, dict):
                        osw_data = loaded
                        break
                except (OSError, json.JSONDecodeError, TypeError):
                    pass
    if not osw_data and _output_exists(record, "osw"):
        try:
            loaded = json.loads(
                _absolute_output_path(garden_root, record, "osw").read_text(
                    encoding="utf-8", errors="replace"
                )
            )
            if isinstance(loaded, dict):
                osw_data = loaded
        except (OSError, ValueError, json.JSONDecodeError, TypeError):
            pass

    osw_completed_status = osw_data.get("completed_status")
    model_steps: list[dict[str, Any]] = []
    ep_measure_steps: list[dict[str, Any]] = []
    reporting_steps: list[dict[str, Any]] = []
    unknown_failed_steps: list[dict[str, Any]] = []
    for step in list(osw_data.get("steps") or []):
        if not isinstance(step, dict):
            continue
        measure_dir = str(step.get("measure_dir_name") or "")
        res = step.get("result") if isinstance(step.get("result"), dict) else {}
        step_info = {
            "measure_dir_name": measure_dir,
            "step_result": res.get("step_result"),
            "step_errors": list(res.get("step_errors") or []),
            "step_warnings": list(res.get("step_warnings") or []),
        }
        m_type = _classify_osw_measure_type(measure_dir, res, configured_types)
        if m_type == "ModelMeasure":
            model_steps.append(step_info)
        elif m_type == "EnergyPlusMeasure":
            ep_measure_steps.append(step_info)
        elif m_type == "ReportingMeasure":
            reporting_steps.append(step_info)
        elif step_info["step_result"] == "Fail" or step_info["step_errors"]:
            unknown_failed_steps.append(step_info)

    err_stats = _err_text_stats(err_path) if err_exists and err_path is not None else None
    ep_clean_from_err = bool(
        err_stats is not None
        and err_stats["fatal_count"] == 0
        and (
            err_stats["completed_successfully"]
            or (sql_exists and not err_stats["terminated"])
        )
    )

    if unknown_failed_steps:
        if ep_clean_from_err or sql_exists:
            reporting_steps.extend(unknown_failed_steps)
        elif in_idf:
            ep_measure_steps.extend(unknown_failed_steps)
        else:
            model_steps.extend(unknown_failed_steps)

    # 1. osm_load stage
    failed_model_steps = [
        s for s in model_steps if s["step_result"] == "Fail" or s["step_errors"]
    ]
    if recipe == "energyplus_idf":
        osm_stage: dict[str, Any] = {"status": "skipped", "detail": "Direct IDF simulation."}
    elif preflight_failed:
        osm_stage = {"status": "not_started", "detail": "Preflight checks failed."}
    elif failed_model_steps:
        osm_stage = {
            "status": "failed",
            "failed_measures": [s["measure_dir_name"] for s in failed_model_steps],
            "errors": [err for s in failed_model_steps for err in s["step_errors"]][:5],
        }
    elif (
        in_osm
        or in_idf
        or sql_exists
        or err_exists
        or (model_steps and all(s["step_result"] == "Success" for s in model_steps))
        or (run_status == "completed" and eui_exists)
    ):
        osm_stage = {"status": "completed"}
    elif run_status in {"queued", "running"}:
        osm_stage = {
            "status": "running" if (osw_dir is not None and osw_dir.exists()) else "not_started"
        }
    else:
        osm_stage = {
            "status": "failed",
            "detail": "Model translation / OSM load failed before generating in.osm.",
        }

    # 2. forward_translator stage
    failed_ep_steps = [
        s for s in ep_measure_steps if s["step_result"] == "Fail" or s["step_errors"]
    ]
    if recipe == "energyplus_idf" or measures_only:
        ft_stage: dict[str, Any] = {
            "status": "skipped",
            "detail": "Direct IDF simulation." if recipe == "energyplus_idf" else "Skipped because measures_only=True.",
        }
    elif osm_stage["status"] in {"failed", "not_started"}:
        ft_stage = {"status": "not_started"}
    elif failed_ep_steps:
        ft_stage = {
            "status": "failed",
            "failed_measures": [s["measure_dir_name"] for s in failed_ep_steps],
            "errors": [err for s in failed_ep_steps for err in s["step_errors"]][:5],
        }
    elif in_idf or sql_exists or err_exists or (run_status == "completed" and eui_exists):
        ft_stage = {"status": "completed"}
    elif run_status in {"queued", "running"}:
        ft_stage = {
            "status": "running" if osm_stage["status"] == "completed" else "not_started"
        }
    else:
        ft_stage = {
            "status": "failed",
            "detail": "OpenStudio ForwardTranslator failed before producing in.idf.",
        }

    # 3. energyplus stage
    if measures_only:
        ep_stage: dict[str, Any] = {
            "status": "skipped",
            "detail": "Skipped because measures_only=True.",
        }
    elif ft_stage["status"] in {"failed", "not_started"}:
        ep_stage = {"status": "not_started"}
    elif err_stats is not None:
        if ep_clean_from_err:
            ep_stage = {
                "status": "completed",
                "fatal_count": err_stats["fatal_count"],
                "severe_count": err_stats["severe_count"],
                "warning_count": err_stats["warning_count"],
                "sql_exists": sql_exists,
            }
        else:
            ep_stage = {
                "status": "failed",
                "fatal_count": err_stats["fatal_count"],
                "severe_count": err_stats["severe_count"],
                "warning_count": err_stats["warning_count"],
                "fatal_errors": err_stats["fatal_errors"][:5],
                "sql_exists": sql_exists,
            }
    elif sql_exists or (run_status == "completed" and eui_exists):
        ep_stage = {"status": "completed", "sql_exists": sql_exists}
    elif run_status in {"queued", "running"}:
        ep_stage = {"status": "running" if in_idf else "not_started"}
    else:
        ep_stage = {
            "status": "failed",
            "detail": "EnergyPlus did not produce eplusout.err or eplusout.sql.",
        }

    # 4. reporting_measures stage
    failed_reporting_steps = [
        s for s in reporting_steps if s["step_result"] == "Fail" or s["step_errors"]
    ]
    if recipe == "energyplus_idf" or (measures_only and not reporting_steps):
        rep_stage: dict[str, Any] = {
            "status": "skipped",
            "detail": "Direct IDF simulation." if recipe == "energyplus_idf" else "Skipped because measures_only=True.",
        }
    elif failed_reporting_steps:
        rep_stage = {
            "status": "failed",
            "failed_measures": [s["measure_dir_name"] for s in failed_reporting_steps],
            "errors": [err for s in failed_reporting_steps for err in s["step_errors"]][:5],
        }
    elif not measures_only and ep_stage["status"] in {"failed", "not_started"}:
        rep_stage = {"status": "not_started"}
    elif reporting_steps and all(
        s["step_result"] in {"Success", "Skip"} for s in reporting_steps
    ):
        if (eui_status is not None and eui_status != 0) or (
            not measures_only and ep_stage["status"] == "completed" and not eui_exists
        ):
            rep_stage = {
                "status": "failed",
                "detail": "Reporting measures succeeded, but EUI output extraction failed.",
            }
        else:
            rep_stage = {
                "status": "completed",
                "measures": [s["measure_dir_name"] for s in reporting_steps],
            }
    elif ep_stage["status"] == "completed":
        if osw_completed_status == "Fail":
            rep_stage = {
                "status": "failed",
                "detail": "OpenStudio reporting measures failed after EnergyPlus completed.",
            }
        elif eui_status is not None and eui_status != 0:
            rep_stage = {
                "status": "failed",
                "detail": f"EUI extraction failed with exit code {eui_status} after EnergyPlus completed.",
            }
        elif simulate_status is not None and simulate_status != 0:
            rep_stage = {
                "status": "failed",
                "detail": "OpenStudio workflow failed after EnergyPlus completed.",
            }
        elif run_status == "failed":
            rep_stage = {
                "status": "failed",
                "detail": "Post-simulation reporting failed after EnergyPlus completed.",
            }
        elif report_html_exists or eui_exists or run_status == "completed":
            rep_stage = {"status": "completed"}
        elif run_status in {"queued", "running"}:
            rep_stage = {"status": "running"}
        else:
            rep_stage = {"status": "not_started"}
    elif run_status in {"queued", "running"}:
        rep_stage = {
            "status": (
                "running"
                if (measures_only and osm_stage["status"] == "completed")
                else "not_started"
            )
        }
    else:
        rep_stage = {"status": "not_started"}

    return {
        "osm_load": osm_stage,
        "forward_translator": ft_stage,
        "energyplus": ep_stage,
        "reporting_measures": rep_stage,
    }


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
                    "UFactorTimesAreaValue and MaximumWaterFlowRate via "
                    "IB_Upsert_Components, then re-apply DetailedHVAC before rerunning."
                ),
                "recommended_tool": "IB_Upsert_Components",
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
    stage_statuses = (
        dict(record["stage_statuses"])
        if status in {"completed", "failed", "cancelled"}
        and isinstance(record.get("stage_statuses"), dict)
        else _derive_stage_statuses(garden_root=garden_root, record=record)
    )
    ep_succeeded = stage_statuses.get("energyplus", {}).get("status") == "completed"
    rep_failed = stage_statuses.get("reporting_measures", {}).get("status") == "failed"
    severe_count = int((err_summary or {}).get("severe_count") or 0)
    fatal_count = int((err_summary or {}).get("fatal_count") or 0)
    completed_with_diagnostics = bool(
        (status == "completed" or ep_succeeded) and eui_exists and err_exists and sql_exists
    )
    final_answer_ready = bool(
        status == "completed"
        and completed_with_diagnostics
        and not severe_count
        and not fatal_count
    )
    if status in {"queued", "running"}:
        recommended_next_tools = ["GD_Poll_Run"]
        final_answer_guidance = (
            "Energy simulation is currently queued or running; poll this run_target with GD_Poll_Run."
        )
    elif final_answer_ready:
        recommended_next_tools = ["EP_Summarize_Results", GARDEN_VERSION_NEXT_TOOL]
        final_answer_guidance = (
            "Energy simulation completed with EUI, SQL, and clean ERR outputs available via EP_Summarize_Results."
        )
    elif ep_succeeded and rep_failed and eui_exists and err_exists and sql_exists:
        recommended_next_tools = ["EP_Summarize_Results", "EP_Read_Errors"]
        final_answer_guidance = (
            "EnergyPlus simulation succeeded with EUI, SQL, and ERR outputs, while "
            "OpenStudio reporting_measures failed; read results via EP_Summarize_Results."
        )
    elif completed_with_diagnostics:
        recommended_next_tools = ["EP_Summarize_Results", "EP_Read_Errors"]
        final_answer_guidance = (
            "Energy simulation completed with EUI and SQL outputs, and ERR diagnostics contain severe or fatal entries."
        )
    elif status == "completed":
        recommended_next_tools = ["GD_Poll_Run", "EP_Read_Errors"]
        final_answer_guidance = (
            "Energy simulation completed, though some EUI, SQL, or ERR outputs are absent; inspect outputs and diagnostics."
        )
    else:
        recommended_next_tools = ["GD_Poll_Run", "EP_Read_Errors"]
        final_answer_guidance = (
            "Energy simulation did not complete successfully; inspect outputs and ERR diagnostics."
        )
    return {
        "run_id": run_id,
        "run_status": status,
        "energyplus_succeeded": ep_succeeded,
        "stage_statuses": stage_statuses,
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
    return _ENERGY_RUNS.public_run(record)


def _completed_reload_response(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    record: dict[str, Any],
) -> dict[str, Any]:
    run_id = str(record["run_id"])
    target = record.get("target") or _run_target(manifest.garden_id, run_id)
    poll_arguments = {"garden_root": str(garden_root), "run_target": target}
    evidence = _energy_run_result_evidence(
        garden_root=garden_root,
        run_id=run_id,
        record=record,
    )
    stage_statuses = evidence["stage_statuses"]
    return {
        "target": target,
        "energy_run_target": target,
        "run_target": target,
        "stage_statuses": stage_statuses,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "run_id": run_id,
            "status": "completed",
            "recipe": record.get("recipe", ENERGY_RUN_RECIPE),
            "run_folder": record.get("run_folder"),
            "outputs": _outputs_map(record),
            "stage_statuses": stage_statuses,
            "preflight": record.get("preflight"),
            "simulation_parameter_target": record.get("simulation_parameter_target"),
            "design_day_resolution": record.get("design_day_resolution"),
            "reloaded": True,
            "result_evidence": evidence,
            "poll_next": {
                "tool": "GD_Poll_Run",
                "arguments": poll_arguments,
            },
        },
        "result_evidence": evidence,
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
    stage_statuses = evidence["stage_statuses"]
    poll_arguments = {"garden_root": str(garden_root), "run_target": target}
    return {
        "target": target,
        "energy_run_target": target,
        "run_target": target,
        "status": status,
        "run_id": run_id,
        "stage_statuses": stage_statuses,
        "result_evidence": evidence,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "run_id": run_id,
            "status": status,
            "recipe": record.get("recipe", ENERGY_RUN_RECIPE),
            "run_folder": record.get("run_folder"),
            "outputs": _outputs_map(record),
            "stage_statuses": stage_statuses,
            "preflight": record.get("preflight"),
            "simulation_parameter_target": record.get("simulation_parameter_target"),
            "design_day_resolution": record.get("design_day_resolution"),
            "result_evidence": evidence,
            "poll_next": {
                "tool": "GD_Poll_Run",
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


def _resolve_measure_path(
    garden_root: Path,
    folder: str,
    *,
    require_measure_files: bool = True,
) -> Path:
    raw = str(folder or "").strip()
    if not raw:
        raise ValueError("Measure folder path cannot be empty.")
    candidate = Path(raw).expanduser()
    resolved = candidate.resolve() if candidate.is_absolute() else (garden_root / candidate).resolve()
    in_garden = False
    try:
        resolved.relative_to(garden_root)
        in_garden = True
    except ValueError:
        in_garden = False

    lbt_measures_root = (
        Path(energy_folders.lbt_measures_path).resolve()
        if getattr(energy_folders, "lbt_measures_path", None)
        else None
    )
    if not in_garden:
        if lbt_measures_root is not None and not candidate.is_absolute() and not resolved.exists():
            builtin = (lbt_measures_root / candidate).resolve()
            if builtin.exists():
                resolved = builtin
        in_lbt = False
        if lbt_measures_root is not None:
            try:
                resolved.relative_to(lbt_measures_root)
                in_lbt = True
            except ValueError:
                in_lbt = False
        if not in_lbt:
            raise ValueError(
                f"Measure folder must stay inside the Garden or LBT measures folder: {folder}"
            )
    if not resolved.is_dir():
        raise ValueError(f"Measure folder was not found: {folder}")
    if require_measure_files:
        if not (resolved / "measure.xml").is_file() or not (resolved / "measure.rb").is_file():
            raise ValueError(
                f"Measure folder must contain measure.xml and measure.rb: {folder}"
            )
    return resolved


def _measure_metadata(measure: Measure, *, include_validation: bool = False) -> dict[str, Any]:
    args_info: list[dict[str, Any]] = []
    missing_required: list[str] = []
    for arg in measure.arguments:
        is_valid = arg.validate(raise_exception=False)
        if not is_valid:
            missing_required.append(arg.identifier)
        args_info.append(
            {
                "identifier": arg.identifier,
                "display_name": arg.display_name,
                "type": arg.type_text,
                "required": bool(arg.required),
                "default_value": arg.default_value,
                "value": arg.value,
                "valid_choices": list(arg.valid_choices) if arg.valid_choices is not None else None,
                "description": arg.description,
                "model_dependent": bool(arg.model_dependent),
            }
        )
    payload: dict[str, Any] = {
        "identifier": measure.identifier,
        "display_name": measure.display_name,
        "description": measure.description,
        "type": measure.type,
        "folder": measure.folder,
        "arguments": args_info,
    }
    if include_validation:
        payload["valid"] = len(missing_required) == 0
        payload["missing_required_arguments"] = missing_required
    return payload


def load_and_configure_measures(
    garden_root: Path,
    measures: list[dict[str, Any] | str] | tuple[dict[str, Any] | str, ...] | None,
    *,
    validate_required: bool = True,
) -> tuple[list[Measure], list[dict[str, Any]]]:
    """Load, configure, and validate ordered OpenStudio Measure definitions."""
    if measures is None:
        return [], []
    if not isinstance(measures, (list, tuple)):
        raise ValueError("measures must be a list of {folder, arguments} objects or folder strings.")
    allowed_keys = {"folder", "arguments", "path", "measure_dir_name"}
    loaded: list[Measure] = []
    specs: list[dict[str, Any]] = []
    for index, item in enumerate(measures):
        if isinstance(item, str):
            folder_value = item
            arguments: dict[str, Any] = {}
        elif isinstance(item, dict):
            unknown_keys = sorted(set(item) - allowed_keys)
            if unknown_keys:
                raise ValueError(
                    f"measures[{index}] contains unsupported field(s): {', '.join(unknown_keys)}."
                )
            folder_value = str(
                item.get("folder") or item.get("path") or item.get("measure_dir_name") or ""
            ).strip()
            if not folder_value:
                raise ValueError(f"measures[{index}] requires 'folder'.")
            raw_args = item.get("arguments")
            if raw_args is None:
                arguments = {}
            elif isinstance(raw_args, dict):
                arguments = dict(raw_args)
            else:
                raise ValueError(f"measures[{index}].arguments must be a dictionary.")
        else:
            raise ValueError(
                f"measures[{index}] must be a {{folder, arguments}} object or folder string."
            )

        resolved_folder = _resolve_measure_path(
            garden_root, folder_value, require_measure_files=True
        )
        try:
            measure = Measure(str(resolved_folder))
        except Exception as exc:
            raise ValueError(f"Failed to load OpenStudio measure {folder_value!r}: {exc}") from exc

        args_by_id = {arg.identifier: arg for arg in measure.arguments}
        unknown_args = sorted(set(arguments) - set(args_by_id))
        if unknown_args:
            allowed_args = ", ".join(sorted(args_by_id)) or "(none)"
            raise ValueError(
                f"Measure {measure.identifier!r} does not define argument(s): "
                f"{', '.join(unknown_args)}. Allowed: {allowed_args}."
            )
        for arg_name, arg_value in arguments.items():
            try:
                args_by_id[arg_name].value = arg_value
            except (TypeError, ValueError, AssertionError) as exc:
                raise ValueError(
                    f"Invalid value for measure {measure.identifier!r} argument {arg_name!r}: {exc}"
                ) from exc
        if validate_required:
            try:
                measure.validate(raise_exception=True)
            except Exception as exc:
                raise ValueError(
                    f"Measure {measure.identifier!r} failed validation: {exc}"
                ) from exc
        loaded.append(measure)
        specs.append(
            {
                "folder": str(resolved_folder),
                "identifier": measure.identifier,
                "display_name": measure.display_name,
                "type": measure.type,
                "arguments": {
                    arg.identifier: arg.value
                    for arg in measure.arguments
                    if arg.value is not None
                },
            }
        )
    return loaded, specs


def inspect_openstudio_measures(
    *,
    garden_root: str,
    measure_folder: str | None = None,
    measures_path: str | None = None,
    measures: list[dict[str, Any] | str] | None = None,
) -> dict[str, Any]:
    """Inspect OpenStudio measure metadata and typed arguments using honeybee_energy.measure.Measure."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    inspected: list[dict[str, Any]] = []
    scanned_roots: list[str] = []

    if measures is not None:
        loaded, _ = load_and_configure_measures(root, measures, validate_required=False)
        for measure in loaded:
            inspected.append(_measure_metadata(measure, include_validation=True))
    else:
        target_raw = measure_folder or measures_path
        if target_raw is not None:
            target_dir = _resolve_measure_path(root, target_raw, require_measure_files=False)
            scanned_roots.append(str(target_dir))
            if (target_dir / "measure.xml").is_file() and (target_dir / "measure.rb").is_file():
                inspected.append(_measure_metadata(Measure(str(target_dir)), include_validation=True))
            else:
                for child in sorted(target_dir.iterdir()):
                    if child.is_dir() and (child / "measure.xml").is_file() and (child / "measure.rb").is_file():
                        inspected.append(_measure_metadata(Measure(str(child)), include_validation=True))
        else:
            candidates: list[Path] = []
            garden_measures = root / "measures"
            if garden_measures.is_dir():
                candidates.append(garden_measures)
            lbt_root = getattr(energy_folders, "lbt_measures_path", None)
            if lbt_root and Path(lbt_root).is_dir():
                candidates.append(Path(lbt_root))
            for base_dir in candidates:
                scanned_roots.append(str(base_dir))
                for child in sorted(base_dir.iterdir()):
                    if child.is_dir() and (child / "measure.xml").is_file() and (child / "measure.rb").is_file():
                        inspected.append(_measure_metadata(Measure(str(child)), include_validation=True))

    return {
        "measures": inspected,
        "summary_view": {
            "garden_target": manifest.target(),
            "measure_count": len(inspected),
            "scanned_roots": scanned_roots,
            "measures": [
                {
                    "identifier": item["identifier"],
                    "display_name": item["display_name"],
                    "type": item["type"],
                    "folder": item["folder"],
                    "argument_count": len(item["arguments"]),
                    "valid": item.get("valid", True),
                    "missing_required_arguments": item.get("missing_required_arguments", []),
                }
                for item in inspected
            ],
        },
        "report": make_report(
            status="ok",
            message=f"Inspected {len(inspected)} OpenStudio measure(s).",
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
    osw_path = recipe_dir / "out.osw"
    if not osw_path.is_file():
        osw_path = recipe_dir / "workflow.osw"
    direct_outputs = {
        "eio": recipe_dir / "run" / "eplusout.eio",
        "err": recipe_dir / "run" / "eplusout.err",
        "eui": recipe_dir / "eui.json",
        "html": recipe_dir / "run" / "eplustbl.htm",
        "osw": osw_path,
        "rdd": recipe_dir / "run" / "eplusout.rdd",
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
    measures_spec_path: Path | None,
    measures_only: bool,
    units: str,
    silent: bool,
) -> tuple[int, int]:
    recipe_dir = run_dir / "openstudio"
    recipe_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "garden.run_energy.simulate_runner",
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
    if measures_spec_path is not None:
        command.extend(["--measures-spec-json", str(measures_spec_path)])
    if measures_only:
        command.append("--measures-only")
    if additional_idf_file is not None:
        command.extend(["--additional-idf", str(additional_idf_file)])
    if silent:
        command.append("--log-file")
        command.append("-")

    with _recipe_cli_environment(), _capture_recipe_stdio(run_dir):
        env = os.environ.copy()
        extra_paths: list[str] = []
        ib_dir = resolve_ironbug_dir()
        os_cs_dir = resolve_openstudio_csharp_dir(ib_dir)
        if os_cs_dir:
            extra_paths.append(str(os_cs_dir))
        if ib_dir:
            extra_paths.append(str(ib_dir))
        base_path = _recipe_cli_path(env.get("PATH"))
        env["PATH"] = os.pathsep.join([*extra_paths, base_path]) if extra_paths else base_path
        _ensure_windows_install_env(env)
        simulate = subprocess.run(
            command,
            cwd=str(run_dir),
            env=env,
            check=False,
        )
        if measures_only:
            return int(simulate.returncode), 0
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
                cwd=str(run_dir),
                env=env,
                check=False,
            )
            eui_status = int(eui.returncode)
        return int(simulate.returncode), eui_status


def _missing_outputs() -> list[dict[str, Any]]:
    return [{"name": name, "path": None, "exists": False} for name in OUTPUT_NAMES]


def _requires_external_ironbug_console(model_path: Path) -> bool:
    """Return True when a Honeybee model references Ironbug DetailedHVAC."""
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
    stage_statuses = record.get("stage_statuses")
    summary_view: dict[str, Any] = {
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
    }
    if stage_statuses is not None:
        summary_view["stage_statuses"] = stage_statuses
    if record.get("worker_pid") is not None:
        summary_view["worker_pid"] = record["worker_pid"]
    result: dict[str, Any] = {
        "target": target,
        "energy_run_target": target,
        "run_target": target,
        "status": status,
        "run_id": record.get("run_id"),
        "summary_view": summary_view,
        "report": make_report(
            status=report_status or ("ok" if status in {"running", "completed"} else "error"),
            message=message,
            warnings=warnings or list(record.get("warnings") or []),
        ),
    }
    if stage_statuses is not None:
        result["stage_statuses"] = stage_statuses
    if record.get("worker_pid") is not None:
        result["worker_pid"] = record["worker_pid"]
    return result


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
    run_dir: Path | None = None
    try:
        run_dir = _run_dir_from_record(garden_root, record)
        record["outputs"] = _recipe_outputs(
            garden_root_path=garden_root,
            run_dir=run_dir,
            warnings=warnings,
        )
    except (OSError, ValueError):
        record["outputs"] = _missing_outputs()
    record["stage_statuses"] = _derive_stage_statuses(
        garden_root=garden_root,
        record=record,
        run_dir=run_dir,
    )
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
    measures: list[dict[str, Any] | str] | None = None,
    measures_only: bool = False,
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
    existing = _ENERGY_RUNS.get(garden_root_path, normalized_run_id)
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
    loaded_measures, normalized_measures = load_and_configure_measures(
        garden_root_path,
        measures,
        validate_required=True,
    )
    units = normalize_simulation_units(units)

    run_id = normalized_run_id
    validate_portable_file_name(run_id, label="Run folder name")
    run_dir = (garden_root_path / ENERGY_RUNS_DIR / run_id).resolve()
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
        *((f"measures[{idx}].folder", Path(m.folder)) for idx, m in enumerate(loaded_measures)),
    ):
        if source is not None and source.resolve().is_relative_to(native_dir):
            raise ValueError(
                f"{field} must be outside the calculation folder being replaced: {native_dir}."
            )
    run_folder = to_posix_relative(run_dir, garden_root_path)
    _ENERGY_RUNS.prepare_folder(
        garden_root_path,
        run_folder,
        recipe=ENERGY_RUN_RECIPE,
        model_target=resolved_model_target,
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    _clear_native_recipe_dir(garden_root_path, native_dir)
    sim_par_path = _write_json_input(run_dir, "simulation_parameter.json", sim_par)
    measures_spec_path: str | None = None
    if normalized_measures:
        input_dir = run_dir / "inputs"
        input_dir.mkdir(parents=True, exist_ok=True)
        spec_file = input_dir / "measures_spec.json"
        spec_file.write_text(
            json.dumps(
                [{"folder": item["folder"], "arguments": item["arguments"]} for item in normalized_measures],
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        measures_spec_path = str(spec_file)
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
        "measures_only": bool(measures_only),
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
    if normalized_measures:
        record["measures"] = normalized_measures
        record["measures_spec_path"] = to_posix_relative(
            Path(measures_spec_path), garden_root_path
        )
    if sim_par_path is not None:
        record["sim_par_path"] = to_posix_relative(
            Path(sim_par_path), garden_root_path
        )
    if resolved_parameter_target is not None:
        record["simulation_parameter_target"] = resolved_parameter_target
    if resolved_output_request_target is not None:
        record["output_request_target"] = resolved_output_request_target
    record["stage_statuses"] = _derive_stage_statuses(
        garden_root=garden_root_path,
        record=record,
        run_dir=run_dir,
    )
    _upsert_record(garden_root_path, record)
    return {"manifest": manifest, "record": record, "reused": False}


def _execute_annual_energy_run(
    *,
    garden_root: Path,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Execute an already registered annual run without preparing its folder."""
    manifest = GardenManifest.read(garden_root)
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
    measures_spec_path = (
        _record_path(
            garden_root,
            record["measures_spec_path"],
            field_name="measures_spec_path",
        )
        if record.get("measures_spec_path")
        else None
    )
    measures_only = bool(record.get("measures_only", False))
    if _requires_external_ironbug_console(model_path):
        ib_dir = resolve_ironbug_dir()
        if resolve_ironbug_console_exe(ib_dir) is None:
            blocker_msg = (
                "Model uses Ironbug DetailedHVAC, but external Ironbug.Console was not found. "
                "Install Ladybug Tools / Ironbug (https://github.com/MingboPeng/Ironbug) and verify "
                "the path with LB_Get_Runtime_Config."
            )
            warnings.append(blocker_msg)
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
                }
            )
            record["stage_statuses"] = _derive_stage_statuses(
                garden_root=garden_root,
                record=record,
                run_dir=run_dir,
            )
            _upsert_record(garden_root, record)
            return _energy_response(
                manifest=manifest,
                record=record,
                message=blocker_msg,
                report_status="blocked",
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
            measures_spec_path=measures_spec_path,
            measures_only=measures_only,
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
        elif not measures_only and eui_status != 0:
            status = "failed"
            warnings.append(
                f"Honeybee Energy EUI command failed with exit code {eui_status}."
            )

    outputs = _recipe_outputs(
        garden_root_path=garden_root,
        run_dir=run_dir,
        warnings=warnings,
    )
    osw_output = _outputs_map({"outputs": outputs}).get("osw", {})
    if osw_output.get("exists") and osw_output.get("path"):
        record["workflow_path"] = osw_output["path"]
    if (
        status == "completed"
        and not measures_only
        and not _outputs_map({"outputs": outputs}).get("eui", {}).get("exists")
    ):
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
    stage_statuses = _derive_stage_statuses(
        garden_root=garden_root,
        record=record,
        run_dir=run_dir,
        simulate_status=simulate_status,
        eui_status=eui_status,
    )
    if (
        stage_statuses.get("energyplus", {}).get("status") == "completed"
        and stage_statuses.get("reporting_measures", {}).get("status") == "failed"
    ):
        note = (
            "EnergyPlus simulation completed, while OpenStudio reporting_measures failed; "
            "SQL/ERR/EUI outputs may still be readable."
        )
        if note not in warnings:
            warnings.append(note)
    record["stage_statuses"] = stage_statuses
    record["warnings"] = warnings
    _upsert_record(garden_root, record)
    ep_ok_rep_failed = (
        status != "completed"
        and stage_statuses.get("energyplus", {}).get("status") == "completed"
        and stage_statuses.get("reporting_measures", {}).get("status") == "failed"
    )
    return _energy_response(
        manifest=manifest,
        record=record,
        message=(
            "OpenStudio measures-only run completed."
            if (status == "completed" and measures_only)
            else "Annual energy-use simulation completed."
            if status == "completed"
            else "Annual EnergyPlus simulation completed, while reporting_measures failed; run record was saved."
            if ep_ok_rep_failed
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
    measures: list[dict[str, Any] | str] | None = None,
    measures_only: bool = False,
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
        measures=measures,
        measures_only=measures_only,
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
    record.setdefault("worker_pid", os.getpid())
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
    measures: list[dict[str, Any] | str] | None = None,
    measures_only: bool = False,
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
        measures=measures,
        measures_only=measures_only,
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
        proc = _submit_energy_background(
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
    worker_pid = getattr(proc, "pid", None)
    if worker_pid is not None:
        latest = _ENERGY_RUNS.get(garden_root_path, str(record["run_id"]))
        record = latest or record
        record["worker_pid"] = int(worker_pid)
        _upsert_record(garden_root_path, record)
    result = _energy_response(
        manifest=manifest,
        record=record,
        message="Annual energy-use simulation started; poll the energy_run target for status.",
    )
    poll_next = {
        "tool": "GD_Poll_Run",
        "arguments": {
            "garden_root": str(garden_root_path),
            "run_target": record["target"],
        },
    }
    result["poll_next"] = poll_next
    result["summary_view"]["poll_next"] = poll_next
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
    raw_record = _run_record_by_id(garden_root_path, resolved_run_id)
    record = _public_run(raw_record)
    outputs = list(record.get("outputs", []))
    status = record.get("status")
    evidence = _energy_run_result_evidence(
        garden_root=garden_root_path,
        run_id=resolved_run_id,
        record=raw_record,
    )
    stage_statuses = evidence["stage_statuses"]
    record["stage_statuses"] = stage_statuses
    return {
        "status": status,
        "run_id": resolved_run_id,
        "outputs": outputs,
        "stage_statuses": stage_statuses,
        "result_evidence": evidence,
        "final_answer_ready": evidence["final_answer_ready"],
        "summary_view": {
            "garden_target": manifest.target(),
            "run": record,
            "run_id": resolved_run_id,
            "status": status,
            "outputs": outputs,
            "stage_statuses": stage_statuses,
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
    try:
        eui_path = _absolute_output_path(garden_root_path, record, "eui")
    except ValueError:
        eui_path = None
    stage_statuses = (
        dict(record["stage_statuses"])
        if record.get("status") in {"completed", "failed", "cancelled"}
        and isinstance(record.get("stage_statuses"), dict)
        else _derive_stage_statuses(garden_root=garden_root_path, record=record)
    )
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
            "stage_statuses": stage_statuses,
            "missing_output": "eui",
            "missing_path": missing_path,
            "available_output_names": existing_output_names,
            "recommended_next_tools": [
                "GD_Poll_Run",
                "EP_Read_Errors",
            ],
        }
        message = (
            f"Energy run {resolved_run_id} has no EUI output. "
            "Read ERR diagnostics for the precise EnergyPlus blocker."
        )
        return {
            "eui": None,
            "path": None,
            "stage_statuses": stage_statuses,
            "energy_blocker": {
                "status": "missing_eui_output",
                "message": message,
                **details,
            },
            "summary_view": {
                "garden_target": manifest.target(),
                "run_id": resolved_run_id,
                "run_status": record.get("status"),
                "stage_statuses": stage_statuses,
                "eui": None,
                "path": None,
                "available_outputs": outputs,
                "available_output_names": existing_output_names,
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
        "GD_Poll_Run",
        "EP_Read_Errors",
    ]
    if final_answer_ready:
        final_answer_guidance = (
            "EUI, SQL, and clean ERR outputs are available."
        )
    elif completed_with_diagnostics:
        final_answer_guidance = (
            "EUI and SQL outputs are available, and ERR diagnostics contain severe or fatal entries."
        )
    else:
        final_answer_guidance = (
            "EUI is available, though SQL or ERR outputs are absent; inspect available outputs for details."
        )
    result_evidence = {
        "run_id": resolved_run_id,
        "run_status": record.get("status"),
        "stage_statuses": stage_statuses,
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
        "stage_statuses": stage_statuses,
        "result_evidence": result_evidence,
        "outputs": outputs,
        "files": outputs,
        "err_exists": err_exists,
        "sql_exists": sql_exists,
        "warning_count": int((err_summary or {}).get("warning_count") or 0),
        "severe_count": severe_count,
        "fatal_count": fatal_count,
        "final_answer_ready": final_answer_ready,
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": resolved_run_id,
            "run_status": record.get("status"),
            "stage_statuses": stage_statuses,
            "eui": eui,
            "path": to_posix_relative(eui_path, garden_root_path),
            "err_exists": err_exists,
            "sql_exists": sql_exists,
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
            "recommended_next_tools": ["GD_Poll_Run", "GD_Read_Run_Logs"],
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
                "recommended_next_tools": ["GD_Poll_Run", "GD_Read_Run_Logs"],
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
