'MCP tool for detailed_hvac_coil_heating_gas.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_heating_gas tool.'

    @mcp.tool(
        name='coil_heating_gas',
        description=(
            'Create IB_CoilHeatingGas, an OpenStudio CoilHeatingGas / EnergyPlus Coil:Heating:Fuel fuel-fired air heating coil with burner efficiency, nominal capacity, parasitic fuel, and part-load curve fields. Use it as a heating, reheat, or supplemental coil child in valid air-loop, terminal, packaged terminal, unit heater, unit ventilator, or heat-pump workflows. Use hydronic water coil or electrical load-center tools for those systems. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'heating', 'gas', 'fuel', 'gas-equipment', 'reheat', 'supplemental-heat', 'air-loop', 'zone-equipment', 'curve', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_heating_gas(
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
            Field(description="Stable identifier for the new IB_CoilHeatingGas object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for the fuel heating coil availability schedule. Maps to Ironbug IB_CoilHeatingGas field AvailabilitySchedule.'),
        ] = None,
        available_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for Ironbug AvailableSchedule when that source field is needed. Maps to Ironbug IB_CoilHeatingGas field AvailableSchedule.'),
        ] = None,
        fuel_type: Annotated[
            str | None,
            Field(description='Optional EnergyPlus fuel type for the heating coil, such as NaturalGas or Propane. Maps to Ironbug IB_CoilHeatingGas field FuelType.'),
        ] = None,
        gas_burner_efficiency: Annotated[
            float | None,
            Field(description='Optional gas burner efficiency as a decimal fraction, not a percent. Maps to Ironbug IB_CoilHeatingGas field GasBurnerEfficiency.'),
        ] = None,
        parasitic_electric_load: Annotated[
            str | float | int | bool | None,
            Field(description='Optional parasitic electric load associated with the fuel heating coil. Maps to Ironbug IB_CoilHeatingGas field ParasiticElectricLoad.'),
        ] = None,
        on_cycle_parasitic_electric_load: Annotated[
            float | None,
            Field(description='Optional on-cycle parasitic electric load, such as an inducer fan load. Maps to Ironbug IB_CoilHeatingGas field OnCycleParasiticElectricLoad.'),
        ] = None,
        parasitic_gas_load: Annotated[
            str | float | int | bool | None,
            Field(description='Optional parasitic fuel/gas load for the heating coil. Maps to Ironbug IB_CoilHeatingGas field ParasiticGasLoad.'),
        ] = None,
        off_cycle_parasitic_gas_load: Annotated[
            float | None,
            Field(description='Optional off-cycle parasitic fuel/gas load, such as a standing pilot light. Maps to Ironbug IB_CoilHeatingGas field OffCycleParasiticGasLoad.'),
        ] = None,
        nominal_capacity: Annotated[
            float | str | None,
            Field(description='Optional maximum heating capacity in W, or an autosize-style value accepted by Ironbug. Maps to Ironbug IB_CoilHeatingGas field NominalCapacity.'),
        ] = None,
        part_load_fraction_correlation_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target or same-model identifier for the part-load fraction correlation curve used to model fuel-consumption losses during cycling. Maps to Ironbug IB_CoilHeatingGas field PartLoadFractionCorrelationCurve.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilHeatingGas field Name.'),
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
        """Create IB_CoilHeatingGas as a reviewed Ironbug Loop Objs authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if available_schedule_target is not None:
            source_field_targets['AvailableSchedule'] = available_schedule_target
        if fuel_type is not None:
            source_fields['FuelType'] = fuel_type
        if gas_burner_efficiency is not None:
            source_fields['GasBurnerEfficiency'] = gas_burner_efficiency
        if parasitic_electric_load is not None:
            source_fields['ParasiticElectricLoad'] = parasitic_electric_load
        if on_cycle_parasitic_electric_load is not None:
            source_fields['OnCycleParasiticElectricLoad'] = on_cycle_parasitic_electric_load
        if parasitic_gas_load is not None:
            source_fields['ParasiticGasLoad'] = parasitic_gas_load
        if off_cycle_parasitic_gas_load is not None:
            source_fields['OffCycleParasiticGasLoad'] = off_cycle_parasitic_gas_load
        if nominal_capacity is not None:
            source_fields['NominalCapacity'] = nominal_capacity
        if part_load_fraction_correlation_curve_target is not None:
            source_field_targets['PartLoadFractionCorrelationCurve'] = part_load_fraction_correlation_curve_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilHeatingGas',
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
