"""Radiance recipe run services."""

from __future__ import annotations

from calendar import month_abbr
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
from typing import Any

import lbt_recipes
from honeybee_radiance.writer import _filter_by_pattern
from lbt_recipes.recipe import Recipe
from lbt_recipes.settings import RecipeSettings

from garden.background import capture_recipe_stdio, submit_worker_process
from garden.honeybee_core.model_io import load_honeybee_model, resolve_model_target
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import (
    require_garden_root,
    simulation_folder_name,
    to_posix_relative,
)
from garden.radiance.sky import (
    RADIANCE_SKY_FILE_TARGET_TYPE,
    WEA_TARGET_TYPE,
    _resolve_epw_path,
)
from garden.run_ledger import RunManager, serialized_run_start
from ladybug_tools_mcp.contracts import make_report
from ladybug_tools_mcp.runtime_home import safe_ascii_temp_dir

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
    "pmv-comfort-map",
    "utci-comfort-map",
    "adaptive-comfort-map",
}
_COMFORT_MAP_RECIPES = {
    "pmv-comfort-map",
    "utci-comfort-map",
    "adaptive-comfort-map",
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
    temp_dir = safe_ascii_temp_dir(garden_root, run_dir.name)
    env["TEMP"] = str(temp_dir)
    env["TMP"] = str(temp_dir)
    return submit_worker_process(
        garden_root=garden_root,
        run_dir=run_dir,
        worker_module="garden.radiance.run:run_radiance_recipe",
        request=kwargs,
        cwd=garden_root,
        environment=env,
    )


_garden_root = require_garden_root
_capture_recipe_stdio = capture_recipe_stdio

RADIANCE_RUN_PUBLIC_FIELDS = (
    "target",
    "run_id",
    "simulation_id",
    "recipe",
    "recipe_source",
    "is_external_recipe",
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
    "debug_folder",
    "outputs",
    "workers",
    "worker_pid",
    "warnings",
    "radiance_parameters_path",
)

_RADIANCE_RUNS = RunManager(
    domain=RADIANCE_RUN_DOMAIN,
    target_type=RADIANCE_RUN_TARGET_TYPE,
    runs_dir=RADIANCE_RUNS_DIR,
    default_recipe="point-in-time-grid",
    allowed_recipes=None,
    run_id_prefix="radiance",
    target_run_id_required=False,
    not_found_label="Radiance",
    public_fields=RADIANCE_RUN_PUBLIC_FIELDS,
)
_RADIANCE_RUN_LEDGER = _RADIANCE_RUNS.ledger


def _run_index_path(garden_root: Path) -> Path:
    return _RADIANCE_RUNS.index_path(garden_root)


def _read_index(garden_root: Path) -> list[dict[str, Any]]:
    return _RADIANCE_RUNS.list(garden_root)


def _run_target(garden_id: str, run_id: str, recipe_name: str) -> dict[str, str]:
    return _RADIANCE_RUNS.make_target(garden_id, run_id, recipe=recipe_name)


def _normalize_run_id(value: str | None) -> str:
    return _RADIANCE_RUNS.normalize_run_id(value)


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


def _resolve_sky_input(
    *,
    garden_root: Path | None = None,
    garden_root_path: Path | None = None,
    manifest: GardenManifest,
    sky_file_target: dict[str, Any] | None,
    sky: str | None,
) -> str:
    root = garden_root_path or garden_root
    if root is None:
        raise ValueError("garden_root is required to resolve sky input.")
    return _resolve_sky_string(
        garden_root=root,
        manifest=manifest,
        sky_file_target=sky_file_target,
        sky=sky,
    )


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


def _split_sky_command_tokens(
    tokens: list[str],
    *,
    two_arg_flags: set[str],
    one_arg_flags: set[str],
) -> list[str]:
    """Return positional date/time tokens even when flags appear before or after them."""
    positionals: list[str] = []
    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        if tok in two_arg_flags:
            idx += 3
            continue
        if tok in one_arg_flags:
            idx += 2
            continue
        if tok.startswith("-"):
            idx += 1
            continue
        positionals.append(tok)
        idx += 1
    return positionals


def _parse_sky_positional_date_time(
    positionals: list[str],
) -> tuple[list[str], int | None]:
    from garden.radiance.sky import _recipe_time_zone_int

    values: list[str] = []
    tz_val: int | None = None
    for token in positionals:
        tz_maybe = _recipe_time_zone_int(token)
        if len(values) == 3 and tz_maybe is not None and not token.isdigit():
            tz_val = tz_maybe
            continue
        if len(values) == 2:
            joined = re.match(r"^([0-9]+(?::[0-9]+|\.[0-9]+)?)([A-Za-z_+-]+)$", token)
            if joined:
                values.append(joined.group(1))
                tz_maybe = _recipe_time_zone_int(joined.group(2))
                if tz_maybe is not None:
                    tz_val = tz_maybe
                continue
        values.append(token)
    return values, tz_val


def _meridian_to_tz(meridian: str | None) -> int | None:
    if meridian is None:
        return None
    try:
        return -int(round(float(meridian) / 15.0))
    except ValueError:
        return None


def _recipe_sky_from_gensky_tokens(tokens: list[str]) -> str:
    sky_type = 0
    filtered_tokens: list[str] = []
    for token in tokens:
        if token in _GENSKY_FLAG_TO_CIE_TYPE:
            sky_type = _GENSKY_FLAG_TO_CIE_TYPE[token]
            continue
        filtered_tokens.append(token)
    positionals = _split_sky_command_tokens(
        filtered_tokens,
        two_arg_flags={"-ang"},
        one_arg_flags={"-a", "-o", "-m", "-g", "-tz", "-t", "-c", "-r", "-B", "-b", "-R", "-alt", "-az"},
    )
    values, tz_val = _parse_sky_positional_date_time(positionals)
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
    _append_option(
        parts,
        "-tz",
        _extract_flag(tokens, "-tz")
        or (tz_val if tz_val is not None else _meridian_to_tz(_extract_flag(tokens, "-m"))),
    )
    _append_option(parts, "-type", sky_type)
    _append_option(parts, "-g", _extract_flag(tokens, "-g"))
    return " ".join(parts)


def _recipe_sky_from_gendaylit_tokens(tokens: list[str]) -> str:
    positionals = _split_sky_command_tokens(
        tokens,
        two_arg_flags={"-W", "-L", "-ang"},
        one_arg_flags={"-a", "-o", "-m", "-g", "-tz", "-O", "-G", "-alt", "-az"},
    )
    values, tz_val = _parse_sky_positional_date_time(positionals)
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
    _append_option(
        parts,
        "-tz",
        _extract_flag(tokens, "-tz")
        or (tz_val if tz_val is not None else _meridian_to_tz(_extract_flag(tokens, "-m"))),
    )
    w_dni: str | None = None
    w_dhi: str | None = None
    l_dni: str | None = None
    l_dhi: str | None = None
    for index, token in enumerate(tokens):
        if token == "-W" and index + 2 < len(tokens):
            w_dni = tokens[index + 1]
            w_dhi = tokens[index + 2]
            break
        if token == "-L" and index + 2 < len(tokens):
            l_dni = tokens[index + 1]
            l_dhi = tokens[index + 2]
            break
    if w_dni is not None or w_dhi is not None:
        _append_option(parts, "-dni", w_dni)
        _append_option(parts, "-dhi", w_dhi)
    elif l_dni is not None and l_dhi is not None:
        parts.extend(["-L", l_dni, l_dhi])
    _append_option(parts, "-g", _extract_flag(tokens, "-g"))
    return " ".join(parts)


def _sky_cli_compatible_string(sky_str: str) -> str:
    """Convert -L illuminance flags inside climate-based sky strings for honeybee-radiance CLI."""
    text = sky_str.strip()
    if not text.lower().startswith("climate-based"):
        return text
    tokens = shlex.split(text)
    if "-L" not in tokens:
        return text
    idx = tokens.index("-L")
    if idx + 2 >= len(tokens):
        return text
    try:
        dni_irr = float(tokens[idx + 1]) / 179.0
        dhi_irr = float(tokens[idx + 2]) / 179.0
    except ValueError:
        return text
    rebuilt = tokens[:idx] + ["-dni", f"{dni_irr:g}", "-dhi", f"{dhi_irr:g}"] + tokens[idx + 3 :]
    return " ".join(rebuilt)


def _resolve_wea_path(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    wea_target: dict[str, Any] | None,
    wea_path: str | None,
    weather_file_target: dict[str, Any] | None = None,
) -> str:
    provided = [
        name
        for name, val in (
            ("wea_target", wea_target),
            ("wea_path", wea_path),
            ("weather_file_target", weather_file_target),
        )
        if val is not None
    ]
    if not provided:
        raise ValueError("Provide exactly one of wea_target or wea_path.")
    if len(provided) > 1 and ("wea_target" in provided or "wea_path" in provided):
        raise ValueError("Provide exactly one of wea_target, wea_path, or weather_file_target.")
    if weather_file_target is not None:
        epw, _ = _resolve_epw_path(
            garden_root=garden_root,
            manifest=manifest,
            weather_target=weather_file_target,
            epw_path=None,
        )
        from garden.radiance.sky import create_wea_from_weather_file

        wea_res = create_wea_from_weather_file(
            garden_root=str(garden_root),
            identifier=f"{epw.stem}_wea",
            weather_target=weather_file_target,
        )
        return str((garden_root / wea_res["target"]["path"]).resolve())
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


def _normalize_grid_metrics(
    grid_metrics: list[dict[str, Any]] | dict[str, Any] | str | None,
) -> list[dict[str, Any]] | str | None:
    """Normalize grid_metrics input to list[dict] | str | None for pollination-handlers."""
    if grid_metrics is None:
        return None
    if isinstance(grid_metrics, str):
        return grid_metrics
    if isinstance(grid_metrics, dict):
        return [grid_metrics]
    if isinstance(grid_metrics, list):
        if not all(isinstance(item, dict) for item in grid_metrics):
            raise ValueError("grid_metrics list items must all be dictionaries.")
        return list(grid_metrics)
    raise ValueError("grid_metrics must be a list of dicts, a dict, or a file/JSON string.")


def _materialize_schedule_values(
    *,
    garden_root_path: Path,
    schedule: Any,
) -> list[float] | None:
    """Resolve hourly numeric schedule values from a Garden target, list, file, or inline CSV text."""
    if schedule is None:
        return None
    if isinstance(schedule, (list, tuple)):
        return [float(v) for v in schedule]
    if isinstance(schedule, dict):
        target_type = schedule.get("target_type")
        if target_type == "garden_properties_library_object":
            if schedule.get("domain") != "honeybee_energy" or schedule.get("object_family") != "schedule":
                raise ValueError("Schedule target must reference honeybee_energy:schedule.")
            from garden.libraries.properties import get_garden_properties_library_object

            schedule = get_garden_properties_library_object(
                garden_root=str(garden_root_path),
                target=schedule,
            )["object_dict"]
        elif target_type == "data_collection":
            rel_path = schedule.get("path")
            if not isinstance(rel_path, str) or not rel_path:
                raise ValueError("data_collection schedule target requires a path.")
            from ladybug.datacollection import BaseCollection

            dc_path = (garden_root_path / rel_path).resolve()
            dc_path.relative_to(garden_root_path)
            dc = BaseCollection.from_dict(json.loads(dc_path.read_text(encoding="utf-8")))
            return [float(v) for v in dc.values]
        elif isinstance(schedule.get("object_dict"), dict):
            schedule = schedule["object_dict"]

        if isinstance(schedule, dict):
            if "values" in schedule and "type" not in schedule:
                return [float(v) for v in schedule["values"]]
            from honeybee_energy.schedule.dictutil import dict_to_schedule

            sch_obj = dict_to_schedule(schedule)
            vals = sch_obj.values() if callable(getattr(sch_obj, "values", None)) else sch_obj.values
            return [float(v) for v in vals]

    if isinstance(schedule, str):
        text = schedule.strip()
        if not text:
            return None
        candidate = Path(text).expanduser()
        if not candidate.is_absolute():
            candidate = (garden_root_path / candidate).resolve()
        if "\n" not in text and "," not in text:
            try:
                candidate.relative_to(garden_root_path)
            except ValueError:
                candidate = Path(text).expanduser().resolve()
            if candidate.is_file():
                if candidate.suffix.lower() == ".json":
                    return _materialize_schedule_values(
                        garden_root_path=garden_root_path,
                        schedule=json.loads(candidate.read_text(encoding="utf-8")),
                    )
                values: list[float] = []
                for line in candidate.read_text(encoding="utf-8").splitlines():
                    for tok in line.replace(",", " ").split():
                        try:
                            values.append(float(tok))
                        except ValueError:
                            pass
                if values:
                    return values
            try:
                from honeybee_energy.lib.schedules import schedule_by_identifier

                sch_obj = schedule_by_identifier(text)
                vals = sch_obj.values() if callable(getattr(sch_obj, "values", None)) else sch_obj.values
                return [float(v) for v in vals]
            except Exception:
                pass
        else:
            parsed: list[float] = []
            for raw_line in text.splitlines():
                for tok in raw_line.replace(",", " ").split():
                    if tok:
                        parsed.append(float(tok))
            if parsed:
                return parsed
    return None


def _materialize_schedule_input(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    run_dir: Path,
    schedule: Any,
) -> str | None:
    """Materialize a Garden schedule target, list, or inline CSV text into a .csv file."""
    if schedule is None:
        return None
    if isinstance(schedule, str) and "\n" not in schedule and "," not in schedule:
        text = schedule.strip()
        candidate = (garden_root_path / text).resolve()
        try:
            candidate.relative_to(garden_root_path)
            if candidate.is_file() and candidate.suffix.lower() in {".csv", ".txt"}:
                return str(candidate)
        except ValueError:
            pass
    values = _materialize_schedule_values(garden_root_path=garden_root_path, schedule=schedule)
    if values is not None:
        csv_text = "\n".join(str(v) for v in values)
        return _write_text_input(run_dir, "schedule.csv", csv_text)
    if isinstance(schedule, str):
        return schedule
    raise ValueError("Unsupported schedule input; provide a CSV file, inline CSV text, or Garden schedule target.")


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


def _recipe_sim_folder(
    run_dir: Path,
    recipe_name: str,
    *,
    simulation_id: str | None = None,
) -> Path:
    if simulation_id:
        candidate = run_dir / simulation_id
        if candidate.exists():
            return candidate
        legacy = run_dir / recipe_name.replace("-", "_")
        if legacy.exists():
            return legacy
        return candidate
    return run_dir / recipe_name.replace("-", "_")


def _recipe_status_path(
    run_dir: Path,
    recipe_name: str,
    *,
    simulation_id: str | None = None,
) -> Path:
    return (
        _recipe_sim_folder(run_dir, recipe_name, simulation_id=simulation_id)
        / "__logs__"
        / "status.json"
    )


def _clear_recipe_status_logs(
    run_dir: Path,
    recipe_name: str,
    *,
    simulation_id: str | None = None,
) -> None:
    log_dir = _recipe_status_path(
        run_dir,
        recipe_name,
        simulation_id=simulation_id,
    ).parent
    for name in ("status.json", "logs.log"):
        (log_dir / name).unlink(missing_ok=True)


def _upsert_record(garden_root: Path, record: dict[str, Any]) -> None:
    _RADIANCE_RUNS.upsert(garden_root, record)


def _run_record_by_id(garden_root: Path, run_id: str) -> dict[str, Any]:
    return _RADIANCE_RUNS.require(garden_root, run_id)


def _run_id_from_target_or_value(
    *,
    run_target: dict[str, Any] | None,
    run_id: str | None,
) -> str:
    return _RADIANCE_RUNS.resolve_run_id(run_target, run_id)


def _outputs_map(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): item for item in record.get("outputs", [])}


