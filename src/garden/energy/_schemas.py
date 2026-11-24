"""Pydantic validation schemas for Honeybee Energy materials and constructions."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator


def _coerce_mapping(value: Any, *, error_message: str) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(exclude_unset=True)
    if isinstance(value, dict):
        return dict(value)
    raise ValueError(error_message)


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
        field_name = _format_loc(err.get("loc", ()))
        if err_type == "extra_forbidden":
            unsupported.append(field_name)
        elif err_type == "missing":
            missing.append(field_name)
        else:
            msg = err.get("msg", "invalid value")
            invalid.append(f"{field_name} ({msg})" if err.get("loc") else msg)

    parts: list[str] = []
    if unsupported:
        parts.append(f"unsupported field(s): {', '.join(sorted(set(unsupported)))}")
    if missing:
        parts.append(f"missing required field(s): {', '.join(missing)}")
    if invalid:
        parts.append(f"invalid field(s): {'; '.join(invalid)}")
    detail = "; ".join(parts) if parts else str(exc)
    if unsupported and accepted_fields is not None:
        accepted = ", ".join(sorted(accepted_fields))
        return ValueError(f"{prefix}: {detail}. Accepted params: {accepted}.")
    return ValueError(f"{prefix}: {detail}.")


class OpaqueMaterialParams(BaseModel):
    """Parameter schema for material_type='opaque'."""

    model_config = ConfigDict(extra="forbid")

    thickness: float
    conductivity: float
    density: float
    specific_heat: float
    roughness: str = "MediumRough"
    thermal_absorptance: float = 0.9
    solar_absorptance: float = 0.7
    visible_absorptance: float | None = None


class OpaqueNoMassMaterialParams(BaseModel):
    """Parameter schema for material_type='opaque_no_mass'."""

    model_config = ConfigDict(extra="forbid")

    r_value: float
    roughness: str = "MediumRough"
    thermal_absorptance: float = 0.9
    solar_absorptance: float = 0.7
    visible_absorptance: float | None = None


class VegetationMaterialParams(BaseModel):
    """Parameter schema for material_type='vegetation'."""

    model_config = ConfigDict(extra="forbid")

    thickness: float = 0.1
    conductivity: float = 0.35
    density: float = 1100
    specific_heat: float = 1200
    roughness: str = "MediumRough"
    soil_thermal_absorptance: float = 0.9
    soil_solar_absorptance: float = 0.7
    soil_visible_absorptance: float | None = None
    plant_height: float = 0.2
    leaf_area_index: float = 1.0
    leaf_reflectivity: float = 0.22
    leaf_emissivity: float = 0.95
    min_stomatal_resist: float = 180


class SimpleGlazingMaterialParams(BaseModel):
    """Parameter schema for material_type='simple_glazing'."""

    model_config = ConfigDict(extra="forbid")

    u_factor: float
    shgc: float
    vt: float = 0.6


class WindowGlazingMaterialParams(BaseModel):
    """Parameter schema for material_type='window_glazing'."""

    model_config = ConfigDict(extra="forbid")

    thickness: float = 0.003
    solar_transmittance: float = 0.85
    solar_reflectance: float = 0.075
    visible_transmittance: float = 0.9
    visible_reflectance: float = 0.075
    infrared_transmittance: float = 0
    emissivity: float = 0.84
    emissivity_back: float = 0.84
    conductivity: float = 0.9


class WindowGasMaterialParams(BaseModel):
    """Parameter schema for material_type='window_gas'."""

    model_config = ConfigDict(extra="forbid")

    thickness: float = 0.0125
    gas_type: str = "Air"


class WindowGasMixtureMaterialParams(BaseModel):
    """Parameter schema for material_type='window_gas_mixture'."""

    model_config = ConfigDict(extra="forbid")

    thickness: float = 0.0125
    gas_types: list[str] | None = None
    gas_fractions: list[float] | None = None


class WindowGasCustomMaterialParams(BaseModel):
    """Parameter schema for material_type='window_gas_custom'."""

    model_config = ConfigDict(extra="forbid")

    thickness: float
    conductivity_coeff_a: float
    viscosity_coeff_a: float
    specific_heat_coeff_a: float
    conductivity_coeff_b: float = 0
    viscosity_coeff_b: float = 0
    specific_heat_coeff_b: float = 0
    conductivity_coeff_c: float = 0
    viscosity_coeff_c: float = 0
    specific_heat_coeff_c: float = 0
    specific_heat_ratio: float = 1.0
    molecular_weight: float = 20.0


class WindowShadeMaterialParams(BaseModel):
    """Parameter schema for material_type='window_shade'."""

    model_config = ConfigDict(extra="forbid")

    thickness: float = 0.005
    solar_transmittance: float = 0.4
    solar_reflectance: float = 0.5
    visible_transmittance: float = 0.4
    visible_reflectance: float = 0.4
    infrared_transmittance: float = 0
    emissivity: float = 0.9
    conductivity: float = 0.05
    distance_to_glass: float = 0.05
    opening_multiplier: float = 0.5
    airflow_permeability: float = 0.0


class WindowBlindMaterialParams(BaseModel):
    """Parameter schema for material_type='window_blind'."""

    model_config = ConfigDict(extra="forbid")

    slat_orientation: str = "Horizontal"
    slat_width: float = 0.025
    slat_separation: float = 0.01875
    slat_thickness: float = 0.001
    slat_angle: float = 45
    slat_conductivity: float = 221
    solar_transmittance: float = 0
    solar_reflectance: float = 0.5
    visible_transmittance: float = 0
    visible_reflectance: float = 0.5
    infrared_transmittance: float = 0
    emissivity: float = 0.9
    distance_to_glass: float = 0.05
    opening_multiplier: float = 0.5


class WindowFrameMaterialParams(BaseModel):
    """Parameter schema for material_type='window_frame'."""

    model_config = ConfigDict(extra="forbid")

    width: float
    conductance: float
    edge_to_center_ratio: float = 1
    outside_projection: float = 0
    inside_projection: float = 0
    thermal_absorptance: float = 0.9
    solar_absorptance: float = 0.7
    visible_absorptance: float | None = None


MATERIAL_PARAM_MODELS: dict[str, type[BaseModel]] = {
    "opaque": OpaqueMaterialParams,
    "opaque_no_mass": OpaqueNoMassMaterialParams,
    "vegetation": VegetationMaterialParams,
    "simple_glazing": SimpleGlazingMaterialParams,
    "window_glazing": WindowGlazingMaterialParams,
    "window_gas": WindowGasMaterialParams,
    "window_gas_mixture": WindowGasMixtureMaterialParams,
    "window_gas_custom": WindowGasCustomMaterialParams,
    "window_shade": WindowShadeMaterialParams,
    "window_blind": WindowBlindMaterialParams,
    "window_frame": WindowFrameMaterialParams,
}

_MATERIAL_PARAM_ADAPTERS: dict[str, TypeAdapter[BaseModel]] = {
    key: TypeAdapter(model_cls) for key, model_cls in MATERIAL_PARAM_MODELS.items()
}


class OpaqueConstructionParams(BaseModel):
    """Params schema for create_construction(construction_type='opaque')."""

    model_config = ConfigDict(extra="forbid")

    materials: list[dict[str, Any] | str] | None = None


class WindowConstructionParams(BaseModel):
    """Params schema for create_construction(construction_type='window')."""

    model_config = ConfigDict(extra="forbid")

    materials: list[dict[str, Any] | str] | None = None
    u_factor: float | None = None
    shgc: float | None = None
    vt: float = 0.6
    frame: dict[str, Any] | str | None = None


class WindowShadeConstructionParams(BaseModel):
    """Params schema for construction_type='window_shade'."""

    model_config = ConfigDict(extra="forbid")

    window_construction: dict[str, Any] | str
    shade_material: dict[str, Any] | str
    shade_location: str = "Interior"
    control_type: str = "AlwaysOn"
    setpoint: float | None = None
    schedule: dict[str, Any] | str | None = None


class WindowDynamicConstructionParams(BaseModel):
    """Params schema for construction_type='window_dynamic'."""

    model_config = ConfigDict(extra="forbid")

    constructions: list[dict[str, Any] | str]
    schedule: dict[str, Any] | str


class ShadeConstructionParams(BaseModel):
    """Params schema for construction_type='shade'."""

    model_config = ConfigDict(extra="forbid")

    solar_reflectance: float = 0.2
    visible_reflectance: float = 0.2
    is_specular: bool = False


class AirBoundaryConstructionParams(BaseModel):
    """Params schema for construction_type='air_boundary'."""

    model_config = ConfigDict(extra="forbid")

    air_mixing_per_area: float = 0.1
    air_mixing_schedule: dict[str, Any] | str | None = None


CONSTRUCTION_PARAM_MODELS: dict[str, type[BaseModel]] = {
    "opaque": OpaqueConstructionParams,
    "window": WindowConstructionParams,
    "window_shade": WindowShadeConstructionParams,
    "window_dynamic": WindowDynamicConstructionParams,
    "shade": ShadeConstructionParams,
    "air_boundary": AirBoundaryConstructionParams,
}

_CONSTRUCTION_PARAM_ADAPTERS: dict[str, TypeAdapter[BaseModel]] = {
    key: TypeAdapter(model_cls) for key, model_cls in CONSTRUCTION_PARAM_MODELS.items()
}


class InlineOpaqueConstructionSpec(BaseModel):
    """Inline dictionary schema for OpaqueConstruction."""

    model_config = ConfigDict(extra="forbid")

    construction_type: str | None = None
    identifier: str | None = None
    materials: list[dict[str, Any] | str] = Field(..., min_length=1)


class InlineWindowConstructionSpec(BaseModel):
    """Inline dictionary schema for WindowConstruction."""

    model_config = ConfigDict(extra="forbid")

    construction_type: str | None = None
    identifier: str | None = None
    materials: list[dict[str, Any] | str] | None = None
    u_factor: float | None = None
    shgc: float | None = None
    vt: float = 0.6
    frame: dict[str, Any] | str | None = None

    @model_validator(mode="after")
    def _validate_window_source(self) -> InlineWindowConstructionSpec:
        if self.materials is not None:
            if not self.materials:
                raise ValueError("materials must be a non-empty list.")
            return self
        if self.u_factor is None or self.shgc is None:
            raise ValueError("requires materials or both u_factor and shgc.")
        return self


class InlineWindowShadeConstructionSpec(WindowShadeConstructionParams):
    """Inline dictionary schema for WindowConstructionShade."""

    construction_type: str | None = None
    identifier: str | None = None


class InlineWindowDynamicConstructionSpec(WindowDynamicConstructionParams):
    """Inline dictionary schema for WindowConstructionDynamic."""

    construction_type: str | None = None
    identifier: str | None = None


class InlineShadeConstructionSpec(ShadeConstructionParams):
    """Inline dictionary schema for ShadeConstruction."""

    construction_type: str | None = None
    identifier: str | None = None


class InlineAirBoundaryConstructionSpec(AirBoundaryConstructionParams):
    """Inline dictionary schema for AirBoundaryConstruction."""

    construction_type: str | None = None
    identifier: str | None = None


INLINE_CONSTRUCTION_MODELS: dict[str, type[BaseModel]] = {
    "opaque": InlineOpaqueConstructionSpec,
    "window": InlineWindowConstructionSpec,
    "window_shade": InlineWindowShadeConstructionSpec,
    "window_dynamic": InlineWindowDynamicConstructionSpec,
    "shade": InlineShadeConstructionSpec,
    "air_boundary": InlineAirBoundaryConstructionSpec,
}

_INLINE_CONSTRUCTION_ADAPTERS: dict[str, TypeAdapter[BaseModel]] = {
    key: TypeAdapter(model_cls) for key, model_cls in INLINE_CONSTRUCTION_MODELS.items()
}


def validate_material_params(material_type: str, params: Any) -> dict[str, Any]:
    """Validate material creation params for a normalized material_type."""
    adapter = _MATERIAL_PARAM_ADAPTERS.get(material_type)
    model_cls = MATERIAL_PARAM_MODELS.get(material_type)
    if adapter is None or model_cls is None:
        allowed = ", ".join(sorted(MATERIAL_PARAM_MODELS))
        raise ValueError(f"material_type must be one of: {allowed}.")
    raw_params = (
        {}
        if params is None
        else _coerce_mapping(params, error_message="params must be a dictionary.")
    )
    try:
        validated = adapter.validate_python(raw_params)
    except ValidationError as exc:
        raise _format_validation_error(
            exc,
            prefix=f"Invalid params for material_type={material_type!r}",
            accepted_fields=model_cls.model_fields,
        ) from exc
    return validated.model_dump()


def validate_construction_params(construction_type: str, params: Any) -> BaseModel:
    """Validate construction creation params for a normalized construction_type."""
    adapter = _CONSTRUCTION_PARAM_ADAPTERS.get(construction_type)
    model_cls = CONSTRUCTION_PARAM_MODELS.get(construction_type)
    if adapter is None or model_cls is None:
        allowed = ", ".join(CONSTRUCTION_PARAM_MODELS)
        raise ValueError(f"construction_type must be one of: {allowed}.")
    raw_params = (
        {}
        if params is None
        else _coerce_mapping(params, error_message="params must be a dictionary.")
    )
    try:
        return adapter.validate_python(raw_params)
    except ValidationError as exc:
        raise _format_validation_error(
            exc,
            prefix=f"Invalid params for construction_type={construction_type!r}",
            accepted_fields=model_cls.model_fields,
        ) from exc


def validate_inline_construction_dict(
    construction_type: str,
    data: Any,
    *,
    field_name: str,
) -> BaseModel:
    """Validate an inline construction dictionary for a resolved construction_type."""
    adapter = _INLINE_CONSTRUCTION_ADAPTERS.get(construction_type)
    model_cls = INLINE_CONSTRUCTION_MODELS.get(construction_type)
    if adapter is None or model_cls is None:
        raise ValueError(
            f"{field_name} inline construction dictionary has unsupported "
            f"construction_type={construction_type!r}."
        )
    raw_data = _coerce_mapping(
        data,
        error_message=f"{field_name} inline construction must be a dictionary.",
    )
    try:
        return adapter.validate_python(raw_data)
    except ValidationError as exc:
        raise _format_validation_error(
            exc,
            prefix=f"{field_name} invalid {construction_type} construction",
            accepted_fields=model_cls.model_fields,
        ) from exc


__all__ = [
    "AirBoundaryConstructionParams",
    "CONSTRUCTION_PARAM_MODELS",
    "INLINE_CONSTRUCTION_MODELS",
    "InlineAirBoundaryConstructionSpec",
    "InlineOpaqueConstructionSpec",
    "InlineShadeConstructionSpec",
    "InlineWindowConstructionSpec",
    "InlineWindowDynamicConstructionSpec",
    "InlineWindowShadeConstructionSpec",
    "MATERIAL_PARAM_MODELS",
    "OpaqueConstructionParams",
    "OpaqueMaterialParams",
    "OpaqueNoMassMaterialParams",
    "ShadeConstructionParams",
    "SimpleGlazingMaterialParams",
    "VegetationMaterialParams",
    "WindowBlindMaterialParams",
    "WindowConstructionParams",
    "WindowDynamicConstructionParams",
    "WindowFrameMaterialParams",
    "WindowGasCustomMaterialParams",
    "WindowGasMaterialParams",
    "WindowGasMixtureMaterialParams",
    "WindowGlazingMaterialParams",
    "WindowShadeConstructionParams",
    "WindowShadeMaterialParams",
    "validate_construction_params",
    "validate_inline_construction_dict",
    "validate_material_params",
]
