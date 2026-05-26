'MCP tool for detailed_hvac_air_terminal_single_duct_constant_volume_four_pipe_beam.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    set_ironbug_thermal_zone_air_terminal,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_air_terminal_single_duct_constant_volume_four_pipe_beam tool.'

    @mcp.tool(
        name='air_terminal_single_duct_constant_volume_four_pipe_beam',
        description=(
            'Create IB_AirTerminalSingleDuctConstantVolumeFourPipeBeam, an '
            'Ironbug single-duct constant-volume four-pipe beam air terminal '
            'that maps downstream to EnergyPlus/OpenStudio '
            'AirTerminal:SingleDuct:ConstantVolume:FourPipeBeam. Use the '
            'returned target as a hydronic beam terminal unit, attach '
            'four-pipe beam cooling and heating coil children when needed, '
            'and bind it to an IB_ThermalZone through thermal_zone_target or '
            'the ThermalZone tool. This is not zone equipment and not a '
            'Honeybee Energy HVAC template. Returns target, summary_view, '
            'persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'air-terminal', 'terminal-unit', 'single-duct', 'constant-volume', 'beam', 'four-pipe', 'heating', 'cooling', 'hot-water', 'chilled-water', 'thermal-zone', 'author'},
        timeout=20,
    )
    def create_ironbug_air_terminal_single_duct_constant_volume_four_pipe_beam(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Required Ironbug model target returned by detailed_hvac_create_model; '
                    "pass result['target'], not the .ibjson file path."
                )
            ),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for the new IB_AirTerminalSingleDuctConstantVolumeFourPipeBeam object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        primary_air_availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for PrimaryAirAvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Schedule values above zero allow primary air.'),
        ] = None,
        cooling_availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for CoolingAvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Schedule values above zero allow beam cooling.'),
        ] = None,
        heating_availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for HeatingAvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Schedule values above zero allow beam heating.'),
        ] = None,
        design_primary_air_volume_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional DesignPrimaryAirVolumeFlowRate in m3/s, or an EnergyPlus autosizable literal accepted by Ironbug.'),
        ] = None,
        design_chilled_water_volume_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional DesignChilledWaterVolumeFlowRate in m3/s, or an EnergyPlus autosizable literal accepted by Ironbug.'),
        ] = None,
        design_hot_water_volume_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional DesignHotWaterVolumeFlowRate in m3/s, or an EnergyPlus autosizable literal accepted by Ironbug.'),
        ] = None,
        zone_total_beam_length: Annotated[
            float | str | None,
            Field(description='Optional ZoneTotalBeamLength in meters, the sum of beam units represented by this air terminal, or an autosizable literal accepted by Ironbug.'),
        ] = None,
        rated_primary_air_flow_rateper_beam_length: Annotated[
            float | None,
            Field(description='Optional RatedPrimaryAirFlowRateperBeamLength in m3/s-m for primary air normalized by beam length.'),
        ] = None,
        thermal_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ThermalZone target or same-model identifier to "
                    "bind this four-pipe beam air terminal to after creation; "
                    "this does not create Honeybee Room geometry."
                )
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_AirTerminalSingleDuctConstantVolumeFourPipeBeam field Name.'),
        ] = None,
        output_variable_names: Annotated[
            list[str] | None,
            Field(
                description="Optional explicit Ironbug output variable names for this object."
            ),
        ] = None,
        output_reporting_frequency: Annotated[
            Literal["Detail", "Hourly", "Daily", "Monthly", "RunPeriod"],
            Field(description="Reporting frequency used for output_variable_names."),
        ] = "Hourly",
        ems_sensor_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional IB_EnergyManagementSystemSensor targets for CustomSensors."),
        ] = None,
        ems_actuator_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional IB_EnergyManagementSystemActuator targets for CustomActuators."),
        ] = None,
        ems_internal_variable_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_EnergyManagementSystemInternalVariable targets for CustomInternalVariables."
            ),
        ] = None,
        cooling_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_CoilCoolingFourPipeBeam child target or same-model "
                    "identifier for Parameter 'CoolingCoil'; use a "
                    "detailed_hvac_coil_cooling_four_pipe_beam target."
                )
            ),
        ] = None,
        heating_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_CoilHeatingFourPipeBeam child target or same-model "
                    "identifier for Parameter 'HeatingCoil'; use a "
                    "detailed_hvac_coil_heating_four_pipe_beam target."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_AirTerminalSingleDuctConstantVolumeFourPipeBeam as a reviewed four-pipe beam terminal."""

        child_targets = [
            cooling_coil_target,
            heating_coil_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if primary_air_availability_schedule_target is not None:
            source_field_targets['PrimaryAirAvailabilitySchedule'] = primary_air_availability_schedule_target
        if cooling_availability_schedule_target is not None:
            source_field_targets['CoolingAvailabilitySchedule'] = cooling_availability_schedule_target
        if heating_availability_schedule_target is not None:
            source_field_targets['HeatingAvailabilitySchedule'] = heating_availability_schedule_target
        if design_primary_air_volume_flow_rate is not None:
            source_fields['DesignPrimaryAirVolumeFlowRate'] = design_primary_air_volume_flow_rate
        if design_chilled_water_volume_flow_rate is not None:
            source_fields['DesignChilledWaterVolumeFlowRate'] = design_chilled_water_volume_flow_rate
        if design_hot_water_volume_flow_rate is not None:
            source_fields['DesignHotWaterVolumeFlowRate'] = design_hot_water_volume_flow_rate
        if zone_total_beam_length is not None:
            source_fields['ZoneTotalBeamLength'] = zone_total_beam_length
        if rated_primary_air_flow_rateper_beam_length is not None:
            source_fields['RatedPrimaryAirFlowRateperBeamLength'] = rated_primary_air_flow_rateper_beam_length
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_AirTerminalSingleDuctConstantVolumeFourPipeBeam',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            child_targets=child_targets if any(item is not None for item in child_targets) else None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
        latest_model_target = created["updated_model_target"]
        binding_summary: dict[str, Any] = {}
        if thermal_zone_target is not None:
            zone = set_ironbug_thermal_zone_air_terminal(
                garden_root=garden_root,
                ironbug_model_target=latest_model_target,
                thermal_zone_target=thermal_zone_target,
                air_terminal_target=created["target"],
            )
            latest_model_target = zone["updated_model_target"]
            created["target"]["model_target"] = latest_model_target
            binding_summary["thermal_zone_bound"] = True
            binding_summary["thermal_zone_identifier"] = zone["summary_view"][
                "thermal_zone_identifier"
            ]
        else:
            binding_summary["thermal_zone_bound"] = False
        created["updated_model_target"] = latest_model_target
        created["summary_view"] = {**created["summary_view"], **binding_summary}
        return created
