'MCP tool for detailed_hvac_energy_management_system_curve_variable.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_energy_management_system_curve_variable tool.'

    @mcp.tool(
        name='energy_management_system_curve_variable',
        description=(
            'Create IB_EnergyManagementSystemCurveVariable, an EMS CurveOrTableIndexVariable that exposes a referenced Ironbug curve or table index to Erl for @CurveValue calls. This tool links an existing curve target; it does not create the curve, evaluate curve values, validate Erl, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'ems', 'curve', 'performance', 'control', 'author'},
        timeout=20,
    )
    def create_ironbug_energy_management_system_curve_variable(
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
            Field(description="Stable identifier for the new IB_EnergyManagementSystemCurveVariable object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="EMS curve/table index Erl variable name; no spaces or special characters because it becomes a global EMS variable."
            ),
        ] = None,
        curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Existing Ironbug curve/table target whose EnergyPlus index should be exposed to Erl for @CurveValue."
            ),
        ] = None,
        tag_id: Annotated[
            str | None,
            Field(description='Optional EMS tracking tag ID from the Ironbug _tagID component parameter.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_EnergyManagementSystemCurveVariable as a reviewed Ironbug EMS authoring object."""

        custom_attributes: dict[str, Any] = {}
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if tag_id is not None:
            custom_attributes['Comment'] = tag_id
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        if name is not None:
            source_properties['Name'] = name
        if curve_target is not None:
            source_property_targets['Curve'] = curve_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_EnergyManagementSystemCurveVariable',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            source_property_targets=source_property_targets or None,
            custom_attributes=custom_attributes or None,
            overwrite=overwrite,
        )
