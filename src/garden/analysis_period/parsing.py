"""Parsing helpers for Ladybug AnalysisPeriod objects."""

from __future__ import annotations

from typing import Any

from ladybug.analysisperiod import AnalysisPeriod


def _unwrap_object_dict(data: Any) -> Any:
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        return data["object_dict"]
    return data


def analysis_period_from_input(
    data: dict[str, Any] | str | None,
    *,
    field_name: str = "analysis_period",
) -> AnalysisPeriod | None:
    """Parse a Ladybug AnalysisPeriod from a dict or SDK string."""
    data = _unwrap_object_dict(data)
    if data is None:
        return None
    try:
        if isinstance(data, str):
            return AnalysisPeriod.from_string(data)
        if isinstance(data, dict):
            return AnalysisPeriod.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"{field_name} must be a valid Ladybug AnalysisPeriod. {exc}") from exc
    raise ValueError(f"{field_name} must be a Ladybug AnalysisPeriod dict or string.")
