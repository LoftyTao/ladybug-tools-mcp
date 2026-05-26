'MCP tool for detailed_hvac_zone_equipment_four_pipe_fan_coil.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    add_ironbug_thermal_zone_equipment,
    set_ironbug_fan_coil_children,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_zone_equipment_four_pipe_fan_coil tool.'

    @mcp.tool(
        name='zone_equipment_four_pipe_fan_coil',
        description=(
            'Create IB_ZoneHVACFourPipeFanCoil, an Ironbug four-pipe fan coil unit '
            '(FCU) / zone equipment object that maps downstream to the EnergyPlus '
            'ZoneHVAC:FourPipeFanCoil and OpenStudio ZoneHVACFourPipeFanCoil concepts. '
            'Bind the hot-water heating coil, chilled-water cooling coil, supply fan, '
            'and optional IB_ThermalZone placement through explicit targets. This authors '
            'Ironbug DetailedHVAC input, not a Honeybee Energy HVAC template; run the '
            'standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
            'Returns target, updated_model_target, summary_view, persistence_receipt, '
            'and report for downstream DetailedHVAC assembly.'
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'zone-equipment',
            'fan-coil',
            'fcu',
            'author',
                    'fan',
},
        timeout=20,
    )
    def create_ironbug_zone_hvac_four_pipe_fan_coil(
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
            Field(description="Stable identifier for the new IB_ZoneHVACFourPipeFanCoil object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        capacity_control_method: Annotated[
            str | None,
            Field(
                description=(
                    "Optional fan-coil capacity control method. Common EnergyPlus/OpenStudio "
                    "values include ConstantFanVariableFlow, CyclingFan, VariableFanVariableFlow, "
                    "VariableFanConstantFlow, MultiSpeedFan, and ASHRAE90VariableFan; choose a "
                    "method compatible with the supplied fan target."
                )
            ),
        ] = None,
        heating_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_CoilHeatingWater target or same-model identifier to bind "
                    "as the FCU hot-water heating coil. Provide heating_coil_target, "
                    "cooling_coil_target, and fan_target together when overriding defaults."
                )
            ),
        ] = None,
        cooling_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_CoilCoolingWater target or same-model identifier to bind "
                    "as the FCU chilled-water cooling coil. Provide heating_coil_target, "
                    "cooling_coil_target, and fan_target together when overriding defaults."
                )
            ),
        ] = None,
        fan_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_FanOnOff, IB_FanConstantVolume, or IB_FanSystemModel "
                    "target or same-model identifier to bind as the FCU supply fan. Provide "
                    "heating_coil_target, cooling_coil_target, and fan_target together when "
                    "overriding defaults."
                )
            ),
        ] = None,
        thermal_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ThermalZone target or same-model identifier for DetailedHVAC "
                    "zone-equipment placement. This links the FCU to an Ironbug thermal zone; "
                    "it does not create or edit Honeybee Room geometry."
                )
            ),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for AvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Maps to Ironbug IB_ZoneHVACFourPipeFanCoil field AvailabilitySchedule.'),
        ] = None,
        maximum_supply_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MaximumSupplyAirFlowRate value; maps to Ironbug IB_ZoneHVACFourPipeFanCoil field MaximumSupplyAirFlowRate.'),
        ] = None,
        low_speed_supply_air_flow_ratio: Annotated[
            float | None,
            Field(description='Optional LowSpeedSupplyAirFlowRatio value; maps to Ironbug IB_ZoneHVACFourPipeFanCoil field LowSpeedSupplyAirFlowRatio.'),
        ] = None,
        medium_speed_supply_air_flow_ratio: Annotated[
            float | None,
            Field(description='Optional MediumSpeedSupplyAirFlowRatio value; maps to Ironbug IB_ZoneHVACFourPipeFanCoil field MediumSpeedSupplyAirFlowRatio.'),
        ] = None,
        maximum_outdoor_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MaximumOutdoorAirFlowRate value; maps to Ironbug IB_ZoneHVACFourPipeFanCoil field MaximumOutdoorAirFlowRate.'),
        ] = None,
        outdoor_air_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for OutdoorAirSchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Maps to Ironbug IB_ZoneHVACFourPipeFanCoil field OutdoorAirSchedule.'),
        ] = None,
        outdoor_air_mixer_object_type: Annotated[
            str | None,
            Field(description='Optional OutdoorAirMixerObjectType value; maps to Ironbug IB_ZoneHVACFourPipeFanCoil field OutdoorAirMixerObjectType.'),
        ] = None,
        maximum_cold_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MaximumColdWaterFlowRate value; maps to Ironbug IB_ZoneHVACFourPipeFanCoil field MaximumColdWaterFlowRate.'),
        ] = None,
        minimum_cold_water_flow_rate: Annotated[
            float | None,
            Field(description='Optional MinimumColdWaterFlowRate value; maps to Ironbug IB_ZoneHVACFourPipeFanCoil field MinimumColdWaterFlowRate.'),
        ] = None,
        cooling_convergence_tolerance: Annotated[
            float | None,
            Field(description='Optional CoolingConvergenceTolerance value; maps to Ironbug IB_ZoneHVACFourPipeFanCoil field CoolingConvergenceTolerance.'),
        ] = None,
        maximum_hot_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MaximumHotWaterFlowRate value; maps to Ironbug IB_ZoneHVACFourPipeFanCoil field MaximumHotWaterFlowRate.'),
        ] = None,
        minimum_hot_water_flow_rate: Annotated[
            float | None,
            Field(description='Optional MinimumHotWaterFlowRate value; maps to Ironbug IB_ZoneHVACFourPipeFanCoil field MinimumHotWaterFlowRate.'),
        ] = None,
        heating_convergence_tolerance: Annotated[
            float | None,
            Field(description='Optional HeatingConvergenceTolerance value; maps to Ironbug IB_ZoneHVACFourPipeFanCoil field HeatingConvergenceTolerance.'),
        ] = None,
        supply_air_fan_operating_mode_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for SupplyAirFanOperatingModeSchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Zero values usually mean cycling fan operation; nonzero values usually mean continuous fan operation.'),
        ] = None,
        minimum_supply_air_temperature_in_cooling_mode: Annotated[
            float | str | None,
            Field(description='Optional MinimumSupplyAirTemperatureInCoolingMode value; maps to Ironbug IB_ZoneHVACFourPipeFanCoil field MinimumSupplyAirTemperatureInCoolingMode.'),
        ] = None,
        maximum_supply_air_temperature_in_heating_mode: Annotated[
            float | str | None,
            Field(description='Optional MaximumSupplyAirTemperatureInHeatingMode value; maps to Ironbug IB_ZoneHVACFourPipeFanCoil field MaximumSupplyAirTemperatureInHeatingMode.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_ZoneHVACFourPipeFanCoil field Name.'),
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
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_ZoneHVACFourPipeFanCoil as reviewed Ironbug FCU zone equipment."""

        child_targets = (heating_coil_target, cooling_coil_target, fan_target)
        if any(item is not None for item in child_targets) and not all(
            item is not None for item in child_targets
        ):
            raise ValueError(
                "heating_coil_target, cooling_coil_target, and fan_target must "
                "be provided together for fan coil child binding."
            )
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if capacity_control_method is not None:
            source_fields['CapacityControlMethod'] = capacity_control_method
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if maximum_supply_air_flow_rate is not None:
            source_fields['MaximumSupplyAirFlowRate'] = maximum_supply_air_flow_rate
        if low_speed_supply_air_flow_ratio is not None:
            source_fields['LowSpeedSupplyAirFlowRatio'] = low_speed_supply_air_flow_ratio
        if medium_speed_supply_air_flow_ratio is not None:
            source_fields['MediumSpeedSupplyAirFlowRatio'] = medium_speed_supply_air_flow_ratio
        if maximum_outdoor_air_flow_rate is not None:
            source_fields['MaximumOutdoorAirFlowRate'] = maximum_outdoor_air_flow_rate
        if outdoor_air_schedule_target is not None:
            source_field_targets['OutdoorAirSchedule'] = outdoor_air_schedule_target
        if outdoor_air_mixer_object_type is not None:
            source_fields['OutdoorAirMixerObjectType'] = outdoor_air_mixer_object_type
        if maximum_cold_water_flow_rate is not None:
            source_fields['MaximumColdWaterFlowRate'] = maximum_cold_water_flow_rate
        if minimum_cold_water_flow_rate is not None:
            source_fields['MinimumColdWaterFlowRate'] = minimum_cold_water_flow_rate
        if cooling_convergence_tolerance is not None:
            source_fields['CoolingConvergenceTolerance'] = cooling_convergence_tolerance
        if maximum_hot_water_flow_rate is not None:
            source_fields['MaximumHotWaterFlowRate'] = maximum_hot_water_flow_rate
        if minimum_hot_water_flow_rate is not None:
            source_fields['MinimumHotWaterFlowRate'] = minimum_hot_water_flow_rate
        if heating_convergence_tolerance is not None:
            source_fields['HeatingConvergenceTolerance'] = heating_convergence_tolerance
        if supply_air_fan_operating_mode_schedule_target is not None:
            source_field_targets['SupplyAirFanOperatingModeSchedule'] = supply_air_fan_operating_mode_schedule_target
        if minimum_supply_air_temperature_in_cooling_mode is not None:
            source_fields['MinimumSupplyAirTemperatureInCoolingMode'] = minimum_supply_air_temperature_in_cooling_mode
        if maximum_supply_air_temperature_in_heating_mode is not None:
            source_fields['MaximumSupplyAirTemperatureInHeatingMode'] = maximum_supply_air_temperature_in_heating_mode
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ZoneHVACFourPipeFanCoil',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
        latest_model_target = created["updated_model_target"]
        binding_summary: dict[str, Any] = {}
        if all(item is not None for item in child_targets):
            children = set_ironbug_fan_coil_children(
                garden_root=garden_root,
                ironbug_model_target=latest_model_target,
                fan_coil_target=created["target"],
                heating_coil_target=heating_coil_target,
                cooling_coil_target=cooling_coil_target,
                fan_target=fan_target,
            )
            latest_model_target = children["updated_model_target"]
            created["target"] = children["target"]
            binding_summary["children_bound"] = True
        else:
            binding_summary["children_bound"] = False
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
