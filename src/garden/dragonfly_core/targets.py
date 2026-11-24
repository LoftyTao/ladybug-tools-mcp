"""Dragonfly typed target helpers."""

from __future__ import annotations

from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationError

DRAGONFLY_OBJECT_TARGET_TYPE = "dragonfly_object"

_TModel = TypeVar("_TModel", bound=BaseModel)


class DragonflyModelTarget(BaseModel):
    """Pydantic schema for a Dragonfly model typed target."""

    model_config = ConfigDict(extra="allow")

    target_type: Literal["dragonfly_model"]
    id: StrictStr = Field(min_length=1)


class DragonflyObjectTarget(BaseModel):
    """Pydantic schema for a Dragonfly object typed target."""

    model_config = ConfigDict(extra="allow")

    target_type: Literal["dragonfly_object"]
    domain: Literal["dragonfly"]
    model_identifier: StrictStr = Field(min_length=1)
    object_type: StrictStr = Field(min_length=1)
    object_identifier: StrictStr = Field(min_length=1)


def _matches_model(model_cls: type[BaseModel], value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    try:
        model_cls.model_validate(value)
    except ValidationError:
        return False
    return True


def _validate_dict_model(model_cls: type[_TModel], value: Any, error_message: str) -> _TModel:
    if not isinstance(value, dict):
        raise ValueError(error_message)
    try:
        return model_cls.model_validate(value)
    except ValidationError as exc:
        raise ValueError(error_message) from exc


def is_dragonfly_model_target(value: Any) -> bool:
    """Return whether a value is a Dragonfly model typed target."""
    return _matches_model(DragonflyModelTarget, value)


def is_dragonfly_object_target(value: Any) -> bool:
    """Return whether a value is a Dragonfly object typed target."""
    return _matches_model(DragonflyObjectTarget, value)


def normalize_dragonfly_object_target(
    value: Any,
    *,
    expected_type: str | None = None,
) -> dict[str, Any]:
    """Validate one Dragonfly object target dict."""
    error_message = (
        f"Expected a Dragonfly {expected_type} typed target dict."
        if expected_type
        else "Expected a Dragonfly object typed target dict."
    )
    parsed = _validate_dict_model(DragonflyObjectTarget, value, error_message)
    if expected_type is not None and parsed.object_type != expected_type:
        raise ValueError(error_message)
    return parsed.model_dump()


def make_dragonfly_object_target(
    *,
    garden_id: str,
    model_identifier: str,
    object_type: str,
    object_identifier: str,
    parent: dict[str, str] | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    """Build a Dragonfly object typed target."""
    parsed = DragonflyObjectTarget(
        target_type=DRAGONFLY_OBJECT_TARGET_TYPE,
        domain="dragonfly",
        model_identifier=model_identifier,
        object_type=object_type,
        object_identifier=object_identifier,
    )
    target: dict[str, Any] = {
        "target_type": parsed.target_type,
        "garden_id": garden_id,
        "domain": parsed.domain,
        "model_identifier": parsed.model_identifier,
        "object_type": parsed.object_type,
        "object_identifier": parsed.object_identifier,
        "identifier": parsed.object_identifier,
        "parent": parent or {},
    }
    if path:
        target["path"] = path
    return target


def object_summary(target: dict[str, Any], object_dict: dict[str, Any]) -> dict[str, Any]:
    """Build a compact Dragonfly object summary."""
    return {
        "target": target,
        "identifier": object_dict.get("identifier"),
        "display_name": object_dict.get("display_name"),
        "type": object_dict.get("type"),
    }
