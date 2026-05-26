'MCP tool for detailed_hvac_setpoint_manager_warmest.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_setpoint_manager_warmest tool.'

    @mcp.tool(
        name='setpoint_manager_warmest',
        description=(
            'Create IB_SetpointManagerWarmest, the Ironbug and EnergyPlus SetpointManager:Warmest object. It resets central forced-air cooling supply-air temperature from the cooling demand of the warmest zone with minimum and maximum temperature limits. Use it as an AirLoopHVAC cooling supply-air setpoint manager, not as a thermostat, cooling coil, load result reader, or Energy simulation runner. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'setpoint', 'control', 'temperature', 'air-loop', 'cooling', 'warmest', 'author'},
        timeout=20,
    )
    def create_ironbug_setpoint_manager_warmest(
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
            Field(description="Stable identifier for the new IB_SetpointManagerWarmest object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        maximum_setpoint_temperature: Annotated[
            float | None,
            Field(
                description="Optional maximum cooling supply-air setpoint temperature in deg C."
            ),
        ] = None,
        minimum_setpoint_temperature: Annotated[
            float | None,
            Field(
                description="Optional minimum cooling supply-air setpoint temperature in deg C."
            ),
        ] = None,
        strategy: Annotated[
            str | None,
            Field(description='Optional EnergyPlus strategy value, typically MaximumTemperature for SetpointManager:Warmest.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_SetpointManagerWarmest field Name.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug warmest-zone cooling setpoint manager."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if maximum_setpoint_temperature is not None:
            source_fields['MaximumSetpointTemperature'] = maximum_setpoint_temperature
        if minimum_setpoint_temperature is not None:
            source_fields['MinimumSetpointTemperature'] = minimum_setpoint_temperature
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if strategy is not None:
            source_fields['Strategy'] = strategy
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SetpointManagerWarmest',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            overwrite=overwrite,
        )
