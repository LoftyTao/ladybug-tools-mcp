'MCP tool for detailed_hvac_coil_heating_water_to_air_heat_pump_equation_fit.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_heating_water_to_air_heat_pump_equation_fit tool.'

    @mcp.tool(
        name='coil_heating_water_to_air_heat_pump_equation_fit',
        description=(
            'Create an Ironbug IB_CoilHeatingWaterToAirHeatPumpEquationFit object for EnergyPlus/OpenStudio Coil:Heating:WaterToAirHeatPump:EquationFit. Use this single-speed DX heating coil with a ZoneHVAC:WaterToAirHeatPump or water-loop heat pump assembly; it is a heat-pump coil, not a hydronic Pump:* object. This authors Ironbug DetailedHVAC input only; run Energy simulation after the DetailedHVAC system is applied. Returns target, summary_view, persistence_receipt, and report.'
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
            'water-to-air',
            'equation-fit',
            'zone-equipment',
            'curve',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_coil_heating_water_to_air_heat_pump_equation_fit(
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
            Field(description="Stable DetailedHVAC object identifier for this water-to-air heat-pump heating coil."),
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
        rated_heating_capacity: Annotated[
            float | str | None,
            Field(description="Optional gross rated heating capacity in W, before supply-fan heat effects."),
        ] = None,
        rated_heating_coefficientof_performance: Annotated[
            float | None,
            Field(description="Optional gross rated heating COP in W/W."),
        ] = None,
        rated_entering_water_temperature: Annotated[
            float | None,
            Field(description="Optional rated entering water temperature in C."),
        ] = None,
        rated_entering_air_dry_bulb_temperature: Annotated[
            float | None,
            Field(description="Optional rated entering air dry-bulb temperature in C."),
        ] = None,
        ratioof_rated_heating_capacityto_rated_cooling_capacity: Annotated[
            float | None,
            Field(description="Optional heating-to-cooling capacity ratio used when autosizing with a companion cooling coil."),
        ] = None,
        heating_capacity_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for normalized heating capacity."),
        ] = None,
        heating_capacity_coefficient1: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 1 for the normalized heating capacity equation-fit curve."),
        ] = None,
        heating_capacity_coefficient2: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 2 for the normalized heating capacity equation-fit curve."),
        ] = None,
        heating_capacity_coefficient3: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 3 for the normalized heating capacity equation-fit curve."),
        ] = None,
        heating_capacity_coefficient4: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 4 for the normalized heating capacity equation-fit curve."),
        ] = None,
        heating_capacity_coefficient5: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 5 for the normalized heating capacity equation-fit curve."),
        ] = None,
        heating_power_consumption_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for heating power consumption."),
        ] = None,
        heating_power_consumption_coefficient1: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 1 for the heating power consumption equation-fit curve."),
        ] = None,
        heating_power_consumption_coefficient2: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 2 for the heating power consumption equation-fit curve."),
        ] = None,
        heating_power_consumption_coefficient3: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 3 for the heating power consumption equation-fit curve."),
        ] = None,
        heating_power_consumption_coefficient4: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 4 for the heating power consumption equation-fit curve."),
        ] = None,
        heating_power_consumption_coefficient5: Annotated[
            str | float | int | bool | None,
            Field(description="Optional coefficient 5 for the heating power consumption equation-fit curve."),
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
        """Create IB_CoilHeatingWaterToAirHeatPumpEquationFit as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if rated_air_flow_rate is not None:
            source_fields['RatedAirFlowRate'] = rated_air_flow_rate
        if rated_water_flow_rate is not None:
            source_fields['RatedWaterFlowRate'] = rated_water_flow_rate
        if rated_heating_capacity is not None:
            source_fields['RatedHeatingCapacity'] = rated_heating_capacity
        if rated_heating_coefficientof_performance is not None:
            source_fields['RatedHeatingCoefficientofPerformance'] = rated_heating_coefficientof_performance
        if rated_entering_water_temperature is not None:
            source_fields['RatedEnteringWaterTemperature'] = rated_entering_water_temperature
        if rated_entering_air_dry_bulb_temperature is not None:
            source_fields['RatedEnteringAirDryBulbTemperature'] = rated_entering_air_dry_bulb_temperature
        if ratioof_rated_heating_capacityto_rated_cooling_capacity is not None:
            source_fields['RatioofRatedHeatingCapacitytoRatedCoolingCapacity'] = ratioof_rated_heating_capacityto_rated_cooling_capacity
        if heating_capacity_curve_target is not None:
            source_field_targets['HeatingCapacityCurve'] = heating_capacity_curve_target
        if heating_capacity_coefficient1 is not None:
            source_fields['HeatingCapacityCoefficient1'] = heating_capacity_coefficient1
        if heating_capacity_coefficient2 is not None:
            source_fields['HeatingCapacityCoefficient2'] = heating_capacity_coefficient2
        if heating_capacity_coefficient3 is not None:
            source_fields['HeatingCapacityCoefficient3'] = heating_capacity_coefficient3
        if heating_capacity_coefficient4 is not None:
            source_fields['HeatingCapacityCoefficient4'] = heating_capacity_coefficient4
        if heating_capacity_coefficient5 is not None:
            source_fields['HeatingCapacityCoefficient5'] = heating_capacity_coefficient5
        if heating_power_consumption_curve_target is not None:
            source_field_targets['HeatingPowerConsumptionCurve'] = heating_power_consumption_curve_target
        if heating_power_consumption_coefficient1 is not None:
            source_fields['HeatingPowerConsumptionCoefficient1'] = heating_power_consumption_coefficient1
        if heating_power_consumption_coefficient2 is not None:
            source_fields['HeatingPowerConsumptionCoefficient2'] = heating_power_consumption_coefficient2
        if heating_power_consumption_coefficient3 is not None:
            source_fields['HeatingPowerConsumptionCoefficient3'] = heating_power_consumption_coefficient3
        if heating_power_consumption_coefficient4 is not None:
            source_fields['HeatingPowerConsumptionCoefficient4'] = heating_power_consumption_coefficient4
        if heating_power_consumption_coefficient5 is not None:
            source_fields['HeatingPowerConsumptionCoefficient5'] = heating_power_consumption_coefficient5
        if part_load_fraction_correlation_curve_target is not None:
            source_field_targets['PartLoadFractionCorrelationCurve'] = part_load_fraction_correlation_curve_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilHeatingWaterToAirHeatPumpEquationFit',
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
