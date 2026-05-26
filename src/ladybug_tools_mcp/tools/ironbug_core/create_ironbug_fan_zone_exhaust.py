'MCP tool for detailed_hvac_fan_zone_exhaust.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    add_ironbug_thermal_zone_equipment,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_fan_zone_exhaust tool.'

    @mcp.tool(
        name='fan_zone_exhaust',
        description=(
            'Create an Ironbug IB_FanZoneExhaust zone equipment object for EnergyPlus/OpenStudio Fan:ZoneExhaust. Use this for exhaust air removed directly from an Ironbug ThermalZone, not for air-loop supply fans or air terminals. Pass thermal_zone_target to add it to the zone equipment list. This authors Ironbug DetailedHVAC input only; run Energy simulation after the DetailedHVAC system is applied. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'fan',
            'zone-equipment',
            'zone-exhaust',
            'exhaust',
            'ventilation',
            'thermal-zone',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_fan_zone_exhaust(
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
            Field(description="Stable DetailedHVAC object identifier for this zone exhaust fan."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional display label shown in Ironbug/Garden summaries."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Schedule target or same-model identifier for the exhaust fan availability schedule; schedule values greater than 0 make the fan available."),
        ] = None,
        fan_total_efficiency: Annotated[
            float | None,
            Field(description="Optional fan total efficiency as a 0-1 fraction for Fan:ZoneExhaust."),
        ] = None,
        pressure_rise: Annotated[
            float | None,
            Field(description="Optional exhaust fan pressure rise in Pa."),
        ] = None,
        maximum_flow_rate: Annotated[
            float | None,
            Field(description="Optional maximum exhaust flow rate in m3/s."),
        ] = None,
        end_use_subcategory: Annotated[
            str | None,
            Field(description="Optional EnergyPlus end-use subcategory text, such as General or Exhaust Fans."),
        ] = None,
        flow_fraction_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Schedule target or same-model identifier that modulates exhaust flow as a fraction of maximum flow."),
        ] = None,
        system_availability_manager_coupling_mode: Annotated[
            str | None,
            Field(description="Optional EnergyPlus System Availability Manager Coupling Mode value for Fan:ZoneExhaust."),
        ] = None,
        minimum_zone_temperature_limit_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Schedule target or same-model identifier for the minimum zone temperature limit schedule."),
        ] = None,
        balanced_exhaust_fraction_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Schedule target or same-model identifier for the balanced exhaust fraction schedule."),
        ] = None,
        fan_efficiency: Annotated[
            str | float | int | bool | None,
            Field(description="Optional OpenStudio fan efficiency field accepted by the Ironbug source mirror; use a 0-1 numeric value unless reproducing source data."),
        ] = None,
        thermal_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ThermalZone target or same-model identifier. When provided, this "
                    "Fan:ZoneExhaust object is added to that ThermalZone's ZoneEquipments list."
                )
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional EnergyPlus/OpenStudio fan name; defaults to the identifier when omitted."),
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
        """Create IB_FanZoneExhaust as a reviewed Ironbug ZoneEquipments authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if fan_efficiency is not None:
            source_fields['FanEfficiency'] = fan_efficiency
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if fan_total_efficiency is not None:
            source_fields['FanTotalEfficiency'] = fan_total_efficiency
        if pressure_rise is not None:
            source_fields['PressureRise'] = pressure_rise
        if maximum_flow_rate is not None:
            source_fields['MaximumFlowRate'] = maximum_flow_rate
        if end_use_subcategory is not None:
            source_fields['EndUseSubcategory'] = end_use_subcategory
        if flow_fraction_schedule_target is not None:
            source_field_targets['FlowFractionSchedule'] = flow_fraction_schedule_target
        if system_availability_manager_coupling_mode is not None:
            source_fields['SystemAvailabilityManagerCouplingMode'] = system_availability_manager_coupling_mode
        if minimum_zone_temperature_limit_schedule_target is not None:
            source_field_targets['MinimumZoneTemperatureLimitSchedule'] = minimum_zone_temperature_limit_schedule_target
        if balanced_exhaust_fraction_schedule_target is not None:
            source_field_targets['BalancedExhaustFractionSchedule'] = balanced_exhaust_fraction_schedule_target
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_FanZoneExhaust',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
        latest_model_target = created["updated_model_target"]
        binding_summary: dict[str, Any] = {}
        if thermal_zone_target is not None:
            zone = add_ironbug_thermal_zone_equipment(
                garden_root=garden_root,
                ironbug_model_target=latest_model_target,
                thermal_zone_target=thermal_zone_target,
                zone_equipment_target=created["target"],
            )
            latest_model_target = zone["updated_model_target"]
            created["target"]["model_target"] = latest_model_target
            binding_summary["thermal_zone_bound"] = True
            binding_summary["thermal_zone_identifier"] = zone["summary_view"][
                "thermal_zone_identifier"
            ]
        else:
            binding_summary["thermal_zone_bound"] = False
        created["updated_model_target"] = latest_model_target
        created["summary_view"] = {**created["summary_view"], **binding_summary}
        return created

