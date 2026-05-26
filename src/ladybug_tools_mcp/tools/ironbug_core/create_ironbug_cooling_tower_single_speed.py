'MCP tool for detailed_hvac_cooling_tower_single_speed.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_cooling_tower_single_speed tool.'

    @mcp.tool(
        name='cooling_tower_single_speed',
        description=(
            'Create IB_CoolingTowerSingleSpeed, an OpenStudio/EnergyPlus CoolingTower:SingleSpeed condenser-water heat-rejection object for an Ironbug plant loop. Use it for single-speed cooling tower equipment on plant-loop heat-rejection branches; use coil, air-loop, or zone-equipment tools for those separate HVAC roles. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
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
            'single-speed',
            'fan',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_cooling_tower_single_speed(
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
            Field(description="Stable identifier for the new IB_CoolingTowerSingleSpeed object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        nominal_capacity: Annotated[
            float | None,
            Field(
                description="Nominal heat rejection capacity for the single-speed cooling tower. Maps to Ironbug field NominalCapacity."
            ),
        ] = None,
        design_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Design condenser-water flow rate through the tower; autosize strings are accepted where Ironbug/OpenStudio allows them. Maps to Ironbug field DesignWaterFlowRate.'),
        ] = None,
        design_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Design fan air flow rate for single-speed operation. Maps to Ironbug field DesignAirFlowRate.'),
        ] = None,
        fan_powerat_design_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Fan power at the design air flow rate. Maps to Ironbug field FanPoweratDesignAirFlowRate.'),
        ] = None,
        u_factor_times_area_valueat_design_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Tower heat-transfer UA at design fan air flow. Maps to Ironbug field UFactorTimesAreaValueatDesignAirFlowRate.'),
        ] = None,
        air_flow_ratein_free_convection_regime: Annotated[
            float | str | None,
            Field(description='Air flow rate used when the cooling tower operates in free-convection mode. Maps to Ironbug field AirFlowRateinFreeConvectionRegime.'),
        ] = None,
        u_factor_times_area_valueat_free_convection_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Tower heat-transfer UA at the free-convection air flow rate. Maps to Ironbug field UFactorTimesAreaValueatFreeConvectionAirFlowRate.'),
        ] = None,
        performance_input_method: Annotated[
            str | None,
            Field(description='Performance input method used by the cooling tower object. Maps to Ironbug field PerformanceInputMethod.'),
        ] = None,
        free_convection_capacity: Annotated[
            float | None,
            Field(description='Heat-rejection capacity available in free-convection operation. Maps to Ironbug field FreeConvectionCapacity.'),
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
        capacity_control: Annotated[
            str | None,
            Field(description='Capacity control method for the single-speed tower. Maps to Ironbug field CapacityControl.'),
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
        free_convection_air_flow_rate_sizing_factor: Annotated[
            float | None,
            Field(description='Sizing factor for free-convection air flow rate. Maps to Ironbug field FreeConvectionAirFlowRateSizingFactor.'),
        ] = None,
        free_convection_u_factor_times_area_value_sizing_factor: Annotated[
            float | None,
            Field(description='Sizing factor for free-convection heat-transfer UA. Maps to Ironbug field FreeConvectionUFactorTimesAreaValueSizingFactor.'),
        ] = None,
        heat_rejection_capacity_and_nominal_capacity_sizing_ratio: Annotated[
            float | None,
            Field(description='Ratio between heat-rejection capacity and nominal capacity for sizing. Maps to Ironbug field HeatRejectionCapacityAndNominalCapacitySizingRatio.'),
        ] = None,
        free_convection_nominal_capacity_sizing_factor: Annotated[
            float | None,
            Field(description='Sizing factor for free-convection nominal capacity. Maps to Ironbug field FreeConvectionNominalCapacitySizingFactor.'),
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
        """Create IB_CoolingTowerSingleSpeed as a reviewed cooling-tower plant-loop object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if nominal_capacity is not None:
            source_fields['NominalCapacity'] = nominal_capacity
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if design_water_flow_rate is not None:
            source_fields['DesignWaterFlowRate'] = design_water_flow_rate
        if design_air_flow_rate is not None:
            source_fields['DesignAirFlowRate'] = design_air_flow_rate
        if fan_powerat_design_air_flow_rate is not None:
            source_fields['FanPoweratDesignAirFlowRate'] = fan_powerat_design_air_flow_rate
        if u_factor_times_area_valueat_design_air_flow_rate is not None:
            source_fields['UFactorTimesAreaValueatDesignAirFlowRate'] = u_factor_times_area_valueat_design_air_flow_rate
        if air_flow_ratein_free_convection_regime is not None:
            source_fields['AirFlowRateinFreeConvectionRegime'] = air_flow_ratein_free_convection_regime
        if u_factor_times_area_valueat_free_convection_air_flow_rate is not None:
            source_fields['UFactorTimesAreaValueatFreeConvectionAirFlowRate'] = u_factor_times_area_valueat_free_convection_air_flow_rate
        if performance_input_method is not None:
            source_fields['PerformanceInputMethod'] = performance_input_method
        if free_convection_capacity is not None:
            source_fields['FreeConvectionCapacity'] = free_convection_capacity
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
        if capacity_control is not None:
            source_fields['CapacityControl'] = capacity_control
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
        if free_convection_air_flow_rate_sizing_factor is not None:
            source_fields['FreeConvectionAirFlowRateSizingFactor'] = free_convection_air_flow_rate_sizing_factor
        if free_convection_u_factor_times_area_value_sizing_factor is not None:
            source_fields['FreeConvectionUFactorTimesAreaValueSizingFactor'] = free_convection_u_factor_times_area_value_sizing_factor
        if heat_rejection_capacity_and_nominal_capacity_sizing_ratio is not None:
            source_fields['HeatRejectionCapacityAndNominalCapacitySizingRatio'] = heat_rejection_capacity_and_nominal_capacity_sizing_ratio
        if free_convection_nominal_capacity_sizing_factor is not None:
            source_fields['FreeConvectionNominalCapacitySizingFactor'] = free_convection_nominal_capacity_sizing_factor
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
            source_class='IB_CoolingTowerSingleSpeed',
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
