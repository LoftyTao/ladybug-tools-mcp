'MCP tool for detailed_hvac_generator_micro_turbine.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_generator_micro_turbine tool.'

    @mcp.tool(
        name='generator_micro_turbine',
        description=(
            'Create IB_GeneratorMicroTurbine, an OpenStudio/EnergyPlus Generator:MicroTurbine object for an Ironbug ElectricLoadCenter distribution. Use it for fuel-fired onsite electric generation with power, efficiency, fuel, exhaust, and curve inputs; this is not a hydronic plant component, PV array, inverter, storage object, or Energy simulation runner. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'electric', 'electric-equipment', 'generator', 'microturbine', 'fuel', 'curve', 'author'},
        timeout=20,
    )
    def create_ironbug_generator_micro_turbine(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, for example garden_create['garden_root']."),
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
            Field(description="Stable identifier for the new IB_GeneratorMicroTurbine object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target controlling when the microturbine generator is available.'),
        ] = None,
        reference_electrical_power_output: Annotated[
            float | None,
            Field(description='Optional reference electrical power output in W for Generator:MicroTurbine.'),
        ] = None,
        minimum_full_load_electrical_power_output: Annotated[
            float | None,
            Field(description='Optional MinimumFullLoadElectricalPowerOutput value; maps to Ironbug IB_GeneratorMicroTurbine field MinimumFullLoadElectricalPowerOutput.'),
        ] = None,
        maximum_full_load_electrical_power_output: Annotated[
            float | None,
            Field(description='Optional MaximumFullLoadElectricalPowerOutput value; maps to Ironbug IB_GeneratorMicroTurbine field MaximumFullLoadElectricalPowerOutput.'),
        ] = None,
        reference_electrical_efficiency_using_lower_heating_value: Annotated[
            float | None,
            Field(description='Optional reference electrical efficiency using the fuel lower heating value.'),
        ] = None,
        reference_combustion_air_inlet_temperature: Annotated[
            float | None,
            Field(description='Optional ReferenceCombustionAirInletTemperature value; maps to Ironbug IB_GeneratorMicroTurbine field ReferenceCombustionAirInletTemperature.'),
        ] = None,
        reference_combustion_air_inlet_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional ReferenceCombustionAirInletHumidityRatio value; maps to Ironbug IB_GeneratorMicroTurbine field ReferenceCombustionAirInletHumidityRatio.'),
        ] = None,
        reference_elevation: Annotated[
            float | None,
            Field(description='Optional ReferenceElevation value; maps to Ironbug IB_GeneratorMicroTurbine field ReferenceElevation.'),
        ] = None,
        electrical_power_functionof_temperatureand_elevation_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for ElectricalPowerFunctionofTemperatureandElevationCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_GeneratorMicroTurbine field ElectricalPowerFunctionofTemperatureandElevationCurve (IB_Curve).'),
        ] = None,
        electrical_efficiency_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for ElectricalEfficiencyFunctionofTemperatureCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_GeneratorMicroTurbine field ElectricalEfficiencyFunctionofTemperatureCurve (IB_Curve).'),
        ] = None,
        electrical_efficiency_functionof_part_load_ratio_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for ElectricalEfficiencyFunctionofPartLoadRatioCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_GeneratorMicroTurbine field ElectricalEfficiencyFunctionofPartLoadRatioCurve (IB_Curve).'),
        ] = None,
        fuel_type: Annotated[
            str | None,
            Field(description='Optional EnergyPlus fuel type for the microturbine generator.'),
        ] = None,
        fuel_higher_heating_value: Annotated[
            float | None,
            Field(description='Optional FuelHigherHeatingValue value; maps to Ironbug IB_GeneratorMicroTurbine field FuelHigherHeatingValue.'),
        ] = None,
        fuel_lower_heating_value: Annotated[
            float | None,
            Field(description='Optional FuelLowerHeatingValue value; maps to Ironbug IB_GeneratorMicroTurbine field FuelLowerHeatingValue.'),
        ] = None,
        standby_power: Annotated[
            float | None,
            Field(description='Optional StandbyPower value; maps to Ironbug IB_GeneratorMicroTurbine field StandbyPower.'),
        ] = None,
        ancillary_power: Annotated[
            float | None,
            Field(description='Optional AncillaryPower value; maps to Ironbug IB_GeneratorMicroTurbine field AncillaryPower.'),
        ] = None,
        ancillary_power_functionof_fuel_input_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for AncillaryPowerFunctionofFuelInputCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_GeneratorMicroTurbine field AncillaryPowerFunctionofFuelInputCurve (IB_Curve).'),
        ] = None,
        reference_exhaust_air_mass_flow_rate: Annotated[
            float | None,
            Field(description='Optional ReferenceExhaustAirMassFlowRate value; maps to Ironbug IB_GeneratorMicroTurbine field ReferenceExhaustAirMassFlowRate.'),
        ] = None,
        exhaust_air_flow_rate_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for ExhaustAirFlowRateFunctionofTemperatureCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_GeneratorMicroTurbine field ExhaustAirFlowRateFunctionofTemperatureCurve (IB_Curve).'),
        ] = None,
        exhaust_air_flow_rate_functionof_part_load_ratio_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for ExhaustAirFlowRateFunctionofPartLoadRatioCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_GeneratorMicroTurbine field ExhaustAirFlowRateFunctionofPartLoadRatioCurve (IB_Curve).'),
        ] = None,
        nominal_exhaust_air_outlet_temperature: Annotated[
            float | None,
            Field(description='Optional NominalExhaustAirOutletTemperature value; maps to Ironbug IB_GeneratorMicroTurbine field NominalExhaustAirOutletTemperature.'),
        ] = None,
        exhaust_air_temperature_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for ExhaustAirTemperatureFunctionofTemperatureCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_GeneratorMicroTurbine field ExhaustAirTemperatureFunctionofTemperatureCurve (IB_Curve).'),
        ] = None,
        exhaust_air_temperature_functionof_part_load_ratio_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for ExhaustAirTemperatureFunctionofPartLoadRatioCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_GeneratorMicroTurbine field ExhaustAirTemperatureFunctionofPartLoadRatioCurve (IB_Curve).'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio name for the microturbine generator object.'),
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
        """Create IB_GeneratorMicroTurbine as a reviewed Ironbug Electrical authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if reference_electrical_power_output is not None:
            source_fields['ReferenceElectricalPowerOutput'] = reference_electrical_power_output
        if minimum_full_load_electrical_power_output is not None:
            source_fields['MinimumFullLoadElectricalPowerOutput'] = minimum_full_load_electrical_power_output
        if maximum_full_load_electrical_power_output is not None:
            source_fields['MaximumFullLoadElectricalPowerOutput'] = maximum_full_load_electrical_power_output
        if reference_electrical_efficiency_using_lower_heating_value is not None:
            source_fields['ReferenceElectricalEfficiencyUsingLowerHeatingValue'] = reference_electrical_efficiency_using_lower_heating_value
        if reference_combustion_air_inlet_temperature is not None:
            source_fields['ReferenceCombustionAirInletTemperature'] = reference_combustion_air_inlet_temperature
        if reference_combustion_air_inlet_humidity_ratio is not None:
            source_fields['ReferenceCombustionAirInletHumidityRatio'] = reference_combustion_air_inlet_humidity_ratio
        if reference_elevation is not None:
            source_fields['ReferenceElevation'] = reference_elevation
        if electrical_power_functionof_temperatureand_elevation_curve_target is not None:
            source_field_targets['ElectricalPowerFunctionofTemperatureandElevationCurve'] = electrical_power_functionof_temperatureand_elevation_curve_target
        if electrical_efficiency_functionof_temperature_curve_target is not None:
            source_field_targets['ElectricalEfficiencyFunctionofTemperatureCurve'] = electrical_efficiency_functionof_temperature_curve_target
        if electrical_efficiency_functionof_part_load_ratio_curve_target is not None:
            source_field_targets['ElectricalEfficiencyFunctionofPartLoadRatioCurve'] = electrical_efficiency_functionof_part_load_ratio_curve_target
        if fuel_type is not None:
            source_fields['FuelType'] = fuel_type
        if fuel_higher_heating_value is not None:
            source_fields['FuelHigherHeatingValue'] = fuel_higher_heating_value
        if fuel_lower_heating_value is not None:
            source_fields['FuelLowerHeatingValue'] = fuel_lower_heating_value
        if standby_power is not None:
            source_fields['StandbyPower'] = standby_power
        if ancillary_power is not None:
            source_fields['AncillaryPower'] = ancillary_power
        if ancillary_power_functionof_fuel_input_curve_target is not None:
            source_field_targets['AncillaryPowerFunctionofFuelInputCurve'] = ancillary_power_functionof_fuel_input_curve_target
        if reference_exhaust_air_mass_flow_rate is not None:
            source_fields['ReferenceExhaustAirMassFlowRate'] = reference_exhaust_air_mass_flow_rate
        if exhaust_air_flow_rate_functionof_temperature_curve_target is not None:
            source_field_targets['ExhaustAirFlowRateFunctionofTemperatureCurve'] = exhaust_air_flow_rate_functionof_temperature_curve_target
        if exhaust_air_flow_rate_functionof_part_load_ratio_curve_target is not None:
            source_field_targets['ExhaustAirFlowRateFunctionofPartLoadRatioCurve'] = exhaust_air_flow_rate_functionof_part_load_ratio_curve_target
        if nominal_exhaust_air_outlet_temperature is not None:
            source_fields['NominalExhaustAirOutletTemperature'] = nominal_exhaust_air_outlet_temperature
        if exhaust_air_temperature_functionof_temperature_curve_target is not None:
            source_field_targets['ExhaustAirTemperatureFunctionofTemperatureCurve'] = exhaust_air_temperature_functionof_temperature_curve_target
        if exhaust_air_temperature_functionof_part_load_ratio_curve_target is not None:
            source_field_targets['ExhaustAirTemperatureFunctionofPartLoadRatioCurve'] = exhaust_air_temperature_functionof_part_load_ratio_curve_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_GeneratorMicroTurbine',
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
