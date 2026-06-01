"""SetpointManager writers for the Python Ironbug OpenStudio writer."""

from __future__ import annotations

from typing import Any

from ironbug.console_ir import ConsoleGraph, ConsoleGraphNode

from garden.ironbug_console.openstudio_source_classes import (
    SETPOINT_MANAGER_OPENSTUDIO_CLASSES as _SETPOINT_MANAGER_OPENSTUDIO_CLASSES,
    SETPOINT_MANAGER_STRING_FIELDS as _SETPOINT_MANAGER_STRING_FIELDS,
    SINGLE_ZONE_SETPOINT_MANAGER_SOURCE_CLASSES as _SINGLE_ZONE_SETPOINT_MANAGER_SOURCE_CLASSES,
)
from garden.ironbug_console.openstudio_writer_contracts import OpenStudioWrittenObject
from garden.ironbug_console.openstudio_writer_context import OpenStudioWriterContext
from garden.ironbug_console.openstudio_writer_utils import (
    _has_node,
    _is_autosize,
    _set_if_present,
)


def _setpoint_value(node: ConsoleGraphNode) -> float | None:
    value = node.fields.get("Value")
    if value is None or _is_autosize(value):
        return None
    return float(value)


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


def _write_schedule_ruleset(
    openstudio: Any,
    model: Any,
    _graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> tuple[OpenStudioWrittenObject, ...]:
    name = str(node.fields.get("Name") or node.identifier)
    value = float(node.fields.get("ConstantValue") or 0.0)
    _constant_schedule_ruleset(openstudio, model, name, value)
    return ()


def _new_setpoint_manager(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
    context: OpenStudioWriterContext | None = None,
) -> tuple[Any, OpenStudioWrittenObject]:
    if node.source_class == "IB_SetpointManagerScheduled":
        return _new_setpoint_manager_scheduled(openstudio, model, node)

    class_name = _SETPOINT_MANAGER_OPENSTUDIO_CLASSES[node.source_class]
    name = str(node.fields.get("Name") or node.identifier)
    optional_manager = getattr(model, f"get{class_name}ByName")(name)
    if optional_manager.is_initialized():
        manager = optional_manager.get()
    else:
        manager = getattr(openstudio.model, class_name)(model)
        manager.setName(name)

    _apply_setpoint_manager_fields(manager, node)
    _configure_setpoint_manager_schedules(openstudio, model, graph, manager, node)
    _configure_single_zone_setpoint_manager(model, graph, manager, node)
    _configure_reference_node_setpoint_manager(context, manager, node)
    return manager, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="setpoint_managers",
        openstudio_type=manager.iddObjectType().valueDescription(),
        name=name,
    )


def _apply_setpoint_manager_fields(manager: Any, node: ConsoleGraphNode) -> None:
    for field_name in node.fields:
        if field_name in {
            "Name",
            "Value",
            "IsTemperature",
            "LowT",
            "HighT",
            "Schedule",
            "HighSetpointSchedule",
            "LowSetpointSchedule",
            "_nodeID",
            "Comment",
        }:
            continue
        setter = getattr(manager, f"set{field_name}", None)
        if setter is None:
            continue
        cast = str if field_name in _SETPOINT_MANAGER_STRING_FIELDS else float
        _set_if_present(setter, node, field_name, cast=cast)


def _configure_setpoint_manager_schedules(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    manager: Any,
    node: ConsoleGraphNode,
) -> None:
    if node.source_class == "IB_SetpointManagerScheduledDualSetpoint":
        low_schedule = _schedule_ruleset_for_field_or_constant(
            openstudio,
            model,
            graph,
            node,
            field_name="LowSetpointSchedule",
            constant_field_name="LowT",
            schedule_name=f"{node.fields.get('Name') or node.identifier} Low Schedule",
        )
        if low_schedule is not None:
            manager.setLowSetpointSchedule(low_schedule)
        high_schedule = _schedule_ruleset_for_field_or_constant(
            openstudio,
            model,
            graph,
            node,
            field_name="HighSetpointSchedule",
            constant_field_name="HighT",
            schedule_name=f"{node.fields.get('Name') or node.identifier} High Schedule",
        )
        if high_schedule is not None:
            manager.setHighSetpointSchedule(high_schedule)
    elif node.source_class == "IB_SetpointManagerOutdoorAirReset":
        schedule = _schedule_ruleset_for_field_or_constant(
            openstudio,
            model,
            graph,
            node,
            field_name="Schedule",
            constant_field_name=None,
            schedule_name=f"{node.fields.get('Name') or node.identifier} Schedule",
        )
        if schedule is not None:
            manager.setSchedule(schedule)


