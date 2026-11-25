"""Pydantic validation schemas and input normalizers for run_energy tools."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


SimulationParameterMode = Literal[
    "simulation_parameter",
    "output_request",
    "inspect_measures",
]

_UNIT_ALIASES: dict[str, str] = {
    "si": "si",
    "meters": "si",
    "meter": "si",
    "metric": "si",
    "ip": "ip",
    "feet": "ip",
    "foot": "ip",
    "imperial": "ip",
}

_TERRAIN_ALIASES: dict[str, str] = {
    "ocean": "Ocean",
    "country": "Country",
    "suburbs": "Suburbs",
    "urban": "Urban",
    "city": "City",
}

_REPORTING_FREQUENCY_ALIASES: dict[str, str] = {
    "annual": "Annual",
    "monthly": "Monthly",
    "daily": "Daily",
    "hourly": "Hourly",
    "timestep": "Timestep",
}


def normalize_simulation_units(value: Any) -> str:
    """Normalize friendly EnergyPlus unit aliases ('Meters'/'metric', 'Feet'/'imperial') to 'si' or 'ip'."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            "units must be 'si' (or 'meters'/'metric') or 'ip' (or 'feet'/'imperial')."
        )
    key = value.strip().lower()
    canonical = _UNIT_ALIASES.get(key)
    if canonical is None:
        raise ValueError(
            f"Unsupported units {value!r}. Expected 'si' ('meters'/'metric') or 'ip' ('feet'/'imperial')."
        )
    return canonical


def normalize_terrain_type(value: Any) -> str | None:
    """Normalize site terrain_type case-insensitively."""
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("terrain_type must be a non-empty string.")
    canonical = _TERRAIN_ALIASES.get(value.strip().lower())
    if canonical is None:
        allowed = ", ".join(_TERRAIN_ALIASES.values())
        raise ValueError(f"Unsupported terrain_type: {value!r}. Allowed: {allowed}.")
    return canonical


