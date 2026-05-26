'MCP tool for detailed_hvac_air_terminal_single_duct_constant_volume_four_pipe_induction.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    set_ironbug_thermal_zone_air_terminal,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_air_terminal_single_duct_constant_volume_four_pipe_induction tool.'

    @mcp.tool(
        name='air_terminal_single_duct_constant_volume_four_pipe_induction',
        description=(
            'Create IB_AirTerminalSingleDuctConstantVolumeFourPipeInduction, '
            'an Ironbug single-duct four-pipe induction air terminal that '
            'maps downstream to EnergyPlus/OpenStudio '
            'AirTerminal:SingleDuct:ConstantVolume:FourPipeInduction. Use '
            'the returned target as a hydronic induction terminal, attach '
            'hot-water and chilled-water coil children when needed, and bind '
            'it to an IB_ThermalZone through thermal_zone_target or the '
            'ThermalZone tool. This induction terminal is not a PIU, not zone '
            'equipment, and not a Honeybee Energy HVAC template. Returns '
            'target, summary_view, persistence_receipt, and report for '
            'downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'air-terminal', 'terminal-unit', 'single-duct', 'constant-volume', 'induction', 'four-pipe', 'heating', 'cooling', 'hot-water', 'chilled-water', 'thermal-zone', 'author'},
        timeout=20,
    )
    def create_ironbug_air_terminal_single_duct_constant_volume_four_pipe_induction(
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
            Field(description="Stable identifier for the new IB_AirTerminalSingleDuctConstantVolumeFourPipeInduction object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for AvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Schedule values above zero make the four-pipe induction terminal available.'),
        ] = None,
        maximum_total_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MaximumTotalAirFlowRate in m3/s, or an EnergyPlus autosizable literal accepted by Ironbug.'),
        ] = None,
        induction_ratio: Annotated[
            float | None,
            Field(description='Optional InductionRatio, the induced air flow rate divided by primary air flow rate.'),
        ] = None,
        maximum_hot_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MaximumHotWaterFlowRate in m3/s for the heating coil circuit, or an autosizable literal accepted by Ironbug.'),
        ] = None,
        minimum_hot_water_flow_rate: Annotated[
            float | None,
            Field(description='Optional MinimumHotWaterFlowRate in m3/s for the heating coil circuit; EnergyPlus defaults this field to 0.0.'),
        ] = None,
        heating_convergence_tolerance: Annotated[
            float | None,
            Field(description='Optional HeatingConvergenceTolerance for hot-water coil iteration; EnergyPlus commonly defaults this field to 0.001.'),
        ] = None,
        maximum_cold_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MaximumColdWaterFlowRate in m3/s for the chilled-water coil circuit, or an autosizable literal accepted by Ironbug.'),
        ] = None,
        minimum_cold_water_flow_rate: Annotated[
            float | None,
            Field(description='Optional MinimumColdWaterFlowRate in m3/s for the chilled-water coil circuit; EnergyPlus defaults this field to 0.0.'),
        ] = None,
        cooling_convergence_tolerance: Annotated[
            float | None,
            Field(description='Optional CoolingConvergenceTolerance for chilled-water coil iteration; EnergyPlus commonly defaults this field to 0.001.'),
        ] = None,
        thermal_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ThermalZone target or same-model identifier to "
                    "bind this four-pipe induction air terminal to after "
                    "creation; this does not create Honeybee Room geometry."
                )
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_AirTerminalSingleDuctConstantVolumeFourPipeInduction field Name.'),
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
                    "Optional IB_CoilCoolingWater child target or same-model "
                    "identifier for Parameter 'CoolingCoil'; use a "
                    "detailed_hvac_coil_cooling_water target."
                )
            ),
        ] = None,
        heating_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_CoilHeatingWater child target or same-model "
                    "identifier for Parameter 'HeatingCoil'; use a "
                    "detailed_hvac_coil_heating_water target."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_AirTerminalSingleDuctConstantVolumeFourPipeInduction as a reviewed induction terminal."""

        child_targets = [
            heating_coil_target,
            cooling_coil_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if maximum_total_air_flow_rate is not None:
            source_fields['MaximumTotalAirFlowRate'] = maximum_total_air_flow_rate
        if induction_ratio is not None:
            source_fields['InductionRatio'] = induction_ratio
        if maximum_hot_water_flow_rate is not None:
            source_fields['MaximumHotWaterFlowRate'] = maximum_hot_water_flow_rate
        if minimum_hot_water_flow_rate is not None:
            source_fields['MinimumHotWaterFlowRate'] = minimum_hot_water_flow_rate
        if heating_convergence_tolerance is not None:
            source_fields['HeatingConvergenceTolerance'] = heating_convergence_tolerance
        if maximum_cold_water_flow_rate is not None:
            source_fields['MaximumColdWaterFlowRate'] = maximum_cold_water_flow_rate
        if minimum_cold_water_flow_rate is not None:
            source_fields['MinimumColdWaterFlowRate'] = minimum_cold_water_flow_rate
        if cooling_convergence_tolerance is not None:
            source_fields['CoolingConvergenceTolerance'] = cooling_convergence_tolerance
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_AirTerminalSingleDuctConstantVolumeFourPipeInduction',
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
