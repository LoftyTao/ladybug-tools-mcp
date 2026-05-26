'MCP tool for detailed_hvac_coil_cooling_water_to_air_heat_pump_equation_fit.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_cooling_water_to_air_heat_pump_equation_fit tool.'

    @mcp.tool(
        name='coil_cooling_water_to_air_heat_pump_equation_fit',
        description=(
            'Create an Ironbug IB_CoilCoolingWaterToAirHeatPumpEquationFit object for EnergyPlus/OpenStudio Coil:Cooling:WaterToAirHeatPump:EquationFit. Use this single-speed DX cooling coil with a ZoneHVAC:WaterToAirHeatPump or water-loop heat pump assembly; it is a heat-pump coil, not a hydronic Pump:* object. This authors Ironbug DetailedHVAC input only; run Energy simulation after the DetailedHVAC system is applied. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'coil',
            'cooling',
            'dx',
            'heat-pump',
            'water-to-air',
            'equation-fit',
            'zone-equipment',
            'curve',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_coil_cooling_water_to_air_heat_pump_equation_fit(
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
            Field(description="Stable DetailedHVAC object identifier for this water-to-air heat-pump cooling coil."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional display label shown in Ironbug/Garden summaries."),
        ] = None,
        rated_air_flow_rate: Annotated[
            float | str | None,
            Field(description="Optional rated air flow rate in m3/s, or autosize-compatible value accepted by Ironbug."),
        ] = None,
        rated_water_flow_rate: Annotated[
            float | str | None,
            Field(description="Optional rated water flow rate in m3/s, or autosize-compatible value accepted by Ironbug."),
        ] = None,
        rated_total_cooling_capacity: Annotated[
            float | str | None,
            Field(description="Optional gross rated total cooling capacity in W, before supply-fan heat effects."),
        ] = None,
        rated_sensible_cooling_capacity: Annotated[
            float | str | None,
            Field(description="Optional gross rated sensible cooling capacity in W."),
        ] = None,
        rated_cooling_coefficientof_performance: Annotated[
            float | None,
            Field(description="Optional gross rated cooling COP in W/W."),
        ] = None,
        rated_entering_water_temperature: Annotated[
            float | None,
            Field(description="Optional rated entering water temperature in C."),
        ] = None,
        rated_entering_air_dry_bulb_temperature: Annotated[
            float | None,
            Field(description="Optional rated entering air dry-bulb temperature in C."),
        ] = None,
        rated_entering_air_wet_bulb_temperature: Annotated[
            float | None,
            Field(description="Optional rated entering air wet-bulb temperature in C."),
        ] = None,
        total_cooling_capacity_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for normalized total cooling capacity."),
        ] = None,
        total_cooling_capacity_coefficient1: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 1 for the normalized total cooling capacity equation-fit curve."),
        ] = None,
        total_cooling_capacity_coefficient2: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 2 for the normalized total cooling capacity equation-fit curve."),
        ] = None,
        total_cooling_capacity_coefficient3: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 3 for the normalized total cooling capacity equation-fit curve."),
        ] = None,
        total_cooling_capacity_coefficient4: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 4 for the normalized total cooling capacity equation-fit curve."),
        ] = None,
        total_cooling_capacity_coefficient5: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 5 for the normalized total cooling capacity equation-fit curve."),
        ] = None,
        sensible_cooling_capacity_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for normalized sensible cooling capacity."),
        ] = None,
        sensible_cooling_capacity_coefficient1: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 1 for the normalized sensible cooling capacity equation-fit curve."),
        ] = None,
        sensible_cooling_capacity_coefficient2: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 2 for the normalized sensible cooling capacity equation-fit curve."),
        ] = None,
        sensible_cooling_capacity_coefficient3: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 3 for the normalized sensible cooling capacity equation-fit curve."),
        ] = None,
        sensible_cooling_capacity_coefficient4: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 4 for the normalized sensible cooling capacity equation-fit curve."),
        ] = None,
        sensible_cooling_capacity_coefficient5: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 5 for the normalized sensible cooling capacity equation-fit curve."),
        ] = None,
        sensible_cooling_capacity_coefficient6: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 6 for the normalized sensible cooling capacity equation-fit curve."),
        ] = None,
        cooling_power_consumption_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for cooling power consumption."),
        ] = None,
        cooling_power_consumption_coefficient1: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 1 for the cooling power consumption equation-fit curve."),
        ] = None,
        cooling_power_consumption_coefficient2: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 2 for the cooling power consumption equation-fit curve."),
        ] = None,
        cooling_power_consumption_coefficient3: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 3 for the cooling power consumption equation-fit curve."),
        ] = None,
        cooling_power_consumption_coefficient4: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 4 for the cooling power consumption equation-fit curve."),
        ] = None,
        cooling_power_consumption_coefficient5: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 5 for the cooling power consumption equation-fit curve."),
        ] = None,
        part_load_fraction_correlation_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for part-load fraction versus part-load ratio."),
        ] = None,
        nominal_timefor_condensate_removalto_begin: Annotated[
            float | None,
            Field(description="Optional nominal time in seconds before condensate removal begins for latent degradation modeling."),
        ] = None,
        ratioof_initial_moisture_evaporation_rateand_steady_state_latent_capacity: Annotated[
            float | None,
            Field(description="Optional ratio of initial moisture evaporation rate to steady-state latent capacity."),
        ] = None,
        maximum_cycling_rate: Annotated[
            float | None,
            Field(description="Optional maximum compressor cycling rate in cycles per hour for latent degradation modeling."),
        ] = None,
        latent_capacity_time_constant: Annotated[
            float | None,
            Field(description="Optional latent capacity time constant in seconds."),
        ] = None,
        fan_delay_time: Annotated[
            float | None,
            Field(description="Optional supply fan delay time in seconds for latent degradation calculations."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional EnergyPlus/OpenStudio coil name; defaults to the identifier when omitted."),
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
        """Create IB_CoilCoolingWaterToAirHeatPumpEquationFit as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if rated_air_flow_rate is not None:
            source_fields['RatedAirFlowRate'] = rated_air_flow_rate
        if rated_water_flow_rate is not None:
            source_fields['RatedWaterFlowRate'] = rated_water_flow_rate
        if rated_total_cooling_capacity is not None:
            source_fields['RatedTotalCoolingCapacity'] = rated_total_cooling_capacity
        if rated_sensible_cooling_capacity is not None:
            source_fields['RatedSensibleCoolingCapacity'] = rated_sensible_cooling_capacity
        if rated_cooling_coefficientof_performance is not None:
            source_fields['RatedCoolingCoefficientofPerformance'] = rated_cooling_coefficientof_performance
        if rated_entering_water_temperature is not None:
            source_fields['RatedEnteringWaterTemperature'] = rated_entering_water_temperature
        if rated_entering_air_dry_bulb_temperature is not None:
            source_fields['RatedEnteringAirDryBulbTemperature'] = rated_entering_air_dry_bulb_temperature
        if rated_entering_air_wet_bulb_temperature is not None:
            source_fields['RatedEnteringAirWetBulbTemperature'] = rated_entering_air_wet_bulb_temperature
        if total_cooling_capacity_curve_target is not None:
            source_field_targets['TotalCoolingCapacityCurve'] = total_cooling_capacity_curve_target
        if total_cooling_capacity_coefficient1 is not None:
            source_fields['TotalCoolingCapacityCoefficient1'] = total_cooling_capacity_coefficient1
        if total_cooling_capacity_coefficient2 is not None:
            source_fields['TotalCoolingCapacityCoefficient2'] = total_cooling_capacity_coefficient2
        if total_cooling_capacity_coefficient3 is not None:
            source_fields['TotalCoolingCapacityCoefficient3'] = total_cooling_capacity_coefficient3
        if total_cooling_capacity_coefficient4 is not None:
            source_fields['TotalCoolingCapacityCoefficient4'] = total_cooling_capacity_coefficient4
        if total_cooling_capacity_coefficient5 is not None:
            source_fields['TotalCoolingCapacityCoefficient5'] = total_cooling_capacity_coefficient5
        if sensible_cooling_capacity_curve_target is not None:
            source_field_targets['SensibleCoolingCapacityCurve'] = sensible_cooling_capacity_curve_target
        if sensible_cooling_capacity_coefficient1 is not None:
            source_fields['SensibleCoolingCapacityCoefficient1'] = sensible_cooling_capacity_coefficient1
        if sensible_cooling_capacity_coefficient2 is not None:
            source_fields['SensibleCoolingCapacityCoefficient2'] = sensible_cooling_capacity_coefficient2
        if sensible_cooling_capacity_coefficient3 is not None:
            source_fields['SensibleCoolingCapacityCoefficient3'] = sensible_cooling_capacity_coefficient3
        if sensible_cooling_capacity_coefficient4 is not None:
            source_fields['SensibleCoolingCapacityCoefficient4'] = sensible_cooling_capacity_coefficient4
        if sensible_cooling_capacity_coefficient5 is not None:
            source_fields['SensibleCoolingCapacityCoefficient5'] = sensible_cooling_capacity_coefficient5
        if sensible_cooling_capacity_coefficient6 is not None:
            source_fields['SensibleCoolingCapacityCoefficient6'] = sensible_cooling_capacity_coefficient6
        if cooling_power_consumption_curve_target is not None:
            source_field_targets['CoolingPowerConsumptionCurve'] = cooling_power_consumption_curve_target
        if cooling_power_consumption_coefficient1 is not None:
            source_fields['CoolingPowerConsumptionCoefficient1'] = cooling_power_consumption_coefficient1
        if cooling_power_consumption_coefficient2 is not None:
            source_fields['CoolingPowerConsumptionCoefficient2'] = cooling_power_consumption_coefficient2
        if cooling_power_consumption_coefficient3 is not None:
            source_fields['CoolingPowerConsumptionCoefficient3'] = cooling_power_consumption_coefficient3
        if cooling_power_consumption_coefficient4 is not None:
            source_fields['CoolingPowerConsumptionCoefficient4'] = cooling_power_consumption_coefficient4
        if cooling_power_consumption_coefficient5 is not None:
            source_fields['CoolingPowerConsumptionCoefficient5'] = cooling_power_consumption_coefficient5
        if part_load_fraction_correlation_curve_target is not None:
            source_field_targets['PartLoadFractionCorrelationCurve'] = part_load_fraction_correlation_curve_target
        if nominal_timefor_condensate_removalto_begin is not None:
            source_fields['NominalTimeforCondensateRemovaltoBegin'] = nominal_timefor_condensate_removalto_begin
        if ratioof_initial_moisture_evaporation_rateand_steady_state_latent_capacity is not None:
            source_fields['RatioofInitialMoistureEvaporationRateandSteadyStateLatentCapacity'] = ratioof_initial_moisture_evaporation_rateand_steady_state_latent_capacity
        if maximum_cycling_rate is not None:
            source_fields['MaximumCyclingRate'] = maximum_cycling_rate
        if latent_capacity_time_constant is not None:
            source_fields['LatentCapacityTimeConstant'] = latent_capacity_time_constant
        if fan_delay_time is not None:
            source_fields['FanDelayTime'] = fan_delay_time
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilCoolingWaterToAirHeatPumpEquationFit',
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
