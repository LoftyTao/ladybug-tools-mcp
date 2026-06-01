'MCP tool for detailed_hvac_energy_management_system_metered_output_variable.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_energy_management_system_metered_output_variable tool.'

    @mcp.tool(
        name='energy_management_system_metered_output_variable',
        description=(
            'Create IB_EnergyManagementSystemMeteredOutputVariable, a custom EMS output variable that is also included in EnergyPlus metering for a resource/end-use category. It reports an EMS variable or local program variable and can reference the EMS program that owns local scope; it does not create meters, validate units, execute Erl, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'ems', 'output-variable', 'meter', 'outputs', 'author', 'control'},
        timeout=20,
    )
    def create_ironbug_energy_management_system_metered_output_variable(
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
            Field(description="Stable identifier for the new IB_EnergyManagementSystemMeteredOutputVariable object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        update_frequency: Annotated[
            str | None,
            Field(description='EnergyPlus EMS output update frequency, typically ZoneTimestep or SystemTimestep.'),
        ] = None,
        resource_type: Annotated[
            str | None,
            Field(description='EnergyPlus metered resource type to aggregate, such as Electricity or Gas.'),
        ] = None,
        group_type: Annotated[
            str | None,
            Field(description='EnergyPlus meter group type for the custom metered output variable.'),
        ] = None,
        end_use_category: Annotated[
            str | None,
            Field(description='EnergyPlus end-use category used when the custom EMS quantity is added to meters.'),
        ] = None,
        end_use_subcategory: Annotated[
            str | None,
            Field(description='Optional EnergyPlus end-use subcategory for the custom metered output.'),
        ] = None,
        units: Annotated[
            str | None,
            Field(description='EnergyPlus units string for the reported EMS variable.'),
        ] = None,
        ems_variable_name: Annotated[
            str | None,
            Field(description='Name of the EMS variable or local Erl variable to expose as a metered output variable.'),
        ] = None,
        ems_program_or_subroutine_name: Annotated[
            str | None,
            Field(
                description=(
                    "Optional EMS Program or Subroutine name that owns the local Erl variable "
                    "referenced by ems_variable_name."
                )
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='User-facing EnergyPlus output variable name that will appear in reporting outputs.'),
        ] = None,
        output_variable_names: Annotated[
            list[str] | None,
            Field(
                description="Optional explicit output variable names to request from this metered EMS output object."
            ),
        ] = None,
        output_reporting_frequency: Annotated[
            Literal["Detail", "Hourly", "Daily", "Monthly", "RunPeriod"],
            Field(description="Reporting frequency used when requesting output_variable_names from EnergyPlus outputs."),
        ] = "Hourly",
        ems_sensor_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional EMS Sensor targets that this metered output depends on or should expose as custom sensors."),
        ] = None,
        ems_actuator_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional EMS Actuator targets that this metered output depends on or should expose as custom actuators."),
        ] = None,
        ems_internal_variable_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional EMS InternalVariable targets that this metered output depends on or should expose as custom internal variables."
            ),
        ] = None,
        ems_program_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional EMS Program target that owns a local Erl variable referenced by this metered output."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_EnergyManagementSystemMeteredOutputVariable as a reviewed Ironbug EMS authoring object."""

        child_targets = [
            ems_program_target,
        ]
        source_fields: dict[str, Any] = {}
        custom_attributes: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if update_frequency is not None:
            source_fields['UpdateFrequency'] = update_frequency
        if resource_type is not None:
            source_fields['ResourceType'] = resource_type
        if group_type is not None:
            source_fields['GroupType'] = group_type
        if end_use_category is not None:
            source_fields['EndUseCategory'] = end_use_category
        if end_use_subcategory is not None:
            source_fields['EndUseSubcategory'] = end_use_subcategory
        if units is not None:
            source_fields['Units'] = units
        if ems_variable_name is not None:
            source_fields['EMSVariableName'] = ems_variable_name
        if ems_program_or_subroutine_name is not None:
            custom_attributes['EMSProgramOrSubroutineName'] = (
                ems_program_or_subroutine_name
            )
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_EnergyManagementSystemMeteredOutputVariable',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            custom_attributes=custom_attributes or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            child_targets=child_targets if any(item is not None for item in child_targets) else None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
