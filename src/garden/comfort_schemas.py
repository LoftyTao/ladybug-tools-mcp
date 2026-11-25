"""Pydantic validation schemas and input normalizers for comfort and DataCollection tools."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from ladybug_tools_mcp.contracts import (
    BuildingModelTargetRef,
    DataCollectionTargetRef,
    WeatherTargetRef,
    dump_input,
)

ComfortModelName = Literal[
    "pmv",
    "adaptive",
    "utci",
    "pet",
    "solarcal",
    "passive_strategy",
    "indoor_solar_mrt",
    "outdoor_solar_mrt",
    "prevailing_temperature",
    "clo_schiavon",
    "local_discomfort",
    "heat_stress",
]

SolarCalVariant = Literal["outdoor", "indoor", "horizontal", "horizontal_ref"]
LocalDiscomfortVariant = Literal["radiant_asymmetry_ppd", "ankle_draft_ppd"]
HeatStressVariant = Literal["wbgt", "hi", "humidex", "wc", "wc_temp", "wc_index", "at", "di"]

DataCollectionAction = Literal[
    "import",
    "create",
    "inspect",
    "filter",
    "aggregate",
    "math",
    "degree_days",
]

DataCollectionType = Literal[
    "HourlyContinuous",
    "HourlyDiscontinuous",
    "Daily",
    "Monthly",
    "MonthlyPerHour",
    "hourly",
    "hourly_continuous",
    "hourlycontinuous",
    "hourly_discontinuous",
    "hourlydiscontinuous",
    "daily",
    "monthly",
    "monthly_per_hour",
    "monthlyperhour",
]

FilterType = Literal[
    "analysis_period",
    "hoys",
    "range",
    "conditional_statement",
    "pattern",
    "statement",
]

AggregationMethod = Literal["average", "avg", "total", "percentile"]
DegreeDayType = Literal["heating", "cooling", "both"]


def _coerce_target(value: Any, ref_cls: type[BaseModel], field_name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    dumped = dump_input(value)
    if not isinstance(dumped, dict):
        raise ValueError(f"{field_name} must be a target dictionary.")
    try:
        return ref_cls.model_validate(dumped).model_dump(exclude_none=True)
    except ValidationError as exc:
        raise ValueError(f"Invalid {field_name}: {exc}") from exc


def _coerce_target_list(
    value: Any, ref_cls: type[BaseModel], field_name: str
) -> list[dict[str, Any]] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list of target dictionaries.")
    return [_coerce_target(item, ref_cls, f"{field_name}[{idx}]") or {} for idx, item in enumerate(value)]


def _coerce_dc_or_numeric(value: Any, field_name: str, *, allow_list: bool = True) -> Any:
    if value is None:
        return None
    dumped = dump_input(value)
    if isinstance(dumped, bool):
        raise ValueError(f"{field_name} must be a number{', list,' if allow_list else ''} or DataCollection target.")
    if isinstance(dumped, (int, float)):
        return dumped
    if allow_list and isinstance(dumped, list):
        for idx, item in enumerate(dumped):
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise ValueError(f"{field_name}[{idx}] must be numeric.")
        return dumped
    if isinstance(dumped, dict):
        if "values" in dumped and "header" in dumped:
            return dumped
        return _coerce_target(dumped, DataCollectionTargetRef, field_name)
    raise ValueError(
        f"{field_name} must be a DataCollection target dict"
        f"{', list of numbers,' if allow_list else ''} or number."
    )


def _coerce_point_input(value: Any, field_name: str) -> dict[str, Any] | list[float] | None:
    if value is None:
        return None
    dumped = dump_input(value)
    if isinstance(dumped, dict):
        return dumped
    if isinstance(dumped, list) and all(
        not isinstance(v, bool) and isinstance(v, (int, float)) for v in dumped
    ):
        return [float(v) for v in dumped]
    raise ValueError(f"{field_name} must be a [x, y, z] list or Point3D dict.")


class ComfortCalculationArgs(BaseModel):
    """Validated top-level arguments for ``LB_Calculate_Comfort``."""

    model_config = ConfigDict(extra="forbid")

    garden_root: str
    model: ComfortModelName
    weather_target: dict[str, Any] | None = None
    epw_path: str | None = None
    include_wind: bool = True
    include_sun: bool = True
    location: dict[str, Any] | None = None
    solarcal_type: SolarCalVariant = "outdoor"
    direct_normal_solar_target: dict[str, Any] | None = None
    diffuse_horizontal_solar_target: dict[str, Any] | None = None
    direct_horizontal_solar_target: dict[str, Any] | None = None
    reflected_horizontal_solar_target: dict[str, Any] | None = None
    horizontal_infrared_target: dict[str, Any] | None = None
    surface_temperatures: Any = None
    longwave_mrt: Any = None
    fraction_body_exposed: Any = None
    sky_exposure: Any = None
    floor_reflectance: Any = None
    window_transmittance: Any = None
    avg_month: bool = True
    outdoor_temperature: Any = None
    max_clo: float = 1.0
    max_clo_temp: float = -5.0
    min_clo: float = 0.46
    min_clo_temp: float = 26.0
    local_discomfort_type: LocalDiscomfortVariant = "radiant_asymmetry_ppd"
    radiant_temperature_difference: Any = None
    asymmetry_type: int | str = 0
    predicted_mean_vote: Any = None
    air_speed_at_ankle: Any = None
    heat_stress_index: HeatStressVariant = "wbgt"
    dew_point_temperature_target: dict[str, Any] | None = None
    output_metrics: list[str] | None = None
    air_temperature_target: dict[str, Any] | None = None
    relative_humidity_target: dict[str, Any] | None = None
    mean_radiant_temperature_target: dict[str, Any] | None = None
    wind_speed_target: dict[str, Any] | None = None
    outdoor_temperature_target: dict[str, Any] | None = None
    operative_temperature_target: dict[str, Any] | None = None
    air_speed_target: dict[str, Any] | None = None
    air_speed: Any = None
    met_rate: Any = None
    clo_value: Any = None
    external_work: Any = None
    barometric_pressure: Any = None
    strategies: list[str] | dict[str, Any] | None = None
    passive_strategy_parameters: dict[str, Any] | None = None
    incident_irradiance_target: dict[str, Any] | None = None
    merge_polygons: bool = True
    solar_altitude: float | None = None
    direct_normal_solar: float | None = None
    diffuse_horizontal_solar: float | None = None
    horizontal_infrared: float | None = None
    human_position: dict[str, Any] | list[float] | None = None
    human_height: float = 1.8
    human_point_count: int = 1
    context_geometry: list[dict[str, Any]] | None = None
    model_target: dict[str, Any] | None = None
    north_angle: float = 0.0
    sun_up_hours_path: str | None = None
    indirect_ill_path: str | None = None
    direct_ill_path: str | None = None
    reflected_ill_path: str | None = None
    indirect_is_total: bool = False
    comfort_parameter: dict[str, Any] | None = None
    identifier: str | None = None
    return_data_collection: bool = False

    @field_validator("max_clo", "min_clo")
    @classmethod
    def _validate_non_negative_clo(cls, value: float) -> float:
        if value < 0.0:
            raise ValueError("clo bounds must be >= 0.")
        return value

    @field_validator("solar_altitude")
    @classmethod
    def _validate_solar_altitude(cls, value: float | None) -> float | None:
        if value is not None and not (-90.0 <= value <= 90.0):
            raise ValueError("solar_altitude must be between -90 and 90 degrees.")
        return value

    @field_validator("direct_normal_solar", "diffuse_horizontal_solar", "horizontal_infrared")
    @classmethod
    def _validate_non_negative_solar(cls, value: float | None) -> float | None:
        if value is not None and value < 0.0:
            raise ValueError("Solar/infrared irradiance must be >= 0.")
        return value

    @field_validator("human_height")
    @classmethod
    def _validate_human_height(cls, value: float) -> float:
        if value <= 0.0:
            raise ValueError("human_height must be > 0.")
        return value

    @field_validator("human_point_count")
    @classmethod
    def _validate_human_point_count(cls, value: int) -> int:
        if value < 1:
            raise ValueError("human_point_count must be >= 1.")
        return value


def normalize_comfort_inputs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize ``LB_Calculate_Comfort`` arguments into service kwargs."""
    cleaned = dict(kwargs)
    cleaned["weather_target"] = _coerce_target(
        cleaned.get("weather_target"), WeatherTargetRef, "weather_target"
    )
    cleaned["model_target"] = _coerce_target(
        cleaned.get("model_target"), BuildingModelTargetRef, "model_target"
    )
    for field_name in (
        "direct_normal_solar_target",
        "diffuse_horizontal_solar_target",
        "direct_horizontal_solar_target",
        "reflected_horizontal_solar_target",
        "horizontal_infrared_target",
        "dew_point_temperature_target",
        "air_temperature_target",
        "relative_humidity_target",
        "mean_radiant_temperature_target",
        "wind_speed_target",
        "outdoor_temperature_target",
        "operative_temperature_target",
        "air_speed_target",
        "incident_irradiance_target",
    ):
        cleaned[field_name] = _coerce_target(
            cleaned.get(field_name), DataCollectionTargetRef, field_name
        )

    for field_name in (
        "surface_temperatures",
        "longwave_mrt",
        "fraction_body_exposed",
        "sky_exposure",
        "floor_reflectance",
        "window_transmittance",
        "outdoor_temperature",
        "radiant_temperature_difference",
        "predicted_mean_vote",
        "air_speed_at_ankle",
        "air_speed",
        "met_rate",
        "clo_value",
        "external_work",
    ):
        cleaned[field_name] = _coerce_dc_or_numeric(cleaned.get(field_name), field_name)

    cleaned["barometric_pressure"] = _coerce_dc_or_numeric(
        cleaned.get("barometric_pressure"), "barometric_pressure", allow_list=False
    )
    cleaned["human_position"] = _coerce_point_input(
        cleaned.get("human_position"), "human_position"
    )
    cleaned["strategies"] = dump_input(cleaned.get("strategies"))
    cleaned["comfort_parameter"] = dump_input(cleaned.get("comfort_parameter"))
    cleaned["passive_strategy_parameters"] = dump_input(cleaned.get("passive_strategy_parameters"))
    cleaned["location"] = dump_input(cleaned.get("location"))
    cleaned["context_geometry"] = dump_input(cleaned.get("context_geometry"))

    try:
        validated = ComfortCalculationArgs.model_validate(cleaned)
    except ValidationError as exc:
        raise ValueError(f"Invalid LB_Calculate_Comfort parameters: {exc}") from exc
    return validated.model_dump()


