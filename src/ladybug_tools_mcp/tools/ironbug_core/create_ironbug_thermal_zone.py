'MCP tool for detailed_hvac_thermal_zone.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    add_ironbug_thermal_zone_equipment,
    set_ironbug_thermal_zone_air_terminal,
    set_ironbug_thermal_zone_return_plenum,
    set_ironbug_thermal_zone_sizing_zone,
    set_ironbug_thermal_zone_supply_plenum,
)


def _target_sequence(
    value: dict[str, Any] | str | list[dict[str, Any] | str] | None,
) -> list[dict[str, Any] | str]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _single_target_from_sequence(
    label: str,
    value: list[dict[str, Any] | str] | None,
) -> dict[str, Any] | str | None:
    if not value:
        return None
    if len(value) != 1:
        raise ValueError(f"{label} accepts exactly one target for a single IB_ThermalZone.")
    return value[0]


def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_thermal_zone tool.'

    @mcp.tool(
        name='thermal_zone',
        description=(
            'Create IB_ThermalZone, an Ironbug DetailedHVAC thermal-zone '
            'target for equipment placement, air-terminal binding, sizing-zone '
            'binding, and supply/return plenum links. This is the HVAC '
            'placement object used by Ironbug DetailedHVAC and is only a '
            'partial downstream mapping to EnergyPlus/OpenStudio thermal-zone '
            'concepts; it does not create Honeybee Room geometry. Bind air '
            'terminals through air_terminal or air_terminals_targets; bind '
            'zone equipment through zone_equipments_targets; bind an '
            'IB_SizingZone target through sizing_zone_target when non-default '
            'sizing is needed. Returns target, summary_view, '
            'persistence_receipt, and report for downstream DetailedHVAC '
            'assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'thermal-zone', 'zone-equipment', 'author'},
        timeout=20,
    )
    def create_ironbug_thermal_zone(
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
            Field(description="Stable identifier for the new IB_ThermalZone object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description=(
                    "Optional room-matching IB_ThermalZone Name. This is "
                    "stored as the Ironbug ThermalZone source Name custom "
                    "attribute so the DetailedHVAC bridge can match a "
                    "Honeybee Room identifier; it does not create or edit "
                    "Honeybee Room geometry."
                )
            ),
        ] = None,
        multiplier: Annotated[
            int | None,
            Field(
                description="Sets Ironbug field Multiplier for IB_ThermalZone."
            ),
        ] = None,
        zone_inside_convection_algorithm: Annotated[
            str | None,
            Field(
                description="Sets Ironbug field ZoneInsideConvectionAlgorithm for IB_ThermalZone."
            ),
        ] = None,
        zone_outside_convection_algorithm: Annotated[
            str | None,
            Field(
                description="Sets Ironbug field ZoneOutsideConvectionAlgorithm for IB_ThermalZone."
            ),
        ] = None,
        air_terminal: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional direct binding to an IB_AirTerminal target or "
                    "component identifier for this IB_ThermalZone."
                )
            ),
        ] = None,
        sizing_zone_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional direct binding to an IB_SizingZone target. "
                    "When provided, the ThermalZone's SizingZone is replaced with the "
                    "target. When omitted, the Ironbug source default IB_SizingZone is "
                    "preserved."
                )
            ),
        ] = None,
        allow_multi_air_loops: Annotated[
            bool | None,
            Field(
                description=(
                    "Optional bool. When true, the thermal zone may be added to "
                    "more than one air loop. Defaults to false in the Ironbug source."
                )
            ),
        ] = None,
        is_air_terminal_before_zone_equipments: Annotated[
            bool | None,
            Field(
                description=(
                    "Optional bool. Controls whether the air terminal is connected "
                    "to the air loop before zone equipment is added to the zone. "
                    "Defaults to false in the Ironbug source."
                )
            ),
        ] = None,
        ceiling_height: Annotated[
            float | None,
            Field(description='Optional CeilingHeight value; maps to Ironbug IB_ThermalZone field CeilingHeight.'),
        ] = None,
        volume: Annotated[
            float | None,
            Field(description='Optional Volume value; maps to Ironbug IB_ThermalZone field Volume.'),
        ] = None,
        zone_conditioning_equipment_list_name: Annotated[
            str | None,
            Field(description='Optional ZoneConditioningEquipmentListName value; maps to Ironbug IB_ThermalZone field ZoneConditioningEquipmentListName.'),
        ] = None,
        thermostat_setpoint_dual_setpoint: Annotated[
            str | float | int | bool | None,
            Field(description='Optional ThermostatSetpointDualSetpoint value; maps to Ironbug IB_ThermalZone field ThermostatSetpointDualSetpoint.'),
        ] = None,
        fractionof_zone_controlledby_primary_daylighting_control: Annotated[
            float | None,
            Field(description='Optional FractionofZoneControlledbyPrimaryDaylightingControl value; maps to Ironbug IB_ThermalZone field FractionofZoneControlledbyPrimaryDaylightingControl.'),
        ] = None,
        fractionof_zone_controlledby_secondary_daylighting_control: Annotated[
            float | None,
            Field(description='Optional FractionofZoneControlledbySecondaryDaylightingControl value; maps to Ironbug IB_ThermalZone field FractionofZoneControlledbySecondaryDaylightingControl.'),
        ] = None,
        daylighting_controls_availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for DaylightingControlsAvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Maps to Ironbug IB_ThermalZone field DaylightingControlsAvailabilitySchedule.'),
        ] = None,
        rendering_color: Annotated[
            str | float | int | bool | None,
            Field(description='Optional RenderingColor value; maps to Ironbug IB_ThermalZone field RenderingColor.'),
        ] = None,
        use_ideal_air_loads: Annotated[
            bool | str | None,
            Field(description='Optional UseIdealAirLoads value; maps to Ironbug IB_ThermalZone field UseIdealAirLoads.'),
        ] = None,
        load_distribution_scheme: Annotated[
            str | float | int | bool | None,
            Field(description='Optional LoadDistributionScheme value; maps to Ironbug IB_ThermalZone field LoadDistributionScheme.'),
        ] = None,
        zone_control_humidistat: Annotated[
            str | float | int | bool | None,
            Field(description='Optional ZoneControlHumidistat value; maps to Ironbug IB_ThermalZone field ZoneControlHumidistat.'),
        ] = None,
        zone_control_contaminant_controller: Annotated[
            str | float | int | bool | None,
            Field(description='Optional ZoneControlContaminantController value; maps to Ironbug IB_ThermalZone field ZoneControlContaminantController.'),
        ] = None,
        return_plenum_identifier: Annotated[
            str | None,
            Field(description='Optional inline IB_ThermalZone identifiers for IB_ThermalZone.ReturnPlenum.'),
        ] = None,
        return_plenum_name: Annotated[
            str | None,
            Field(description='Optional inline Name value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.ReturnPlenum child field Name.'),
        ] = None,
        return_plenum_multiplier: Annotated[
            int | None,
            Field(description='Optional inline Multiplier value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.ReturnPlenum child field Multiplier.'),
        ] = None,
        return_plenum_ceiling_height: Annotated[
            float | None,
            Field(description='Optional inline CeilingHeight value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.ReturnPlenum child field CeilingHeight.'),
        ] = None,
        return_plenum_volume: Annotated[
            float | None,
            Field(description='Optional inline Volume value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.ReturnPlenum child field Volume.'),
        ] = None,
        return_plenum_zone_inside_convection_algorithm: Annotated[
            str | None,
            Field(description='Optional inline ZoneInsideConvectionAlgorithm value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.ReturnPlenum child field ZoneInsideConvectionAlgorithm.'),
        ] = None,
        return_plenum_zone_outside_convection_algorithm: Annotated[
            str | None,
            Field(description='Optional inline ZoneOutsideConvectionAlgorithm value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.ReturnPlenum child field ZoneOutsideConvectionAlgorithm.'),
        ] = None,
        return_plenum_zone_conditioning_equipment_list_name: Annotated[
            str | None,
            Field(description='Optional inline ZoneConditioningEquipmentListName value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.ReturnPlenum child field ZoneConditioningEquipmentListName.'),
        ] = None,
        return_plenum_thermostat_setpoint_dual_setpoint: Annotated[
            str | float | int | bool | None,
            Field(description='Optional inline ThermostatSetpointDualSetpoint value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.ReturnPlenum child field ThermostatSetpointDualSetpoint.'),
        ] = None,
        return_plenum_zone_control_humidistat: Annotated[
            str | float | int | bool | None,
            Field(description='Optional inline ZoneControlHumidistat value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.ReturnPlenum child field ZoneControlHumidistat.'),
        ] = None,
        return_plenum_zone_control_contaminant_controller: Annotated[
            str | float | int | bool | None,
            Field(description='Optional inline ZoneControlContaminantController value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.ReturnPlenum child field ZoneControlContaminantController.'),
        ] = None,
        return_plenum_fractionof_zone_controlledby_primary_daylighting_control: Annotated[
            float | None,
            Field(description='Optional inline FractionofZoneControlledbyPrimaryDaylightingControl value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.ReturnPlenum child field FractionofZoneControlledbyPrimaryDaylightingControl.'),
        ] = None,
        return_plenum_fractionof_zone_controlledby_secondary_daylighting_control: Annotated[
            float | None,
            Field(description='Optional inline FractionofZoneControlledbySecondaryDaylightingControl value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.ReturnPlenum child field FractionofZoneControlledbySecondaryDaylightingControl.'),
        ] = None,
        return_plenum_daylighting_controls_availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional inline IB_Schedule target for DaylightingControlsAvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Maps to Ironbug IB_ThermalZone.ReturnPlenum child field DaylightingControlsAvailabilitySchedule.'),
        ] = None,
        return_plenum_rendering_color: Annotated[
            str | float | int | bool | None,
            Field(description='Optional inline RenderingColor value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.ReturnPlenum child field RenderingColor.'),
        ] = None,
        return_plenum_use_ideal_air_loads: Annotated[
            bool | str | None,
            Field(description='Optional inline UseIdealAirLoads value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.ReturnPlenum child field UseIdealAirLoads.'),
        ] = None,
        return_plenum_load_distribution_scheme: Annotated[
            str | float | int | bool | None,
            Field(description='Optional inline LoadDistributionScheme value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.ReturnPlenum child field LoadDistributionScheme.'),
        ] = None,
        supply_plenum_identifier: Annotated[
            str | None,
            Field(description='Optional inline IB_ThermalZone identifiers for IB_ThermalZone.SupplyPlenum.'),
        ] = None,
        supply_plenum_name: Annotated[
            str | None,
            Field(description='Optional inline Name value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.SupplyPlenum child field Name.'),
        ] = None,
        supply_plenum_multiplier: Annotated[
            int | None,
            Field(description='Optional inline Multiplier value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.SupplyPlenum child field Multiplier.'),
        ] = None,
        supply_plenum_ceiling_height: Annotated[
            float | None,
            Field(description='Optional inline CeilingHeight value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.SupplyPlenum child field CeilingHeight.'),
        ] = None,
        supply_plenum_volume: Annotated[
            float | None,
            Field(description='Optional inline Volume value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.SupplyPlenum child field Volume.'),
        ] = None,
        supply_plenum_zone_inside_convection_algorithm: Annotated[
            str | None,
            Field(description='Optional inline ZoneInsideConvectionAlgorithm value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.SupplyPlenum child field ZoneInsideConvectionAlgorithm.'),
        ] = None,
        supply_plenum_zone_outside_convection_algorithm: Annotated[
            str | None,
            Field(description='Optional inline ZoneOutsideConvectionAlgorithm value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.SupplyPlenum child field ZoneOutsideConvectionAlgorithm.'),
        ] = None,
        supply_plenum_zone_conditioning_equipment_list_name: Annotated[
            str | None,
            Field(description='Optional inline ZoneConditioningEquipmentListName value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.SupplyPlenum child field ZoneConditioningEquipmentListName.'),
        ] = None,
        supply_plenum_thermostat_setpoint_dual_setpoint: Annotated[
            str | float | int | bool | None,
            Field(description='Optional inline ThermostatSetpointDualSetpoint value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.SupplyPlenum child field ThermostatSetpointDualSetpoint.'),
        ] = None,
        supply_plenum_zone_control_humidistat: Annotated[
            str | float | int | bool | None,
            Field(description='Optional inline ZoneControlHumidistat value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.SupplyPlenum child field ZoneControlHumidistat.'),
        ] = None,
        supply_plenum_zone_control_contaminant_controller: Annotated[
            str | float | int | bool | None,
            Field(description='Optional inline ZoneControlContaminantController value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.SupplyPlenum child field ZoneControlContaminantController.'),
        ] = None,
        supply_plenum_fractionof_zone_controlledby_primary_daylighting_control: Annotated[
            float | None,
            Field(description='Optional inline FractionofZoneControlledbyPrimaryDaylightingControl value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.SupplyPlenum child field FractionofZoneControlledbyPrimaryDaylightingControl.'),
        ] = None,
        supply_plenum_fractionof_zone_controlledby_secondary_daylighting_control: Annotated[
            float | None,
            Field(description='Optional inline FractionofZoneControlledbySecondaryDaylightingControl value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.SupplyPlenum child field FractionofZoneControlledbySecondaryDaylightingControl.'),
        ] = None,
        supply_plenum_daylighting_controls_availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional inline IB_Schedule target for DaylightingControlsAvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Maps to Ironbug IB_ThermalZone.SupplyPlenum child field DaylightingControlsAvailabilitySchedule.'),
        ] = None,
        supply_plenum_rendering_color: Annotated[
            str | float | int | bool | None,
            Field(description='Optional inline RenderingColor value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.SupplyPlenum child field RenderingColor.'),
        ] = None,
        supply_plenum_use_ideal_air_loads: Annotated[
            bool | str | None,
            Field(description='Optional inline UseIdealAirLoads value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.SupplyPlenum child field UseIdealAirLoads.'),
        ] = None,
        supply_plenum_load_distribution_scheme: Annotated[
            str | float | int | bool | None,
            Field(description='Optional inline LoadDistributionScheme value for IB_ThermalZone; maps to Ironbug IB_ThermalZone.SupplyPlenum child field LoadDistributionScheme.'),
        ] = None,
        output_variable_names: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional EnergyPlus output variable names to request for this "
                    "thermal zone."
                )
            ),
        ] = None,
        output_reporting_frequency: Annotated[
            str | None,
            Field(
                description=(
                    "Optional EnergyPlus reporting frequency for the output variable "
                    "requests (e.g. 'Timestep', 'Hourly', 'Daily')."
                )
            ),
        ] = None,
        ems_sensor_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Optional list of EnergyPlus EMS sensor binding targets for "
                    "this thermal zone."
                )
            ),
        ] = None,
        ems_actuator_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Optional list of EnergyPlus EMS actuator binding targets for "
                    "this thermal zone."
                )
            ),
        ] = None,
        ems_internal_variable_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Optional list of EnergyPlus EMS internal variable binding targets "
                    "for this thermal zone."
                )
            ),
        ] = None,
        supply_plenum_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description=(
                    "Optional single IB_ThermalZone target for the source "
                    "property SupplyPlenum; pass a target dict or same-model "
                    "identifier. This links a plenum ThermalZone and does not "
                    "create Honeybee Room geometry."
                )
            ),
        ] = None,
        return_plenum_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description=(
                    "Optional single IB_ThermalZone target for the source "
                    "property ReturnPlenum; pass a target dict or same-model "
                    "identifier. This links a plenum ThermalZone and does not "
                    "create Honeybee Room geometry."
                )
            ),
        ] = None,
        air_terminals_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description=(
                    "Optional single IB_AirTerminal target for the source "
                    "property AirTerminal; pass a target dict from a compatible "
                    "detailed_hvac_air_terminal_* tool or a same-model identifier."
                )
            ),
        ] = None,
        zone_equipments_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description=(
                    "Optional list of IB_ZoneEquipment targets for the source "
                    "property ZoneEquipments; pass target dicts from compatible "
                    "detailed_hvac_zone_equipment_* tools, "
                    "detailed_hvac_zone_equipment_group, or same-model identifiers."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_ThermalZone as a reviewed DetailedHVAC placement target."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        custom_attributes: dict[str, Any] = {}
        if name is not None:
            custom_attributes['Name'] = name
        if multiplier is not None:
            source_fields['Multiplier'] = multiplier
        if zone_inside_convection_algorithm is not None:
            source_fields['ZoneInsideConvectionAlgorithm'] = zone_inside_convection_algorithm
        if zone_outside_convection_algorithm is not None:
            source_fields['ZoneOutsideConvectionAlgorithm'] = zone_outside_convection_algorithm
        source_properties: dict[str, Any] = {}
        inline_source_property_children: dict[str, Any] = {}
        if zone_control_humidistat is not None:
            source_fields['ZoneControlHumidistat'] = zone_control_humidistat
        if zone_control_contaminant_controller is not None:
            source_fields['ZoneControlContaminantController'] = zone_control_contaminant_controller
        if ceiling_height is not None:
            source_fields['CeilingHeight'] = ceiling_height
        if volume is not None:
            source_fields['Volume'] = volume
        if zone_conditioning_equipment_list_name is not None:
            source_fields['ZoneConditioningEquipmentListName'] = zone_conditioning_equipment_list_name
        if thermostat_setpoint_dual_setpoint is not None:
            source_fields['ThermostatSetpointDualSetpoint'] = thermostat_setpoint_dual_setpoint
        if fractionof_zone_controlledby_primary_daylighting_control is not None:
            source_fields['FractionofZoneControlledbyPrimaryDaylightingControl'] = fractionof_zone_controlledby_primary_daylighting_control
        if fractionof_zone_controlledby_secondary_daylighting_control is not None:
            source_fields['FractionofZoneControlledbySecondaryDaylightingControl'] = fractionof_zone_controlledby_secondary_daylighting_control
        if daylighting_controls_availability_schedule_target is not None:
            source_field_targets['DaylightingControlsAvailabilitySchedule'] = daylighting_controls_availability_schedule_target
        if rendering_color is not None:
            source_fields['RenderingColor'] = rendering_color
        if use_ideal_air_loads is not None:
            source_fields['UseIdealAirLoads'] = use_ideal_air_loads
        if load_distribution_scheme is not None:
            source_fields['LoadDistributionScheme'] = load_distribution_scheme
        if allow_multi_air_loops is not None:
            source_properties['AllowMultiAirLoops'] = allow_multi_air_loops
        if is_air_terminal_before_zone_equipments is not None:
            source_properties['IsAirTerminalBeforeZoneEquipments'] = is_air_terminal_before_zone_equipments

        # Build output/EMS kwargs only when values are provided.
        output_ems_kwargs: dict[str, Any] = {}
        if output_variable_names is not None:
            output_ems_kwargs['output_variable_names'] = output_variable_names
        if output_reporting_frequency is not None:
            output_ems_kwargs['output_reporting_frequency'] = output_reporting_frequency
        if ems_sensor_targets is not None:
            output_ems_kwargs['ems_sensor_targets'] = ems_sensor_targets
        if ems_actuator_targets is not None:
            output_ems_kwargs['ems_actuator_targets'] = ems_actuator_targets
        if ems_internal_variable_targets is not None:
            output_ems_kwargs['ems_internal_variable_targets'] = ems_internal_variable_targets

        inline_return_plenum_fields: dict[str, Any] = {}
        inline_return_plenum_field_targets: dict[str, Any] = {}
        if return_plenum_name is not None:
            inline_return_plenum_fields['Name'] = return_plenum_name
        if return_plenum_multiplier is not None:
            inline_return_plenum_fields['Multiplier'] = return_plenum_multiplier
        if return_plenum_ceiling_height is not None:
            inline_return_plenum_fields['CeilingHeight'] = return_plenum_ceiling_height
        if return_plenum_volume is not None:
            inline_return_plenum_fields['Volume'] = return_plenum_volume
        if return_plenum_zone_inside_convection_algorithm is not None:
            inline_return_plenum_fields['ZoneInsideConvectionAlgorithm'] = return_plenum_zone_inside_convection_algorithm
        if return_plenum_zone_outside_convection_algorithm is not None:
            inline_return_plenum_fields['ZoneOutsideConvectionAlgorithm'] = return_plenum_zone_outside_convection_algorithm
        if return_plenum_zone_conditioning_equipment_list_name is not None:
            inline_return_plenum_fields['ZoneConditioningEquipmentListName'] = return_plenum_zone_conditioning_equipment_list_name
        if return_plenum_thermostat_setpoint_dual_setpoint is not None:
            inline_return_plenum_fields['ThermostatSetpointDualSetpoint'] = return_plenum_thermostat_setpoint_dual_setpoint
        if return_plenum_zone_control_humidistat is not None:
            inline_return_plenum_fields['ZoneControlHumidistat'] = return_plenum_zone_control_humidistat
        if return_plenum_zone_control_contaminant_controller is not None:
            inline_return_plenum_fields['ZoneControlContaminantController'] = return_plenum_zone_control_contaminant_controller
        if return_plenum_fractionof_zone_controlledby_primary_daylighting_control is not None:
            inline_return_plenum_fields['FractionofZoneControlledbyPrimaryDaylightingControl'] = return_plenum_fractionof_zone_controlledby_primary_daylighting_control
        if return_plenum_fractionof_zone_controlledby_secondary_daylighting_control is not None:
            inline_return_plenum_fields['FractionofZoneControlledbySecondaryDaylightingControl'] = return_plenum_fractionof_zone_controlledby_secondary_daylighting_control
        if return_plenum_daylighting_controls_availability_schedule_target is not None:
            inline_return_plenum_field_targets['DaylightingControlsAvailabilitySchedule'] = return_plenum_daylighting_controls_availability_schedule_target
        if return_plenum_rendering_color is not None:
            inline_return_plenum_fields['RenderingColor'] = return_plenum_rendering_color
        if return_plenum_use_ideal_air_loads is not None:
            inline_return_plenum_fields['UseIdealAirLoads'] = return_plenum_use_ideal_air_loads
        if return_plenum_load_distribution_scheme is not None:
            inline_return_plenum_fields['LoadDistributionScheme'] = return_plenum_load_distribution_scheme
        if return_plenum_identifier is not None or inline_return_plenum_fields or inline_return_plenum_field_targets:
            if return_plenum_targets is not None:
                raise ValueError("Provide either return_plenum_targets or inline return_plenum_* parameters, not both.")
            inline_source_property_children['ReturnPlenum'] = {
                'source_class': 'IB_ThermalZone',
                'is_list': False,
                'identifiers': return_plenum_identifier,
                'source_fields': inline_return_plenum_fields,
                'source_field_targets': inline_return_plenum_field_targets,
            }
        inline_supply_plenum_fields: dict[str, Any] = {}
        inline_supply_plenum_field_targets: dict[str, Any] = {}
        if supply_plenum_name is not None:
            inline_supply_plenum_fields['Name'] = supply_plenum_name
        if supply_plenum_multiplier is not None:
            inline_supply_plenum_fields['Multiplier'] = supply_plenum_multiplier
        if supply_plenum_ceiling_height is not None:
            inline_supply_plenum_fields['CeilingHeight'] = supply_plenum_ceiling_height
        if supply_plenum_volume is not None:
            inline_supply_plenum_fields['Volume'] = supply_plenum_volume
        if supply_plenum_zone_inside_convection_algorithm is not None:
            inline_supply_plenum_fields['ZoneInsideConvectionAlgorithm'] = supply_plenum_zone_inside_convection_algorithm
        if supply_plenum_zone_outside_convection_algorithm is not None:
            inline_supply_plenum_fields['ZoneOutsideConvectionAlgorithm'] = supply_plenum_zone_outside_convection_algorithm
        if supply_plenum_zone_conditioning_equipment_list_name is not None:
            inline_supply_plenum_fields['ZoneConditioningEquipmentListName'] = supply_plenum_zone_conditioning_equipment_list_name
        if supply_plenum_thermostat_setpoint_dual_setpoint is not None:
            inline_supply_plenum_fields['ThermostatSetpointDualSetpoint'] = supply_plenum_thermostat_setpoint_dual_setpoint
        if supply_plenum_zone_control_humidistat is not None:
            inline_supply_plenum_fields['ZoneControlHumidistat'] = supply_plenum_zone_control_humidistat
        if supply_plenum_zone_control_contaminant_controller is not None:
            inline_supply_plenum_fields['ZoneControlContaminantController'] = supply_plenum_zone_control_contaminant_controller
        if supply_plenum_fractionof_zone_controlledby_primary_daylighting_control is not None:
            inline_supply_plenum_fields['FractionofZoneControlledbyPrimaryDaylightingControl'] = supply_plenum_fractionof_zone_controlledby_primary_daylighting_control
        if supply_plenum_fractionof_zone_controlledby_secondary_daylighting_control is not None:
            inline_supply_plenum_fields['FractionofZoneControlledbySecondaryDaylightingControl'] = supply_plenum_fractionof_zone_controlledby_secondary_daylighting_control
        if supply_plenum_daylighting_controls_availability_schedule_target is not None:
            inline_supply_plenum_field_targets['DaylightingControlsAvailabilitySchedule'] = supply_plenum_daylighting_controls_availability_schedule_target
        if supply_plenum_rendering_color is not None:
            inline_supply_plenum_fields['RenderingColor'] = supply_plenum_rendering_color
        if supply_plenum_use_ideal_air_loads is not None:
            inline_supply_plenum_fields['UseIdealAirLoads'] = supply_plenum_use_ideal_air_loads
        if supply_plenum_load_distribution_scheme is not None:
            inline_supply_plenum_fields['LoadDistributionScheme'] = supply_plenum_load_distribution_scheme
        if supply_plenum_identifier is not None or inline_supply_plenum_fields or inline_supply_plenum_field_targets:
            if supply_plenum_targets is not None:
                raise ValueError("Provide either supply_plenum_targets or inline supply_plenum_* parameters, not both.")
            inline_source_property_children['SupplyPlenum'] = {
                'source_class': 'IB_ThermalZone',
                'is_list': False,
                'identifiers': supply_plenum_identifier,
                'source_fields': inline_supply_plenum_fields,
                'source_field_targets': inline_supply_plenum_field_targets,
            }
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ThermalZone',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            inline_source_property_children=inline_source_property_children or None,
            custom_attributes=custom_attributes or None,
            overwrite=overwrite,
            **output_ems_kwargs,
        )

        sizing_result = set_ironbug_thermal_zone_sizing_zone(
            garden_root=garden_root,
            ironbug_model_target=created["updated_model_target"],
            thermal_zone_target=created["target"],
            sizing_zone_target=sizing_zone_target,
        )
        created["target"] = sizing_result["target"]
        created["updated_model_target"] = sizing_result["updated_model_target"]
        created["summary_view"] = {
            **created["summary_view"],
            "sizing_zone_bound": sizing_zone_target is not None,
            "sizing_zone_source_default": sizing_zone_target is None,
            "sizing_zone_identifier": sizing_result["summary_view"][
                "sizing_zone_identifier"
            ],
        }

        selected_air_terminal = air_terminal or _single_target_from_sequence(
            "air_terminals_targets",
            air_terminals_targets,
        )
        if selected_air_terminal is not None:
            updated = set_ironbug_thermal_zone_air_terminal(
                garden_root=garden_root,
                ironbug_model_target=created["updated_model_target"],
                thermal_zone_target=created["target"],
                air_terminal_target=selected_air_terminal,
            )
            created["target"] = updated["target"]
            created["updated_model_target"] = updated["updated_model_target"]
            created["summary_view"] = {
                **created["summary_view"],
                "air_terminal_bound": True,
                "air_terminal_identifier": updated["summary_view"][
                    "air_terminal_identifier"
                ],
            }
        else:
            created["summary_view"] = {
                **created["summary_view"],
                "air_terminal_bound": False,
            }
        zone_equipment_identifiers: list[str] = []
        for selected_zone_equipment in _target_sequence(zone_equipments_targets):
            updated = add_ironbug_thermal_zone_equipment(
                garden_root=garden_root,
                ironbug_model_target=created["updated_model_target"],
                thermal_zone_target=created["target"],
                zone_equipment_target=selected_zone_equipment,
            )
            created["target"] = updated["target"]
            created["updated_model_target"] = updated["updated_model_target"]
            zone_equipment_identifiers.append(
                updated["summary_view"]["zone_equipment_identifier"]
            )
        created["summary_view"] = {
            **created["summary_view"],
            "zone_equipment_bound": bool(zone_equipment_identifiers),
            "zone_equipment_identifier": (
                zone_equipment_identifiers[-1] if zone_equipment_identifiers else None
            ),
            "zone_equipment_identifiers": zone_equipment_identifiers,
            "zone_equipment_count": len(zone_equipment_identifiers),
        }
        supply_plenum_target = _single_target_from_sequence(
            "supply_plenum_targets",
            supply_plenum_targets,
        )
        if supply_plenum_target is not None:
            updated = set_ironbug_thermal_zone_supply_plenum(
                garden_root=garden_root,
                ironbug_model_target=created["updated_model_target"],
                thermal_zone_target=created["target"],
                supply_plenum_target=supply_plenum_target,
            )
            created["target"] = updated["target"]
            created["updated_model_target"] = updated["updated_model_target"]
            created["summary_view"] = {
                **created["summary_view"],
                "supply_plenum_bound": True,
                "supply_plenum_identifier": updated["summary_view"][
                    "supply_plenum_identifier"
                ],
            }
        else:
            created["summary_view"] = {
                **created["summary_view"],
                "supply_plenum_bound": False,
            }
        return_plenum_target = _single_target_from_sequence(
            "return_plenum_targets",
            return_plenum_targets,
        )
        if return_plenum_target is not None:
            updated = set_ironbug_thermal_zone_return_plenum(
                garden_root=garden_root,
                ironbug_model_target=created["updated_model_target"],
                thermal_zone_target=created["target"],
                return_plenum_target=return_plenum_target,
            )
            created["target"] = updated["target"]
            created["updated_model_target"] = updated["updated_model_target"]
            created["summary_view"] = {
                **created["summary_view"],
                "return_plenum_bound": True,
                "return_plenum_identifier": updated["summary_view"][
                    "return_plenum_identifier"
                ],
            }
        else:
            created["summary_view"] = {
                **created["summary_view"],
                "return_plenum_bound": False,
            }
        return created
