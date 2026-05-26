'MCP tool for detailed_hvac_air_loop_unitary_system.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_air_loop_unitary_system tool.'

    @mcp.tool(
        name='air_loop_unitary_system',
        description=(
            'Create IB_AirLoopHVACUnitarySystem, an air-loop unitary system component that can combine fan, coil, supplemental heat, and DOAS control fields, from the Ironbug LoopObjs source mirror. Attach this unitary component to an IB_AirLoopHVAC supply side through detailed_hvac_air_loop_hvac supply_component_targets; do not use it as standalone zone equipment or an air terminal. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={'ironbug', 'detailed-hvac', 'air-loop', 'unitary', 'doas', 'hvac', 'component', 'author'},
        timeout=20,
    )
    def create_ironbug_air_loop_hvac_unitary_system(
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
            Field(description="Stable identifier for the new air-loop unitary system component."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional display label shown in Ironbug/Garden summaries."),
        ] = None,
        control_type: Annotated[
            str | None,
            Field(description='Optional ControlType value; maps to Ironbug IB_AirLoopHVACUnitarySystem field ControlType.'),
        ] = None,
        dehumidification_control_type: Annotated[
            str | None,
            Field(description='Optional DehumidificationControlType value; maps to Ironbug IB_AirLoopHVACUnitarySystem field DehumidificationControlType.'),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for AvailabilitySchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirLoopHVACUnitarySystem field AvailabilitySchedule (IB_Schedule).'),
        ] = None,
        fan_placement: Annotated[
            str | None,
            Field(description='Optional FanPlacement value; maps to Ironbug IB_AirLoopHVACUnitarySystem field FanPlacement.'),
        ] = None,
        supply_air_fan_operating_mode_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for SupplyAirFanOperatingModeSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirLoopHVACUnitarySystem field SupplyAirFanOperatingModeSchedule (IB_Schedule).'),
        ] = None,
        dx_heating_coil_sizing_ratio: Annotated[
            float | None,
            Field(description='Optional DXHeatingCoilSizingRatio value; maps to Ironbug IB_AirLoopHVACUnitarySystem field DXHeatingCoilSizingRatio.'),
        ] = None,
        use_doasdx_cooling_coil: Annotated[
            bool | str | None,
            Field(description='Optional UseDOASDXCoolingCoil value; maps to Ironbug IB_AirLoopHVACUnitarySystem field UseDOASDXCoolingCoil.'),
        ] = None,
        doasdx_cooling_coil_leaving_minimum_air_temperature: Annotated[
            float | str | None,
            Field(description='Optional DOASDXCoolingCoilLeavingMinimumAirTemperature value; maps to Ironbug IB_AirLoopHVACUnitarySystem field DOASDXCoolingCoilLeavingMinimumAirTemperature.'),
        ] = None,
        latent_load_control: Annotated[
            str | None,
            Field(description='Optional LatentLoadControl value; maps to Ironbug IB_AirLoopHVACUnitarySystem field LatentLoadControl.'),
        ] = None,
        supply_air_flow_rate_during_cooling_operation: Annotated[
            float | str | None,
            Field(description='Optional SupplyAirFlowRateDuringCoolingOperation value; maps to Ironbug IB_AirLoopHVACUnitarySystem field SupplyAirFlowRateDuringCoolingOperation.'),
        ] = None,
        supply_air_flow_rate_per_floor_area_during_cooling_operation: Annotated[
            float | None,
            Field(description='Optional SupplyAirFlowRatePerFloorAreaDuringCoolingOperation value; maps to Ironbug IB_AirLoopHVACUnitarySystem field SupplyAirFlowRatePerFloorAreaDuringCoolingOperation.'),
        ] = None,
        fractionof_autosized_design_cooling_supply_air_flow_rate: Annotated[
            float | None,
            Field(description='Optional FractionofAutosizedDesignCoolingSupplyAirFlowRate value; maps to Ironbug IB_AirLoopHVACUnitarySystem field FractionofAutosizedDesignCoolingSupplyAirFlowRate.'),
        ] = None,
        design_supply_air_flow_rate_per_unitof_capacity_during_cooling_operation: Annotated[
            float | None,
            Field(description='Optional DesignSupplyAirFlowRatePerUnitofCapacityDuringCoolingOperation value; maps to Ironbug IB_AirLoopHVACUnitarySystem field DesignSupplyAirFlowRatePerUnitofCapacityDuringCoolingOperation.'),
        ] = None,
        supply_air_flow_rate_method_during_cooling_operation: Annotated[
            str | None,
            Field(description='Optional SupplyAirFlowRateMethodDuringCoolingOperation value; maps to Ironbug IB_AirLoopHVACUnitarySystem field SupplyAirFlowRateMethodDuringCoolingOperation.'),
        ] = None,
        supply_air_flow_rate_during_heating_operation: Annotated[
            float | str | None,
            Field(description='Optional SupplyAirFlowRateDuringHeatingOperation value; maps to Ironbug IB_AirLoopHVACUnitarySystem field SupplyAirFlowRateDuringHeatingOperation.'),
        ] = None,
        supply_air_flow_rate_per_floor_areaduring_heating_operation: Annotated[
            float | None,
            Field(description='Optional SupplyAirFlowRatePerFloorAreaduringHeatingOperation value; maps to Ironbug IB_AirLoopHVACUnitarySystem field SupplyAirFlowRatePerFloorAreaduringHeatingOperation.'),
        ] = None,
        fractionof_autosized_design_heating_supply_air_flow_rate: Annotated[
            float | None,
            Field(description='Optional FractionofAutosizedDesignHeatingSupplyAirFlowRate value; maps to Ironbug IB_AirLoopHVACUnitarySystem field FractionofAutosizedDesignHeatingSupplyAirFlowRate.'),
        ] = None,
        design_supply_air_flow_rate_per_unitof_capacity_during_heating_operation: Annotated[
            float | None,
            Field(description='Optional DesignSupplyAirFlowRatePerUnitofCapacityDuringHeatingOperation value; maps to Ironbug IB_AirLoopHVACUnitarySystem field DesignSupplyAirFlowRatePerUnitofCapacityDuringHeatingOperation.'),
        ] = None,
        supply_air_flow_rate_method_during_heating_operation: Annotated[
            str | None,
            Field(description='Optional SupplyAirFlowRateMethodDuringHeatingOperation value; maps to Ironbug IB_AirLoopHVACUnitarySystem field SupplyAirFlowRateMethodDuringHeatingOperation.'),
        ] = None,
        supply_air_flow_rate_when_no_coolingor_heatingis_required: Annotated[
            float | str | None,
            Field(description='Optional SupplyAirFlowRateWhenNoCoolingorHeatingisRequired value; maps to Ironbug IB_AirLoopHVACUnitarySystem field SupplyAirFlowRateWhenNoCoolingorHeatingisRequired.'),
        ] = None,
        supply_air_flow_rate_per_floor_area_when_no_coolingor_heatingis_required: Annotated[
            float | None,
            Field(description='Optional SupplyAirFlowRatePerFloorAreaWhenNoCoolingorHeatingisRequired value; maps to Ironbug IB_AirLoopHVACUnitarySystem field SupplyAirFlowRatePerFloorAreaWhenNoCoolingorHeatingisRequired.'),
        ] = None,
        fractionof_autosized_design_cooling_supply_air_flow_rate_when_no_coolingor_heatingis_required: Annotated[
            float | None,
            Field(description='Optional FractionofAutosizedDesignCoolingSupplyAirFlowRateWhenNoCoolingorHeatingisRequired value; maps to Ironbug IB_AirLoopHVACUnitarySystem field FractionofAutosizedDesignCoolingSupplyAirFlowRateWhenNoCoolingorHeatingisRequired.'),
        ] = None,
        fractionof_autosized_design_heating_supply_air_flow_rate_when_no_coolingor_heatingis_required: Annotated[
            float | None,
            Field(description='Optional FractionofAutosizedDesignHeatingSupplyAirFlowRateWhenNoCoolingorHeatingisRequired value; maps to Ironbug IB_AirLoopHVACUnitarySystem field FractionofAutosizedDesignHeatingSupplyAirFlowRateWhenNoCoolingorHeatingisRequired.'),
        ] = None,
        design_supply_air_flow_rate_per_unitof_capacity_during_cooling_operation_when_no_coolingor_heatingis_required: Annotated[
            float | None,
            Field(description='Optional DesignSupplyAirFlowRatePerUnitofCapacityDuringCoolingOperationWhenNoCoolingorHeatingisRequired value; maps to Ironbug IB_AirLoopHVACUnitarySystem field DesignSupplyAirFlowRatePerUnitofCapacityDuringCoolingOperationWhenNoCoolingorHeatingisRequired.'),
        ] = None,
        design_supply_air_flow_rate_per_unitof_capacity_during_heating_operation_when_no_coolingor_heatingis_required: Annotated[
            float | None,
            Field(description='Optional DesignSupplyAirFlowRatePerUnitofCapacityDuringHeatingOperationWhenNoCoolingorHeatingisRequired value; maps to Ironbug IB_AirLoopHVACUnitarySystem field DesignSupplyAirFlowRatePerUnitofCapacityDuringHeatingOperationWhenNoCoolingorHeatingisRequired.'),
        ] = None,
        no_load_supply_air_flow_rate_control_set_to_low_speed: Annotated[
            bool | str | None,
            Field(description='Optional NoLoadSupplyAirFlowRateControlSetToLowSpeed value; maps to Ironbug IB_AirLoopHVACUnitarySystem field NoLoadSupplyAirFlowRateControlSetToLowSpeed.'),
        ] = None,
        supply_air_flow_rate_method_when_no_coolingor_heatingis_required: Annotated[
            str | None,
            Field(description='Optional SupplyAirFlowRateMethodWhenNoCoolingorHeatingisRequired value; maps to Ironbug IB_AirLoopHVACUnitarySystem field SupplyAirFlowRateMethodWhenNoCoolingorHeatingisRequired.'),
        ] = None,
        maximum_supply_air_temperature: Annotated[
            float | str | None,
            Field(description='Optional MaximumSupplyAirTemperature value; maps to Ironbug IB_AirLoopHVACUnitarySystem field MaximumSupplyAirTemperature.'),
        ] = None,
        maximum_outdoor_dry_bulb_temperaturefor_supplemental_heater_operation: Annotated[
            float | None,
            Field(description='Optional MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation value; maps to Ironbug IB_AirLoopHVACUnitarySystem field MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation.'),
        ] = None,
        maximum_cycling_rate: Annotated[
            str | float | int | bool | None,
            Field(description='Optional MaximumCyclingRate value; maps to Ironbug IB_AirLoopHVACUnitarySystem field MaximumCyclingRate.'),
        ] = None,
        fractionof_on_cycle_power_use: Annotated[
            str | float | int | bool | None,
            Field(description='Optional FractionofOnCyclePowerUse value; maps to Ironbug IB_AirLoopHVACUnitarySystem field FractionofOnCyclePowerUse.'),
        ] = None,
        ancilliary_on_cycle_electric_power: Annotated[
            float | None,
            Field(description='Optional AncilliaryOnCycleElectricPower value; maps to Ironbug IB_AirLoopHVACUnitarySystem field AncilliaryOnCycleElectricPower.'),
        ] = None,
        ancilliary_off_cycle_electric_power: Annotated[
            float | None,
            Field(description='Optional AncilliaryOffCycleElectricPower value; maps to Ironbug IB_AirLoopHVACUnitarySystem field AncilliaryOffCycleElectricPower.'),
        ] = None,
        heat_pump_time_constant: Annotated[
            str | float | int | bool | None,
            Field(description='Optional HeatPumpTimeConstant value; maps to Ironbug IB_AirLoopHVACUnitarySystem field HeatPumpTimeConstant.'),
        ] = None,
        heat_pump_fan_delay_time: Annotated[
            str | float | int | bool | None,
            Field(description='Optional HeatPumpFanDelayTime value; maps to Ironbug IB_AirLoopHVACUnitarySystem field HeatPumpFanDelayTime.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_AirLoopHVACUnitarySystem field Name.'),
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
        controlling_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional target for Ironbug component Parameter 'ControllingZone' "
                    "on IB_AirLoopHVACUnitarySystem."
                )
            ),
        ] = None,
        heating_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional target for Ironbug component Parameter 'HeatingCoil' "
                    "on IB_AirLoopHVACUnitarySystem."
                )
            ),
        ] = None,
        cooling_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional target for Ironbug component Parameter 'CoolingCoil' "
                    "on IB_AirLoopHVACUnitarySystem."
                )
            ),
        ] = None,
        fan_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional target for Ironbug component Parameter 'Fan' "
                    "on IB_AirLoopHVACUnitarySystem."
                )
            ),
        ] = None,
        supplemental_heating_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional target for Ironbug component Parameter 'SupplementalHeatingCoil' "
                    "on IB_AirLoopHVACUnitarySystem."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_AirLoopHVACUnitarySystem as a reviewed Ironbug ZoneEquipments authoring object."""

        child_targets = [
            cooling_coil_target,
            heating_coil_target,
            fan_target,
            supplemental_heating_coil_target,
            controlling_zone_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if heat_pump_time_constant is not None:
            source_fields['HeatPumpTimeConstant'] = heat_pump_time_constant
        if heat_pump_fan_delay_time is not None:
            source_fields['HeatPumpFanDelayTime'] = heat_pump_fan_delay_time
        if control_type is not None:
            source_fields['ControlType'] = control_type
        if dehumidification_control_type is not None:
            source_fields['DehumidificationControlType'] = dehumidification_control_type
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if fan_placement is not None:
            source_fields['FanPlacement'] = fan_placement
        if supply_air_fan_operating_mode_schedule_target is not None:
            source_field_targets['SupplyAirFanOperatingModeSchedule'] = supply_air_fan_operating_mode_schedule_target
        if dx_heating_coil_sizing_ratio is not None:
            source_fields['DXHeatingCoilSizingRatio'] = dx_heating_coil_sizing_ratio
        if use_doasdx_cooling_coil is not None:
            source_fields['UseDOASDXCoolingCoil'] = use_doasdx_cooling_coil
        if doasdx_cooling_coil_leaving_minimum_air_temperature is not None:
            source_fields['DOASDXCoolingCoilLeavingMinimumAirTemperature'] = doasdx_cooling_coil_leaving_minimum_air_temperature
        if latent_load_control is not None:
            source_fields['LatentLoadControl'] = latent_load_control
        if supply_air_flow_rate_during_cooling_operation is not None:
            source_fields['SupplyAirFlowRateDuringCoolingOperation'] = supply_air_flow_rate_during_cooling_operation
        if supply_air_flow_rate_per_floor_area_during_cooling_operation is not None:
            source_fields['SupplyAirFlowRatePerFloorAreaDuringCoolingOperation'] = supply_air_flow_rate_per_floor_area_during_cooling_operation
        if fractionof_autosized_design_cooling_supply_air_flow_rate is not None:
            source_fields['FractionofAutosizedDesignCoolingSupplyAirFlowRate'] = fractionof_autosized_design_cooling_supply_air_flow_rate
        if design_supply_air_flow_rate_per_unitof_capacity_during_cooling_operation is not None:
            source_fields['DesignSupplyAirFlowRatePerUnitofCapacityDuringCoolingOperation'] = design_supply_air_flow_rate_per_unitof_capacity_during_cooling_operation
        if supply_air_flow_rate_method_during_cooling_operation is not None:
            source_fields['SupplyAirFlowRateMethodDuringCoolingOperation'] = supply_air_flow_rate_method_during_cooling_operation
        if supply_air_flow_rate_during_heating_operation is not None:
            source_fields['SupplyAirFlowRateDuringHeatingOperation'] = supply_air_flow_rate_during_heating_operation
        if supply_air_flow_rate_per_floor_areaduring_heating_operation is not None:
            source_fields['SupplyAirFlowRatePerFloorAreaduringHeatingOperation'] = supply_air_flow_rate_per_floor_areaduring_heating_operation
        if fractionof_autosized_design_heating_supply_air_flow_rate is not None:
            source_fields['FractionofAutosizedDesignHeatingSupplyAirFlowRate'] = fractionof_autosized_design_heating_supply_air_flow_rate
        if design_supply_air_flow_rate_per_unitof_capacity_during_heating_operation is not None:
            source_fields['DesignSupplyAirFlowRatePerUnitofCapacityDuringHeatingOperation'] = design_supply_air_flow_rate_per_unitof_capacity_during_heating_operation
        if supply_air_flow_rate_method_during_heating_operation is not None:
            source_fields['SupplyAirFlowRateMethodDuringHeatingOperation'] = supply_air_flow_rate_method_during_heating_operation
        if supply_air_flow_rate_when_no_coolingor_heatingis_required is not None:
            source_fields['SupplyAirFlowRateWhenNoCoolingorHeatingisRequired'] = supply_air_flow_rate_when_no_coolingor_heatingis_required
        if supply_air_flow_rate_per_floor_area_when_no_coolingor_heatingis_required is not None:
            source_fields['SupplyAirFlowRatePerFloorAreaWhenNoCoolingorHeatingisRequired'] = supply_air_flow_rate_per_floor_area_when_no_coolingor_heatingis_required
        if fractionof_autosized_design_cooling_supply_air_flow_rate_when_no_coolingor_heatingis_required is not None:
            source_fields['FractionofAutosizedDesignCoolingSupplyAirFlowRateWhenNoCoolingorHeatingisRequired'] = fractionof_autosized_design_cooling_supply_air_flow_rate_when_no_coolingor_heatingis_required
        if fractionof_autosized_design_heating_supply_air_flow_rate_when_no_coolingor_heatingis_required is not None:
            source_fields['FractionofAutosizedDesignHeatingSupplyAirFlowRateWhenNoCoolingorHeatingisRequired'] = fractionof_autosized_design_heating_supply_air_flow_rate_when_no_coolingor_heatingis_required
        if design_supply_air_flow_rate_per_unitof_capacity_during_cooling_operation_when_no_coolingor_heatingis_required is not None:
            source_fields['DesignSupplyAirFlowRatePerUnitofCapacityDuringCoolingOperationWhenNoCoolingorHeatingisRequired'] = design_supply_air_flow_rate_per_unitof_capacity_during_cooling_operation_when_no_coolingor_heatingis_required
        if design_supply_air_flow_rate_per_unitof_capacity_during_heating_operation_when_no_coolingor_heatingis_required is not None:
            source_fields['DesignSupplyAirFlowRatePerUnitofCapacityDuringHeatingOperationWhenNoCoolingorHeatingisRequired'] = design_supply_air_flow_rate_per_unitof_capacity_during_heating_operation_when_no_coolingor_heatingis_required
        if no_load_supply_air_flow_rate_control_set_to_low_speed is not None:
            source_fields['NoLoadSupplyAirFlowRateControlSetToLowSpeed'] = no_load_supply_air_flow_rate_control_set_to_low_speed
        if supply_air_flow_rate_method_when_no_coolingor_heatingis_required is not None:
            source_fields['SupplyAirFlowRateMethodWhenNoCoolingorHeatingisRequired'] = supply_air_flow_rate_method_when_no_coolingor_heatingis_required
        if maximum_supply_air_temperature is not None:
            source_fields['MaximumSupplyAirTemperature'] = maximum_supply_air_temperature
        if maximum_outdoor_dry_bulb_temperaturefor_supplemental_heater_operation is not None:
            source_fields['MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation'] = maximum_outdoor_dry_bulb_temperaturefor_supplemental_heater_operation
        if maximum_cycling_rate is not None:
            source_fields['MaximumCyclingRate'] = maximum_cycling_rate
        if fractionof_on_cycle_power_use is not None:
            source_fields['FractionofOnCyclePowerUse'] = fractionof_on_cycle_power_use
        if ancilliary_on_cycle_electric_power is not None:
            source_fields['AncilliaryOnCycleElectricPower'] = ancilliary_on_cycle_electric_power
        if ancilliary_off_cycle_electric_power is not None:
            source_fields['AncilliaryOffCycleElectricPower'] = ancilliary_off_cycle_electric_power
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_AirLoopHVACUnitarySystem',
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
