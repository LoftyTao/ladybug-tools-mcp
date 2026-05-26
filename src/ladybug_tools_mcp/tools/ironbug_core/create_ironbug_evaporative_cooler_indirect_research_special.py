'MCP tool for detailed_hvac_evaporative_cooler_indirect_research_special.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_evaporative_cooler_indirect_research_special tool.'

    @mcp.tool(
        name='evaporative_cooler_indirect_research_special',
        description=(
            'Create IB_EvaporativeCoolerIndirectResearchSpecial, an EnergyPlus/OpenStudio indirect evaporative cooler for an Ironbug air loop or outdoor-air path. Use it for primary/secondary air evaporative cooling with wetbulb/drybulb effectiveness, secondary fan and pump power, flow-fraction modifier curves, drift/blowdown water use, and operating limits; this is not a hydronic fluid cooler or cooling tower. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'air-loop', 'evaporative-cooling', 'cooling', 'water-use', 'control', 'curve', 'fan', 'author'},
        timeout=20,
    )
    def create_ironbug_evaporative_cooler_indirect_research_special(
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
            Field(description="Stable identifier for the new IB_EvaporativeCoolerIndirectResearchSpecial object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional schedule target that defines when the indirect evaporative cooler can operate.'),
        ] = None,
        cooler_maximum_effectiveness: Annotated[
            float | None,
            Field(description='Maximum or wetbulb design effectiveness for indirect evaporative cooling.'),
        ] = None,
        recirculating_water_pump_power_consumption: Annotated[
            float | str | None,
            Field(description='Recirculating water pump design power in W, or autosize when supported by the source object.'),
        ] = None,
        secondary_fan_flow_rate: Annotated[
            float | str | None,
            Field(description='Secondary air fan flow rate in m3/s for the wet-side air stream.'),
        ] = None,
        secondary_fan_total_efficiency: Annotated[
            float | None,
            Field(description='Secondary fan total efficiency for parasitic fan power calculations.'),
        ] = None,
        secondary_fan_delta_pressure: Annotated[
            float | None,
            Field(description='Secondary fan pressure rise in Pa across the wet-side air stream.'),
        ] = None,
        dewpoint_effectiveness_factor: Annotated[
            float | None,
            Field(description='Dewpoint effectiveness factor that bounds indirect cooler leaving-air conditions.'),
        ] = None,
        drift_loss_fraction: Annotated[
            float | None,
            Field(description='Additional water drift loss as a fraction of normal evaporative water use.'),
        ] = None,
        blowdown_concentration_ratio: Annotated[
            float | None,
            Field(description='Blowdown concentration ratio used to estimate sump blowdown water use from evaporation.'),
        ] = None,
        wetbulb_effectiveness_flow_ratio_modifier_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional one-variable curve target that modifies wetbulb effectiveness by primary/secondary air flow fraction.'),
        ] = None,
        cooler_drybulb_design_effectiveness: Annotated[
            float | None,
            Field(description='Drybulb design effectiveness for dry indirect heat-exchanger operation.'),
        ] = None,
        drybulb_effectiveness_flow_ratio_modifier_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional one-variable curve target that modifies drybulb effectiveness by air flow fraction.'),
        ] = None,
        water_pump_power_sizing_factor: Annotated[
            float | None,
            Field(description='Water pump power sizing factor in W per m3/s when pump design power is autosized.'),
        ] = None,
        water_pump_power_modifier_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional curve target that modifies water pump power by secondary air flow fraction.'),
        ] = None,
        secondary_air_flow_scaling_factor: Annotated[
            float | None,
            Field(description='Scaling factor used to autosize secondary air design flow from primary design flow.'),
        ] = None,
        secondary_air_fan_design_power: Annotated[
            float | str | None,
            Field(description='Secondary air fan design power in W, or autosize when supported by the source object.'),
        ] = None,
        secondary_air_fan_power_modifier_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional curve target that modifies secondary fan power by secondary air flow fraction.'),
        ] = None,
        primary_design_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Primary air design flow rate in m3/s through the air-loop or outdoor-air path.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='EnergyPlus/OpenStudio name for the indirect ResearchSpecial evaporative cooler.'),
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
        """Create IB_EvaporativeCoolerIndirectResearchSpecial as a reviewed Ironbug LoopObjs / AirLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if cooler_maximum_effectiveness is not None:
            source_fields['CoolerMaximumEffectiveness'] = cooler_maximum_effectiveness
        if recirculating_water_pump_power_consumption is not None:
            source_fields['RecirculatingWaterPumpPowerConsumption'] = recirculating_water_pump_power_consumption
        if secondary_fan_flow_rate is not None:
            source_fields['SecondaryFanFlowRate'] = secondary_fan_flow_rate
        if secondary_fan_total_efficiency is not None:
            source_fields['SecondaryFanTotalEfficiency'] = secondary_fan_total_efficiency
        if secondary_fan_delta_pressure is not None:
            source_fields['SecondaryFanDeltaPressure'] = secondary_fan_delta_pressure
        if dewpoint_effectiveness_factor is not None:
            source_fields['DewpointEffectivenessFactor'] = dewpoint_effectiveness_factor
        if drift_loss_fraction is not None:
            source_fields['DriftLossFraction'] = drift_loss_fraction
        if blowdown_concentration_ratio is not None:
            source_fields['BlowdownConcentrationRatio'] = blowdown_concentration_ratio
        if wetbulb_effectiveness_flow_ratio_modifier_curve_target is not None:
            source_field_targets['WetbulbEffectivenessFlowRatioModifierCurve'] = wetbulb_effectiveness_flow_ratio_modifier_curve_target
        if cooler_drybulb_design_effectiveness is not None:
            source_fields['CoolerDrybulbDesignEffectiveness'] = cooler_drybulb_design_effectiveness
        if drybulb_effectiveness_flow_ratio_modifier_curve_target is not None:
            source_field_targets['DrybulbEffectivenessFlowRatioModifierCurve'] = drybulb_effectiveness_flow_ratio_modifier_curve_target
        if water_pump_power_sizing_factor is not None:
            source_fields['WaterPumpPowerSizingFactor'] = water_pump_power_sizing_factor
        if water_pump_power_modifier_curve_target is not None:
            source_field_targets['WaterPumpPowerModifierCurve'] = water_pump_power_modifier_curve_target
        if secondary_air_flow_scaling_factor is not None:
            source_fields['SecondaryAirFlowScalingFactor'] = secondary_air_flow_scaling_factor
        if secondary_air_fan_design_power is not None:
            source_fields['SecondaryAirFanDesignPower'] = secondary_air_fan_design_power
        if secondary_air_fan_power_modifier_curve_target is not None:
            source_field_targets['SecondaryAirFanPowerModifierCurve'] = secondary_air_fan_power_modifier_curve_target
        if primary_design_air_flow_rate is not None:
            source_fields['PrimaryDesignAirFlowRate'] = primary_design_air_flow_rate
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_EvaporativeCoolerIndirectResearchSpecial',
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
