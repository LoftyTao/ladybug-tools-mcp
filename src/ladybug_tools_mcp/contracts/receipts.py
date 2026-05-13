"""Persistence receipt contract helpers."""

from __future__ import annotations

from typing import Any


def make_persistence_receipt(
    *,
    status: str,
    garden_id: str,
    base_honeybee_model_changed: bool = False,
    base_dragonfly_model_changed: bool = False,
    base_fairyfly_model_changed: bool = False,
    warnings: list[str] | None = None,
    model_target: dict[str, Any] | None = None,
    persisted_path: str | None = None,
    change_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the minimal Garden persistence receipt shape."""
    return {
        "status": status,
        "garden_id": garden_id,
        "base_honeybee_model_changed": base_honeybee_model_changed,
        "base_dragonfly_model_changed": base_dragonfly_model_changed,
        "base_fairyfly_model_changed": base_fairyfly_model_changed,
        "warnings": warnings or [],
        "model_target": model_target or {},
        "persisted_path": persisted_path,
        "change_summary": change_summary or {},
    }


def make_artifact_receipt(
    *,
    status: str,
    garden_id: str,
    artifact_type: str,
    artifact_path: str,
    absolute_path: str,
    source: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Build the minimal Garden artifact receipt shape."""
    return {
        "status": status,
        "garden_id": garden_id,
        "artifact_type": artifact_type,
        "artifact_path": artifact_path,
        "absolute_path": absolute_path,
        "source": source or {},
        "warnings": warnings or [],
    }
