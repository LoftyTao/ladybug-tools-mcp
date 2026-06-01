"""Small OpenStudio writer slices for the Python Ironbug Console."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ironbug.console_ir import (
    ConsoleGraph,
)

from garden.ironbug_console.writer_registry import build_writer_family_plan
from garden.ironbug_console.graph_decoder import (
    detailed_hvac_specification_to_console_graph,
    source_payload_to_console_graph,
)
from garden.ironbug_console.console_model_payloads import (
    ConsoleModelSpecification,
)
from garden.ironbug_console.openstudio_writer_contracts import (
    OpenStudioWriteResult,
    OpenStudioWrittenObject,
)
from garden.ironbug_console.openstudio_writer_context import OpenStudioWriterContext
from garden.ironbug_console.openstudio_writer_diagnostics import (
    _reference_diagnostics,
    _unsupported_writer_diagnostic,
)
from garden.ironbug_console.openstudio_writer_order import _writer_order
from garden.ironbug_console.openstudio_writer_source_sets import (
    _SUPPORTED_SOURCE_CLASSES,
    _TERMINAL_COMPONENT_SOURCE_CLASSES,
)
from garden.ironbug_console.openstudio_air_loops import (
    _write_air_loop_hvac,
)
from garden.ironbug_console.openstudio_basic_objects import (
    _write_output_variable,
    _write_thermal_zone,
)
from garden.ironbug_console.openstudio_curves import (
    _CURVE_SPECS,
    _write_curve,
)
from garden.ironbug_console.openstudio_electric_load_center import (
    _write_electric_load_center_distribution,
    _write_generator_photovoltaic,
    _write_electric_load_center_storage_converter,
    _write_generator_pv_watts,
)
from garden.ironbug_console.openstudio_generic_objects import (
    _write_ems_program_calling_manager,
    _write_generic_openstudio_object,
    _write_generic_zone_equipment,
    _write_noop_source_object,
    _write_special_openstudio_object,
    _write_special_zone_equipment,
)
from garden.ironbug_console.openstudio_schedules import (
    _schedule_rule_owned_by_ruleset,
    _write_schedule_day,
    _write_schedule_file,
    _write_schedule_rule_standalone,
    _write_schedule_ruleset,
    _write_schedule_type_limits,
)
from garden.ironbug_console.openstudio_sizing import (
    _write_sizing_plant,
    _write_sizing_system,
    _write_sizing_zone,
)
from garden.ironbug_console.openstudio_plant_loops import (
    _write_plant_loop,
)
from garden.ironbug_console.openstudio_vrf import (
    _write_vrf_system,
)
from garden.ironbug_console.openstudio_water_systems import (
    _new_water_use_connections,
    _new_water_use_equipment,
)
from garden.ironbug_console.openstudio_writer_utils import (
    _append_written,
)
from garden.ironbug_console.openstudio_zone_equipment import (
    _ZONE_HVAC_EQUIPMENT_SOURCE_CLASSES,
    _write_baseboard_convective_water,
    _write_baseboard_radiant_convective_water,
    _write_four_pipe_fan_coil,
    _write_high_temperature_radiant,
    _write_low_temp_radiant_const_flow,
    _write_low_temp_radiant_var_flow,
    _write_ptac,
    _write_pthp,
    _write_water_to_air_heat_pump,
    _write_unit_heater,
    _write_unit_ventilator_cooling_heating,
    _write_unit_ventilator_cooling_only,
    _write_unit_ventilator_heating_only,
)


from garden.ironbug_console.openstudio_source_classes import (
    GENERIC_OPENSTUDIO_SOURCE_CLASSES as _GENERIC_OPENSTUDIO_SOURCE_CLASSES,
    GENERIC_ZONE_EQUIPMENT_SOURCE_CLASSES as _GENERIC_ZONE_EQUIPMENT_SOURCE_CLASSES,
    NOOP_CONTAINER_SOURCE_CLASSES as _NOOP_CONTAINER_SOURCE_CLASSES,
    SPECIAL_OPENSTUDIO_SOURCE_CLASSES as _SPECIAL_OPENSTUDIO_SOURCE_CLASSES,
    SPECIAL_ZONE_EQUIPMENT_SOURCE_CLASSES as _SPECIAL_ZONE_EQUIPMENT_SOURCE_CLASSES,
)


def write_first_family_to_openstudio_model(
    *,
    model: Any,
    graph: ConsoleGraph,
    output_path: Path | None = None,
) -> OpenStudioWriteResult:
    """Write the first verified Python Console slice to an OpenStudio model."""

    openstudio = _import_openstudio()
    writer_plan = build_writer_family_plan(graph)
    diagnostics = [
        *writer_plan.diagnostics,
        *(
            _unsupported_writer_diagnostic(node)
            for node in graph.nodes
            if node.source_class not in _SUPPORTED_SOURCE_CLASSES
            and not any(
                diagnostic.identifier == node.identifier
                for diagnostic in writer_plan.diagnostics
            )
        ),
    ]
    diagnostics.extend(_reference_diagnostics(graph))
    if diagnostics:
        return OpenStudioWriteResult(
            status="blocked",
            diagnostics=tuple(diagnostics),
        )

    context = OpenStudioWriterContext()
    inlet_mixer_zone_equipment_identifiers = (
        _inlet_mixer_zone_equipment_identifiers(graph)
    )
    written_objects: list[OpenStudioWrittenObject] = []
    for node in _writer_order(graph):
        if node.identifier in inlet_mixer_zone_equipment_identifiers:
            continue
        if node.source_class == "IB_ThermalZone":
            written_objects.append(_write_thermal_zone(openstudio, model, node))
        elif node.source_class == "IB_OutputVariable":
            written_objects.append(_write_output_variable(openstudio, model, node))
        elif node.source_class == "IB_ScheduleTypeLimits":
            written_objects.append(
                _write_schedule_type_limits(openstudio, model, node)
            )
        elif node.source_class == "IB_ScheduleDay":
            written_objects.append(_write_schedule_day(openstudio, model, graph, node))
        elif node.source_class == "IB_ScheduleFile":
            written_objects.append(
                _write_schedule_file(openstudio, model, graph, node)
            )
        elif node.source_class == "IB_ScheduleRuleset":
            _append_written(
                written_objects,
                _write_schedule_ruleset(openstudio, model, graph, node),
            )
        elif node.source_class == "IB_ScheduleRule":
            if not _schedule_rule_owned_by_ruleset(graph, node):
                written_objects.append(
                    _write_schedule_rule_standalone(openstudio, model, graph, node)
                )
        elif node.source_class in _CURVE_SPECS:
            written_objects.append(_write_curve(openstudio, model, node))
        elif node.source_class == "IB_SizingZone":
            written_objects.append(_write_sizing_zone(model, graph, node))
        elif node.source_class == "IB_SizingSystem":
            written_objects.append(_write_sizing_system(model, graph, node))
        elif node.source_class == "IB_SizingPlant":
            written_objects.append(_write_sizing_plant(model, graph, node))
        elif node.source_class == "IB_AirLoopHVAC":
            _append_written(
                written_objects,
                _write_air_loop_hvac(openstudio, model, graph, node, context),
            )
        elif node.source_class == "IB_PlantLoop":
            _append_written(
                written_objects,
                _write_plant_loop(openstudio, model, graph, node, context),
            )
        elif node.source_class == "IB_ZoneHVACPackagedTerminalAirConditioner":
            _append_written(
                written_objects,
                _write_ptac(openstudio, model, graph, node),
            )
        elif node.source_class == "IB_ZoneHVACPackagedTerminalHeatPump":
            _append_written(
                written_objects,
                _write_pthp(openstudio, model, graph, node),
            )
        elif node.source_class == "IB_ZoneHVACUnitHeater":
            _append_written(
                written_objects,
                _write_unit_heater(openstudio, model, graph, node),
            )
        elif node.source_class == "IB_ZoneHVACFourPipeFanCoil":
            _append_written(
                written_objects,
                _write_four_pipe_fan_coil(openstudio, model, graph, node),
            )
        elif node.source_class == "IB_ZoneHVACWaterToAirHeatPump":
            _append_written(
                written_objects,
                _write_water_to_air_heat_pump(openstudio, model, graph, node),
            )
        elif node.source_class == "IB_ZoneHVACBaseboardConvectiveWater":
            _append_written(
                written_objects,
                _write_baseboard_convective_water(
                    openstudio,
                    model,
                    graph,
                    node,
                ),
            )
        elif node.source_class == "IB_ZoneHVACBaseboardRadiantConvectiveWater":
            _append_written(
                written_objects,
                _write_baseboard_radiant_convective_water(
                    openstudio,
                    model,
                    graph,
                    node,
                ),
            )
        elif node.source_class == "IB_ZoneHVACLowTempRadiantConstFlow":
            _append_written(
                written_objects,
                _write_low_temp_radiant_const_flow(
                    openstudio,
                    model,
                    graph,
                    node,
                ),
            )
        elif node.source_class == "IB_ZoneHVACLowTempRadiantVarFlow":
            _append_written(
                written_objects,
                _write_low_temp_radiant_var_flow(
                    openstudio,
                    model,
                    graph,
                    node,
                ),
            )
        elif node.source_class == "IB_ZoneHVACHighTemperatureRadiant":
            _append_written(
                written_objects,
                _write_high_temperature_radiant(
                    openstudio,
                    model,
                    graph,
                    node,
                ),
            )
        elif node.source_class == "IB_ZoneHVACUnitVentilator_CoolingHeating":
            _append_written(
                written_objects,
                _write_unit_ventilator_cooling_heating(
                    openstudio,
                    model,
                    graph,
                    node,
                ),
            )
        elif node.source_class == "IB_ZoneHVACUnitVentilator_CoolingOnly":
            _append_written(
                written_objects,
                _write_unit_ventilator_cooling_only(openstudio, model, graph, node),
            )
        elif node.source_class == "IB_ZoneHVACUnitVentilator_HeatingOnly":
            _append_written(
                written_objects,
                _write_unit_ventilator_heating_only(openstudio, model, graph, node),
            )
        elif node.source_class == "IB_AirConditionerVariableRefrigerantFlow":
            _append_written(
                written_objects,
                _write_vrf_system(openstudio, model, graph, node),
            )
        elif node.source_class == "IB_GeneratorPVWatts":
            written_objects.append(_write_generator_pv_watts(openstudio, model, node))
        elif node.source_class == "IB_GeneratorPhotovoltaic":
            written_objects.append(
                _write_generator_photovoltaic(openstudio, model, graph, node)
            )
        elif node.source_class == "IB_ElectricLoadCenterDistribution":
            written_objects.append(
                _write_electric_load_center_distribution(
                    openstudio,
                    model,
                    graph,
                    node,
                )
            )
        elif node.source_class == "IB_ElectricLoadCenterStorageConverter":
            written_objects.append(
                _write_electric_load_center_storage_converter(
                    openstudio,
                    model,
                    node,
                )
            )
        elif node.source_class == "IB_WaterUseEquipment":
            _equipment, summary = _new_water_use_equipment(
                openstudio,
                model,
                graph,
                node,
            )
            written_objects.append(summary)
        elif node.source_class == "IB_WaterUseConnections":
            _connections, summary = _new_water_use_connections(
                openstudio,
                model,
                graph,
                node,
            )
            written_objects.append(summary)
        elif node.source_class in _GENERIC_ZONE_EQUIPMENT_SOURCE_CLASSES:
            _append_written(
                written_objects,
                _write_generic_zone_equipment(openstudio, model, graph, node),
            )
        elif node.source_class in _SPECIAL_ZONE_EQUIPMENT_SOURCE_CLASSES:
            _append_written(
                written_objects,
                _write_special_zone_equipment(openstudio, model, graph, node),
            )
        elif node.source_class in _NOOP_CONTAINER_SOURCE_CLASSES:
            written_objects.append(_write_noop_source_object(node))
        elif node.source_class == "IB_EnergyManagementSystemProgramCallingManager":
            written_objects.append(
                _write_ems_program_calling_manager(openstudio, model, graph, node)
            )
        elif (
            node.source_class in _SPECIAL_OPENSTUDIO_SOURCE_CLASSES
            and node.source_class not in _TERMINAL_COMPONENT_SOURCE_CLASSES
        ):
            written_objects.append(
                _write_special_openstudio_object(openstudio, model, node)
            )
        elif (
            node.source_class in _GENERIC_OPENSTUDIO_SOURCE_CLASSES
            and node.source_class not in _TERMINAL_COMPONENT_SOURCE_CLASSES
        ):
            written_objects.append(
                _write_generic_openstudio_object(openstudio, model, node)
            )
        elif node.source_class in _TERMINAL_COMPONENT_SOURCE_CLASSES:
            continue

    context.resolve_pending_reference_nodes()

    saved_path = None
    if output_path is not None:
        saved_path = Path(output_path)
        saved_path.parent.mkdir(parents=True, exist_ok=True)
        model.save(openstudio.path(str(saved_path)), True)

    return OpenStudioWriteResult(
        status="written",
        written_objects=tuple(written_objects),
        output_path=saved_path,
    )


def write_detailed_hvac_specification_to_openstudio_model(
    *,
    model: Any,
    specification: Mapping[str, Any],
    output_path: Path | None = None,
) -> OpenStudioWriteResult:
    """Decode a DetailedHVAC Ironbug spec and write supported objects."""

    graph = detailed_hvac_specification_to_console_graph(specification)
    return write_first_family_to_openstudio_model(
        model=model,
        graph=graph,
        output_path=output_path,
    )


def write_console_model_specification_to_openstudio_model(
    *,
    model: Any,
    specification: ConsoleModelSpecification,
    output_path: Path | None = None,
) -> OpenStudioWriteResult:
    """Write all supported roots of an Ironbug model specification."""

    openstudio = _import_openstudio()
    written_objects: list[OpenStudioWrittenObject] = []
    diagnostics = []
    if _has_hvac_content(specification.hvac_specification):
        hvac_result = write_detailed_hvac_specification_to_openstudio_model(
            model=model,
            specification=specification.hvac_specification,
        )
        written_objects.extend(hvac_result.written_objects)
        diagnostics.extend(hvac_result.diagnostics)
        if hvac_result.status != "written":
            return OpenStudioWriteResult(
                status="blocked",
                written_objects=tuple(written_objects),
                diagnostics=tuple(diagnostics),
            )

    for root_payload in specification.root_payloads:
        graph = source_payload_to_console_graph(root_payload)
        root_result = write_first_family_to_openstudio_model(
            model=model,
            graph=graph,
        )
        written_objects.extend(root_result.written_objects)
        diagnostics.extend(root_result.diagnostics)
        if root_result.status != "written":
            return OpenStudioWriteResult(
                status="blocked",
                written_objects=tuple(written_objects),
                diagnostics=tuple(diagnostics),
            )

    saved_path = None
    if output_path is not None:
        saved_path = Path(output_path)
        saved_path.parent.mkdir(parents=True, exist_ok=True)
        model.save(openstudio.path(str(saved_path)), True)
    return OpenStudioWriteResult(
        status="written",
        written_objects=tuple(written_objects),
        diagnostics=tuple(diagnostics),
        output_path=saved_path,
    )


def _has_hvac_content(specification: Mapping[str, Any]) -> bool:
    return any(
        bool(specification.get(key))
        for key in ("AirLoops", "PlantLoops", "VariableRefrigerantFlows")
    )


def _inlet_mixer_zone_equipment_identifiers(graph: ConsoleGraph) -> frozenset[str]:
    identifiers: set[str] = set()
    for node in graph.nodes:
        if node.source_class != "IB_AirTerminalSingleDuctInletSideMixer":
            continue
        for child_identifier in node.children:
            child = graph.node_by_identifier(str(child_identifier))
            if child.source_class in _ZONE_HVAC_EQUIPMENT_SOURCE_CLASSES:
                identifiers.add(child.identifier)
    return frozenset(identifiers)


def _import_openstudio() -> Any:
    import openstudio

    return openstudio
