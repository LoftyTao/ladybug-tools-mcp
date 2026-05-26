'MCP tool for detailed_hvac_setpoint_manager_single_zone_heating.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_setpoint_manager_single_zone_heating tool.'

    @mcp.tool(
        name='setpoint_manager_single_zone_heating',
        description=(
            'Create IB_SetpointManagerSingleZoneHeating / EnergyPlus SetpointManager:SingleZone:Heating. The manager uses one IB_ThermalZone control zone to determine heating supply-air temperature, then applies optional minimum and maximum supply-air temperature limits. This authors Ironbug DetailedHVAC input only; it is not a zone thermostat, heating coil, humidity manager, result reader, or Energy simulation runner. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'setpoint', 'control', 'temperature', 'single-zone', 'thermal-zone', 'heating', 'air-loop', 'author'},
        timeout=20,
    )
    def create_ironbug_setpoint_manager_single_zone_heating(
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
            Field(description="Stable identifier for the new IB_SetpointManagerSingleZoneHeating object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        minimum_supply_air_temperature: Annotated[
            float | None,
            Field(description='Optional minimum heating supply-air temperature in deg C allowed by this manager; maps to Ironbug field MinimumSupplyAirTemperature.'),
        ] = None,
        maximum_supply_air_temperature: Annotated[
            float | None,
            Field(description='Optional maximum heating supply-air temperature in deg C allowed by this manager; maps to Ironbug field MaximumSupplyAirTemperature.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio object name; maps to Ironbug IB_SetpointManagerSingleZoneHeating field Name.'),
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
        control_zone_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description=(
                    "Optional IB_ThermalZone target list for the single control zone. "
                    "Ironbug stores the zone name and binds it after loop nodes are saved."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug SetpointManager:SingleZone:Heating target."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if minimum_supply_air_temperature is not None:
            source_fields['MinimumSupplyAirTemperature'] = minimum_supply_air_temperature
        if maximum_supply_air_temperature is not None:
            source_fields['MaximumSupplyAirTemperature'] = maximum_supply_air_temperature
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SetpointManagerSingleZoneHeating',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            child_targets=control_zone_targets if control_zone_targets is not None else None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
