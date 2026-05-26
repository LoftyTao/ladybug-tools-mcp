'MCP tool for detailed_hvac_evaporative_fluid_cooler_single_speed.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_evaporative_fluid_cooler_single_speed tool.'

    @mcp.tool(
        name='evaporative_fluid_cooler_single_speed',
        description=(
            'Create IB_EvaporativeFluidCoolerSingleSpeed, an EnergyPlus/OpenStudio single-speed evaporative fluid cooler for condenser-water plant-loop heat rejection. Use it for counterflow fluid cooler performance defined by UA/design-water-flow, standard design capacity, or user-specified design capacity, with fan power, spray water, evaporation/drift/blowdown water use, and capacity control. This is not an air-loop evaporative cooler, chiller, or cooling tower. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'plant-loop', 'plant-component', 'condenser-water', 'heat-rejection', 'fluid-cooler', 'evaporative-cooling', 'single-speed', 'water-use', 'author'},
        timeout=20,
    )
    def create_ironbug_evaporative_fluid_cooler_single_speed(
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
            Field(description="Stable identifier for the new IB_EvaporativeFluidCoolerSingleSpeed object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        design_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Design air flow rate induced by the single-speed fluid cooler fan in m3/s, or autosize when supported.'),
        ] = None,
        fan_powerat_design_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Fan power in W at the design air flow rate.'),
        ] = None,
        design_spray_water_flow_rate: Annotated[
            float | None,
            Field(description='Design spray water flow rate through the evaporative fluid cooler in m3/s.'),
        ] = None,
        performance_input_method: Annotated[
            str | None,
            Field(description='Fluid cooler performance method: UFactorTimesAreaAndDesignWaterFlowRate, StandardDesignCapacity, or UserSpecifiedDesignCapacity.'),
        ] = None,
        standard_design_capacity: Annotated[
            float | None,
            Field(description='Standard heat rejection capacity in W for the StandardDesignCapacity performance method.'),
        ] = None,
        ufactor_times_area_valueat_design_air_flow_rate: Annotated[
            float | str | None,
            Field(description='UA value in W/K at design air and water flow for the UFactorTimesAreaAndDesignWaterFlowRate method.'),
        ] = None,
        design_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Condenser loop design water flow rate through the fluid cooler in m3/s, or autosize when supported.'),
        ] = None,
        user_specified_design_capacity: Annotated[
            float | None,
            Field(description='User-specified heat rejection capacity in W for non-standard design conditions.'),
        ] = None,
        design_entering_water_temperature: Annotated[
            float | None,
            Field(description='Design entering water temperature in degC for UserSpecifiedDesignCapacity.'),
        ] = None,
        design_entering_air_temperature: Annotated[
            float | None,
            Field(description='Design entering air drybulb temperature in degC for UserSpecifiedDesignCapacity.'),
        ] = None,
        design_entering_air_wetbulb_temperature: Annotated[
            float | None,
            Field(description='Design entering air wetbulb temperature in degC for UserSpecifiedDesignCapacity.'),
        ] = None,
        capacity_control: Annotated[
            str | None,
            Field(description='Single-speed capacity control mode, typically FanCycling or FluidBypass.'),
        ] = None,
        sizing_factor: Annotated[
            float | None,
            Field(description='Sizing multiplier applied to autosized fluid cooler design inputs.'),
        ] = None,
        evaporation_loss_mode: Annotated[
            str | None,
            Field(description='Evaporative water-loss calculation mode, such as LossFactor or SaturatedExit.'),
        ] = None,
        evaporation_loss_factor: Annotated[
            float | None,
            Field(description='Water evaporation loss factor in percent per K when EvaporationLossMode is LossFactor.'),
        ] = None,
        drift_loss_percent: Annotated[
            float | None,
            Field(description='Percent of condenser water flow lost as drift droplets.'),
        ] = None,
        blowdown_calculation_mode: Annotated[
            str | None,
            Field(description='Blowdown calculation mode, such as ConcentrationRatio or ScheduledRate.'),
        ] = None,
        blowdown_concentration_ratio: Annotated[
            float | None,
            Field(description='Blowdown concentration ratio used when BlowdownCalculationMode is ConcentrationRatio.'),
        ] = None,
        blowdown_makeup_water_usage_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional schedule target for scheduled blowdown makeup water use in m3/s.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='EnergyPlus/OpenStudio name for the single-speed evaporative fluid cooler.'),
        ] = None,
        output_variable_names: Annotated[
            list[str] | None,
            Field(
                description="Optional explicit EnergyPlus output variable names to request for this fluid cooler."
            ),
        ] = None,
        output_reporting_frequency: Annotated[
            Literal["Detail", "Hourly", "Daily", "Monthly", "RunPeriod"],
            Field(description="Reporting frequency used when requesting output_variable_names from EnergyPlus outputs."),
        ] = "Hourly",
        ems_sensor_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional EMS Sensor targets associated with this fluid cooler."),
        ] = None,
        ems_actuator_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional EMS Actuator targets associated with this fluid cooler."),
        ] = None,
        ems_internal_variable_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional EMS InternalVariable targets associated with this fluid cooler."
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_EvaporativeFluidCoolerSingleSpeed as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if design_air_flow_rate is not None:
            source_fields['DesignAirFlowRate'] = design_air_flow_rate
        if fan_powerat_design_air_flow_rate is not None:
            source_fields['FanPoweratDesignAirFlowRate'] = fan_powerat_design_air_flow_rate
        if design_spray_water_flow_rate is not None:
            source_fields['DesignSprayWaterFlowRate'] = design_spray_water_flow_rate
        if performance_input_method is not None:
            source_fields['PerformanceInputMethod'] = performance_input_method
        if standard_design_capacity is not None:
            source_fields['StandardDesignCapacity'] = standard_design_capacity
        if ufactor_times_area_valueat_design_air_flow_rate is not None:
            source_fields['UfactorTimesAreaValueatDesignAirFlowRate'] = ufactor_times_area_valueat_design_air_flow_rate
        if design_water_flow_rate is not None:
            source_fields['DesignWaterFlowRate'] = design_water_flow_rate
        if user_specified_design_capacity is not None:
            source_fields['UserSpecifiedDesignCapacity'] = user_specified_design_capacity
        if design_entering_water_temperature is not None:
            source_fields['DesignEnteringWaterTemperature'] = design_entering_water_temperature
        if design_entering_air_temperature is not None:
            source_fields['DesignEnteringAirTemperature'] = design_entering_air_temperature
        if design_entering_air_wetbulb_temperature is not None:
            source_fields['DesignEnteringAirWetbulbTemperature'] = design_entering_air_wetbulb_temperature
        if capacity_control is not None:
            source_fields['CapacityControl'] = capacity_control
        if sizing_factor is not None:
            source_fields['SizingFactor'] = sizing_factor
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
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_EvaporativeFluidCoolerSingleSpeed',
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
