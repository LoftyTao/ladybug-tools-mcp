"""Shared field application helpers for generic OpenStudio object writers."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraphNode

from garden.ironbug_console.openstudio_writer_utils import _is_autosize


def _constant_schedule_ruleset(
    openstudio: Any,
    model: Any,
    name: str,
    value: float,
) -> Any:
    optional_schedule = model.getScheduleRulesetByName(name)
    if optional_schedule.is_initialized():
        schedule = optional_schedule.get()
    else:
        schedule = openstudio.model.ScheduleRuleset(model)
        schedule.setName(name)
    schedule.defaultDaySchedule().clearValues()
    schedule.defaultDaySchedule().addValue(openstudio.Time(0, 24, 0, 0), value)
    return schedule


def _temperature_schedule(
    openstudio: Any,
    model: Any,
    name: str,
    value: float,
) -> Any:
    return _constant_schedule_ruleset(openstudio, model, name, value)


def _apply_generic_openstudio_fields(component: Any, node: ConsoleGraphNode) -> None:
    for field_name, value in node.fields.items():
        if field_name in {"Name", "ThermalZoneIdentifier"} or value is None:
            continue
        setter = getattr(component, f"set{field_name}", None)
        if setter is None:
            continue
        autosize = getattr(component, f"autosize{field_name}", None)
        if autosize is not None and _is_autosize(value):
            autosize()
            continue
        _call_generic_setter(setter, value)


def _call_generic_setter(setter: Any, value: Any) -> None:
    candidates: list[Any] = [value]
    if isinstance(value, bool):
        candidates.extend((str(value), int(value)))
    elif isinstance(value, int):
        candidates.extend((float(value), str(value)))
    elif isinstance(value, float):
        candidates.extend((str(value), int(value)))
    elif isinstance(value, str):
        candidates.append(value.strip())
        try:
            candidates.append(float(value))
        except ValueError:
            pass
    for candidate in candidates:
        try:
            setter(candidate)
            return
        except (TypeError, RuntimeError, ValueError):
            continue
