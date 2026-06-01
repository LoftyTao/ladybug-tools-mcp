"""Decode Ironbug Console specifications into Python Console IR graphs."""

from __future__ import annotations

from typing import Any, Mapping

from ironbug.console_ir import ConsoleGraph

from garden.ironbug_console.graph_decoder_state import _DecodeState
from garden.ironbug_console.graph_decoder_traversal import _visit_node


def detailed_hvac_specification_to_console_graph(
    specification: Mapping[str, Any],
) -> ConsoleGraph:
    """Decode a Honeybee DetailedHVAC Ironbug Console specification."""

    state = _DecodeState()
    for air_loop in specification.get("AirLoops") or []:
        _visit_node(
            air_loop,
            state=state,
            path=("AirLoops",),
            thermal_zone_identifier=None,
        )
    for plant_loop in specification.get("PlantLoops") or []:
        _visit_node(
            plant_loop,
            state=state,
            path=("PlantLoops",),
            thermal_zone_identifier=None,
        )
    for vrf in specification.get("VariableRefrigerantFlows") or []:
        _visit_node(
            vrf,
            state=state,
            path=("VariableRefrigerantFlows",),
            thermal_zone_identifier=None,
        )
    for root_key in ("EnergyManagementSystem", "ElectricLoadCenter"):
        root_payload = specification.get(root_key)
        if root_payload:
            _visit_node(
                root_payload,
                state=state,
                path=(root_key,),
                thermal_zone_identifier=None,
            )
    return ConsoleGraph.from_nodes(state.nodes)


def source_payload_to_console_graph(payload: Mapping[str, Any]) -> ConsoleGraph:
    """Decode a single Ironbug source-root payload into a Console graph."""

    state = _DecodeState()
    _visit_node(
        payload,
        state=state,
        path=(),
        thermal_zone_identifier=None,
    )
    return ConsoleGraph.from_nodes(state.nodes)