class DataCollectionAnalysisArgs(BaseModel):
    """Validated top-level arguments for ``LB_Analyze_Data_Collection``."""

    model_config = ConfigDict(extra="forbid")

    garden_root: str
    action: DataCollectionAction
    data_collection: dict[str, Any] | None = None
    data_collection_target: dict[str, Any] | None = None
    data_collections: list[dict[str, Any]] | None = None
    data_collection_targets: list[dict[str, Any]] | None = None
    source_path: str | None = None
    values: list[float] | None = None
    collection_type: DataCollectionType = "HourlyContinuous"
    header: dict[str, Any] | None = None
    data_type: str | None = None
    unit: str | None = None
    analysis_period: dict[str, Any] | str | None = None
    metadata: dict[str, Any] | None = None
    datetimes: list[str | dict[str, Any]] | None = None
    percentiles: list[float] | None = None
    histogram_bins: int = 10
    include_values: bool = False
    max_values: int = 24
    filter_type: FilterType | None = None
    hoys: list[float] | None = None
    greater_than: float | None = None
    less_than: float | None = None
    conditional_statement: str | None = None
    pattern: list[bool | int] | None = None
    operation: str | None = None
    aggregation_method: AggregationMethod = "average"
    percentile_value: float = 50.0
    timestep: int = 1
    cumulative: bool | None = None
    area: float | None = None
    area_unit: str = "m2"
    target_unit: str | None = None
    scalar: float | None = None
    other_data_collection: dict[str, Any] | None = None
    other_data_collection_target: dict[str, Any] | None = None
    base_temperature: float | None = None
    heating_base_temperature: float = 18.0
    cooling_base_temperature: float = 23.0
    degree_day_type: DegreeDayType = "both"
    identifier: str | None = None
    return_data_collection: bool = False

    @model_validator(mode="after")
    def _validate_bounds(self) -> DataCollectionAnalysisArgs:
        if self.histogram_bins < 1:
            raise ValueError("histogram_bins must be >= 1.")
        if self.max_values < 1:
            raise ValueError("max_values must be >= 1.")
        if not (0.0 <= self.percentile_value <= 100.0):
            raise ValueError("percentile_value must be between 0 and 100.")
        if self.timestep < 1:
            raise ValueError("timestep must be >= 1.")
        if self.area is not None and self.area <= 0.0:
            raise ValueError("area must be > 0.")
        return self


