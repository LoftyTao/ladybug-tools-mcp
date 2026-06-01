"""Graph traversal for Ironbug Console DetailedHVAC decoding."""

from __future__ import annotations

from typing import Any, Mapping

from ironbug.console_ir import ConsoleGraphNode

from garden.ironbug_console.graph_decoder_fields import (
    _fields,
    _identifier,
    _source_class,
)
from garden.ironbug_console.graph_decoder_state import _DecodeState

_CONTAINER_SOURCE_CLASSES = frozenset({"IB_NoAirLoop"})
_GRAPH_COLLECTION_KEYS = (
    "Children",
    "SupplyComponents",
    "DemandComponents",
    "Branches",
    "Terminals",
    "Actuators",
    "Sensors",
    "Variables",
    "ProgramClnManagers",
    "Programs",
    "CustomOutputVariables",
    "SubPanels",
    "Generators",
    "WaterUseEquips",
    "Stages",
    "OAStreamObjs",
    "ReliefStreamObjs",
)
_SINGLE_CHILD_KEYS = (
    "PowerInTransformer",
    "PowerOutTransformer",
    "ElectricalStorage",
    "StorageConverter",
)


def _visit_node(
    value: Any,
    *,
    state: _DecodeState,
    path: tuple[str, ...],
    thermal_zone_identifier: str | None,
) -> str | None:
    if not isinstance(value, Mapping):
        return None

    source_class = _source_class(value)
    if source_class is None:
        _visit_nested_collections(
            value,
            state=state,
            path=path,
            thermal_zone_identifier=thermal_zone_identifier,
        )
        return None

    if source_class in _CONTAINER_SOURCE_CLASSES:
        _visit_nested_collections(
            value,
            state=state,
            path=(*path, source_class),
            thermal_zone_identifier=thermal_zone_identifier,
        )
        return None

    fields = _fields(value)
    identifier = _identifier(value, fields, source_class, state)
    node_path = (*path, identifier)

    if source_class == "IB_ThermalZone":
        node = ConsoleGraphNode(
            identifier=identifier,
            source_class=source_class,
            path=node_path,
            fields=fields,
        )
        state.add_node(node)
        _visit_thermal_zone_children(
            value,
            state=state,
            path=node_path,
            thermal_zone_identifier=identifier,
        )
        return identifier

    if thermal_zone_identifier is not None and (
        source_class == "IB_SizingZone"
        or source_class.startswith("IB_ZoneHVAC")
        or source_class.startswith("IB_AirTerminal")
    ):
        fields = {**fields, "ThermalZoneIdentifier": thermal_zone_identifier}

    child_identifiers = _visit_child_list(
        value.get("Children") or [],
        state=state,
        path=(*node_path, "Children"),
        thermal_zone_identifier=thermal_zone_identifier,
    )
    supply_component_identifiers = _visit_child_list(
        value.get("SupplyComponents") or [],
        state=state,
        path=(*node_path, "SupplyComponents"),
        thermal_zone_identifier=thermal_zone_identifier,
    )
    demand_component_identifiers = _visit_child_list(
        value.get("DemandComponents") or [],
        state=state,
        path=(*node_path, "DemandComponents"),
        thermal_zone_identifier=thermal_zone_identifier,
    )
    branch_component_identifiers = _visit_branch_lists(
        value.get("Branches") or [],
        state=state,
        path=(*node_path, "Branches"),
        thermal_zone_identifier=thermal_zone_identifier,
    )
    terminal_identifiers = _visit_child_list(
        value.get("Terminals") or [],
        state=state,
        path=(*node_path, "Terminals"),
        thermal_zone_identifier=thermal_zone_identifier,
    )
    custom_attribute_identifiers, custom_attribute_fields = (
        _visit_custom_attribute_targets(
            value,
            state=state,
            path=(*node_path, "CustomAttributes"),
            thermal_zone_identifier=thermal_zone_identifier,
        )
    )
    if custom_attribute_fields:
        fields = {**fields, **custom_attribute_fields}
    extra_child_identifiers = _visit_extra_children(
        value,
        state=state,
        path=node_path,
        thermal_zone_identifier=thermal_zone_identifier,
    )
    if supply_component_identifiers:
        fields = {
            **fields,
            "SupplyComponentIdentifiers": supply_component_identifiers,
        }
    if demand_component_identifiers:
        fields = {
            **fields,
            "DemandComponentIdentifiers": demand_component_identifiers,
        }
    if branch_component_identifiers:
        fields = {
            **fields,
            "BranchComponentIdentifiers": branch_component_identifiers,
        }
    if terminal_identifiers:
        fields = {
            **fields,
            "TerminalIdentifiers": terminal_identifiers,
        }
    child_identifiers = tuple(
        [
            *child_identifiers,
            *supply_component_identifiers,
            *demand_component_identifiers,
            *(
                identifier
                for branch in branch_component_identifiers
                for identifier in branch
            ),
            *terminal_identifiers,
            *custom_attribute_identifiers,
            *extra_child_identifiers,
        ]
    )
    node = ConsoleGraphNode(
        identifier=identifier,
        source_class=source_class,
        path=node_path,
        fields=fields,
        children=child_identifiers,
    )
    state.add_node(node)
    return identifier


