'MCP tool for detailed_hvac_plant_component_user_defined.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_plant_component_user_defined tool.'

    @mcp.tool(
        name='plant_component_user_defined',
        description=(
            'Create IB_PlantComponentUserDefined, an EnergyPlus PlantComponent:UserDefined custom plant component backed by EMS actuators, Erl programs, and calling managers. Use it only when supplying the required plant loading/flow modes and EMS control targets; this is not the generic DetailedHVAC component fallback, an external-code runner, a result reader, or an Energy run. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'plant-loop', 'plant-component', 'user-defined', 'custom-component', 'ems', 'actuator', 'program', 'author'},
        timeout=20,
    )
    def create_ironbug_plant_component_user_defined(
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
            Field(description="Stable identifier for the new IB_PlantComponentUserDefined object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        plant_loading_mode: Annotated[
            str | None,
            Field(description='Optional plant connection loading mode such as DemandsLoad or MeetsLoadWithNominalCapacity; maps to PlantLoadingMode.'),
        ] = None,
        plant_loop_flow_request_mode: Annotated[
            str | None,
            Field(description='Optional plant loop flow request mode such as NeedsFlowIfLoopOn or ReceivesWhateverFlowAvailable; maps to PlantLoopFlowRequestMode.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus object name for this PlantComponent:UserDefined custom plant component; maps to Name.'),
        ] = None,
        output_variable_names: Annotated[
            list[str] | None,
            Field(
                description="Optional explicit Ironbug output variable names for this object."
            ),
        ] = None,
        output_reporting_frequency: Annotated[
            Literal["Detail", "Hourly", "Daily", "Monthly", "RunPeriod"],
            Field(description="Reporting frequency used for output_variable_names."),
        ] = "Hourly",
        ems_sensor_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional IB_EnergyManagementSystemSensor targets for CustomSensors."),
        ] = None,
        ems_actuator_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional IB_EnergyManagementSystemActuator targets for CustomActuators."),
        ] = None,
        ems_internal_variable_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_EnergyManagementSystemInternalVariable targets for CustomInternalVariables."
            ),
        ] = None,
        plant_init_program_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_EnergyManagementSystemProgram target or same-model identifier "
                    "for the PlantComponent:UserDefined initialization program."
                )
            ),
        ] = None,
        plant_init_program_calling_manager_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_EnergyManagementSystemProgramCallingManager target or same-model identifier "
                    "for the initialization program calling manager."
                )
            ),
        ] = None,
        design_volume_flow_rate_actuator_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_EnergyManagementSystemActuator target for the design volume flow rate actuator."
                )
            ),
        ] = None,
        maximum_loading_capacity_actuator_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_EnergyManagementSystemActuator target for the maximum loading capacity actuator."
                )
            ),
        ] = None,
        maximum_mass_flow_rate_actuator_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_EnergyManagementSystemActuator target for the maximum mass flow rate actuator."
                )
            ),
        ] = None,
        minimum_loading_capacity_actuator_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_EnergyManagementSystemActuator target for the minimum loading capacity actuator."
                )
            ),
        ] = None,
        minimum_mass_flow_rate_actuator_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_EnergyManagementSystemActuator target for the minimum mass flow rate actuator."
                )
            ),
        ] = None,
        optimal_loading_capacity_actuator_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_EnergyManagementSystemActuator target for the optimal loading capacity actuator."
                )
            ),
        ] = None,
        outlet_temperature_actuator_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_EnergyManagementSystemActuator target for the outlet temperature actuator."
                )
            ),
        ] = None,
        mass_flow_rate_actuator_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_EnergyManagementSystemActuator target for the mass flow rate actuator."
                )
            ),
        ] = None,
        plant_simulation_program_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_EnergyManagementSystemProgram target or same-model identifier "
                    "for the PlantComponent:UserDefined simulation program."
                )
            ),
        ] = None,
        plant_simulation_program_calling_manager_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_EnergyManagementSystemProgramCallingManager target or same-model identifier "
                    "for the simulation program calling manager."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug PlantComponent:UserDefined object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if plant_loading_mode is not None:
            source_fields['PlantLoadingMode'] = plant_loading_mode
        if plant_loop_flow_request_mode is not None:
            source_fields['PlantLoopFlowRequestMode'] = plant_loop_flow_request_mode
        ib_property_targets = {
            '_dvfrActuator': design_volume_flow_rate_actuator_target,
            '_mxlcActuator': maximum_loading_capacity_actuator_target,
            '_mxfrActuator': maximum_mass_flow_rate_actuator_target,
            '_mlcActuator': minimum_loading_capacity_actuator_target,
            '_mmfrActuator': minimum_mass_flow_rate_actuator_target,
            '_olcActuator': optimal_loading_capacity_actuator_target,
            '_plantInitializationProgram': plant_init_program_target,
            '_plantInitializationProgramCallingManager': plant_init_program_calling_manager_target,
            '_otActuator': outlet_temperature_actuator_target,
            '_mfrActuator': mass_flow_rate_actuator_target,
            '_plantSimulationProgram': plant_simulation_program_target,
            '_plantSimulationProgramCallingManager': plant_simulation_program_calling_manager_target,
        }
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_PlantComponentUserDefined',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            ib_property_targets=ib_property_targets or None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
