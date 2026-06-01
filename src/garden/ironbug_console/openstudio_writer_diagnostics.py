"""OpenStudio writer diagnostics for Python Ironbug Console graphs."""

from __future__ import annotations

from pathlib import Path

from ironbug.console_ir import (
    PYCONSOLE_MISSING_REQUIRED_CHILD,
    PYCONSOLE_UNRESOLVED_REFERENCE,
    PYCONSOLE_WRITER_NOT_IMPLEMENTED,
    ConsoleDiagnostic,
    ConsoleGraph,
    ConsoleGraphNode,
)

from garden.ironbug_console.openstudio_vrf import _vrf_terminal_identifiers
from garden.ironbug_console.openstudio_writer_child_rules import (
    _missing_terminal_child_classes,
    _missing_terminal_child_message,
)
from garden.ironbug_console.openstudio_writer_utils import _has_node


def _unsupported_writer_diagnostic(node: ConsoleGraphNode) -> ConsoleDiagnostic:
    return ConsoleDiagnostic(
        code=PYCONSOLE_WRITER_NOT_IMPLEMENTED,
        message=(
            f"{node.source_class} is in the writer registry, but no OpenStudio "
            "writer is implemented for that source class yet."
        ),
        source_class=node.source_class,
        identifier=node.identifier,
        path=node.path,
    )

def _reference_diagnostics(graph: ConsoleGraph) -> list[ConsoleDiagnostic]:
    diagnostics: list[ConsoleDiagnostic] = []
    for node in graph.nodes:
        if node.source_class != "IB_SizingZone":
            if node.source_class in {
                "IB_ZoneHVACPackagedTerminalAirConditioner",
                "IB_ZoneHVACPackagedTerminalHeatPump",
                "IB_ZoneHVACFourPipeFanCoil",
                "IB_ZoneHVACBaseboardRadiantConvectiveWater",
                "IB_ZoneHVACUnitHeater",
                "IB_ZoneHVACUnitVentilator_CoolingHeating",
                "IB_ZoneHVACUnitVentilator_CoolingOnly",
                "IB_ZoneHVACUnitVentilator_HeatingOnly",
                "IB_ZoneHVACTerminalUnitVariableRefrigerantFlow",
                "IB_AirTerminalSingleDuctConstantVolumeNoReheat",
                "IB_AirTerminalSingleDuctConstantVolumeReheat",
                "IB_AirTerminalSingleDuctConstantVolumeCooledBeam",
                "IB_AirTerminalSingleDuctConstantVolumeFourPipeBeam",
                "IB_AirTerminalSingleDuctConstantVolumeFourPipeInduction",
                "IB_AirTerminalSingleDuctInletSideMixer",
                "IB_AirTerminalSingleDuctParallelPIUReheat",
                "IB_AirTerminalSingleDuctSeriesPIUReheat",
                "IB_AirTerminalSingleDuctVAVHeatAndCoolNoReheat",
                "IB_AirTerminalSingleDuctVAVHeatAndCoolReheat",
                "IB_AirTerminalSingleDuctVAVNoReheat",
                "IB_AirTerminalSingleDuctVAVReheat",
            }:
                diagnostics.extend(_terminal_reference_diagnostics(graph, node))
            elif node.source_class == "IB_AirLoopHVACUnitarySystem":
                diagnostics.extend(_air_loop_unitary_reference_diagnostics(graph, node))
            elif node.source_class == "IB_AirConditionerVariableRefrigerantFlow":
                diagnostics.extend(_vrf_reference_diagnostics(graph, node))
            elif node.source_class == "IB_ScheduleFile":
                diagnostics.extend(_schedule_file_diagnostics(node))
                diagnostics.extend(
                    _field_reference_diagnostics(
                        graph,
                        node,
                        "ScheduleTypeLimitsIdentifier",
                        "IB_ScheduleTypeLimits",
                    )
                )
            elif node.source_class == "IB_ScheduleDay":
                diagnostics.extend(
                    _field_reference_diagnostics(
                        graph,
                        node,
                        "ScheduleTypeLimitsIdentifier",
                        "IB_ScheduleTypeLimits",
                    )
                )
            elif node.source_class == "IB_ScheduleRuleset":
                diagnostics.extend(
                    _field_reference_diagnostics(
                        graph,
                        node,
                        "DefaultDayScheduleIdentifier",
                        "IB_ScheduleDay",
                    )
                )
                diagnostics.extend(
                    _field_reference_diagnostics(
                        graph,
                        node,
                        "ScheduleTypeLimitsIdentifier",
                        "IB_ScheduleTypeLimits",
                    )
                )
            elif node.source_class == "IB_SizingSystem":
                diagnostics.extend(
                    _required_field_reference_diagnostics(
                        graph,
                        node,
                        ("AirLoopIdentifier", "AirLoopHVACIdentifier"),
                        "IB_AirLoopHVAC",
                    )
                )
            elif node.source_class == "IB_SizingPlant":
                diagnostics.extend(
                    _required_field_reference_diagnostics(
                        graph,
                        node,
                        ("PlantLoopIdentifier",),
                        "IB_PlantLoop",
                    )
                )
            continue
        zone_identifier = node.fields.get("ThermalZoneIdentifier")
        if zone_identifier is None:
            diagnostics.append(
                ConsoleDiagnostic(
                    code=PYCONSOLE_UNRESOLVED_REFERENCE,
                    message=(
                        "IB_SizingZone writer requires ThermalZoneIdentifier "
                        "until full child graph resolution exists."
                    ),
                    source_class=node.source_class,
                    identifier=node.identifier,
                    path=node.path,
                )
            )
            continue
        try:
            graph.node_by_identifier(str(zone_identifier))
        except KeyError:
            diagnostics.append(
                ConsoleDiagnostic(
                    code=PYCONSOLE_UNRESOLVED_REFERENCE,
                    message=(
                        "IB_SizingZone references missing ThermalZoneIdentifier "
                        f"{zone_identifier}."
                    ),
                    source_class=node.source_class,
                    identifier=node.identifier,
                    path=node.path,
                )
            )
    return diagnostics

