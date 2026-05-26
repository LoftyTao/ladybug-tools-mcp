'MCP tool for detailed_hvac_energy_management_system_program.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_energy_management_system_program tool.'

    @mcp.tool(
        name='energy_management_system_program',
        description=(
            'Create IB_EnergyManagementSystemProgram, the EnergyPlus EMS program container for EnergyPlus Runtime Language (Erl) lines. A ProgramCallingManager controls when this program runs; this tool records Erl source only and does not validate Erl syntax, create sensors or actuators, choose a calling point, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'ems', 'program', 'control', 'author'},
        timeout=20,
    )
    def create_ironbug_energy_management_system_program(
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
            Field(description="Stable identifier for the new IB_EnergyManagementSystemProgram object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="Unique Erl program name referenced by ProgramCallingManager objects; no spaces or arithmetic symbols."
            ),
        ] = None,
        body: Annotated[
            str | float | int | bool | None,
            Field(
                description="EnergyPlus Runtime Language program body. Use valid Erl lines; this wrapper stores the body but does not parse it."
            ),
        ] = None,
        lines: Annotated[
            str | float | int | bool | None,
            Field(description='Optional Erl program lines alias for the EnergyManagementSystem:Program line fields.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_EnergyManagementSystemProgram as a reviewed Ironbug EMS authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if body is not None:
            source_fields['Body'] = body
        source_properties: dict[str, Any] = {}
        if lines is not None:
            source_fields['Lines'] = lines
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_EnergyManagementSystemProgram',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            overwrite=overwrite,
        )
