'MCP tool for detailed_hvac_controller_water_coil.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_controller_water_coil tool.'

    @mcp.tool(
        name='controller_water_coil',
        description=(
            'Create IB_ControllerWaterCoil, the EnergyPlus Controller:WaterCoil object used by advanced hot-water or chilled-water coil wrappers to modulate water flow at an actuated node. Use it for control variable, action, actuator flow limits, and convergence tolerance; attach it through the advanced CoilCoolingWater or CoilHeatingWater controller input. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'controller', 'water-coil', 'coil', 'chilled-water', 'hot-water', 'setpoint', 'plant-loop', 'air-loop', 'author'},
        timeout=20,
    )
    def create_ironbug_controller_water_coil(
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
            Field(description="Stable identifier for the new IB_ControllerWaterCoil object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        control_variable: Annotated[
            str | None,
            Field(description='Optional controlled node variable for the water coil controller, such as Temperature, HumidityRatio, TemperatureAndHumidityRatio, or Flow. Maps to Ironbug IB_ControllerWaterCoil field ControlVariable.'),
        ] = None,
        action: Annotated[
            str | None,
            Field(description='Optional controller action, usually Normal for heating coils or Reverse for cooling coils. Maps to Ironbug IB_ControllerWaterCoil field Action.'),
        ] = None,
        actuator_variable: Annotated[
            str | None,
            Field(description='Optional actuator variable for the controlled water coil; EnergyPlus Controller:WaterCoil typically uses Flow. Maps to Ironbug IB_ControllerWaterCoil field ActuatorVariable.'),
        ] = None,
        controller_convergence_tolerance: Annotated[
            float | str | None,
            Field(description='Optional convergence tolerance for matching the controlled node setpoint, usually a small temperature or humidity-ratio offset. Maps to Ironbug IB_ControllerWaterCoil field ControllerConvergenceTolerance.'),
        ] = None,
        maximum_actuated_flow: Annotated[
            float | str | None,
            Field(description='Optional maximum water flow through the controlled coil, in m3/s or an autosize-style value accepted by Ironbug. Maps to Ironbug IB_ControllerWaterCoil field MaximumActuatedFlow.'),
        ] = None,
        minimum_actuated_flow: Annotated[
            float | None,
            Field(description='Optional minimum water flow through the controlled coil, often 0 for shutoff. Maps to Ironbug IB_ControllerWaterCoil field MinimumActuatedFlow.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_ControllerWaterCoil field Name.'),
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
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_ControllerWaterCoil as a reviewed Ironbug Loop Objs authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if control_variable is not None:
            source_fields['ControlVariable'] = control_variable
        if action is not None:
            source_fields['Action'] = action
        if actuator_variable is not None:
            source_fields['ActuatorVariable'] = actuator_variable
        if controller_convergence_tolerance is not None:
            source_fields['ControllerConvergenceTolerance'] = controller_convergence_tolerance
        if maximum_actuated_flow is not None:
            source_fields['MaximumActuatedFlow'] = maximum_actuated_flow
        if minimum_actuated_flow is not None:
            source_fields['MinimumActuatedFlow'] = minimum_actuated_flow
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ControllerWaterCoil',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
