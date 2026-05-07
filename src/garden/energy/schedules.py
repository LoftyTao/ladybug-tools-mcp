"""Honeybee Energy schedule creation services."""

from __future__ import annotations

from typing import Any

from honeybee_energy.lib.scheduletypelimits import schedule_type_limit_by_identifier
from honeybee_energy.schedule.day import ScheduleDay
from honeybee_energy.schedule.rule import ScheduleRule
from honeybee_energy.schedule.ruleset import ScheduleRuleset
from honeybee_energy.schedule.typelimit import ScheduleTypeLimit
from ladybug.dt import Date, Time

from garden.analysis_period import (
    analysis_period_from_input,
    analysis_period_summary,
)
from ladybug_tools_mcp.contracts.report import make_report
from garden.data_collection import data_collection_summary, save_data_collection
from garden.libraries.properties import save_garden_properties_library_object


def _unwrap_object_dict(data: Any) -> Any:
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        return data["object_dict"]
    return data


def _date_from_input(data: dict[str, Any] | str | None, *, field_name: str) -> Date | None:
    if data is None:
        return None
    try:
        if isinstance(data, str):
            return Date.from_date_string(data)
        return Date.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"{field_name} must be a Ladybug Date dict or date string. {exc}") from exc


def _time_from_input(data: dict[str, Any] | str, *, field_name: str) -> Time:
    try:
        if isinstance(data, str):
            return Time.from_time_string(data)
        return Time.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"{field_name} must be a Ladybug Time dict or time string. {exc}") from exc


def _schedule_day_from_input(data: dict[str, Any], *, field_name: str) -> ScheduleDay:
    data = _unwrap_object_dict(data)
    if not isinstance(data, dict):
        raise ValueError(f"{field_name} must be a ScheduleDay dictionary.")
    try:
        schedule_day = ScheduleDay.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"{field_name} must be a valid ScheduleDay dictionary. {exc}") from exc
    if not isinstance(schedule_day, ScheduleDay):
        raise ValueError(f"{field_name} must resolve to a ScheduleDay.")
    return schedule_day


def _schedule_rule_from_input(data: dict[str, Any], *, field_name: str) -> ScheduleRule:
    data = _unwrap_object_dict(data)
    if not isinstance(data, dict):
        raise ValueError(f"{field_name} must be a ScheduleRule dictionary.")
    try:
        schedule_rule = ScheduleRule.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"{field_name} must be a valid ScheduleRule dictionary. {exc}") from exc
    if not isinstance(schedule_rule, ScheduleRule):
        raise ValueError(f"{field_name} must resolve to a ScheduleRule.")
    return schedule_rule


def _schedule_type_limit_from_input(
    data: dict[str, Any] | str | None,
) -> ScheduleTypeLimit | None:
    data = _unwrap_object_dict(data)
    if data is None:
        return None
    if isinstance(data, str):
        normalized = data.strip()
        aliases = {
            "fraction": "Fractional",
            "fractional": "Fractional",
            "percent": "Percentage",
            "percentage": "Percentage",
            "temperature": "Temperature",
            "onoff": "On/Off",
            "on_off": "On/Off",
            "on/off": "On/Off",
            "activity": "Activity Level",
            "activitylevel": "Activity Level",
            "activity_level": "Activity Level",
            "activity level": "Activity Level",
            "metabolic": "Activity Level",
        }
        data = aliases.get(normalized.lower(), normalized)
        try:
            return schedule_type_limit_by_identifier(data)
        except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
            raise ValueError(f"schedule_type_limit library identifier was not found. {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("schedule_type_limit must be a ScheduleTypeLimit dict or library identifier.")
    try:
        return ScheduleTypeLimit.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"schedule_type_limit must be a valid ScheduleTypeLimit dictionary. {exc}") from exc


def _schedule_day_summary(schedule_day: ScheduleDay) -> dict[str, Any]:
    return {
        "type": "ScheduleDay",
        "identifier": schedule_day.identifier,
        "value_count": len(schedule_day.values),
        "time_count": len(schedule_day.times),
        "is_constant": schedule_day.is_constant,
        "interpolate": schedule_day.interpolate,
    }


