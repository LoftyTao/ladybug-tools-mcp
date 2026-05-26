'MCP tool for detailed_hvac_energy_management_system_construction_index_variable.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_energy_management_system_construction_index_variable tool.'

    @mcp.tool(
        name='energy_management_system_construction_index_variable',
        description=(
            'Create IB_EnergyManagementSystemConstructionIndexVariable, an EMS Erl variable containing the EnergyPlus construction index for a named Construction object. Use it with EMS actuators for Surface / Construction State overrides; this tool does not create the Construction, attach the actuator, validate Erl, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'ems', 'construction', 'control', 'author'},
        timeout=20,
    )
    def create_ironbug_energy_management_system_construction_index_variable(
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
            Field(description="Stable identifier for the new IB_EnergyManagementSystemConstructionIndexVariable object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="EMS construction index Erl variable name; no spaces or arithmetic symbols because it becomes a global EMS variable."
            ),
        ] = None,
        construction_id: Annotated[
            str | None,
            Field(
                description="Name of an existing EnergyPlus/OpenStudio Construction object whose index should be exposed to Erl."
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_EnergyManagementSystemConstructionIndexVariable as a reviewed Ironbug EMS authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        source_properties: dict[str, Any] = {}
        if construction_id is not None:
            source_properties['ConstructionID'] = construction_id
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_EnergyManagementSystemConstructionIndexVariable',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            overwrite=overwrite,
        )
