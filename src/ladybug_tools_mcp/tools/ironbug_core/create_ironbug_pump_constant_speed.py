'MCP tool for detailed_hvac_pump_constant_speed.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_pump_constant_speed tool.'

    @mcp.tool(
        name='pump_constant_speed',
        description=(
            'Create an Ironbug IB_PumpConstantSpeed component for an EnergyPlus/OpenStudio Pump:ConstantSpeed on a plant or condenser loop. Use this hydronic pump with chilled-water, hot-water, or condenser-water plant loops before adding chillers, boilers, cooling towers, coils, and other plant components. In chilled-water plant workflows, pair pump targets with chiller and cooling tower components before assembling the loop. This authors Ironbug DetailedHVAC input only; run Energy simulation after the DetailedHVAC system is applied. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'pump',
            'constant-speed',
            'plant-loop',
            'plant-component',
            'chilled-water',
            'hot-water',
            'condenser-water',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_pump_constant_speed(
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
            Field(description="Stable DetailedHVAC object identifier for this constant-speed pump."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional display label shown in Ironbug/Garden summaries."),
        ] = None,
        rated_pump_head: Annotated[
            float | None,
            Field(
                description="Optional design pump head in Pa."
            ),
        ] = None,
        motor_efficiency: Annotated[
            float | None,
            Field(
                description="Optional pump motor efficiency as a 0-1 fraction."
            ),
        ] = None,
        rated_flow_rate: Annotated[
            float | str | None,
            Field(
                description="Optional design flow rate in m3/s, or autosize-compatible value accepted by the Ironbug source mirror."
            ),
        ] = None,
        pump_control_type: Annotated[
            str | None,
            Field(
                description="Optional EnergyPlus pump control type, typically Continuous or Intermittent."
            ),
        ] = None,
        rated_power_consumption: Annotated[
            float | str | None,
            Field(description="Optional design power consumption in W, or autosize-compatible value accepted by the Ironbug source mirror."),
        ] = None,
        fractionof_motor_inefficienciesto_fluid_stream: Annotated[
            float | None,
            Field(description="Optional fraction of motor inefficiencies added to the fluid stream, from 0 to 1."),
        ] = None,
        pump_flow_rate_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Schedule target or same-model identifier that modifies pump flow rate over time."),
        ] = None,
        pump_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Curve target or same-model identifier for pump pressure as a function of flow."),
        ] = None,
        impeller_diameter: Annotated[
            float | None,
            Field(description="Optional pump impeller diameter in m used with the pump curve."),
        ] = None,
        rotational_speed: Annotated[
            float | None,
            Field(description="Optional rotational speed in rev/min used with the pump curve."),
        ] = None,
        skin_loss_radiative_fraction: Annotated[
            float | None,
            Field(description="Optional radiative fraction of pump skin losses assigned to a loss zone, from 0 to 1."),
        ] = None,
        design_power_sizing_method: Annotated[
            str | None,
            Field(description="Optional EnergyPlus design power sizing method, usually PowerPerFlow or PowerPerFlowPerPressure."),
        ] = None,
        design_electric_power_per_unit_flow_rate: Annotated[
            float | None,
            Field(description="Optional design electric power per unit flow rate in W/(m3/s)."),
        ] = None,
        design_shaft_power_per_unit_flow_rate_per_unit_head: Annotated[
            float | None,
            Field(description="Optional design shaft power per unit flow rate per unit head in W/((m3/s)-Pa)."),
        ] = None,
        end_use_subcategory: Annotated[
            str | None,
            Field(description="Optional EnergyPlus end-use subcategory text, such as General, Chilled Water, Hot Water, or Condenser."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional EnergyPlus/OpenStudio pump name; defaults to the identifier when omitted."),
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
        """Create IB_PumpConstantSpeed as a reviewed Ironbug Loop Objs authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if rated_pump_head is not None:
            source_fields['RatedPumpHead'] = rated_pump_head
        if motor_efficiency is not None:
            source_fields['MotorEfficiency'] = motor_efficiency
        if rated_flow_rate is not None:
            source_fields['RatedFlowRate'] = rated_flow_rate
        if pump_control_type is not None:
            source_fields['PumpControlType'] = pump_control_type
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if rated_power_consumption is not None:
            source_fields['RatedPowerConsumption'] = rated_power_consumption
        if fractionof_motor_inefficienciesto_fluid_stream is not None:
            source_fields['FractionofMotorInefficienciestoFluidStream'] = fractionof_motor_inefficienciesto_fluid_stream
        if pump_flow_rate_schedule_target is not None:
            source_field_targets['PumpFlowRateSchedule'] = pump_flow_rate_schedule_target
        if pump_curve_target is not None:
            source_field_targets['PumpCurve'] = pump_curve_target
        if impeller_diameter is not None:
            source_fields['ImpellerDiameter'] = impeller_diameter
        if rotational_speed is not None:
            source_fields['RotationalSpeed'] = rotational_speed
        if skin_loss_radiative_fraction is not None:
            source_fields['SkinLossRadiativeFraction'] = skin_loss_radiative_fraction
        if design_power_sizing_method is not None:
            source_fields['DesignPowerSizingMethod'] = design_power_sizing_method
        if design_electric_power_per_unit_flow_rate is not None:
            source_fields['DesignElectricPowerPerUnitFlowRate'] = design_electric_power_per_unit_flow_rate
        if design_shaft_power_per_unit_flow_rate_per_unit_head is not None:
            source_fields['DesignShaftPowerPerUnitFlowRatePerUnitHead'] = design_shaft_power_per_unit_flow_rate_per_unit_head
        if end_use_subcategory is not None:
            source_fields['EndUseSubcategory'] = end_use_subcategory
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_PumpConstantSpeed',
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
