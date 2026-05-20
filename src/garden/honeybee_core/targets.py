"""Honeybee typed target helpers."""

from __future__ import annotations

from typing import Any


def is_honeybee_model_target(value: Any) -> bool:
    """Return whether a value is a Honeybee model typed target."""
    return (
        isinstance(value, dict)
        and value.get("target_type") == "honeybee_model"
        and isinstance(value.get("id"), str)
        and bool(value.get("id"))
    )

def is_honeybee_object_target(value: Any) -> bool:
    """Return whether a value is a Honeybee object typed target."""
    return (
        isinstance(value, dict)
        and value.get("target_type") == "honeybee_object"
        and value.get("domain") == "honeybee"
        and isinstance(value.get("model_identifier"), str)
        and isinstance(value.get("object_type"), str)
        and isinstance(value.get("object_identifier"), str)
        and bool(value.get("model_identifier"))
        and bool(value.get("object_type"))
        and bool(value.get("object_identifier"))
    )


def normalize_honeybee_model_target(value: Any) -> dict[str, Any]:
    """Validate and normalize a formal Honeybee model target."""
    if not is_honeybee_model_target(value):
        raise ValueError(
            "Honeybee model target must be a dict with target_type "
            "'honeybee_model' and a non-empty id."
        )
    target = dict(value)
    target["domain"] = "honeybee"
    target["model_identifier"] = str(target["id"])
    return target


def normalize_honeybee_object_target(value: Any) -> dict[str, Any]:
    """Validate a formal Honeybee object target."""
    if is_honeybee_object_target(value):
        return dict(value)
    raise ValueError(
        "Expected a Honeybee object typed target dict with target_type "
        "'honeybee_object'. Pass only matches[0].target or a write tool result target."
    )


def normalize_honeybee_target(value: Any) -> dict[str, Any]:
    """Validate either a Honeybee model target or object target."""
    if is_honeybee_model_target(value):
        return normalize_honeybee_model_target(value)
    if is_honeybee_object_target(value):
        return dict(value)
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
    return {
        "target_type": "honeybee_object",
        "garden_id": garden_id,
        "domain": "honeybee",
        "model_identifier": model_identifier,
        "object_type": object_type,
        "object_identifier": object_identifier,
        "identifier": object_identifier,
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
