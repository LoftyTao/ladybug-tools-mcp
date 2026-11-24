"""Honeybee Energy schedule creation services."""

from __future__ import annotations

from typing import Any

from honeybee.altnumber import no_limit
from honeybee_energy.lib.scheduletypelimits import schedule_type_limit_by_identifier
from honeybee_energy.schedule.day import ScheduleDay
from honeybee_energy.schedule.fixedinterval import ScheduleFixedInterval
from honeybee_energy.schedule.rule import ScheduleRule
from honeybee_energy.schedule.ruleset import ScheduleRuleset
from honeybee_energy.schedule.typelimit import ScheduleTypeLimit
from ladybug.dt import Date, Time

from garden.analysis_period import (
    analysis_period_from_input,
    analysis_period_summary,
)
from ladybug_tools_mcp.contracts import make_report
from garden.data_collection import data_collection_summary, save_data_collection
from garden.libraries.properties import (
    get_garden_properties_library_object,
    save_garden_properties_library_object,
)


def _date_from_input(data: dict[str, Any] | list[Any] | tuple[Any, ...] | str | None, *, field_name: str) -> Date | None:
    if data is None:
        return None
    if isinstance(data, Date):
        return data
    try:
        if isinstance(data, str):
            text = data.strip()
            try:
                return Date.from_date_string(text)
            except ValueError:
                if "/" in text:
                    parts = [int(part.strip()) for part in text.split("/")]
                    if len(parts) == 2:
                        return Date(parts[0], parts[1])
                    if len(parts) == 3:
                        return Date(parts[1], parts[2])
                if "-" in text:
                    parts = [int(part.strip()) for part in text.split("-")]
                    if len(parts) == 2:
                        return Date(parts[0], parts[1])
                    if len(parts) == 3:
                        return Date(parts[1], parts[2])
                raise
        if isinstance(data, (list, tuple)) and len(data) in {2, 3}:
            leap_year = bool(data[2]) if len(data) == 3 else False
            return Date(int(data[0]), int(data[1]), leap_year)
        return Date.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"{field_name} must be a Ladybug Date dict or date string. {exc}") from exc


def _time_from_input(data: dict[str, Any] | list[Any] | tuple[Any, ...] | int | float | str, *, field_name: str) -> Time:
    if isinstance(data, Time):
        return data
    try:
        if isinstance(data, str):
            return Time.from_time_string(data)
        if isinstance(data, (int, float)) and not isinstance(data, bool):
            hour = int(data)
            minute = int(round((float(data) - hour) * 60))
            return Time(hour, minute)
        if isinstance(data, (list, tuple)) and len(data) == 2:
            return Time(int(data[0]), int(data[1]))
        return Time.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"{field_name} must be a Ladybug Time dict or time string. {exc}") from exc


def _schedule_day_from_input(
    data: dict[str, Any] | list[Any] | tuple[Any, ...] | int | float | ScheduleDay,
    *,
    field_name: str,
    default_identifier: str | None = None,
) -> ScheduleDay:
    if isinstance(data, ScheduleDay):
        return data
    if isinstance(data, (int, float)) and not isinstance(data, bool):
        return _schedule_day_from_values(
            identifier=default_identifier or f"{field_name}_day",
            values=[float(data)],
        )
    if isinstance(data, (list, tuple)):
        return _schedule_day_from_values(
            identifier=default_identifier or f"{field_name}_day",
            values=[float(item) for item in data],
        )
    if not isinstance(data, dict):
        raise ValueError(
            f"{field_name} must be a ScheduleDay dictionary, inline day spec, or 24-value list."
        )
    if data.get("type") == "ScheduleDay":
        try:
            schedule_day = ScheduleDay.from_dict(data)
        except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
            if "values" not in data:
                raise ValueError(f"{field_name} must be a valid ScheduleDay dictionary. {exc}") from exc
        else:
            if not isinstance(schedule_day, ScheduleDay):
                raise ValueError(f"{field_name} must resolve to a ScheduleDay.")
            return schedule_day
    if "values" in data:
        unknown = sorted(set(data) - {"type", "identifier", "display_name", "values", "times", "interpolate"})
        if unknown:
            raise ValueError(
                f"{field_name} contains unsupported ScheduleDay field(s): {', '.join(unknown)}."
            )
        raw_values = data["values"]
        if not isinstance(raw_values, (list, tuple)):
            raise ValueError(f"{field_name}.values must be a list of numbers.")
        return _schedule_day_from_values(
            identifier=str(data.get("identifier") or default_identifier or f"{field_name}_day"),
            values=[float(item) for item in raw_values],
            times=data.get("times"),
            interpolate=bool(data.get("interpolate", False)),
        )
    if "value" in data:
        unknown = sorted(set(data) - {"type", "identifier", "value", "interpolate"})
        if unknown:
            raise ValueError(
                f"{field_name} contains unsupported ScheduleDay field(s): {', '.join(unknown)}."
            )
        return _schedule_day_from_values(
            identifier=str(data.get("identifier") or default_identifier or f"{field_name}_day"),
            values=[float(data["value"])],
            interpolate=bool(data.get("interpolate", False)),
        )
    try:
        schedule_day = ScheduleDay.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"{field_name} must be a valid ScheduleDay dictionary. {exc}") from exc
    if not isinstance(schedule_day, ScheduleDay):
        raise ValueError(f"{field_name} must resolve to a ScheduleDay.")
    return schedule_day


