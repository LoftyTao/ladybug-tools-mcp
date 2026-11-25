"""Pydantic validation schemas and input normalizers for visualization chart tools."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from ladybug_tools_mcp.contracts import (
    DataCollectionTargetRef,
    RunTargetRef,
    dump_input,
)

ChartType = Literal[
    "hourly_plot",
    "monthly_chart",
    "psychrometric_chart",
    "adaptive_chart",
    "windrose",
]
ChartExportFormat = Literal["visualization_set", "html"]
MonthlyChartTimeInterval = Literal[
    "as_is",
    "hourly",
    "daily",
    "monthly",
    "monthly_per_hour",
    "total_daily",
    "total_monthly",
    "total_monthly_per_hour",
]


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


def _coerce_axis_bounds(value: Any, field_name: str) -> list[float | None] | float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number or list of numbers/null.")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        out: list[float | None] = []
        for idx, item in enumerate(value):
            if item is None:
                out.append(None)
            elif isinstance(item, bool) or not isinstance(item, (int, float)):
                raise ValueError(f"{field_name}[{idx}] must be a number or null.")
            else:
                out.append(float(item))
        return out
    raise ValueError(f"{field_name} must be a number, list of numbers/null, or null.")


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


class ChartVisualizationArgs(BaseModel):
    """Validated top-level arguments for ``LB_Chart_To_Visualization_Set``."""

    model_config = ConfigDict(extra="forbid")

    chart_type: ChartType
    export_format: ChartExportFormat = "visualization_set"
    garden_root: str | None = None
    legend_parameter: dict[str, Any] | None = None
    x_dim: float | None = None
    y_dim: float | None = None
    width: int | None = None
    height: int | None = None
    name: str | None = None
    output_subdir: str | None = None
    return_visualization_set: bool = True
    energy_run_target: dict[str, Any] | None = None
    run_id: str | None = None
    output_name: str | None = None
    collection_index: int = 0
    run_period_index: int | None = None
    data_collection: dict[str, Any] | None = None
    data_collection_target: dict[str, Any] | None = None
    series: list[dict[str, Any]] | None = None
    time_interval: MonthlyChartTimeInterval = "as_is"
    chart_title: str | None = None
    y_axis_title: str | None = None
    stack: bool = False
    percentile: float = 34
    time_marks: bool = False
    temperature_target: dict[str, Any] | None = None
    relative_humidity_target: dict[str, Any] | None = None
    strategy_layers: list[dict[str, Any]] | None = None
    average_pressure: float = 101325
    base_point: dict[str, Any] | list[float] | None = None
    min_temperature: float = -20
    max_temperature: float = 50
    max_humidity_ratio: float = 0.03
    use_ip: bool = False
    z: float = 0
    plot_wet_bulb: bool = False
    direction_data_collection: dict[str, Any] | None = None
    direction_data_collection_target: dict[str, Any] | None = None
    analysis_data_collection: dict[str, Any] | None = None
    analysis_data_collection_target: dict[str, Any] | None = None
    direction_count: int = 36
    calm_threshold: float = 1e-10
    analysis_period: dict[str, Any] | str | None = None
    north: float = 0.0
    show_zeros: bool = False
    frequency_labels: bool = True
    z_dim: float = 0.0
    reverse_y: bool = False
    custom_hours: list[int] | None = None
    y_axis_min: list[float | None] | float | None = None
    y_axis_max: list[float | None] | float | None = None
    comfort_polygon: dict[str, Any] | None = None
    include_passive_strategies: bool = True
    passive_strategy_parameters: dict[str, Any] | None = None
    passive_strategies: list[str] | None = None
    incident_irradiance_target: dict[str, Any] | None = None
    outdoor_temperature_target: dict[str, Any] | None = None
    operative_temperature_target: dict[str, Any] | None = None
    air_temperature_target: dict[str, Any] | None = None
    mean_radiant_temperature_target: dict[str, Any] | None = None
    air_speed_target: dict[str, Any] | None = None
    wind_speed_target: dict[str, Any] | None = None
    comfort_parameter: dict[str, Any] | None = None
    min_prevailing: float = 10
    max_prevailing: float = 33
    min_operative: float = 14
    max_operative: float = 40

    @field_validator("x_dim", "y_dim", "average_pressure", "max_humidity_ratio")
    @classmethod
    def _validate_positive_float(cls, value: float | None) -> float | None:
        if value is not None and value <= 0.0:
            raise ValueError("Dimension/pressure/humidity ratio overrides must be > 0.")
        return value

    @field_validator("width", "height")
    @classmethod
    def _validate_positive_pixel_hint(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("width and height must be >= 1 when provided.")
        return value

    @field_validator("collection_index", "run_period_index")
    @classmethod
    def _validate_non_negative_index(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("Index fields must be >= 0.")
        return value

    @field_validator("percentile")
    @classmethod
    def _validate_percentile(cls, value: float) -> float:
        if not (0.0 <= value <= 100.0):
            raise ValueError("percentile must be between 0 and 100.")
        return value

    @field_validator("direction_count")
    @classmethod
    def _validate_direction_count(cls, value: int) -> int:
        if value < 3:
            raise ValueError("direction_count must be >= 3.")
        return value

    @field_validator("calm_threshold")
    @classmethod
    def _validate_calm_threshold(cls, value: float) -> float:
        if value < 0.0:
            raise ValueError("calm_threshold must be >= 0.")
        return value


def normalize_chart_inputs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize ``LB_Chart_To_Visualization_Set`` arguments."""
    cleaned = dict(kwargs)
    cleaned["energy_run_target"] = _coerce_target(
        cleaned.get("energy_run_target"), RunTargetRef, "energy_run_target"
    )
    for field_name in (
        "data_collection_target",
        "temperature_target",
        "relative_humidity_target",
        "direction_data_collection_target",
        "analysis_data_collection_target",
        "incident_irradiance_target",
        "outdoor_temperature_target",
        "operative_temperature_target",
        "air_temperature_target",
        "mean_radiant_temperature_target",
        "air_speed_target",
        "wind_speed_target",
    ):
        cleaned[field_name] = _coerce_target(
            cleaned.get(field_name), DataCollectionTargetRef, field_name
        )

    for field_name in (
        "legend_parameter",
        "data_collection",
        "series",
        "strategy_layers",
        "direction_data_collection",
        "analysis_data_collection",
        "analysis_period",
        "comfort_polygon",
        "passive_strategy_parameters",
        "comfort_parameter",
    ):
        cleaned[field_name] = dump_input(cleaned.get(field_name))

    cleaned["base_point"] = _coerce_point_input(cleaned.get("base_point"), "base_point")
    cleaned["y_axis_min"] = _coerce_axis_bounds(cleaned.get("y_axis_min"), "y_axis_min")
    cleaned["y_axis_max"] = _coerce_axis_bounds(cleaned.get("y_axis_max"), "y_axis_max")

    try:
        validated = ChartVisualizationArgs.model_validate(cleaned)
    except ValidationError as exc:
        raise ValueError(f"Invalid LB_Chart_To_Visualization_Set parameters: {exc}") from exc
    return validated.model_dump()


__all__ = [
    "ChartExportFormat",
    "ChartType",
    "ChartVisualizationArgs",
    "MonthlyChartTimeInterval",
    "normalize_chart_inputs",
]
