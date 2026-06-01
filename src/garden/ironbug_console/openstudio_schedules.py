"""Schedule writers for the Python Ironbug OpenStudio writer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_utils import _set_if_present


def _write_schedule_type_limits(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    name = str(node.fields.get("Name") or node.identifier)
    optional_limits = model.getScheduleTypeLimitsByName(name)
    if optional_limits.is_initialized():
        type_limits = optional_limits.get()
    else:
        type_limits = openstudio.model.ScheduleTypeLimits(model)
        type_limits.setName(name)
    _set_if_present(type_limits.setLowerLimitValue, node, "LowerLimitValue")
    _set_if_present(type_limits.setUpperLimitValue, node, "UpperLimitValue")
    _set_if_present(type_limits.setUnitType, node, "UnitType", cast=str)
    _set_if_present(type_limits.setNumericType, node, "NumericType", cast=str)
    return OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="schedules",
        openstudio_type="OS:ScheduleTypeLimits",
        name=name,
    )


def _write_schedule_day(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    name = str(node.fields.get("Name") or node.identifier)
    optional_day = model.getScheduleDayByName(name)
    if optional_day.is_initialized():
        day = optional_day.get()
    else:
        day = openstudio.model.ScheduleDay(model)
        day.setName(name)
    _copy_values_to_schedule_day(openstudio, day, node)
    type_limits = _schedule_type_limits_for_node(model, graph, node)
    if type_limits is not None:
        day.setScheduleTypeLimits(type_limits)
    return OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="schedules",
        openstudio_type="OS:Schedule:Day",
        name=name,
    )


def _write_schedule_file(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    name = str(node.fields.get("Name") or node.identifier)
    optional_file = model.getScheduleFileByName(name)
    if optional_file.is_initialized():
        schedule = optional_file.get()
    else:
        path = Path(str(node.fields.get("FilePath") or node.fields.get("Path")))
        schedule = openstudio.model.ScheduleFile(
            model,
            openstudio.path(str(path.resolve())),
        )
        schedule.setName(name)
    _set_if_present(schedule.setColumnNumber, node, "ColumnNumber", cast=int)
    _set_if_present(schedule.setRowstoSkipatTop, node, "RowsToSkipAtTop", cast=int)
    _set_if_present(schedule.setMinutesperItem, node, "MinutesperItem", cast=int)
    _set_if_present(
        schedule.setNumberofHoursofData,
        node,
        "NumberofHoursofData",
        cast=int,
    )
    _set_if_present(
        schedule.setColumnSeparator,
        node,
        "ColumnSeparator",
        cast=str,
    )
    type_limits = _schedule_type_limits_for_node(model, graph, node)
    if type_limits is not None:
        schedule.setScheduleTypeLimits(type_limits)
    return OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="schedules",
        openstudio_type="OS:Schedule:File",
        name=name,
    )


def _write_schedule_ruleset(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_schedule = model.getScheduleRulesetByName(name)
    if optional_schedule.is_initialized():
        schedule = optional_schedule.get()
    else:
        schedule = openstudio.model.ScheduleRuleset(model)
        schedule.setName(name)
    type_limits = _schedule_type_limits_for_node(model, graph, node)
    if type_limits is not None:
        schedule.setScheduleTypeLimits(type_limits)
    constant_value = node.fields.get("ConstantValue")
    if constant_value is not None:
        day_schedule = schedule.defaultDaySchedule()
        day_schedule.clearValues()
        day_schedule.addValue(openstudio.Time(0, 24, 0, 0), float(constant_value))
    default_day_identifier = node.fields.get("DefaultDayScheduleIdentifier")
    if default_day_identifier is not None:
        day_node = graph.node_by_identifier(str(default_day_identifier))
        _copy_values_to_schedule_day(
            openstudio,
            schedule.defaultDaySchedule(),
            day_node,
        )

    written_rules: list[OpenStudioWrittenObject] = []
    rule_index = 0
    for child_identifier in node.children:
        child_node = graph.node_by_identifier(str(child_identifier))
        if child_node.source_class != "IB_ScheduleRule":
            continue
        _write_schedule_rule_to_ruleset(
            openstudio,
            model,
            graph,
            schedule,
            child_node,
            rule_index,
        )
        written_rules.append(
            OpenStudioWrittenObject(
                identifier=child_node.identifier,
                source_class=child_node.source_class,
                writer_family="schedules",
                openstudio_type="OS:Schedule:Rule",
                name=str(child_node.fields.get("Name") or child_node.identifier),
            )
        )
        rule_index += 1

    ruleset_summary = OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="schedules",
        openstudio_type="OS:Schedule:Ruleset",
        name=name,
    )
    return (*written_rules, ruleset_summary)


def _write_schedule_rule_standalone(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> OpenStudioWrittenObject:
    ruleset_identifier = node.fields.get("ScheduleRulesetIdentifier")
    if ruleset_identifier is None:
        ruleset = openstudio.model.ScheduleRuleset(model)
        ruleset.setName(f"{node.identifier} Ruleset")
        rule_index = 0
    else:
        ruleset_node = graph.node_by_identifier(str(ruleset_identifier))
        ruleset_name = str(ruleset_node.fields.get("Name") or ruleset_node.identifier)
        optional_ruleset = model.getScheduleRulesetByName(ruleset_name)
        if optional_ruleset.is_initialized():
            ruleset = optional_ruleset.get()
        else:
            ruleset = openstudio.model.ScheduleRuleset(model)
            ruleset.setName(ruleset_name)
        rule_index = len(ruleset.scheduleRules())
    _write_schedule_rule_to_ruleset(
        openstudio,
        model,
        graph,
        ruleset,
        node,
        rule_index,
    )
    return OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="schedules",
        openstudio_type="OS:Schedule:Rule",
        name=str(node.fields.get("Name") or node.identifier),
    )


def _copy_values_to_schedule_day(
    openstudio: Any,
    schedule_day: Any,
    node: ConsoleGraphNode,
) -> None:
    schedule_day.clearValues()
    values = node.fields.get("Values") or node.fields.get("HourlyValues")
    if values is None:
        constant = node.fields.get("ConstantValue")
        if constant is None:
            constant = node.fields.get("constantNumber")
        schedule_day.addValue(openstudio.Time(0, 24, 0, 0), float(constant or 0.0))
        return
    hourly_values = [float(value) for value in values]
    if len(hourly_values) != 24:
        raise ValueError("IB_ScheduleDay Values must contain 24 hourly values.")
    previous_value = hourly_values[0]
    for hour, value in enumerate(hourly_values[1:], start=1):
        if value != previous_value:
            schedule_day.addValue(openstudio.Time(0, hour, 0, 0), previous_value)
            previous_value = value
    schedule_day.addValue(openstudio.Time(0, 24, 0, 0), previous_value)


def _schedule_type_limits_for_node(
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> Any | None:
    identifier = node.fields.get("ScheduleTypeLimitsIdentifier")
    if identifier is None:
        for child_identifier in node.children:
            child_node = graph.node_by_identifier(str(child_identifier))
            if child_node.source_class == "IB_ScheduleTypeLimits":
                identifier = child_identifier
                break
    if identifier is None:
        return None
    limits_node = graph.node_by_identifier(str(identifier))
    limits_name = str(limits_node.fields.get("Name") or limits_node.identifier)
    optional_limits = model.getScheduleTypeLimitsByName(limits_name)
    if optional_limits.is_initialized():
        return optional_limits.get()
    return None


def _write_schedule_rule_to_ruleset(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    ruleset: Any,
    node: ConsoleGraphNode,
    rule_index: int,
) -> None:
    day_node = _schedule_day_node_for_rule(graph, node)
    day = openstudio.model.ScheduleDay(model)
    day.setName(f"{node.fields.get('Name') or node.identifier} Day")
    _copy_values_to_schedule_day(openstudio, day, day_node)
    rule = openstudio.model.ScheduleRule(ruleset, day)
    rule.setName(str(node.fields.get("Name") or node.identifier))
    rule.setStartDate(
        openstudio.Date(
            openstudio.MonthOfYear(int(node.fields.get("StartMonth") or 1)),
            int(node.fields.get("StartDay") or 1),
        )
    )
    rule.setEndDate(
        openstudio.Date(
            openstudio.MonthOfYear(int(node.fields.get("EndMonth") or 12)),
            int(node.fields.get("EndDay") or 31),
        )
    )
    for day_name in (
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ):
        field_name = f"Apply{day_name}"
        if field_name in node.fields:
            getattr(rule, f"set{field_name}")(bool(node.fields[field_name]))
    ruleset.setScheduleRuleIndex(rule, rule_index)


def _schedule_day_node_for_rule(
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> ConsoleGraphNode:
    identifier = node.fields.get("ScheduleDayIdentifier")
    if identifier is None and node.children:
        identifier = node.children[0]
    if identifier is None:
        raise ValueError("IB_ScheduleRule requires ScheduleDayIdentifier or child.")
    return graph.node_by_identifier(str(identifier))


def _schedule_rule_owned_by_ruleset(
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> bool:
    for candidate in graph.nodes:
        if candidate.source_class == "IB_ScheduleRuleset" and (
            node.identifier in candidate.children
        ):
            return True
    return False


