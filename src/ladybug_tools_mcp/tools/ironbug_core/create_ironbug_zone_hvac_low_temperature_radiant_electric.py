'MCP tool for detailed_hvac_zone_equipment_low_temperature_radiant_electric.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    add_ironbug_thermal_zone_equipment,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_zone_equipment_low_temperature_radiant_electric tool.'

    @mcp.tool(
        name='zone_equipment_low_temperature_radiant_electric',
        description=(
            'Create IB_ZoneHVACLowTemperatureRadiantElectric, the Ironbug and EnergyPlus ZoneHVAC:LowTemperatureRadiant:Electric zone heater with availability, heating setpoint, radiant surface, panel power, and temperature-control fields. Use it for electric low-temperature radiant zone equipment, not as a hydronic radiant loop, high-temperature radiant heater, baseboard, air terminal, or result reader. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'zone-equipment', 'radiant', 'low-temperature', 'electric', 'heating', 'schedule', 'thermal-zone', 'author'},
        timeout=20,
    )
    def create_ironbug_zone_hvac_low_temperature_radiant_electric(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json where the Ironbug model and created electric low-temperature radiant zone equipment are stored."),
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
            Field(description="Stable identifier for the new IB_ZoneHVACLowTemperatureRadiantElectric object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for electric low-temperature radiant availability.'),
        ] = None,
        heating_setpoint_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for electric low-temperature radiant heating setpoint temperature.'),
        ] = None,
        radiant_surface_type: Annotated[
            str | None,
            Field(description='Optional RadiantSurfaceType value; maps to Ironbug IB_ZoneHVACLowTemperatureRadiantElectric field RadiantSurfaceType.'),
        ] = None,
        maximum_electrical_powerto_panel: Annotated[
            float | str | None,
            Field(description='Optional maximum electrical power to the radiant panel; accepts numeric values or autosizing strings supported by the Ironbug source field.'),
        ] = None,
        temperature_control_type: Annotated[
            str | None,
            Field(description='Optional TemperatureControlType value; maps to Ironbug IB_ZoneHVACLowTemperatureRadiantElectric field TemperatureControlType.'),
        ] = None,
        setpoint_control_type: Annotated[
            str | None,
            Field(description='Optional SetpointControlType value; maps to Ironbug IB_ZoneHVACLowTemperatureRadiantElectric field SetpointControlType.'),
        ] = None,
        heating_throttling_range: Annotated[
            float | None,
            Field(description='Optional HeatingThrottlingRange value; maps to Ironbug IB_ZoneHVACLowTemperatureRadiantElectric field HeatingThrottlingRange.'),
        ] = None,
        thermal_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ThermalZone target or same-model identifier. When provided, the "
                    "created zone equipment is added to that ThermalZone's ZoneEquipments."
                )
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_ZoneHVACLowTemperatureRadiantElectric field Name.'),
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
        """Create an Ironbug ZoneHVAC:LowTemperatureRadiant:Electric object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if heating_setpoint_temperature_schedule_target is not None:
            source_field_targets['HeatingSetpointTemperatureSchedule'] = heating_setpoint_temperature_schedule_target
        if radiant_surface_type is not None:
            source_fields['RadiantSurfaceType'] = radiant_surface_type
        if maximum_electrical_powerto_panel is not None:
            source_fields['MaximumElectricalPowertoPanel'] = maximum_electrical_powerto_panel
        if temperature_control_type is not None:
            source_fields['TemperatureControlType'] = temperature_control_type
        if setpoint_control_type is not None:
            source_fields['SetpointControlType'] = setpoint_control_type
        if heating_throttling_range is not None:
            source_fields['HeatingThrottlingRange'] = heating_throttling_range
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ZoneHVACLowTemperatureRadiantElectric',
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