def _schedule_rule_from_input(
    data: dict[str, Any] | ScheduleRule,
    *,
    field_name: str,
    default_day_identifier: str | None = None,
) -> ScheduleRule:
    if isinstance(data, ScheduleRule):
        return data
    if not isinstance(data, dict):
        raise ValueError(f"{field_name} must be a ScheduleRule dictionary.")
    if data.get("type") == "ScheduleRule":
        try:
            schedule_rule = ScheduleRule.from_dict(data)
        except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
            if not any(key in data for key in ("schedule_day", "day", "values")):
                raise ValueError(f"{field_name} must be a valid ScheduleRule dictionary. {exc}") from exc
        else:
            if not isinstance(schedule_rule, ScheduleRule):
                raise ValueError(f"{field_name} must resolve to a ScheduleRule.")
            return schedule_rule

    if "schedule_day" in data:
        day_input = data["schedule_day"]
    elif "day" in data:
        day_input = data["day"]
    elif "values" in data:
        day_input = {
            key: data[key]
            for key in ("identifier", "values", "times", "interpolate")
            if key in data
        }
    else:
        try:
            schedule_rule = ScheduleRule.from_dict(data)
        except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
            raise ValueError(
                f"{field_name} must include schedule_day, day, or values for an inline ScheduleRule. {exc}"
            ) from exc
        if not isinstance(schedule_rule, ScheduleRule):
            raise ValueError(f"{field_name} must resolve to a ScheduleRule.")
        return schedule_rule

    allowed_rule_fields = {
        "type",
        "schedule_day",
        "day",
        "identifier",
        "values",
        "times",
        "interpolate",
        "apply_sunday",
        "apply_monday",
        "apply_tuesday",
        "apply_wednesday",
        "apply_thursday",
        "apply_friday",
        "apply_saturday",
        "days",
        "apply_days",
        "weekdays",
        "start_date",
        "end_date",
    }
    unknown = sorted(set(data) - allowed_rule_fields)
    if unknown:
        raise ValueError(
            f"{field_name} contains unsupported ScheduleRule field(s): {', '.join(unknown)}."
        )
    schedule_day_obj = _schedule_day_from_input(
        day_input,
        field_name=f"{field_name}.schedule_day",
        default_identifier=default_day_identifier or f"{field_name}_day",
    )
    day_flags = _coerce_rule_days(data)
    start_date_obj = _date_from_input(data.get("start_date"), field_name=f"{field_name}.start_date")
    end_date_obj = _date_from_input(data.get("end_date"), field_name=f"{field_name}.end_date")
    try:
        return ScheduleRule(
            schedule_day_obj,
            **day_flags,
            start_date=start_date_obj,
            end_date=end_date_obj,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid ScheduleRule input in {field_name}. {exc}") from exc


def _schedule_type_limit_from_input(
    data: dict[str, Any] | str | None,
    *,
    garden_root: str | None = None,
) -> ScheduleTypeLimit | None:
    if data is None:
        return None
    if isinstance(data, dict) and data.get("target_type") == "garden_properties_library_object":
        if garden_root is None:
            raise ValueError("schedule_type_limit target requires garden_root.")
        if data.get("domain") != "honeybee_energy" or data.get("object_family") != "schedule_type_limit":
            raise ValueError(
                "schedule_type_limit target must reference honeybee_energy:schedule_type_limit."
            )
        data = get_garden_properties_library_object(
            garden_root=garden_root,
            target=data,
        )["object_dict"]
    if isinstance(data, dict) and "type" not in data and isinstance(data.get("identifier"), str) and set(data) == {"identifier"}:
        data = data["identifier"]
    if isinstance(data, str):
        try:
            return schedule_type_limit_by_identifier(data)
        except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
            if garden_root is not None:
                try:
                    return ScheduleTypeLimit.from_dict(
                        get_garden_properties_library_object(
                            garden_root=garden_root,
                            domain="honeybee_energy",
                            object_family="schedule_type_limit",
                            identifier=data,
                        )["object_dict"]
                    )
                except Exception:
                    pass
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
    times: list[dict[str, Any] | list[Any] | tuple[Any, ...] | int | float | str] | None = None,
    interpolate: bool = False,
) -> ScheduleDay:
    numeric_values = [float(value) for value in values]
    parsed_times = None
    if times is not None:
        parsed_times = [
            _time_from_input(time, field_name=f"{identifier}.times[{index}]")
            for index, time in enumerate(times)
        ]
    elif len(numeric_values) == 24:
        parsed_times = [Time(hour, 0) for hour in range(24)]
    elif len(numeric_values) != 1:
        raise ValueError(
            f"ScheduleDay {identifier} without times must contain 1 constant value or 24 hourly values; got {len(numeric_values)}."
        )
    try:
        return ScheduleDay(
            identifier,
            numeric_values,
            times=parsed_times,
            interpolate=interpolate,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid ScheduleDay input for {identifier}. {exc}") from exc


def _coerce_rule_days(rule: dict[str, Any]) -> dict[str, bool]:
    day_names = {
        "sunday": "apply_sunday",
        "sun": "apply_sunday",
        "monday": "apply_monday",
        "mon": "apply_monday",
        "tuesday": "apply_tuesday",
        "tue": "apply_tuesday",
        "tues": "apply_tuesday",
        "wednesday": "apply_wednesday",
        "wed": "apply_wednesday",
        "thursday": "apply_thursday",
        "thu": "apply_thursday",
        "thur": "apply_thursday",
        "thurs": "apply_thursday",
        "friday": "apply_friday",
        "fri": "apply_friday",
        "saturday": "apply_saturday",
        "sat": "apply_saturday",
    }
    ordered_fields = (
        "apply_sunday",
        "apply_monday",
        "apply_tuesday",
        "apply_wednesday",
        "apply_thursday",
        "apply_friday",
        "apply_saturday",
    )
    output = {field: bool(rule.get(field, False)) for field in ordered_fields}
    days = rule.get("days") if "days" in rule else rule.get("apply_days") if "apply_days" in rule else rule.get("weekdays")
    if days is None:
        return output
    if isinstance(days, str):
        lowered = days.strip().lower()
        if lowered in {"weekday", "weekdays", "workday", "workdays"}:
            days = ["monday", "tuesday", "wednesday", "thursday", "friday"]
        elif lowered in {"weekend", "weekends"}:
            days = ["saturday", "sunday"]
        elif lowered in {"all", "everyday", "daily", "all_days"}:
            days = list(ordered_fields)
            for field in days:
                output[field] = True
            return output
        else:
            days = [days]
    if (
        isinstance(days, (list, tuple))
        and len(days) == 7
        and all(isinstance(day, bool) for day in days)
    ):
        for field, applied in zip(ordered_fields, days):
            output[field] = applied
        return output
    if isinstance(days, (list, tuple)):
        for day in days:
            if isinstance(day, str):
                token = day.strip().lower()
                if token in {"weekday", "weekdays", "workday", "workdays"}:
                    for field in ("apply_monday", "apply_tuesday", "apply_wednesday", "apply_thursday", "apply_friday"):
                        output[field] = True
                elif token in {"weekend", "weekends"}:
                    for field in ("apply_saturday", "apply_sunday"):
                        output[field] = True
                elif token in {"all", "everyday", "daily", "all_days"}:
                    for field in ordered_fields:
                        output[field] = True
                else:
                    field = day_names.get(token)
                    if field:
                        output[field] = True
                    else:
                        raise ValueError(f"Unsupported weekday label: {day!r}.")
    return output


def _date_key(date: Date | None) -> tuple[int, int, bool] | None:
    if date is None:
        return None
    return (date.month, date.day, bool(date.leap_year))


def _rule_from_interval_specs(
    *,
    identifier: str,
    rules: list[dict[str, Any]],
    day_identifier: str | None = None,
) -> ScheduleRule:
    if not rules:
        raise ValueError("rules must contain at least one interval rule.")
    day_flags = _coerce_rule_days(rules[0])
    start_date_obj = _date_from_input(rules[0].get("start_date"), field_name="rules[0].start_date")
    end_date_obj = _date_from_input(rules[0].get("end_date"), field_name="rules[0].end_date")
    expected_dates = (_date_key(start_date_obj), _date_key(end_date_obj))
    for index, rule in enumerate(rules[1:], start=1):
        if _coerce_rule_days(rule) != day_flags:
            raise ValueError(
                "rules shorthand currently supports one shared day pattern. "
                f"rules[{index}] uses a different day pattern."
            )
        rule_start = _date_from_input(rule.get("start_date"), field_name=f"rules[{index}].start_date")
        rule_end = _date_from_input(rule.get("end_date"), field_name=f"rules[{index}].end_date")
        if (_date_key(rule_start), _date_key(rule_end)) != expected_dates:
            raise ValueError(
                "rules shorthand group must share one start_date/end_date range. "
                f"rules[{index}] uses a different date range."
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
    return ScheduleRule(day, **day_flags, start_date=start_date_obj, end_date=end_date_obj)


def _rules_from_interval_specs(
    *,
    identifier: str,
    rules: list[dict[str, Any]],
) -> list[ScheduleRule]:
    if not rules:
        return []
    grouped: dict[
        tuple[tuple[tuple[str, bool], ...], tuple[tuple[int, int, bool] | None, tuple[int, int, bool] | None]],
        list[dict[str, Any]],
    ] = {}
    for index, rule in enumerate(rules):
        day_flags = _coerce_rule_days(rule)
        start_date_obj = _date_from_input(rule.get("start_date"), field_name=f"rules[{index}].start_date")
        end_date_obj = _date_from_input(rule.get("end_date"), field_name=f"rules[{index}].end_date")
        key = (
            tuple(sorted(day_flags.items())),
            (_date_key(start_date_obj), _date_key(end_date_obj)),
        )
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


def _schedule_fixed_interval_summary(schedule: ScheduleFixedInterval) -> dict[str, Any]:
    return {
        "type": "ScheduleFixedInterval",
        "identifier": schedule.identifier,
        "value_count": len(schedule.values),
        "timestep": schedule.timestep,
        "start_date": schedule.start_date.to_dict(),
        "end_date_time": str(schedule.end_date_time),
        "placeholder_value": schedule.placeholder_value,
        "interpolate": schedule.interpolate,
        "is_constant": schedule.is_constant,
        "is_leap_year": schedule.is_leap_year,
        "schedule_type_limit": (
            schedule.schedule_type_limit.identifier
            if schedule.schedule_type_limit is not None
            else None
        ),
    }


def _schedule_type_limit_summary(type_limit: ScheduleTypeLimit) -> dict[str, Any]:
    return {
        "type": "ScheduleTypeLimit",
        "identifier": type_limit.identifier,
        "lower_limit": None if type_limit.lower_limit == no_limit else type_limit.lower_limit,
        "upper_limit": None if type_limit.upper_limit == no_limit else type_limit.upper_limit,
        "numeric_type": type_limit.numeric_type,
        "unit_type": type_limit.unit_type,
    }


def _limit_bound_from_input(value: float | str | None, *, field_name: str) -> Any:
    if value is None:
        return no_limit
    if isinstance(value, str):
        normalized = value.strip().lower().replace("_", "").replace("-", "").replace(" ", "")
        if normalized in {"nolimit", "unlimited", "none", ""}:
            return no_limit
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a number or 'no_limit'.") from exc
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number or 'no_limit'.")
    return float(value)


def create_schedule_type_limit(
    *,
    identifier: str,
    lower_limit: float | str | None = None,
    upper_limit: float | str | None = None,
    numeric_type: str = "Continuous",
    unit_type: str = "Dimensionless",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy ScheduleTypeLimit."""
    try:
        type_limit = ScheduleTypeLimit(
            identifier,
            lower_limit=_limit_bound_from_input(lower_limit, field_name="lower_limit"),
            upper_limit=_limit_bound_from_input(upper_limit, field_name="upper_limit"),
            numeric_type=numeric_type,
            unit_type=unit_type,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid ScheduleTypeLimit input. {exc}") from exc

    result: dict[str, Any] = {
        "object_dict": type_limit.to_dict(),
        "data": None,
        "data_target": None,
        "summary_view": _schedule_type_limit_summary(type_limit),
        "report": make_report(
            status="ok",
            message=f"Created ScheduleTypeLimit: {type_limit.identifier}",
        ),
    }
    if garden_root:
        saved = save_garden_properties_library_object(
            garden_root=garden_root,
            domain="honeybee_energy",
            object_family="schedule_type_limit",
            object_dict=result["object_dict"],
        )
        result["target"] = saved["target"]
        result["persistence_receipt"] = saved["persistence_receipt"]
        result["summary_view"]["target"] = saved["target"]
        result["summary_view"]["ready_for"] = (
            "EP_Create_Schedule_Ruleset.schedule_type_limit"
        )
        if not return_object_dict:
            result.pop("object_dict", None)
    return result


def create_schedule_fixed_interval(
    *,
    identifier: str,
    values: list[float],
    schedule_type_limit: dict[str, Any] | str | None = None,
    timestep: int = 1,
    start_date: dict[str, Any] | list[Any] | str | None = None,
    placeholder_value: float = 0.0,
    interpolate: bool = False,
    include_data: bool = True,
    data_analysis_period: dict[str, Any] | str | None = None,
    data_timestep: int | None = None,
    data_start_date: dict[str, Any] | str | None = None,
    data_end_date: dict[str, Any] | str | None = None,
    garden_root: str | None = None,
    return_data: bool = True,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy ScheduleFixedInterval."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("schedule_type='fixed_interval' requires a non-empty list of numeric values.")
    type_limit = _schedule_type_limit_from_input(schedule_type_limit, garden_root=garden_root)
    start_date_obj = _date_from_input(start_date, field_name="start_date") or Date(1, 1)
    try:
        schedule = ScheduleFixedInterval(
            identifier,
            [float(val) for val in values],
            schedule_type_limit=type_limit,
            timestep=timestep,
            start_date=start_date_obj,
            placeholder_value=placeholder_value,
            interpolate=interpolate,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid ScheduleFixedInterval input. {exc}") from exc

    data = None
    data_target = None
    data_persistence_receipt = None
    summary_view = _schedule_fixed_interval_summary(schedule)
    if include_data:
        analysis_period = analysis_period_from_input(
            data_analysis_period,
            field_name="data_analysis_period",
        )
        try:
            if (
                analysis_period is None
                and data_start_date is None
                and data_end_date is None
                and data_timestep is None
            ):
                data_collection = schedule.data_collection
            else:
                if analysis_period is None:
                    dc_start = _date_from_input(data_start_date, field_name="data_start_date") or Date(1, 1)
                    dc_end = _date_from_input(data_end_date, field_name="data_end_date") or Date(12, 31)
                    dc_timestep = data_timestep if data_timestep is not None else schedule.timestep
                else:
                    dc_start = Date(1, 1)
                    dc_end = Date(12, 31)
                    dc_timestep = analysis_period.timestep
                    summary_view["analysis_period"] = analysis_period_summary(analysis_period)
                data_collection = schedule.data_collection_at_timestep(
                    timestep=dc_timestep,
                    start_date=dc_start,
                    end_date=dc_end,
                )
                if analysis_period is not None and not analysis_period.is_annual:
                    data_collection = data_collection.filter_by_analysis_period(analysis_period)
        except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
            raise ValueError(f"Could not create ScheduleFixedInterval data collection. {exc}") from exc
        if return_data:
            data = data_collection.to_dict()
        summary_view["data"] = data_collection_summary(data_collection)
        if garden_root:
            saved_data = save_data_collection(
                garden_root=garden_root,
                data_collection=data_collection,
                identifier=f"{identifier}_data",
                source={
                    "producer": "create_schedule_fixed_interval",
                    "schedule_identifier": schedule.identifier,
                },
            )
            data_target = saved_data["target"]
            data_persistence_receipt = saved_data["persistence_receipt"]
            summary_view["data_target"] = data_target

    result: dict[str, Any] = {
        "object_dict": schedule.to_dict(),
        "data": data,
        "data_target": data_target,
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message=f"Created ScheduleFixedInterval: {schedule.identifier}",
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
        result["persistence_receipt"] = saved["persistence_receipt"]
        result["summary_view"]["target"] = saved["target"]
        result["summary_view"]["ready_for"] = (
            "create_program_type schedule fields or edit_honeybee_shade.transmittance_schedule"
        )
        if not return_object_dict:
            result.pop("object_dict", None)
    return result


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
    schedule_type: str = "ruleset",
    default_day_schedule: dict[str, Any] | list[float] | None = None,
    schedule_rules: list[dict[str, Any]] | None = None,
    rules: list[dict[str, Any]] | None = None,
    schedule_type_limit: dict[str, Any] | str | None = None,
    default_value: float | None = None,
    summer_designday_schedule: dict[str, Any] | list[float] | None = None,
    winter_designday_schedule: dict[str, Any] | list[float] | None = None,
    holiday_schedule: dict[str, Any] | list[float] | None = None,
    values: list[float] | None = None,
    timestep: int | None = None,
    start_date: dict[str, Any] | list[Any] | str | None = None,
    placeholder_value: float | None = None,
    interpolate: bool | None = None,
    lower_limit: float | str | None = None,
    upper_limit: float | str | None = None,
    numeric_type: str | None = None,
    unit_type: str | None = None,
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
    """Create a Honeybee Energy ScheduleRuleset, ScheduleFixedInterval, or ScheduleTypeLimit."""
    normalized_type = str(schedule_type or "ruleset").strip().lower().replace("-", "_")
    ruleset_only = {
        name: val
        for name, val in {
            "default_day_schedule": default_day_schedule,
            "schedule_rules": schedule_rules,
            "rules": rules,
            "default_value": default_value,
            "summer_designday_schedule": summer_designday_schedule,
            "winter_designday_schedule": winter_designday_schedule,
            "holiday_schedule": holiday_schedule,
        }.items()
        if val is not None
    }
    fixed_only = {
        name: val
        for name, val in {
            "values": values,
            "timestep": timestep,
            "start_date": start_date,
            "placeholder_value": placeholder_value,
            "interpolate": interpolate,
        }.items()
        if val is not None
    }
    type_limit_only = {
        name: val
        for name, val in {
            "lower_limit": lower_limit,
            "upper_limit": upper_limit,
            "numeric_type": numeric_type,
            "unit_type": unit_type,
        }.items()
        if val is not None
    }

    if normalized_type == "fixed_interval":
        bad = sorted([*ruleset_only, *type_limit_only])
        if bad:
            raise ValueError(
                f"schedule_type='fixed_interval' does not accept parameter(s): {', '.join(bad)}."
            )
        if values is None:
            raise ValueError(
                "schedule_type='fixed_interval' requires values (list of 24 to 8760*timestep numbers)."
            )
        return create_schedule_fixed_interval(
            identifier=identifier,
            values=values,
            schedule_type_limit=schedule_type_limit,
            timestep=1 if timestep is None else timestep,
            start_date=start_date,
            placeholder_value=0.0 if placeholder_value is None else placeholder_value,
            interpolate=False if interpolate is None else interpolate,
            include_data=include_data,
            data_analysis_period=data_analysis_period,
            data_timestep=data_timestep if data_timestep != 1 else None,
            data_start_date=data_start_date,
            data_end_date=data_end_date,
            garden_root=garden_root,
            return_data=return_data,
            return_object_dict=return_object_dict,
        )

    if normalized_type == "type_limit":
        bad = sorted([*ruleset_only, *fixed_only])
        if schedule_type_limit is not None:
            bad.append("schedule_type_limit")
        if bad:
            raise ValueError(
                f"schedule_type='type_limit' does not accept parameter(s): {', '.join(sorted(set(bad)))}."
            )
        return create_schedule_type_limit(
            identifier=identifier,
            lower_limit=lower_limit,
            upper_limit=upper_limit,
            numeric_type="Continuous" if numeric_type is None else numeric_type,
            unit_type="Dimensionless" if unit_type is None else unit_type,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    if normalized_type != "ruleset":
        raise ValueError("schedule_type must be one of: ruleset, fixed_interval, type_limit.")

    bad_for_ruleset = sorted([*fixed_only, *type_limit_only])
    if bad_for_ruleset:
        raise ValueError(
            f"schedule_type='ruleset' does not accept parameter(s): {', '.join(bad_for_ruleset)}."
        )

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
            default_identifier=f"{identifier}_default_day",
        )
    if schedule_rules and rules:
        raise ValueError("Use either schedule_rules SDK dictionaries or rules shorthand, not both.")
    default_day = _schedule_day_from_input(
        default_day.to_dict(),
        field_name="_default_day_schedule",
        default_identifier=f"{identifier}_default_day",
    )
    parsed_rules = [
        _schedule_rule_from_input(
            rule,
            field_name=f"schedule_rules[{index}]",
            default_day_identifier=f"{identifier}_rule_{index + 1}_day",
        )
        for index, rule in enumerate(schedule_rules or [])
    ]
    if rules:
        pending_intervals: list[dict[str, Any]] = []
        interval_group_index = 0
        for index, rule in enumerate(rules):
            if isinstance(rule, dict) and (
                "schedule_day" in rule
                or "day" in rule
                or ("values" in rule and "start_time" not in rule and "start" not in rule)
                or rule.get("type") == "ScheduleRule"
            ):
                if pending_intervals:
                    interval_group_index += 1
                    parsed_rules.extend(
                        _rules_from_interval_specs(
                            identifier=f"{identifier}_g{interval_group_index}" if interval_group_index > 1 else identifier,
                            rules=pending_intervals,
                        )
                    )
                    pending_intervals = []
                parsed_rules.append(
                    _schedule_rule_from_input(
                        rule,
                        field_name=f"rules[{index}]",
                        default_day_identifier=f"{identifier}_rule_{index + 1}_day",
                    )
                )
            else:
                pending_intervals.append(rule)
        if pending_intervals:
            interval_group_index += 1
            parsed_rules.extend(
                _rules_from_interval_specs(
                    identifier=f"{identifier}_g{interval_group_index}" if interval_group_index > 1 else identifier,
                    rules=pending_intervals,
                )
            )
    type_limit = _schedule_type_limit_from_input(schedule_type_limit, garden_root=garden_root)
    summer_day = (
        _schedule_day_from_input(
            summer_designday_schedule,
            field_name="summer_designday_schedule",
            default_identifier=f"{identifier}_summer_designday",
        )
        if summer_designday_schedule is not None
        else None
    )
    winter_day = (
        _schedule_day_from_input(
            winter_designday_schedule,
            field_name="winter_designday_schedule",
            default_identifier=f"{identifier}_winter_designday",
        )
        if winter_designday_schedule is not None
        else None
    )
    holiday_day = (
        _schedule_day_from_input(
            holiday_schedule,
            field_name="holiday_schedule",
            default_identifier=f"{identifier}_holiday",
        )
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
        result["persistence_receipt"] = saved["persistence_receipt"]
        result["summary_view"]["target"] = saved["target"]
        result["summary_view"]["ready_for"] = (
            "create_program_type schedule fields or edit_honeybee_shade.transmittance_schedule"
        )
        if not return_object_dict:
            result.pop("object_dict", None)
    return result
