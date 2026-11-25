"""Pydantic validation schemas for Dragonfly Core batch creation and property inputs."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


def _require_non_empty_identifier(value: str) -> str:
    if not value.strip():
        raise ValueError("identifier is required and must not be empty.")
    return value


def _format_dragonfly_validation_error(
    exc: ValidationError,
    *,
    object_type: str,
    accepted_fields: Iterable[str],
) -> ValueError:
    unsupported: list[str] = []
    missing: list[str] = []
    invalid: list[str] = []
    for err in exc.errors():
        err_type = err.get("type", "")
        loc = err.get("loc", ())
        field_name = ".".join(str(part) for part in loc) if loc else "item"
        if err_type == "extra_forbidden":
            unsupported.append(field_name)
        elif err_type == "missing":
            missing.append(field_name)
        else:
            msg = err.get("msg", "invalid value")
            invalid.append(f"{field_name} ({msg})" if loc else msg)

    parts: list[str] = []
    if unsupported:
        parts.append(f"unsupported key(s): {', '.join(sorted(set(unsupported)))}")
    if missing:
        parts.append(f"missing required key(s): {', '.join(missing)}")
    if invalid:
        parts.append(f"invalid field(s): {'; '.join(invalid)}")
    detail = "; ".join(parts) if parts else str(exc)
    if unsupported:
        allowed = ", ".join(sorted(accepted_fields))
        return ValueError(
            f"Unsupported or invalid fields for Dragonfly {object_type}: {detail}. "
            f"Accepted keys: {allowed}."
        )
    return ValueError(f"Invalid Dragonfly {object_type} batch item: {detail}.")


class DragonflyRoom2DBatchItem(BaseModel):
    """Batch item specification for Dragonfly Room2D creation."""

    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(..., min_length=1)
    display_name: str | None = None
    floor_height: float | None = None
    vertices: list[list[float]] | None = None
    floor_to_ceiling_height: float | None = None
    model_target: dict[str, Any] | None = None
    is_ground_contact: bool = False
    is_top_exposed: bool = False
    x_dim: float | None = None
    y_dim: float | None = None
    origin: list[float] | None = None
    height: float | None = None
    story_number: int | None = None
    ceiling_plenum_depth: float | None = None
    floor_plenum_depth: float | None = None

    @field_validator("identifier")
    @classmethod
    def _validate_identifier(cls, value: str) -> str:
        return _require_non_empty_identifier(value)


class DragonflyContextShadeBatchItem(BaseModel):
    """Batch item specification for Dragonfly ContextShade creation."""

    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(..., min_length=1)
    geometry: Any = None
    vertices: list[Any] | None = None
    model_target: dict[str, Any] | None = None
    is_detached: bool = True
    x_dim: float | None = None
    y_dim: float | None = None
    height: float | None = None
    origin: list[float] | None = None
    display_name: str | None = None
    context_shade_type: str | None = None
    is_vegetation: bool | None = None
    cen_pt: list[float] | None = None
    radius: float | None = None

    @field_validator("identifier")
    @classmethod
    def _validate_identifier(cls, value: str) -> str:
        return _require_non_empty_identifier(value)


_BATCH_ITEM_MODELS: dict[str, type[BaseModel]] = {
    "room2d": DragonflyRoom2DBatchItem,
    "context_shade": DragonflyContextShadeBatchItem,
}


def validate_dragonfly_batch_item(object_type: str, raw_item: Any) -> dict[str, Any]:
    """Validate one Dragonfly batch creation item and return its set fields."""
    normalized_type = str(object_type or "").strip().lower()
    model_cls = _BATCH_ITEM_MODELS.get(normalized_type)
    if model_cls is None:
        raise ValueError("object_type must be 'room2d' or 'context_shade'.")
    if isinstance(raw_item, BaseModel):
        payload = raw_item.model_dump(exclude_unset=True)
    elif isinstance(raw_item, dict):
        payload = dict(raw_item)
    else:
        raise ValueError("Batch item must be an object definition dictionary.")

    try:
        validated = model_cls.model_validate(payload)
    except ValidationError as exc:
        raise _format_dragonfly_validation_error(
            exc,
            object_type=normalized_type,
            accepted_fields=model_cls.model_fields,
        ) from exc
    return validated.model_dump(exclude_unset=True)


class DragonflyApplyPropertiesInput(BaseModel):
    """Runtime validation schema preserving constraints for slimmed DF_Apply_Properties."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    host_type: Literal["room2d", "story", "building", "context_shade", "model"] | None = None
    program_type_identifier: str | None = None
    construction_set_identifier: str | None = None
    person_count: float | None = Field(default=None, ge=0.0)
    lighting_watts: float | None = Field(default=None, ge=0.0)
    electric_equipment_watts: float | None = Field(default=None, ge=0.0)
    gas_equipment_watts: float | None = Field(default=None, ge=0.0)
    hot_water_flow: float | None = Field(default=None, ge=0.0)
    infiltration_ach: float | None = Field(default=None, ge=0.0)
    daylighting_control: dict[str, Any] | None = None
    daylight_center: dict[str, Any] | None = None
    window_vent_control: dict[str, Any] | None = None
    window_vent_opening: dict[str, Any] | None = None
    fans: list[Any] | None = None
    process_loads: list[Any] | None = None
    diversify: dict[str, Any] | bool | None = None
    modifier_set_identifier: str | None = None
    grid_parameter_type: Literal[
        "room_grid",
        "room_radial_grid",
        "exterior_face_grid",
        "exterior_aperture_grid",
    ] | None = None
    grid_dimension: float | None = Field(default=None, gt=0.0)
    grid_offset: float | None = Field(default=None, ge=0.0)
    face_type: Literal["Wall", "Roof", "Floor", "All", "wall", "roof", "floor", "all"] = "Wall"
    aperture_type: Literal["Window", "Skylight", "All", "window", "skylight", "all"] = "All"
    dir_count: int = Field(default=8, ge=1)
    start_vector: list[float] | None = None
    mesh_radius: float | None = Field(default=None, gt=0.0)
    window_parameter: dict[str, Any] | None = None
    shading_parameter: dict[str, Any] | None = None
    skylight_parameter: dict[str, Any] | None = None
    clerestory_parameter: dict[str, Any] | None = None
    parameter_type: str | None = None
    application_scope: Literal["all_outdoor", "segment_index"] = "all_outdoor"
    segment_index: int | list[int] | None = None
    window_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    window_height: float | None = Field(default=None, gt=0.0)
    sill_height: float | None = Field(default=None, ge=0.0)
    horizontal_separation: float | None = Field(default=None, ge=0.0)
    vertical_separation: float = Field(default=0.0, ge=0.0)
    width: float | None = Field(default=None, gt=0.0)
    height: float | None = Field(default=None, gt=0.0)
    window_area: float | None = Field(default=None, gt=0.0)
    window_width: float | None = Field(default=None, gt=0.0)
    origins: list[list[float]] | None = None
    widths: list[float] | None = None
    heights: list[float] | None = None
    polygons: list[list[list[float]]] | None = None
    are_doors: list[bool] | None = None
    depth: float | None = None
    distance: float | None = Field(default=None, gt=0.0)
    louver_count: int | None = Field(default=None, ge=1)
    contour_vector: list[float] | None = None
    skylight_area: float | None = Field(default=None, gt=0.0)
    skylight_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    spacing: float | str | None = None
    story_identifier: str | None = None
    air_boundary: bool | None = None
    air_boundaries: list[bool] | None = None
    boundary_condition: str | dict[str, Any] | None = None
    guide_lines: list[list[list[float]]] | None = None
    room_identifiers: list[str] | None = None
    wall_modifiers: dict[str, Any] | None = None
    tolerance: float = Field(default=0.01, gt=0.0)


def validate_df_apply_properties_inputs(**kwargs: Any) -> dict[str, Any]:
    """Validate DF_Apply_Properties inputs offloaded from the MCP JSON schema."""
    try:
        validated = DragonflyApplyPropertiesInput.model_validate(kwargs)
    except ValidationError as exc:
        err = exc.errors()[0]
        loc = ".".join(str(part) for part in err.get("loc", ())) or "input"
        raise ValueError(f"Invalid DF_Apply_Properties parameter {loc}: {err.get('msg', exc)}") from exc
    return validated.model_dump()


__all__ = [
    "DragonflyApplyPropertiesInput",
    "DragonflyContextShadeBatchItem",
    "DragonflyRoom2DBatchItem",
    "validate_df_apply_properties_inputs",
    "validate_dragonfly_batch_item",
]
