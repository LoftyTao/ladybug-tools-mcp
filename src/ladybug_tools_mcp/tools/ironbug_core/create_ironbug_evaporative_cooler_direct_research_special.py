'MCP tool for detailed_hvac_evaporative_cooler_direct_research_special.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_evaporative_cooler_direct_research_special tool.'

    @mcp.tool(
        name='evaporative_cooler_direct_research_special',
        description=(
            'Create IB_EvaporativeCoolerDirectResearchSpecial, an EnergyPlus/OpenStudio direct evaporative cooler for an Ironbug air loop or outdoor-air path. Use it for direct adiabatic cooling with design effectiveness, primary-air-flow modifier curves, water pump power, drift/blowdown water use, and drybulb/wetbulb operating limits; this is not a hydronic fluid cooler, cooling tower, chiller, or Energy run. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'air-loop', 'evaporative-cooling', 'cooling', 'water-use', 'control', 'curve', 'author'},
        timeout=20,
    )
    def create_ironbug_evaporative_cooler_direct_research_special(
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
            Field(description="Stable identifier for the new IB_EvaporativeCoolerDirectResearchSpecial object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional schedule target that defines when the direct evaporative cooler can operate.'),
        ] = None,
        available_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional legacy Ironbug AvailableSchedule target; use availability_schedule_target for new calls.'),
        ] = None,
        cooler_design_effectiveness: Annotated[
            float | None,
            Field(description='Direct evaporative cooler design effectiveness applied to wetbulb depression at design air flow.'),
        ] = None,
        cooler_effectiveness: Annotated[
            str | float | int | bool | None,
            Field(description='Optional legacy cooler effectiveness field; prefer cooler_design_effectiveness for EnergyPlus ResearchSpecial input.'),
        ] = None,
        recirculating_water_pump_power_consumption: Annotated[
            float | str | None,
            Field(description='Recirculating/spray water pump design power in W, or autosize when supported by the source object.'),
        ] = None,
        primary_air_design_flow_rate: Annotated[
            float | str | None,
            Field(description='Primary air design flow rate in m3/s for the air-loop or outdoor-air path; may be autosized.'),
        ] = None,
        drift_loss_fraction: Annotated[
            float | None,
            Field(description='Additional water drift loss as a fraction of normal evaporative water use.'),
        ] = None,
        blowdown_concentration_ratio: Annotated[
            float | None,
            Field(description='Blowdown concentration ratio used to estimate sump blowdown water use from evaporation.'),
        ] = None,
        effectiveness_flow_ratio_modifier_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional one-variable curve target that modifies cooler effectiveness by primary air flow fraction.'),
        ] = None,
        water_pump_power_sizing_factor: Annotated[
            float | None,
            Field(description='Water pump power sizing factor in W per m3/s when pump design power is autosized.'),
        ] = None,
        water_pump_power_modifier_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional one-variable curve target that modifies pump power by primary air flow fraction.'),
        ] = None,
        evaporative_operation_minimum_drybulb_temperature: Annotated[
            float | None,
            Field(description='Minimum inlet air drybulb temperature in degC below which the evaporative cooler turns off.'),
        ] = None,
        evaporative_operation_maximum_limit_wetbulb_temperature: Annotated[
            float | None,
            Field(description='Maximum inlet air wetbulb temperature in degC above which the evaporative cooler turns off.'),
        ] = None,
        evaporative_operation_maximum_limit_drybulb_temperature: Annotated[
            float | None,
            Field(description='Maximum inlet air drybulb temperature in degC above which the evaporative cooler turns off.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='EnergyPlus/OpenStudio name for the direct ResearchSpecial evaporative cooler.'),
        ] = None,
        output_variable_names: Annotated[
            list[str] | None,
            Field(
                description="Optional explicit EnergyPlus output variable names to request for this evaporative cooler."
            ),
        ] = None,
        output_reporting_frequency: Annotated[
            Literal["Detail", "Hourly", "Daily", "Monthly", "RunPeriod"],
            Field(description="Reporting frequency used when requesting output_variable_names from EnergyPlus outputs."),
        ] = "Hourly",
        ems_sensor_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional EMS Sensor targets associated with this evaporative cooler."),
        ] = None,
        ems_actuator_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional EMS Actuator targets associated with this evaporative cooler."),
        ] = None,
        ems_internal_variable_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional EMS InternalVariable targets associated with this evaporative cooler."
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_EvaporativeCoolerDirectResearchSpecial as a reviewed Ironbug LoopObjs / AirLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if available_schedule_target is not None:
            source_field_targets['AvailableSchedule'] = available_schedule_target
        if cooler_design_effectiveness is not None:
            source_fields['CoolerDesignEffectiveness'] = cooler_design_effectiveness
        if cooler_effectiveness is not None:
            source_fields['CoolerEffectiveness'] = cooler_effectiveness
        if recirculating_water_pump_power_consumption is not None:
            source_fields['RecirculatingWaterPumpPowerConsumption'] = recirculating_water_pump_power_consumption
        if primary_air_design_flow_rate is not None:
            source_fields['PrimaryAirDesignFlowRate'] = primary_air_design_flow_rate
        if drift_loss_fraction is not None:
            source_fields['DriftLossFraction'] = drift_loss_fraction
        if blowdown_concentration_ratio is not None:
            source_fields['BlowdownConcentrationRatio'] = blowdown_concentration_ratio
        if effectiveness_flow_ratio_modifier_curve_target is not None:
            source_field_targets['EffectivenessFlowRatioModifierCurve'] = effectiveness_flow_ratio_modifier_curve_target
        if water_pump_power_sizing_factor is not None:
            source_fields['WaterPumpPowerSizingFactor'] = water_pump_power_sizing_factor
        if water_pump_power_modifier_curve_target is not None:
            source_field_targets['WaterPumpPowerModifierCurve'] = water_pump_power_modifier_curve_target
        if evaporative_operation_minimum_drybulb_temperature is not None:
            source_fields['EvaporativeOperationMinimumDrybulbTemperature'] = evaporative_operation_minimum_drybulb_temperature
        if evaporative_operation_maximum_limit_wetbulb_temperature is not None:
            source_fields['EvaporativeOperationMaximumLimitWetbulbTemperature'] = evaporative_operation_maximum_limit_wetbulb_temperature
        if evaporative_operation_maximum_limit_drybulb_temperature is not None:
            source_fields['EvaporativeOperationMaximumLimitDrybulbTemperature'] = evaporative_operation_maximum_limit_drybulb_temperature
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_EvaporativeCoolerDirectResearchSpecial',
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
