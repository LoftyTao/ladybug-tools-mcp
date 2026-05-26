'MCP tool for detailed_hvac_sizing_zone.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_sizing_zone tool.'

    @mcp.tool(
        name='sizing_zone',
        description=(
            'Create IB_SizingZone, the Ironbug and EnergyPlus Sizing:Zone object used by an IB_ThermalZone for zone design airflow, supply-air temperature, humidity-ratio, DOAS, humidistat schedule, and zone load sizing inputs. Use it as ThermalZone sizing metadata, not as Honeybee Room geometry, zone equipment, thermostat, or a sizing-result reader. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'sizing', 'thermal-zone', 'ventilation', 'doas', 'temperature', 'humidity-ratio', 'humidistat', 'author', 'component'},
        timeout=20,
    )
    def create_ironbug_sizing_zone(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json for the Ironbug model."),
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
            Field(description="Stable identifier for the new IB_SizingZone object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        zone_cooling_design_supply_air_temperature_input_method: Annotated[
            str | None,
            Field(description='Optional cooling supply-air temperature input method, SupplyAirTemperature or TemperatureDifference.'),
        ] = None,
        zone_cooling_design_supply_air_temperature: Annotated[
            float | None,
            Field(description='Optional zone cooling design supply-air temperature in deg C.'),
        ] = None,
        zone_cooling_design_supply_air_temperature_difference: Annotated[
            float | None,
            Field(description='Optional ZoneCoolingDesignSupplyAirTemperatureDifference value; maps to Ironbug IB_SizingZone field ZoneCoolingDesignSupplyAirTemperatureDifference.'),
        ] = None,
        zone_heating_design_supply_air_temperature_input_method: Annotated[
            str | None,
            Field(description='Optional heating supply-air temperature input method, SupplyAirTemperature or TemperatureDifference.'),
        ] = None,
        zone_heating_design_supply_air_temperature: Annotated[
            float | None,
            Field(description='Optional zone heating design supply-air temperature in deg C.'),
        ] = None,
        zone_heating_design_supply_air_temperature_difference: Annotated[
            float | None,
            Field(description='Optional ZoneHeatingDesignSupplyAirTemperatureDifference value; maps to Ironbug IB_SizingZone field ZoneHeatingDesignSupplyAirTemperatureDifference.'),
        ] = None,
        zone_cooling_design_supply_air_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional zone cooling design supply-air humidity ratio in kgWater/kgDryAir.'),
        ] = None,
        zone_heating_design_supply_air_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional zone heating design supply-air humidity ratio in kgWater/kgDryAir.'),
        ] = None,
        zone_heating_sizing_factor: Annotated[
            float | None,
            Field(description='Optional ZoneHeatingSizingFactor value; maps to Ironbug IB_SizingZone field ZoneHeatingSizingFactor.'),
        ] = None,
        zone_cooling_sizing_factor: Annotated[
            float | None,
            Field(description='Optional ZoneCoolingSizingFactor value; maps to Ironbug IB_SizingZone field ZoneCoolingSizingFactor.'),
        ] = None,
        cooling_design_air_flow_method: Annotated[
            str | None,
            Field(description='Optional CoolingDesignAirFlowMethod value; maps to Ironbug IB_SizingZone field CoolingDesignAirFlowMethod.'),
        ] = None,
        cooling_design_air_flow_rate: Annotated[
            float | None,
            Field(description='Optional CoolingDesignAirFlowRate value; maps to Ironbug IB_SizingZone field CoolingDesignAirFlowRate.'),
        ] = None,
        cooling_minimum_air_flowper_zone_floor_area: Annotated[
            float | None,
            Field(description='Optional CoolingMinimumAirFlowperZoneFloorArea value; maps to Ironbug IB_SizingZone field CoolingMinimumAirFlowperZoneFloorArea.'),
        ] = None,
        cooling_minimum_air_flow: Annotated[
            float | None,
            Field(description='Optional CoolingMinimumAirFlow value; maps to Ironbug IB_SizingZone field CoolingMinimumAirFlow.'),
        ] = None,
        cooling_minimum_air_flow_fraction: Annotated[
            float | None,
            Field(description='Optional CoolingMinimumAirFlowFraction value; maps to Ironbug IB_SizingZone field CoolingMinimumAirFlowFraction.'),
        ] = None,
        heating_design_air_flow_method: Annotated[
            str | None,
            Field(description='Optional HeatingDesignAirFlowMethod value; maps to Ironbug IB_SizingZone field HeatingDesignAirFlowMethod.'),
        ] = None,
        heating_design_air_flow_rate: Annotated[
            float | None,
            Field(description='Optional HeatingDesignAirFlowRate value; maps to Ironbug IB_SizingZone field HeatingDesignAirFlowRate.'),
        ] = None,
        heating_maximum_air_flowper_zone_floor_area: Annotated[
            float | None,
            Field(description='Optional HeatingMaximumAirFlowperZoneFloorArea value; maps to Ironbug IB_SizingZone field HeatingMaximumAirFlowperZoneFloorArea.'),
        ] = None,
        heating_maximum_air_flow: Annotated[
            float | None,
            Field(description='Optional HeatingMaximumAirFlow value; maps to Ironbug IB_SizingZone field HeatingMaximumAirFlow.'),
        ] = None,
        heating_maximum_air_flow_fraction: Annotated[
            float | None,
            Field(description='Optional HeatingMaximumAirFlowFraction value; maps to Ironbug IB_SizingZone field HeatingMaximumAirFlowFraction.'),
        ] = None,
        accountfor_dedicated_outdoor_air_system: Annotated[
            bool | str | None,
            Field(description='Optional AccountforDedicatedOutdoorAirSystem value; maps to Ironbug IB_SizingZone field AccountforDedicatedOutdoorAirSystem.'),
        ] = None,
        dedicated_outdoor_air_system_control_strategy: Annotated[
            str | None,
            Field(description='Optional DedicatedOutdoorAirSystemControlStrategy value; maps to Ironbug IB_SizingZone field DedicatedOutdoorAirSystemControlStrategy.'),
        ] = None,
        dedicated_outdoor_air_low_setpoint_temperaturefor_design: Annotated[
            float | str | None,
            Field(description='Optional DedicatedOutdoorAirLowSetpointTemperatureforDesign value; maps to Ironbug IB_SizingZone field DedicatedOutdoorAirLowSetpointTemperatureforDesign.'),
        ] = None,
        dedicated_outdoor_air_high_setpoint_temperaturefor_design: Annotated[
            float | str | None,
            Field(description='Optional DedicatedOutdoorAirHighSetpointTemperatureforDesign value; maps to Ironbug IB_SizingZone field DedicatedOutdoorAirHighSetpointTemperatureforDesign.'),
        ] = None,
        zone_load_sizing_method: Annotated[
            str | None,
            Field(description='Optional ZoneLoadSizingMethod value; maps to Ironbug IB_SizingZone field ZoneLoadSizingMethod.'),
        ] = None,
        zone_latent_cooling_design_supply_air_humidity_ratio_input_method: Annotated[
            str | None,
            Field(description='Optional ZoneLatentCoolingDesignSupplyAirHumidityRatioInputMethod value; maps to Ironbug IB_SizingZone field ZoneLatentCoolingDesignSupplyAirHumidityRatioInputMethod.'),
        ] = None,
        zone_dehumidification_design_supply_air_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional ZoneDehumidificationDesignSupplyAirHumidityRatio value; maps to Ironbug IB_SizingZone field ZoneDehumidificationDesignSupplyAirHumidityRatio.'),
        ] = None,
        zone_cooling_design_supply_air_humidity_ratio_difference: Annotated[
            float | None,
            Field(description='Optional ZoneCoolingDesignSupplyAirHumidityRatioDifference value; maps to Ironbug IB_SizingZone field ZoneCoolingDesignSupplyAirHumidityRatioDifference.'),
        ] = None,
        zone_latent_heating_design_supply_air_humidity_ratio_input_method: Annotated[
            str | None,
            Field(description='Optional ZoneLatentHeatingDesignSupplyAirHumidityRatioInputMethod value; maps to Ironbug IB_SizingZone field ZoneLatentHeatingDesignSupplyAirHumidityRatioInputMethod.'),
        ] = None,
        zone_humidification_design_supply_air_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional ZoneHumidificationDesignSupplyAirHumidityRatio value; maps to Ironbug IB_SizingZone field ZoneHumidificationDesignSupplyAirHumidityRatio.'),
        ] = None,
        zone_humidification_design_supply_air_humidity_ratio_difference: Annotated[
            float | None,
            Field(description='Optional ZoneHumidificationDesignSupplyAirHumidityRatioDifference value; maps to Ironbug IB_SizingZone field ZoneHumidificationDesignSupplyAirHumidityRatioDifference.'),
        ] = None,
        zone_humidistat_dehumidification_set_point_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for ZoneHumidistatDehumidificationSetPointSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_SizingZone field ZoneHumidistatDehumidificationSetPointSchedule (IB_Schedule).'),
        ] = None,
        zone_humidistat_humidification_set_point_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for ZoneHumidistatHumidificationSetPointSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_SizingZone field ZoneHumidistatHumidificationSetPointSchedule (IB_Schedule).'),
        ] = None,
        design_zone_air_distribution_effectivenessin_cooling_mode: Annotated[
            float | None,
            Field(description='Optional DesignZoneAirDistributionEffectivenessinCoolingMode value; maps to Ironbug IB_SizingZone field DesignZoneAirDistributionEffectivenessinCoolingMode.'),
        ] = None,
        design_zone_air_distribution_effectivenessin_heating_mode: Annotated[
            float | None,
            Field(description='Optional DesignZoneAirDistributionEffectivenessinHeatingMode value; maps to Ironbug IB_SizingZone field DesignZoneAirDistributionEffectivenessinHeatingMode.'),
        ] = None,
        design_zone_secondary_recirculation_fraction: Annotated[
            float | None,
            Field(description='Optional DesignZoneSecondaryRecirculationFraction value; maps to Ironbug IB_SizingZone field DesignZoneSecondaryRecirculationFraction.'),
        ] = None,
        design_minimum_zone_ventilation_efficiency: Annotated[
            float | None,
            Field(description='Optional DesignMinimumZoneVentilationEfficiency value; maps to Ironbug IB_SizingZone field DesignMinimumZoneVentilationEfficiency.'),
        ] = None,
        sizing_option: Annotated[
            str | None,
            Field(description='Optional SizingOption value; maps to Ironbug IB_SizingZone field SizingOption.'),
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
        """Create Ironbug thermal-zone sizing inputs."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if zone_cooling_design_supply_air_temperature_input_method is not None:
            source_fields['ZoneCoolingDesignSupplyAirTemperatureInputMethod'] = zone_cooling_design_supply_air_temperature_input_method
        if zone_cooling_design_supply_air_temperature is not None:
            source_fields['ZoneCoolingDesignSupplyAirTemperature'] = zone_cooling_design_supply_air_temperature
        if zone_cooling_design_supply_air_temperature_difference is not None:
            source_fields['ZoneCoolingDesignSupplyAirTemperatureDifference'] = zone_cooling_design_supply_air_temperature_difference
        if zone_heating_design_supply_air_temperature_input_method is not None:
            source_fields['ZoneHeatingDesignSupplyAirTemperatureInputMethod'] = zone_heating_design_supply_air_temperature_input_method
        if zone_heating_design_supply_air_temperature is not None:
            source_fields['ZoneHeatingDesignSupplyAirTemperature'] = zone_heating_design_supply_air_temperature
        if zone_heating_design_supply_air_temperature_difference is not None:
            source_fields['ZoneHeatingDesignSupplyAirTemperatureDifference'] = zone_heating_design_supply_air_temperature_difference
        if zone_cooling_design_supply_air_humidity_ratio is not None:
            source_fields['ZoneCoolingDesignSupplyAirHumidityRatio'] = zone_cooling_design_supply_air_humidity_ratio
        if zone_heating_design_supply_air_humidity_ratio is not None:
            source_fields['ZoneHeatingDesignSupplyAirHumidityRatio'] = zone_heating_design_supply_air_humidity_ratio
        if zone_heating_sizing_factor is not None:
            source_fields['ZoneHeatingSizingFactor'] = zone_heating_sizing_factor
        if zone_cooling_sizing_factor is not None:
            source_fields['ZoneCoolingSizingFactor'] = zone_cooling_sizing_factor
        if cooling_design_air_flow_method is not None:
            source_fields['CoolingDesignAirFlowMethod'] = cooling_design_air_flow_method
        if cooling_design_air_flow_rate is not None:
            source_fields['CoolingDesignAirFlowRate'] = cooling_design_air_flow_rate
        if cooling_minimum_air_flowper_zone_floor_area is not None:
            source_fields['CoolingMinimumAirFlowperZoneFloorArea'] = cooling_minimum_air_flowper_zone_floor_area
        if cooling_minimum_air_flow is not None:
            source_fields['CoolingMinimumAirFlow'] = cooling_minimum_air_flow
        if cooling_minimum_air_flow_fraction is not None:
            source_fields['CoolingMinimumAirFlowFraction'] = cooling_minimum_air_flow_fraction
        if heating_design_air_flow_method is not None:
            source_fields['HeatingDesignAirFlowMethod'] = heating_design_air_flow_method
        if heating_design_air_flow_rate is not None:
            source_fields['HeatingDesignAirFlowRate'] = heating_design_air_flow_rate
        if heating_maximum_air_flowper_zone_floor_area is not None:
            source_fields['HeatingMaximumAirFlowperZoneFloorArea'] = heating_maximum_air_flowper_zone_floor_area
        if heating_maximum_air_flow is not None:
            source_fields['HeatingMaximumAirFlow'] = heating_maximum_air_flow
        if heating_maximum_air_flow_fraction is not None:
            source_fields['HeatingMaximumAirFlowFraction'] = heating_maximum_air_flow_fraction
        if accountfor_dedicated_outdoor_air_system is not None:
            source_fields['AccountforDedicatedOutdoorAirSystem'] = accountfor_dedicated_outdoor_air_system
        if dedicated_outdoor_air_system_control_strategy is not None:
            source_fields['DedicatedOutdoorAirSystemControlStrategy'] = dedicated_outdoor_air_system_control_strategy
        if dedicated_outdoor_air_low_setpoint_temperaturefor_design is not None:
            source_fields['DedicatedOutdoorAirLowSetpointTemperatureforDesign'] = dedicated_outdoor_air_low_setpoint_temperaturefor_design
        if dedicated_outdoor_air_high_setpoint_temperaturefor_design is not None:
            source_fields['DedicatedOutdoorAirHighSetpointTemperatureforDesign'] = dedicated_outdoor_air_high_setpoint_temperaturefor_design
        if zone_load_sizing_method is not None:
            source_fields['ZoneLoadSizingMethod'] = zone_load_sizing_method
        if zone_latent_cooling_design_supply_air_humidity_ratio_input_method is not None:
            source_fields['ZoneLatentCoolingDesignSupplyAirHumidityRatioInputMethod'] = zone_latent_cooling_design_supply_air_humidity_ratio_input_method
        if zone_dehumidification_design_supply_air_humidity_ratio is not None:
            source_fields['ZoneDehumidificationDesignSupplyAirHumidityRatio'] = zone_dehumidification_design_supply_air_humidity_ratio
        if zone_cooling_design_supply_air_humidity_ratio_difference is not None:
            source_fields['ZoneCoolingDesignSupplyAirHumidityRatioDifference'] = zone_cooling_design_supply_air_humidity_ratio_difference
        if zone_latent_heating_design_supply_air_humidity_ratio_input_method is not None:
            source_fields['ZoneLatentHeatingDesignSupplyAirHumidityRatioInputMethod'] = zone_latent_heating_design_supply_air_humidity_ratio_input_method
        if zone_humidification_design_supply_air_humidity_ratio is not None:
            source_fields['ZoneHumidificationDesignSupplyAirHumidityRatio'] = zone_humidification_design_supply_air_humidity_ratio
        if zone_humidification_design_supply_air_humidity_ratio_difference is not None:
            source_fields['ZoneHumidificationDesignSupplyAirHumidityRatioDifference'] = zone_humidification_design_supply_air_humidity_ratio_difference
        if zone_humidistat_dehumidification_set_point_schedule_target is not None:
            source_field_targets['ZoneHumidistatDehumidificationSetPointSchedule'] = zone_humidistat_dehumidification_set_point_schedule_target
        if zone_humidistat_humidification_set_point_schedule_target is not None:
            source_field_targets['ZoneHumidistatHumidificationSetPointSchedule'] = zone_humidistat_humidification_set_point_schedule_target
        if design_zone_air_distribution_effectivenessin_cooling_mode is not None:
            source_fields['DesignZoneAirDistributionEffectivenessinCoolingMode'] = design_zone_air_distribution_effectivenessin_cooling_mode
        if design_zone_air_distribution_effectivenessin_heating_mode is not None:
            source_fields['DesignZoneAirDistributionEffectivenessinHeatingMode'] = design_zone_air_distribution_effectivenessin_heating_mode
        if design_zone_secondary_recirculation_fraction is not None:
            source_fields['DesignZoneSecondaryRecirculationFraction'] = design_zone_secondary_recirculation_fraction
        if design_minimum_zone_ventilation_efficiency is not None:
            source_fields['DesignMinimumZoneVentilationEfficiency'] = design_minimum_zone_ventilation_efficiency
        if sizing_option is not None:
            source_fields['SizingOption'] = sizing_option
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SizingZone',
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
