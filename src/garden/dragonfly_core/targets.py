"""Dragonfly typed target helpers."""

from __future__ import annotations

from typing import Any

DRAGONFLY_OBJECT_TARGET_TYPE = "dragonfly_object"


def is_dragonfly_model_target(value: Any) -> bool:
    """Return whether a value is a Dragonfly model typed target."""
    return (
        isinstance(value, dict)
        and value.get("target_type") == "dragonfly_model"
        and isinstance(value.get("id"), str)
        and bool(value.get("id"))
    )


def is_dragonfly_object_target(value: Any) -> bool:
    """Return whether a value is a Dragonfly object typed target."""
    return (
        isinstance(value, dict)
        and value.get("target_type") == DRAGONFLY_OBJECT_TARGET_TYPE
        and value.get("domain") == "dragonfly"
        and isinstance(value.get("model_identifier"), str)
        and isinstance(value.get("object_type"), str)
        and isinstance(value.get("object_identifier"), str)
        and bool(value.get("model_identifier"))
        and bool(value.get("object_type"))
        and bool(value.get("object_identifier"))
    )


def normalize_dragonfly_object_target(
    value: Any,
    *,
    expected_type: str | None = None,
) -> dict[str, Any]:
    """Validate one Dragonfly object target dict."""
    if is_dragonfly_object_target(value) and (
        expected_type is None or value.get("object_type") == expected_type
    ):
        return value
    if expected_type:
        raise ValueError(f"Expected a Dragonfly {expected_type} typed target dict.")
    raise ValueError("Expected a Dragonfly object typed target dict.")


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
    target: dict[str, Any] = {
        "target_type": DRAGONFLY_OBJECT_TARGET_TYPE,
        "garden_id": garden_id,
        "domain": "dragonfly",
        "model_identifier": model_identifier,
        "object_type": object_type,
        "object_identifier": object_identifier,
        "identifier": object_identifier,
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
