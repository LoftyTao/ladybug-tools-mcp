'MCP tool for detailed_hvac_energy_management_system_actuator.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_energy_management_system_actuator tool.'

    @mcp.tool(
        name='energy_management_system_actuator',
        description=(
            'Create IB_EnergyManagementSystemActuator, an EnergyPlus EMS actuator mapping an Erl variable to an actuated component unique name, component type, and control type. Use actuator names and control types from EnergyPlus EDD output; this tool does not discover available actuators, execute EMS programs, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'ems', 'actuator', 'control', 'author'},
        timeout=20,
    )
    def create_ironbug_energy_management_system_actuator(
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
            Field(description="Stable identifier for the new IB_EnergyManagementSystemActuator object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        actuated_component_control_type: Annotated[
            str | None,
            Field(
                description="EnergyPlus actuator control type from EDD output, such as Availability Status, Temperature Setpoint, or Schedule Value."
            ),
        ] = None,
        actuated_component_type: Annotated[
            str | None,
            Field(
                description="EnergyPlus actuated component type from EDD output, such as AirLoopHVAC, System Node Setpoint, or Schedule:Constant."
            ),
        ] = None,
        tag_id: Annotated[
            str | None,
            Field(description='Optional EMS actuator tracking tag ID from the Ironbug _tagID component parameter.'),
        ] = None,
        type: Annotated[
            str | None,
            Field(description='Grasshopper _type alias for the EnergyPlus actuated component type; prefer actuated_component_type when writing new calls.'),
        ] = None,
        control_type: Annotated[
            str | None,
            Field(description='Grasshopper _controlType alias for the EnergyPlus actuator control type; prefer actuated_component_control_type when writing new calls.'),
        ] = None,
        space: Annotated[
            str | float | int | bool | None,
            Field(description='Optional actuated component unique name or legacy Ironbug Space value used to identify the controlled object.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='EMS actuator Erl variable name; no spaces or arithmetic symbols because it becomes a global Erl variable.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_EnergyManagementSystemActuator as a reviewed Ironbug EMS authoring object."""

        custom_attributes: dict[str, Any] = {}
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if tag_id is not None:
            custom_attributes['Comment'] = tag_id
        if type is not None:
            source_fields['ActuatedComponentType'] = type
        if control_type is not None:
            source_fields['ActuatedComponentControlType'] = control_type
        if actuated_component_control_type is not None:
            source_fields['ActuatedComponentControlType'] = actuated_component_control_type
        if actuated_component_type is not None:
            source_fields['ActuatedComponentType'] = actuated_component_type
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if space is not None:
            source_fields['Space'] = space
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_EnergyManagementSystemActuator',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            custom_attributes=custom_attributes or None,
            overwrite=overwrite,
        )