def _field_reference_diagnostics(
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
    field_name: str,
    expected_source_class: str,
) -> list[ConsoleDiagnostic]:
    if field_name not in node.fields:
        return []
    return _required_field_reference_diagnostics(
        graph,
        node,
        (field_name,),
        expected_source_class,
    )

def _required_field_reference_diagnostics(
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
    field_names: tuple[str, ...],
    expected_source_class: str,
) -> list[ConsoleDiagnostic]:
    identifier = None
    field_label = " / ".join(field_names)
    for field_name in field_names:
        if field_name in node.fields:
            identifier = str(node.fields[field_name])
            break
    if identifier is None:
        return [
            ConsoleDiagnostic(
                code=PYCONSOLE_UNRESOLVED_REFERENCE,
                message=(
                    f"{node.source_class} writer requires {field_label} "
                    "until full child graph resolution exists."
                ),
                source_class=node.source_class,
                identifier=node.identifier,
                path=node.path,
            )
        ]
    try:
        referenced = graph.node_by_identifier(identifier)
    except KeyError:
        return [
            ConsoleDiagnostic(
                code=PYCONSOLE_UNRESOLVED_REFERENCE,
                message=(
                    f"{node.source_class} references missing {field_label} "
                    f"{identifier}."
                ),
                source_class=node.source_class,
                identifier=node.identifier,
                path=node.path,
            )
        ]
    if referenced.source_class != expected_source_class:
        return [
            ConsoleDiagnostic(
                code=PYCONSOLE_UNRESOLVED_REFERENCE,
                message=(
                    f"{node.source_class} {field_label} must reference "
                    f"{expected_source_class}, not {referenced.source_class}."
                ),
                source_class=node.source_class,
                identifier=node.identifier,
                path=node.path,
            )
        ]
    return []

