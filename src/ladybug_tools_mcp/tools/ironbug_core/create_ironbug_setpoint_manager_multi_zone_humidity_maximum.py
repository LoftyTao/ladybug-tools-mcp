'MCP tool for detailed_hvac_setpoint_manager_multi_zone_humidity_maximum.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_setpoint_manager_multi_zone_humidity_maximum tool.'

    @mcp.tool(
        name='setpoint_manager_multi_zone_humidity_maximum',
        description=(
            'Create IB_SetpointManagerMultiZoneHumidityMaximum / EnergyPlus SetpointManager:MultiZone:Humidity:Maximum for maximum humidity-ratio node setpoints across multiple zones. Use the humidity-ratio bounds to limit calculated setpoints before the manager is attached to HVAC system nodes. This authors Ironbug DetailedHVAC input only; it is not a thermostat, humidistat, humidity result reader, or Energy simulation runner. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'setpoint', 'control', 'humidity-control', 'humidity-ratio', 'multi-zone', 'author'},
        timeout=20,
    )
    def create_ironbug_setpoint_manager_multi_zone_humidity_maximum(
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
            Field(description="Stable identifier for the new IB_SetpointManagerMultiZoneHumidityMaximum object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        maximum_setpoint_humidity_ratio: Annotated[
            float | None,
            Field(
                description="Optional upper humidity-ratio limit in kgWater/kgDryAir; maps to Ironbug field MaximumSetpointHumidityRatio."
            ),
        ] = None,
        minimum_setpoint_humidity_ratio: Annotated[
            float | None,
            Field(
                description="Optional lower humidity-ratio limit in kgWater/kgDryAir; maps to Ironbug field MinimumSetpointHumidityRatio."
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio object name; maps to Ironbug IB_SetpointManagerMultiZoneHumidityMaximum field Name.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug SetpointManager:MultiZone:Humidity:Maximum target."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if maximum_setpoint_humidity_ratio is not None:
            source_fields['MaximumSetpointHumidityRatio'] = maximum_setpoint_humidity_ratio
        if minimum_setpoint_humidity_ratio is not None:
            source_fields['MinimumSetpointHumidityRatio'] = minimum_setpoint_humidity_ratio
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SetpointManagerMultiZoneHumidityMaximum',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            overwrite=overwrite,
        )