def normalize_reporting_frequency(value: Any) -> str:
    """Normalize EnergyPlus reporting_frequency case-insensitively."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("reporting_frequency must be a non-empty string.")
    canonical = _REPORTING_FREQUENCY_ALIASES.get(value.strip().lower())
    if canonical is None:
        allowed = ", ".join(_REPORTING_FREQUENCY_ALIASES.values())
        raise ValueError(
            f"Unsupported reporting_frequency: {value!r}. Allowed: {allowed}."
        )
    return canonical


def _format_loc(loc: tuple[Any, ...]) -> str:
    return ".".join(str(part) for part in loc) if loc else "input"


def _format_validation_error(
    exc: ValidationError,
    *,
    prefix: str,
    accepted_fields: Iterable[str] | None = None,
) -> ValueError:
    unsupported: list[str] = []
    missing: list[str] = []
    invalid: list[str] = []
    for err in exc.errors():
        err_type = err.get("type", "")
        loc = err.get("loc", ())
        field_name = _format_loc(loc)
        if err_type == "extra_forbidden":
            unsupported.append(field_name)
        elif err_type == "missing":
            missing.append(field_name)
        else:
            msg = err.get("msg", "invalid value")
            invalid.append(f"{field_name} ({msg})" if loc else msg)

    parts: list[str] = []
    if unsupported:
        parts.append(f"unsupported field(s): {', '.join(sorted(set(unsupported)))}")
    if missing:
        parts.append(f"missing required field(s): {', '.join(missing)}")
    if invalid:
        parts.append(f"invalid field(s): {'; '.join(invalid)}")
    detail = "; ".join(parts) if parts else str(exc)
    if accepted_fields is not None and (unsupported or missing):
        accepted = ", ".join(sorted(accepted_fields))
        return ValueError(f"{prefix}: {detail}. Accepted fields: {accepted}.")
    return ValueError(f"{prefix}: {detail}.")


def _coerce_mapping(value: Any, *, field_name: str) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(exclude_unset=True)
    if isinstance(value, dict):
        return dict(value)
    raise ValueError(f"{field_name} must be a dictionary.")


class DaylightSavingTimeInput(BaseModel):
    """Schema for SimulationParameter DaylightSavingTime configuration."""

    model_config = ConfigDict(extra="forbid")

    type: str | None = None
    start_date: Any = None
    end_date: Any = None
    start_month: int | None = None
    start_day: int | None = None
    end_month: int | None = None
    end_day: int | None = None
    leap_year: bool | None = None


class RunPeriodInput(BaseModel):
    """Schema for SimulationParameter RunPeriod configuration."""

    model_config = ConfigDict(extra="forbid")

    type: str | None = None
    start_month: int | None = None
    start_day: int | None = None
    end_month: int | None = None
    end_day: int | None = None
    start_date: Any = None
    end_date: Any = None
    start_day_of_week: str | None = None
    leap_year: bool | None = None
    holidays: list[Any] | None = None
    daylight_saving_time: dict[str, Any] | None = None


class SimulationControlInput(BaseModel):
    """Schema for EnergyPlus SimulationControl toggles."""

    model_config = ConfigDict(extra="forbid")

    type: str | None = None
    do_zone_sizing: bool | None = None
    do_system_sizing: bool | None = None
    do_plant_sizing: bool | None = None
    run_for_sizing_periods: bool | None = None
    run_for_run_periods: bool | None = None


class SizingInput(BaseModel):
    """Schema for SimulationParameter SizingParameter settings."""

    model_config = ConfigDict(extra="forbid")

    heating_factor: float | None = None
    cooling_factor: float | None = None
    efficiency_standard: str | None = None
    climate_zone: str | None = None
    building_type: str | None = None
    bypass_efficiency_sizing: bool | None = None


class ShadowCalculationInput(BaseModel):
    """Schema for EnergyPlus ShadowCalculation settings."""

    model_config = ConfigDict(extra="forbid")

    solar_distribution: str | None = None
    calculation_method: str | None = None
    calculation_update_method: str | None = None
    calculation_frequency: int | None = None
    maximum_figures: int | None = None


class OutputRequestInput(BaseModel):
    """Schema for inline EnergyPlus output_request settings."""

    model_config = ConfigDict(extra="forbid")

    identifier: str | None = None
    presets: list[str] | None = None
    custom_outputs: list[str] | None = None
    summary_reports: list[str] | None = None
    reporting_frequency: str | None = None
    include_sqlite: bool | None = None
    include_html: bool | None = None
    unmet_setpoint_tolerance: float | None = Field(default=None, ge=0.0, le=10.0)

    @field_validator("reporting_frequency")
    @classmethod
    def _validate_reporting_frequency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_reporting_frequency(value)


class MeasureItemInput(BaseModel):
    """Schema for one OpenStudio measure entry."""

    model_config = ConfigDict(extra="forbid")

    folder: str | None = None
    path: str | None = None
    measure_dir_name: str | None = None
    arguments: dict[str, Any] | None = None


def _validate_dict_model(
    value: Any,
    *,
    model_cls: type[BaseModel],
    field_name: str,
) -> dict[str, Any] | None:
    if value is None:
        return None
    mapping = _coerce_mapping(value, field_name=field_name)
    try:
        validated = model_cls.model_validate(mapping)
    except ValidationError as exc:
        raise _format_validation_error(
            exc,
            prefix=field_name,
            accepted_fields=model_cls.model_fields,
        ) from exc
    return validated.model_dump(exclude_unset=True)


def validate_run_period(value: Any) -> dict[str, Any] | None:
    """Validate optional run_period dictionary."""
    return _validate_dict_model(value, model_cls=RunPeriodInput, field_name="run_period")


def validate_sizing(value: Any) -> dict[str, Any] | None:
    """Validate optional sizing dictionary."""
    return _validate_dict_model(value, model_cls=SizingInput, field_name="sizing")


def validate_shadow_calculation(value: Any) -> dict[str, Any] | None:
    """Validate optional shadow_calculation dictionary."""
    return _validate_dict_model(
        value, model_cls=ShadowCalculationInput, field_name="shadow_calculation"
    )


def validate_simulation_control(value: Any) -> dict[str, Any] | None:
    """Validate optional simulation_control dictionary."""
    return _validate_dict_model(
        value, model_cls=SimulationControlInput, field_name="simulation_control"
    )


def validate_daylight_saving_time(value: Any) -> dict[str, Any] | None:
    """Validate optional daylight_saving_time dictionary."""
    return _validate_dict_model(
        value, model_cls=DaylightSavingTimeInput, field_name="daylight_saving_time"
    )


def validate_output_request(value: Any) -> dict[str, Any] | None:
    """Validate optional inline output_request dictionary."""
    return _validate_dict_model(
        value, model_cls=OutputRequestInput, field_name="output_request"
    )


def validate_measures_input(value: Any) -> list[dict[str, Any] | str] | None:
    """Validate optional OpenStudio measure list."""
    if value is None:
        return None
    if not isinstance(value, (list, tuple)):
        raise ValueError(
            "measures must be a list of {folder, arguments} objects or folder strings."
        )
    normalized: list[dict[str, Any] | str] = []
    for index, item in enumerate(value):
        if isinstance(item, str):
            normalized.append(item)
            continue
        mapping = _coerce_mapping(item, field_name=f"measures[{index}]")
        try:
            validated = MeasureItemInput.model_validate(mapping)
        except ValidationError as exc:
            raise _format_validation_error(
                exc,
                prefix=f"measures[{index}]",
                accepted_fields=MeasureItemInput.model_fields,
            ) from exc
        normalized.append(validated.model_dump(exclude_unset=True))
    return normalized


__all__ = [
    "DaylightSavingTimeInput",
    "MeasureItemInput",
    "OutputRequestInput",
    "RunPeriodInput",
    "ShadowCalculationInput",
    "SimulationControlInput",
    "SimulationParameterMode",
    "SizingInput",
    "normalize_reporting_frequency",
    "normalize_simulation_units",
    "normalize_terrain_type",
    "validate_daylight_saving_time",
    "validate_measures_input",
    "validate_output_request",
    "validate_run_period",
    "validate_shadow_calculation",
    "validate_simulation_control",
    "validate_sizing",
]
