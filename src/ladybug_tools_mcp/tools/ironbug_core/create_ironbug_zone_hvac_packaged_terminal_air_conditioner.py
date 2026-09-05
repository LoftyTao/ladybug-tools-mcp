'MCP tool for IB_zone_equipment_ptac.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field




def register(mcp: FastMCP) -> None:
    'Register the IB_zone_equipment_ptac tool.'

    @mcp.tool(
        name='IB_zone_equipment_ptac',
        description=(
            'Create IB_ZoneHVACPackagedTerminalAirConditioner, an Ironbug packaged '
            'terminal air conditioner (PTAC) zone-equipment component that maps '
            'downstream to EnergyPlus ZoneHVAC:PackagedTerminalAirConditioner and '
            'OpenStudio ZoneHVACPackagedTerminalAirConditioner. Bind the required '
            'supply fan, heating coil, cooling coil, and IB_ThermalZone placement through '
            'explicit targets. This authors Ironbug DetailedHVAC input, not a Honeybee '
            'Energy HVAC template. Returns target, updated_model_target, summary_view, '
            'persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'zone-equipment',
            'packaged-terminal',
            'ptac',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_zone_hvac_packaged_terminal_air_conditioner(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_create['garden_root']."),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Required Ironbug model target returned by IB_create_model; '
                    "pass result['target'], not the .ibjson file path."
                )
            ),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for the new IB_ZoneHVACPackagedTerminalAirConditioner object."),
        ],
        fan_target: Annotated[
            dict[str, Any] | str,
            Field(description="Required IB_Fan target or same-model identifier used as the PTAC supply fan."),
        ],
        heating_coil_target: Annotated[
            dict[str, Any] | str,
            Field(description="Required IB_CoilHeatingBasic target or same-model identifier used as the PTAC heating coil."),
        ],
        cooling_coil_target: Annotated[
            dict[str, Any] | str,
            Field(description="Required IB_Coil target or same-model identifier used as the PTAC cooling coil."),
        ],
        thermal_zone_target: Annotated[
            dict[str, Any] | str,
            Field(description="Required IB_ThermalZone target or same-model identifier to receive this PTAC as zone equipment; this does not create Honeybee Room geometry."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for AvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Schedule values above zero make the PTAC available.'),
        ] = None,
        outdoor_air_mixer_object_type: Annotated[
            str | None,
            Field(description='Optional OutdoorAirMixerObjectType value; maps to Ironbug IB_ZoneHVACPackagedTerminalAirConditioner field OutdoorAirMixerObjectType.'),
        ] = None,
        supply_air_flow_rate_during_cooling_operation: Annotated[
            float | str | None,
            Field(description='Optional SupplyAirFlowRateDuringCoolingOperation value; maps to Ironbug IB_ZoneHVACPackagedTerminalAirConditioner field SupplyAirFlowRateDuringCoolingOperation.'),
        ] = None,
        supply_air_flow_rate_during_heating_operation: Annotated[
            float | str | None,
            Field(description='Optional SupplyAirFlowRateDuringHeatingOperation value; maps to Ironbug IB_ZoneHVACPackagedTerminalAirConditioner field SupplyAirFlowRateDuringHeatingOperation.'),
        ] = None,
        supply_air_flow_rate_when_no_coolingor_heatingis_needed: Annotated[
            float | str | None,
            Field(description='Optional SupplyAirFlowRateWhenNoCoolingorHeatingisNeeded value; maps to Ironbug IB_ZoneHVACPackagedTerminalAirConditioner field SupplyAirFlowRateWhenNoCoolingorHeatingisNeeded.'),
        ] = None,
        no_load_supply_air_flow_rate_control_set_to_low_speed: Annotated[
            bool | str | None,
            Field(description='Optional NoLoadSupplyAirFlowRateControlSetToLowSpeed value; maps to Ironbug IB_ZoneHVACPackagedTerminalAirConditioner field NoLoadSupplyAirFlowRateControlSetToLowSpeed.'),
        ] = None,
        outdoor_air_flow_rate_during_cooling_operation: Annotated[
            float | str | None,
            Field(description='Optional OutdoorAirFlowRateDuringCoolingOperation value; maps to Ironbug IB_ZoneHVACPackagedTerminalAirConditioner field OutdoorAirFlowRateDuringCoolingOperation.'),
        ] = None,
        outdoor_air_flow_rate_during_heating_operation: Annotated[
            float | str | None,
            Field(description='Optional OutdoorAirFlowRateDuringHeatingOperation value; maps to Ironbug IB_ZoneHVACPackagedTerminalAirConditioner field OutdoorAirFlowRateDuringHeatingOperation.'),
        ] = None,
        outdoor_air_flow_rate_when_no_coolingor_heatingis_needed: Annotated[
            float | str | None,
            Field(description='Optional OutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded value; maps to Ironbug IB_ZoneHVACPackagedTerminalAirConditioner field OutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded.'),
        ] = None,
        fan_placement: Annotated[
            str | None,
            Field(description='Optional FanPlacement value; maps to Ironbug IB_ZoneHVACPackagedTerminalAirConditioner field FanPlacement.'),
        ] = None,
        supply_air_fan_operating_mode_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for SupplyAirFanOperatingModeSchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Values above zero usually indicate continuous fan operation.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_ZoneHVACPackagedTerminalAirConditioner field Name.'),
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
        """Create IB_ZoneHVACPackagedTerminalAirConditioner as reviewed PTAC zone equipment."""

        from garden.ironbug_core.create_tools import create_source_backed_ironbug_ptac

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if outdoor_air_mixer_object_type is not None:
            source_fields['OutdoorAirMixerObjectType'] = outdoor_air_mixer_object_type
        if supply_air_flow_rate_during_cooling_operation is not None:
            source_fields['SupplyAirFlowRateDuringCoolingOperation'] = supply_air_flow_rate_during_cooling_operation
        if supply_air_flow_rate_during_heating_operation is not None:
            source_fields['SupplyAirFlowRateDuringHeatingOperation'] = supply_air_flow_rate_during_heating_operation
        if supply_air_flow_rate_when_no_coolingor_heatingis_needed is not None:
            source_fields['SupplyAirFlowRateWhenNoCoolingorHeatingisNeeded'] = supply_air_flow_rate_when_no_coolingor_heatingis_needed
        if no_load_supply_air_flow_rate_control_set_to_low_speed is not None:
            source_fields['NoLoadSupplyAirFlowRateControlSetToLowSpeed'] = no_load_supply_air_flow_rate_control_set_to_low_speed
        if outdoor_air_flow_rate_during_cooling_operation is not None:
            source_fields['OutdoorAirFlowRateDuringCoolingOperation'] = outdoor_air_flow_rate_during_cooling_operation
        if outdoor_air_flow_rate_during_heating_operation is not None:
            source_fields['OutdoorAirFlowRateDuringHeatingOperation'] = outdoor_air_flow_rate_during_heating_operation
        if outdoor_air_flow_rate_when_no_coolingor_heatingis_needed is not None:
            source_fields['OutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded'] = outdoor_air_flow_rate_when_no_coolingor_heatingis_needed
        if fan_placement is not None:
            source_fields['FanPlacement'] = fan_placement
        if supply_air_fan_operating_mode_schedule_target is not None:
            source_field_targets['SupplyAirFanOperatingModeSchedule'] = supply_air_fan_operating_mode_schedule_target
        required_targets = {
            "fan_target": fan_target,
            "heating_coil_target": heating_coil_target,
            "cooling_coil_target": cooling_coil_target,
            "thermal_zone_target": thermal_zone_target,
        }
        missing_targets = [name for name, target in required_targets.items() if target is None]
        if missing_targets:
            raise ValueError(
                "PTAC requires fan_target, heating_coil_target, cooling_coil_target, "
                "and thermal_zone_target; missing: "
                f"{', '.join(missing_targets)}."
            )
        return create_source_backed_ironbug_ptac(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
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
            fan_target=fan_target,
            heating_coil_target=heating_coil_target,
            cooling_coil_target=cooling_coil_target,
            thermal_zone_target=thermal_zone_target,
        )
