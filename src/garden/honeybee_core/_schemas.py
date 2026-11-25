"""Pydantic validation schemas for Honeybee Core batch object creation."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


def _require_non_empty_identifier(value: str) -> str:
    if not value.strip():
        raise ValueError("identifier is required and must not be empty.")
    return value


def _format_item_validation_error(
    exc: ValidationError,
    *,
    index: int,
    context: str,
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
        parts.append(f"unsupported field(s): {', '.join(sorted(set(unsupported)))}")
    if missing:
        parts.append(f"missing required field(s): {', '.join(missing)}")
    if invalid:
        parts.append(f"invalid field(s): {'; '.join(invalid)}")
    detail = "; ".join(parts) if parts else str(exc)
    if unsupported:
        allowed = ", ".join(sorted(accepted_fields))
        return ValueError(f"{context}[{index}]: {detail}. Accepted keys: {allowed}.")
    return ValueError(f"{context}[{index}]: {detail}.")


class RoomBatchItemSpec(BaseModel):
    """Batch item specification for Honeybee Room creation."""

    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(..., min_length=1)
    display_name: str | None = None
    faces: list[dict[str, Any]] | None = None
    room_geometry: dict[str, Any] | None = None
    x_dim: float | None = None
    y_dim: float | None = None
    height: float | None = None
    origin: list[float] | dict[str, Any] | None = None

    @field_validator("identifier")
    @classmethod
    def _validate_identifier(cls, value: str) -> str:
        return _require_non_empty_identifier(value)


class FaceBatchItemSpec(BaseModel):
    """Batch item specification for Honeybee Face creation."""

    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(..., min_length=1)
    display_name: str | None = None
    geometry: dict[str, Any]

    @field_validator("identifier")
    @classmethod
    def _validate_identifier(cls, value: str) -> str:
        return _require_non_empty_identifier(value)


class DoorBatchItemSpec(BaseModel):
    """Batch item specification for Honeybee Door creation."""

    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(..., min_length=1)
    display_name: str | None = None
    host_target: dict[str, Any] | None = None
    geometry: dict[str, Any] | None = None
    is_glass: bool = False
    door_width: float | None = None
    door_height: float = 2.1
    sill_height: float = 0.05
    placement: str = "auto"

    @field_validator("identifier")
    @classmethod
    def _validate_identifier(cls, value: str) -> str:
        return _require_non_empty_identifier(value)


class ApertureBatchItemSpec(BaseModel):
    """Batch item specification for Honeybee Aperture creation."""

    model_config = ConfigDict(extra="forbid")

    mode: str | None = None
    host_target: dict[str, Any] | None = None
    identifier: str | None = None
    geometry: dict[str, Any] | None = None
    is_operable: bool = False
    generation_mode: str | None = "by_ratio"
    ratio: float | None = None
    aperture_width: float | None = None
    aperture_height: float | None = None
    sill_height: float = 1.0
    aperture_identifier: str | None = None
    identifier_prefix: str | None = None
    tolerance: float = 0.01
    rect_split: bool = True
    guide_surfaces: list[dict[str, Any]] | None = None


class ShadeBatchItemSpec(BaseModel):
    """Batch item specification for Honeybee Shade creation."""

    model_config = ConfigDict(extra="forbid")

    identifier: str | None = None
    geometry: dict[str, Any] | None = None
    host_target: dict[str, Any] | None = None
    attach_side: str = "outdoor"
    is_detached: bool = False
    generation_mode: str | None = None
    parameters: dict[str, Any] | None = None


OBJECT_BATCH_ITEM_MODELS: dict[str, type[BaseModel]] = {
    "room": RoomBatchItemSpec,
    "face": FaceBatchItemSpec,
    "door": DoorBatchItemSpec,
}


def _raw_item_mapping(raw_item: Any, *, index: int) -> dict[str, Any]:
    if isinstance(raw_item, BaseModel):
        return raw_item.model_dump(exclude_unset=True)
    if isinstance(raw_item, dict):
        return dict(raw_item)
    raise ValueError(f"items[{index}] must be a dictionary.")


def validate_honeybee_object_batch_items(
    object_type: str,
    items: list[Any],
) -> list[RoomBatchItemSpec | FaceBatchItemSpec | DoorBatchItemSpec]:
    """Validate batch items for create_honeybee_objects_batch."""
    model_cls = OBJECT_BATCH_ITEM_MODELS.get(object_type)
    if model_cls is None:
        raise ValueError("object_type must be one of room, face, or door.")
    validated_items: list[RoomBatchItemSpec | FaceBatchItemSpec | DoorBatchItemSpec] = []
    for index, raw_item in enumerate(items):
        payload = _raw_item_mapping(raw_item, index=index)
        try:
            validated = model_cls.model_validate(payload)
        except ValidationError as exc:
            raise _format_item_validation_error(
                exc,
                index=index,
                context="items",
                accepted_fields=model_cls.model_fields,
            ) from exc
        assert isinstance(validated, (RoomBatchItemSpec, FaceBatchItemSpec, DoorBatchItemSpec))
        validated_items.append(validated)
    return validated_items


def _validate_item_specs_with_default_host(
    items: list[Any],
    *,
    model_cls: type[BaseModel],
    default_host_target: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    validated_specs: list[dict[str, Any]] = []
    for index, raw_item in enumerate(items):
        payload = _raw_item_mapping(raw_item, index=index)
        try:
            validated = model_cls.model_validate(payload)
        except ValidationError as exc:
            raise _format_item_validation_error(
                exc,
                index=index,
                context="items",
                accepted_fields=model_cls.model_fields,
            ) from exc
        # Keep only explicitly supplied fields so top-level batch defaults still apply.
        spec = validated.model_dump(exclude_unset=True)
        if "host_target" not in spec and default_host_target is not None:
            spec["host_target"] = default_host_target
        validated_specs.append(spec)
    return validated_specs


def validate_honeybee_aperture_batch_items(
    items: list[Any],
    *,
    default_host_target: dict[str, Any] | None = None,
    expected_mode: str | None = None,
) -> list[dict[str, Any]]:
    """Validate batch item specs for create_honeybee_apertures_batch."""
    specs = _validate_item_specs_with_default_host(
        items,
        model_cls=ApertureBatchItemSpec,
        default_host_target=default_host_target,
    )
    if expected_mode is not None:
        for index, spec in enumerate(specs):
            item_mode = spec.pop("mode", None)
            if item_mode is not None and str(item_mode).strip() != expected_mode:
                raise ValueError(
                    f"items[{index}].mode ({item_mode!r}) does not match "
                    f"HB_Create_Apertures mode={expected_mode!r}."
                )
    return specs


def validate_honeybee_shade_batch_items(
    items: list[Any],
    *,
    default_host_target: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Validate batch item specs for create_honeybee_shades_batch."""
    return _validate_item_specs_with_default_host(
        items,
        model_cls=ShadeBatchItemSpec,
        default_host_target=default_host_target,
    )


__all__ = [
    "ApertureBatchItemSpec",
    "DoorBatchItemSpec",
    "FaceBatchItemSpec",
    "OBJECT_BATCH_ITEM_MODELS",
    "RoomBatchItemSpec",
    "ShadeBatchItemSpec",
    "validate_honeybee_aperture_batch_items",
    "validate_honeybee_object_batch_items",
    "validate_honeybee_shade_batch_items",
]
