'MCP tool for detailed_hvac_no_air_loop.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_no_air_loop tool.'

    @mcp.tool(
        name='no_air_loop',
        description=(
            'Create IB_NoAirLoop, an Ironbug air-loop placeholder for ThermalZones served only by zone equipment and no central AirLoopHVAC. Pass existing IB_ThermalZone targets or inline thermal-zone fields, then include this object in the HVACSystem AirLoops list; this is not a plant loop, ideal-air template, or room geometry tool. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'air-loop',
            'no-air-loop',
            'thermal-zone',
            'zone-equipment',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_no_air_loop(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, for example garden_create['garden_root']."),
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
            Field(description="Stable identifier for the new IB_NoAirLoop object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        thermal_zones_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_ThermalZone targets or same-model identifiers for zones that have zone equipment but no central air loop."
            ),
        ] = None,
        thermal_zones_identifiers: Annotated[
            list[str] | None,
            Field(description='Optional inline IB_ThermalZone identifiers to create ThermalZones inside this NoAirLoop object.'),
        ] = None,
        thermal_zones_name_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline Name value for IB_ThermalZone; maps to Ironbug IB_NoAirLoop.ThermalZones child field Name.'),
        ] = None,
        thermal_zones_multiplier_values: Annotated[
            list[int | None] | None,
            Field(description='Optional inline Multiplier value for IB_ThermalZone; maps to Ironbug IB_NoAirLoop.ThermalZones child field Multiplier.'),
        ] = None,
        thermal_zones_ceiling_height_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline CeilingHeight value for IB_ThermalZone; maps to Ironbug IB_NoAirLoop.ThermalZones child field CeilingHeight.'),
        ] = None,
        thermal_zones_volume_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline Volume value for IB_ThermalZone; maps to Ironbug IB_NoAirLoop.ThermalZones child field Volume.'),
        ] = None,
        thermal_zones_zone_inside_convection_algorithm_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline ZoneInsideConvectionAlgorithm value for IB_ThermalZone; maps to Ironbug IB_NoAirLoop.ThermalZones child field ZoneInsideConvectionAlgorithm.'),
        ] = None,
        thermal_zones_zone_outside_convection_algorithm_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline ZoneOutsideConvectionAlgorithm value for IB_ThermalZone; maps to Ironbug IB_NoAirLoop.ThermalZones child field ZoneOutsideConvectionAlgorithm.'),
        ] = None,
        thermal_zones_zone_conditioning_equipment_list_name_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline ZoneConditioningEquipmentListName value for IB_ThermalZone; maps to Ironbug IB_NoAirLoop.ThermalZones child field ZoneConditioningEquipmentListName.'),
        ] = None,
        thermal_zones_thermostat_setpoint_dual_setpoint_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline ThermostatSetpointDualSetpoint value for IB_ThermalZone; maps to Ironbug IB_NoAirLoop.ThermalZones child field ThermostatSetpointDualSetpoint.'),
        ] = None,
        thermal_zones_zone_control_humidistat_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline ZoneControlHumidistat value for IB_ThermalZone; maps to Ironbug IB_NoAirLoop.ThermalZones child field ZoneControlHumidistat.'),
        ] = None,
        thermal_zones_zone_control_contaminant_controller_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline ZoneControlContaminantController value for IB_ThermalZone; maps to Ironbug IB_NoAirLoop.ThermalZones child field ZoneControlContaminantController.'),
        ] = None,
        thermal_zones_fractionof_zone_controlledby_primary_daylighting_control_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline FractionofZoneControlledbyPrimaryDaylightingControl value for IB_ThermalZone; maps to Ironbug IB_NoAirLoop.ThermalZones child field FractionofZoneControlledbyPrimaryDaylightingControl.'),
        ] = None,
        thermal_zones_fractionof_zone_controlledby_secondary_daylighting_control_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline FractionofZoneControlledbySecondaryDaylightingControl value for IB_ThermalZone; maps to Ironbug IB_NoAirLoop.ThermalZones child field FractionofZoneControlledbySecondaryDaylightingControl.'),
        ] = None,
        thermal_zones_daylighting_controls_availability_schedule_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for DaylightingControlsAvailabilitySchedule; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_NoAirLoop.ThermalZones child IB_ThermalZone field DaylightingControlsAvailabilitySchedule.'),
        ] = None,
        thermal_zones_rendering_color_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline RenderingColor value for IB_ThermalZone; maps to Ironbug IB_NoAirLoop.ThermalZones child field RenderingColor.'),
        ] = None,
        thermal_zones_use_ideal_air_loads_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline IB_ThermalZone UseIdealAirLoads flag inside this NoAirLoop; this does not create a Honeybee ideal-air HVAC template.'),
        ] = None,
        thermal_zones_load_distribution_scheme_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline LoadDistributionScheme value for IB_ThermalZone; maps to Ironbug IB_NoAirLoop.ThermalZones child field LoadDistributionScheme.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_NoAirLoop as a reviewed Ironbug Loops authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        inline_source_property_children: dict[str, Any] = {}
        if thermal_zones_targets is not None:
            source_property_targets['ThermalZones'] = thermal_zones_targets
        inline_thermal_zones_fields: dict[str, Any] = {}
        inline_thermal_zones_field_targets: dict[str, Any] = {}
        if thermal_zones_name_values is not None:
            inline_thermal_zones_fields['Name'] = thermal_zones_name_values
        if thermal_zones_multiplier_values is not None:
            inline_thermal_zones_fields['Multiplier'] = thermal_zones_multiplier_values
        if thermal_zones_ceiling_height_values is not None:
            inline_thermal_zones_fields['CeilingHeight'] = thermal_zones_ceiling_height_values
        if thermal_zones_volume_values is not None:
            inline_thermal_zones_fields['Volume'] = thermal_zones_volume_values
        if thermal_zones_zone_inside_convection_algorithm_values is not None:
            inline_thermal_zones_fields['ZoneInsideConvectionAlgorithm'] = thermal_zones_zone_inside_convection_algorithm_values
        if thermal_zones_zone_outside_convection_algorithm_values is not None:
            inline_thermal_zones_fields['ZoneOutsideConvectionAlgorithm'] = thermal_zones_zone_outside_convection_algorithm_values
        if thermal_zones_zone_conditioning_equipment_list_name_values is not None:
            inline_thermal_zones_fields['ZoneConditioningEquipmentListName'] = thermal_zones_zone_conditioning_equipment_list_name_values
        if thermal_zones_thermostat_setpoint_dual_setpoint_values is not None:
            inline_thermal_zones_fields['ThermostatSetpointDualSetpoint'] = thermal_zones_thermostat_setpoint_dual_setpoint_values
        if thermal_zones_zone_control_humidistat_values is not None:
            inline_thermal_zones_fields['ZoneControlHumidistat'] = thermal_zones_zone_control_humidistat_values
        if thermal_zones_zone_control_contaminant_controller_values is not None:
            inline_thermal_zones_fields['ZoneControlContaminantController'] = thermal_zones_zone_control_contaminant_controller_values
        if thermal_zones_fractionof_zone_controlledby_primary_daylighting_control_values is not None:
            inline_thermal_zones_fields['FractionofZoneControlledbyPrimaryDaylightingControl'] = thermal_zones_fractionof_zone_controlledby_primary_daylighting_control_values
        if thermal_zones_fractionof_zone_controlledby_secondary_daylighting_control_values is not None:
            inline_thermal_zones_fields['FractionofZoneControlledbySecondaryDaylightingControl'] = thermal_zones_fractionof_zone_controlledby_secondary_daylighting_control_values
        if thermal_zones_daylighting_controls_availability_schedule_targets is not None:
            inline_thermal_zones_field_targets['DaylightingControlsAvailabilitySchedule'] = thermal_zones_daylighting_controls_availability_schedule_targets
        if thermal_zones_rendering_color_values is not None:
            inline_thermal_zones_fields['RenderingColor'] = thermal_zones_rendering_color_values
        if thermal_zones_use_ideal_air_loads_values is not None:
            inline_thermal_zones_fields['UseIdealAirLoads'] = thermal_zones_use_ideal_air_loads_values
        if thermal_zones_load_distribution_scheme_values is not None:
            inline_thermal_zones_fields['LoadDistributionScheme'] = thermal_zones_load_distribution_scheme_values
        if thermal_zones_identifiers is not None or inline_thermal_zones_fields or inline_thermal_zones_field_targets:
            if thermal_zones_targets is not None:
                raise ValueError("Provide either thermal_zones_targets or inline thermal_zones_* parameters, not both.")
            inline_source_property_children['ThermalZones'] = {
                'source_class': 'IB_ThermalZone',
                'is_list': True,
                'identifiers': thermal_zones_identifiers,
                'source_fields': inline_thermal_zones_fields,
                'source_field_targets': inline_thermal_zones_field_targets,
            }
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_NoAirLoop',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            source_property_targets=source_property_targets or None,
            inline_source_property_children=inline_source_property_children or None,
            overwrite=overwrite,
        )

