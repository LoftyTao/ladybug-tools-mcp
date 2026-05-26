'MCP tool for detailed_hvac_coil_heating_dx_single_speed.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_heating_dx_single_speed tool.'

    @mcp.tool(
        name='coil_heating_dx_single_speed',
        description=(
            'Create IB_CoilHeatingDXSingleSpeed, an Ironbug single-speed direct '
            'expansion (DX) heat-pump heating coil component that maps '
            'downstream to EnergyPlus/OpenStudio Coil:Heating:DX:SingleSpeed. '
            'Use the returned target as the heating-coil child for PTHP or '
            'unitary air-loop DetailedHVAC assemblies. This is not a '
            'plant-loop coil, air-terminal reheat coil, PTAC heating coil, or '
            'Honeybee Energy HVAC template. Returns target, summary_view, '
            'persistence_receipt, and report for downstream DetailedHVAC '
            'assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'heating', 'dx', 'heat-pump', 'air-loop', 'zone-equipment', 'pthp', 'unitary', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_heating_dx_single_speed(
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
            Field(description="Stable identifier for the new IB_CoilHeatingDXSingleSpeed object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        rated_total_heating_capacity: Annotated[
            float | str | None,
            Field(description='Optional RatedTotalHeatingCapacity in W, or an EnergyPlus autosizable literal accepted by Ironbug.'),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for AvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Schedule values above zero make the DX heating coil available.'),
        ] = None,
        rated_cop: Annotated[
            float | None,
            Field(description='Optional RatedCOP value in W/W for IB_CoilHeatingDXSingleSpeed.'),
        ] = None,
        rated_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional RatedAirFlowRate in m3/s, or an EnergyPlus autosizable literal accepted by Ironbug.'),
        ] = None,
        rated_supply_fan_power_per_volume_flow_rate2017: Annotated[
            float | None,
            Field(description='Optional RatedSupplyFanPowerPerVolumeFlowRate2017 value; maps to Ironbug IB_CoilHeatingDXSingleSpeed field RatedSupplyFanPowerPerVolumeFlowRate2017.'),
        ] = None,
        rated_supply_fan_power_per_volume_flow_rate2023: Annotated[
            float | None,
            Field(description='Optional RatedSupplyFanPowerPerVolumeFlowRate2023 value; maps to Ironbug IB_CoilHeatingDXSingleSpeed field RatedSupplyFanPowerPerVolumeFlowRate2023.'),
        ] = None,
        minimum_outdoor_dry_bulb_temperaturefor_compressor_operation: Annotated[
            float | None,
            Field(description='Optional MinimumOutdoorDryBulbTemperatureforCompressorOperation value; maps to Ironbug IB_CoilHeatingDXSingleSpeed field MinimumOutdoorDryBulbTemperatureforCompressorOperation.'),
        ] = None,
        maximum_outdoor_dry_bulb_temperaturefor_defrost_operation: Annotated[
            float | None,
            Field(description='Optional MaximumOutdoorDryBulbTemperatureforDefrostOperation value; maps to Ironbug IB_CoilHeatingDXSingleSpeed field MaximumOutdoorDryBulbTemperatureforDefrostOperation.'),
        ] = None,
        crankcase_heater_capacity: Annotated[
            float | None,
            Field(description='Optional CrankcaseHeaterCapacity value; maps to Ironbug IB_CoilHeatingDXSingleSpeed field CrankcaseHeaterCapacity.'),
        ] = None,
        crankcase_heater_capacity_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional same-model IB_Curve target for CrankcaseHeaterCapacityFunctionofTemperatureCurve; pass a target dict from a compatible detailed_hvac curve tool or a same-model identifier.'),
        ] = None,
        maximum_outdoor_dry_bulb_temperaturefor_crankcase_heater_operation: Annotated[
            float | None,
            Field(description='Optional MaximumOutdoorDryBulbTemperatureforCrankcaseHeaterOperation value; maps to Ironbug IB_CoilHeatingDXSingleSpeed field MaximumOutdoorDryBulbTemperatureforCrankcaseHeaterOperation.'),
        ] = None,
        defrost_strategy: Annotated[
            str | None,
            Field(description="Optional DefrostStrategy value, typically 'Resistive' or 'ReverseCycle' where supported by the EnergyPlus/OpenStudio object."),
        ] = None,
        defrost_control: Annotated[
            str | None,
            Field(description="Optional DefrostControl value, typically 'Timed' or 'OnDemand' where supported by the EnergyPlus/OpenStudio object."),
        ] = None,
        defrost_time_period_fraction: Annotated[
            float | None,
            Field(description='Optional DefrostTimePeriodFraction value; maps to Ironbug IB_CoilHeatingDXSingleSpeed field DefrostTimePeriodFraction.'),
        ] = None,
        resistive_defrost_heater_capacity: Annotated[
            float | str | None,
            Field(description='Optional ResistiveDefrostHeaterCapacity in W, or an EnergyPlus autosizable literal accepted by Ironbug.'),
        ] = None,
        total_heating_capacity_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional same-model IB_Curve target for TotalHeatingCapacityFunctionofTemperatureCurve; pass a target dict from a compatible detailed_hvac curve tool or a same-model identifier, not bare curve coefficients.'),
        ] = None,
        total_heating_capacity_functionof_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional same-model IB_Curve target for TotalHeatingCapacityFunctionofFlowFractionCurve; pass a target dict from a compatible detailed_hvac curve tool or a same-model identifier, not bare curve coefficients.'),
        ] = None,
        energy_input_ratio_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional same-model IB_Curve target for EnergyInputRatioFunctionofTemperatureCurve; pass a target dict from a compatible detailed_hvac curve tool or a same-model identifier, not bare curve coefficients.'),
        ] = None,
        energy_input_ratio_functionof_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional same-model IB_Curve target for EnergyInputRatioFunctionofFlowFractionCurve; pass a target dict from a compatible detailed_hvac curve tool or a same-model identifier, not bare curve coefficients.'),
        ] = None,
        part_load_fraction_correlation_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional same-model IB_Curve target for PartLoadFractionCorrelationCurve; pass a target dict from a compatible detailed_hvac curve tool or a same-model identifier, not bare curve coefficients.'),
        ] = None,
        defrost_energy_input_ratio_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional same-model IB_Curve target for DefrostEnergyInputRatioFunctionofTemperatureCurve; pass a target dict from a compatible detailed_hvac curve tool or a same-model identifier.'),
        ] = None,
        rated_supply_fan_power_per_volume_flow_rate: Annotated[
            str | float | int | bool | None,
            Field(description='Optional RatedSupplyFanPowerPerVolumeFlowRate in W/(m3/s), or an EnergyPlus autosizable/default literal accepted by Ironbug.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilHeatingDXSingleSpeed field Name.'),
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
        """Create IB_CoilHeatingDXSingleSpeed as a reviewed DX heating coil."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if rated_supply_fan_power_per_volume_flow_rate is not None:
            source_fields['RatedSupplyFanPowerPerVolumeFlowRate'] = rated_supply_fan_power_per_volume_flow_rate
        if rated_total_heating_capacity is not None:
            source_fields['RatedTotalHeatingCapacity'] = rated_total_heating_capacity
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if rated_cop is not None:
            source_fields['RatedCOP'] = rated_cop
        if rated_air_flow_rate is not None:
            source_fields['RatedAirFlowRate'] = rated_air_flow_rate
        if rated_supply_fan_power_per_volume_flow_rate2017 is not None:
            source_fields['RatedSupplyFanPowerPerVolumeFlowRate2017'] = rated_supply_fan_power_per_volume_flow_rate2017
        if rated_supply_fan_power_per_volume_flow_rate2023 is not None:
            source_fields['RatedSupplyFanPowerPerVolumeFlowRate2023'] = rated_supply_fan_power_per_volume_flow_rate2023
        if minimum_outdoor_dry_bulb_temperaturefor_compressor_operation is not None:
            source_fields['MinimumOutdoorDryBulbTemperatureforCompressorOperation'] = minimum_outdoor_dry_bulb_temperaturefor_compressor_operation
        if maximum_outdoor_dry_bulb_temperaturefor_defrost_operation is not None:
            source_fields['MaximumOutdoorDryBulbTemperatureforDefrostOperation'] = maximum_outdoor_dry_bulb_temperaturefor_defrost_operation
        if crankcase_heater_capacity is not None:
            source_fields['CrankcaseHeaterCapacity'] = crankcase_heater_capacity
        if crankcase_heater_capacity_functionof_temperature_curve_target is not None:
            source_field_targets['CrankcaseHeaterCapacityFunctionofTemperatureCurve'] = crankcase_heater_capacity_functionof_temperature_curve_target
        if maximum_outdoor_dry_bulb_temperaturefor_crankcase_heater_operation is not None:
            source_fields['MaximumOutdoorDryBulbTemperatureforCrankcaseHeaterOperation'] = maximum_outdoor_dry_bulb_temperaturefor_crankcase_heater_operation
        if defrost_strategy is not None:
            source_fields['DefrostStrategy'] = defrost_strategy
        if defrost_control is not None:
            source_fields['DefrostControl'] = defrost_control
        if defrost_time_period_fraction is not None:
            source_fields['DefrostTimePeriodFraction'] = defrost_time_period_fraction
        if resistive_defrost_heater_capacity is not None:
            source_fields['ResistiveDefrostHeaterCapacity'] = resistive_defrost_heater_capacity
        if total_heating_capacity_functionof_temperature_curve_target is not None:
            source_field_targets['TotalHeatingCapacityFunctionofTemperatureCurve'] = total_heating_capacity_functionof_temperature_curve_target
        if total_heating_capacity_functionof_flow_fraction_curve_target is not None:
            source_field_targets['TotalHeatingCapacityFunctionofFlowFractionCurve'] = total_heating_capacity_functionof_flow_fraction_curve_target
        if energy_input_ratio_functionof_temperature_curve_target is not None:
            source_field_targets['EnergyInputRatioFunctionofTemperatureCurve'] = energy_input_ratio_functionof_temperature_curve_target
        if energy_input_ratio_functionof_flow_fraction_curve_target is not None:
            source_field_targets['EnergyInputRatioFunctionofFlowFractionCurve'] = energy_input_ratio_functionof_flow_fraction_curve_target
        if part_load_fraction_correlation_curve_target is not None:
            source_field_targets['PartLoadFractionCorrelationCurve'] = part_load_fraction_correlation_curve_target
        if defrost_energy_input_ratio_functionof_temperature_curve_target is not None:
            source_field_targets['DefrostEnergyInputRatioFunctionofTemperatureCurve'] = defrost_energy_input_ratio_functionof_temperature_curve_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilHeatingDXSingleSpeed',
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
