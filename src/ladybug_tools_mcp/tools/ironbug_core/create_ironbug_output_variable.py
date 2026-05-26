'MCP tool for detailed_hvac_output_variable.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_output_variable tool.'

    @mcp.tool(
        name='output_variable',
        description=(
            'Create IB_OutputVariable, an Ironbug reporting request for a specific EnergyPlus Output:Variable name and reporting frequency. Attach it to source-backed component tools through output_variable_names or component custom output-variable hooks when you need simulation outputs; this is not an Energy result reader, SQL query, or EMS output-variable definition. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'output-variable', 'outputs', 'reporting', 'energyplus', 'author', 'component'},
        timeout=20,
    )
    def create_ironbug_output_variable(
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
            Field(description="Stable identifier for the new IB_OutputVariable object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        variable_name: Annotated[
            str | None,
            Field(
                description="Optional EnergyPlus Output:Variable name to request, for example a component output from Ironbug's available output-variable list."
            ),
        ] = None,
        time_step: Annotated[
            str | None,
            Field(
                description="Optional reporting frequency string such as Detail, Hourly, Daily, Monthly, or RunPeriod; maps to IB_OutputVariable.TimeStep."
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_OutputVariable as a reviewed Ironbug Root authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if variable_name is not None:
            source_properties['VariableName'] = variable_name
        if time_step is not None:
            source_properties['TimeStep'] = time_step
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_OutputVariable',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            overwrite=overwrite,
        )
