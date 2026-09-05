"""Garden-backed Honeybee Energy SimulationParameter services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from honeybee_energy.simulation.output import SimulationOutput
from honeybee_energy.simulation.parameter import (
    RunPeriod,
    ShadowCalculation,
    SimulationParameter,
    SizingParameter,
)
from ladybug.dt import Date

from garden.manifest import GardenManifest, write_json_file
from garden.paths import slugify_name, to_posix_relative
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report


ENERGY_PARAMETER_TARGET_TYPE = "simulation_parameter"
ENERGY_PARAMETER_DOMAIN = "honeybee_energy"
ENERGY_PARAMETER_ARTIFACT_TYPE = "simulation_parameter"
ENERGY_PARAMETER_DIR = Path("artifacts") / "energy" / "parameters"

_RUN_PERIOD_FIELDS = {
    "start_month",
    "start_day",
    "end_month",
    "end_day",
    "start_day_of_week",
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
    design_days: list[str] | str | None = None,
    sizing: dict[str, Any] | None = None,
    shadow_calculation: dict[str, Any] | None = None,
    output_request_target: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and persist an SDK SimulationParameter target."""
    root = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(root)
    strategies = _normalize_design_days(design_days)
    parameter = _build_parameter(
        run_period=run_period,
        sizing=sizing,
        shadow_calculation=shadow_calculation,
        output_request_target=output_request_target,
        garden_root=root,
    )
    design_day_resolution = {
        "status": "not_requested" if not strategies else "pending_weather_ddy",
        "strategies": list(strategies),
        "resolved_count": len(parameter.sizing_parameter.design_days),
    }
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
    output_request_target: dict[str, Any] | None,
    garden_root: Path,
) -> SimulationParameter:
    kwargs: dict[str, Any] = {}
    if run_period is not None:
        kwargs["run_period"] = _run_period_from_input(run_period)
    if sizing is not None:
        kwargs["sizing_parameter"] = _sizing_from_input(sizing)
    if shadow_calculation is not None:
        kwargs["shadow_calculation"] = _shadow_from_input(shadow_calculation)
    if output_request_target is not None:
        from garden.run_energy.output_requests import read_energy_output_request

        payload = read_energy_output_request(
            garden_root=garden_root,
            output_request_target=output_request_target,
        )
        kwargs["output"] = SimulationOutput.from_dict(payload["simulation_output"])
    return SimulationParameter(**kwargs)


def _run_period_from_input(value: dict[str, Any]) -> RunPeriod:
    _check_fields(value, _RUN_PERIOD_FIELDS, "run_period")
    required = ("start_month", "start_day", "end_month", "end_day")
    missing = [name for name in required if name not in value]
    if missing:
        raise ValueError("run_period requires: " + ", ".join(missing) + ".")
    leap_year = bool(value.get("leap_year", False))
    return RunPeriod(
        Date(int(value["start_month"]), int(value["start_day"]), leap_year),
        Date(int(value["end_month"]), int(value["end_day"]), leap_year),
        str(value.get("start_day_of_week", "Sunday")),
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
