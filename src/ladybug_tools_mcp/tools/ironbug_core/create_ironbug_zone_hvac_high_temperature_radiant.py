'MCP tool for detailed_hvac_zone_equipment_high_temperature_radiant.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    add_ironbug_thermal_zone_equipment,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_zone_equipment_high_temperature_radiant tool.'

    @mcp.tool(
        name='zone_equipment_high_temperature_radiant',
        description=(
            'Create IB_ZoneHVACHighTemperatureRadiant, the Ironbug and EnergyPlus ZoneHVAC:HighTemperatureRadiant zone heater for fuel/electric high-temperature radiant panels. Use it for ThermalZone radiant heating with power, fuel, combustion efficiency, radiant/latent/lost fractions, and heating setpoint schedule fields, not as a low-temperature hydronic slab, baseboard, air terminal, or result reader. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'zone-equipment', 'radiant', 'high-temperature', 'heating', 'fuel', 'schedule', 'thermal-zone', 'author'},
        timeout=20,
    )
    def create_ironbug_zone_hvac_high_temperature_radiant(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json where the Ironbug model and created high-temperature radiant zone equipment are stored."),
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
            Field(description="Stable identifier for the new IB_ZoneHVACHighTemperatureRadiant object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for high-temperature radiant heater availability; pass a detailed_hvac_schedule_* target or same-model identifier.'),
        ] = None,
        maximum_power_input: Annotated[
            float | str | None,
            Field(description='Optional maximum heater power input for the high-temperature radiant zone equipment; accepts numeric values or autosizing strings supported by the Ironbug field.'),
        ] = None,
        fuel_type: Annotated[
            str | None,
            Field(description='Optional fuel type for the high-temperature radiant heater, such as electricity, natural gas, or another EnergyPlus fuel choice accepted by Ironbug.'),
        ] = None,
        combustion_efficiency: Annotated[
            float | None,
            Field(description='Optional CombustionEfficiency value; maps to Ironbug IB_ZoneHVACHighTemperatureRadiant field CombustionEfficiency.'),
        ] = None,
        fractionof_input_convertedto_radiant_energy: Annotated[
            float | None,
            Field(description='Optional FractionofInputConvertedtoRadiantEnergy value; maps to Ironbug IB_ZoneHVACHighTemperatureRadiant field FractionofInputConvertedtoRadiantEnergy.'),
        ] = None,
        fractionof_input_convertedto_latent_energy: Annotated[
            float | None,
            Field(description='Optional FractionofInputConvertedtoLatentEnergy value; maps to Ironbug IB_ZoneHVACHighTemperatureRadiant field FractionofInputConvertedtoLatentEnergy.'),
        ] = None,
        fractionof_inputthat_is_lost: Annotated[
            float | None,
            Field(description='Optional FractionofInputthatIsLost value; maps to Ironbug IB_ZoneHVACHighTemperatureRadiant field FractionofInputthatIsLost.'),
        ] = None,
        temperature_control_type: Annotated[
            str | None,
            Field(description='Optional TemperatureControlType value; maps to Ironbug IB_ZoneHVACHighTemperatureRadiant field TemperatureControlType.'),
        ] = None,
        heating_throttling_range: Annotated[
            float | None,
            Field(description='Optional HeatingThrottlingRange value; maps to Ironbug IB_ZoneHVACHighTemperatureRadiant field HeatingThrottlingRange.'),
        ] = None,
        heating_setpoint_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for the high-temperature radiant heating setpoint temperature.'),
        ] = None,
        fractionof_radiant_energy_incidenton_people: Annotated[
            float | None,
            Field(description='Optional FractionofRadiantEnergyIncidentonPeople value; maps to Ironbug IB_ZoneHVACHighTemperatureRadiant field FractionofRadiantEnergyIncidentonPeople.'),
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
            Field(description='Optional Name value; maps to Ironbug IB_ZoneHVACHighTemperatureRadiant field Name.'),
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
        """Create an Ironbug ZoneHVAC:HighTemperatureRadiant zone-heater object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if maximum_power_input is not None:
            source_fields['MaximumPowerInput'] = maximum_power_input
        if fuel_type is not None:
            source_fields['FuelType'] = fuel_type
        if combustion_efficiency is not None:
            source_fields['CombustionEfficiency'] = combustion_efficiency
        if fractionof_input_convertedto_radiant_energy is not None:
            source_fields['FractionofInputConvertedtoRadiantEnergy'] = fractionof_input_convertedto_radiant_energy
        if fractionof_input_convertedto_latent_energy is not None:
            source_fields['FractionofInputConvertedtoLatentEnergy'] = fractionof_input_convertedto_latent_energy
        if fractionof_inputthat_is_lost is not None:
            source_fields['FractionofInputthatIsLost'] = fractionof_inputthat_is_lost
        if temperature_control_type is not None:
            source_fields['TemperatureControlType'] = temperature_control_type
        if heating_throttling_range is not None:
            source_fields['HeatingThrottlingRange'] = heating_throttling_range
        if heating_setpoint_temperature_schedule_target is not None:
            source_field_targets['HeatingSetpointTemperatureSchedule'] = heating_setpoint_temperature_schedule_target
        if fractionof_radiant_energy_incidenton_people is not None:
            source_fields['FractionofRadiantEnergyIncidentonPeople'] = fractionof_radiant_energy_incidenton_people
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ZoneHVACHighTemperatureRadiant',
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
