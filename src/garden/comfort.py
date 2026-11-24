"""Garden-backed Ladybug thermal comfort calculations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ladybug.analysisperiod import AnalysisPeriod
from ladybug.datacollection import HourlyContinuousCollection
from ladybug.datatype.rvalue import ClothingInsulation
from ladybug.datatype.temperature import Temperature
from ladybug.datatype.temperaturetime import CoolingDegreeTime
from ladybug.epw import EPW
from ladybug.header import Header
from ladybug.location import Location
from ladybug_geometry.geometry3d import Face3D, Mesh3D, Point3D

from garden.data_collection import (
    DATA_COLLECTION_TARGET_TYPE,
    collection_from_dict,
    data_collection_summary,
    load_data_collection,
    save_data_collection,
)
from garden.manifest import GardenManifest
from garden.passive_strategy import (
    STRATEGY_DISPLAY_NAMES,
    PassiveStrategyParameters,
    evaluate_pmv_passive_strategies,
    normalize_passive_strategies,
    summarize_polygon_numeric_input,
)
from garden.ray_intersect import compute_human_to_sky_relation
from garden.run_energy.config import resolve_garden_weather_epw
from ladybug_tools_mcp.contracts import make_report


_METRIC_ALIASES = {
    "pmv": "predicted_mean_vote",
    "ppd": "percentage_people_dissatisfied",
    "set": "standard_effective_temperature",
    "utci": "universal_thermal_climate_index",
    "pet": "physiologic_equivalent_temperature",
    "mrt": "mean_radiant_temperature",
    "erf": "effective_radiant_field",
    "dmrt": "mrt_delta",
    "short_erf": "shortwave_effective_radiant_field",
    "long_erf": "longwave_effective_radiant_field",
    "short_dmrt": "shortwave_mrt_delta",
    "long_dmrt": "longwave_mrt_delta",
    "eleven_point": "thermal_condition_eleven_point",
    "nine_point": "thermal_condition_nine_point",
    "seven_point": "thermal_condition_seven_point",
    "five_point": "thermal_condition_five_point",
}


def _load_required_collection(
    *,
    garden_root: str | Path,
    target: dict[str, Any] | None,
    field_name: str,
) -> Any:
    if not isinstance(target, dict):
        raise ValueError(f"{field_name} must be a ladybug_data_collection target.")
    if target.get("target_type") == DATA_COLLECTION_TARGET_TYPE:
        try:
            collection = load_data_collection(
                garden_root=garden_root,
                data_collection_target=target,
            )
        except (OSError, TypeError, ValueError) as exc:
            raise ValueError(f"Could not load {field_name}: {exc}") from exc
    elif "values" in target and "header" in target:
        collection = collection_from_dict(target)
    else:
        raise ValueError(
            f"{field_name}.target_type must be {DATA_COLLECTION_TARGET_TYPE!r}."
        )
    if not getattr(collection, "values", None):
        raise ValueError(f"{field_name} must contain at least one value.")
    return collection


def _load_optional_input(
    *,
    garden_root: str | Path,
    value: dict[str, Any] | float | int | None,
    field_name: str,
) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return _load_required_collection(
            garden_root=garden_root,
            target=value,
            field_name=field_name,
        )
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number or DataCollection target.")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number or DataCollection target.") from exc


def _load_parameter(
    parameter: dict[str, Any] | None,
    *,
    expected_type: str,
    parameter_cls: type[Any],
) -> Any:
    if parameter is None:
        return None
    if not isinstance(parameter, dict):
        raise ValueError(f"comfort_parameter must be a {expected_type} dictionary.")
    data = dict(parameter)
    if "type" not in data or data.get("type") is None:
        data["type"] = expected_type
    elif data.get("type") != expected_type:
        raise ValueError(
            f"comfort_parameter.type must be {expected_type!r}; "
            f"got {data.get('type')!r}."
        )
    try:
        return parameter_cls.from_dict(data)
    except (AssertionError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {expected_type}: {exc}") from exc


def _resolve_epw_object(
    *,
    garden_root: str | Path,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
) -> EPW:
    root = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(root)
    if weather_target is not None:
        epw_file = resolve_garden_weather_epw(
            garden_root=root,
            manifest=manifest,
            weather_target=weather_target,
        )
        return EPW(str(epw_file))
    if epw_path:
        raw = Path(epw_path).expanduser()
        candidate = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
        candidate.relative_to(root)
        if not candidate.is_file() or candidate.suffix.lower() != ".epw":
            raise ValueError(f"epw_path must reference an existing .epw inside Garden: {epw_path}")
        return EPW(str(candidate))
    raise ValueError("Provide weather_target or epw_path.")


def _resolve_metric_collection(comfort: Any, metric_name: str, comfort_model: str) -> Any:
    attr_name = _METRIC_ALIASES.get(metric_name.strip().lower(), metric_name.strip())
    if attr_name == "effective_radiant_field" and not hasattr(comfort, attr_name):
        if hasattr(comfort, "shortwave_effective_radiant_field") and hasattr(
            comfort, "longwave_effective_radiant_field"
        ):
            return comfort.shortwave_effective_radiant_field + comfort.longwave_effective_radiant_field
    if not hasattr(comfort, attr_name):
        raise ValueError(
            f"Metric {metric_name!r} (resolved as {attr_name!r}) is not available on {comfort_model}."
        )
    return getattr(comfort, attr_name)


def _comfort_percentages(comfort: Any, comfort_model: str) -> dict[str, Any]:
    percentages: dict[str, Any] = {}
    for key, attr in (
        ("comfortable", "percent_comfortable"),
        ("uncomfortable", "percent_uncomfortable"),
        ("neutral", "percent_neutral"),
        ("cold", "percent_cold"),
        ("hot", "percent_hot"),
    ):
        try:
            percentages[key] = getattr(comfort, attr)
        except (AttributeError, NotImplementedError):
            pass
    if comfort_model == "UTCI":
        for attr in (
            "percent_extreme_cold_stress",
            "percent_very_strong_cold_stress",
            "percent_strong_cold_stress",
            "percent_moderate_cold_stress",
            "percent_slight_cold_stress",
            "percent_slight_heat_stress",
            "percent_moderate_heat_stress",
            "percent_strong_heat_stress",
            "percent_very_strong_heat_stress",
            "percent_extreme_heat_stress",
        ):
            try:
                percentages[attr.removeprefix("percent_")] = getattr(comfort, attr)
            except (AttributeError, NotImplementedError):
                pass
    return percentages


def _calculate(
    *,
    garden_root: str | Path,
    comfort_model: str,
    metric_name: str,
    metric_attribute: str,
    comfort: Any,
    input_targets: dict[str, Any],
    parameter: Any,
    identifier: str | None,
    producer: str,
    output_metrics: list[str] | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    parameter_dict = parameter.to_dict() if parameter is not None else None
    comfort_summary = _comfort_percentages(comfort, comfort_model)
    garden_target = GardenManifest.read(Path(garden_root).resolve()).target()

    requested_metrics = list(output_metrics) if output_metrics else [metric_attribute]
    persisted_by_name: dict[str, dict[str, Any]] = {}
    metric_summaries: dict[str, Any] = {}
    metric_objects: dict[str, Any] = {}

    for raw_metric in requested_metrics:
        metric = _resolve_metric_collection(comfort, raw_metric, comfort_model)
        if hasattr(metric, "duplicate"):
            metric = metric.duplicate()
        header = getattr(metric, "header", None)
        if header is not None:
            header.metadata.update(
                {
                    "source": "ladybug_comfort",
                    "comfort_model": comfort_model,
                    "comfort_metric": raw_metric,
                }
            )
        base_id = identifier or f"{comfort_model.lower()}_{metric_name}"
        result_identifier = (
            base_id
            if len(requested_metrics) == 1
            else f"{base_id}_{raw_metric.strip().lower()}"
        )
        saved = save_data_collection(
            garden_root=garden_root,
            data_collection=metric,
            identifier=result_identifier,
            source={
                "producer": producer,
                "comfort_model": comfort_model,
                "comfort_metric": raw_metric,
                "input_targets": input_targets,
                "comfort_parameter": parameter_dict,
            },
        )
        persisted_by_name[raw_metric] = saved
        metric_summaries[raw_metric] = data_collection_summary(metric)
        metric_objects[raw_metric] = metric

    primary_key = requested_metrics[0]
    primary_saved = persisted_by_name[primary_key]
    primary_summary = metric_summaries[primary_key]

    summary_view: dict[str, Any] = {
        "garden_target": garden_target,
        "comfort_model": comfort_model,
        "comfort_metric": metric_name if not output_metrics else primary_key,
        "input_targets": input_targets,
        "comfort_parameter": parameter_dict,
        "data_collection": primary_summary,
        "percentages": comfort_summary,
    }
    if comfort_model == "PMV":
        summary_view["percentage_people_dissatisfied"] = data_collection_summary(
            comfort.percentage_people_dissatisfied
        )
    if output_metrics:
        summary_view["output_metrics"] = metric_summaries
        summary_view["output_targets"] = {k: v["target"] for k, v in persisted_by_name.items()}

    result: dict[str, Any] = {
        "target": primary_saved["target"],
        "data_target": primary_saved["target"],
        "data_collection_target": primary_saved["target"],
        "artifact": primary_saved["artifact"],
        "persistence_receipt": primary_saved["persistence_receipt"],
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message=f"{comfort_model} comfort DataCollection persisted.",
        ),
    }
    if output_metrics:
        targets_map = {k: v["target"] for k, v in persisted_by_name.items()}
        result["targets"] = targets_map
        result["data_collection_targets"] = targets_map
        result["artifacts"] = {k: v["artifact"] for k, v in persisted_by_name.items()}
        result["persistence_receipts"] = {
            k: v["persistence_receipt"] for k, v in persisted_by_name.items()
        }
    if return_data_collection:
        result["data_collection"] = metric_objects[primary_key].to_dict()
        if output_metrics:
            result["data_collections"] = {k: obj.to_dict() for k, obj in metric_objects.items()}
    return result


def calculate_utci(
    *,
    garden_root: str,
    air_temperature_target: dict[str, Any] | None = None,
    relative_humidity_target: dict[str, Any] | None = None,
    mean_radiant_temperature_target: dict[str, Any] | None = None,
    wind_speed_target: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    include_wind: bool = True,
    include_sun: bool = True,
    comfort_parameter: dict[str, Any] | None = None,
    output_metrics: list[str] | None = None,
    identifier: str | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    """Calculate UTCI from Garden DataCollection targets or weather_target/epw_path."""
    from ladybug_comfort.collection.utci import UTCI
    from ladybug_comfort.parameter.utci import UTCIParameter

    parameter = _load_parameter(
        comfort_parameter,
        expected_type="UTCIParameter",
        parameter_cls=UTCIParameter,
    )
    if weather_target is not None or epw_path is not None:
        epw = _resolve_epw_object(
            garden_root=garden_root,
            weather_target=weather_target,
            epw_path=epw_path,
        )
        comfort = UTCI.from_epw(
            epw,
            include_wind=include_wind,
            include_sun=include_sun,
            utci_parameter=parameter,
        )
        input_targets = {
            "weather_target": weather_target,
            "epw_path": epw_path,
            "include_wind": include_wind,
            "include_sun": include_sun,
        }
    else:
        air_temperature = _load_required_collection(
            garden_root=garden_root,
            target=air_temperature_target,
            field_name="air_temperature_target",
        )
        relative_humidity = _load_required_collection(
            garden_root=garden_root,
            target=relative_humidity_target,
            field_name="relative_humidity_target",
        )
        rad_temperature = (
            _load_required_collection(
                garden_root=garden_root,
                target=mean_radiant_temperature_target,
                field_name="mean_radiant_temperature_target",
            )
            if mean_radiant_temperature_target is not None
            else None
        )
        wind_speed = (
            _load_required_collection(
                garden_root=garden_root,
                target=wind_speed_target,
                field_name="wind_speed_target",
            )
            if wind_speed_target is not None
            else None
        )
        try:
            comfort = UTCI(
                air_temperature,
                relative_humidity,
                rad_temperature=rad_temperature,
                wind_speed=wind_speed,
                comfort_parameter=parameter,
            )
        except (AssertionError, TypeError, ValueError) as exc:
            raise ValueError(f"Could not calculate UTCI comfort: {exc}") from exc
        input_targets = {
            "air_temperature": air_temperature_target,
            "relative_humidity": relative_humidity_target,
            "mean_radiant_temperature": mean_radiant_temperature_target,
            "wind_speed": wind_speed_target,
        }
    return _calculate(
        garden_root=garden_root,
        comfort_model="UTCI",
        metric_name="universal_thermal_climate_index",
        metric_attribute="universal_thermal_climate_index",
        comfort=comfort,
        input_targets=input_targets,
        parameter=parameter,
        identifier=identifier,
        producer="LB_Calculate_Comfort",
        output_metrics=output_metrics,
        return_data_collection=return_data_collection,
    )


def calculate_adaptive(
    *,
    garden_root: str,
    outdoor_temperature_target: dict[str, Any],
    operative_temperature_target: dict[str, Any] | None = None,
    air_temperature_target: dict[str, Any] | None = None,
    mean_radiant_temperature_target: dict[str, Any] | None = None,
    air_speed_target: dict[str, Any] | None = None,
    comfort_parameter: dict[str, Any] | None = None,
    output_metrics: list[str] | None = None,
    identifier: str | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    """Calculate Adaptive comfort from Garden DataCollection targets."""
    from ladybug_comfort.collection.adaptive import Adaptive
    from ladybug_comfort.parameter.adaptive import AdaptiveParameter

    outdoor_temperature = _load_required_collection(
        garden_root=garden_root,
        target=outdoor_temperature_target,
        field_name="outdoor_temperature_target",
    )
    air_speed = (
        _load_required_collection(
            garden_root=garden_root,
            target=air_speed_target,
            field_name="air_speed_target",
        )
        if air_speed_target is not None
        else None
    )
    parameter = _load_parameter(
        comfort_parameter,
        expected_type="AdaptiveParameter",
        parameter_cls=AdaptiveParameter,
    )
    try:
        if operative_temperature_target is not None:
            operative_temperature = _load_required_collection(
                garden_root=garden_root,
                target=operative_temperature_target,
                field_name="operative_temperature_target",
            )
            comfort = Adaptive(
                outdoor_temperature,
                operative_temperature,
                air_speed=air_speed,
                comfort_parameter=parameter,
            )
        elif air_temperature_target is not None:
            air_temp = _load_required_collection(
                garden_root=garden_root,
                target=air_temperature_target,
                field_name="air_temperature_target",
            )
            rad_temp = (
                _load_required_collection(
                    garden_root=garden_root,
                    target=mean_radiant_temperature_target,
                    field_name="mean_radiant_temperature_target",
                )
                if mean_radiant_temperature_target is not None
                else None
            )
            comfort = Adaptive.from_air_and_rad_temp(
                outdoor_temperature,
                air_temp,
                rad_temperature=rad_temp,
                air_speed=air_speed,
                comfort_parameter=parameter,
            )
        else:
            raise ValueError(
                "Adaptive comfort requires operative_temperature_target or air_temperature_target."
            )
    except (AssertionError, TypeError, ValueError) as exc:
        raise ValueError(f"Could not calculate Adaptive comfort: {exc}") from exc
    return _calculate(
        garden_root=garden_root,
        comfort_model="Adaptive",
        metric_name="degrees_from_neutral",
        metric_attribute="degrees_from_neutral",
        comfort=comfort,
        input_targets={
            "outdoor_temperature": outdoor_temperature_target,
            "operative_temperature": operative_temperature_target,
            "air_temperature": air_temperature_target,
            "mean_radiant_temperature": mean_radiant_temperature_target,
            "air_speed": air_speed_target,
        },
        parameter=parameter,
        identifier=identifier,
        producer="LB_Calculate_Comfort",
        output_metrics=output_metrics,
        return_data_collection=return_data_collection,
    )


def calculate_pmv(
    *,
    garden_root: str,
    air_temperature_target: dict[str, Any] | None = None,
    relative_humidity_target: dict[str, Any] | None = None,
    mean_radiant_temperature_target: dict[str, Any] | None = None,
    air_speed: dict[str, Any] | float | int | None = None,
    met_rate: dict[str, Any] | float | int | None = None,
    clo_value: dict[str, Any] | float | int | None = None,
    external_work: dict[str, Any] | float | int | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    include_wind: bool = True,
    include_sun: bool = True,
    comfort_parameter: dict[str, Any] | None = None,
    output_metrics: list[str] | None = None,
    identifier: str | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    """Calculate PMV from Garden DataCollection targets or weather_target/epw_path."""
    from ladybug_comfort.collection.pmv import PMV
    from ladybug_comfort.parameter.pmv import PMVParameter

    resolved_met_rate = _load_optional_input(
        garden_root=garden_root,
        value=met_rate,
        field_name="met_rate",
    )
    resolved_clo_value = _load_optional_input(
        garden_root=garden_root,
        value=clo_value,
        field_name="clo_value",
    )
    resolved_external_work = _load_optional_input(
        garden_root=garden_root,
        value=external_work,
        field_name="external_work",
    )
    parameter = _load_parameter(
        comfort_parameter,
        expected_type="PMVParameter",
        parameter_cls=PMVParameter,
    )
    if weather_target is not None or epw_path is not None:
        epw = _resolve_epw_object(
            garden_root=garden_root,
            weather_target=weather_target,
            epw_path=epw_path,
        )
        comfort = PMV.from_epw(
            epw,
            include_wind=include_wind,
            include_sun=include_sun,
            met_rate=resolved_met_rate,
            clo_value=resolved_clo_value,
            external_work=resolved_external_work,
            pmv_parameter=parameter,
        )
        input_targets = {
            "weather_target": weather_target,
            "epw_path": epw_path,
            "include_wind": include_wind,
            "include_sun": include_sun,
            "met_rate": met_rate if isinstance(met_rate, dict) else None,
            "clo_value": clo_value if isinstance(clo_value, dict) else None,
            "external_work": external_work if isinstance(external_work, dict) else None,
        }
    else:
        air_temperature = _load_required_collection(
            garden_root=garden_root,
            target=air_temperature_target,
            field_name="air_temperature_target",
        )
        relative_humidity = _load_required_collection(
            garden_root=garden_root,
            target=relative_humidity_target,
            field_name="relative_humidity_target",
        )
        rad_temperature = (
            _load_required_collection(
                garden_root=garden_root,
                target=mean_radiant_temperature_target,
                field_name="mean_radiant_temperature_target",
            )
            if mean_radiant_temperature_target is not None
            else None
        )
        resolved_air_speed = _load_optional_input(
            garden_root=garden_root,
            value=air_speed,
            field_name="air_speed",
        )
        try:
            comfort = PMV(
                air_temperature,
                relative_humidity,
                rad_temperature=rad_temperature,
                air_speed=resolved_air_speed,
                met_rate=resolved_met_rate,
                clo_value=resolved_clo_value,
                external_work=resolved_external_work,
                comfort_parameter=parameter,
            )
        except (AssertionError, TypeError, ValueError) as exc:
            raise ValueError(f"Could not calculate PMV comfort: {exc}") from exc
        input_targets = {
            "air_temperature": air_temperature_target,
            "relative_humidity": relative_humidity_target,
            "mean_radiant_temperature": mean_radiant_temperature_target,
            "air_speed": air_speed if isinstance(air_speed, dict) else None,
            "met_rate": met_rate if isinstance(met_rate, dict) else None,
            "clo_value": clo_value if isinstance(clo_value, dict) else None,
            "external_work": external_work if isinstance(external_work, dict) else None,
        }
    return _calculate(
        garden_root=garden_root,
        comfort_model="PMV",
        metric_name="predicted_mean_vote",
        metric_attribute="predicted_mean_vote",
        comfort=comfort,
        input_targets=input_targets,
        parameter=parameter,
        identifier=identifier,
        producer="LB_Calculate_Comfort",
        output_metrics=output_metrics,
        return_data_collection=return_data_collection,
    )


def calculate_pet(
    *,
    garden_root: str,
    air_temperature_target: dict[str, Any] | None = None,
    relative_humidity_target: dict[str, Any] | None = None,
    mean_radiant_temperature_target: dict[str, Any] | None = None,
    air_speed: dict[str, Any] | float | int | None = None,
    barometric_pressure: dict[str, Any] | float | int | None = None,
    met_rate: dict[str, Any] | float | int | None = None,
    clo_value: dict[str, Any] | float | int | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    include_wind: bool = True,
    include_sun: bool = True,
    comfort_parameter: dict[str, Any] | None = None,
    output_metrics: list[str] | None = None,
    identifier: str | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    """Calculate Physiological Equivalent Temperature (PET) comfort."""
    from ladybug_comfort.collection.pet import PET
    from ladybug_comfort.parameter.pet import PETParameter

    resolved_met_rate = _load_optional_input(garden_root=garden_root, value=met_rate, field_name="met_rate")
    resolved_clo_value = _load_optional_input(garden_root=garden_root, value=clo_value, field_name="clo_value")
    parameter = _load_parameter(
        comfort_parameter,
        expected_type="PETParameter",
        parameter_cls=PETParameter,
    )
    if weather_target is not None or epw_path is not None:
        epw = _resolve_epw_object(
            garden_root=garden_root,
            weather_target=weather_target,
            epw_path=epw_path,
        )
        comfort = PET.from_epw(
            epw,
            include_wind=include_wind,
            include_sun=include_sun,
            met_rate=resolved_met_rate,
            clo_value=resolved_clo_value,
            body_parameter=parameter,
        )
        input_targets = {
            "weather_target": weather_target,
            "epw_path": epw_path,
            "include_wind": include_wind,
            "include_sun": include_sun,
        }
    else:
        air_temperature = _load_required_collection(
            garden_root=garden_root,
            target=air_temperature_target,
            field_name="air_temperature_target",
        )
        relative_humidity = _load_required_collection(
            garden_root=garden_root,
            target=relative_humidity_target,
            field_name="relative_humidity_target",
        )
        rad_temperature = (
            _load_required_collection(
                garden_root=garden_root,
                target=mean_radiant_temperature_target,
                field_name="mean_radiant_temperature_target",
            )
            if mean_radiant_temperature_target is not None
            else None
        )
        resolved_air_speed = _load_optional_input(garden_root=garden_root, value=air_speed, field_name="air_speed")
        resolved_pressure = _load_optional_input(
            garden_root=garden_root, value=barometric_pressure, field_name="barometric_pressure"
        )
        try:
            comfort = PET(
                air_temperature,
                relative_humidity,
                rad_temperature=rad_temperature,
                air_speed=resolved_air_speed,
                barometric_pressure=resolved_pressure,
                met_rate=resolved_met_rate,
                clo_value=resolved_clo_value,
                body_parameter=parameter,
            )
        except (AssertionError, TypeError, ValueError) as exc:
            raise ValueError(f"Could not calculate PET comfort: {exc}") from exc
        input_targets = {
            "air_temperature": air_temperature_target,
            "relative_humidity": relative_humidity_target,
            "mean_radiant_temperature": mean_radiant_temperature_target,
        }
    return _calculate(
        garden_root=garden_root,
        comfort_model="PET",
        metric_name="physiologic_equivalent_temperature",
        metric_attribute="physiologic_equivalent_temperature",
        comfort=comfort,
        input_targets=input_targets,
        parameter=parameter,
        identifier=identifier,
        producer="LB_Calculate_Comfort",
        output_metrics=output_metrics,
        return_data_collection=return_data_collection,
    )


def calculate_solarcal(
    *,
    garden_root: str,
    solarcal_type: str = "outdoor",
    location: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    direct_normal_solar_target: dict[str, Any] | None = None,
    diffuse_horizontal_solar_target: dict[str, Any] | None = None,
    direct_horizontal_solar_target: dict[str, Any] | None = None,
    reflected_horizontal_solar_target: dict[str, Any] | None = None,
    horizontal_infrared_target: dict[str, Any] | None = None,
    surface_temperatures: dict[str, Any] | float | int | None = None,
    longwave_mrt: dict[str, Any] | float | int | None = None,
    fraction_body_exposed: dict[str, Any] | float | int | None = None,
    sky_exposure: dict[str, Any] | float | int | None = None,
    floor_reflectance: dict[str, Any] | float | int | None = None,
    window_transmittance: dict[str, Any] | float | int | None = None,
    comfort_parameter: dict[str, Any] | None = None,
    output_metrics: list[str] | None = None,
    identifier: str | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    """Calculate Outdoor, Indoor, Horizontal, or HorizontalRef SolarCal MRT deltas."""
    from ladybug_comfort.collection.solarcal import (
        HorizontalRefSolarCal,
        HorizontalSolarCal,
        IndoorSolarCal,
        OutdoorSolarCal,
    )
    from ladybug_comfort.parameter.solarcal import SolarCalParameter

    sc_kind = str(solarcal_type or "outdoor").strip().lower()
    parameter = _load_parameter(
        comfort_parameter,
        expected_type="SolarCalParameter",
        parameter_cls=SolarCalParameter,
    )
    epw_obj = (
        _resolve_epw_object(garden_root=garden_root, weather_target=weather_target, epw_path=epw_path)
        if (weather_target is not None or epw_path is not None)
        else None
    )
    if location is not None:
        loc_data = dict(location)
        loc_data.setdefault("type", "Location")
        loc_obj = Location.from_dict(loc_data)
    elif epw_obj is not None:
        loc_obj = epw_obj.location
    else:
        raise ValueError("SolarCal requires location or weather_target/epw_path.")

    diff_solar = (
        _load_required_collection(
            garden_root=garden_root,
            target=diffuse_horizontal_solar_target,
            field_name="diffuse_horizontal_solar_target",
        )
        if diffuse_horizontal_solar_target is not None
        else (epw_obj.diffuse_horizontal_radiation if epw_obj is not None else None)
    )
    if diff_solar is None:
        raise ValueError("SolarCal requires diffuse_horizontal_solar_target or weather_target/epw_path.")

    frac_exposed = _load_optional_input(
        garden_root=garden_root, value=fraction_body_exposed, field_name="fraction_body_exposed"
    )
    sky_exp = _load_optional_input(garden_root=garden_root, value=sky_exposure, field_name="sky_exposure")
    floor_ref = _load_optional_input(
        garden_root=garden_root, value=floor_reflectance, field_name="floor_reflectance"
    )

    if sc_kind == "outdoor":
        dir_solar = (
            _load_required_collection(
                garden_root=garden_root,
                target=direct_normal_solar_target,
                field_name="direct_normal_solar_target",
            )
            if direct_normal_solar_target is not None
            else (epw_obj.direct_normal_radiation if epw_obj is not None else None)
        )
        horiz_ir = (
            _load_required_collection(
                garden_root=garden_root,
                target=horizontal_infrared_target,
                field_name="horizontal_infrared_target",
            )
            if horizontal_infrared_target is not None
            else (epw_obj.horizontal_infrared_radiation_intensity if epw_obj is not None else None)
        )
        surf_temp = _load_optional_input(
            garden_root=garden_root,
            value=surface_temperatures if surface_temperatures is not None else longwave_mrt,
            field_name="surface_temperatures",
        )
        if surf_temp is None and epw_obj is not None:
            surf_temp = epw_obj.dry_bulb_temperature
        if dir_solar is None or horiz_ir is None or surf_temp is None:
            raise ValueError(
                "OutdoorSolarCal requires direct_normal_solar_target, horizontal_infrared_target, "
                "and surface_temperatures (or weather_target/epw_path)."
            )
        comfort = OutdoorSolarCal(
            loc_obj,
            dir_solar,
            diff_solar,
            horiz_ir,
            surf_temp,
            fraction_body_exposed=frac_exposed,
            sky_exposure=sky_exp,
            floor_reflectance=floor_ref,
            solarcal_body_parameter=parameter,
        )
        model_label = "OutdoorSolarCal"
    elif sc_kind == "indoor":
        dir_solar = (
            _load_required_collection(
                garden_root=garden_root,
                target=direct_normal_solar_target,
                field_name="direct_normal_solar_target",
            )
            if direct_normal_solar_target is not None
            else (epw_obj.direct_normal_radiation if epw_obj is not None else None)
        )
        lw_mrt = _load_optional_input(
            garden_root=garden_root,
            value=longwave_mrt if longwave_mrt is not None else surface_temperatures,
            field_name="longwave_mrt",
        )
        if lw_mrt is None and epw_obj is not None:
            lw_mrt = epw_obj.dry_bulb_temperature
        win_trans = _load_optional_input(
            garden_root=garden_root, value=window_transmittance, field_name="window_transmittance"
        )
        if dir_solar is None or lw_mrt is None:
            raise ValueError("IndoorSolarCal requires direct_normal_solar_target and longwave_mrt.")
        comfort = IndoorSolarCal(
            loc_obj,
            dir_solar,
            diff_solar,
            lw_mrt,
            fraction_body_exposed=frac_exposed,
            sky_exposure=sky_exp,
            floor_reflectance=floor_ref,
            window_transmittance=win_trans,
            solarcal_body_parameter=parameter,
        )
        model_label = "IndoorSolarCal"
    elif sc_kind in {"horizontal", "horizontal_ref"}:
        dir_horiz = (
            _load_required_collection(
                garden_root=garden_root,
                target=direct_horizontal_solar_target,
                field_name="direct_horizontal_solar_target",
            )
            if direct_horizontal_solar_target is not None
            else None
        )
        lw_mrt = _load_optional_input(
            garden_root=garden_root,
            value=longwave_mrt if longwave_mrt is not None else surface_temperatures,
            field_name="longwave_mrt",
        )
        if lw_mrt is None and epw_obj is not None:
            lw_mrt = epw_obj.dry_bulb_temperature
        if dir_horiz is None or lw_mrt is None:
            raise ValueError(
                f"{sc_kind} SolarCal requires direct_horizontal_solar_target and longwave_mrt."
            )
        if sc_kind == "horizontal":
            comfort = HorizontalSolarCal(
                loc_obj,
                dir_horiz,
                diff_solar,
                lw_mrt,
                fraction_body_exposed=frac_exposed,
                floor_reflectance=floor_ref,
                solarcal_body_parameter=parameter,
            )
            model_label = "HorizontalSolarCal"
        else:
            ref_horiz = _load_required_collection(
                garden_root=garden_root,
                target=reflected_horizontal_solar_target,
                field_name="reflected_horizontal_solar_target",
            )
            comfort = HorizontalRefSolarCal(
                loc_obj,
                dir_horiz,
                diff_solar,
                ref_horiz,
                lw_mrt,
                fraction_body_exposed=frac_exposed,
                solarcal_body_parameter=parameter,
            )
            model_label = "HorizontalRefSolarCal"
    else:
        raise ValueError(
            "solarcal_type must be one of: outdoor, indoor, horizontal, horizontal_ref."
        )

    return _calculate(
        garden_root=garden_root,
        comfort_model=model_label,
        metric_name="mean_radiant_temperature",
        metric_attribute="mean_radiant_temperature",
        comfort=comfort,
        input_targets={
            "solarcal_type": sc_kind,
            "weather_target": weather_target,
            "location": loc_obj.to_dict(),
        },
        parameter=parameter,
        identifier=identifier,
        producer="LB_Calculate_Comfort",
        output_metrics=output_metrics,
        return_data_collection=return_data_collection,
    )


def _calculate_prevailing_temperature(
    *,
    garden_root: str,
    outdoor_temperature_target: dict[str, Any] | None,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
    avg_month: bool = True,
    output_metrics: list[str] | None = None,
    identifier: str | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    from ladybug_comfort.collection.adaptive import PrevailingTemperature

    if outdoor_temperature_target is not None:
        out_temp = _load_required_collection(
            garden_root=garden_root,
            target=outdoor_temperature_target,
            field_name="outdoor_temperature_target",
        )
    elif weather_target is not None or epw_path is not None:
        out_temp = _resolve_epw_object(
            garden_root=garden_root, weather_target=weather_target, epw_path=epw_path
        ).dry_bulb_temperature
    else:
        raise ValueError("prevailing_temperature requires outdoor_temperature_target or weather_target/epw_path.")

    pt = PrevailingTemperature(out_temp, avg_month=avg_month)
    return _calculate(
        garden_root=garden_root,
        comfort_model="PrevailingTemperature",
        metric_name="hourly_prevailing_temperature",
        metric_attribute="hourly_prevailing_temperature",
        comfort=pt,
        input_targets={"outdoor_temperature": outdoor_temperature_target, "avg_month": avg_month},
        parameter=None,
        identifier=identifier,
        producer="LB_Calculate_Comfort",
        output_metrics=output_metrics,
        return_data_collection=return_data_collection,
    )


def _calculate_clo_schiavon(
    *,
    garden_root: str,
    outdoor_temperature: dict[str, Any] | float | int | None,
    outdoor_temperature_target: dict[str, Any] | None,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
    max_clo: float = 1.0,
    max_clo_temp: float = -5.0,
    min_clo: float = 0.46,
    min_clo_temp: float = 26.0,
    identifier: str | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    from ladybug_comfort.clo import schiavon_clo

    source_col = None
    if outdoor_temperature_target is not None:
        source_col = _load_required_collection(
            garden_root=garden_root,
            target=outdoor_temperature_target,
            field_name="outdoor_temperature_target",
        )
    elif isinstance(outdoor_temperature, dict):
        source_col = _load_required_collection(
            garden_root=garden_root,
            target=outdoor_temperature,
            field_name="outdoor_temperature",
        )
    elif weather_target is not None or epw_path is not None:
        source_col = _resolve_epw_object(
            garden_root=garden_root, weather_target=weather_target, epw_path=epw_path
        ).dry_bulb_temperature

    if source_col is None:
        if outdoor_temperature is None or isinstance(outdoor_temperature, bool):
            raise ValueError(
                "clo_schiavon requires outdoor_temperature (scalar/target), outdoor_temperature_target, or weather_target."
            )
        clo_val = float(
            schiavon_clo(
                float(outdoor_temperature),
                max_clo=max_clo,
                max_clo_temp=max_clo_temp,
                min_clo=min_clo,
                min_clo_temp=min_clo_temp,
            )
        )
        return {
            "clo_value": clo_val,
            "summary_view": {
                "comfort_model": "SchiavonClo",
                "outdoor_temperature": float(outdoor_temperature),
                "clo_value": clo_val,
            },
            "report": make_report(status="ok", message="Schiavon dynamic clothing computed."),
        }

    clo_vals = [
        float(
            schiavon_clo(
                float(t),
                max_clo=max_clo,
                max_clo_temp=max_clo_temp,
                min_clo=min_clo,
                min_clo_temp=min_clo_temp,
            )
        )
        for t in source_col.values
    ]
    meta = dict(source_col.header.metadata or {})
    meta["comfort_model"] = "SchiavonClo"
    hdr = Header(ClothingInsulation(), "clo", source_col.header.analysis_period, metadata=meta)
    clo_col = (
        HourlyContinuousCollection(hdr, clo_vals)
        if isinstance(source_col, HourlyContinuousCollection)
        else type(source_col)(hdr, clo_vals, source_col.datetimes)
    )
    saved = save_data_collection(
        garden_root=garden_root,
        data_collection=clo_col,
        identifier=identifier or "clo_schiavon",
        source={"producer": "LB_Calculate_Comfort", "comfort_model": "SchiavonClo"},
    )
    res: dict[str, Any] = {
        "target": saved["target"],
        "data_target": saved["target"],
        "data_collection_target": saved["target"],
        "artifact": saved["artifact"],
        "persistence_receipt": saved["persistence_receipt"],
        "summary_view": {
            "garden_target": GardenManifest.read(Path(garden_root).resolve()).target(),
            "comfort_model": "SchiavonClo",
            "data_collection": saved["summary_view"],
        },
        "report": make_report(status="ok", message="Schiavon clo DataCollection persisted."),
    }
    if return_data_collection:
        res["data_collection"] = clo_col.to_dict()
    return res


def _calculate_local_discomfort(
    *,
    garden_root: str,
    local_discomfort_type: str = "radiant_asymmetry_ppd",
    radiant_temperature_difference: dict[str, Any] | float | int | None = None,
    asymmetry_type: int | str = 0,
    predicted_mean_vote: dict[str, Any] | float | int | None = None,
    air_speed_at_ankle: dict[str, Any] | float | int | None = None,
    identifier: str | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    from ladybug.datatype.thermalcondition import DiscomfortReason
    from ladybug_comfort.local import ankle_draft_ppd, radiant_asymmetry_ppd

    kind = str(local_discomfort_type or "radiant_asymmetry_ppd").strip().lower()
    if kind == "radiant_asymmetry_ppd":
        asym_map = {
            "0": 0,
            "warmceiling": 0,
            "warm_ceiling": 0,
            "1": 1,
            "coolwall": 1,
            "cool_wall": 1,
            "2": 2,
            "coolceiling": 2,
            "cool_ceiling": 2,
            "3": 3,
            "warmwall": 3,
            "warm_wall": 3,
        }
        asym_idx = (
            asymmetry_type
            if isinstance(asymmetry_type, int)
            else asym_map.get(str(asymmetry_type).strip().lower())
        )
        if asym_idx is None:
            raise ValueError("asymmetry_type must be 0..3 or warm_ceiling/cool_wall/cool_ceiling/warm_wall.")
        inp = _load_optional_input(
            garden_root=garden_root,
            value=radiant_temperature_difference,
            field_name="radiant_temperature_difference",
        )
        if inp is None:
            raise ValueError("radiant_temperature_difference is required for radiant_asymmetry_ppd.")
        if not hasattr(inp, "values"):
            ppd_val = float(radiant_asymmetry_ppd(float(inp), asym_idx))
            return {
                "ppd": ppd_val,
                "summary_view": {"comfort_model": kind, "asymmetry_type": asym_idx, "ppd": ppd_val},
                "report": make_report(status="ok", message="Radiant asymmetry PPD computed."),
            }
        ppd_vals = [float(radiant_asymmetry_ppd(float(v), asym_idx)) for v in inp.values]
        template_col = inp
    elif kind == "ankle_draft_ppd":
        pmv_in = _load_optional_input(
            garden_root=garden_root, value=predicted_mean_vote, field_name="predicted_mean_vote"
        )
        vel_in = _load_optional_input(
            garden_root=garden_root, value=air_speed_at_ankle, field_name="air_speed_at_ankle"
        )
        if pmv_in is None or vel_in is None:
            raise ValueError("ankle_draft_ppd requires predicted_mean_vote and air_speed_at_ankle.")
        if not hasattr(pmv_in, "values") and not hasattr(vel_in, "values"):
            ppd_val = float(ankle_draft_ppd(float(pmv_in), float(vel_in)))
            return {
                "ppd": ppd_val,
                "summary_view": {"comfort_model": kind, "ppd": ppd_val},
                "report": make_report(status="ok", message="Ankle draft PPD computed."),
            }
        template_col = pmv_in if hasattr(pmv_in, "values") else vel_in
        n = len(template_col)
        pmv_seq = list(pmv_in.values) if hasattr(pmv_in, "values") else [float(pmv_in)] * n
        vel_seq = list(vel_in.values) if hasattr(vel_in, "values") else [float(vel_in)] * n
        ppd_vals = [float(ankle_draft_ppd(float(p), float(v))) for p, v in zip(pmv_seq, vel_seq)]
    else:
        raise ValueError("local_discomfort_type must be radiant_asymmetry_ppd or ankle_draft_ppd.")

    from ladybug.datatype.fraction import PercentagePeopleDissatisfied

    meta = dict(template_col.header.metadata or {})
    meta["comfort_model"] = kind
    hdr = Header(PercentagePeopleDissatisfied(), "%", template_col.header.analysis_period, metadata=meta)
    out_col = (
        HourlyContinuousCollection(hdr, ppd_vals)
        if isinstance(template_col, HourlyContinuousCollection)
        else type(template_col)(hdr, ppd_vals, template_col.datetimes)
    )
    saved = save_data_collection(
        garden_root=garden_root,
        data_collection=out_col,
        identifier=identifier or kind,
        source={"producer": "LB_Calculate_Comfort", "comfort_model": kind},
    )
    res: dict[str, Any] = {
        "target": saved["target"],
        "data_target": saved["target"],
        "data_collection_target": saved["target"],
        "artifact": saved["artifact"],
        "persistence_receipt": saved["persistence_receipt"],
        "summary_view": {
            "garden_target": GardenManifest.read(Path(garden_root).resolve()).target(),
            "comfort_model": kind,
            "data_collection": saved["summary_view"],
        },
        "report": make_report(status="ok", message=f"Local discomfort '{kind}' persisted."),
    }
    if return_data_collection:
        res["data_collection"] = out_col.to_dict()
    return res


def _calculate_heat_stress(
    *,
    garden_root: str,
    heat_stress_index: str = "wbgt",
    air_temperature_target: dict[str, Any] | float | int | None = None,
    relative_humidity_target: dict[str, Any] | float | int | None = None,
    mean_radiant_temperature_target: dict[str, Any] | float | int | None = None,
    wind_speed_target: dict[str, Any] | float | int | None = None,
    dew_point_temperature_target: dict[str, Any] | float | int | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    identifier: str | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    from ladybug.datatype.energyflux import Irradiance
    from ladybug.datatype.temperature import (
        HeatIndexTemperature,
        WetBulbGlobeTemperature,
        WindChillTemperature,
    )
    from ladybug.psychrometrics import dew_point_from_db_rh
    from ladybug_comfort.at import apparent_temperature, apparent_temperature_warning_category
    from ladybug_comfort.di import discomfort_index, discomfort_index_effect_category
    from ladybug_comfort.hi import heat_index, heat_index_warning_category
    from ladybug_comfort.humidex import humidex, humidex_degree_of_comfort
    from ladybug_comfort.wbgt import wbgt_warning_category, wet_bulb_globe_temperature
    from ladybug_comfort.wc import (
        windchill_index,
        windchill_index_effect_category,
        windchill_temp,
        windchill_temp_effect_category,
    )

    idx_name = str(heat_stress_index or "wbgt").strip().lower()
    epw_obj = (
        _resolve_epw_object(garden_root=garden_root, weather_target=weather_target, epw_path=epw_path)
        if (weather_target is not None or epw_path is not None)
        else None
    )

    ta_in = _load_optional_input(
        garden_root=garden_root, value=air_temperature_target, field_name="air_temperature_target"
    )
    if ta_in is None and epw_obj is not None:
        ta_in = epw_obj.dry_bulb_temperature
    rh_in = _load_optional_input(
        garden_root=garden_root, value=relative_humidity_target, field_name="relative_humidity_target"
    )
    if rh_in is None and epw_obj is not None:
        rh_in = epw_obj.relative_humidity
    mrt_in = _load_optional_input(
        garden_root=garden_root,
        value=mean_radiant_temperature_target,
        field_name="mean_radiant_temperature_target",
    )
    ws_in = _load_optional_input(
        garden_root=garden_root, value=wind_speed_target, field_name="wind_speed_target"
    )
    if ws_in is None and epw_obj is not None:
        ws_in = epw_obj.wind_speed
    dp_in = _load_optional_input(
        garden_root=garden_root,
        value=dew_point_temperature_target,
        field_name="dew_point_temperature_target",
    )
    if dp_in is None and epw_obj is not None:
        dp_in = epw_obj.dew_point_temperature

    if ta_in is None:
        raise ValueError(f"heat_stress ({idx_name}) requires air_temperature_target or weather_target/epw_path.")

    collections = [v for v in (ta_in, rh_in, mrt_in, ws_in, dp_in) if hasattr(v, "values")]
    template_col = collections[0] if collections else None

    def _seq(val: Any, default: float | None = None) -> list[float]:
        n = len(template_col) if template_col is not None else 1
        if hasattr(val, "values"):
            if len(val) != n:
                raise ValueError("All heat_stress DataCollection inputs must have the same length.")
            return [float(x) for x in val.values]
        if val is None:
            if default is None:
                raise ValueError(f"Missing required input for heat_stress={idx_name!r}.")
            return [default] * n
        return [float(val)] * n

    ta_seq = _seq(ta_in)
    if idx_name == "wbgt":
        rh_seq = _seq(rh_in)
        mrt_seq = _seq(mrt_in) if mrt_in is not None else ta_seq
        ws_seq = _seq(ws_in, default=0.5)
        vals = [float(wet_bulb_globe_temperature(ta, mrt, ws, rh)) for ta, mrt, ws, rh in zip(ta_seq, mrt_seq, ws_seq, rh_seq)]
        cats = [wbgt_warning_category(v) for v in vals]
        dt_cls, unit_str = WetBulbGlobeTemperature, "C"
    elif idx_name == "hi":
        rh_seq = _seq(rh_in)
        vals = [float(heat_index(ta, rh)) for ta, rh in zip(ta_seq, rh_seq)]
        cats = [heat_index_warning_category(v) for v in vals]
        dt_cls, unit_str = HeatIndexTemperature, "C"
    elif idx_name == "humidex":
        if dp_in is not None:
            dp_seq = _seq(dp_in)
        elif rh_in is not None:
            rh_seq = _seq(rh_in)
            dp_seq = [float(dew_point_from_db_rh(ta, rh)) for ta, rh in zip(ta_seq, rh_seq)]
        else:
            raise ValueError("humidex requires dew_point_temperature_target or relative_humidity_target.")
        vals = [float(humidex(ta, dp)) for ta, dp in zip(ta_seq, dp_seq)]
        cats = [humidex_degree_of_comfort(v) for v in vals]
        dt_cls, unit_str = Temperature, "C"
    elif idx_name in {"wc", "wc_temp", "wc_index"}:
        ws_seq = _seq(ws_in, default=1.0)
        if idx_name == "wc_index":
            vals = [float(windchill_index(ta, ws)) for ta, ws in zip(ta_seq, ws_seq)]
            cats = [windchill_index_effect_category(v) for v in vals]
            dt_cls, unit_str = Irradiance, "W/m2"
        else:
            vals = [float(windchill_temp(ta, ws)) for ta, ws in zip(ta_seq, ws_seq)]
            cats = [windchill_temp_effect_category(v) for v in vals]
            dt_cls, unit_str = WindChillTemperature, "C"
    elif idx_name == "at":
        rh_seq = _seq(rh_in)
        ws_unit = getattr(getattr(ws_in, "header", None), "unit", "m/s") if hasattr(ws_in, "values") else "m/s"
        ws_seq = _seq(ws_in, default=0.5)
        ws_kmh_seq = ws_seq if str(ws_unit).lower() == "km/h" else [w * 3.6 for w in ws_seq]
        vals = [float(apparent_temperature(ta, rh, ws_kmh)) for ta, rh, ws_kmh in zip(ta_seq, rh_seq, ws_kmh_seq)]
        cats = [apparent_temperature_warning_category(v) for v in vals]
        dt_cls, unit_str = Temperature, "C"
    elif idx_name == "di":
        rh_seq = _seq(rh_in)
        vals = [float(discomfort_index(ta, rh)) for ta, rh in zip(ta_seq, rh_seq)]
        cats = [discomfort_index_effect_category(v) for v in vals]
        dt_cls, unit_str = Temperature, "C"
    else:
        raise ValueError("heat_stress_index must be one of: wbgt, hi, humidex, wc, wc_index, at, di.")

    if template_col is None:
        return {
            "value": vals[0],
            "category": cats[0],
            "summary_view": {
                "comfort_model": f"heat_stress:{idx_name}",
                "value": vals[0],
                "category": cats[0],
            },
            "report": make_report(status="ok", message=f"Heat stress '{idx_name}' computed."),
        }

    meta = dict(template_col.header.metadata or {})
    meta["comfort_model"] = f"heat_stress:{idx_name}"
    hdr = Header(dt_cls(), unit_str, template_col.header.analysis_period, metadata=meta)
    out_col = (
        HourlyContinuousCollection(hdr, vals)
        if isinstance(template_col, HourlyContinuousCollection)
        else type(template_col)(hdr, vals, template_col.datetimes)
    )
    saved = save_data_collection(
        garden_root=garden_root,
        data_collection=out_col,
        identifier=identifier or f"heat_stress_{idx_name}",
        source={"producer": "LB_Calculate_Comfort", "comfort_model": f"heat_stress:{idx_name}"},
    )
    res: dict[str, Any] = {
        "target": saved["target"],
        "data_target": saved["target"],
        "data_collection_target": saved["target"],
        "artifact": saved["artifact"],
        "persistence_receipt": saved["persistence_receipt"],
        "summary_view": {
            "garden_target": GardenManifest.read(Path(garden_root).resolve()).target(),
            "comfort_model": f"heat_stress:{idx_name}",
            "data_collection": saved["summary_view"],
            "category_min": min(cats),
            "category_max": max(cats),
        },
        "report": make_report(status="ok", message=f"Heat stress '{idx_name}' DataCollection persisted."),
    }
    if return_data_collection:
        res["data_collection"] = out_col.to_dict()
    return res


def _resolve_garden_input_path(garden_root: str | Path, raw_path: str, field_name: str) -> Path:
    root = Path(garden_root).expanduser().resolve()
    raw = Path(raw_path).expanduser()
    candidate = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be inside Garden root: {raw_path}") from exc
    if not candidate.is_file():
        raise ValueError(f"{field_name} must reference an existing file: {raw_path}")
    return candidate


def _coerce_point3d(raw: dict[str, Any] | list[float] | tuple[float, ...]) -> Point3D:
    if isinstance(raw, dict):
        return Point3D(float(raw.get("x", 0.0)), float(raw.get("y", 0.0)), float(raw.get("z", 0.0)))
    if isinstance(raw, (list, tuple)) and len(raw) >= 3:
        return Point3D(float(raw[0]), float(raw[1]), float(raw[2]))
    raise ValueError("human_position must be a [x, y, z] list or Point3D dict.")


def _resolve_solarcal_context(
    *,
    garden_root: str | Path,
    context_geometry: list[dict[str, Any]] | None,
    model_target: dict[str, Any] | None,
) -> list[Face3D | Mesh3D]:
    ctx: list[Face3D | Mesh3D] = []
    if model_target is not None:
        from garden.honeybee_core.model_io import load_honeybee_model, resolve_model_target

        root = Path(garden_root).expanduser().resolve()
        _, resolved_target = resolve_model_target(root, model_target)
        model = load_honeybee_model(root, resolved_target)
        for room in model.rooms:
            for face in room.faces:
                ctx.append(face.geometry)
                for sh in face.shades:
                    ctx.append(sh.geometry)
            for sh in room.shades:
                ctx.append(sh.geometry)
        for face in model.orphaned_faces:
            ctx.append(face.geometry)
            for sh in face.shades:
                ctx.append(sh.geometry)
        for sh in model.shades:
            ctx.append(sh.geometry)
    for item in context_geometry or []:
        if not isinstance(item, dict):
            raise ValueError("Each context_geometry entry must be a Face3D or Mesh3D dict.")
        data = dict(item)
        if data.get("type") == "Mesh3D" or "faces" in data:
            data.setdefault("type", "Mesh3D")
            ctx.append(Mesh3D.from_dict(data))
        else:
            data.setdefault("type", "Face3D")
            ctx.append(Face3D.from_dict(data))
    return ctx


def _maybe_human_to_sky(
    *,
    garden_root: str | Path,
    location_obj: Location,
    human_position: dict[str, Any] | list[float] | None,
    human_height: float,
    human_point_count: int,
    context_geometry: list[dict[str, Any]] | None,
    model_target: dict[str, Any] | None,
    north_angle: float,
    frac_exposed: Any,
    sky_exp: Any,
) -> tuple[Any, Any, dict[str, Any] | None]:
    if human_position is None:
        return frac_exposed, sky_exp, None
    ctx = _resolve_solarcal_context(
        garden_root=garden_root,
        context_geometry=context_geometry,
        model_target=model_target,
    )
    if not ctx:
        return frac_exposed, sky_exp, None
    pos_pt = _coerce_point3d(human_position)
    auto_fract, auto_sky = compute_human_to_sky_relation(
        location=location_obj,
        human_position=pos_pt,
        context_geometries=ctx,
        north_angle=float(north_angle),
        height=float(human_height),
        point_count=int(human_point_count),
    )
    resolved_fract = auto_fract if frac_exposed is None else frac_exposed
    resolved_sky = auto_sky if sky_exp is None else sky_exp
    info = {
        "human_position": [pos_pt.x, pos_pt.y, pos_pt.z],
        "human_height": float(human_height),
        "human_point_count": int(human_point_count),
        "north_angle": float(north_angle),
        "context_count": len(ctx),
        "computed_sky_exposure": auto_sky,
        "computed_fraction_body_exposed_mean": float(auto_fract.average),
    }
    return resolved_fract, resolved_sky, info


def _resolve_scalar_or_collection_float(
    *,
    garden_root: str | Path,
    value: Any,
    field_name: str,
) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number or DataCollection target.")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        col = _load_required_collection(garden_root=garden_root, target=value, field_name=field_name)
        return float(col.average)
    raise ValueError(f"{field_name} must be a number or DataCollection target.")


def calculate_passive_strategy(
    *,
    garden_root: str,
    air_temperature_target: dict[str, Any] | None = None,
    relative_humidity_target: dict[str, Any] | None = None,
    mean_radiant_temperature_target: dict[str, Any] | None = None,
    longwave_mrt: dict[str, Any] | list[float] | float | int | None = None,
    outdoor_temperature_target: dict[str, Any] | None = None,
    incident_irradiance_target: dict[str, Any] | None = None,
    barometric_pressure: dict[str, Any] | float | int | None = None,
    air_speed: dict[str, Any] | list[float] | float | int | None = None,
    met_rate: dict[str, Any] | list[float] | float | int | None = None,
    clo_value: dict[str, Any] | list[float] | float | int | None = None,
    external_work: dict[str, Any] | list[float] | float | int | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    strategies: list[str] | dict[str, Any] | None = None,
    passive_strategy_parameters: dict[str, Any] | None = None,
    merge_polygons: bool = True,
    comfort_parameter: dict[str, Any] | None = None,
    output_metrics: list[str] | None = None,
    identifier: str | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    """Calculate passive strategy comfort coverage using PsychrometricChart and PolygonPMV."""
    from ladybug.psychchart import PsychrometricChart
    from ladybug_comfort.chart.polygonpmv import PolygonPMV
    from ladybug_comfort.parameter.pmv import PMVParameter

    root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(root_path)
    garden_target = manifest.target()

    epw_obj = (
        _resolve_epw_object(garden_root=garden_root, weather_target=weather_target, epw_path=epw_path)
        if (weather_target is not None or epw_path is not None)
        else None
    )

    if air_temperature_target is not None:
        temperature = _load_required_collection(
            garden_root=garden_root,
            target=air_temperature_target,
            field_name="air_temperature_target",
        )
    elif epw_obj is not None:
        temperature = epw_obj.dry_bulb_temperature
    else:
        raise ValueError(
            "passive_strategy requires air_temperature_target and relative_humidity_target, "
            "or weather_target/epw_path."
        )

    if relative_humidity_target is not None:
        relative_humidity = _load_required_collection(
            garden_root=garden_root,
            target=relative_humidity_target,
            field_name="relative_humidity_target",
        )
    elif epw_obj is not None:
        relative_humidity = epw_obj.relative_humidity
    else:
        raise ValueError(
            "passive_strategy requires air_temperature_target and relative_humidity_target, "
            "or weather_target/epw_path."
        )

    if len(temperature) != len(relative_humidity):
        raise ValueError("air_temperature_target and relative_humidity_target must align in length.")

    outdoor_col = (
        _load_required_collection(
            garden_root=garden_root,
            target=outdoor_temperature_target,
            field_name="outdoor_temperature_target",
        )
        if outdoor_temperature_target is not None
        else (epw_obj.dry_bulb_temperature if epw_obj is not None else None)
    )
    solar_col = (
        _load_required_collection(
            garden_root=garden_root,
            target=incident_irradiance_target,
            field_name="incident_irradiance_target",
        )
        if incident_irradiance_target is not None
        else (epw_obj.global_horizontal_radiation if epw_obj is not None else None)
    )

    avg_pressure = _resolve_scalar_or_collection_float(
        garden_root=garden_root, value=barometric_pressure, field_name="barometric_pressure"
    )
    if avg_pressure is None:
        avg_pressure = (
            float(epw_obj.atmospheric_station_pressure.average)
            if epw_obj is not None
            else 101325.0
        )

    def _loader(tgt: dict[str, Any], fname: str) -> Any:
        return _load_required_collection(garden_root=garden_root, target=tgt, field_name=fname)

    rad_vals = summarize_polygon_numeric_input(
        mean_radiant_temperature_target if mean_radiant_temperature_target is not None else longwave_mrt,
        load_collection_fn=_loader,
        field_name="mean_radiant_temperature_target",
    )
    air_speed_vals = summarize_polygon_numeric_input(
        air_speed, load_collection_fn=_loader, field_name="air_speed"
    )
    met_vals = summarize_polygon_numeric_input(
        met_rate, load_collection_fn=_loader, field_name="met_rate"
    )
    clo_vals = summarize_polygon_numeric_input(
        clo_value, load_collection_fn=_loader, field_name="clo_value"
    )
    wme_vals = summarize_polygon_numeric_input(
        external_work, load_collection_fn=_loader, field_name="external_work"
    )

    pmv_par = _load_parameter(
        comfort_parameter,
        expected_type="PMVParameter",
        parameter_cls=PMVParameter,
    )
    params = PassiveStrategyParameters.from_dict(passive_strategy_parameters)
    enabled_strategies = normalize_passive_strategies(
        strategies,
        has_solar=(solar_col is not None),
        strict=True,
    )
    enabled_strategies = [s for s in enabled_strategies if s != "shade_line"]

    chart = PsychrometricChart(temperature, relative_humidity, average_pressure=avg_pressure)
    ppmv = PolygonPMV(
        chart,
        rad_temperature=rad_vals,
        air_speed=air_speed_vals,
        met_rate=met_vals,
        clo_value=clo_vals,
        external_work=wme_vals,
        comfort_parameter=pmv_par,
    )
    eval_res = evaluate_pmv_passive_strategies(
        chart=chart,
        ppmv=ppmv,
        params=params,
        strategies=enabled_strategies,
        outdoor_temperature=outdoor_col,
        incident_irradiance=solar_col,
        merge_polygons=merge_polygons,
    )
    masks = eval_res["masks"]
    stats = eval_res["statistics"]

    mask_collections: dict[str, Any] = {
        "total_comfort": ppmv.create_collection(masks["total_comfort"], "Total Comfort"),
        "comfort": ppmv.create_collection(masks["comfort"], "Comfort"),
    }
    for strat_key, strat_vals in masks.items():
        if strat_key in {"total_comfort", "comfort"}:
            continue
        mask_collections[strat_key] = ppmv.create_collection(
            strat_vals, STRATEGY_DISPLAY_NAMES.get(strat_key, strat_key)
        )

    requested_metrics = list(output_metrics) if output_metrics else ["total_comfort"]
    resolved_metric_keys: list[tuple[str, str]] = []
    for raw_m in requested_metrics:
        key_clean = raw_m.strip().lower()
        if key_clean in mask_collections:
            resolved_metric_keys.append((raw_m, key_clean))
        else:
            mapped = normalize_passive_strategies([raw_m], strict=False)
            if mapped and mapped[0] in mask_collections:
                resolved_metric_keys.append((raw_m, mapped[0]))
            else:
                raise ValueError(
                    f"Metric {raw_m!r} is not available in PassiveStrategy results "
                    f"(available: {sorted(mask_collections.keys())})."
                )

    input_targets = {
        "weather_target": weather_target,
        "epw_path": epw_path,
        "air_temperature": air_temperature_target,
        "relative_humidity": relative_humidity_target,
        "outdoor_temperature": outdoor_temperature_target,
        "incident_irradiance": incident_irradiance_target,
        "average_pressure": avg_pressure,
    }
    param_dict = pmv_par.to_dict() if pmv_par is not None else None
    persisted_by_name: dict[str, dict[str, Any]] = {}
    metric_summaries: dict[str, Any] = {}
    metric_objects: dict[str, Any] = {}
    base_id = identifier or "passive_strategy_total_comfort"

    for raw_m, canon_m in resolved_metric_keys:
        col = mask_collections[canon_m].duplicate()
        col.header.metadata.update(
            {
                "source": "ladybug_comfort",
                "comfort_model": "PassiveStrategy",
                "comfort_metric": canon_m,
            }
        )
        res_id = base_id if len(resolved_metric_keys) == 1 else f"{base_id}_{canon_m}"
        saved = save_data_collection(
            garden_root=garden_root,
            data_collection=col,
            identifier=res_id,
            source={
                "producer": "LB_Calculate_Comfort",
                "comfort_model": "PassiveStrategy",
                "comfort_metric": canon_m,
                "input_targets": input_targets,
                "comfort_parameter": param_dict,
                "passive_strategy_parameters": params.to_dict(),
            },
        )
        persisted_by_name[raw_m] = saved
        metric_summaries[raw_m] = data_collection_summary(col)
        metric_objects[raw_m] = col

    primary_key = requested_metrics[0]
    primary_saved = persisted_by_name[primary_key]
    summary_view: dict[str, Any] = {
        "garden_target": garden_target,
        "comfort_model": "PassiveStrategy",
        "comfort_metric": primary_key,
        "input_targets": input_targets,
        "comfort_parameter": param_dict,
        "passive_strategy_parameters": stats["passive_strategy_parameters"],
        "baseline_comfort_percent": stats["baseline_comfort_percent"],
        "total_comfort_percent": stats["total_comfort_percent"],
        "passive_gain_percent": stats["passive_gain_percent"],
        "baseline_comfort_hours": stats["baseline_comfort_hours"],
        "total_comfort_hours": stats["total_comfort_hours"],
        "passive_gain_hours": stats["passive_gain_hours"],
        "strategies_requested": stats["strategies_requested"],
        "strategies_added": stats["strategies_added"],
        "strategies_skipped": stats["strategies_skipped"],
        "strategy_percents": stats["strategy_percents"],
        "strategy_details": stats["strategy_details"],
        "polygon_names": stats["polygon_names"],
        "polygon_comfort": stats["polygon_comfort"],
        "percentages": {
            "comfortable": stats["baseline_comfort_percent"],
            "total_comfortable": stats["total_comfort_percent"],
            "passive_gain": stats["passive_gain_percent"],
            "uncomfortable": max(0.0, 100.0 - stats["total_comfort_percent"]),
        },
        "data_collection": metric_summaries[primary_key],
    }
    if output_metrics:
        summary_view["output_metrics"] = metric_summaries
        summary_view["output_targets"] = {k: v["target"] for k, v in persisted_by_name.items()}

    result: dict[str, Any] = {
        "target": primary_saved["target"],
        "data_target": primary_saved["target"],
        "data_collection_target": primary_saved["target"],
        "artifact": primary_saved["artifact"],
        "persistence_receipt": primary_saved["persistence_receipt"],
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message="Passive strategy comfort analysis completed and persisted.",
        ),
    }
    if output_metrics:
        targets_map = {k: v["target"] for k, v in persisted_by_name.items()}
        result["targets"] = targets_map
        result["data_collection_targets"] = targets_map
        result["artifacts"] = {k: v["artifact"] for k, v in persisted_by_name.items()}
        result["persistence_receipts"] = {
            k: v["persistence_receipt"] for k, v in persisted_by_name.items()
        }
    if return_data_collection:
        result["data_collection"] = metric_objects[primary_key].to_dict()
        if output_metrics:
            result["data_collections"] = {k: obj.to_dict() for k, obj in metric_objects.items()}
    return result


def _calculate_solar_mrt_map(
    *,
    garden_root: str,
    comfort_model: str,
    loc_obj: Location,
    longwave_mrt: Any,
    surface_temperatures: Any,
    air_temperature_target: dict[str, Any] | None,
    epw_obj: EPW | None,
    sun_up_hours_path: str,
    indirect_ill_path: str,
    direct_ill_path: str | None,
    reflected_ill_path: str | None,
    indirect_is_total: bool,
    parameter: Any,
    identifier: str | None,
    return_data_collection: bool,
) -> dict[str, Any]:
    from ladybug_comfort.map.mrt import shortwave_mrt_map

    sun_up_file = _resolve_garden_input_path(garden_root, sun_up_hours_path, "sun_up_hours_path")
    ind_file = _resolve_garden_input_path(garden_root, indirect_ill_path, "indirect_ill_path")
    dir_file = (
        _resolve_garden_input_path(garden_root, direct_ill_path, "direct_ill_path")
        if direct_ill_path
        else None
    )
    ref_file = (
        _resolve_garden_input_path(garden_root, reflected_ill_path, "reflected_ill_path")
        if reflected_ill_path
        else None
    )

    lw_raw = longwave_mrt if longwave_mrt is not None else surface_temperatures
    if isinstance(lw_raw, dict):
        lw_data = [
            _load_required_collection(
                garden_root=garden_root, target=lw_raw, field_name="longwave_mrt"
            )
        ]
    elif isinstance(lw_raw, (int, float)) and not isinstance(lw_raw, bool):
        hdr = Header(Temperature(), "C", AnalysisPeriod())
        lw_data = [HourlyContinuousCollection(hdr, [float(lw_raw)] * 8760)]
    elif air_temperature_target is not None:
        lw_data = [
            _load_required_collection(
                garden_root=garden_root,
                target=air_temperature_target,
                field_name="air_temperature_target",
            )
        ]
    elif epw_obj is not None:
        lw_data = [epw_obj.dry_bulb_temperature]
    else:
        raise ValueError(
            "Solar MRT map mode requires longwave_mrt, surface_temperatures, "
            "air_temperature_target, or weather_target/epw_path."
        )

    mrt_cols = shortwave_mrt_map(
        location=loc_obj,
        longwave_data=lw_data,
        sun_up_hours=str(sun_up_file),
        indirect_ill=str(ind_file),
        direct_ill=str(dir_file) if dir_file else None,
        ref_ill=str(ref_file) if ref_file else None,
        solarcal_par=parameter,
        indirect_is_total=indirect_is_total,
    )
    if not mrt_cols:
        raise ValueError("shortwave_mrt_map produced no sensor MRT collections.")

    if len(mrt_cols) == 1:
        primary_col = mrt_cols[0].duplicate()
    else:
        n_steps = len(mrt_cols[0].values)
        mean_vals = [
            sum(col.values[idx] for col in mrt_cols) / len(mrt_cols)
            for idx in range(n_steps)
        ]
        hdr = mrt_cols[0].header.duplicate()
        hdr.metadata["sensor_count"] = len(mrt_cols)
        primary_col = HourlyContinuousCollection(hdr, mean_vals)

    saved = save_data_collection(
        garden_root=garden_root,
        data_collection=primary_col,
        identifier=identifier or f"{comfort_model.lower()}_map",
        source={
            "producer": "LB_Calculate_Comfort",
            "comfort_model": f"{comfort_model}Map",
            "sensor_count": len(mrt_cols),
        },
    )
    sensor_summaries = [data_collection_summary(c) for c in mrt_cols[:32]]
    res: dict[str, Any] = {
        "target": saved["target"],
        "data_target": saved["target"],
        "data_collection_target": saved["target"],
        "artifact": saved["artifact"],
        "persistence_receipt": saved["persistence_receipt"],
        "summary_view": {
            "garden_target": GardenManifest.read(Path(garden_root).resolve()).target(),
            "comfort_model": f"{comfort_model}Map",
            "sensor_count": len(mrt_cols),
            "sensors": sensor_summaries,
            "data_collection": data_collection_summary(primary_col),
        },
        "report": make_report(
            status="ok",
            message=f"{comfort_model} map MRT computed for {len(mrt_cols)} sensor(s).",
        ),
    }
    if return_data_collection:
        res["data_collection"] = primary_col.to_dict()
    return res


def calculate_indoor_solar_mrt(
    *,
    garden_root: str,
    location: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    direct_normal_solar_target: dict[str, Any] | None = None,
    diffuse_horizontal_solar_target: dict[str, Any] | None = None,
    air_temperature_target: dict[str, Any] | None = None,
    mean_radiant_temperature_target: dict[str, Any] | None = None,
    surface_temperatures: dict[str, Any] | list[float] | float | None = None,
    longwave_mrt: dict[str, Any] | list[float] | float | None = None,
    fraction_body_exposed: dict[str, Any] | list[float] | float | None = None,
    sky_exposure: dict[str, Any] | list[float] | float | None = None,
    floor_reflectance: dict[str, Any] | list[float] | float | None = None,
    window_transmittance: dict[str, Any] | list[float] | float | None = None,
    solar_altitude: float | None = None,
    direct_normal_solar: float | None = None,
    diffuse_horizontal_solar: float | None = None,
    human_position: dict[str, Any] | list[float] | None = None,
    human_height: float = 1.8,
    human_point_count: int = 1,
    context_geometry: list[dict[str, Any]] | None = None,
    model_target: dict[str, Any] | None = None,
    north_angle: float = 0.0,
    sun_up_hours_path: str | None = None,
    indirect_ill_path: str | None = None,
    direct_ill_path: str | None = None,
    reflected_ill_path: str | None = None,
    indirect_is_total: bool = False,
    comfort_parameter: dict[str, Any] | None = None,
    output_metrics: list[str] | None = None,
    identifier: str | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    """Calculate Indoor Solar MRT (DataCollection/EPW, Radiance map, or scalar SolarCal)."""
    from ladybug_comfort.collection.solarcal import IndoorSolarCal
    from ladybug_comfort.parameter.solarcal import SolarCalParameter
    from ladybug_comfort.solarcal import indoor_sky_heat_exch

    parameter = _load_parameter(
        comfort_parameter,
        expected_type="SolarCalParameter",
        parameter_cls=SolarCalParameter,
    )

    is_scalar_mode = (
        solar_altitude is not None
        and weather_target is None
        and epw_path is None
        and direct_normal_solar_target is None
        and diffuse_horizontal_solar_target is None
        and not (sun_up_hours_path and indirect_ill_path)
    )
    if is_scalar_mode:
        lw_val = _resolve_scalar_or_collection_float(
            garden_root=garden_root,
            value=longwave_mrt if longwave_mrt is not None else surface_temperatures,
            field_name="longwave_mrt",
        )
        if lw_val is None:
            lw_val = _resolve_scalar_or_collection_float(
                garden_root=garden_root,
                value=mean_radiant_temperature_target if mean_radiant_temperature_target is not None else air_temperature_target,
                field_name="air_temperature_target",
            )
        if lw_val is None:
            raise ValueError("Scalar indoor_solar_mrt requires longwave_mrt or surface_temperatures.")
        sky_e = _resolve_scalar_or_collection_float(
            garden_root=garden_root, value=sky_exposure, field_name="sky_exposure"
        )
        frac_e = _resolve_scalar_or_collection_float(
            garden_root=garden_root, value=fraction_body_exposed, field_name="fraction_body_exposed"
        )
        flr_ref = _resolve_scalar_or_collection_float(
            garden_root=garden_root, value=floor_reflectance, field_name="floor_reflectance"
        )
        win_tr = _resolve_scalar_or_collection_float(
            garden_root=garden_root, value=window_transmittance, field_name="window_transmittance"
        )
        exch = indoor_sky_heat_exch(
            longwave_mrt=lw_val,
            diff_horiz_solar=float(diffuse_horizontal_solar or 0.0),
            dir_normal_solar=float(direct_normal_solar or 0.0),
            alt=float(solar_altitude),
            sky_exposure=0.5 if sky_e is None else sky_e,
            fract_exposed=1.0 if frac_e is None else frac_e,
            floor_reflectance=0.25 if flr_ref is None else flr_ref,
            window_transmittance=0.4 if win_tr is None else win_tr,
            posture=parameter.posture if parameter is not None else "seated",
            sharp=(parameter.sharp if parameter is not None and parameter.sharp is not None else 135),
            body_absorptivity=parameter.body_absorptivity if parameter is not None else 0.7,
            body_emissivity=parameter.body_emissivity if parameter is not None else 0.95,
        )
        return {
            "mrt": float(exch["mrt"]),
            "dmrt": float(exch["dmrt"]),
            "erf": float(exch["erf"]),
            "summary_view": {
                "comfort_model": "IndoorSolarCal",
                "mode": "scalar",
                "solar_altitude": float(solar_altitude),
                "longwave_mrt": lw_val,
                "mrt": float(exch["mrt"]),
                "dmrt": float(exch["dmrt"]),
                "erf": float(exch["erf"]),
            },
            "report": make_report(status="ok", message="Scalar Indoor SolarCal MRT computed."),
        }

    epw_obj = (
        _resolve_epw_object(garden_root=garden_root, weather_target=weather_target, epw_path=epw_path)
        if (weather_target is not None or epw_path is not None)
        else None
    )
    if location is not None:
        loc_data = dict(location)
        loc_data.setdefault("type", "Location")
        loc_obj = Location.from_dict(loc_data)
    elif epw_obj is not None:
        loc_obj = epw_obj.location
    else:
        raise ValueError("indoor_solar_mrt requires location or weather_target/epw_path.")

    if sun_up_hours_path and indirect_ill_path:
        return _calculate_solar_mrt_map(
            garden_root=garden_root,
            comfort_model="IndoorSolarCal",
            loc_obj=loc_obj,
            longwave_mrt=longwave_mrt,
            surface_temperatures=surface_temperatures,
            air_temperature_target=air_temperature_target,
            epw_obj=epw_obj,
            sun_up_hours_path=sun_up_hours_path,
            indirect_ill_path=indirect_ill_path,
            direct_ill_path=direct_ill_path,
            reflected_ill_path=reflected_ill_path,
            indirect_is_total=indirect_is_total,
            parameter=parameter,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )

    dir_solar = (
        _load_required_collection(
            garden_root=garden_root,
            target=direct_normal_solar_target,
            field_name="direct_normal_solar_target",
        )
        if direct_normal_solar_target is not None
        else (epw_obj.direct_normal_radiation if epw_obj is not None else None)
    )
    diff_solar = (
        _load_required_collection(
            garden_root=garden_root,
            target=diffuse_horizontal_solar_target,
            field_name="diffuse_horizontal_solar_target",
        )
        if diffuse_horizontal_solar_target is not None
        else (epw_obj.diffuse_horizontal_radiation if epw_obj is not None else None)
    )
    lw_source = (
        longwave_mrt
        if longwave_mrt is not None
        else (
            surface_temperatures
            if surface_temperatures is not None
            else (
                mean_radiant_temperature_target
                if mean_radiant_temperature_target is not None
                else air_temperature_target
            )
        )
    )
    lw_mrt = _load_optional_input(garden_root=garden_root, value=lw_source, field_name="longwave_mrt")
    if lw_mrt is None and epw_obj is not None:
        lw_mrt = epw_obj.dry_bulb_temperature
    if dir_solar is None or diff_solar is None or lw_mrt is None:
        raise ValueError(
            "indoor_solar_mrt requires direct_normal_solar_target, diffuse_horizontal_solar_target, "
            "and longwave_mrt (or weather_target/epw_path)."
        )

    frac_exposed = _load_optional_input(
        garden_root=garden_root, value=fraction_body_exposed, field_name="fraction_body_exposed"
    )
    sky_exp = _load_optional_input(garden_root=garden_root, value=sky_exposure, field_name="sky_exposure")
    floor_ref = _load_optional_input(
        garden_root=garden_root, value=floor_reflectance, field_name="floor_reflectance"
    )
    win_trans = _load_optional_input(
        garden_root=garden_root, value=window_transmittance, field_name="window_transmittance"
    )

    frac_exposed, sky_exp, human_to_sky_info = _maybe_human_to_sky(
        garden_root=garden_root,
        location_obj=loc_obj,
        human_position=human_position,
        human_height=human_height,
        human_point_count=human_point_count,
        context_geometry=context_geometry,
        model_target=model_target,
        north_angle=north_angle,
        frac_exposed=frac_exposed,
        sky_exp=sky_exp,
    )
    if sky_exp is None:
        sky_exp = 0.5  # Matches LB Indoor Solar MRT default (next to an all-glass facade)

    comfort = IndoorSolarCal(
        loc_obj,
        dir_solar,
        diff_solar,
        lw_mrt,
        fraction_body_exposed=frac_exposed,
        sky_exposure=sky_exp,
        floor_reflectance=floor_ref,
        window_transmittance=win_trans,
        solarcal_body_parameter=parameter,
    )
    res = _calculate(
        garden_root=garden_root,
        comfort_model="IndoorSolarCal",
        metric_name="mean_radiant_temperature",
        metric_attribute="mean_radiant_temperature",
        comfort=comfort,
        input_targets={
            "solarcal_type": "indoor",
            "weather_target": weather_target,
            "location": loc_obj.to_dict(),
            "sky_exposure": sky_exp if not hasattr(sky_exp, "values") else "data_collection",
        },
        parameter=parameter,
        identifier=identifier,
        producer="LB_Calculate_Comfort",
        output_metrics=output_metrics,
        return_data_collection=return_data_collection,
    )
    res["summary_view"]["effective_radiant_field"] = data_collection_summary(
        comfort.effective_radiant_field
    )
    res["summary_view"]["mrt_delta"] = data_collection_summary(comfort.mrt_delta)
    if human_to_sky_info is not None:
        res["summary_view"]["human_to_sky"] = human_to_sky_info
    return res


def calculate_outdoor_solar_mrt(
    *,
    garden_root: str,
    location: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    direct_normal_solar_target: dict[str, Any] | None = None,
    diffuse_horizontal_solar_target: dict[str, Any] | None = None,
    horizontal_infrared_target: dict[str, Any] | None = None,
    air_temperature_target: dict[str, Any] | None = None,
    mean_radiant_temperature_target: dict[str, Any] | None = None,
    surface_temperatures: dict[str, Any] | list[float] | float | None = None,
    longwave_mrt: dict[str, Any] | list[float] | float | None = None,
    fraction_body_exposed: dict[str, Any] | list[float] | float | None = None,
    sky_exposure: dict[str, Any] | list[float] | float | None = None,
    floor_reflectance: dict[str, Any] | list[float] | float | None = None,
    solar_altitude: float | None = None,
    direct_normal_solar: float | None = None,
    diffuse_horizontal_solar: float | None = None,
    horizontal_infrared: float | None = None,
    human_position: dict[str, Any] | list[float] | None = None,
    human_height: float = 1.8,
    human_point_count: int = 1,
    context_geometry: list[dict[str, Any]] | None = None,
    model_target: dict[str, Any] | None = None,
    north_angle: float = 0.0,
    sun_up_hours_path: str | None = None,
    indirect_ill_path: str | None = None,
    direct_ill_path: str | None = None,
    reflected_ill_path: str | None = None,
    indirect_is_total: bool = False,
    comfort_parameter: dict[str, Any] | None = None,
    output_metrics: list[str] | None = None,
    identifier: str | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    """Calculate Outdoor Solar MRT (DataCollection/EPW, Radiance map, or scalar SolarCal)."""
    from ladybug_comfort.collection.solarcal import OutdoorSolarCal
    from ladybug_comfort.parameter.solarcal import SolarCalParameter
    from ladybug_comfort.solarcal import outdoor_sky_heat_exch

    parameter = _load_parameter(
        comfort_parameter,
        expected_type="SolarCalParameter",
        parameter_cls=SolarCalParameter,
    )

    is_scalar_mode = (
        solar_altitude is not None
        and weather_target is None
        and epw_path is None
        and direct_normal_solar_target is None
        and diffuse_horizontal_solar_target is None
        and not (sun_up_hours_path and indirect_ill_path)
    )
    if is_scalar_mode:
        srfs_val = _resolve_scalar_or_collection_float(
            garden_root=garden_root,
            value=surface_temperatures if surface_temperatures is not None else longwave_mrt,
            field_name="surface_temperatures",
        )
        if srfs_val is None:
            srfs_val = _resolve_scalar_or_collection_float(
                garden_root=garden_root,
                value=mean_radiant_temperature_target if mean_radiant_temperature_target is not None else air_temperature_target,
                field_name="air_temperature_target",
            )
        hir_val = _resolve_scalar_or_collection_float(
            garden_root=garden_root,
            value=horizontal_infrared if horizontal_infrared is not None else horizontal_infrared_target,
            field_name="horizontal_infrared",
        )
        if srfs_val is None or hir_val is None:
            raise ValueError(
                "Scalar outdoor_solar_mrt requires surface_temperatures (or longwave_mrt) "
                "and horizontal_infrared."
            )
        sky_e = _resolve_scalar_or_collection_float(
            garden_root=garden_root, value=sky_exposure, field_name="sky_exposure"
        )
        frac_e = _resolve_scalar_or_collection_float(
            garden_root=garden_root, value=fraction_body_exposed, field_name="fraction_body_exposed"
        )
        flr_ref = _resolve_scalar_or_collection_float(
            garden_root=garden_root, value=floor_reflectance, field_name="floor_reflectance"
        )
        exch = outdoor_sky_heat_exch(
            srfs_temp=srfs_val,
            horiz_ir=hir_val,
            diff_horiz_solar=float(diffuse_horizontal_solar or 0.0),
            dir_normal_solar=float(direct_normal_solar or 0.0),
            alt=float(solar_altitude),
            sky_exposure=1.0 if sky_e is None else sky_e,
            fract_exposed=1.0 if frac_e is None else frac_e,
            floor_reflectance=0.25 if flr_ref is None else flr_ref,
            posture=parameter.posture if parameter is not None else "standing",
            sharp=(parameter.sharp if parameter is not None and parameter.sharp is not None else 135),
            body_absorptivity=parameter.body_absorptivity if parameter is not None else 0.7,
            body_emissivity=parameter.body_emissivity if parameter is not None else 0.95,
        )
        total_dmrt = float(exch["s_dmrt"]) + float(exch["l_dmrt"])
        total_erf = float(exch["s_erf"]) + float(exch["l_erf"])
        return {
            "mrt": float(exch["mrt"]),
            "s_dmrt": float(exch["s_dmrt"]),
            "l_dmrt": float(exch["l_dmrt"]),
            "dmrt": total_dmrt,
            "s_erf": float(exch["s_erf"]),
            "l_erf": float(exch["l_erf"]),
            "erf": total_erf,
            "summary_view": {
                "comfort_model": "OutdoorSolarCal",
                "mode": "scalar",
                "solar_altitude": float(solar_altitude),
                "surface_temperatures": srfs_val,
                "horizontal_infrared": hir_val,
                "mrt": float(exch["mrt"]),
                "s_dmrt": float(exch["s_dmrt"]),
                "l_dmrt": float(exch["l_dmrt"]),
                "dmrt": total_dmrt,
                "s_erf": float(exch["s_erf"]),
                "l_erf": float(exch["l_erf"]),
                "erf": total_erf,
            },
            "report": make_report(status="ok", message="Scalar Outdoor SolarCal MRT computed."),
        }

    epw_obj = (
        _resolve_epw_object(garden_root=garden_root, weather_target=weather_target, epw_path=epw_path)
        if (weather_target is not None or epw_path is not None)
        else None
    )
    if location is not None:
        loc_data = dict(location)
        loc_data.setdefault("type", "Location")
        loc_obj = Location.from_dict(loc_data)
    elif epw_obj is not None:
        loc_obj = epw_obj.location
    else:
        raise ValueError("outdoor_solar_mrt requires location or weather_target/epw_path.")

    if sun_up_hours_path and indirect_ill_path:
        return _calculate_solar_mrt_map(
            garden_root=garden_root,
            comfort_model="OutdoorSolarCal",
            loc_obj=loc_obj,
            longwave_mrt=longwave_mrt,
            surface_temperatures=surface_temperatures,
            air_temperature_target=air_temperature_target,
            epw_obj=epw_obj,
            sun_up_hours_path=sun_up_hours_path,
            indirect_ill_path=indirect_ill_path,
            direct_ill_path=direct_ill_path,
            reflected_ill_path=reflected_ill_path,
            indirect_is_total=indirect_is_total,
            parameter=parameter,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )

    dir_solar = (
        _load_required_collection(
            garden_root=garden_root,
            target=direct_normal_solar_target,
            field_name="direct_normal_solar_target",
        )
        if direct_normal_solar_target is not None
        else (epw_obj.direct_normal_radiation if epw_obj is not None else None)
    )
    diff_solar = (
        _load_required_collection(
            garden_root=garden_root,
            target=diffuse_horizontal_solar_target,
            field_name="diffuse_horizontal_solar_target",
        )
        if diffuse_horizontal_solar_target is not None
        else (epw_obj.diffuse_horizontal_radiation if epw_obj is not None else None)
    )
    horiz_ir = (
        _load_required_collection(
            garden_root=garden_root,
            target=horizontal_infrared_target,
            field_name="horizontal_infrared_target",
        )
        if horizontal_infrared_target is not None
        else (epw_obj.horizontal_infrared_radiation_intensity if epw_obj is not None else None)
    )
    srfs_source = (
        surface_temperatures
        if surface_temperatures is not None
        else (
            longwave_mrt
            if longwave_mrt is not None
            else (
                mean_radiant_temperature_target
                if mean_radiant_temperature_target is not None
                else air_temperature_target
            )
        )
    )
    surf_temp = _load_optional_input(
        garden_root=garden_root, value=srfs_source, field_name="surface_temperatures"
    )
    if surf_temp is None and epw_obj is not None:
        surf_temp = epw_obj.dry_bulb_temperature
    if dir_solar is None or diff_solar is None or horiz_ir is None or surf_temp is None:
        raise ValueError(
            "outdoor_solar_mrt requires direct_normal_solar_target, diffuse_horizontal_solar_target, "
            "horizontal_infrared_target, and surface_temperatures (or weather_target/epw_path)."
        )

    frac_exposed = _load_optional_input(
        garden_root=garden_root, value=fraction_body_exposed, field_name="fraction_body_exposed"
    )
    sky_exp = _load_optional_input(garden_root=garden_root, value=sky_exposure, field_name="sky_exposure")
    floor_ref = _load_optional_input(
        garden_root=garden_root, value=floor_reflectance, field_name="floor_reflectance"
    )

    frac_exposed, sky_exp, human_to_sky_info = _maybe_human_to_sky(
        garden_root=garden_root,
        location_obj=loc_obj,
        human_position=human_position,
        human_height=human_height,
        human_point_count=human_point_count,
        context_geometry=context_geometry,
        model_target=model_target,
        north_angle=north_angle,
        frac_exposed=frac_exposed,
        sky_exp=sky_exp,
    )
    if sky_exp is None:
        sky_exp = 1.0

    comfort = OutdoorSolarCal(
        loc_obj,
        dir_solar,
        diff_solar,
        horiz_ir,
        surf_temp,
        fraction_body_exposed=frac_exposed,
        sky_exposure=sky_exp,
        floor_reflectance=floor_ref,
        solarcal_body_parameter=parameter,
    )
    res = _calculate(
        garden_root=garden_root,
        comfort_model="OutdoorSolarCal",
        metric_name="mean_radiant_temperature",
        metric_attribute="mean_radiant_temperature",
        comfort=comfort,
        input_targets={
            "solarcal_type": "outdoor",
            "weather_target": weather_target,
            "location": loc_obj.to_dict(),
            "sky_exposure": sky_exp if not hasattr(sky_exp, "values") else "data_collection",
        },
        parameter=parameter,
        identifier=identifier,
        producer="LB_Calculate_Comfort",
        output_metrics=output_metrics,
        return_data_collection=return_data_collection,
    )
    res["summary_view"]["shortwave_effective_radiant_field"] = data_collection_summary(
        comfort.shortwave_effective_radiant_field
    )
    res["summary_view"]["longwave_effective_radiant_field"] = data_collection_summary(
        comfort.longwave_effective_radiant_field
    )
    res["summary_view"]["shortwave_mrt_delta"] = data_collection_summary(
        comfort.shortwave_mrt_delta
    )
    res["summary_view"]["longwave_mrt_delta"] = data_collection_summary(
        comfort.longwave_mrt_delta
    )
    res["summary_view"]["mrt_delta"] = data_collection_summary(comfort.mrt_delta)
    if human_to_sky_info is not None:
        res["summary_view"]["human_to_sky"] = human_to_sky_info
    return res


def calculate_comfort(
    *,
    garden_root: str,
    model: str,
    air_temperature_target: dict[str, Any] | float | int | None = None,
    relative_humidity_target: dict[str, Any] | float | int | None = None,
    mean_radiant_temperature_target: dict[str, Any] | float | int | None = None,
    wind_speed_target: dict[str, Any] | float | int | None = None,
    outdoor_temperature_target: dict[str, Any] | None = None,
    operative_temperature_target: dict[str, Any] | None = None,
    air_speed_target: dict[str, Any] | None = None,
    air_speed: dict[str, Any] | list[float] | float | int | None = None,
    met_rate: dict[str, Any] | list[float] | float | int | None = None,
    clo_value: dict[str, Any] | list[float] | float | int | None = None,
    external_work: dict[str, Any] | list[float] | float | int | None = None,
    barometric_pressure: dict[str, Any] | float | int | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    include_wind: bool = True,
    include_sun: bool = True,
    location: dict[str, Any] | None = None,
    solarcal_type: str = "outdoor",
    direct_normal_solar_target: dict[str, Any] | None = None,
    diffuse_horizontal_solar_target: dict[str, Any] | None = None,
    direct_horizontal_solar_target: dict[str, Any] | None = None,
    reflected_horizontal_solar_target: dict[str, Any] | None = None,
    horizontal_infrared_target: dict[str, Any] | None = None,
    surface_temperatures: dict[str, Any] | list[float] | float | int | None = None,
    longwave_mrt: dict[str, Any] | list[float] | float | int | None = None,
    fraction_body_exposed: dict[str, Any] | list[float] | float | int | None = None,
    sky_exposure: dict[str, Any] | list[float] | float | int | None = None,
    floor_reflectance: dict[str, Any] | list[float] | float | int | None = None,
    window_transmittance: dict[str, Any] | list[float] | float | int | None = None,
    avg_month: bool = True,
    outdoor_temperature: dict[str, Any] | float | int | None = None,
    max_clo: float = 1.0,
    max_clo_temp: float = -5.0,
    min_clo: float = 0.46,
    min_clo_temp: float = 26.0,
    local_discomfort_type: str = "radiant_asymmetry_ppd",
    radiant_temperature_difference: dict[str, Any] | float | int | None = None,
    asymmetry_type: int | str = 0,
    predicted_mean_vote: dict[str, Any] | float | int | None = None,
    air_speed_at_ankle: dict[str, Any] | float | int | None = None,
    heat_stress_index: str = "wbgt",
    dew_point_temperature_target: dict[str, Any] | float | int | None = None,
    strategies: list[str] | dict[str, Any] | None = None,
    passive_strategy_parameters: dict[str, Any] | None = None,
    incident_irradiance_target: dict[str, Any] | None = None,
    merge_polygons: bool = True,
    solar_altitude: float | None = None,
    direct_normal_solar: float | None = None,
    diffuse_horizontal_solar: float | None = None,
    horizontal_infrared: float | None = None,
    human_position: dict[str, Any] | list[float] | None = None,
    human_height: float = 1.8,
    human_point_count: int = 1,
    context_geometry: list[dict[str, Any]] | None = None,
    model_target: dict[str, Any] | None = None,
    north_angle: float = 0.0,
    sun_up_hours_path: str | None = None,
    indirect_ill_path: str | None = None,
    direct_ill_path: str | None = None,
    reflected_ill_path: str | None = None,
    indirect_is_total: bool = False,
    comfort_parameter: dict[str, Any] | None = None,
    output_metrics: list[str] | None = None,
    identifier: str | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    """Calculate PMV, Adaptive, UTCI, PET, SolarCal, Prevailing, Clo, Local Discomfort, or Heat Stress."""
    normalized_model = str(model).strip().lower()
    if normalized_model == "pmv":
        if weather_target is None and epw_path is None and (
            air_temperature_target is None or relative_humidity_target is None
        ):
            raise ValueError(
                "PMV comfort requires air_temperature_target and relative_humidity_target, "
                "or weather_target/epw_path."
            )
        resolved_air_speed = air_speed if air_speed is not None else air_speed_target
        return calculate_pmv(
            garden_root=garden_root,
            air_temperature_target=air_temperature_target if isinstance(air_temperature_target, dict) else None,
            relative_humidity_target=relative_humidity_target if isinstance(relative_humidity_target, dict) else None,
            mean_radiant_temperature_target=mean_radiant_temperature_target if isinstance(mean_radiant_temperature_target, dict) else None,
            air_speed=resolved_air_speed,
            met_rate=met_rate,
            clo_value=clo_value,
            external_work=external_work,
            weather_target=weather_target,
            epw_path=epw_path,
            include_wind=include_wind,
            include_sun=include_sun,
            comfort_parameter=comfort_parameter,
            output_metrics=output_metrics,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )
    if normalized_model == "adaptive":
        if outdoor_temperature_target is None or (
            operative_temperature_target is None and air_temperature_target is None
        ):
            raise ValueError(
                "Adaptive comfort requires outdoor_temperature_target and operative_temperature_target "
                "(or air_temperature_target + optional mean_radiant_temperature_target)."
            )
        resolved_air_speed_target = air_speed_target
        if resolved_air_speed_target is None and isinstance(air_speed, dict):
            resolved_air_speed_target = air_speed
        return calculate_adaptive(
            garden_root=garden_root,
            outdoor_temperature_target=outdoor_temperature_target,
            operative_temperature_target=operative_temperature_target,
            air_temperature_target=air_temperature_target if isinstance(air_temperature_target, dict) else None,
            mean_radiant_temperature_target=mean_radiant_temperature_target if isinstance(mean_radiant_temperature_target, dict) else None,
            air_speed_target=resolved_air_speed_target,
            comfort_parameter=comfort_parameter,
            output_metrics=output_metrics,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )
    if normalized_model == "utci":
        if weather_target is None and epw_path is None and (
            air_temperature_target is None or relative_humidity_target is None
        ):
            raise ValueError(
                "UTCI comfort requires air_temperature_target and relative_humidity_target, "
                "or weather_target/epw_path."
            )
        return calculate_utci(
            garden_root=garden_root,
            air_temperature_target=air_temperature_target if isinstance(air_temperature_target, dict) else None,
            relative_humidity_target=relative_humidity_target if isinstance(relative_humidity_target, dict) else None,
            mean_radiant_temperature_target=mean_radiant_temperature_target if isinstance(mean_radiant_temperature_target, dict) else None,
            wind_speed_target=wind_speed_target if isinstance(wind_speed_target, dict) else None,
            weather_target=weather_target,
            epw_path=epw_path,
            include_wind=include_wind,
            include_sun=include_sun,
            comfort_parameter=comfort_parameter,
            output_metrics=output_metrics,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )
    if normalized_model == "pet":
        if weather_target is None and epw_path is None and (
            air_temperature_target is None or relative_humidity_target is None
        ):
            raise ValueError(
                "PET comfort requires air_temperature_target and relative_humidity_target, "
                "or weather_target/epw_path."
            )
        resolved_air_speed = air_speed if air_speed is not None else air_speed_target
        return calculate_pet(
            garden_root=garden_root,
            air_temperature_target=air_temperature_target if isinstance(air_temperature_target, dict) else None,
            relative_humidity_target=relative_humidity_target if isinstance(relative_humidity_target, dict) else None,
            mean_radiant_temperature_target=mean_radiant_temperature_target if isinstance(mean_radiant_temperature_target, dict) else None,
            air_speed=resolved_air_speed,
            barometric_pressure=barometric_pressure,
            met_rate=met_rate,
            clo_value=clo_value,
            weather_target=weather_target,
            epw_path=epw_path,
            include_wind=include_wind,
            include_sun=include_sun,
            comfort_parameter=comfort_parameter,
            output_metrics=output_metrics,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )
    if normalized_model == "solarcal":
        return calculate_solarcal(
            garden_root=garden_root,
            solarcal_type=solarcal_type,
            location=location,
            weather_target=weather_target,
            epw_path=epw_path,
            direct_normal_solar_target=direct_normal_solar_target,
            diffuse_horizontal_solar_target=diffuse_horizontal_solar_target,
            direct_horizontal_solar_target=direct_horizontal_solar_target,
            reflected_horizontal_solar_target=reflected_horizontal_solar_target,
            horizontal_infrared_target=horizontal_infrared_target,
            surface_temperatures=surface_temperatures,
            longwave_mrt=longwave_mrt,
            fraction_body_exposed=fraction_body_exposed,
            sky_exposure=sky_exposure,
            floor_reflectance=floor_reflectance,
            window_transmittance=window_transmittance,
            comfort_parameter=comfort_parameter,
            output_metrics=output_metrics,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )
    if normalized_model == "prevailing_temperature":
        return _calculate_prevailing_temperature(
            garden_root=garden_root,
            outdoor_temperature_target=outdoor_temperature_target,
            weather_target=weather_target,
            epw_path=epw_path,
            avg_month=avg_month,
            output_metrics=output_metrics,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )
    if normalized_model == "clo_schiavon":
        return _calculate_clo_schiavon(
            garden_root=garden_root,
            outdoor_temperature=outdoor_temperature,
            outdoor_temperature_target=outdoor_temperature_target,
            weather_target=weather_target,
            epw_path=epw_path,
            max_clo=max_clo,
            max_clo_temp=max_clo_temp,
            min_clo=min_clo,
            min_clo_temp=min_clo_temp,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )
    if normalized_model == "local_discomfort":
        return _calculate_local_discomfort(
            garden_root=garden_root,
            local_discomfort_type=local_discomfort_type,
            radiant_temperature_difference=radiant_temperature_difference,
            asymmetry_type=asymmetry_type,
            predicted_mean_vote=predicted_mean_vote,
            air_speed_at_ankle=air_speed_at_ankle,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )
    if normalized_model == "heat_stress":
        return _calculate_heat_stress(
            garden_root=garden_root,
            heat_stress_index=heat_stress_index,
            air_temperature_target=air_temperature_target,
            relative_humidity_target=relative_humidity_target,
            mean_radiant_temperature_target=mean_radiant_temperature_target,
            wind_speed_target=wind_speed_target,
            dew_point_temperature_target=dew_point_temperature_target,
            weather_target=weather_target,
            epw_path=epw_path,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )
    if normalized_model == "passive_strategy":
        resolved_air_speed = air_speed if air_speed is not None else air_speed_target
        return calculate_passive_strategy(
            garden_root=garden_root,
            air_temperature_target=air_temperature_target if isinstance(air_temperature_target, dict) else None,
            relative_humidity_target=relative_humidity_target if isinstance(relative_humidity_target, dict) else None,
            mean_radiant_temperature_target=mean_radiant_temperature_target if isinstance(mean_radiant_temperature_target, dict) else None,
            longwave_mrt=longwave_mrt,
            outdoor_temperature_target=outdoor_temperature_target,
            incident_irradiance_target=incident_irradiance_target,
            barometric_pressure=barometric_pressure,
            air_speed=resolved_air_speed,
            met_rate=met_rate,
            clo_value=clo_value,
            external_work=external_work,
            weather_target=weather_target,
            epw_path=epw_path,
            strategies=strategies,
            passive_strategy_parameters=passive_strategy_parameters,
            merge_polygons=merge_polygons,
            comfort_parameter=comfort_parameter,
            output_metrics=output_metrics,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )
    if normalized_model == "indoor_solar_mrt":
        return calculate_indoor_solar_mrt(
            garden_root=garden_root,
            location=location,
            weather_target=weather_target,
            epw_path=epw_path,
            direct_normal_solar_target=direct_normal_solar_target,
            diffuse_horizontal_solar_target=diffuse_horizontal_solar_target,
            air_temperature_target=air_temperature_target if isinstance(air_temperature_target, dict) else None,
            mean_radiant_temperature_target=mean_radiant_temperature_target if isinstance(mean_radiant_temperature_target, dict) else None,
            surface_temperatures=surface_temperatures,
            longwave_mrt=longwave_mrt,
            fraction_body_exposed=fraction_body_exposed,
            sky_exposure=sky_exposure,
            floor_reflectance=floor_reflectance,
            window_transmittance=window_transmittance,
            solar_altitude=solar_altitude,
            direct_normal_solar=direct_normal_solar,
            diffuse_horizontal_solar=diffuse_horizontal_solar,
            human_position=human_position,
            human_height=human_height,
            human_point_count=human_point_count,
            context_geometry=context_geometry,
            model_target=model_target,
            north_angle=north_angle,
            sun_up_hours_path=sun_up_hours_path,
            indirect_ill_path=indirect_ill_path,
            direct_ill_path=direct_ill_path,
            reflected_ill_path=reflected_ill_path,
            indirect_is_total=indirect_is_total,
            comfort_parameter=comfort_parameter,
            output_metrics=output_metrics,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )
    if normalized_model == "outdoor_solar_mrt":
        return calculate_outdoor_solar_mrt(
            garden_root=garden_root,
            location=location,
            weather_target=weather_target,
            epw_path=epw_path,
            direct_normal_solar_target=direct_normal_solar_target,
            diffuse_horizontal_solar_target=diffuse_horizontal_solar_target,
            horizontal_infrared_target=horizontal_infrared_target,
            air_temperature_target=air_temperature_target if isinstance(air_temperature_target, dict) else None,
            mean_radiant_temperature_target=mean_radiant_temperature_target if isinstance(mean_radiant_temperature_target, dict) else None,
            surface_temperatures=surface_temperatures,
            longwave_mrt=longwave_mrt,
            fraction_body_exposed=fraction_body_exposed,
            sky_exposure=sky_exposure,
            floor_reflectance=floor_reflectance,
            solar_altitude=solar_altitude,
            direct_normal_solar=direct_normal_solar,
            diffuse_horizontal_solar=diffuse_horizontal_solar,
            horizontal_infrared=horizontal_infrared,
            human_position=human_position,
            human_height=human_height,
            human_point_count=human_point_count,
            context_geometry=context_geometry,
            model_target=model_target,
            north_angle=north_angle,
            sun_up_hours_path=sun_up_hours_path,
            indirect_ill_path=indirect_ill_path,
            direct_ill_path=direct_ill_path,
            reflected_ill_path=reflected_ill_path,
            indirect_is_total=indirect_is_total,
            comfort_parameter=comfort_parameter,
            output_metrics=output_metrics,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )
    raise ValueError(
        "model must be one of: pmv, adaptive, utci, pet, solarcal, "
        "prevailing_temperature, clo_schiavon, local_discomfort, heat_stress, "
        "passive_strategy, indoor_solar_mrt, outdoor_solar_mrt."
    )


__all__ = [
    "calculate_adaptive",
    "calculate_comfort",
    "calculate_indoor_solar_mrt",
    "calculate_outdoor_solar_mrt",
    "calculate_passive_strategy",
    "calculate_pet",
    "calculate_pmv",
    "calculate_solarcal",
    "calculate_utci",
]
