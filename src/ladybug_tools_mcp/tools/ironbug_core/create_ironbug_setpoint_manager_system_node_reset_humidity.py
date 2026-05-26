'MCP tool for detailed_hvac_setpoint_manager_system_node_reset_humidity.'

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
    'Register the detailed_hvac_setpoint_manager_system_node_reset_humidity tool.'

    @mcp.tool(
        name='setpoint_manager_system_node_reset_humidity',
        description=(
            'Create IB_SetpointManagerSystemNodeResetHumidity, the Ironbug and EnergyPlus SetpointManager:SystemNodeReset:Humidity object. It places a humidity-ratio setpoint on a system node from a reset curve tied to an existing IB_NodeProbe reference node. Use it for humidity-ratio reset control, not as a humidistat, thermostat, output reader, or Energy simulation runner. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'setpoint', 'control', 'humidity-control', 'humidity-ratio', 'system-node-reset', 'node-probe', 'sensor', 'reset', 'air-loop', 'plant-loop', 'author'},
        timeout=20,
    )
    def create_ironbug_setpoint_manager_system_node_reset_humidity(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json for the Ironbug model."),
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
            Field(description="Stable identifier for the new IB_SetpointManagerSystemNodeResetHumidity object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        setpointat_low_reference_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional humidity-ratio setpoint at the low reference humidity ratio, in kgWater/kgDryAir.'),
        ] = None,
        setpointat_high_reference_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional humidity-ratio setpoint at the high reference humidity ratio, in kgWater/kgDryAir.'),
        ] = None,
        low_reference_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional low reference-node humidity ratio breakpoint, in kgWater/kgDryAir.'),
        ] = None,
        high_reference_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional high reference-node humidity ratio breakpoint, in kgWater/kgDryAir.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_SetpointManagerSystemNodeResetHumidity field Name.'),
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
                    "Optional IB_NodeProbe target used as the reference system node for "
                    "the humidity-ratio reset curve."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug system-node humidity reset setpoint manager."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        ib_properties: dict[str, Any] = {}
        if sensor_probe_target is not None:
            ib_properties["_nodeID"] = _target_identifier(sensor_probe_target)
        if setpointat_low_reference_humidity_ratio is not None:
            source_fields['SetpointatLowReferenceHumidityRatio'] = setpointat_low_reference_humidity_ratio
        if setpointat_high_reference_humidity_ratio is not None:
            source_fields['SetpointatHighReferenceHumidityRatio'] = setpointat_high_reference_humidity_ratio
        if low_reference_humidity_ratio is not None:
            source_fields['LowReferenceHumidityRatio'] = low_reference_humidity_ratio
        if high_reference_humidity_ratio is not None:
            source_fields['HighReferenceHumidityRatio'] = high_reference_humidity_ratio
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SetpointManagerSystemNodeResetHumidity',
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
