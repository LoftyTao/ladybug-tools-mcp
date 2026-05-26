'MCP tool for detailed_hvac_coil_cooling_dx_variable_refrigerant_flow.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_cooling_dx_variable_refrigerant_flow tool.'

    @mcp.tool(
        name='coil_cooling_dx_variable_refrigerant_flow',
        description=(
            'Create IB_CoilCoolingDXVariableRefrigerantFlow, an OpenStudio/EnergyPlus Coil:Cooling:DX:VariableRefrigerantFlow object for a VRF terminal unit cooling coil. Use the returned target with the advanced VRF terminal-unit workflow and connect that terminal to an AirConditioner:VariableRefrigerantFlow outdoor system; this is not the VRF outdoor unit itself. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'cooling', 'dx', 'vrf', 'terminal-unit', 'zone-equipment', 'curve', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_cooling_dx_variable_refrigerant_flow(
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
            Field(description="Stable identifier for the new IB_CoilCoolingDXVariableRefrigerantFlow object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for VRF DX cooling coil availability; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXVariableRefrigerantFlow field AvailabilitySchedule.'),
        ] = None,
        rated_total_cooling_capacity: Annotated[
            float | str | None,
            Field(description='Optional gross rated total cooling capacity in watts or Autosize; maps to Ironbug IB_CoilCoolingDXVariableRefrigerantFlow field RatedTotalCoolingCapacity.'),
        ] = None,
        rated_sensible_heat_ratio: Annotated[
            float | str | None,
            Field(description='Optional gross rated sensible heat ratio; maps to Ironbug IB_CoilCoolingDXVariableRefrigerantFlow field RatedSensibleHeatRatio.'),
        ] = None,
        rated_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional rated terminal-unit air flow rate in m3/s or Autosize; maps to Ironbug IB_CoilCoolingDXVariableRefrigerantFlow field RatedAirFlowRate.'),
        ] = None,
        cooling_capacity_ratio_modifier_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for VRF cooling-capacity ratio versus temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXVariableRefrigerantFlow field CoolingCapacityRatioModifierFunctionofTemperatureCurve.'),
        ] = None,
        cooling_capacity_modifier_curve_functionof_flow_fraction_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for VRF cooling-capacity modifier versus air-flow fraction; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXVariableRefrigerantFlow field CoolingCapacityModifierCurveFunctionofFlowFraction.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilCoolingDXVariableRefrigerantFlow field Name.'),
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
        """Create IB_CoilCoolingDXVariableRefrigerantFlow as a reviewed Ironbug Loop Objs authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if rated_total_cooling_capacity is not None:
            source_fields['RatedTotalCoolingCapacity'] = rated_total_cooling_capacity
        if rated_sensible_heat_ratio is not None:
            source_fields['RatedSensibleHeatRatio'] = rated_sensible_heat_ratio
        if rated_air_flow_rate is not None:
            source_fields['RatedAirFlowRate'] = rated_air_flow_rate
        if cooling_capacity_ratio_modifier_functionof_temperature_curve_target is not None:
            source_field_targets['CoolingCapacityRatioModifierFunctionofTemperatureCurve'] = cooling_capacity_ratio_modifier_functionof_temperature_curve_target
        if cooling_capacity_modifier_curve_functionof_flow_fraction_target is not None:
            source_field_targets['CoolingCapacityModifierCurveFunctionofFlowFraction'] = cooling_capacity_modifier_curve_functionof_flow_fraction_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilCoolingDXVariableRefrigerantFlow',
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