def _schedule_file_diagnostics(node: ConsoleGraphNode) -> list[ConsoleDiagnostic]:
    path_value = node.fields.get("FilePath") or node.fields.get("Path")
    if path_value and Path(str(path_value)).exists():
        return []
    return [
        ConsoleDiagnostic(
            code=PYCONSOLE_UNRESOLVED_REFERENCE,
            message="IB_ScheduleFile writer requires an existing FilePath.",
            source_class=node.source_class,
            identifier=node.identifier,
            path=node.path,
        )
    ]

def _terminal_reference_diagnostics(
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> list[ConsoleDiagnostic]:
    diagnostics: list[ConsoleDiagnostic] = []
    zone_identifier = node.fields.get("ThermalZoneIdentifier")
    if zone_identifier is None:
        diagnostics.append(
            ConsoleDiagnostic(
                code=PYCONSOLE_UNRESOLVED_REFERENCE,
                message=(
                    f"{node.source_class} writer requires "
                    "ThermalZoneIdentifier until full graph resolution exists."
                ),
                source_class=node.source_class,
                identifier=node.identifier,
                path=node.path,
            )
        )
    else:
        try:
            graph.node_by_identifier(str(zone_identifier))
        except KeyError:
            diagnostics.append(
                ConsoleDiagnostic(
                    code=PYCONSOLE_UNRESOLVED_REFERENCE,
                    message=(
                        f"{node.source_class} references "
                        f"missing ThermalZoneIdentifier {zone_identifier}."
                    ),
                    source_class=node.source_class,
                    identifier=node.identifier,
                    path=node.path,
                )
            )

    child_source_classes = {
        graph.node_by_identifier(child_identifier).source_class
        for child_identifier in node.children
        if _has_node(graph, child_identifier)
    }
    missing_children = _missing_terminal_child_classes(
        source_class=node.source_class,
        child_source_classes=child_source_classes,
    )
    if missing_children:
        diagnostics.append(
            ConsoleDiagnostic(
                code=PYCONSOLE_MISSING_REQUIRED_CHILD,
                message=_missing_terminal_child_message(
                    source_class=node.source_class,
                    missing_children=missing_children,
                ),
                source_class=node.source_class,
                identifier=node.identifier,
                path=node.path,
            )
        )
    return diagnostics

def _air_loop_unitary_reference_diagnostics(
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> list[ConsoleDiagnostic]:
    child_source_classes = {
        graph.node_by_identifier(child_identifier).source_class
        for child_identifier in node.children
        if _has_node(graph, child_identifier)
    }
    missing_children = _missing_terminal_child_classes(
        source_class=node.source_class,
        child_source_classes=child_source_classes,
    )
    if not missing_children:
        return []
    return [
        ConsoleDiagnostic(
            code=PYCONSOLE_MISSING_REQUIRED_CHILD,
            message=(
                "IB_AirLoopHVACUnitarySystem requires child source classes: "
                f"{', '.join(missing_children)}."
            ),
            source_class=node.source_class,
            identifier=node.identifier,
            path=node.path,
        )
    ]

def _vrf_reference_diagnostics(
    graph: ConsoleGraph,
    node: ConsoleGraphNode,
) -> list[ConsoleDiagnostic]:
    child_source_classes = {
        graph.node_by_identifier(child_identifier).source_class
        for child_identifier in _vrf_terminal_identifiers(node)
        if _has_node(graph, child_identifier)
    }
    if "IB_ZoneHVACTerminalUnitVariableRefrigerantFlow" in child_source_classes:
        return []
    return [
        ConsoleDiagnostic(
            code=PYCONSOLE_MISSING_REQUIRED_CHILD,
            message=(
                "IB_AirConditionerVariableRefrigerantFlow requires at least one "
                "IB_ZoneHVACTerminalUnitVariableRefrigerantFlow terminal."
            ),
            source_class=node.source_class,
            identifier=node.identifier,
            path=node.path,
        )
    ]
