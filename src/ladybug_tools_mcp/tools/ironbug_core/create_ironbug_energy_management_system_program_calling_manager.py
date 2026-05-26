'MCP tool for detailed_hvac_energy_management_system_program_calling_manager.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_energy_management_system_program_calling_manager tool.'

    @mcp.tool(
        name='energy_management_system_program_calling_manager',
        description=(
            'Create IB_EnergyManagementSystemProgramCallingManager, the EnergyPlus EMS object that calls one or more EMS programs at a named EnergyPlus model calling point and in listed order. Use it to schedule existing or inline EMS Program targets; this tool does not validate calling-point suitability, execute Erl, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'ems', 'program', 'calling-manager', 'control', 'author'},
        timeout=20,
    )
    def create_ironbug_energy_management_system_program_calling_manager(
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
            Field(description="Stable identifier for the new IB_EnergyManagementSystemProgramCallingManager object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="Unique name for this EMS ProgramCallingManager."
            ),
        ] = None,
        calling_point: Annotated[
            str | float | int | bool | None,
            Field(
                description="EnergyPlus EMS calling point such as BeginNewEnvironment, AfterPredictorAfterHVACManagers, or InsideHVACSystemIterationLoop."
            ),
        ] = None,
        programs_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional EMS Program targets to run at this calling point, in listed order."
            ),
        ] = None,
        programs_identifiers: Annotated[
            list[str] | None,
            Field(description='Optional inline IB_EnergyManagementSystemProgram identifiers for IB_EnergyManagementSystemProgramCallingManager.Programs.'),
        ] = None,
        programs_name_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline Erl program names for Program child objects referenced by this calling manager.'),
        ] = None,
        programs_body_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline EnergyPlus Runtime Language bodies for Program child objects.'),
        ] = None,
        programs_lines_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline Erl line-field alias for Program child objects.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_EnergyManagementSystemProgramCallingManager as a reviewed Ironbug EMS authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if calling_point is not None:
            source_fields['CallingPoint'] = calling_point
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        inline_source_property_children: dict[str, Any] = {}
        if programs_targets is not None:
            source_property_targets['Programs'] = programs_targets
        inline_programs_fields: dict[str, Any] = {}
        inline_programs_field_targets: dict[str, Any] = {}
        if programs_name_values is not None:
            inline_programs_fields['Name'] = programs_name_values
        if programs_body_values is not None:
            inline_programs_fields['Body'] = programs_body_values
        if programs_lines_values is not None:
            inline_programs_fields['Lines'] = programs_lines_values
        if programs_identifiers is not None or inline_programs_fields or inline_programs_field_targets:
            if programs_targets is not None:
                raise ValueError("Provide either programs_targets or inline programs_* parameters, not both.")
            inline_source_property_children['Programs'] = {
                'source_class': 'IB_EnergyManagementSystemProgram',
                'is_list': True,
                'identifiers': programs_identifiers,
                'source_fields': inline_programs_fields,
                'source_field_targets': inline_programs_field_targets,
            }
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_EnergyManagementSystemProgramCallingManager',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            source_property_targets=source_property_targets or None,
            inline_source_property_children=inline_source_property_children or None,
            overwrite=overwrite,
        )
