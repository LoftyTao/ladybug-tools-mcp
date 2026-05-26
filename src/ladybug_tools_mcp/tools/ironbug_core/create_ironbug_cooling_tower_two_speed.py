'MCP tool for detailed_hvac_cooling_tower_two_speed.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_cooling_tower_two_speed tool.'

    @mcp.tool(
        name='cooling_tower_two_speed',
        description=(
            'Create IB_CoolingTowerTwoSpeed, an OpenStudio/EnergyPlus CoolingTower:TwoSpeed condenser-water heat-rejection object for an Ironbug plant loop. Use it for cooling tower equipment with high-speed and low-speed fan operation on plant-loop heat-rejection branches; use coil, air-loop, or zone-equipment tools for those separate HVAC roles. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'cooling-tower',
            'heat-rejection',
            'condenser-water',
            'plant-loop',
            'two-speed',
            'fan',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_cooling_tower_two_speed(
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
            Field(description="Stable identifier for the new IB_CoolingTowerTwoSpeed object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        high_speed_nominal_capacity: Annotated[
            float | None,
            Field(
                description="Nominal heat-rejection capacity at high fan speed. Maps to Ironbug field HighSpeedNominalCapacity."
            ),
        ] = None,
        low_speed_nominal_capacity: Annotated[
            float | str | None,
            Field(
                description="Nominal heat-rejection capacity at low fan speed; autosize strings are accepted where Ironbug/OpenStudio allows them. Maps to Ironbug field LowSpeedNominalCapacity."
            ),
        ] = None,
        design_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Design condenser-water flow rate through the two-speed tower. Maps to Ironbug field DesignWaterFlowRate.'),
        ] = None,
        high_fan_speed_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Air flow rate when the tower fan runs at high speed. Maps to Ironbug field HighFanSpeedAirFlowRate.'),
        ] = None,
        high_fan_speed_fan_power: Annotated[
            float | str | None,
            Field(description='Fan power when the tower fan runs at high speed. Maps to Ironbug field HighFanSpeedFanPower.'),
        ] = None,
        high_fan_speed_u_factor_times_area_value: Annotated[
            float | str | None,
            Field(description='Tower heat-transfer UA at high fan speed. Maps to Ironbug field HighFanSpeedUFactorTimesAreaValue.'),
        ] = None,
        low_fan_speed_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Air flow rate when the tower fan runs at low speed. Maps to Ironbug field LowFanSpeedAirFlowRate.'),
        ] = None,
        low_fan_speed_air_flow_rate_sizing_factor: Annotated[
            float | None,
            Field(description='Sizing factor for low-speed air flow rate. Maps to Ironbug field LowFanSpeedAirFlowRateSizingFactor.'),
        ] = None,
        low_fan_speed_fan_power: Annotated[
            float | str | None,
            Field(description='Fan power when the tower fan runs at low speed. Maps to Ironbug field LowFanSpeedFanPower.'),
        ] = None,
        low_fan_speed_fan_power_sizing_factor: Annotated[
            float | None,
            Field(description='Sizing factor for low-speed fan power. Maps to Ironbug field LowFanSpeedFanPowerSizingFactor.'),
        ] = None,
        low_fan_speed_u_factor_times_area_value: Annotated[
            float | str | None,
            Field(description='Tower heat-transfer UA at low fan speed. Maps to Ironbug field LowFanSpeedUFactorTimesAreaValue.'),
        ] = None,
        low_fan_speed_u_factor_times_area_sizing_factor: Annotated[
            float | None,
            Field(description='Sizing factor for low-speed heat-transfer UA. Maps to Ironbug field LowFanSpeedUFactorTimesAreaSizingFactor.'),
        ] = None,
        free_convection_regime_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Air flow rate used when the tower operates in free-convection mode. Maps to Ironbug field FreeConvectionRegimeAirFlowRate.'),
        ] = None,
        free_convection_regime_air_flow_rate_sizing_factor: Annotated[
            float | None,
            Field(description='Sizing factor for free-convection air flow rate. Maps to Ironbug field FreeConvectionRegimeAirFlowRateSizingFactor.'),
        ] = None,
        free_convection_regime_u_factor_times_area_value: Annotated[
            float | str | None,
            Field(description='Tower heat-transfer UA in free-convection operation. Maps to Ironbug field FreeConvectionRegimeUFactorTimesAreaValue.'),
        ] = None,
        free_convection_u_factor_times_area_value_sizing_factor: Annotated[
            float | None,
            Field(description='Sizing factor for free-convection heat-transfer UA. Maps to Ironbug field FreeConvectionUFactorTimesAreaValueSizingFactor.'),
        ] = None,
        performance_input_method: Annotated[
            str | None,
            Field(description='Performance input method used by the two-speed cooling tower object. Maps to Ironbug field PerformanceInputMethod.'),
        ] = None,
        heat_rejection_capacityand_nominal_capacity_sizing_ratio: Annotated[
            float | None,
            Field(description='Ratio between heat-rejection capacity and nominal capacity for sizing. Maps to Ironbug field HeatRejectionCapacityandNominalCapacitySizingRatio.'),
        ] = None,
        low_speed_nominal_capacity_sizing_factor: Annotated[
            float | None,
            Field(description='Sizing factor for low-speed nominal capacity. Maps to Ironbug field LowSpeedNominalCapacitySizingFactor.'),
        ] = None,
        free_convection_nominal_capacity: Annotated[
            float | str | None,
            Field(description='Nominal heat-rejection capacity in free-convection operation. Maps to Ironbug field FreeConvectionNominalCapacity.'),
        ] = None,
        free_convection_nominal_capacity_sizing_factor: Annotated[
            float | None,
            Field(description='Sizing factor for free-convection nominal capacity. Maps to Ironbug field FreeConvectionNominalCapacitySizingFactor.'),
        ] = None,
        basin_heater_capacity: Annotated[
            float | None,
            Field(description='Basin heater capacity for freeze protection. Maps to Ironbug field BasinHeaterCapacity.'),
        ] = None,
        basin_heater_setpoint_temperature: Annotated[
            float | None,
            Field(description='Water temperature setpoint for basin heater operation. Maps to Ironbug field BasinHeaterSetpointTemperature.'),
        ] = None,
        basin_heater_operating_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='IB_Schedule target dict or same-model schedule identifier for basin heater availability. Maps to Ironbug field BasinHeaterOperatingSchedule.'),
        ] = None,
        evaporation_loss_mode: Annotated[
            str | None,
            Field(description='Evaporation loss calculation mode for cooling tower water use. Maps to Ironbug field EvaporationLossMode.'),
        ] = None,
        evaporation_loss_factor: Annotated[
            float | None,
            Field(description='Evaporation loss factor used with the selected evaporation loss mode. Maps to Ironbug field EvaporationLossFactor.'),
        ] = None,
        drift_loss_percent: Annotated[
            float | None,
            Field(description='Percent of condenser-water flow lost as tower drift. Maps to Ironbug field DriftLossPercent.'),
        ] = None,
        blowdown_calculation_mode: Annotated[
            str | None,
            Field(description='Blowdown water-use calculation mode. Maps to Ironbug field BlowdownCalculationMode.'),
        ] = None,
        blowdown_concentration_ratio: Annotated[
            float | None,
            Field(description='Concentration ratio used for blowdown calculation. Maps to Ironbug field BlowdownConcentrationRatio.'),
        ] = None,
        blowdown_makeup_water_usage_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='IB_Schedule target dict or same-model schedule identifier for blowdown makeup-water use. Maps to Ironbug field BlowdownMakeupWaterUsageSchedule.'),
        ] = None,
        numberof_cells: Annotated[
            int | None,
            Field(description='Number of tower cells represented by this object. Maps to Ironbug field NumberofCells.'),
        ] = None,
        cell_control: Annotated[
            str | None,
            Field(description='Control strategy for distributing load across tower cells. Maps to Ironbug field CellControl.'),
        ] = None,
        cell_minimum_water_flow_rate_fraction: Annotated[
            float | None,
            Field(description='Minimum water flow fraction allowed for each active tower cell. Maps to Ironbug field CellMinimumWaterFlowRateFraction.'),
        ] = None,
        cell_maximum_water_flow_rate_fraction: Annotated[
            float | None,
            Field(description='Maximum water flow fraction allowed for each active tower cell. Maps to Ironbug field CellMaximumWaterFlowRateFraction.'),
        ] = None,
        sizing_factor: Annotated[
            float | None,
            Field(description='Sizing multiplier applied to autosized cooling tower values. Maps to Ironbug field SizingFactor.'),
        ] = None,
        design_inlet_air_dry_bulb_temperature: Annotated[
            float | None,
            Field(description='Design inlet air dry-bulb temperature at the cooling tower. Maps to Ironbug field DesignInletAirDryBulbTemperature.'),
        ] = None,
        design_inlet_air_wet_bulb_temperature: Annotated[
            float | None,
            Field(description='Design inlet air wet-bulb temperature at the cooling tower. Maps to Ironbug field DesignInletAirWetBulbTemperature.'),
        ] = None,
        design_approach_temperature: Annotated[
            float | str | None,
            Field(description='Design approach temperature between leaving water and entering wet-bulb conditions. Maps to Ironbug field DesignApproachTemperature.'),
        ] = None,
        design_range_temperature: Annotated[
            float | str | None,
            Field(description='Design condenser-water range across the tower. Maps to Ironbug field DesignRangeTemperature.'),
        ] = None,
        end_use_subcategory: Annotated[
            str | None,
            Field(description='EnergyPlus end-use subcategory label for tower reporting. Maps to Ironbug field EndUseSubcategory.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Explicit OpenStudio object name for this cooling tower. Maps to Ironbug field Name.'),
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
        """Create IB_CoolingTowerTwoSpeed as a reviewed cooling-tower plant-loop object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if high_speed_nominal_capacity is not None:
            source_fields['HighSpeedNominalCapacity'] = high_speed_nominal_capacity
        if low_speed_nominal_capacity is not None:
            source_fields['LowSpeedNominalCapacity'] = low_speed_nominal_capacity
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if design_water_flow_rate is not None:
            source_fields['DesignWaterFlowRate'] = design_water_flow_rate
        if high_fan_speed_air_flow_rate is not None:
            source_fields['HighFanSpeedAirFlowRate'] = high_fan_speed_air_flow_rate
        if high_fan_speed_fan_power is not None:
            source_fields['HighFanSpeedFanPower'] = high_fan_speed_fan_power
        if high_fan_speed_u_factor_times_area_value is not None:
            source_fields['HighFanSpeedUFactorTimesAreaValue'] = high_fan_speed_u_factor_times_area_value
        if low_fan_speed_air_flow_rate is not None:
            source_fields['LowFanSpeedAirFlowRate'] = low_fan_speed_air_flow_rate
        if low_fan_speed_air_flow_rate_sizing_factor is not None:
            source_fields['LowFanSpeedAirFlowRateSizingFactor'] = low_fan_speed_air_flow_rate_sizing_factor
        if low_fan_speed_fan_power is not None:
            source_fields['LowFanSpeedFanPower'] = low_fan_speed_fan_power
        if low_fan_speed_fan_power_sizing_factor is not None:
            source_fields['LowFanSpeedFanPowerSizingFactor'] = low_fan_speed_fan_power_sizing_factor
        if low_fan_speed_u_factor_times_area_value is not None:
            source_fields['LowFanSpeedUFactorTimesAreaValue'] = low_fan_speed_u_factor_times_area_value
        if low_fan_speed_u_factor_times_area_sizing_factor is not None:
            source_fields['LowFanSpeedUFactorTimesAreaSizingFactor'] = low_fan_speed_u_factor_times_area_sizing_factor
        if free_convection_regime_air_flow_rate is not None:
            source_fields['FreeConvectionRegimeAirFlowRate'] = free_convection_regime_air_flow_rate
        if free_convection_regime_air_flow_rate_sizing_factor is not None:
            source_fields['FreeConvectionRegimeAirFlowRateSizingFactor'] = free_convection_regime_air_flow_rate_sizing_factor
        if free_convection_regime_u_factor_times_area_value is not None:
            source_fields['FreeConvectionRegimeUFactorTimesAreaValue'] = free_convection_regime_u_factor_times_area_value
        if free_convection_u_factor_times_area_value_sizing_factor is not None:
            source_fields['FreeConvectionUFactorTimesAreaValueSizingFactor'] = free_convection_u_factor_times_area_value_sizing_factor
        if performance_input_method is not None:
            source_fields['PerformanceInputMethod'] = performance_input_method
        if heat_rejection_capacityand_nominal_capacity_sizing_ratio is not None:
            source_fields['HeatRejectionCapacityandNominalCapacitySizingRatio'] = heat_rejection_capacityand_nominal_capacity_sizing_ratio
        if low_speed_nominal_capacity_sizing_factor is not None:
            source_fields['LowSpeedNominalCapacitySizingFactor'] = low_speed_nominal_capacity_sizing_factor
        if free_convection_nominal_capacity is not None:
            source_fields['FreeConvectionNominalCapacity'] = free_convection_nominal_capacity
        if free_convection_nominal_capacity_sizing_factor is not None:
            source_fields['FreeConvectionNominalCapacitySizingFactor'] = free_convection_nominal_capacity_sizing_factor
        if basin_heater_capacity is not None:
            source_fields['BasinHeaterCapacity'] = basin_heater_capacity
        if basin_heater_setpoint_temperature is not None:
            source_fields['BasinHeaterSetpointTemperature'] = basin_heater_setpoint_temperature
        if basin_heater_operating_schedule_target is not None:
            source_field_targets['BasinHeaterOperatingSchedule'] = basin_heater_operating_schedule_target
        if evaporation_loss_mode is not None:
            source_fields['EvaporationLossMode'] = evaporation_loss_mode
        if evaporation_loss_factor is not None:
            source_fields['EvaporationLossFactor'] = evaporation_loss_factor
        if drift_loss_percent is not None:
            source_fields['DriftLossPercent'] = drift_loss_percent
        if blowdown_calculation_mode is not None:
            source_fields['BlowdownCalculationMode'] = blowdown_calculation_mode
        if blowdown_concentration_ratio is not None:
            source_fields['BlowdownConcentrationRatio'] = blowdown_concentration_ratio
        if blowdown_makeup_water_usage_schedule_target is not None:
            source_field_targets['BlowdownMakeupWaterUsageSchedule'] = blowdown_makeup_water_usage_schedule_target
        if numberof_cells is not None:
            source_fields['NumberofCells'] = numberof_cells
        if cell_control is not None:
            source_fields['CellControl'] = cell_control
        if cell_minimum_water_flow_rate_fraction is not None:
            source_fields['CellMinimumWaterFlowRateFraction'] = cell_minimum_water_flow_rate_fraction
        if cell_maximum_water_flow_rate_fraction is not None:
            source_fields['CellMaximumWaterFlowRateFraction'] = cell_maximum_water_flow_rate_fraction
        if sizing_factor is not None:
            source_fields['SizingFactor'] = sizing_factor
        if design_inlet_air_dry_bulb_temperature is not None:
            source_fields['DesignInletAirDryBulbTemperature'] = design_inlet_air_dry_bulb_temperature
        if design_inlet_air_wet_bulb_temperature is not None:
            source_fields['DesignInletAirWetBulbTemperature'] = design_inlet_air_wet_bulb_temperature
        if design_approach_temperature is not None:
            source_fields['DesignApproachTemperature'] = design_approach_temperature
        if design_range_temperature is not None:
            source_fields['DesignRangeTemperature'] = design_range_temperature
        if end_use_subcategory is not None:
            source_fields['EndUseSubcategory'] = end_use_subcategory
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoolingTowerTwoSpeed',
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