@lru_cache(maxsize=None)
def _recipe_output_specs(recipe_name_or_path: str) -> tuple[dict[str, Any], ...]:
    """Read native output paths without running Grasshopper value handlers."""
    candidate = Path(recipe_name_or_path)
    if candidate.is_dir() and (candidate / "package.json").is_file():
        return tuple(json.loads((candidate / "package.json").read_text(encoding="utf-8"))["outputs"])
    package_path = (
        Path(lbt_recipes.__file__).parent
        / recipe_name_or_path.replace("-", "_")
        / "package.json"
    )
    if not package_path.is_file():
        raise ValueError(f"Unsupported Radiance recipe: {recipe_name_or_path}")
    return tuple(json.loads(package_path.read_text(encoding="utf-8"))["outputs"])


def _missing_outputs(
    recipe_name_or_path: str,
    *,
    simulation_id: str | None = None,
) -> list[dict[str, Any]]:
    return [
        {"name": spec["name"], "path": None, "exists": False}
        for spec in _recipe_output_specs(recipe_name_or_path)
    ]


def _recipe_log_status(
    *,
    run_dir: Path,
    recipe_name: str,
    simulation_id: str | None = None,
) -> tuple[str | None, str | None]:
    status_path = _recipe_status_path(
        run_dir,
        recipe_name,
        simulation_id=simulation_id,
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
    simulation_id: str | None = None,
    recipe_source: str | None = None,
) -> list[dict[str, Any]]:
    outputs = []
    recipe_folder = _recipe_sim_folder(
        run_dir,
        recipe_name,
        simulation_id=simulation_id,
    )
    for spec in _recipe_output_specs(recipe_source or recipe_name):
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
    return _RADIANCE_RUNS.public_run(record)


