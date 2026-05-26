'MCP tool for detailed_hvac_energy_management_system_internal_variable.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_energy_management_system_internal_variable tool.'

    @mcp.tool(
        name='energy_management_system_internal_variable',
        description=(
            'Create IB_EnergyManagementSystemInternalVariable, an EnergyPlus EMS internal variable for static model data such as zone area or air volume. Use internal data key/type values from EnergyPlus EDD/EIO output or a referenced host object; this tool does not discover internal data names, validate Erl, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'ems', 'internal-variable', 'control', 'author'},
        timeout=20,
    )
    def create_ironbug_energy_management_system_internal_variable(
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
            Field(description="Stable identifier for the new IB_EnergyManagementSystemInternalVariable object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="EMS internal variable Erl name; no spaces or arithmetic symbols because it becomes a global EMS variable."
            ),
        ] = None,
        internal_data_type: Annotated[
            str | None,
            Field(
                description="EnergyPlus internal data type from EDD/EIO output, such as Zone Air Volume."
            ),
        ] = None,
        host_obj_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Ironbug host object target used to derive the internal data index key name when writing the EMS object."
            ),
        ] = None,
        tag_id: Annotated[
            str | None,
            Field(description='Optional EMS tracking tag ID from the Ironbug _tagID component parameter.'),
        ] = None,
        internal_data_index_key_name: Annotated[
            str | None,
            Field(description='EnergyPlus internal data index key name, often the user-defined name of a zone or model object.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_EnergyManagementSystemInternalVariable as a reviewed Ironbug EMS authoring object."""

        custom_attributes: dict[str, Any] = {}
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if tag_id is not None:
            custom_attributes['Comment'] = tag_id
        if name is not None:
            source_fields['Name'] = name
        if internal_data_type is not None:
            source_fields['InternalDataType'] = internal_data_type
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        if internal_data_index_key_name is not None:
            source_fields['InternalDataIndexKeyName'] = internal_data_index_key_name
        if host_obj_target is not None:
            source_property_targets['HostObj'] = host_obj_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_EnergyManagementSystemInternalVariable',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            source_property_targets=source_property_targets or None,
            custom_attributes=custom_attributes or None,
            overwrite=overwrite,
        )
