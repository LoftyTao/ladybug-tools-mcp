"""Ladybug AnalysisPeriod parsing and summary helpers."""

from __future__ import annotations

from typing import Any

from ladybug.analysisperiod import AnalysisPeriod


def analysis_period_from_input(
    data: dict[str, object] | str | None,
    *,
    field_name: str = "analysis_period",
) -> AnalysisPeriod | None:
    """Parse a Ladybug AnalysisPeriod from a dict or SDK string."""
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


def analysis_period_summary(analysis_period: AnalysisPeriod) -> dict[str, Any]:
    """Return a compact summary for a Ladybug AnalysisPeriod."""
    return {
        "type": "AnalysisPeriod",
        "start": {
            "month": analysis_period.st_month,
            "day": analysis_period.st_day,
            "hour": analysis_period.st_hour,
        },
        "end": {
            "month": analysis_period.end_month,
            "day": analysis_period.end_day,
            "hour": analysis_period.end_hour,
        },
        "timestep": analysis_period.timestep,
        "is_leap_year": analysis_period.is_leap_year,
        "is_annual": analysis_period.is_annual,
        "is_reversed": analysis_period.is_reversed,
        "is_overnight": analysis_period.is_overnight,
        "datetime_count": len(analysis_period.datetimes),
    }


__all__ = ["analysis_period_from_input", "analysis_period_summary"]
