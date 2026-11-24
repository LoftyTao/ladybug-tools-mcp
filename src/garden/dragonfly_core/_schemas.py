"""Pydantic validation schemas for Dragonfly Core batch object creation."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

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


__all__ = [
    "DragonflyContextShadeBatchItem",
    "DragonflyRoom2DBatchItem",
    "validate_dragonfly_batch_item",
]