def _visit_thermal_zone_children(
    value: Mapping[str, Any],
    *,
    state: _DecodeState,
    path: tuple[str, ...],
    thermal_zone_identifier: str,
) -> None:
    sizing_zone = value.get("SizingZone")
    if isinstance(sizing_zone, Mapping):
        _visit_node(
            sizing_zone,
            state=state,
            path=(*path, "SizingZone"),
            thermal_zone_identifier=thermal_zone_identifier,
        )
    for equipment in value.get("ZoneEquipments") or []:
        _visit_node(
            equipment,
            state=state,
            path=(*path, "ZoneEquipments"),
            thermal_zone_identifier=thermal_zone_identifier,
        )
    air_terminal = value.get("AirTerminal")
    if isinstance(air_terminal, Mapping):
        _visit_node(
            air_terminal,
            state=state,
            path=(*path, "AirTerminal"),
            thermal_zone_identifier=thermal_zone_identifier,
        )


def _visit_nested_collections(
    value: Mapping[str, Any],
    *,
    state: _DecodeState,
    path: tuple[str, ...],
    thermal_zone_identifier: str | None,
) -> None:
    for key in (
        "ThermalZones",
        "ZoneEquipments",
        "AirLoops",
        "PlantLoops",
        "VariableRefrigerantFlows",
        *_GRAPH_COLLECTION_KEYS,
    ):
        items = value.get(key) or []
        if key == "Branches":
            items = [child for branch in items for child in branch]
        for child in items:
            _visit_node(
                child,
                state=state,
                path=(*path, key),
                thermal_zone_identifier=thermal_zone_identifier,
            )
    ib_properties = value.get("IBProperties")
    if isinstance(ib_properties, Mapping):
        for key in _GRAPH_COLLECTION_KEYS:
            for child in ib_properties.get(key) or []:
                _visit_node(
                    child,
                    state=state,
                    path=(*path, "IBProperties", key),
                    thermal_zone_identifier=thermal_zone_identifier,
                )
    for key in _SINGLE_CHILD_KEYS:
        child = value.get(key)
        if isinstance(child, Mapping):
            _visit_node(
                child,
                state=state,
                path=(*path, key),
                thermal_zone_identifier=thermal_zone_identifier,
            )


def _visit_extra_children(
    value: Mapping[str, Any],
    *,
    state: _DecodeState,
    path: tuple[str, ...],
    thermal_zone_identifier: str | None,
) -> tuple[str, ...]:
    identifiers: list[str] = []
    for key in _GRAPH_COLLECTION_KEYS:
        if key in {
            "Children",
            "SupplyComponents",
            "DemandComponents",
            "Branches",
            "Terminals",
        }:
            continue
        identifiers.extend(
            _visit_child_list(
                value.get(key) or [],
                state=state,
                path=(*path, key),
                thermal_zone_identifier=thermal_zone_identifier,
            )
        )
    ib_properties = value.get("IBProperties")
    if isinstance(ib_properties, Mapping):
        for key in _GRAPH_COLLECTION_KEYS:
            identifiers.extend(
                _visit_child_list(
                    ib_properties.get(key) or [],
                    state=state,
                    path=(*path, "IBProperties", key),
                    thermal_zone_identifier=thermal_zone_identifier,
                )
            )
    for key in _SINGLE_CHILD_KEYS:
        child = value.get(key)
        if not isinstance(child, Mapping):
            continue
        child_identifier = _visit_node(
            child,
            state=state,
            path=(*path, key),
            thermal_zone_identifier=thermal_zone_identifier,
        )
        if child_identifier is not None:
            identifiers.append(child_identifier)
    return tuple(identifiers)


def _visit_custom_attribute_targets(
    value: Mapping[str, Any],
    *,
    state: _DecodeState,
    path: tuple[str, ...],
    thermal_zone_identifier: str | None,
) -> tuple[tuple[str, ...], dict[str, str]]:
    identifiers: list[str] = []
    reference_fields: dict[str, str] = {}
    custom_attributes = value.get("CustomAttributes")
    if not isinstance(custom_attributes, list):
        return (), {}
    for attribute in custom_attributes:
        if not isinstance(attribute, Mapping):
            continue
        field = attribute.get("Field")
        if not isinstance(field, Mapping):
            continue
        full_name = field.get("FullName")
        target = attribute.get("Value")
        if not full_name or not isinstance(target, Mapping):
            continue
        child_identifier = _visit_node(
            target,
            state=state,
            path=(*path, str(full_name)),
            thermal_zone_identifier=thermal_zone_identifier,
        )
        if child_identifier is None:
            continue
        identifiers.append(child_identifier)
        reference_fields[f"{full_name}Identifier"] = child_identifier
    return tuple(identifiers), reference_fields


def _visit_child_list(
    values: Any,
    *,
    state: _DecodeState,
    path: tuple[str, ...],
    thermal_zone_identifier: str | None,
) -> tuple[str, ...]:
    return tuple(
        child_identifier
        for child in values
        if (
            child_identifier := _visit_node(
                child,
                state=state,
                path=path,
                thermal_zone_identifier=thermal_zone_identifier,
            )
        )
        is not None
    )


def _visit_branch_lists(
    values: Any,
    *,
    state: _DecodeState,
    path: tuple[str, ...],
    thermal_zone_identifier: str | None,
) -> tuple[tuple[str, ...], ...]:
    branch_identifiers: list[tuple[str, ...]] = []
    for index, branch in enumerate(values):
        branch_identifiers.append(
            _visit_child_list(
                branch,
                state=state,
                path=(*path, str(index)),
                thermal_zone_identifier=thermal_zone_identifier,
            )
        )
    return tuple(branch_identifiers)
