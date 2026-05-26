'MCP tool for detailed_hvac_zone_equipment_energy_recovery_ventilator.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    add_ironbug_thermal_zone_equipment,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_zone_equipment_energy_recovery_ventilator tool.'

    @mcp.tool(
        name='zone_equipment_energy_recovery_ventilator',
        description=(
            'Create IB_ZoneHVACEnergyRecoveryVentilator, the Ironbug and EnergyPlus ZoneHVAC:EnergyRecoveryVentilator zone equipment with heat-exchanger, supply-fan, and exhaust-fan children plus supply/exhaust ventilation flow fields. Use it for room-level energy-recovery ventilation attached to an IB_ThermalZone, not as an air-loop outdoor-air system, standalone heat exchanger, or result reader. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'zone-equipment', 'energy-recovery', 'heat-recovery', 'ventilation', 'fan', 'thermal-zone', 'author'},
        timeout=20,
    )
    def create_ironbug_zone_hvac_energy_recovery_ventilator(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json where the Ironbug model and created zone energy-recovery ventilator are stored."),
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
            Field(description="Stable identifier for the new IB_ZoneHVACEnergyRecoveryVentilator object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for ZoneHVAC:EnergyRecoveryVentilator availability; pass a detailed_hvac_schedule_* target or same-model identifier.'),
        ] = None,
        supply_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional supply air flow rate for the zone energy-recovery ventilator; accepts numeric values or autosizing strings supported by the Ironbug source field.'),
        ] = None,
        exhaust_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional exhaust air flow rate for the zone energy-recovery ventilator; accepts numeric values or autosizing strings supported by the Ironbug source field.'),
        ] = None,
        ventilation_rateper_unit_floor_area: Annotated[
            float | None,
            Field(description='Optional VentilationRateperUnitFloorArea value; maps to Ironbug IB_ZoneHVACEnergyRecoveryVentilator field VentilationRateperUnitFloorArea.'),
        ] = None,
        ventilation_rateper_occupant: Annotated[
            float | None,
            Field(description='Optional VentilationRateperOccupant value; maps to Ironbug IB_ZoneHVACEnergyRecoveryVentilator field VentilationRateperOccupant.'),
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
            Field(description='Optional Name value; maps to Ironbug IB_ZoneHVACEnergyRecoveryVentilator field Name.'),
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
        heating_exchanger_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_HeatExchangerAirToAirSensibleAndLatent target used as the ERV heat exchanger child."
                )
            ),
        ] = None,
        supply_fan_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_Fan target used as the zone energy-recovery ventilator supply fan child."
                )
            ),
        ] = None,
        exhaust_fan_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_Fan target used as the zone energy-recovery ventilator exhaust fan child."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug ZoneHVAC:EnergyRecoveryVentilator zone-equipment object."""

        child_targets = [
            heating_exchanger_target,
            supply_fan_target,
            exhaust_fan_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if supply_air_flow_rate is not None:
            source_fields['SupplyAirFlowRate'] = supply_air_flow_rate
        if exhaust_air_flow_rate is not None:
            source_fields['ExhaustAirFlowRate'] = exhaust_air_flow_rate
        if ventilation_rateper_unit_floor_area is not None:
            source_fields['VentilationRateperUnitFloorArea'] = ventilation_rateper_unit_floor_area
        if ventilation_rateper_occupant is not None:
            source_fields['VentilationRateperOccupant'] = ventilation_rateper_occupant
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ZoneHVACEnergyRecoveryVentilator',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            child_targets=child_targets if any(item is not None for item in child_targets) else None,
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