def _reconcile_running_record(
    *,
    garden_root_path: Path,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Repair stale running records when a background recipe wrote final outputs."""
    if record.get("status") != "running":
        return record
    recipe_name = str(record.get("recipe") or "")
    recipe_source = str(record.get("recipe_source") or recipe_name)
    try:
        _recipe_output_specs(recipe_source)
    except ValueError:
        return record
    run_folder = record.get("run_folder")
    if not isinstance(run_folder, str) or not run_folder:
        return record
    run_dir = (garden_root_path / run_folder).resolve()
    try:
        run_dir.relative_to(garden_root_path)
    except ValueError:
        return record
    simulation_id = record.get("simulation_id")
    warnings = list(record.get("warnings") or [])
    outputs = _recipe_outputs(
        garden_root_path=garden_root_path,
        recipe_name=recipe_name,
        run_dir=run_dir,
        simulation_id=simulation_id,
        recipe_source=recipe_source,
    )
    missing_outputs = _missing_required_outputs(outputs)
    logged_status, logged_message = _recipe_log_status(
        run_dir=run_dir,
        recipe_name=recipe_name,
        simulation_id=simulation_id,
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
        "simulation_id": public.get("simulation_id"),
        "debug_folder": public.get("debug_folder"),
        "status": status,
        "recipe": recipe,
        "outputs": public.get("outputs", []),
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "run_id": run_id,
            "simulation_id": public.get("simulation_id"),
            "debug_folder": public.get("debug_folder"),
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
        poll_next = {
            "tool": "GD_Poll_Run",
            "arguments": {
                "garden_root": str(garden_root_path),
                "run_target": target,
            },
        }
        result["poll_next"] = poll_next
        result["summary_view"]["poll_next"] = poll_next
    if record.get("worker_pid") is not None:
        result["worker_pid"] = record.get("worker_pid")
        result["summary_view"]["worker_pid"] = record.get("worker_pid")
    return result


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
    recipe_source: str | None = None,
    debug_folder: str | None = None,
) -> dict[str, Any]:
    """Run one Honeybee Radiance or generic Queenbee recipe and update the Garden run ledger."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    record = _run_record_by_id(garden_root_path, run_id)
    run_folder = record.get("run_folder")
    if not isinstance(run_folder, str) or not run_folder:
        raise ValueError(f"Radiance run has no valid run folder: {run_id}")
    run_dir = (garden_root_path / run_folder).resolve()
    run_dir.relative_to(garden_root_path)
    run_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = safe_ascii_temp_dir(garden_root_path, run_dir.name)
    os.environ["TEMP"] = str(temp_dir)
    os.environ["TMP"] = str(temp_dir)
    effective_source = recipe_source or record.get("recipe_source") or recipe_name
    simulation_id = str(record.get("simulation_id") or run_id)
    warnings: list[str] = []
    status = "completed"
    try:
        with _capture_recipe_stdio(run_dir):
            recipe = Recipe(effective_source)
            recipe.simulation_id = simulation_id
            for name, value in inputs.items():
                if value is None:
                    continue
                if name == "sky" and isinstance(value, str):
                    value = _sky_cli_compatible_string(value)
                elif name == "grid-metrics":
                    value = _normalize_grid_metrics(value)
                elif name == "schedule":
                    value = _materialize_schedule_input(
                        garden_root_path=garden_root_path,
                        manifest=manifest,
                        run_dir=run_dir,
                        schedule=value,
                    )
                recipe.input_value_by_name(name, value)
            settings_kwargs: dict[str, Any] = {
                "folder": str(run_dir),
                "workers": workers,
                "reload_old": reload_old,
                "report_out": False,
            }
            if debug_folder:
                settings_kwargs["debug_folder"] = debug_folder
            settings = RecipeSettings(**settings_kwargs)
            recipe.run(
                settings=settings,
                radiance_check=True,
                queenbee_path=str(
                    Path(sys.executable).absolute().parent
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
        simulation_id=simulation_id,
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
                    recipe_folder=_recipe_sim_folder(
                        run_dir,
                        recipe_name,
                        simulation_id=simulation_id,
                    ),
                    grid_filter=str(inputs.get("grid-filter") or "*"),
                )
        except Exception as exc:  # pragma: no cover - exercised by real engines
            status = "failed"
            warnings.append(f"Could not refresh EN 17037 results: {exc}")

    outputs = _recipe_outputs(
        garden_root_path=garden_root_path,
        recipe_name=recipe_name,
        run_dir=run_dir,
        simulation_id=simulation_id,
        recipe_source=effective_source,
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
            "worker_pid": record.get("worker_pid") or os.getpid(),
        }
    )
    _upsert_record(garden_root_path, record)
    return {
        "target": _run_target(manifest.garden_id, run_id, recipe_name),
        "summary_view": {
            "garden_target": manifest.target(),
            "run_id": run_id,
            "simulation_id": simulation_id,
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
    debug_folder: str | None = None,
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
        / simulation_folder_name(f"{model_display_name}_{run_id}")
    ).resolve()
    run_dir.relative_to(garden_root_path)
    run_folder = to_posix_relative(run_dir, garden_root_path)
    _RADIANCE_RUNS.prepare_folder(
        garden_root_path,
        run_folder,
        recipe=recipe_name,
        model_target=resolved_model_target,
        preserve_other_recipes=True,
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    _clear_recipe_status_logs(run_dir, recipe_name, simulation_id=run_id)
    radiance_parameters_path = _write_text_input(
        run_dir,
        "radiance_parameters.txt",
        radiance_parameters,
    )
    resolved_debug_folder: str | None = None
    if debug_folder:
        dbg = Path(debug_folder).expanduser()
        dbg = (garden_root_path / dbg).resolve() if not dbg.is_absolute() else dbg.resolve()
        dbg.relative_to(garden_root_path)
        dbg.mkdir(parents=True, exist_ok=True)
        resolved_debug_folder = str(dbg)

    target = _run_target(manifest.garden_id, run_id, recipe_name)
    recipe_inputs = dict(inputs)
    recipe_inputs["model"] = str(model_path)
    if recipe_inputs.get("schedule") is not None:
        recipe_inputs["schedule"] = _materialize_schedule_input(
            garden_root_path=garden_root_path,
            manifest=manifest,
            run_dir=run_dir,
            schedule=recipe_inputs["schedule"],
        )
    if recipe_inputs.get("grid-metrics") is not None:
        recipe_inputs["grid-metrics"] = _normalize_grid_metrics(recipe_inputs["grid-metrics"])
    if radiance_parameters:
        recipe_inputs["radiance-parameters"] = radiance_parameters
    if workers is not None:
        recipe_inputs["cpu-count"] = workers

    record: dict[str, Any] = {
        "run_id": run_id,
        "simulation_id": run_id,
        "target": target,
        "recipe": recipe_name,
        "recipe_source": recipe_name,
        "is_external_recipe": False,
        "calculation_family": calculation_family,
        "calculation_type": calculation_type,
        "command_name": command_name,
        "status": "running",
        "created_at": utc_now_iso(),
        "model_target": resolved_model_target,
        "model_display_name": model_display_name,
        "model_path": to_posix_relative(model_path, garden_root_path),
        "run_folder": run_folder,
        "debug_folder": (
            to_posix_relative(Path(resolved_debug_folder), garden_root_path)
            if resolved_debug_folder
            else None
        ),
        "outputs": _missing_outputs(recipe_name, simulation_id=run_id),
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
        proc = _submit_radiance_background(
            garden_root=str(garden_root_path),
            recipe_name=recipe_name,
            recipe_source=recipe_name,
            inputs=recipe_inputs,
            run_id=run_id,
            model_target=resolved_model_target,
            calculation_family=calculation_family,
            calculation_type=calculation_type,
            command_name=command_name,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            debug_folder=resolved_debug_folder,
        )
    except Exception as exc:
        record.update(
            {
                "status": "failed",
                "completed_at": utc_now_iso(),
                "outputs": _missing_outputs(recipe_name, simulation_id=run_id),
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

    worker_pid = getattr(proc, "pid", None)
    if worker_pid is not None:
        latest = _RADIANCE_RUNS.get(garden_root_path, run_id)
        if latest is not None:
            record = dict(latest)
        record["worker_pid"] = worker_pid
        _upsert_record(garden_root_path, record)

    if record.get("status") != "running":
        return _run_response(
            garden_root_path=garden_root_path,
            manifest=manifest,
            record=record,
            message=f"Radiance recipe finished with status {record.get('status')}.",
            report_status="ok" if record.get("status") == "completed" else "error",
        )

    poll_arguments = {"garden_root": str(garden_root_path), "run_target": target}
    poll_next = {
        "tool": "GD_Poll_Run",
        "arguments": poll_arguments,
    }
    return {
        "target": target,
        "radiance_run_target": target,
        "run_target": target,
        "run_id": run_id,
        "simulation_id": run_id,
        "debug_folder": record.get("debug_folder"),
        "status": "running",
        "recipe": recipe_name,
        "worker_pid": record.get("worker_pid"),
        "poll_next": poll_next,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "run_id": run_id,
            "simulation_id": run_id,
            "debug_folder": record.get("debug_folder"),
            "status": "running",
            "recipe": recipe_name,
            "calculation_family": calculation_family,
            "calculation_type": calculation_type,
            "command_name": command_name,
            "run_folder": run_folder,
            "worker_pid": record.get("worker_pid"),
            "outputs": _outputs_map(record),
            "poll_next": poll_next,
        },
        "report": make_report(
            status="ok",
            message="Radiance recipe started; poll the radiance_run target with GD_Poll_Run for status.",
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
    grid_metrics: list[dict[str, Any]] | dict[str, Any] | str | None = None,
    cloudy_sky: str = "uniform",
    radiance_parameters: str | dict[str, Any] | None = None,
    run_id: str | None = None,
    workers: int | None = None,
    reload_old: bool = False,
    silent: bool = True,
    debug_folder: str | None = None,
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
    elif recipe_name == "daylight-factor":
        normalized_gm = _normalize_grid_metrics(grid_metrics)
        if normalized_gm is not None:
            inputs["grid-metrics"] = normalized_gm
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
        debug_folder=debug_folder,
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
    debug_folder: str | None = None,
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
        debug_folder=debug_folder,
    )


def start_radiance_matrix_run(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    calculation_type: str = "annual_daylight",
    enhanced: bool = True,
    wea_target: dict[str, Any] | None = None,
    wea_path: str | None = None,
    weather_file_target: dict[str, Any] | None = None,
    grid_filter: str = "*",
    north: float | None = None,
    timestep: int | None = None,
    schedule: Any = None,
    thresholds: str | None = None,
    output_type: str | None = None,
    sky_density: int | None = None,
    min_sensor_count: int | None = 1,
    grid_metrics: list[dict[str, Any]] | dict[str, Any] | str | None = None,
    radiance_parameters: str | dict[str, Any] | None = None,
    run_id: str | None = None,
    workers: int | None = None,
    reload_old: bool = False,
    silent: bool = True,
    debug_folder: str | None = None,
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
            weather_file_target=weather_file_target,
        ),
        "grid-filter": grid_filter,
    }
    if north is not None:
        inputs["north"] = north
    if timestep is not None:
        inputs["timestep"] = timestep
    if min_sensor_count is not None:
        inputs["min-sensor-count"] = min_sensor_count
    normalized_gm = _normalize_grid_metrics(grid_metrics)
    if normalized_gm is not None and recipe_name in _ANNUAL_DAYLIGHT_RECIPES:
        inputs["grid-metrics"] = normalized_gm
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
        debug_folder=debug_folder,
    )


def start_radiance_imageless_annual_glare(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    wea_target: dict[str, Any] | None = None,
    wea_path: str | None = None,
    weather_file_target: dict[str, Any] | None = None,
    view_filter: str = "*",
    grid_filter: str = "*",
    north: float | None = None,
    schedule: Any = None,
    dgp_threshold: float = 0.4,
    luminance_factor: float = 2000.0,
    min_sensor_count: int = 1,
    radiance_parameters: str | dict[str, Any] | None = None,
    run_id: str | None = None,
    workers: int | None = None,
    reload_old: bool = False,
    silent: bool = True,
    debug_folder: str | None = None,
) -> dict[str, Any]:
    """Start the native imageless annual glare recipe in the background (uses SensorGrids, no Views needed)."""
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
    normalized_grid_filter = _normalize_grid_filter(grid_filter)
    sensor_grids = _filter_by_pattern(
        model.properties.radiance.sensor_grids,
        normalized_grid_filter,
    )
    if not sensor_grids:
        raise ValueError(
            "The model must have attached SensorGrids (typically radial sensor grids) matching grid_filter."
        )

    inputs: dict[str, Any] = {
        "wea": _resolve_wea_path(
            garden_root=garden_root_path,
            manifest=manifest,
            wea_target=wea_target,
            wea_path=wea_path,
            weather_file_target=weather_file_target,
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
        debug_folder=debug_folder,
    )
    result["summary_view"].update(
        {
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


def start_radiance_compliance_run(
    *,
    garden_root: str,
    recipe_name: str,
    model_target: dict[str, Any] | None = None,
    wea_target: dict[str, Any] | None = None,
    wea_path: str | None = None,
    weather_file_target: dict[str, Any] | None = None,
    grid_filter: str = "*",
    north: float | None = None,
    min_sensor_count: int = 1,
    radiance_parameters: str | dict[str, Any] | None = None,
    run_id: str | None = None,
    workers: int | None = None,
    reload_old: bool = False,
    silent: bool = True,
    debug_folder: str | None = None,
    recipe_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve typed weather and model inputs before starting a compliance run."""
    if recipe_name not in {
        "leed-daylight-option-two", "annual-daylight-en17037",
        "leed-daylight-option-one", "well-daylight", "breeam-daylight-4b",
    }:
        raise ValueError(f"Unsupported daylight compliance recipe: {recipe_name}")
    if min_sensor_count < 1 or (workers is not None and workers < 1):
        raise ValueError("min_sensor_count and workers must be positive integers.")
    root = _garden_root(garden_root)
    manifest, model_target = resolve_model_target(root, model_target)
    model = load_honeybee_model(root, model_target)
    grids = _filter_by_pattern(model.properties.radiance.sensor_grids, grid_filter)
    if not grids:
        raise ValueError("The model must have attached SensorGrids matching grid_filter.")
    if len({grid.full_identifier for grid in grids}) != len(grids):
        raise ValueError(
            "Daylight compliance requires unique selected SensorGrid identifiers. "
            "Use distinct names and select only the intended workplanes."
        )
    if recipe_name in {
        "leed-daylight-option-two", "annual-daylight-en17037", "breeam-daylight-4b",
    } and any(grid.group_identifier for grid in grids):
        raise ValueError(
            f"{recipe_name} does not support grouped SensorGrids in the installed SDK. "
            "Use grids with an empty group_identifier."
        )
    if recipe_name == "breeam-daylight-4b":
        room_ids = {room.identifier for room in model.rooms}
        if any(grid.room_identifier not in room_ids or grid.mesh is None for grid in grids):
            raise ValueError(
                "BREEAM requires SensorGrids with meshes and valid room_identifier values. "
                "Create attached grids from room floor faces."
            )
    inputs = dict(recipe_options or {})
    inputs.update({"grid-filter": grid_filter, "min-sensor-count": min_sensor_count})
    if north is not None:
        inputs["north"] = north
    if recipe_name in {"annual-daylight-en17037", "well-daylight"}:
        if weather_file_target is None or wea_target is not None or wea_path is not None:
            raise ValueError("This recipe requires an EPW weather_file_target.")
        epw, _ = _resolve_epw_path(
            garden_root=root, manifest=manifest,
            weather_target=weather_file_target, epw_path=None,
        )
        inputs["epw"] = str(epw)
    else:
        if (wea_target is None and wea_path is None) or weather_file_target is not None:
            raise ValueError("This recipe requires a wea_target or wea_path.")
        inputs["wea"] = _resolve_wea_path(
            garden_root=root, manifest=manifest, wea_target=wea_target, wea_path=wea_path,
        )
    result = _start_radiance_run(
        garden_root=garden_root,
        model_target=model_target,
        recipe_name=recipe_name,
        calculation_family="compliance",
        calculation_type=recipe_name.replace("-", "_"),
        command_name="rtrace" if recipe_name == "leed-daylight-option-two" else "rfluxmtx",
        inputs=inputs,
        radiance_parameters=_radiance_parameters_from_input(radiance_parameters),
        run_id=run_id,
        workers=workers,
        reload_old=reload_old,
        silent=silent,
        debug_folder=debug_folder,
    )
    if recipe_name == "breeam-daylight-4b":
        from honeybee_radiance_postprocess.breeam.breeam import program_type_metrics

        rooms = model.rooms_by_identifier([grid.room_identifier for grid in grids])
        if any(
            room.properties.energy.program_type.identifier.replace("Creche", "Crèche")
            not in program_type_metrics for room in rooms
        ):
            result["report"]["warnings"].append(
                "The BREEAM recipe treats unrecognized room program types as office occupied spaces."
            )
    return result


def start_radiance_simulation(
    *,
    garden_root: str,
    recipe: str,
    model_target: dict[str, Any] | None = None,
    radiance_sky_file: dict[str, Any] | None = None,
    sky_file_target: dict[str, Any] | None = None,
    sky: str | None = None,
    wea_target: dict[str, Any] | None = None,
    wea_path: str | None = None,
    weather_file_target: dict[str, Any] | None = None,
    grid_filter: str = "*",
    sensor_grid_target: dict[str, Any] | None = None,
    view_filter: str = "*",
    view_target: dict[str, Any] | None = None,
    north: float | None = None,
    min_sensor_count: int = 1,
    radiance_parameters: str | dict[str, Any] | None = None,
    run_id: str | None = None,
    workers: int | None = None,
    reload_old: bool = False,
    silent: bool = True,
    wait_seconds: float | None = None,
    poll_interval: float = 1.0,
    metric: str | None = None,
    cloudy_sky: str | None = None,
    resolution: int | None = None,
    skip_overture: bool | None = None,
    timestep: int | None = None,
    schedule: Any = None,
    thresholds: str | None = None,
    output_type: str | None = None,
    sky_density: int | None = None,
    grid_metrics: list[dict[str, Any]] | dict[str, Any] | str | None = None,
    dgp_threshold: float | None = None,
    luminance_factor: float | None = None,
    diffuse_transmission: float | None = None,
    specular_transmission: float | None = None,
    glare_control_devices: str | None = None,
    debug_folder: str | None = None,
    recipe_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Start any supported Radiance or comfort-map recipe and optionally wait for completion."""
    normalized_recipe = recipe.strip().lower().replace("_", "-")
    if normalized_recipe not in SUPPORTED_RECIPES:
        allowed = ", ".join(sorted(SUPPORTED_RECIPES))
        raise ValueError(f"Unsupported Radiance recipe '{recipe}'. Supported: {allowed}.")

    opts: dict[str, Any] = {}
    if recipe_options is not None:
        if not isinstance(recipe_options, dict):
            raise ValueError("recipe_options must be a dictionary.")
        for key, value in recipe_options.items():
            opts[str(key).strip().lower().replace("-", "_")] = value

    def _opt(name: str, explicit: Any, default: Any = None) -> Any:
        if explicit is not None:
            return explicit
        if name in opts and opts[name] is not None:
            return opts[name]
        return default

    resolved_sky_file = radiance_sky_file if radiance_sky_file is not None else sky_file_target

    resolved_grid_filter = grid_filter
    if resolved_grid_filter == "*" and isinstance(sensor_grid_target, dict):
        if sensor_grid_target.get("target_type") != "radiance_sensor_grid":
            raise ValueError("sensor_grid_target must be a radiance_sensor_grid target.")
        grid_id = sensor_grid_target.get("identifier")
        if grid_id:
            resolved_grid_filter = str(grid_id)

    resolved_view_filter = view_filter
    if resolved_view_filter == "*" and isinstance(view_target, dict):
        if view_target.get("target_type") != "radiance_view":
            raise ValueError("view_target must be a radiance_view target.")
        view_id = view_target.get("identifier")
        if view_id:
            resolved_view_filter = str(view_id)

    if normalized_recipe in _COMFORT_MAP_RECIPES:
        from garden.recipes.runner import start_generic_recipe

        comfort_options = dict(recipe_options or {})
        if north is not None and "north" not in comfort_options:
            comfort_options["north"] = north
        if min_sensor_count is not None and "min-sensor-count" not in comfort_options and "min_sensor_count" not in comfort_options:
            comfort_options["min-sensor-count"] = min_sensor_count
        result = start_generic_recipe(
            garden_root=garden_root,
            recipe=normalized_recipe,
            model_target=model_target,
            weather_file_target=weather_file_target,
            radiance_parameters=radiance_parameters,
            recipe_options=comfort_options,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            debug_folder=debug_folder,
        )
    elif normalized_recipe in {"point-in-time-grid", "daylight-factor", "sky-view"}:
        if normalized_recipe == "point-in-time-grid" and resolved_sky_file is None and sky is None:
            raise ValueError("Provide radiance_sky_file for point-in-time-grid Radiance runs.")
        result = start_radiance_grid_run(
            garden_root=garden_root,
            model_target=model_target,
            calculation_type=normalized_recipe,
            sky_file_target=resolved_sky_file,
            sky=sky,
            grid_filter=resolved_grid_filter,
            metric=str(_opt("metric", metric, "illuminance")),
            min_sensor_count=min_sensor_count,
            grid_metrics=_opt("grid_metrics", grid_metrics),
            cloudy_sky=str(_opt("cloudy_sky", cloudy_sky, "uniform")),
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            debug_folder=debug_folder,
        )
    elif normalized_recipe == "point-in-time-view":
        if resolved_sky_file is None and sky is None:
            raise ValueError("Provide radiance_sky_file for point-in-time-view Radiance runs.")
        result = start_radiance_view_run(
            garden_root=garden_root,
            model_target=model_target,
            calculation_type="point_in_time",
            sky_file_target=resolved_sky_file,
            sky=sky,
            view_filter=resolved_view_filter,
            metric=str(_opt("metric", metric, "luminance")),
            resolution=_opt("resolution", resolution),
            skip_overture=_opt("skip_overture", skip_overture),
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            debug_folder=debug_folder,
        )
    elif normalized_recipe in {
        "annual-daylight",
        "annual-daylight-enhanced",
        "annual-irradiance",
        "cumulative-radiation",
        "direct-sun-hours",
    }:
        calc_type = (
            "annual_daylight"
            if normalized_recipe == "annual-daylight-enhanced"
            else normalized_recipe.replace("-", "_")
        )
        result = start_radiance_matrix_run(
            garden_root=garden_root,
            model_target=model_target,
            calculation_type=calc_type,
            enhanced=(normalized_recipe == "annual-daylight-enhanced"),
            wea_target=wea_target,
            wea_path=wea_path,
            weather_file_target=weather_file_target,
            grid_filter=resolved_grid_filter,
            north=north,
            timestep=_opt("timestep", timestep),
            schedule=_opt("schedule", schedule),
            thresholds=_opt("thresholds", thresholds),
            output_type=_opt("output_type", output_type),
            sky_density=_opt("sky_density", sky_density),
            min_sensor_count=min_sensor_count,
            grid_metrics=_opt("grid_metrics", grid_metrics),
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            debug_folder=debug_folder,
        )
    elif normalized_recipe == "imageless-annual-glare":
        result = start_radiance_imageless_annual_glare(
            garden_root=garden_root,
            model_target=model_target,
            wea_target=wea_target,
            wea_path=wea_path,
            weather_file_target=weather_file_target,
            view_filter=resolved_view_filter,
            grid_filter=resolved_grid_filter,
            north=north,
            schedule=_opt("schedule", schedule),
            dgp_threshold=float(_opt("dgp_threshold", dgp_threshold, 0.4)),
            luminance_factor=float(_opt("luminance_factor", luminance_factor, 2000.0)),
            min_sensor_count=min_sensor_count,
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            debug_folder=debug_folder,
        )
    else:
        compliance_options: dict[str, Any] = {}
        if normalized_recipe in {"leed-daylight-option-one", "well-daylight"}:
            diff = float(_opt("diffuse_transmission", diffuse_transmission, 0.05))
            spec = float(_opt("specular_transmission", specular_transmission, 0.0001))
            if not 0.0001 <= diff <= 1.0:
                raise ValueError("diffuse_transmission must be between 0.0001 and 1.")
            if not 0.0001 <= spec <= 1.0:
                raise ValueError("specular_transmission must be between 0.0001 and 1.")
            compliance_options = {
                "diffuse-transmission": diff,
                "specular-transmission": spec,
            }
        elif normalized_recipe == "leed-daylight-option-two":
            glare_devices = str(
                _opt("glare_control_devices", glare_control_devices, "glare-control")
            )
            if glare_devices not in {"glare-control", "no-glare-control"}:
                raise ValueError(
                    "glare_control_devices must be 'glare-control' or 'no-glare-control'."
                )
            compliance_options = {"glare-control-devices": glare_devices}
        elif normalized_recipe == "annual-daylight-en17037":
            compliance_options = {
                "grid-metrics": _normalize_grid_metrics(_opt("grid_metrics", grid_metrics)),
                "thresholds": _opt("thresholds", thresholds),
            }
        result = start_radiance_compliance_run(
            garden_root=garden_root,
            recipe_name=normalized_recipe,
            model_target=model_target,
            wea_target=wea_target,
            wea_path=wea_path,
            weather_file_target=weather_file_target,
            grid_filter=resolved_grid_filter,
            north=north,
            min_sensor_count=min_sensor_count,
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            debug_folder=debug_folder,
            recipe_options=compliance_options or None,
        )

    if wait_seconds is not None and wait_seconds > 0:
        interval = max(float(poll_interval or 1.0), 0.2)
        deadline = time.monotonic() + float(wait_seconds)
        run_target = result.get("run_target") or result.get("target")
        resolved_run_id = result.get("run_id")
        while result.get("status") in {"queued", "running"} and time.monotonic() < deadline:
            remaining = max(deadline - time.monotonic(), 0.0)
            if remaining <= 0:
                break
            time.sleep(min(interval, remaining))
            result = get_radiance_run(
                garden_root=garden_root,
                run_target=run_target,
                run_id=resolved_run_id,
            )
        result.setdefault("summary_view", {})["wait_seconds_requested"] = wait_seconds
    return result
