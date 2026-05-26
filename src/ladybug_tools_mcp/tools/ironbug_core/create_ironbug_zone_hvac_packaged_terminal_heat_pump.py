'MCP tool for detailed_hvac_zone_equipment_pthp.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core import relationships as relationship_service



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_zone_equipment_pthp tool.'

    @mcp.tool(
        name='zone_equipment_pthp',
        description=(
            'Create IB_ZoneHVACPackagedTerminalHeatPump, an Ironbug packaged terminal '
            'heat pump (PTHP) zone-equipment component that maps downstream to '
            'EnergyPlus ZoneHVAC:PackagedTerminalHeatPump and OpenStudio '
            'ZoneHVACPackagedTerminalHeatPump. Bind a supply fan, DX heating coil, '
            'DX cooling coil, supplemental heating coil, and optional IB_ThermalZone '
            'placement through explicit targets. This authors Ironbug DetailedHVAC '
            'input, not a Honeybee Energy HVAC template. Returns target, '
            'updated_model_target, summary_view, persistence_receipt, and report for '
            'downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'zone-equipment',
            'packaged-terminal',
            'pthp',
            'heat-pump',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_zone_hvac_packaged_terminal_heat_pump(
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
            Field(description="Stable identifier for the new IB_ZoneHVACPackagedTerminalHeatPump object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for AvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Schedule values above zero make the PTHP available.'),
        ] = None,
        outdoor_air_mixer_object_type: Annotated[
            str | None,
            Field(description='Optional OutdoorAirMixerObjectType value; maps to Ironbug IB_ZoneHVACPackagedTerminalHeatPump field OutdoorAirMixerObjectType.'),
        ] = None,
        outdoor_air_mixer_name: Annotated[
            str | None,
            Field(description='Optional OutdoorAirMixerName value; maps to Ironbug IB_ZoneHVACPackagedTerminalHeatPump field OutdoorAirMixerName.'),
        ] = None,
        supply_air_flow_rate_during_cooling_operation: Annotated[
            float | str | None,
            Field(description='Optional SupplyAirFlowRateDuringCoolingOperation value; maps to Ironbug IB_ZoneHVACPackagedTerminalHeatPump field SupplyAirFlowRateDuringCoolingOperation.'),
        ] = None,
        supply_air_flow_rate_during_heating_operation: Annotated[
            float | str | None,
            Field(description='Optional SupplyAirFlowRateDuringHeatingOperation value; maps to Ironbug IB_ZoneHVACPackagedTerminalHeatPump field SupplyAirFlowRateDuringHeatingOperation.'),
        ] = None,
        supply_air_flow_rate_when_no_coolingor_heatingis_needed: Annotated[
            float | str | None,
            Field(description='Optional SupplyAirFlowRateWhenNoCoolingorHeatingisNeeded value; maps to Ironbug IB_ZoneHVACPackagedTerminalHeatPump field SupplyAirFlowRateWhenNoCoolingorHeatingisNeeded.'),
        ] = None,
        no_load_supply_air_flow_rate_control_set_to_low_speed: Annotated[
            bool | str | None,
            Field(description='Optional NoLoadSupplyAirFlowRateControlSetToLowSpeed value; maps to Ironbug IB_ZoneHVACPackagedTerminalHeatPump field NoLoadSupplyAirFlowRateControlSetToLowSpeed.'),
        ] = None,
        outdoor_air_flow_rate_during_cooling_operation: Annotated[
            float | str | None,
            Field(description='Optional OutdoorAirFlowRateDuringCoolingOperation value; maps to Ironbug IB_ZoneHVACPackagedTerminalHeatPump field OutdoorAirFlowRateDuringCoolingOperation.'),
        ] = None,
        outdoor_air_flow_rate_during_heating_operation: Annotated[
            float | str | None,
            Field(description='Optional OutdoorAirFlowRateDuringHeatingOperation value; maps to Ironbug IB_ZoneHVACPackagedTerminalHeatPump field OutdoorAirFlowRateDuringHeatingOperation.'),
        ] = None,
        outdoor_air_flow_rate_when_no_coolingor_heatingis_needed: Annotated[
            float | str | None,
            Field(description='Optional OutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded value; maps to Ironbug IB_ZoneHVACPackagedTerminalHeatPump field OutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded.'),
        ] = None,
        heating_convergence_tolerance: Annotated[
            float | None,
            Field(description='Optional HeatingConvergenceTolerance value; maps to Ironbug IB_ZoneHVACPackagedTerminalHeatPump field HeatingConvergenceTolerance.'),
        ] = None,
        minimum_outdoor_dry_bulb_temperaturefor_compressor_operation: Annotated[
            float | None,
            Field(description='Optional MinimumOutdoorDryBulbTemperatureforCompressorOperation value; maps to Ironbug IB_ZoneHVACPackagedTerminalHeatPump field MinimumOutdoorDryBulbTemperatureforCompressorOperation.'),
        ] = None,
        cooling_convergence_tolerance: Annotated[
            float | None,
            Field(description='Optional CoolingConvergenceTolerance value; maps to Ironbug IB_ZoneHVACPackagedTerminalHeatPump field CoolingConvergenceTolerance.'),
        ] = None,
        maximum_supply_air_temperaturefrom_supplemental_heater: Annotated[
            float | str | None,
            Field(description='Optional MaximumSupplyAirTemperaturefromSupplementalHeater value; maps to Ironbug IB_ZoneHVACPackagedTerminalHeatPump field MaximumSupplyAirTemperaturefromSupplementalHeater.'),
        ] = None,
        maximum_outdoor_dry_bulb_temperaturefor_supplemental_heater_operation: Annotated[
            float | None,
            Field(description='Optional MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation value; maps to Ironbug IB_ZoneHVACPackagedTerminalHeatPump field MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation.'),
        ] = None,
        fan_placement: Annotated[
            str | None,
            Field(description='Optional FanPlacement value; maps to Ironbug IB_ZoneHVACPackagedTerminalHeatPump field FanPlacement.'),
        ] = None,
        supply_air_fan_operating_mode_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for SupplyAirFanOperatingModeSchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Values above zero usually indicate continuous fan operation.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_ZoneHVACPackagedTerminalHeatPump field Name.'),
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
        fan_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_FanOnOff, IB_FanConstantVolume, or IB_FanSystemModel target or same-model identifier used as the PTHP supply fan."),
        ] = None,
        heating_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional PTHP DX heating coil target or same-model identifier, usually IB_CoilHeatingDXSingleSpeed."),
        ] = None,
        cooling_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional PTHP DX cooling coil target or same-model identifier, usually IB_CoilCoolingDXSingleSpeed."),
        ] = None,
        supplemental_heating_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional PTHP supplemental heating coil target or same-model identifier, usually IB_CoilHeatingElectric."),
        ] = None,
        thermal_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_ThermalZone target or same-model identifier to receive this PTHP as zone equipment; this does not create Honeybee Room geometry."),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_ZoneHVACPackagedTerminalHeatPump as reviewed PTHP zone equipment."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if outdoor_air_mixer_object_type is not None:
            source_fields['OutdoorAirMixerObjectType'] = outdoor_air_mixer_object_type
        if outdoor_air_mixer_name is not None:
            source_fields['OutdoorAirMixerName'] = outdoor_air_mixer_name
        if supply_air_flow_rate_during_cooling_operation is not None:
            source_fields['SupplyAirFlowRateDuringCoolingOperation'] = supply_air_flow_rate_during_cooling_operation
        if supply_air_flow_rate_during_heating_operation is not None:
            source_fields['SupplyAirFlowRateDuringHeatingOperation'] = supply_air_flow_rate_during_heating_operation
        if supply_air_flow_rate_when_no_coolingor_heatingis_needed is not None:
            source_fields['SupplyAirFlowRateWhenNoCoolingorHeatingisNeeded'] = supply_air_flow_rate_when_no_coolingor_heatingis_needed
        if no_load_supply_air_flow_rate_control_set_to_low_speed is not None:
            source_fields['NoLoadSupplyAirFlowRateControlSetToLowSpeed'] = no_load_supply_air_flow_rate_control_set_to_low_speed
        if outdoor_air_flow_rate_during_cooling_operation is not None:
            source_fields['OutdoorAirFlowRateDuringCoolingOperation'] = outdoor_air_flow_rate_during_cooling_operation
        if outdoor_air_flow_rate_during_heating_operation is not None:
            source_fields['OutdoorAirFlowRateDuringHeatingOperation'] = outdoor_air_flow_rate_during_heating_operation
        if outdoor_air_flow_rate_when_no_coolingor_heatingis_needed is not None:
            source_fields['OutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded'] = outdoor_air_flow_rate_when_no_coolingor_heatingis_needed
        if heating_convergence_tolerance is not None:
            source_fields['HeatingConvergenceTolerance'] = heating_convergence_tolerance
        if minimum_outdoor_dry_bulb_temperaturefor_compressor_operation is not None:
            source_fields['MinimumOutdoorDryBulbTemperatureforCompressorOperation'] = minimum_outdoor_dry_bulb_temperaturefor_compressor_operation
        if cooling_convergence_tolerance is not None:
            source_fields['CoolingConvergenceTolerance'] = cooling_convergence_tolerance
        if maximum_supply_air_temperaturefrom_supplemental_heater is not None:
            source_fields['MaximumSupplyAirTemperaturefromSupplementalHeater'] = maximum_supply_air_temperaturefrom_supplemental_heater
        if maximum_outdoor_dry_bulb_temperaturefor_supplemental_heater_operation is not None:
            source_fields['MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation'] = maximum_outdoor_dry_bulb_temperaturefor_supplemental_heater_operation
        if fan_placement is not None:
            source_fields['FanPlacement'] = fan_placement
        if supply_air_fan_operating_mode_schedule_target is not None:
            source_field_targets['SupplyAirFanOperatingModeSchedule'] = supply_air_fan_operating_mode_schedule_target
        child_targets = [
            fan_target,
            heating_coil_target,
            cooling_coil_target,
            supplemental_heating_coil_target,
        ]
        if any(target is not None for target in child_targets) and not all(
            target is not None for target in child_targets
        ):
            raise ValueError(
                "fan_target, heating_coil_target, cooling_coil_target, and "
                "supplemental_heating_coil_target must be provided together for "
                "PTHP child binding."
            )
        result = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ZoneHVACPackagedTerminalHeatPump',
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
        binding_steps: list[str] = []
        current_model_target = result["updated_model_target"]
        current_target = result["target"]
        if (
            fan_target is not None
            and heating_coil_target is not None
            and cooling_coil_target is not None
            and supplemental_heating_coil_target is not None
        ):
            children_result = relationship_service.set_ironbug_pthp_children(
                garden_root=garden_root,
                ironbug_model_target=current_model_target,
                pthp_target=current_target,
                fan_target=fan_target,
                heating_coil_target=heating_coil_target,
                cooling_coil_target=cooling_coil_target,
                supplemental_heating_coil_target=supplemental_heating_coil_target,
            )
            current_model_target = children_result["updated_model_target"]
            current_target = children_result["target"]
            binding_steps.append("pthp_children")
        if thermal_zone_target is not None:
            zone_result = relationship_service.add_ironbug_thermal_zone_equipment(
                garden_root=garden_root,
                ironbug_model_target=current_model_target,
                thermal_zone_target=thermal_zone_target,
                zone_equipment_target=current_target,
            )
            current_model_target = zone_result["updated_model_target"]
            binding_steps.append("thermal_zone_equipment")
        current_target["model_target"] = current_model_target
        result["target"] = current_target
        result["object_target"] = current_target
        result["updated_model_target"] = current_model_target
        result["summary_view"]["binding_steps"] = binding_steps
        return result
