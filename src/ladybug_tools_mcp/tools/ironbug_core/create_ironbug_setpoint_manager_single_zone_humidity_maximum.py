'MCP tool for detailed_hvac_setpoint_manager_single_zone_humidity_maximum.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_setpoint_manager_single_zone_humidity_maximum tool.'

    @mcp.tool(
        name='setpoint_manager_single_zone_humidity_maximum',
        description=(
            'Create IB_SetpointManagerSingleZoneHumidityMaximum / EnergyPlus SetpointManager:SingleZone:Humidity:Maximum. The manager uses one IB_ThermalZone control zone air node for maximum humidity-ratio control, usually with ZoneControl:Humidistat and humidity-capable equipment. This authors Ironbug DetailedHVAC input only; it is not a humidistat, zone thermostat, humidity result reader, or Energy simulation runner. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'setpoint', 'control', 'humidity-control', 'humidity-ratio', 'humidistat', 'single-zone', 'thermal-zone', 'author'},
        timeout=20,
    )
    def create_ironbug_setpoint_manager_single_zone_humidity_maximum(
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
            Field(description="Stable identifier for the new IB_SetpointManagerSingleZoneHumidityMaximum object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        control_variable: Annotated[
            str | None,
            Field(description='Optional controlled humidity variable for the single-zone humidity manager; maps to Ironbug field ControlVariable.'),
        ] = None,
        control_zone_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description=(
                    "Optional IB_ThermalZone target list for the humidity control zone. "
                    "Ironbug stores the zone name and binds the zone air node after loop nodes are saved."
                )
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio object name; maps to Ironbug IB_SetpointManagerSingleZoneHumidityMaximum field Name.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug SetpointManager:SingleZone:Humidity:Maximum target."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if control_variable is not None:
            source_fields['ControlVariable'] = control_variable
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SetpointManagerSingleZoneHumidityMaximum',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            child_targets=control_zone_targets if control_zone_targets is not None else None,
            overwrite=overwrite,
        )
