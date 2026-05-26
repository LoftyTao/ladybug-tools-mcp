'MCP tool for detailed_hvac_air_terminal_single_duct_series_piu_reheat.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    set_ironbug_thermal_zone_air_terminal,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_air_terminal_single_duct_series_piu_reheat tool.'

    @mcp.tool(
        name='air_terminal_single_duct_series_piu_reheat',
        description=(
            'Create IB_AirTerminalSingleDuctSeriesPIUReheat, an Ironbug '
            'single-duct series powered induction unit (PIU) reheat air '
            'terminal that maps downstream to EnergyPlus/OpenStudio '
            'AirTerminal:SingleDuct:SeriesPIU:Reheat. Use the returned target '
            'as a fan-powered demand terminal, distinguish total airflow from '
            'primary airflow, attach compatible fan and heating-coil child '
            'targets when needed, and bind it to an IB_ThermalZone through '
            'thermal_zone_target or the ThermalZone tool. This is not zone '
            'equipment and not a Honeybee Energy HVAC template. Returns '
            'target, summary_view, persistence_receipt, and report for '
            'downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'air-terminal', 'terminal-unit', 'single-duct', 'piu', 'series', 'constant-volume', 'reheat', 'thermal-zone', 'author'},
        timeout=20,
    )
    def create_ironbug_air_terminal_single_duct_series_piu_reheat(
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
            Field(description="Stable identifier for the new IB_AirTerminalSingleDuctSeriesPIUReheat object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for AvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Schedule values above zero make the series PIU terminal available.'),
        ] = None,
        maximum_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MaximumAirFlowRate in m3/s for total series PIU airflow, or an EnergyPlus autosizable literal accepted by Ironbug.'),
        ] = None,
        maximum_primary_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MaximumPrimaryAirFlowRate in m3/s for primary air flow, or an EnergyPlus autosizable literal accepted by Ironbug.'),
        ] = None,
        minimum_primary_air_flow_fraction: Annotated[
            float | str | None,
            Field(description='Optional MinimumPrimaryAirFlowFraction, a 0.0-1.0 fraction of primary air flow or an autosizable literal accepted by Ironbug.'),
        ] = None,
        maximum_hot_wateror_steam_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MaximumHotWaterorSteamFlowRate in m3/s for hydronic or steam reheat coils; not used by electric or gas reheat coils.'),
        ] = None,
        minimum_hot_wateror_steam_flow_rate: Annotated[
            float | None,
            Field(description='Optional MinimumHotWaterorSteamFlowRate in m3/s for hydronic or steam reheat coils; EnergyPlus defaults this field to 0.0.'),
        ] = None,
        convergence_tolerance: Annotated[
            float | None,
            Field(description='Optional ConvergenceTolerance for water/steam reheat coil iteration; EnergyPlus commonly defaults this field to 0.001.'),
        ] = None,
        fan_control_type: Annotated[
            str | None,
            Field(description="Optional FanControlType, typically 'ConstantSpeed' or 'VariableSpeed' where supported by the downstream fan object."),
        ] = None,
        minimum_fan_turn_down_ratio: Annotated[
            float | None,
            Field(description='Optional MinimumFanTurnDownRatio, a 0.0-1.0 dimensionless fan turndown ratio.'),
        ] = None,
        heating_control_type: Annotated[
            str | None,
            Field(description="Optional HeatingControlType, typically 'Staged' or 'Modulated' for the PIU reheat terminal."),
        ] = None,
        design_heating_discharge_air_temperature: Annotated[
            float | None,
            Field(description='Optional DesignHeatingDischargeAirTemperature in degrees C, used when HeatingControlType is Modulated.'),
        ] = None,
        high_limit_heating_discharge_air_temperature: Annotated[
            float | None,
            Field(description='Optional HighLimitHeatingDischargeAirTemperature in degrees C, used when HeatingControlType is Modulated.'),
        ] = None,
        thermal_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ThermalZone target or same-model identifier to "
                    "bind this series PIU air terminal to after creation; "
                    "this does not create Honeybee Room geometry."
                )
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_AirTerminalSingleDuctSeriesPIUReheat field Name.'),
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
        heating_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_CoilHeatingBasic child target or same-model "
                    "identifier for Parameter 'HeatingCoil' on the series PIU "
                    "terminal; use a detailed_hvac_coil_heating_* target."
                )
            ),
        ] = None,
        fan_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_FanConstantVolume child target or same-model "
                    "identifier for Parameter 'Fan' on the series PIU terminal."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_AirTerminalSingleDuctSeriesPIUReheat as a reviewed series PIU terminal."""

        child_targets = [
            heating_coil_target,
            fan_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if maximum_air_flow_rate is not None:
            source_fields['MaximumAirFlowRate'] = maximum_air_flow_rate
        if maximum_primary_air_flow_rate is not None:
            source_fields['MaximumPrimaryAirFlowRate'] = maximum_primary_air_flow_rate
        if minimum_primary_air_flow_fraction is not None:
            source_fields['MinimumPrimaryAirFlowFraction'] = minimum_primary_air_flow_fraction
        if maximum_hot_wateror_steam_flow_rate is not None:
            source_fields['MaximumHotWaterorSteamFlowRate'] = maximum_hot_wateror_steam_flow_rate
        if minimum_hot_wateror_steam_flow_rate is not None:
            source_fields['MinimumHotWaterorSteamFlowRate'] = minimum_hot_wateror_steam_flow_rate
        if convergence_tolerance is not None:
            source_fields['ConvergenceTolerance'] = convergence_tolerance
        if fan_control_type is not None:
            source_fields['FanControlType'] = fan_control_type
        if minimum_fan_turn_down_ratio is not None:
            source_fields['MinimumFanTurnDownRatio'] = minimum_fan_turn_down_ratio
        if heating_control_type is not None:
            source_fields['HeatingControlType'] = heating_control_type
        if design_heating_discharge_air_temperature is not None:
            source_fields['DesignHeatingDischargeAirTemperature'] = design_heating_discharge_air_temperature
        if high_limit_heating_discharge_air_temperature is not None:
            source_fields['HighLimitHeatingDischargeAirTemperature'] = high_limit_heating_discharge_air_temperature
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_AirTerminalSingleDuctSeriesPIUReheat',
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
