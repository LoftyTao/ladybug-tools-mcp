'MCP tool for detailed_hvac_air_terminal_vav_no_reheat.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    set_ironbug_thermal_zone_air_terminal,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_air_terminal_vav_no_reheat tool.'

    @mcp.tool(
        name='air_terminal_vav_no_reheat',
        description=(
            'Create IB_AirTerminalSingleDuctVAVNoReheat, an Ironbug '
            'single-duct variable air volume (VAV) no-reheat terminal unit '
            'that maps downstream to EnergyPlus/OpenStudio '
            'AirTerminal:SingleDuct:VAV:NoReheat. Use the returned target as '
            'an air-loop demand-side air terminal and bind it to an '
            'IB_ThermalZone through thermal_zone_target or the ThermalZone '
            'tool. This tool has no reheat coil and is not a Honeybee Energy '
            'HVAC template. Returns target, summary_view, persistence_receipt, '
            'and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'air-terminal', 'terminal-unit', 'vav', 'no-reheat', 'author'},
        timeout=20,
    )
    def create_ironbug_air_terminal_single_duct_vav_no_reheat(
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
            Field(description="Stable identifier for the new IB_AirTerminalSingleDuctVAVNoReheat object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for AvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Schedule values above zero make the VAV no-reheat terminal available.'),
        ] = None,
        maximum_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MaximumAirFlowRate in m3/s, or an EnergyPlus autosizable literal accepted by Ironbug.'),
        ] = None,
        zone_minimum_air_flow_input_method: Annotated[
            str | None,
            Field(description="Optional ZoneMinimumAirFlowInputMethod, typically 'Constant', 'Scheduled', or 'FixedFlowRate' for the EnergyPlus/OpenStudio VAV terminal object."),
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
        control_for_outdoor_air: Annotated[
            bool | str | None,
            Field(description='Optional ControlForOutdoorAir value; maps to Ironbug IB_AirTerminalSingleDuctVAVNoReheat field ControlForOutdoorAir.'),
        ] = None,
        thermal_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ThermalZone target or same-model identifier "
                    "to bind this no-reheat VAV air terminal to after "
                    "creation; this does not create Honeybee Room geometry."
                )
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_AirTerminalSingleDuctVAVNoReheat field Name.'),
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
        """Create IB_AirTerminalSingleDuctVAVNoReheat as a reviewed VAV air terminal."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
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
        if control_for_outdoor_air is not None:
            source_fields['ControlForOutdoorAir'] = control_for_outdoor_air
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_AirTerminalSingleDuctVAVNoReheat',
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