def _schedule_day_from_values(
    *,
    identifier: str,
    values: list[float],
    times: list[dict[str, Any] | str] | None = None,
    interpolate: bool = False,
) -> ScheduleDay:
    parsed_times = None
    if times is not None:
        parsed_times = [
            _time_from_input(time, field_name=f"{identifier}.times[{index}]")
            for index, time in enumerate(times)
        ]
    try:
        return ScheduleDay(
            identifier,
            values,
            times=parsed_times,
            interpolate=interpolate,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid ScheduleDay input for {identifier}. {exc}") from exc


def _coerce_rule_days(rule: dict[str, Any]) -> dict[str, bool]:
    day_names = {
        "sunday": "apply_sunday",
        "monday": "apply_monday",
        "tuesday": "apply_tuesday",
        "wednesday": "apply_wednesday",
        "thursday": "apply_thursday",
        "friday": "apply_friday",
        "saturday": "apply_saturday",
    }
    output = {field: bool(rule.get(field, False)) for field in day_names.values()}
    days = rule.get("days") or rule.get("apply_days") or rule.get("weekdays")
    if days is None:
        return output
    if isinstance(days, str):
        lowered = days.strip().lower()
        if lowered in {"weekday", "weekdays", "workday", "workdays"}:
            days = ["monday", "tuesday", "wednesday", "thursday", "friday"]
        elif lowered in {"weekend", "weekends"}:
            days = ["saturday", "sunday"]
        else:
            days = [days]
    if (
        isinstance(days, list)
        and len(days) == 7
        and all(isinstance(day, bool) for day in days)
    ):
        for field, applied in zip(day_names.values(), days):
            output[field] = applied
        return output
    if isinstance(days, list):
        for day in days:
            if isinstance(day, str):
                field = day_names.get(day.strip().lower())
                if field:
                    output[field] = True
    return output


def _rule_from_interval_specs(
    *,
    identifier: str,
    rules: list[dict[str, Any]],
    day_identifier: str | None = None,
) -> ScheduleRule:
    if not rules:
        raise ValueError("rules must contain at least one interval rule.")
    day_flags = _coerce_rule_days(rules[0])
    for index, rule in enumerate(rules[1:], start=1):
        if _coerce_rule_days(rule) != day_flags:
            raise ValueError(
                "rules shorthand currently supports one shared day pattern. "
                f"rules[{index}] uses a different day pattern."
            )

    events: list[tuple[Time, float]] = [(Time(0, 0), 0.0)]
    for index, rule in enumerate(rules):
        raw_start = rule.get("start_time") or rule.get("start")
        raw_end = rule.get("end_time") or rule.get("end")
        if raw_start is None or raw_end is None or "value" not in rule:
            raise ValueError(
                "rules shorthand entries must include start_time, end_time, and value."
            )
        start = _time_from_input(raw_start, field_name=f"rules[{index}].start_time")
        end = _time_from_input(raw_end, field_name=f"rules[{index}].end_time")
        value = float(rule["value"])
        events.append((start, value))
        if end.hour != 0 or end.minute != 0:
            events.append((end, 0.0))

    collapsed: dict[int, float] = {}
    for time, value in events:
        minute_of_day = time.hour * 60 + time.minute
        if not 0 <= minute_of_day <= 1439:
            raise ValueError("rules shorthand times must be within 00:00 through 23:59.")
        collapsed[minute_of_day] = value
    ordered = sorted(collapsed.items())
    day = ScheduleDay(
        day_identifier or f"{identifier}_rule_day",
        [value for _, value in ordered],
        times=[Time(minutes // 60, minutes % 60) for minutes, _ in ordered],
    )
    return ScheduleRule(day, **day_flags)


def _rules_from_interval_specs(
    *,
    identifier: str,
    rules: list[dict[str, Any]],
) -> list[ScheduleRule]:
    if not rules:
        return []
    grouped: dict[tuple[tuple[str, bool], ...], list[dict[str, Any]]] = {}
    for rule in rules:
        day_flags = _coerce_rule_days(rule)
        key = tuple(sorted(day_flags.items()))
        grouped.setdefault(key, []).append(rule)
    if len(grouped) == 1:
        return [_rule_from_interval_specs(identifier=identifier, rules=rules)]
    parsed: list[ScheduleRule] = []
    for index, group_rules in enumerate(grouped.values(), start=1):
        parsed.append(
            _rule_from_interval_specs(
                identifier=identifier,
                rules=group_rules,
                day_identifier=f"{identifier}_rule_day_{index}",
            )
        )
    return parsed


def _schedule_rule_summary(schedule_rule: ScheduleRule) -> dict[str, Any]:
    return {
        "type": "ScheduleRule",
        "schedule_day_identifier": schedule_rule.schedule_day.identifier,
        "start_date": schedule_rule.start_date.to_dict(),
        "end_date": schedule_rule.end_date.to_dict(),
        "days_applied": schedule_rule.days_applied,
    }


def _schedule_ruleset_summary(schedule_ruleset: ScheduleRuleset) -> dict[str, Any]:
    return {
        "type": "ScheduleRuleset",
        "identifier": schedule_ruleset.identifier,
        "rule_count": len(schedule_ruleset.schedule_rules),
        "day_schedule_count": len(schedule_ruleset.day_schedules),
        "default_day_schedule": schedule_ruleset.default_day_schedule.identifier,
        "is_constant": schedule_ruleset.is_constant,
        "schedule_type_limit": (
            schedule_ruleset.schedule_type_limit.identifier
            if schedule_ruleset.schedule_type_limit is not None
            else None
        ),
    }


def create_schedule_day(
    *,
    identifier: str,
    values: list[float],
    times: list[dict[str, Any] | str] | None = None,
    interpolate: bool = False,
) -> dict[str, Any]:
    """Create a Honeybee Energy ScheduleDay."""
    schedule_day = _schedule_day_from_values(
        identifier=identifier,
        values=values,
        times=times,
        interpolate=interpolate,
    )

    return {
        "object_dict": schedule_day.to_dict(),
        "summary_view": _schedule_day_summary(schedule_day),
        "report": make_report(
            status="ok",
            message=f"Created ScheduleDay: {schedule_day.identifier}",
        ),
    }


def create_schedule_rule(
    *,
    schedule_day: dict[str, Any],
    apply_sunday: bool = False,
    apply_monday: bool = False,
    apply_tuesday: bool = False,
    apply_wednesday: bool = False,
    apply_thursday: bool = False,
    apply_friday: bool = False,
    apply_saturday: bool = False,
    start_date: dict[str, Any] | str | None = None,
    end_date: dict[str, Any] | str | None = None,
) -> dict[str, Any]:
    """Create a Honeybee Energy ScheduleRule."""
    schedule_day_obj = _schedule_day_from_input(schedule_day, field_name="_schedule_day")
    start_date_obj = _date_from_input(start_date, field_name="start_date")
    end_date_obj = _date_from_input(end_date, field_name="end_date")
    try:
        schedule_rule = ScheduleRule(
            schedule_day_obj,
            apply_sunday=apply_sunday,
            apply_monday=apply_monday,
            apply_tuesday=apply_tuesday,
            apply_wednesday=apply_wednesday,
            apply_thursday=apply_thursday,
            apply_friday=apply_friday,
            apply_saturday=apply_saturday,
            start_date=start_date_obj,
            end_date=end_date_obj,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid ScheduleRule input. {exc}") from exc

    return {
        "object_dict": schedule_rule.to_dict(),
        "summary_view": _schedule_rule_summary(schedule_rule),
        "report": make_report(
            status="ok",
            message=f"Created ScheduleRule for ScheduleDay: {schedule_day_obj.identifier}",
        ),
    }


def create_schedule_ruleset(
    *,
    identifier: str,
    default_day_schedule: dict[str, Any] | None = None,
    schedule_rules: list[dict[str, Any]] | None = None,
    rules: list[dict[str, Any]] | None = None,
    schedule_type_limit: dict[str, Any] | str | None = None,
    schedule_type: str | None = None,
    default_value: float | None = None,
    summer_designday_schedule: dict[str, Any] | None = None,
    winter_designday_schedule: dict[str, Any] | None = None,
    holiday_schedule: dict[str, Any] | None = None,
    include_data: bool = True,
    data_analysis_period: dict[str, Any] | str | None = None,
    data_timestep: int = 1,
    data_start_date: dict[str, Any] | str | None = None,
    data_end_date: dict[str, Any] | str | None = None,
    data_start_dow: str = "Sunday",
    data_holidays: list[dict[str, Any] | str] | None = None,
    data_leap_year: bool = False,
    garden_root: str | None = None,
    return_data: bool = True,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy ScheduleRuleset."""
    if schedule_type_limit is None and schedule_type is not None:
        schedule_type_limit = schedule_type
    if default_day_schedule is None:
        value = 0.0 if default_value is None else float(default_value)
        default_day = _schedule_day_from_values(
            identifier=f"{identifier}_default_day",
            values=[value],
        )
    else:
        default_day = _schedule_day_from_input(
            default_day_schedule,
            field_name="_default_day_schedule",
        )
    if schedule_rules and rules:
        raise ValueError("Use either schedule_rules SDK dictionaries or rules shorthand, not both.")
    default_day = _schedule_day_from_input(
        default_day.to_dict(),
        field_name="_default_day_schedule",
    )
    parsed_rules = [
        _schedule_rule_from_input(rule, field_name=f"schedule_rules[{index}]")
        for index, rule in enumerate(schedule_rules or [])
    ]
    if rules:
        parsed_rules.extend(_rules_from_interval_specs(identifier=identifier, rules=rules))
    type_limit = _schedule_type_limit_from_input(schedule_type_limit)
    summer_day = (
        _schedule_day_from_input(summer_designday_schedule, field_name="summer_designday_schedule")
        if summer_designday_schedule is not None
        else None
    )
    winter_day = (
        _schedule_day_from_input(winter_designday_schedule, field_name="winter_designday_schedule")
        if winter_designday_schedule is not None
        else None
    )
    holiday_day = (
        _schedule_day_from_input(holiday_schedule, field_name="holiday_schedule")
        if holiday_schedule is not None
        else None
    )
    try:
        schedule_ruleset = ScheduleRuleset(
            identifier,
            default_day,
            schedule_rules=parsed_rules,
            schedule_type_limit=type_limit,
            holiday_schedule=holiday_day,
            summer_designday_schedule=summer_day,
            winter_designday_schedule=winter_day,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid ScheduleRuleset input. {exc}") from exc

    data = None
    data_target = None
    data_persistence_receipt = None
    summary_view = _schedule_ruleset_summary(schedule_ruleset)
    if include_data:
        analysis_period = analysis_period_from_input(
            data_analysis_period,
            field_name="data_analysis_period",
        )
        if analysis_period is None:
            start_date = _date_from_input(data_start_date, field_name="data_start_date") or Date(1, 1)
            end_date = _date_from_input(data_end_date, field_name="data_end_date") or Date(12, 31)
            data_collection_timestep = data_timestep
            data_collection_leap_year = data_leap_year
        else:
            start_date = Date(1, 1)
            end_date = Date(12, 31)
            data_collection_timestep = analysis_period.timestep
            data_collection_leap_year = analysis_period.is_leap_year
            summary_view["analysis_period"] = analysis_period_summary(analysis_period)
        holidays = None
        if data_holidays is not None:
            holidays = [
                _date_from_input(holiday, field_name=f"data_holidays[{index}]")
                for index, holiday in enumerate(data_holidays)
            ]
        try:
            data_collection = schedule_ruleset.data_collection(
                timestep=data_collection_timestep,
                start_date=start_date,
                end_date=end_date,
                start_dow=data_start_dow,
                holidays=holidays,
                leap_year=data_collection_leap_year,
            )
            if analysis_period is not None and not analysis_period.is_annual:
                data_collection = data_collection.filter_by_analysis_period(analysis_period)
        except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
            raise ValueError(f"Could not create ScheduleRuleset data collection. {exc}") from exc
        if return_data:
            data = data_collection.to_dict()
        summary_view["data"] = data_collection_summary(data_collection)
        if garden_root:
            saved_data = save_data_collection(
                garden_root=garden_root,
                data_collection=data_collection,
                identifier=f"{identifier}_data",
                source={
                    "producer": "create_schedule_ruleset",
                    "schedule_identifier": schedule_ruleset.identifier,
                },
            )
            data_target = saved_data["target"]
            data_persistence_receipt = saved_data["persistence_receipt"]
            summary_view["data_target"] = data_target

    result = {
        "object_dict": schedule_ruleset.to_dict(),
        "data": data,
        "data_target": data_target,
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message=f"Created ScheduleRuleset: {schedule_ruleset.identifier}",
        ),
    }
    if data_persistence_receipt is not None:
        result["data_persistence_receipt"] = data_persistence_receipt
    if garden_root:
        saved = save_garden_properties_library_object(
            garden_root=garden_root,
            domain="honeybee_energy",
            object_family="schedule",
            object_dict=result["object_dict"],
        )
        result["target"] = saved["target"]
        result["schedule_target"] = saved["target"]
        result["persistence_receipt"] = saved["persistence_receipt"]
        result["summary_view"]["target"] = saved["target"]
        result["summary_view"]["ready_for"] = (
            "create_program_type schedule fields or edit_honeybee_shade.transmittance_schedule"
        )
        if not return_object_dict:
            result.pop("object_dict", None)
    return result