def normalize_data_collection_inputs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize ``LB_Analyze_Data_Collection`` arguments into service kwargs."""
    cleaned = dict(kwargs)
    cleaned["data_collection"] = dump_input(cleaned.get("data_collection"))
    cleaned["data_collections"] = dump_input(cleaned.get("data_collections"))
    cleaned["data_collection_target"] = _coerce_target(
        cleaned.get("data_collection_target"), DataCollectionTargetRef, "data_collection_target"
    )
    cleaned["data_collection_targets"] = _coerce_target_list(
        cleaned.get("data_collection_targets"), DataCollectionTargetRef, "data_collection_targets"
    )
    cleaned["other_data_collection"] = dump_input(cleaned.get("other_data_collection"))
    cleaned["other_data_collection_target"] = _coerce_target(
        cleaned.get("other_data_collection_target"),
        DataCollectionTargetRef,
        "other_data_collection_target",
    )
    cleaned["analysis_period"] = dump_input(cleaned.get("analysis_period"))
    cleaned["header"] = dump_input(cleaned.get("header"))
    cleaned["metadata"] = dump_input(cleaned.get("metadata"))
    cleaned["datetimes"] = dump_input(cleaned.get("datetimes"))

    try:
        validated = DataCollectionAnalysisArgs.model_validate(cleaned)
    except ValidationError as exc:
        raise ValueError(f"Invalid LB_Analyze_Data_Collection parameters: {exc}") from exc
    return validated.model_dump()


__all__ = [
    "AggregationMethod",
    "ComfortCalculationArgs",
    "ComfortModelName",
    "DataCollectionAction",
    "DataCollectionAnalysisArgs",
    "DataCollectionType",
    "DegreeDayType",
    "FilterType",
    "HeatStressVariant",
    "LocalDiscomfortVariant",
    "SolarCalVariant",
    "normalize_comfort_inputs",
    "normalize_data_collection_inputs",
]
