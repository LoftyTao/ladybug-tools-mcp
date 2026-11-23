"""Shared public contract helpers for Ladybug Tools MCP tools."""

from __future__ import annotations

from typing import Any


def make_report(
    status: str,
    message: str,
    *,
    warnings: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the minimal report shape used by public tool returns."""
    return {
        "status": status,
        "message": message,
        "warnings": warnings or [],
        "details": details or {},
    }


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


def make_flowerpot(
    *,
    kind: str,
    label: str,
    target: dict[str, Any] | None = None,
    payload_context: dict[str, Any] | None = None,
    platform: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the minimal opaque Flowerpot shape."""
    return {
        "type": "Flowerpot",
        "schema_version": "1",
        "kind": kind,
        "label": label,
        "target": target or {},
        "payload_context": payload_context or {},
        "platform": platform or {},
    }


__all__ = [
    "make_artifact_receipt",
    "make_flowerpot",
    "make_garden_properties_library_target",
    "make_garden_target",
    "make_garden_version_target",
    "make_persistence_receipt",
    "make_report",
]
