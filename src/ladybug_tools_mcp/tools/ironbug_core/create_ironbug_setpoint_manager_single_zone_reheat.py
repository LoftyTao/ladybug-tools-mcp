'MCP tool for detailed_hvac_setpoint_manager_single_zone_reheat.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_setpoint_manager_single_zone_reheat tool.'

    @mcp.tool(
        name='setpoint_manager_single_zone_reheat',
        description=(
            'Create IB_SetpointManagerSingleZoneReheat, the Ironbug and EnergyPlus SetpointManager:SingleZone:Reheat object. It uses one IB_ThermalZone control zone to calculate supply-air temperature setpoints from zone load, inlet flow, and zone temperature; the EnergyPlus object is not limited to reheat coils. Use it as an air-loop setpoint manager, not as a thermostat, zone equipment object, coil, result reader, or Energy simulation runner. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'setpoint', 'control', 'temperature', 'single-zone', 'thermal-zone', 'reheat', 'air-loop', 'author'},
        timeout=20,
    )
    def create_ironbug_setpoint_manager_single_zone_reheat(
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
            Field(description="Stable identifier for the new IB_SetpointManagerSingleZoneReheat object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        maximum_supply_air_temperature: Annotated[
            float | None,
            Field(
                description="Optional maximum supply-air temperature setpoint limit in deg C."
            ),
        ] = None,
        minimum_supply_air_temperature: Annotated[
            float | None,
            Field(
                description="Optional minimum supply-air temperature setpoint limit in deg C."
            ),
        ] = None,
        control_variable: Annotated[
            str | None,
            Field(description='Optional ControlVariable value; maps to Ironbug IB_SetpointManagerSingleZoneReheat field ControlVariable.'),
        ] = None,
        control_zone_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description=(
                    "Optional IB_ThermalZone control-zone target; pass one thermal-zone target dict "
                    "or identifier so Ironbug can bind the zone node during OpenStudio conversion."
                )
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_SetpointManagerSingleZoneReheat field Name.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug single-zone reheat setpoint manager."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if maximum_supply_air_temperature is not None:
            source_fields['MaximumSupplyAirTemperature'] = maximum_supply_air_temperature
        if minimum_supply_air_temperature is not None:
            source_fields['MinimumSupplyAirTemperature'] = minimum_supply_air_temperature
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if control_variable is not None:
            source_fields['ControlVariable'] = control_variable
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SetpointManagerSingleZoneReheat',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            child_targets=control_zone_targets if control_zone_targets is not None else None,
            overwrite=overwrite,
        )
