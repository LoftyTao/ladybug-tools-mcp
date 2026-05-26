'MCP tool for detailed_hvac_zone_equipment_group.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_zone_equipment_group tool.'

    @mcp.tool(
        name='zone_equipment_group',
        description=(
            'Create IB_ZoneEquipmentGroup, an Ironbug zone-equipment aggregate '
            'for grouping multiple IB_ZoneEquipment targets before placement '
            'on an IB_ThermalZone. This maps to EnergyPlus/OpenStudio '
            'zone HVAC equipment-list and equipment-connections concepts, '
            'but it is not an air terminal and does not create Honeybee Room '
            'geometry. This tool authors Ironbug DetailedHVAC input only; run '
            'Energy simulation with the standard Ladybug Tools MCP Energy '
            'workflow after DetailedHVAC is applied. Returns target, '
            'summary_view, persistence_receipt, and report for downstream '
            'DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'zone-equipment', 'equipment-group', 'author', 'component'},
        timeout=20,
    )
    def create_ironbug_zone_equipment_group(
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
            Field(description="Stable identifier for the new IB_ZoneEquipmentGroup object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        zone_equipments_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description=(
                    "Optional list of IB_ZoneEquipment targets for the source "
                    "property ZoneEquipments (List<IB_ZoneEquipment>); pass "
                    "target dicts from compatible detailed_hvac_zone_equipment_* "
                    "tools or same-model identifiers. Do not pass air-terminal "
                    "targets here."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_ZoneEquipmentGroup as a reviewed zone-equipment aggregate."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        if zone_equipments_targets is not None:
            source_property_targets['ZoneEquipments'] = zone_equipments_targets
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ZoneEquipmentGroup',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            source_property_targets=source_property_targets or None,
            overwrite=overwrite,
        )
