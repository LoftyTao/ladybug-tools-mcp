'MCP tool for detailed_hvac_zone_equipment_unit_ventilator_cooling_only.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    add_ironbug_thermal_zone_equipment,
    set_ironbug_unit_ventilator_cooling_only_children,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_zone_equipment_unit_ventilator_cooling_only tool.'

    @mcp.tool(
        name='zone_equipment_unit_ventilator_cooling_only',
        description=(
            'Create IB_ZoneHVACUnitVentilator_CoolingOnly, the Ironbug and EnergyPlus ZoneHVAC:UnitVentilator variant with a cooling coil, fan, outdoor-air controls, and optional ThermalZone placement. Use it for room-level cooling-only unit ventilators, not as a unit heater, fan coil, air terminal, standalone coil, or result reader. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'zone-equipment', 'unit-ventilator', 'cooling', 'fan', 'outdoor-air', 'thermal-zone', 'author'},
        timeout=20,
    )
    def create_ironbug_zone_hvac_unit_ventilator_cooling_only(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json where the Ironbug model and created cooling-only unit ventilator are stored."),
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
            Field(description="Stable identifier for the new IB_ZoneHVACUnitVentilator_CoolingOnly object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        cooling_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_CoilCoolingWater target or identifier to bind as the "
                    "unit ventilator cooling coil."
                )
            ),
        ] = None,
        fan_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_FanOnOff, IB_FanConstantVolume, IB_FanVariableVolume, "
                    "or IB_FanSystemModel target or identifier to bind as the "
                    "unit ventilator fan."
                )
            ),
        ] = None,
        thermal_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ThermalZone target or identifier. When provided, the "
                    "created unit ventilator is added to that ThermalZone's ZoneEquipments."
                )
            ),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for unit-ventilator availability.'),
        ] = None,
        maximum_supply_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional maximum supply air flow rate for the unit ventilator; accepts numeric values or autosizing strings supported by Ironbug.'),
        ] = None,
        outdoor_air_control_type: Annotated[
            str | None,
            Field(description='Optional OutdoorAirControlType value; maps to Ironbug IB_ZoneHVACUnitVentilator_CoolingOnly field OutdoorAirControlType. EnergyPlus accepts VariablePercent, FixedTemperature, or FixedAmount.'),
        ] = None,
        minimum_outdoor_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MinimumOutdoorAirFlowRate value; maps to Ironbug IB_ZoneHVACUnitVentilator_CoolingOnly field MinimumOutdoorAirFlowRate.'),
        ] = None,
        minimum_outdoor_air_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for MinimumOutdoorAirSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_ZoneHVACUnitVentilator_CoolingOnly field MinimumOutdoorAirSchedule (IB_Schedule).'),
        ] = None,
        maximum_outdoor_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MaximumOutdoorAirFlowRate value; maps to Ironbug IB_ZoneHVACUnitVentilator_CoolingOnly field MaximumOutdoorAirFlowRate.'),
        ] = None,
        maximum_outdoor_air_fractionor_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for MaximumOutdoorAirFractionorTemperatureSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_ZoneHVACUnitVentilator_CoolingOnly field MaximumOutdoorAirFractionorTemperatureSchedule (IB_Schedule).'),
        ] = None,
        supply_air_fan_operating_mode_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for SupplyAirFanOperatingModeSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_ZoneHVACUnitVentilator_CoolingOnly field SupplyAirFanOperatingModeSchedule (IB_Schedule).'),
        ] = None,
        heating_convergence_tolerance: Annotated[
            float | None,
            Field(description='Optional HeatingConvergenceTolerance value; maps to Ironbug IB_ZoneHVACUnitVentilator_CoolingOnly field HeatingConvergenceTolerance.'),
        ] = None,
        cooling_convergence_tolerance: Annotated[
            float | None,
            Field(description='Optional CoolingConvergenceTolerance value; maps to Ironbug IB_ZoneHVACUnitVentilator_CoolingOnly field CoolingConvergenceTolerance.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_ZoneHVACUnitVentilator_CoolingOnly field Name.'),
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
        """Create an Ironbug ZoneHVAC:UnitVentilator cooling-only object."""

        child_targets = (cooling_coil_target, fan_target)
        if any(item is not None for item in child_targets) and not all(
            item is not None for item in child_targets
        ):
            raise ValueError(
                "cooling_coil_target and fan_target must "
                "be provided together for unit ventilator cooling-only child binding."
            )
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if maximum_supply_air_flow_rate is not None:
            source_fields['MaximumSupplyAirFlowRate'] = maximum_supply_air_flow_rate
        if outdoor_air_control_type is not None:
            source_fields['OutdoorAirControlType'] = outdoor_air_control_type
        if minimum_outdoor_air_flow_rate is not None:
            source_fields['MinimumOutdoorAirFlowRate'] = minimum_outdoor_air_flow_rate
        if minimum_outdoor_air_schedule_target is not None:
            source_field_targets['MinimumOutdoorAirSchedule'] = minimum_outdoor_air_schedule_target
        if maximum_outdoor_air_flow_rate is not None:
            source_fields['MaximumOutdoorAirFlowRate'] = maximum_outdoor_air_flow_rate
        if maximum_outdoor_air_fractionor_temperature_schedule_target is not None:
            source_field_targets['MaximumOutdoorAirFractionorTemperatureSchedule'] = maximum_outdoor_air_fractionor_temperature_schedule_target
        if supply_air_fan_operating_mode_schedule_target is not None:
            source_field_targets['SupplyAirFanOperatingModeSchedule'] = supply_air_fan_operating_mode_schedule_target
        if heating_convergence_tolerance is not None:
            source_fields['HeatingConvergenceTolerance'] = heating_convergence_tolerance
        if cooling_convergence_tolerance is not None:
            source_fields['CoolingConvergenceTolerance'] = cooling_convergence_tolerance
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ZoneHVACUnitVentilator_CoolingOnly',
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
        if all(item is not None for item in child_targets):
            children = set_ironbug_unit_ventilator_cooling_only_children(
                garden_root=garden_root,
                ironbug_model_target=latest_model_target,
                unit_ventilator_target=created["target"],
                cooling_coil_target=cooling_coil_target,
                fan_target=fan_target,
            )
            latest_model_target = children["updated_model_target"]
            created["target"] = children["target"]
            binding_summary["children_bound"] = True
        else:
            binding_summary["children_bound"] = False
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
