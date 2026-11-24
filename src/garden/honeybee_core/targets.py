"""Honeybee typed target helpers."""

from __future__ import annotations

from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationError

_TModel = TypeVar("_TModel", bound=BaseModel)


class HoneybeeModelTarget(BaseModel):
    """Pydantic schema for a Honeybee model typed target."""

    model_config = ConfigDict(extra="allow")

    target_type: Literal["honeybee_model"]
    id: StrictStr = Field(min_length=1)


class HoneybeeObjectTarget(BaseModel):
    """Pydantic schema for a Honeybee object typed target."""

    model_config = ConfigDict(extra="allow")

    target_type: Literal["honeybee_object"]
    domain: Literal["honeybee"]
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


def is_honeybee_model_target(value: Any) -> bool:
    """Return whether a value is a Honeybee model typed target."""
    return _matches_model(HoneybeeModelTarget, value)


def is_honeybee_object_target(value: Any) -> bool:
    """Return whether a value is a Honeybee object typed target."""
    return _matches_model(HoneybeeObjectTarget, value)


def normalize_honeybee_model_target(value: Any) -> dict[str, Any]:
    """Validate and normalize a formal Honeybee model target."""
    parsed = _validate_dict_model(
        HoneybeeModelTarget,
        value,
        "Honeybee model target must be a dict with target_type "
        "'honeybee_model' and a non-empty id.",
    )
    target = parsed.model_dump()
    target["domain"] = "honeybee"
    target["model_identifier"] = parsed.id
    return target


def normalize_honeybee_object_target(value: Any) -> dict[str, Any]:
    """Validate a formal Honeybee object target."""
    parsed = _validate_dict_model(
        HoneybeeObjectTarget,
        value,
        "Expected a Honeybee object typed target dict with target_type "
        "'honeybee_object'. Pass only matches[0].target or a write tool result target.",
    )
    return parsed.model_dump()


def normalize_honeybee_target(value: Any) -> dict[str, Any]:
    """Validate either a Honeybee model target or object target."""
    if is_honeybee_model_target(value):
        return normalize_honeybee_model_target(value)
    if is_honeybee_object_target(value):
        return normalize_honeybee_object_target(value)
    raise ValueError("Expected a Honeybee model or object typed target dict.")


def make_honeybee_object_target(
    *,
    garden_id: str,
    model_identifier: str,
    object_type: str,
    object_identifier: str,
    parent: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a Honeybee object typed target."""
    parsed = HoneybeeObjectTarget(
        target_type="honeybee_object",
        domain="honeybee",
        model_identifier=model_identifier,
        object_type=object_type,
        object_identifier=object_identifier,
    )
    return {
        "target_type": parsed.target_type,
        "garden_id": garden_id,
        "domain": parsed.domain,
        "model_identifier": parsed.model_identifier,
        "object_type": parsed.object_type,
        "object_identifier": parsed.object_identifier,
        "identifier": parsed.object_identifier,
        "parent": parent or {},
    }


def object_summary(target: dict[str, Any], object_dict: dict[str, Any]) -> dict[str, Any]:
    """Build a compact Honeybee object summary."""
    return {
        "target": target,
        "identifier": object_dict.get("identifier"),
        "display_name": object_dict.get("display_name"),
        "type": object_dict.get("type"),
    }
