"""Garden-backed Ladybug thermal comfort calculations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from garden.data_collection import (
    DATA_COLLECTION_TARGET_TYPE,
    data_collection_summary,
    load_data_collection,
    save_data_collection,
)
from garden.manifest import GardenManifest
from ladybug_tools_mcp.contracts.report import make_report


def _load_required_collection(
    *,
    garden_root: str | Path,
    target: dict[str, Any] | None,
    field_name: str,
) -> Any:
    if not isinstance(target, dict):
        raise ValueError(f"{field_name} must be a ladybug_data_collection target.")
    if target.get("target_type") != DATA_COLLECTION_TARGET_TYPE:
        raise ValueError(
            f"{field_name}.target_type must be {DATA_COLLECTION_TARGET_TYPE!r}."
        )
    try:
        collection = load_data_collection(
            garden_root=garden_root,
            data_collection_target=target,
        )
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError(f"Could not load {field_name}: {exc}") from exc
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
    if parameter.get("type") != expected_type:
        raise ValueError(
            f"comfort_parameter.type must be {expected_type!r}; "
            f"got {parameter.get('type')!r}."
        )
    try:
        return parameter_cls.from_dict(parameter)
    except (AssertionError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {expected_type}: {exc}") from exc


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
) -> dict[str, Any]:
    metric = getattr(comfort, metric_attribute)
    header = getattr(metric, "header", None)
    if header is not None:
        header.metadata.update(
            {
                "source": "ladybug_comfort",
                "comfort_model": comfort_model,
                "comfort_metric": metric_name,
            }
        )

    parameter_dict = parameter.to_dict() if parameter is not None else None
    result_identifier = identifier or f"{comfort_model.lower()}_{metric_name}"
    saved = save_data_collection(
        garden_root=garden_root,
        data_collection=metric,
        identifier=result_identifier,
        source={
            "producer": producer,
            "comfort_model": comfort_model,
            "comfort_metric": metric_name,
            "input_targets": input_targets,
            "comfort_parameter": parameter_dict,
        },
    )
    result_summary = data_collection_summary(metric)
    comfort_summary = {
        "comfortable": comfort.percent_comfortable,
        "uncomfortable": comfort.percent_uncomfortable,
        "neutral": comfort.percent_neutral,
        "cold": comfort.percent_cold,
        "hot": comfort.percent_hot,
    }
    summary_view: dict[str, Any] = {
        "garden_target": GardenManifest.read(Path(garden_root).resolve()).target(),
        "comfort_model": comfort_model,
        "comfort_metric": metric_name,
        "input_targets": input_targets,
        "comfort_parameter": parameter_dict,
        "data_collection": result_summary,
        "percentages": comfort_summary,
    }
    if comfort_model == "PMV":
        summary_view["percentage_people_dissatisfied"] = data_collection_summary(
            comfort.percentage_people_dissatisfied
        )
    result = {
        "target": saved["target"],
        "data_target": saved["target"],
        "data_collection_target": saved["target"],
        "artifact": saved["artifact"],
        "persistence_receipt": saved["persistence_receipt"],
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message=f"{comfort_model} comfort DataCollection persisted.",
        ),
    }
    return result


def calculate_utci(
    *,
    garden_root: str,
    air_temperature_target: dict[str, Any],
    relative_humidity_target: dict[str, Any],
    mean_radiant_temperature_target: dict[str, Any] | None = None,
    wind_speed_target: dict[str, Any] | None = None,
    comfort_parameter: dict[str, Any] | None = None,
    identifier: str | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    """Calculate UTCI from Garden DataCollection targets."""
    from ladybug_comfort.collection.utci import UTCI
    from ladybug_comfort.parameter.utci import UTCIParameter

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
    parameter = _load_parameter(
        comfort_parameter,
        expected_type="UTCIParameter",
        parameter_cls=UTCIParameter,
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
    result = _calculate(
        garden_root=garden_root,
        comfort_model="UTCI",
        metric_name="universal_thermal_climate_index",
        metric_attribute="universal_thermal_climate_index",
        comfort=comfort,
        input_targets={
            "air_temperature": air_temperature_target,
            "relative_humidity": relative_humidity_target,
            "mean_radiant_temperature": mean_radiant_temperature_target,
            "wind_speed": wind_speed_target,
        },
        parameter=parameter,
        identifier=identifier,
        producer="LB_calculate_utci",
    )
    if return_data_collection:
        result["data_collection"] = comfort.universal_thermal_climate_index.to_dict()
    return result


def calculate_adaptive(
    *,
    garden_root: str,
    outdoor_temperature_target: dict[str, Any],
    operative_temperature_target: dict[str, Any],
    air_speed_target: dict[str, Any] | None = None,
    comfort_parameter: dict[str, Any] | None = None,
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
    operative_temperature = _load_required_collection(
        garden_root=garden_root,
        target=operative_temperature_target,
        field_name="operative_temperature_target",
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
        comfort = Adaptive(
            outdoor_temperature,
            operative_temperature,
            air_speed=air_speed,
            comfort_parameter=parameter,
        )
    except (AssertionError, TypeError, ValueError) as exc:
        raise ValueError(f"Could not calculate Adaptive comfort: {exc}") from exc
    result = _calculate(
        garden_root=garden_root,
        comfort_model="Adaptive",
        metric_name="degrees_from_neutral",
        metric_attribute="degrees_from_neutral",
        comfort=comfort,
        input_targets={
            "outdoor_temperature": outdoor_temperature_target,
            "operative_temperature": operative_temperature_target,
            "air_speed": air_speed_target,
        },
        parameter=parameter,
        identifier=identifier,
        producer="LB_calculate_adaptive",
    )
    if return_data_collection:
        result["data_collection"] = comfort.degrees_from_neutral.to_dict()
    return result


def calculate_pmv(
    *,
    garden_root: str,
    air_temperature_target: dict[str, Any],
    relative_humidity_target: dict[str, Any],
    mean_radiant_temperature_target: dict[str, Any] | None = None,
    air_speed: dict[str, Any] | float | int | None = None,
    met_rate: dict[str, Any] | float | int | None = None,
    clo_value: dict[str, Any] | float | int | None = None,
    external_work: dict[str, Any] | float | int | None = None,
    comfort_parameter: dict[str, Any] | None = None,
    identifier: str | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    """Calculate PMV from Garden DataCollection targets and scalar inputs."""
    from ladybug_comfort.collection.pmv import PMV
    from ladybug_comfort.parameter.pmv import PMVParameter

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
    result = _calculate(
        garden_root=garden_root,
        comfort_model="PMV",
        metric_name="predicted_mean_vote",
        metric_attribute="predicted_mean_vote",
        comfort=comfort,
        input_targets={
            "air_temperature": air_temperature_target,
            "relative_humidity": relative_humidity_target,
            "mean_radiant_temperature": mean_radiant_temperature_target,
            "air_speed": air_speed if isinstance(air_speed, dict) else None,
            "met_rate": met_rate if isinstance(met_rate, dict) else None,
            "clo_value": clo_value if isinstance(clo_value, dict) else None,
            "external_work": external_work if isinstance(external_work, dict) else None,
        },
        parameter=parameter,
        identifier=identifier,
        producer="LB_calculate_pmv",
    )
    if return_data_collection:
        result["data_collection"] = comfort.predicted_mean_vote.to_dict()
    return result


__all__ = ["calculate_adaptive", "calculate_pmv", "calculate_utci"]
