'MCP tool for detailed_hvac_coil_heating_dx_variable_refrigerant_flow.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_heating_dx_variable_refrigerant_flow tool.'

    @mcp.tool(
        name='coil_heating_dx_variable_refrigerant_flow',
        description=(
            'Create IB_CoilHeatingDXVariableRefrigerantFlow, an OpenStudio/EnergyPlus Coil:Heating:DX:VariableRefrigerantFlow object for a VRF terminal unit heating coil. Use the returned target with the advanced VRF terminal-unit workflow and connect that terminal to an AirConditioner:VariableRefrigerantFlow outdoor/root system. The VRF outdoor/root system remains a separate object. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'heating', 'dx', 'vrf', 'terminal-unit', 'zone-equipment', 'curve', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_heating_dx_variable_refrigerant_flow(
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
            Field(description="Stable identifier for the new IB_CoilHeatingDXVariableRefrigerantFlow object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for the VRF DX heating coil availability schedule; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilHeatingDXVariableRefrigerantFlow field AvailabilitySchedule.'),
        ] = None,
        rated_total_heating_capacity: Annotated[
            float | str | None,
            Field(description='Optional gross rated heating capacity in watts for the VRF DX heating coil. Maps to Ironbug IB_CoilHeatingDXVariableRefrigerantFlow field RatedTotalHeatingCapacity.'),
        ] = None,
        rated_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional rated air flow rate across the VRF DX heating coil. Maps to Ironbug IB_CoilHeatingDXVariableRefrigerantFlow field RatedAirFlowRate.'),
        ] = None,
        heating_capacity_ratio_modifier_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for heating capacity ratio as a function of temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilHeatingDXVariableRefrigerantFlow field HeatingCapacityRatioModifierFunctionofTemperatureCurve.'),
        ] = None,
        heating_capacity_modifier_functionof_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for heating capacity as a function of air flow fraction; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilHeatingDXVariableRefrigerantFlow field HeatingCapacityModifierFunctionofFlowFractionCurve.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilHeatingDXVariableRefrigerantFlow field Name.'),
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
        """Create IB_CoilHeatingDXVariableRefrigerantFlow as a reviewed Ironbug Loop Objs authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if rated_total_heating_capacity is not None:
            source_fields['RatedTotalHeatingCapacity'] = rated_total_heating_capacity
        if rated_air_flow_rate is not None:
            source_fields['RatedAirFlowRate'] = rated_air_flow_rate
        if heating_capacity_ratio_modifier_functionof_temperature_curve_target is not None:
            source_field_targets['HeatingCapacityRatioModifierFunctionofTemperatureCurve'] = heating_capacity_ratio_modifier_functionof_temperature_curve_target
        if heating_capacity_modifier_functionof_flow_fraction_curve_target is not None:
            source_field_targets['HeatingCapacityModifierFunctionofFlowFractionCurve'] = heating_capacity_modifier_functionof_flow_fraction_curve_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilHeatingDXVariableRefrigerantFlow',
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
