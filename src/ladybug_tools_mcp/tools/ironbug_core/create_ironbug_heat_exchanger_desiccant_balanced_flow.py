'MCP tool for detailed_hvac_heat_exchanger_desiccant_balanced_flow.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_heat_exchanger_desiccant_balanced_flow tool.'

    @mcp.tool(
        name='heat_exchanger_desiccant_balanced_flow',
        description=(
            'Create IB_HeatExchangerDesiccantBalancedFlow, an EnergyPlus HeatExchanger:Desiccant:BalancedFlow air-loop desiccant heat exchanger for process/regeneration air streams. Use it for enhanced dehumidification or outdoor-air systems with schedule and economizer lockout fields; this is not the performance-data child, an air-to-air sensible/latent exchanger, or a hydronic plant heat exchanger. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'air-loop',
            'heat-exchanger',
            'desiccant',
            'dehumidification',
            'humidity-control',
            'ventilation',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_heat_exchanger_desiccant_balanced_flow(
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
            Field(description="Stable identifier for the new IB_HeatExchangerDesiccantBalancedFlow object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier controlling when the desiccant heat exchanger can operate; maps to AvailabilitySchedule.'),
        ] = None,
        economizer_lockout: Annotated[
            bool | str | None,
            Field(description='Optional economizer lockout flag for suspending desiccant wheel operation during air-side economizer or high-humidity control; maps to EconomizerLockout.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus object name for this balanced-flow desiccant heat exchanger; maps to Name.'),
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
        """Create IB_HeatExchangerDesiccantBalancedFlow as a reviewed Ironbug LoopObjs / AirLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if economizer_lockout is not None:
            source_fields['EconomizerLockout'] = economizer_lockout
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_HeatExchangerDesiccantBalancedFlow',
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
