"""Garden-backed Honeybee Energy SimulationParameter services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from honeybee_energy.simulation.control import SimulationControl
from honeybee_energy.simulation.daylightsaving import DaylightSavingTime
from honeybee_energy.simulation.output import SimulationOutput
from honeybee_energy.simulation.parameter import (
    RunPeriod,
    ShadowCalculation,
    SimulationParameter,
    SizingParameter,
)
from ladybug.designday import DesignDay
from ladybug.dt import Date

from garden.manifest import GardenManifest, write_json_file
from garden.paths import slugify_name, to_posix_relative
from ladybug_tools_mcp.contracts import make_persistence_receipt, make_report


ENERGY_PARAMETER_TARGET_TYPE = "simulation_parameter"
ENERGY_PARAMETER_DOMAIN = "honeybee_energy"
ENERGY_PARAMETER_ARTIFACT_TYPE = "simulation_parameter"
ENERGY_PARAMETER_DIR = Path("artifacts") / "energy" / "parameters"

_RUN_PERIOD_FIELDS = {
    "type",
    "start_month",
    "start_day",
    "end_month",
    "end_day",
    "start_date",
    "end_date",
    "start_day_of_week",
    "leap_year",
    "holidays",
    "daylight_saving_time",
}
_SIMULATION_CONTROL_FIELDS = {
    "type",
    "do_zone_sizing",
    "do_system_sizing",
    "do_plant_sizing",
    "run_for_sizing_periods",
    "run_for_run_periods",
}
_DAYLIGHT_SAVING_FIELDS = {
    "type",
    "start_date",
    "end_date",
    "start_month",
    "start_day",
    "end_month",
    "end_day",
    "leap_year",
}
_SIZING_FIELDS = {
    "heating_factor",
    "cooling_factor",
    "efficiency_standard",
    "climate_zone",
    "building_type",
    "bypass_efficiency_sizing",
}
_SHADOW_FIELDS = {
    "solar_distribution",
    "calculation_method",
    "calculation_update_method",
    "calculation_frequency",
    "maximum_figures",
}
_TERRAIN_TYPES = {item.lower(): item for item in SimulationParameter.TERRAIN_TYPES}
_DESIGN_DAY_ALIASES = {
    "all": "all",
    "heating": "heating",
    "winter": "heating",
    "cooling": "cooling",
    "summer": "cooling",
    "heating_99.6": "heating_99.6",
    "99.6": "heating_99.6",
    "99.6%": "heating_99.6",
    "heating_99": "heating_99",
    "99": "heating_99",
    "99%": "heating_99",
    "cooling_0.4": "cooling_0.4",
    "0.4": "cooling_0.4",
    "0.4%": "cooling_0.4",
    "cooling_1": "cooling_1",
    "1": "cooling_1",
    "1%": "cooling_1",
    "99.6/0.4": "99.6/0.4",
    "99.6%/0.4%": "99.6/0.4",
    "99/1": "99/1",
    "99%/1%": "99/1",
}
_DESIGN_DAY_SELECTORS = {
    "all": ("add_from_ddy", None),
    "heating": ("add_from_ddy_keyword", "Htg"),
    "cooling": ("add_from_ddy_keyword", "Clg"),
    "heating_99.6": ("add_from_ddy_keyword", "Htg 99.6%"),
    "heating_99": ("add_from_ddy_keyword", "Htg 99%"),
    "cooling_0.4": ("add_from_ddy_keyword", "Clg .4%"),
    "cooling_1": ("add_from_ddy_keyword", "Clg 1%"),
}


def create_simulation_parameter(
    *,
    garden_root: str,
    identifier: str | None = None,
    run_period: dict[str, Any] | None = None,
    design_days: list[str | dict[str, Any]] | str | dict[str, Any] | None = None,
    sizing: dict[str, Any] | None = None,
    shadow_calculation: dict[str, Any] | None = None,
    timestep: int | None = None,
    north_angle: float | None = None,
    terrain_type: str | None = None,
    simulation_control: dict[str, Any] | None = None,
    holidays: list[Any] | None = None,
    daylight_saving_time: dict[str, Any] | None = None,
    output_request_target: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist an SDK SimulationParameter target."""
    root = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(root)
    strategies, direct_design_days = _split_design_days(design_days)
    parameter = _build_parameter(
        run_period=run_period,
        sizing=sizing,
        shadow_calculation=shadow_calculation,
        timestep=timestep,
        north_angle=north_angle,
        terrain_type=terrain_type,
        simulation_control=simulation_control,
        holidays=holidays,
        daylight_saving_time=daylight_saving_time,
        direct_design_days=direct_design_days,
        output_request_target=output_request_target,
        garden_root=root,
    )
    embedded_count = len(parameter.sizing_parameter.design_days)
    design_day_resolution: dict[str, Any] = {
        "status": (
            "embedded"
            if embedded_count and not strategies
            else ("pending_weather_ddy" if strategies else "not_requested")
        ),
        "strategies": list(strategies),
        "resolved_count": embedded_count,
    }
    if embedded_count:
        design_day_resolution["resolved_names_sample"] = [
            day.name for day in parameter.sizing_parameter.design_days[:5]
        ]
    if strategies and weather_target is not None:
        parameter, design_day_resolution = resolve_simulation_parameter_design_days(
            parameter,
            design_day_strategies=strategies,
            ddy_path=_ddy_path_from_weather_target(root, manifest, weather_target),
        )

    identifier_value = slugify_name(identifier or "simulation_parameter").replace(
        "-", "_"
    )
    output_path = root / ENERGY_PARAMETER_DIR / f"{identifier_value}.json"
    object_dict = parameter.to_dict()
    write_json_file(output_path, object_dict, ensure_ascii=False)
    target = make_simulation_parameter_target(
        garden_id=manifest.garden_id,
        identifier=identifier_value,
        path=to_posix_relative(output_path, root),
        design_day_strategies=strategies,
        output_request_target=output_request_target,
    )
    artifact = {
        "target_type": "artifact",
        "garden_id": manifest.garden_id,
        "domain": ENERGY_PARAMETER_DOMAIN,
        "artifact_type": ENERGY_PARAMETER_ARTIFACT_TYPE,
        "identifier": identifier_value,
        "path": target["path"],
        "source": target,
    }
    manifest.upsert_artifact(artifact, key_fields=("artifact_type", "identifier"))
    manifest.write(root)

    result: dict[str, Any] = {
        "target": target,
        "simulation_parameter_target": target,
        "summary_view": {
            "garden_target": manifest.target(),
            **_parameter_summary(object_dict),
            "target": target,
            "design_day_resolution": design_day_resolution,
            "body_returned": include_body,
        },
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            persisted_path=target["path"],
            change_summary={
                "operation": "create_simulation_parameter",
                "target": target,
                "design_day_resolution": design_day_resolution,
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Created Energy SimulationParameter: {identifier_value}.",
        ),
    }
    if include_body:
        result["object_dict"] = object_dict
    return result


