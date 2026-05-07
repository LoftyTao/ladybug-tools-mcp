"""Summary helpers for Ladybug AnalysisPeriod objects."""

from __future__ import annotations

from typing import Any

from ladybug.analysisperiod import AnalysisPeriod


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
