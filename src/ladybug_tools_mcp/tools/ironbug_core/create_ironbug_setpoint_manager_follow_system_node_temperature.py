'MCP tool for detailed_hvac_setpoint_manager_follow_system_node_temperature.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object


def _target_identifier(target: dict[str, Any] | str) -> str:
    if isinstance(target, str):
        return target
    identifier = target.get("identifier")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("sensor_probe_target requires an Ironbug target identifier.")
    return identifier



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_setpoint_manager_follow_system_node_temperature tool.'

    @mcp.tool(
        name='setpoint_manager_follow_system_node_temperature',
        description=(
            'Create IB_SetpointManagerFollowSystemNodeTemperature / EnergyPlus SetpointManager:FollowSystemNodeTemperature. Pass a NodeProbe as sensor_probe_target so the manager follows that system node dry-bulb or wet-bulb temperature, applies an offset, and clips the resulting setpoint by optional limits. This authors Ironbug DetailedHVAC input only; it is not a NodeProbe creator, sensor result reader, plant component, or Energy simulation runner. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'setpoint', 'control', 'temperature', 'follow', 'node-probe', 'sensor', 'air-loop', 'plant-loop', 'author'},
        timeout=20,
    )
    def create_ironbug_setpoint_manager_follow_system_node_temperature(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json; for example garden_create['garden_root']."),
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
            Field(description="Stable identifier for the new IB_SetpointManagerFollowSystemNodeTemperature object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        control_variable: Annotated[
            str | None,
            Field(description='Optional controlled setpoint variable, typically Temperature, MaximumTemperature, or MinimumTemperature; maps to Ironbug field ControlVariable.'),
        ] = None,
        reference_temperature_type: Annotated[
            str | None,
            Field(description='Optional system-node reference temperature type, NodeDryBulb or NodeWetBulb; maps to Ironbug field ReferenceTemperatureType.'),
        ] = None,
        offset_temperature_difference: Annotated[
            float | None,
            Field(description='Optional temperature offset in deg C applied to the referenced system-node temperature; maps to Ironbug field OffsetTemperatureDifference.'),
        ] = None,
        maximum_limit_setpoint_temperature: Annotated[
            float | None,
            Field(description='Optional upper limit in deg C for the calculated setpoint; maps to Ironbug field MaximumLimitSetpointTemperature.'),
        ] = None,
        minimum_limit_setpoint_temperature: Annotated[
            float | None,
            Field(description='Optional lower limit in deg C for the calculated setpoint; maps to Ironbug field MinimumLimitSetpointTemperature.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio object name; maps to Ironbug IB_SetpointManagerFollowSystemNodeTemperature field Name.'),
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
        sensor_probe_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_NodeProbe target or identifier for the reference system node. "
                    "The probe stores the node tracking ID used by SetSensorNode."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug SetpointManager:FollowSystemNodeTemperature target."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        ib_properties: dict[str, Any] = {}
        if sensor_probe_target is not None:
            ib_properties["_nodeID"] = _target_identifier(sensor_probe_target)
        if control_variable is not None:
            source_fields['ControlVariable'] = control_variable
        if reference_temperature_type is not None:
            source_fields['ReferenceTemperatureType'] = reference_temperature_type
        if offset_temperature_difference is not None:
            source_fields['OffsetTemperatureDifference'] = offset_temperature_difference
        if maximum_limit_setpoint_temperature is not None:
            source_fields['MaximumLimitSetpointTemperature'] = maximum_limit_setpoint_temperature
        if minimum_limit_setpoint_temperature is not None:
            source_fields['MinimumLimitSetpointTemperature'] = minimum_limit_setpoint_temperature
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SetpointManagerFollowSystemNodeTemperature',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            ib_properties=ib_properties or None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
