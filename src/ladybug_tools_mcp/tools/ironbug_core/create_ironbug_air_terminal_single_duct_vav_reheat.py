'MCP tool for detailed_hvac_air_terminal_vav_reheat.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    set_ironbug_thermal_zone_air_terminal,
    set_ironbug_vav_reheat_terminal_coil,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_air_terminal_vav_reheat tool.'

    @mcp.tool(
        name='air_terminal_vav_reheat',
        description=(
            'Create IB_AirTerminalSingleDuctVAVReheat, an Ironbug single-duct '
            'variable air volume (VAV) reheat terminal unit that maps '
            'downstream to EnergyPlus/OpenStudio '
            'AirTerminal:SingleDuct:VAV:Reheat. Use the returned target as an '
            'air-loop demand-side air terminal, optionally bind a water, '
            'electric, or gas reheat coil through reheat_coil_target, and bind '
            'it to an IB_ThermalZone through thermal_zone_target or the '
            'ThermalZone tool. This is not a Honeybee Energy HVAC template. '
            'Returns target, summary_view, persistence_receipt, and report for '
            'downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'air-terminal', 'terminal-unit', 'vav', 'reheat', 'author'},
        timeout=20,
    )
    def create_ironbug_air_terminal_single_duct_vav_reheat(
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
            Field(description="Stable identifier for the new IB_AirTerminalSingleDuctVAVReheat object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for AvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Schedule values above zero make the VAV reheat terminal available.'),
        ] = None,
        maximum_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MaximumAirFlowRate in m3/s, or an EnergyPlus autosizable literal accepted by Ironbug.'),
        ] = None,
        zone_minimum_air_flow_input_method: Annotated[
            str | None,
            Field(description="Optional ZoneMinimumAirFlowInputMethod, typically 'Constant', 'Scheduled', or 'FixedFlowRate' for the EnergyPlus/OpenStudio VAV reheat terminal object."),
        ] = None,
        constant_minimum_air_flow_fraction: Annotated[
            float | str | None,
            Field(description='Optional ConstantMinimumAirFlowFraction, dimensionless fraction of MaximumAirFlowRate used when the input method is Constant.'),
        ] = None,
        fixed_minimum_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional FixedMinimumAirFlowRate in m3/s used when ZoneMinimumAirFlowInputMethod is FixedFlowRate.'),
        ] = None,
        minimum_air_flow_fraction_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for MinimumAirFlowFractionSchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Schedule values are fractions of MaximumAirFlowRate.'),
        ] = None,
        minimum_air_flow_turndown_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for MinimumAirFlowTurndownSchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier.'),
        ] = None,
        maximum_hot_water_or_steam_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MaximumHotWaterOrSteamFlowRate in m3/s, or an EnergyPlus autosizable literal accepted by Ironbug, used for hydronic or steam reheat coils.'),
        ] = None,
        minimum_hot_water_or_stream_flow_rate: Annotated[
            str | float | int | bool | None,
            Field(description='Optional MinimumHotWaterOrStreamFlowRate in m3/s, or an EnergyPlus default/autosizable literal accepted by Ironbug.'),
        ] = None,
        convergence_tolerance: Annotated[
            float | None,
            Field(description='Optional ConvergenceTolerance value; maps to Ironbug IB_AirTerminalSingleDuctVAVReheat field ConvergenceTolerance.'),
        ] = None,
        damper_heating_action: Annotated[
            str | None,
            Field(description="Optional DamperHeatingAction value, typically 'Normal', 'Reverse', or 'ReverseWithLimits' where supported by EnergyPlus/OpenStudio."),
        ] = None,
        maximum_flow_per_zone_floor_area_during_reheat: Annotated[
            float | str | None,
            Field(description='Optional MaximumFlowPerZoneFloorAreaDuringReheat in m3/s-m2, or an EnergyPlus autosizable/default literal accepted by Ironbug.'),
        ] = None,
        maximum_flow_fraction_during_reheat: Annotated[
            float | str | None,
            Field(description='Optional MaximumFlowFractionDuringReheat, dimensionless fraction of MaximumAirFlowRate.'),
        ] = None,
        maximum_reheat_air_temperature: Annotated[
            float | None,
            Field(description='Optional MaximumReheatAirTemperature in degrees C for the VAV reheat terminal.'),
        ] = None,
        control_for_outdoor_air: Annotated[
            bool | str | None,
            Field(description='Optional ControlForOutdoorAir value; maps to Ironbug IB_AirTerminalSingleDuctVAVReheat field ControlForOutdoorAir.'),
        ] = None,
        zone_minimum_air_flow_method: Annotated[
            str | float | int | bool | None,
            Field(description='Optional ZoneMinimumAirFlowMethod value; maps to Ironbug IB_AirTerminalSingleDuctVAVReheat field ZoneMinimumAirFlowMethod.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_AirTerminalSingleDuctVAVReheat field Name.'),
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
        reheat_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_CoilHeatingWater, IB_CoilHeatingElectric, "
                    "or IB_CoilHeatingGas target or same-model identifier to "
                    "attach as this VAV terminal's child reheat coil. Use a "
                    "detailed_hvac_coil_heating_* target, not a cooling coil."
                )
            ),
        ] = None,
        thermal_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ThermalZone target or same-model identifier "
                    "to bind this VAV reheat air terminal to after creation; "
                    "this does not create Honeybee Room geometry."
                )
            ),
        ] = None,
        heating_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional source child target for the Ironbug component "
                    "Parameter 'HeatingCoil' on IB_AirTerminalSingleDuctVAVReheat; "
                    "prefer reheat_coil_target for reviewed bottom-layer binding."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_AirTerminalSingleDuctVAVReheat as a reviewed VAV reheat terminal."""

        child_targets = [
            heating_coil_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if zone_minimum_air_flow_method is not None:
            source_fields['ZoneMinimumAirFlowMethod'] = zone_minimum_air_flow_method
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if maximum_air_flow_rate is not None:
            source_fields['MaximumAirFlowRate'] = maximum_air_flow_rate
        if zone_minimum_air_flow_input_method is not None:
            source_fields['ZoneMinimumAirFlowInputMethod'] = zone_minimum_air_flow_input_method
        if constant_minimum_air_flow_fraction is not None:
            source_fields['ConstantMinimumAirFlowFraction'] = constant_minimum_air_flow_fraction
        if fixed_minimum_air_flow_rate is not None:
            source_fields['FixedMinimumAirFlowRate'] = fixed_minimum_air_flow_rate
        if minimum_air_flow_fraction_schedule_target is not None:
            source_field_targets['MinimumAirFlowFractionSchedule'] = minimum_air_flow_fraction_schedule_target
        if minimum_air_flow_turndown_schedule_target is not None:
            source_field_targets['MinimumAirFlowTurndownSchedule'] = minimum_air_flow_turndown_schedule_target
        if maximum_hot_water_or_steam_flow_rate is not None:
            source_fields['MaximumHotWaterOrSteamFlowRate'] = maximum_hot_water_or_steam_flow_rate
        if minimum_hot_water_or_stream_flow_rate is not None:
            source_fields['MinimumHotWaterOrStreamFlowRate'] = minimum_hot_water_or_stream_flow_rate
        if convergence_tolerance is not None:
            source_fields['ConvergenceTolerance'] = convergence_tolerance
        if damper_heating_action is not None:
            source_fields['DamperHeatingAction'] = damper_heating_action
        if maximum_flow_per_zone_floor_area_during_reheat is not None:
            source_fields['MaximumFlowPerZoneFloorAreaDuringReheat'] = maximum_flow_per_zone_floor_area_during_reheat
        if maximum_flow_fraction_during_reheat is not None:
            source_fields['MaximumFlowFractionDuringReheat'] = maximum_flow_fraction_during_reheat
        if maximum_reheat_air_temperature is not None:
            source_fields['MaximumReheatAirTemperature'] = maximum_reheat_air_temperature
        if control_for_outdoor_air is not None:
            source_fields['ControlForOutdoorAir'] = control_for_outdoor_air
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_AirTerminalSingleDuctVAVReheat',
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
        if reheat_coil_target is not None:
            child = set_ironbug_vav_reheat_terminal_coil(
                garden_root=garden_root,
                ironbug_model_target=latest_model_target,
                air_terminal_target=created["target"],
                reheat_coil_target=reheat_coil_target,
            )
            latest_model_target = child["updated_model_target"]
            created["target"] = child["target"]
            binding_summary["reheat_coil_bound"] = True
        else:
            binding_summary["reheat_coil_bound"] = False
        if thermal_zone_target is not None:
            zone = set_ironbug_thermal_zone_air_terminal(
                garden_root=garden_root,
                ironbug_model_target=latest_model_target,
                thermal_zone_target=thermal_zone_target,
                air_terminal_target=created["target"],
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
