"""Ironbug Garden target helpers."""

from __future__ import annotations

from typing import Any

IRONBUG_MODEL_TARGET_TYPE = "ironbug_model"


def is_ironbug_model_target(value: Any) -> bool:
    """Return whether a value is an Ironbug system target."""
    return (
        isinstance(value, dict)
        and value.get("target_type") == IRONBUG_MODEL_TARGET_TYPE
        and isinstance(value.get("id"), str)
        and bool(value.get("id"))
    )


def make_ironbug_model_target(
    *,
    garden_id: str,
    identifier: str,
    path: str,
) -> dict[str, Any]:
    """Build an Ironbug system target."""
    return {
        "target_type": IRONBUG_MODEL_TARGET_TYPE,
        "id": identifier,
        "identifier": identifier,
        "garden_id": garden_id,
        "domain": "ironbug",
        "path": path,
        "root_type": "IB_HVACSystem",
    }


def normalize_ironbug_model_target(value: Any) -> dict[str, Any]:
    """Validate and normalize an Ironbug system target."""
    if not is_ironbug_model_target(value):
        raise ValueError(
            "ironbug_model_target must be a dict with target_type 'ironbug_model' "
            "and a non-empty id."
        )
    target = dict(value)
    target["domain"] = "ironbug"
    target["identifier"] = str(target["id"])
    target["root_type"] = "IB_HVACSystem"
    path = target.get("path")
    if not isinstance(path, str) or not path:
        raise ValueError("ironbug_model_target requires a Garden-relative path.")
    return target
