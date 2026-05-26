'MCP tool for detailed_hvac_controller_mechanical_ventilation.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_controller_mechanical_ventilation tool.'

    @mcp.tool(
        name='controller_mechanical_ventilation',
        description=(
            'Create IB_ControllerMechanicalVentilation, the EnergyPlus Controller:MechanicalVentilation object used with Controller:OutdoorAir to calculate minimum outdoor air for an air loop. Use it for ASHRAE 62.1 ventilation-rate procedure, IAQP, demand-controlled ventilation, and system outdoor air method fields; pass the result to controller_outdoor_air.mechanical_ventilation_target. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'controller', 'mechanical-ventilation', 'ventilation', 'dcv', 'outdoor-air', 'air-loop', 'author'},
        timeout=20,
    )
    def create_ironbug_controller_mechanical_ventilation(
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
            Field(description="Stable identifier for the new IB_ControllerMechanicalVentilation object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        demand_controlled_ventilation: Annotated[
            bool | str | None,
            Field(
                description="Optional demand-controlled ventilation flag for varying outdoor air with occupancy or contaminant signals. Maps to Ironbug IB_ControllerMechanicalVentilation field DemandControlledVentilation."
            ),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for when mechanical ventilation calculations are available. Maps to Ironbug IB_ControllerMechanicalVentilation field AvailabilitySchedule.'),
        ] = None,
        demand_controlled_ventilation_no_fail: Annotated[
            str | float | int | bool | None,
            Field(description='Optional DemandControlledVentilationNoFail source value for explicit EnergyPlus DCV failure behavior. Maps to Ironbug IB_ControllerMechanicalVentilation field DemandControlledVentilationNoFail.'),
        ] = None,
        system_outdoor_air_method: Annotated[
            str | None,
            Field(description='Optional system outdoor air calculation method, such as ZoneSum, Standard62.1VentilationRateProcedure, or IndoorAirQualityProcedure. Maps to Ironbug IB_ControllerMechanicalVentilation field SystemOutdoorAirMethod.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_ControllerMechanicalVentilation field Name.'),
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
        """Create IB_ControllerMechanicalVentilation as a reviewed Ironbug Loop Objs authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if demand_controlled_ventilation is not None:
            source_fields['DemandControlledVentilation'] = demand_controlled_ventilation
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if demand_controlled_ventilation_no_fail is not None:
            source_fields['DemandControlledVentilationNoFail'] = demand_controlled_ventilation_no_fail
        if system_outdoor_air_method is not None:
            source_fields['SystemOutdoorAirMethod'] = system_outdoor_air_method
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ControllerMechanicalVentilation',
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