def make_simulation_parameter_target(
    *,
    garden_id: str,
    identifier: str,
    path: str,
    design_day_strategies: list[str] | tuple[str, ...] = (),
    output_request_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a persisted SimulationParameter target."""
    target: dict[str, Any] = {
        "target_type": ENERGY_PARAMETER_TARGET_TYPE,
        "garden_id": garden_id,
        "domain": ENERGY_PARAMETER_DOMAIN,
        "identifier": identifier,
        "path": path,
    }
    if design_day_strategies:
        target["design_day_strategies"] = list(design_day_strategies)
    if output_request_target is not None:
        target["output_request_target"] = output_request_target
    return target


def load_simulation_parameter(
    *,
    garden_root: Path,
    simulation_parameter_target: dict[str, Any] | None = None,
    sim_par: dict[str, Any] | None = None,
) -> tuple[SimulationParameter | None, dict[str, Any] | None, dict[str, Any] | None]:
    """Resolve a persisted target or the existing inline dictionary."""
    if simulation_parameter_target is not None and sim_par is not None:
        raise ValueError(
            "Pass either simulation_parameter_target or sim_par, not both."
        )
    if simulation_parameter_target is None:
        if sim_par is None:
            return None, None, None
        parameter = SimulationParameter.from_dict(sim_par)
        return parameter, None, parameter.to_dict()

    root = garden_root.expanduser().resolve()
    manifest = GardenManifest.read(root)
    target = _normalize_target(simulation_parameter_target, manifest.garden_id)
    path = _resolve_parameter_path(root, str(target["path"]))
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("type") != "SimulationParameter":
        raise ValueError("Simulation parameter file must contain a SimulationParameter object.")
    target = _target_with_manifest_metadata(target, manifest)
    parameter = SimulationParameter.from_dict(data)
    return parameter, target, parameter.to_dict()


def resolve_simulation_parameter_design_days(
    parameter: SimulationParameter,
    *,
    design_day_strategies: list[str] | tuple[str, ...],
    ddy_path: str | Path,
) -> tuple[SimulationParameter, dict[str, Any]]:
    """Resolve task-level design-day strategies against one weather DDY file."""
    path = Path(ddy_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(
            "A valid DDY file is required to resolve simulation parameter design_days."
        )
    sizing = parameter.sizing_parameter.duplicate()
    missing: list[str] = []
    for strategy in design_day_strategies:
        method_name, keyword = _DESIGN_DAY_SELECTORS.get(strategy, (None, None))
        if method_name is None:
            missing.append(strategy)
            continue
        before = len(sizing.design_days)
        method = getattr(sizing, method_name)
        if keyword is None:
            method(str(path))
        else:
            method(str(path), keyword)
        if len(sizing.design_days) == before:
            missing.append(strategy)
    selected = list({day.name: day for day in sizing.design_days}.values())
    if missing or not selected:
        raise ValueError(
            "DDY cannot satisfy simulation parameter design_days strategy "
            f"{missing or list(design_day_strategies)}. Choose "
            "all, heating, cooling, heating_99.6, heating_99, cooling_0.4, or cooling_1."
        )

    sizing.design_days = selected
    parameter.sizing_parameter = sizing
    return parameter, {
        "status": "resolved",
        "strategies": list(design_day_strategies),
        "resolved_count": len(selected),
        "resolved_names_sample": [day.name for day in selected[:5]],
        "ddy_path": str(path),
    }


def _build_parameter(
    *,
    run_period: dict[str, Any] | None,
    sizing: dict[str, Any] | None,
    shadow_calculation: dict[str, Any] | None,
    timestep: int | None,
    north_angle: float | None,
    terrain_type: str | None,
    simulation_control: dict[str, Any] | None,
    holidays: list[Any] | None,
    daylight_saving_time: dict[str, Any] | None,
    direct_design_days: list[DesignDay],
    output_request_target: dict[str, Any] | None,
    garden_root: Path,
) -> SimulationParameter:
    kwargs: dict[str, Any] = {}
    if run_period is not None or holidays is not None or daylight_saving_time is not None:
        kwargs["run_period"] = _run_period_from_input(
            run_period,
            holidays=holidays,
            daylight_saving_time=daylight_saving_time,
        )
    if sizing is not None or direct_design_days:
        sizing_obj = _sizing_from_input(sizing) if sizing is not None else SizingParameter()
        for design_day in direct_design_days:
            sizing_obj.add_design_day(design_day)
        kwargs["sizing_parameter"] = sizing_obj
    if shadow_calculation is not None:
        kwargs["shadow_calculation"] = _shadow_from_input(shadow_calculation)
    if timestep is not None:
        if isinstance(timestep, bool) or not isinstance(timestep, int) or timestep not in SimulationParameter.VALIDTIMESTEPS:
            raise ValueError(
                f"Unsupported timestep: {timestep!r}. Allowed: {SimulationParameter.VALIDTIMESTEPS}."
            )
        kwargs["timestep"] = timestep
    if north_angle is not None:
        if isinstance(north_angle, bool) or not isinstance(north_angle, (int, float)):
            raise ValueError("north_angle must be a number between -360 and 360.")
        angle = float(north_angle)
        if not (-360.0 <= angle <= 360.0):
            raise ValueError("north_angle must be between -360 and 360.")
        kwargs["north_angle"] = angle
    if terrain_type is not None:
        if not isinstance(terrain_type, str) or not terrain_type.strip():
            raise ValueError("terrain_type must be a non-empty string.")
        canonical_terrain = _TERRAIN_TYPES.get(terrain_type.strip().lower())
        if canonical_terrain is None:
            raise ValueError(
                f"Unsupported terrain_type: {terrain_type!r}. "
                f"Allowed: {', '.join(SimulationParameter.TERRAIN_TYPES)}."
            )
        kwargs["terrain_type"] = canonical_terrain
    if simulation_control is not None:
        kwargs["simulation_control"] = _simulation_control_from_input(simulation_control)
    if output_request_target is not None:
        from garden.run_energy.output_requests import read_energy_output_request

        payload = read_energy_output_request(
            garden_root=garden_root,
            output_request_target=output_request_target,
        )
        kwargs["output"] = SimulationOutput.from_dict(payload["simulation_output"])
    return SimulationParameter(**kwargs)


def _parse_date_input(value: Any, *, leap_year: bool, field_name: str) -> Date:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        month, day = int(value[0]), int(value[1])
        return Date(month, day, leap_year)
    if isinstance(value, dict):
        if "month" in value and "day" in value:
            return Date(int(value["month"]), int(value["day"]), leap_year)
    if isinstance(value, str):
        cleaned = value.strip()
        for sep in ("/", "-"):
            if sep in cleaned:
                parts = [part.strip() for part in cleaned.split(sep)]
                if len(parts) == 2:
                    return Date(int(parts[0]), int(parts[1]), leap_year)
    raise ValueError(
        f"{field_name} entries must be [month, day], {{month, day}}, or 'MM/DD'."
    )


def _holidays_from_input(value: Any, *, leap_year: bool) -> tuple[Date, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("holidays must be a list of [month, day] dates.")
    return tuple(
        _parse_date_input(item, leap_year=leap_year, field_name="holidays")
        for item in value
    )


def _daylight_saving_from_input(
    value: Any, *, leap_year: bool
) -> DaylightSavingTime:
    _check_fields(value, _DAYLIGHT_SAVING_FIELDS, "daylight_saving_time")
    if value.get("type") is not None and value.get("type") != "DaylightSavingTime":
        raise ValueError("daylight_saving_time type must be 'DaylightSavingTime'.")
    dst_leap = bool(value.get("leap_year", leap_year))
    if "start_date" in value and value["start_date"] is not None:
        start_date = _parse_date_input(
            value["start_date"], leap_year=leap_year, field_name="daylight_saving_time.start_date"
        )
    elif "start_month" in value or "start_day" in value:
        if "start_month" not in value or "start_day" not in value:
            raise ValueError("daylight_saving_time requires both start_month and start_day.")
        start_date = Date(int(value["start_month"]), int(value["start_day"]), leap_year)
    else:
        start_date = Date(3, 12, leap_year)

    if "end_date" in value and value["end_date"] is not None:
        end_date = _parse_date_input(
            value["end_date"], leap_year=leap_year, field_name="daylight_saving_time.end_date"
        )
    elif "end_month" in value or "end_day" in value:
        if "end_month" not in value or "end_day" not in value:
            raise ValueError("daylight_saving_time requires both end_month and end_day.")
        end_date = Date(int(value["end_month"]), int(value["end_day"]), leap_year)
    else:
        end_date = Date(11, 5, leap_year)
    if dst_leap != leap_year:
        start_date = Date(start_date.month, start_date.day, leap_year)
        end_date = Date(end_date.month, end_date.day, leap_year)
    return DaylightSavingTime(start_date, end_date)


def _simulation_control_from_input(value: dict[str, Any]) -> SimulationControl:
    _check_fields(value, _SIMULATION_CONTROL_FIELDS, "simulation_control")
    if value.get("type") is not None and value.get("type") != "SimulationControl":
        raise ValueError("simulation_control type must be 'SimulationControl'.")
    kwargs = {key: bool(val) for key, val in value.items() if key != "type"}
    return SimulationControl(**kwargs)


def _run_period_from_input(
    value: dict[str, Any] | None,
    *,
    holidays: list[Any] | None = None,
    daylight_saving_time: dict[str, Any] | None = None,
) -> RunPeriod:
    data = dict(value or {})
    if value is not None:
        _check_fields(data, _RUN_PERIOD_FIELDS, "run_period")
        if data.get("type") is not None and data.get("type") != "RunPeriod":
            raise ValueError("run_period type must be 'RunPeriod'.")
    if holidays is not None and data.get("holidays") is not None:
        raise ValueError("Pass holidays either at top level or inside run_period, not both.")
    if daylight_saving_time is not None and data.get("daylight_saving_time") is not None:
        raise ValueError(
            "Pass daylight_saving_time either at top level or inside run_period, not both."
        )

    leap_year = bool(data.get("leap_year", False))
    if value is None:
        start_date = Date(1, 1, leap_year)
        end_date = Date(12, 31, leap_year)
    else:
        if "start_date" in data and data["start_date"] is not None:
            start_date = _parse_date_input(
                data["start_date"], leap_year=leap_year, field_name="run_period.start_date"
            )
        else:
            if "start_month" not in data or "start_day" not in data:
                raise ValueError("run_period requires: start_month, start_day.")
            start_date = Date(int(data["start_month"]), int(data["start_day"]), leap_year)
        if "end_date" in data and data["end_date"] is not None:
            end_date = _parse_date_input(
                data["end_date"], leap_year=leap_year, field_name="run_period.end_date"
            )
        else:
            if "end_month" not in data or "end_day" not in data:
                raise ValueError("run_period requires: end_month, end_day.")
            end_date = Date(int(data["end_month"]), int(data["end_day"]), leap_year)

    raw_holidays = holidays if holidays is not None else data.get("holidays")
    parsed_holidays = (
        _holidays_from_input(raw_holidays, leap_year=leap_year)
        if raw_holidays is not None
        else None
    )
    raw_dst = (
        daylight_saving_time
        if daylight_saving_time is not None
        else data.get("daylight_saving_time")
    )
    parsed_dst = (
        _daylight_saving_from_input(raw_dst, leap_year=leap_year)
        if raw_dst is not None
        else None
    )
    return RunPeriod(
        start_date,
        end_date,
        str(data.get("start_day_of_week", "Sunday")),
        holidays=parsed_holidays,
        daylight_saving_time=parsed_dst,
    )


def _sizing_from_input(value: dict[str, Any]) -> SizingParameter:
    _check_fields(value, _SIZING_FIELDS, "sizing")
    return SizingParameter(**value)


def _shadow_from_input(value: dict[str, Any]) -> ShadowCalculation:
    _check_fields(value, _SHADOW_FIELDS, "shadow_calculation")
    return ShadowCalculation(**value)


def _check_fields(value: Any, allowed: set[str], field_name: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a dictionary.")
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(
            f"{field_name} contains unsupported field(s): {', '.join(unknown)}."
        )


def _split_design_days(
    value: list[str | dict[str, Any]] | str | dict[str, Any] | None,
) -> tuple[list[str], list[DesignDay]]:
    if value is None:
        return [], []
    items = [value] if isinstance(value, (str, dict)) else value
    if not isinstance(items, (list, tuple)):
        raise ValueError(
            "design_days must be a strategy string, a DesignDay dictionary, or a list of those."
        )
    strategy_inputs: list[str] = []
    direct_days: list[DesignDay] = []
    for item in items:
        if isinstance(item, str):
            strategy_inputs.append(item)
        elif isinstance(item, dict):
            try:
                direct_days.append(DesignDay.from_dict(item))
            except Exception as exc:
                raise ValueError(f"Invalid DesignDay dictionary in design_days: {exc}") from exc
        else:
            raise ValueError(
                "Each entry in design_days must be a strategy string or DesignDay dictionary."
            )
    strategies = _normalize_design_days(strategy_inputs) if strategy_inputs else []
    return strategies, direct_days


def _normalize_design_days(value: list[str] | str | None) -> list[str]:
    if value is None:
        return []
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise ValueError("design_days must be a string or a list of strategy strings.")
    normalized: list[str] = []
    for item in values:
        key = item.strip().lower().replace(" ", "_").replace("-", "_")
        strategy = _DESIGN_DAY_ALIASES.get(key)
        if strategy is None:
            allowed = ", ".join(sorted(set(_DESIGN_DAY_ALIASES.values())))
            raise ValueError(f"Unsupported design_days strategy {item!r}. Allowed: {allowed}.")
        if strategy == "99.6/0.4":
            normalized.extend(("heating_99.6", "cooling_0.4"))
        elif strategy == "99/1":
            normalized.extend(("heating_99", "cooling_1"))
        elif strategy not in normalized:
            normalized.append(strategy)
    return normalized


def _normalize_target(value: Any, garden_id: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("simulation_parameter_target must be a dictionary.")
    if value.get("target_type") != ENERGY_PARAMETER_TARGET_TYPE:
        raise ValueError(
            "simulation_parameter_target must have target_type "
            f"{ENERGY_PARAMETER_TARGET_TYPE!r}."
        )
    if value.get("domain") != ENERGY_PARAMETER_DOMAIN:
        raise ValueError(
            "simulation_parameter_target must have domain "
            f"{ENERGY_PARAMETER_DOMAIN!r}."
        )
    if value.get("garden_id") != garden_id:
        raise ValueError("simulation_parameter_target belongs to a different Garden.")
    if not isinstance(value.get("path"), str) or not value["path"]:
        raise ValueError("simulation_parameter_target requires a Garden-relative path.")
    return dict(value)


def _resolve_parameter_path(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError("simulation_parameter_target path must be Garden-relative.")
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("simulation_parameter_target path must stay inside the Garden.") from exc
    if not resolved.is_file():
        raise ValueError(f"Simulation parameter file not found: {value}")
    return resolved


def _target_with_manifest_metadata(
    target: dict[str, Any], manifest: GardenManifest
) -> dict[str, Any]:
    if target.get("design_day_strategies") and target.get("output_request_target"):
        return target
    for artifact in manifest.artifacts:
        if artifact.get("artifact_type") != ENERGY_PARAMETER_ARTIFACT_TYPE:
            continue
        if artifact.get("identifier") != target.get("identifier") and artifact.get(
            "path"
        ) != target.get("path"):
            continue

        source = artifact.get("source")
        if isinstance(source, dict):
            if source.get("design_day_strategies"):
                target["design_day_strategies"] = list(source["design_day_strategies"])
            if source.get("output_request_target"):
                target["output_request_target"] = source["output_request_target"]
        if target.get("design_day_strategies") or target.get("output_request_target"):
            break
    return target


def _parameter_summary(data: dict[str, Any]) -> dict[str, Any]:
    sizing = data.get("sizing_parameter") or {}
    shadow = data.get("shadow_calculation") or {}
    return {
        "type": data.get("type"),
        "timestep": data.get("timestep"),
        "north_angle": data.get("north_angle"),
        "terrain_type": data.get("terrain_type"),
        "simulation_control": data.get("simulation_control"),
        "run_period": data.get("run_period"),
        "sizing": {
            "heating_factor": sizing.get("heating_factor"),
            "cooling_factor": sizing.get("cooling_factor"),
            "design_day_count": len(sizing.get("design_days") or []),
        },
        "shadow_calculation": {
            "solar_distribution": shadow.get("solar_distribution"),
            "calculation_method": shadow.get("calculation_method"),
            "calculation_update_method": shadow.get("calculation_update_method"),
        },
        "output_count": len((data.get("output") or {}).get("outputs") or []),
    }


def _ddy_path_from_weather_target(
    root: Path, manifest: GardenManifest, weather_target: dict[str, Any]
) -> Path:
    if not isinstance(weather_target, dict) or weather_target.get("target_type") != "weather_file":
        raise ValueError("weather_target must be a weather_file target.")
    if weather_target.get("garden_id") != manifest.garden_id:
        raise ValueError("weather_target belongs to a different Garden.")
    value = weather_target.get("ddy_path")
    if not isinstance(value, str) or not value:
        raise ValueError("weather_target requires ddy_path to resolve design_days.")
    path = Path(value)
    if path.is_absolute():
        raise ValueError("weather_target ddy_path must be Garden-relative.")
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("weather_target ddy_path must stay inside the Garden.") from exc
    if not resolved.is_file():
        raise ValueError(f"Weather DDY file not found: {value}")
    return resolved
