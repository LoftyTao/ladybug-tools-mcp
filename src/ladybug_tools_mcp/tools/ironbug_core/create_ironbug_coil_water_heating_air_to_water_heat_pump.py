'MCP tool for detailed_hvac_coil_water_heating_air_to_water_heat_pump.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_water_heating_air_to_water_heat_pump tool.'

    @mcp.tool(
        name='coil_water_heating_air_to_water_heat_pump',
        description=(
            'Create an Ironbug IB_CoilWaterHeatingAirToWaterHeatPump object for EnergyPlus/OpenStudio Coil:WaterHeating:AirToWaterHeatPump:Pumped. Use this DX air-to-water heat-pump water-heating coil with WaterHeater:HeatPump:PumpedCondenser workflows; fields mentioning condenser pump power describe the coil package and do not make this a hydronic Pump:* object. This authors Ironbug DetailedHVAC input only; run Energy simulation after the DetailedHVAC system is applied. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'coil',
            'heating',
            'dx',
            'heat-pump',
            'air-to-water',
            'hot-water',
            'water-heater',
            'curve',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_coil_water_heating_air_to_water_heat_pump(
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
            Field(description="Stable DetailedHVAC object identifier for this air-to-water heat-pump water-heating coil."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional display label shown in Ironbug/Garden summaries."),
        ] = None,
        rated_heating_capacity: Annotated[
            float | None,
            Field(description="Optional rated water-heating capacity in W."),
        ] = None,
        rated_cop: Annotated[
            float | None,
            Field(description="Optional rated coefficient of performance in W/W."),
        ] = None,
        rated_sensible_heat_ratio: Annotated[
            float | None,
            Field(description="Optional rated sensible heat ratio as a 0-1 fraction."),
        ] = None,
        rated_evaporator_inlet_air_dry_bulb_temperature: Annotated[
            float | None,
            Field(description="Optional rated evaporator inlet air dry-bulb temperature in C."),
        ] = None,
        rated_evaporator_inlet_air_wet_bulb_temperature: Annotated[
            float | None,
            Field(description="Optional rated evaporator inlet air wet-bulb temperature in C."),
        ] = None,
        rated_condenser_inlet_water_temperature: Annotated[
            float | None,
            Field(description="Optional rated condenser inlet water temperature in C."),
        ] = None,
        rated_evaporator_air_flow_rate: Annotated[
            float | str | None,
            Field(description="Optional rated evaporator air flow rate in m3/s, or autosize-compatible value accepted by Ironbug."),
        ] = None,
        rated_condenser_water_flow_rate: Annotated[
            float | str | None,
            Field(description="Optional rated condenser water flow rate in m3/s, or autosize-compatible value accepted by Ironbug."),
        ] = None,
        evaporator_fan_power_includedin_rated_cop: Annotated[
            bool | str | None,
            Field(description="Optional flag indicating whether evaporator fan power is included in the rated COP."),
        ] = None,
        condenser_pump_power_includedin_rated_cop: Annotated[
            bool | str | None,
            Field(description="Optional flag indicating whether packaged condenser pump power is included in the rated COP."),
        ] = None,
        condenser_pump_heat_includedin_rated_heating_capacityand_rated_cop: Annotated[
            bool | str | None,
            Field(description="Optional flag indicating whether condenser pump heat is included in rated heating capacity and rated COP."),
        ] = None,
        condenser_water_pump_power: Annotated[
            float | None,
            Field(description="Optional packaged condenser water pump power in W for this heat-pump coil calculation."),
        ] = None,
        fractionof_condenser_pump_heatto_water: Annotated[
            float | None,
            Field(description="Optional fraction of condenser pump heat added to water, from 0 to 1."),
        ] = None,
        crankcase_heater_capacity: Annotated[
            float | None,
            Field(description="Optional crankcase heater capacity in W."),
        ] = None,
        crankcase_heater_capacity_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for crankcase heater capacity as a function of temperature."),
        ] = None,
        maximum_ambient_temperaturefor_crankcase_heater_operation: Annotated[
            float | None,
            Field(description="Optional maximum ambient temperature in C for crankcase heater operation."),
        ] = None,
        evaporator_air_temperature_typefor_curve_objects_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional same-model identifier or target for the evaporator air temperature type used by performance curves."),
        ] = None,
        heating_capacity_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for heating capacity as a function of temperature."),
        ] = None,
        heating_capacity_functionof_air_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for heating capacity as a function of evaporator air flow fraction."),
        ] = None,
        heating_capacity_functionof_water_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for heating capacity as a function of condenser water flow fraction."),
        ] = None,
        heating_cop_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for heating COP as a function of temperature."),
        ] = None,
        heating_cop_functionof_air_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for heating COP as a function of evaporator air flow fraction."),
        ] = None,
        heating_cop_functionof_water_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for heating COP as a function of condenser water flow fraction."),
        ] = None,
        part_load_fraction_correlation_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for part-load fraction versus part-load ratio."),
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
        """Create IB_CoilWaterHeatingAirToWaterHeatPump as a reviewed Ironbug Loop Objs authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if rated_heating_capacity is not None:
            source_fields['RatedHeatingCapacity'] = rated_heating_capacity
        if rated_cop is not None:
            source_fields['RatedCOP'] = rated_cop
        if rated_sensible_heat_ratio is not None:
            source_fields['RatedSensibleHeatRatio'] = rated_sensible_heat_ratio
        if rated_evaporator_inlet_air_dry_bulb_temperature is not None:
            source_fields['RatedEvaporatorInletAirDryBulbTemperature'] = rated_evaporator_inlet_air_dry_bulb_temperature
        if rated_evaporator_inlet_air_wet_bulb_temperature is not None:
            source_fields['RatedEvaporatorInletAirWetBulbTemperature'] = rated_evaporator_inlet_air_wet_bulb_temperature
        if rated_condenser_inlet_water_temperature is not None:
            source_fields['RatedCondenserInletWaterTemperature'] = rated_condenser_inlet_water_temperature
        if rated_evaporator_air_flow_rate is not None:
            source_fields['RatedEvaporatorAirFlowRate'] = rated_evaporator_air_flow_rate
        if rated_condenser_water_flow_rate is not None:
            source_fields['RatedCondenserWaterFlowRate'] = rated_condenser_water_flow_rate
        if evaporator_fan_power_includedin_rated_cop is not None:
            source_fields['EvaporatorFanPowerIncludedinRatedCOP'] = evaporator_fan_power_includedin_rated_cop
        if condenser_pump_power_includedin_rated_cop is not None:
            source_fields['CondenserPumpPowerIncludedinRatedCOP'] = condenser_pump_power_includedin_rated_cop
        if condenser_pump_heat_includedin_rated_heating_capacityand_rated_cop is not None:
            source_fields['CondenserPumpHeatIncludedinRatedHeatingCapacityandRatedCOP'] = condenser_pump_heat_includedin_rated_heating_capacityand_rated_cop
        if condenser_water_pump_power is not None:
            source_fields['CondenserWaterPumpPower'] = condenser_water_pump_power
        if fractionof_condenser_pump_heatto_water is not None:
            source_fields['FractionofCondenserPumpHeattoWater'] = fractionof_condenser_pump_heatto_water
        if crankcase_heater_capacity is not None:
            source_fields['CrankcaseHeaterCapacity'] = crankcase_heater_capacity
        if crankcase_heater_capacity_functionof_temperature_curve_target is not None:
            source_field_targets['CrankcaseHeaterCapacityFunctionofTemperatureCurve'] = crankcase_heater_capacity_functionof_temperature_curve_target
        if maximum_ambient_temperaturefor_crankcase_heater_operation is not None:
            source_fields['MaximumAmbientTemperatureforCrankcaseHeaterOperation'] = maximum_ambient_temperaturefor_crankcase_heater_operation
        if evaporator_air_temperature_typefor_curve_objects_target is not None:
            source_field_targets['EvaporatorAirTemperatureTypeforCurveObjects'] = evaporator_air_temperature_typefor_curve_objects_target
        if heating_capacity_functionof_temperature_curve_target is not None:
            source_field_targets['HeatingCapacityFunctionofTemperatureCurve'] = heating_capacity_functionof_temperature_curve_target
        if heating_capacity_functionof_air_flow_fraction_curve_target is not None:
            source_field_targets['HeatingCapacityFunctionofAirFlowFractionCurve'] = heating_capacity_functionof_air_flow_fraction_curve_target
        if heating_capacity_functionof_water_flow_fraction_curve_target is not None:
            source_field_targets['HeatingCapacityFunctionofWaterFlowFractionCurve'] = heating_capacity_functionof_water_flow_fraction_curve_target
        if heating_cop_functionof_temperature_curve_target is not None:
            source_field_targets['HeatingCOPFunctionofTemperatureCurve'] = heating_cop_functionof_temperature_curve_target
        if heating_cop_functionof_air_flow_fraction_curve_target is not None:
            source_field_targets['HeatingCOPFunctionofAirFlowFractionCurve'] = heating_cop_functionof_air_flow_fraction_curve_target
        if heating_cop_functionof_water_flow_fraction_curve_target is not None:
            source_field_targets['HeatingCOPFunctionofWaterFlowFractionCurve'] = heating_cop_functionof_water_flow_fraction_curve_target
        if part_load_fraction_correlation_curve_target is not None:
            source_field_targets['PartLoadFractionCorrelationCurve'] = part_load_fraction_correlation_curve_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilWaterHeatingAirToWaterHeatPump',
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
