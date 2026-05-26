"""Ironbug Garden target helpers."""

from __future__ import annotations

from typing import Any


IRONBUG_MODEL_TARGET_TYPE = "ironbug_model"
IRONBUG_OBJECT_TARGET_TYPE = "ironbug_model_object"


def is_ironbug_model_target(value: Any) -> bool:
    """Return whether a value is an Ironbug model target."""

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
    """Build an Ironbug model target."""

    return {
        "target_type": IRONBUG_MODEL_TARGET_TYPE,
        "id": identifier,
        "identifier": identifier,
        "garden_id": garden_id,
        "domain": "ironbug",
        "path": path,
        "root_type": "IB_Model",
    }


def normalize_ironbug_model_target(value: Any) -> dict[str, Any]:
    """Validate and normalize an Ironbug model target."""

    if not is_ironbug_model_target(value):
        raise ValueError(
            "Ironbug model target must be a dict with target_type "
            "'ironbug_model' and a non-empty id."
        )
    target = dict(value)
    target["domain"] = "ironbug"
    target["identifier"] = str(target["id"])
    target["root_type"] = "IB_Model"
    path = target.get("path")
    if not isinstance(path, str) or not path:
        raise ValueError("Ironbug model target requires a Garden-relative path.")
    return target


def make_ironbug_model_object_target(
    *,
    model_target: dict[str, Any],
    object_type: str,
    object_path: str,
    source_class: str,
    identifier: str,
) -> dict[str, Any]:
    """Build a compact target for an object inside an Ironbug model."""

    normalized_model = normalize_ironbug_model_target(model_target)
    return {
        "target_type": IRONBUG_OBJECT_TARGET_TYPE,
        "garden_id": normalized_model["garden_id"],
        "domain": "ironbug",
        "model_target": normalized_model,
        "object_type": object_type,
        "object_path": object_path,
        "source_class": source_class,
        "identifier": identifier,
    }
