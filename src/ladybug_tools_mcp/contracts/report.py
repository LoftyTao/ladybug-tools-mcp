"""Report contract helpers."""

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
