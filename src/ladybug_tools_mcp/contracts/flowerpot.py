"""Flowerpot contract helpers."""

from __future__ import annotations

from typing import Any


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