def _schedule_ruleset_for_field_or_constant(
    openstudio: Any,
    model: Any,
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
    *,
    field_name: str,
    constant_field_name: str | None,
    schedule_name: str,
) -> Any | None:
    field_value = node.fields.get(field_name)
    if isinstance(field_value, str) and _has_node(graph, field_value):
        schedule_node = graph.node_by_identifier(field_value)
        if schedule_node.source_class == "IB_ScheduleRuleset":
            schedule_name = str(schedule_node.fields.get("Name") or schedule_node.identifier)
            optional_schedule = model.getScheduleRulesetByName(schedule_name)
            if not optional_schedule.is_initialized():
                _write_schedule_ruleset(openstudio, model, graph, schedule_node)
                optional_schedule = model.getScheduleRulesetByName(schedule_name)
            if optional_schedule.is_initialized():
                return optional_schedule.get()

    if constant_field_name is None:
        return None
    constant_value = node.fields.get(constant_field_name)
    if constant_value is None:
        return None
    return _constant_schedule_ruleset(
        openstudio,
        model,
        schedule_name,
        float(constant_value),
    )


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


def _configure_single_zone_setpoint_manager(
    model: Any,
    graph: ConsoleGraph,
    manager: Any,
    node: ConsoleGraphNode,
) -> None:
    if node.source_class not in _SINGLE_ZONE_SETPOINT_MANAGER_SOURCE_CLASSES:
        return
    for identifier in (
        *tuple(str(child_identifier) for child_identifier in node.children),
        *tuple(
            str(node.fields[field_name])
            for field_name in ("ControlZoneIdentifier", "ThermalZoneIdentifier")
            if field_name in node.fields
        ),
    ):
        if not _has_node(graph, identifier):
            continue
        zone_node = graph.node_by_identifier(identifier)
        if zone_node.source_class != "IB_ThermalZone":
            continue
        zone_name = str(zone_node.fields.get("Name") or zone_node.identifier)
        optional_zone = model.getThermalZoneByName(zone_name)
        if optional_zone.is_initialized():
            manager.setControlZone(optional_zone.get())
        return


def _configure_reference_node_setpoint_manager(
    context: OpenStudioWriterContext | None,
    manager: Any,
    node: ConsoleGraphNode,
) -> None:
    if context is None:
        return
    if node.source_class not in {
        "IB_SetpointManagerFollowSystemNodeTemperature",
        "IB_SetpointManagerSystemNodeResetHumidity",
        "IB_SetpointManagerSystemNodeResetTemperature",
    }:
        return
    context.bind_reference_node(
        manager,
        probe_identifier=node.fields.get("_nodeID"),
        owner=str(node.fields.get("Name") or node.identifier),
    )


def _new_setpoint_manager_scheduled(
    openstudio: Any,
    model: Any,
    node: ConsoleGraphNode,
) -> tuple[Any, OpenStudioWrittenObject]:
    name = str(node.fields.get("Name") or node.identifier)
    optional_manager = model.getSetpointManagerScheduledByName(name)
    if optional_manager.is_initialized():
        manager = optional_manager.get()
    else:
        schedule = openstudio.model.ScheduleRuleset(model)
        schedule.setName(f"{name} Schedule")
        value = _setpoint_value(node)
        if value is None:
            value = 0.0
        schedule.defaultDaySchedule().clearValues()
        schedule.defaultDaySchedule().addValue(
            openstudio.Time(0, 24, 0, 0),
            value,
        )
        manager = openstudio.model.SetpointManagerScheduled(
            model,
            str(node.fields.get("ControlVariable") or "Temperature"),
            schedule,
        )
        manager.setName(name)
    return manager, OpenStudioWrittenObject(
        identifier=node.identifier,
        source_class=node.source_class,
        writer_family="plant_components",
        openstudio_type="OS:SetpointManager:Scheduled",
        name=name,
    )


