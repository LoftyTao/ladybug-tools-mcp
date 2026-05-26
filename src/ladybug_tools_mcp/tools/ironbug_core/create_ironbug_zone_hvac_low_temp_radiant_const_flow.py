'MCP tool for detailed_hvac_zone_equipment_low_temp_radiant_const_flow.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    add_ironbug_thermal_zone_equipment,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_zone_equipment_low_temp_radiant_const_flow tool.'

    @mcp.tool(
        name='zone_equipment_low_temp_radiant_const_flow',
        description=(
            'Create IB_ZoneHVACLowTempRadiantConstFlow, the Ironbug and EnergyPlus ZoneHVAC:LowTemperatureRadiant:ConstantFlow hydronic radiant zone equipment with heating/cooling radiant coil children, tubing geometry, pump fields, and ThermalZone placement. Use it for constant-flow low-temperature radiant systems, not as a baseboard, high-temperature radiant heater, air terminal, or result reader. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'zone-equipment', 'radiant', 'low-temperature', 'hydronic', 'constant-flow', 'heating', 'cooling', 'thermal-zone', 'author'},
        timeout=20,
    )
    def create_ironbug_zone_hvac_low_temp_radiant_const_flow(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json where the Ironbug model and created constant-flow radiant zone equipment are stored."),
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
            Field(description="Stable identifier for the new IB_ZoneHVACLowTempRadiantConstFlow object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for the low-temperature radiant constant-flow availability schedule.'),
        ] = None,
        radiant_surface_type: Annotated[
            str | None,
            Field(description='Optional RadiantSurfaceType value; maps to Ironbug IB_ZoneHVACLowTempRadiantConstFlow field RadiantSurfaceType.'),
        ] = None,
        fluidto_radiant_surface_heat_transfer_model: Annotated[
            str | None,
            Field(description='Optional FluidtoRadiantSurfaceHeatTransferModel value; maps to Ironbug IB_ZoneHVACLowTempRadiantConstFlow field FluidtoRadiantSurfaceHeatTransferModel.'),
        ] = None,
        hydronic_tubing_inside_diameter: Annotated[
            float | None,
            Field(description='Optional HydronicTubingInsideDiameter value; maps to Ironbug IB_ZoneHVACLowTempRadiantConstFlow field HydronicTubingInsideDiameter.'),
        ] = None,
        hydronic_tubing_outside_diameter: Annotated[
            float | None,
            Field(description='Optional HydronicTubingOutsideDiameter value; maps to Ironbug IB_ZoneHVACLowTempRadiantConstFlow field HydronicTubingOutsideDiameter.'),
        ] = None,
        hydronic_tubing_length: Annotated[
            float | str | None,
            Field(description='Optional hydronic tubing length for the radiant surface; accepts a numeric length or an autosizing string supported by the Ironbug source field.'),
        ] = None,
        hydronic_tubing_conductivity: Annotated[
            float | None,
            Field(description='Optional HydronicTubingConductivity value; maps to Ironbug IB_ZoneHVACLowTempRadiantConstFlow field HydronicTubingConductivity.'),
        ] = None,
        temperature_control_type: Annotated[
            str | None,
            Field(description='Optional TemperatureControlType value; maps to Ironbug IB_ZoneHVACLowTempRadiantConstFlow field TemperatureControlType.'),
        ] = None,
        running_mean_outdoor_dry_bulb_temperature_weighting_factor: Annotated[
            float | None,
            Field(description='Optional RunningMeanOutdoorDryBulbTemperatureWeightingFactor value; maps to Ironbug IB_ZoneHVACLowTempRadiantConstFlow field RunningMeanOutdoorDryBulbTemperatureWeightingFactor.'),
        ] = None,
        rated_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional RatedFlowRate value; maps to Ironbug IB_ZoneHVACLowTempRadiantConstFlow field RatedFlowRate.'),
        ] = None,
        pump_flow_rate_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for PumpFlowRateSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_ZoneHVACLowTempRadiantConstFlow field PumpFlowRateSchedule (IB_Schedule).'),
        ] = None,
        rated_pump_head: Annotated[
            float | None,
            Field(description='Optional RatedPumpHead value; maps to Ironbug IB_ZoneHVACLowTempRadiantConstFlow field RatedPumpHead.'),
        ] = None,
        rated_power_consumption: Annotated[
            float | None,
            Field(description='Optional RatedPowerConsumption value; maps to Ironbug IB_ZoneHVACLowTempRadiantConstFlow field RatedPowerConsumption.'),
        ] = None,
        motor_efficiency: Annotated[
            float | None,
            Field(description='Optional MotorEfficiency value; maps to Ironbug IB_ZoneHVACLowTempRadiantConstFlow field MotorEfficiency.'),
        ] = None,
        fractionof_motor_inefficienciesto_fluid_stream: Annotated[
            float | None,
            Field(description='Optional FractionofMotorInefficienciestoFluidStream value; maps to Ironbug IB_ZoneHVACLowTempRadiantConstFlow field FractionofMotorInefficienciestoFluidStream.'),
        ] = None,
        numberof_circuits: Annotated[
            str | None,
            Field(description='Optional NumberofCircuits value; maps to Ironbug IB_ZoneHVACLowTempRadiantConstFlow field NumberofCircuits.'),
        ] = None,
        circuit_length: Annotated[
            float | None,
            Field(description='Optional CircuitLength value; maps to Ironbug IB_ZoneHVACLowTempRadiantConstFlow field CircuitLength.'),
        ] = None,
        changeover_delay_time_period_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for ChangeoverDelayTimePeriodSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_ZoneHVACLowTempRadiantConstFlow field ChangeoverDelayTimePeriodSchedule (IB_Schedule).'),
        ] = None,
        thermal_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ThermalZone target or same-model identifier. When provided, the "
                    "created zone equipment is added to that ThermalZone's ZoneEquipments."
                )
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_ZoneHVACLowTempRadiantConstFlow field Name.'),
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
        heating_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_CoilHeatingLowTempRadiantConstFlow target used as the constant-flow radiant heating coil child."
                )
            ),
        ] = None,
        cooling_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_CoilCoolingLowTempRadiantConstFlow target used as the constant-flow radiant cooling coil child."
                )
            ),
        ] = None,
        pipe_length: Annotated[
            float | None,
            Field(description='Optional Ironbug component parameter pipe_length stored as source private property TubingLength.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug ZoneHVAC:LowTemperatureRadiant:ConstantFlow object."""

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
        if radiant_surface_type is not None:
            source_fields['RadiantSurfaceType'] = radiant_surface_type
        if fluidto_radiant_surface_heat_transfer_model is not None:
            source_fields['FluidtoRadiantSurfaceHeatTransferModel'] = fluidto_radiant_surface_heat_transfer_model
        if hydronic_tubing_inside_diameter is not None:
            source_fields['HydronicTubingInsideDiameter'] = hydronic_tubing_inside_diameter
        if hydronic_tubing_outside_diameter is not None:
            source_fields['HydronicTubingOutsideDiameter'] = hydronic_tubing_outside_diameter
        if hydronic_tubing_length is not None:
            source_fields['HydronicTubingLength'] = hydronic_tubing_length
        if hydronic_tubing_conductivity is not None:
            source_fields['HydronicTubingConductivity'] = hydronic_tubing_conductivity
        if temperature_control_type is not None:
            source_fields['TemperatureControlType'] = temperature_control_type
        if running_mean_outdoor_dry_bulb_temperature_weighting_factor is not None:
            source_fields['RunningMeanOutdoorDryBulbTemperatureWeightingFactor'] = running_mean_outdoor_dry_bulb_temperature_weighting_factor
        if rated_flow_rate is not None:
            source_fields['RatedFlowRate'] = rated_flow_rate
        if pump_flow_rate_schedule_target is not None:
            source_field_targets['PumpFlowRateSchedule'] = pump_flow_rate_schedule_target
        if rated_pump_head is not None:
            source_fields['RatedPumpHead'] = rated_pump_head
        if rated_power_consumption is not None:
            source_fields['RatedPowerConsumption'] = rated_power_consumption
        if motor_efficiency is not None:
            source_fields['MotorEfficiency'] = motor_efficiency
        if fractionof_motor_inefficienciesto_fluid_stream is not None:
            source_fields['FractionofMotorInefficienciestoFluidStream'] = fractionof_motor_inefficienciesto_fluid_stream
        if numberof_circuits is not None:
            source_fields['NumberofCircuits'] = numberof_circuits
        if circuit_length is not None:
            source_fields['CircuitLength'] = circuit_length
        if changeover_delay_time_period_schedule_target is not None:
            source_field_targets['ChangeoverDelayTimePeriodSchedule'] = changeover_delay_time_period_schedule_target
        ib_properties: dict[str, Any] = {}
        if pipe_length is not None:
            ib_properties['TubingLength'] = pipe_length
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ZoneHVACLowTempRadiantConstFlow',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            ib_properties=ib_properties or None,
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
            zone = add_ironbug_thermal_zone_equipment(
                garden_root=garden_root,
                ironbug_model_target=latest_model_target,
                thermal_zone_target=thermal_zone_target,
                zone_equipment_target=created["target"],
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
