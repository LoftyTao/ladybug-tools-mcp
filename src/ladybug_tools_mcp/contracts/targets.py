"""Target contract helpers."""

from __future__ import annotations

from typing import Any


def make_garden_target(garden_id: str) -> dict[str, str]:
    """Build a Garden target."""
    return {
        "target_type": "garden",
        "garden_id": garden_id,
    }


def make_garden_version_target(
    garden_id: str,
    version_id: str,
    *,
    short_version_id: str | None = None,
) -> dict[str, str]:
    """Build a Garden version target."""
    target = {
        "target_type": "garden_version",
        "garden_id": garden_id,
        "version_id": version_id,
    }
    if short_version_id:
        target["short_version_id"] = short_version_id
    return target


def make_model_target(
    garden_id: str,
    model_identifier: str,
    *,
    domain: str = "honeybee",
) -> dict[str, str]:
    """Build a model target."""
    return {
        "target_type": "model",
        "garden_id": garden_id,
        "domain": domain,
        "model_identifier": model_identifier,
    }


def make_garden_properties_library_target(
    garden_id: str,
    *,
    domain: str,
    object_family: str,
    identifier: str,
    path: str,
) -> dict[str, str]:
    """Build a Garden Properties Library object target."""
    return {
        "target_type": "garden_properties_library_object",
        "garden_id": garden_id,
        "domain": domain,
        "object_family": object_family,
        "identifier": identifier,
        "path": path,
    }


def target_summary(target: dict[str, Any] | None) -> dict[str, Any]:
    """Build a small target summary for user-facing responses."""
    if target is None:
        return {"has_target": False}
    return {"has_target": True, "target": target}
