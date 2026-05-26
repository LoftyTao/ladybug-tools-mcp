'MCP tool for detailed_hvac_electric_load_center_inverter_look_up_table.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_electric_load_center_inverter_look_up_table tool.'

    @mcp.tool(
        name='electric_load_center_inverter_look_up_table',
        description=(
            'Create IB_ElectricLoadCenterInverterLookUpTable, an EnergyPlus/OpenStudio ElectricLoadCenter:Inverter:LookUpTable object whose efficiency varies by power fraction at nominal voltage. Use it as a Distribution inverter target when tabulated inverter performance is known. This tool authors inverter lookup-table input only; it does not create PV generators, storage, distribution panels, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'electric', 'electric-equipment', 'load-center', 'inverter', 'performance', 'author'},
        timeout=20,
    )
    def create_ironbug_electric_load_center_inverter_look_up_table(
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
            Field(description="Stable identifier for the new IB_ElectricLoadCenterInverterLookUpTable object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier controlling inverter availability; maps to Ironbug field AvailabilitySchedule.'),
        ] = None,
        radiative_fraction: Annotated[
            float | None,
            Field(description='Fraction of inverter losses released as zone radiative heat gain; maps to Ironbug field RadiativeFraction.'),
        ] = None,
        rated_maximum_continuous_output_power: Annotated[
            float | None,
            Field(description='Rated maximum continuous inverter AC output power in W; maps to Ironbug field RatedMaximumContinuousOutputPower.'),
        ] = None,
        night_tare_loss_power: Annotated[
            float | None,
            Field(description='Night tare loss power in W when the inverter is not producing output; maps to Ironbug field NightTareLossPower.'),
        ] = None,
        nominal_voltage_input: Annotated[
            float | None,
            Field(description='Nominal DC input voltage for the lookup table in V; maps to Ironbug field NominalVoltageInput.'),
        ] = None,
        efficiency_at10_power_and_nominal_voltage: Annotated[
            float | None,
            Field(description='Inverter efficiency fraction at 10 percent power and nominal voltage; maps to Ironbug field EfficiencyAt10PowerAndNominalVoltage.'),
        ] = None,
        efficiency_at20_power_and_nominal_voltage: Annotated[
            float | None,
            Field(description='Inverter efficiency fraction at 20 percent power and nominal voltage; maps to Ironbug field EfficiencyAt20PowerAndNominalVoltage.'),
        ] = None,
        efficiency_at30_power_and_nominal_voltage: Annotated[
            float | None,
            Field(description='Inverter efficiency fraction at 30 percent power and nominal voltage; maps to Ironbug field EfficiencyAt30PowerAndNominalVoltage.'),
        ] = None,
        efficiency_at50_power_and_nominal_voltage: Annotated[
            float | None,
            Field(description='Inverter efficiency fraction at 50 percent power and nominal voltage; maps to Ironbug field EfficiencyAt50PowerAndNominalVoltage.'),
        ] = None,
        efficiency_at75_power_and_nominal_voltage: Annotated[
            float | None,
            Field(description='Inverter efficiency fraction at 75 percent power and nominal voltage; maps to Ironbug field EfficiencyAt75PowerAndNominalVoltage.'),
        ] = None,
        efficiency_at100_power_and_nominal_voltage: Annotated[
            float | None,
            Field(description='Inverter efficiency fraction at 100 percent power and nominal voltage; maps to Ironbug field EfficiencyAt100PowerAndNominalVoltage.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio ElectricLoadCenter:Inverter:LookUpTable object name; defaults to the identifier when omitted.'),
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
        """Create IB_ElectricLoadCenterInverterLookUpTable as reviewed inverter lookup-table data."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if radiative_fraction is not None:
            source_fields['RadiativeFraction'] = radiative_fraction
        if rated_maximum_continuous_output_power is not None:
            source_fields['RatedMaximumContinuousOutputPower'] = rated_maximum_continuous_output_power
        if night_tare_loss_power is not None:
            source_fields['NightTareLossPower'] = night_tare_loss_power
        if nominal_voltage_input is not None:
            source_fields['NominalVoltageInput'] = nominal_voltage_input
        if efficiency_at10_power_and_nominal_voltage is not None:
            source_fields['EfficiencyAt10PowerAndNominalVoltage'] = efficiency_at10_power_and_nominal_voltage
        if efficiency_at20_power_and_nominal_voltage is not None:
            source_fields['EfficiencyAt20PowerAndNominalVoltage'] = efficiency_at20_power_and_nominal_voltage
        if efficiency_at30_power_and_nominal_voltage is not None:
            source_fields['EfficiencyAt30PowerAndNominalVoltage'] = efficiency_at30_power_and_nominal_voltage
        if efficiency_at50_power_and_nominal_voltage is not None:
            source_fields['EfficiencyAt50PowerAndNominalVoltage'] = efficiency_at50_power_and_nominal_voltage
        if efficiency_at75_power_and_nominal_voltage is not None:
            source_fields['EfficiencyAt75PowerAndNominalVoltage'] = efficiency_at75_power_and_nominal_voltage
        if efficiency_at100_power_and_nominal_voltage is not None:
            source_fields['EfficiencyAt100PowerAndNominalVoltage'] = efficiency_at100_power_and_nominal_voltage
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ElectricLoadCenterInverterLookUpTable',
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
