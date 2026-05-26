'MCP tool for detailed_hvac_energy_management_system.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_energy_management_system tool.'

    @mcp.tool(
        name='energy_management_system',
        description=(
            'Create IB_EnergyManagementSystem, the Ironbug root assembly for EnergyPlus EMS actuators, sensors, EMS variables, and ProgramCallingManager objects. Use this after authoring or referencing EMS child targets; it groups EMS authoring input but does not discover EDD/RDD sensor or actuator names, validate Erl code, choose calling-point timing, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'ems', 'control', 'author'},
        timeout=20,
    )
    def create_ironbug_energy_management_system(
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
            Field(description="Stable identifier for the new IB_EnergyManagementSystem object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        actuators_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_EnergyManagementSystemActuator targets that map Erl variables to EnergyPlus actuator component/control types."
            ),
        ] = None,
        sensors_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_EnergyManagementSystemSensor targets that map Erl variables to EnergyPlus output variables or meters."
            ),
        ] = None,
        program_calling_managers_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_EnergyManagementSystemProgramCallingManager targets that call EMS programs at EnergyPlus calling points."
            ),
        ] = None,
        variables_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional EMS variable targets such as construction index, curve/table index, internal variable, or metered output variable objects."
            ),
        ] = None,
        actuators_identifiers: Annotated[
            list[str] | None,
            Field(description='Optional inline IB_EnergyManagementSystemActuator identifiers for IB_EnergyManagementSystem.Actuators.'),
        ] = None,
        actuators_name_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline Erl variable names for Actuators child objects; EnergyPlus EMS names cannot contain spaces.'),
        ] = None,
        actuators_actuated_component_control_type_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline actuator control types, such as a Schedule Value or Temperature Setpoint entry from EnergyPlus EDD output.'),
        ] = None,
        actuators_actuated_component_type_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline actuator component types, such as AirLoopHVAC, System Node Setpoint, or Schedule:Constant from EnergyPlus EDD output.'),
        ] = None,
        actuators_space_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline actuated component unique names or legacy Ironbug Space values for Actuators child objects.'),
        ] = None,
        program_cln_managers_identifiers: Annotated[
            list[str] | None,
            Field(description='Optional inline IB_EnergyManagementSystemProgramCallingManager identifiers for IB_EnergyManagementSystem.ProgramClnManagers.'),
        ] = None,
        program_cln_managers_name_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline names for ProgramCallingManager child objects.'),
        ] = None,
        program_cln_managers_calling_point_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline EnergyPlus EMS calling points, such as BeginNewEnvironment or AfterPredictorAfterHVACManagers.'),
        ] = None,
        sensors_identifiers: Annotated[
            list[str] | None,
            Field(description='Optional inline IB_EnergyManagementSystemSensor identifiers for IB_EnergyManagementSystem.Sensors.'),
        ] = None,
        sensors_name_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline Erl variable names for Sensor child objects; names become global EMS variables.'),
        ] = None,
        sensors_key_name_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline output variable key names, such as a zone, node, or schedule name; omit for weather variables and meters.'),
        ] = None,
        sensors_output_variable_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline EnergyPlus output variable names from eplusout.rdd for Sensor child objects.'),
        ] = None,
        sensors_output_meter_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline EnergyPlus output meter names from eplusout.mdd for Sensor child objects.'),
        ] = None,
        sensors_output_variable_or_meter_name_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline EnergyPlus output variable or meter names when using the unified Sensor field.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_EnergyManagementSystem as a reviewed Ironbug Root authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        inline_source_property_children: dict[str, Any] = {}
        if actuators_targets is not None:
            source_property_targets['Actuators'] = actuators_targets
        if sensors_targets is not None:
            source_property_targets['Sensors'] = sensors_targets
        if program_calling_managers_targets is not None:
            source_property_targets['ProgramClnManagers'] = program_calling_managers_targets
        if variables_targets is not None:
            source_property_targets['Variables'] = variables_targets
        inline_actuators_fields: dict[str, Any] = {}
        inline_actuators_field_targets: dict[str, Any] = {}
        if actuators_name_values is not None:
            inline_actuators_fields['Name'] = actuators_name_values
        if actuators_actuated_component_control_type_values is not None:
            inline_actuators_fields['ActuatedComponentControlType'] = actuators_actuated_component_control_type_values
        if actuators_actuated_component_type_values is not None:
            inline_actuators_fields['ActuatedComponentType'] = actuators_actuated_component_type_values
        if actuators_space_values is not None:
            inline_actuators_fields['Space'] = actuators_space_values
        if actuators_identifiers is not None or inline_actuators_fields or inline_actuators_field_targets:
            if actuators_targets is not None:
                raise ValueError("Provide either actuators_targets or inline actuators_* parameters, not both.")
            inline_source_property_children['Actuators'] = {
                'source_class': 'IB_EnergyManagementSystemActuator',
                'is_list': True,
                'identifiers': actuators_identifiers,
                'source_fields': inline_actuators_fields,
                'source_field_targets': inline_actuators_field_targets,
            }
        inline_program_cln_managers_fields: dict[str, Any] = {}
        inline_program_cln_managers_field_targets: dict[str, Any] = {}
        if program_cln_managers_name_values is not None:
            inline_program_cln_managers_fields['Name'] = program_cln_managers_name_values
        if program_cln_managers_calling_point_values is not None:
            inline_program_cln_managers_fields['CallingPoint'] = program_cln_managers_calling_point_values
        if program_cln_managers_identifiers is not None or inline_program_cln_managers_fields or inline_program_cln_managers_field_targets:
            if program_calling_managers_targets is not None:
                raise ValueError("Provide either program_calling_managers_targets or inline program_cln_managers_* parameters, not both.")
            inline_source_property_children['ProgramClnManagers'] = {
                'source_class': 'IB_EnergyManagementSystemProgramCallingManager',
                'is_list': True,
                'identifiers': program_cln_managers_identifiers,
                'source_fields': inline_program_cln_managers_fields,
                'source_field_targets': inline_program_cln_managers_field_targets,
            }
        inline_sensors_fields: dict[str, Any] = {}
        inline_sensors_field_targets: dict[str, Any] = {}
        if sensors_name_values is not None:
            inline_sensors_fields['Name'] = sensors_name_values
        if sensors_key_name_values is not None:
            inline_sensors_fields['KeyName'] = sensors_key_name_values
        if sensors_output_variable_values is not None:
            inline_sensors_fields['OutputVariable'] = sensors_output_variable_values
        if sensors_output_meter_values is not None:
            inline_sensors_fields['OutputMeter'] = sensors_output_meter_values
        if sensors_output_variable_or_meter_name_values is not None:
            inline_sensors_fields['OutputVariableOrMeterName'] = sensors_output_variable_or_meter_name_values
        if sensors_identifiers is not None or inline_sensors_fields or inline_sensors_field_targets:
            if sensors_targets is not None:
                raise ValueError("Provide either sensors_targets or inline sensors_* parameters, not both.")
            inline_source_property_children['Sensors'] = {
                'source_class': 'IB_EnergyManagementSystemSensor',
                'is_list': True,
                'identifiers': sensors_identifiers,
                'source_fields': inline_sensors_fields,
                'source_field_targets': inline_sensors_field_targets,
            }
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_EnergyManagementSystem',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            source_property_targets=source_property_targets or None,
            inline_source_property_children=inline_source_property_children or None,
            overwrite=overwrite,
        )
