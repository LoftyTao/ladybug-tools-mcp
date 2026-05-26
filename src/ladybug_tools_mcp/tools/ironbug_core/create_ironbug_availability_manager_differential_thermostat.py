'MCP tool for detailed_hvac_availability_manager_differential_thermostat.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object


def _target_identifier(target: dict[str, Any] | str, *, parameter_name: str) -> str:
    if isinstance(target, str):
        return target
    identifier = target.get("identifier")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError(f"{parameter_name} requires an Ironbug target identifier.")
    return identifier


def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_availability_manager_differential_thermostat tool.'

    @mcp.tool(
        name='availability_manager_differential_thermostat',
        description=(
            'Create IB_AvailabilityManagerDifferentialThermostat, an OpenStudio availability manager that compares hot and cold IB_NodeProbe targets before enabling loop or system operation. Use the returned target in an AirLoopHVAC, PlantLoop, or AvailabilityManagerList availability-manager slot. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={'ironbug', 'detailed-hvac', 'availability-manager', 'control', 'temperature', 'thermostat', 'air-loop', 'plant-loop', 'hvac', 'author'},
        timeout=20,
    )
    def create_ironbug_availability_manager_differential_thermostat(
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
            Field(description="Stable identifier for the new IB_AvailabilityManagerDifferentialThermostat object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        temperature_difference_on_limit: Annotated[
            float | None,
            Field(description='Optional temperature-difference on limit; maps to Ironbug IB_AvailabilityManagerDifferentialThermostat field TemperatureDifferenceOnLimit.'),
        ] = None,
        temperature_difference_off_limit: Annotated[
            float | None,
            Field(description='Optional temperature-difference off limit; maps to Ironbug IB_AvailabilityManagerDifferentialThermostat field TemperatureDifferenceOffLimit.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_AvailabilityManagerDifferentialThermostat field Name.'),
        ] = None,
        cold_probe_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional target for Ironbug component Parameter 'Cold Probe' "
                    "(IB_NodeProbe) on IB_AvailabilityManagerDifferentialThermostat."
                )
            ),
        ] = None,
        hot_probe_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional target for Ironbug component Parameter 'Hot Probe' "
                    "(IB_NodeProbe) on IB_AvailabilityManagerDifferentialThermostat."
                )
            ),
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
        """Create IB_AvailabilityManagerDifferentialThermostat as a reviewed Ironbug AvailabilityManagers authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        ib_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if cold_probe_target is not None:
            ib_properties["_nodeCID"] = _target_identifier(
                cold_probe_target,
                parameter_name="cold_probe_target",
            )
        if hot_probe_target is not None:
            ib_properties["_nodeHID"] = _target_identifier(
                hot_probe_target,
                parameter_name="hot_probe_target",
            )
        if temperature_difference_on_limit is not None:
            source_fields['TemperatureDifferenceOnLimit'] = temperature_difference_on_limit
        if temperature_difference_off_limit is not None:
            source_fields['TemperatureDifferenceOffLimit'] = temperature_difference_off_limit
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_AvailabilityManagerDifferentialThermostat',
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
