'MCP tool for detailed_hvac_energy_management_system_sensor.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_energy_management_system_sensor tool.'

    @mcp.tool(
        name='energy_management_system_sensor',
        description=(
            'Create IB_EnergyManagementSystemSensor, an EnergyPlus EMS sensor that maps an Erl variable to an EnergyPlus output variable or meter. Use output variable names from eplusout.rdd and meter names from eplusout.mdd; this tool does not discover output names, create reporting requests, validate Erl, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'ems', 'sensor', 'outputs', 'control', 'author'},
        timeout=20,
    )
    def create_ironbug_energy_management_system_sensor(
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
            Field(description="Stable identifier for the new IB_EnergyManagementSystemSensor object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="EMS sensor Erl variable name; no spaces because it becomes a global Erl variable."
            ),
        ] = None,
        output_variable_or_meter_name: Annotated[
            str | float | int | bool | None,
            Field(
                description="EnergyPlus output variable or meter name to map to the sensor, usually from eplusout.rdd or eplusout.mdd."
            ),
        ] = None,
        key_name: Annotated[
            str | float | int | bool | None,
            Field(
                description="EnergyPlus output variable key name, such as a zone, node, or schedule name; omit for weather variables and meters."
            ),
        ] = None,
        tag_id: Annotated[
            str | None,
            Field(description='Optional EMS tracking tag ID from the Ironbug _tagID component parameter.'),
        ] = None,
        output_variable: Annotated[
            str | float | int | bool | None,
            Field(description='EnergyPlus output variable name from eplusout.rdd; use output_variable_or_meter_name for the unified field.'),
        ] = None,
        output_meter: Annotated[
            str | float | int | bool | None,
            Field(description='EnergyPlus output meter name from eplusout.mdd; use output_variable_or_meter_name for the unified field.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_EnergyManagementSystemSensor as a reviewed Ironbug EMS authoring object."""

        custom_attributes: dict[str, Any] = {}
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if tag_id is not None:
            custom_attributes['Comment'] = tag_id
        if name is not None:
            source_fields['Name'] = name
        if output_variable_or_meter_name is not None:
            source_fields['OutputVariableOrMeterName'] = output_variable_or_meter_name
        if key_name is not None:
            source_fields['KeyName'] = key_name
        source_properties: dict[str, Any] = {}
        if output_variable is not None:
            source_fields['OutputVariable'] = output_variable
        if output_meter is not None:
            source_fields['OutputMeter'] = output_meter
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_EnergyManagementSystemSensor',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            custom_attributes=custom_attributes or None,
            overwrite=overwrite,
        )
