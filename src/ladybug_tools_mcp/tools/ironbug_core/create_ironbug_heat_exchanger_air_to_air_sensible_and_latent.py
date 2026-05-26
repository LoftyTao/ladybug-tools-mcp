'MCP tool for detailed_hvac_heat_exchanger_air_to_air_sensible_and_latent.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_heat_exchanger_air_to_air_sensible_and_latent tool.'

    @mcp.tool(
        name='heat_exchanger_air_to_air_sensible_and_latent',
        description=(
            'Create IB_HeatExchangerAirToAirSensibleAndLatent, an EnergyPlus HeatExchanger:AirToAir:SensibleAndLatent air-loop heat-recovery object for supply and exhaust air streams. Use it for ERV/outdoor-air paths with sensible/latent effectiveness, economizer lockout, frost control, and optional effectiveness curves; this is not a hydronic or ground heat exchanger. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'air-loop',
            'air-to-air',
            'heat-exchanger',
            'heat-recovery',
            'energy-recovery',
            'ventilation',
            'outdoor-air',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_heat_exchanger_air_to_air_sensible_and_latent(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, for example garden_create['garden_root']."),
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
            Field(description="Stable identifier for the new IB_HeatExchangerAirToAirSensibleAndLatent object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for AvailabilitySchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_HeatExchangerAirToAirSensibleAndLatent field AvailabilitySchedule (IB_Schedule).'),
        ] = None,
        nominal_supply_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional nominal primary supply air flow rate in m3/s, or autosize string, for the heat-recovery unit; maps to NominalSupplyAirFlowRate.'),
        ] = None,
        sensible_effectivenessat100_heating_air_flow: Annotated[
            float | None,
            Field(description='Optional sensible heat-recovery effectiveness at 100 percent heating airflow; maps to SensibleEffectivenessat100HeatingAirFlow.'),
        ] = None,
        latent_effectivenessat100_heating_air_flow: Annotated[
            float | None,
            Field(description='Optional latent heat-recovery effectiveness at 100 percent heating airflow; maps to LatentEffectivenessat100HeatingAirFlow.'),
        ] = None,
        sensible_effectivenessat75_heating_air_flow: Annotated[
            str | float | int | bool | None,
            Field(description='Optional SensibleEffectivenessat75HeatingAirFlow value; maps to Ironbug IB_HeatExchangerAirToAirSensibleAndLatent field SensibleEffectivenessat75HeatingAirFlow.'),
        ] = None,
        latent_effectivenessat75_heating_air_flow: Annotated[
            str | float | int | bool | None,
            Field(description='Optional LatentEffectivenessat75HeatingAirFlow value; maps to Ironbug IB_HeatExchangerAirToAirSensibleAndLatent field LatentEffectivenessat75HeatingAirFlow.'),
        ] = None,
        sensible_effectivenessat100_cooling_air_flow: Annotated[
            float | None,
            Field(description='Optional SensibleEffectivenessat100CoolingAirFlow value; maps to Ironbug IB_HeatExchangerAirToAirSensibleAndLatent field SensibleEffectivenessat100CoolingAirFlow.'),
        ] = None,
        latent_effectivenessat100_cooling_air_flow: Annotated[
            float | None,
            Field(description='Optional LatentEffectivenessat100CoolingAirFlow value; maps to Ironbug IB_HeatExchangerAirToAirSensibleAndLatent field LatentEffectivenessat100CoolingAirFlow.'),
        ] = None,
        sensible_effectivenessat75_cooling_air_flow: Annotated[
            str | float | int | bool | None,
            Field(description='Optional SensibleEffectivenessat75CoolingAirFlow value; maps to Ironbug IB_HeatExchangerAirToAirSensibleAndLatent field SensibleEffectivenessat75CoolingAirFlow.'),
        ] = None,
        latent_effectivenessat75_cooling_air_flow: Annotated[
            str | float | int | bool | None,
            Field(description='Optional LatentEffectivenessat75CoolingAirFlow value; maps to Ironbug IB_HeatExchangerAirToAirSensibleAndLatent field LatentEffectivenessat75CoolingAirFlow.'),
        ] = None,
        nominal_electric_power: Annotated[
            float | None,
            Field(description='Optional NominalElectricPower value; maps to Ironbug IB_HeatExchangerAirToAirSensibleAndLatent field NominalElectricPower.'),
        ] = None,
        supply_air_outlet_temperature_control: Annotated[
            bool | str | None,
            Field(description='Optional SupplyAirOutletTemperatureControl value; maps to Ironbug IB_HeatExchangerAirToAirSensibleAndLatent field SupplyAirOutletTemperatureControl.'),
        ] = None,
        heat_exchanger_type: Annotated[
            str | None,
            Field(description='Optional air-to-air heat exchanger type such as Plate or Rotary; maps to HeatExchangerType.'),
        ] = None,
        frost_control_type: Annotated[
            str | None,
            Field(description='Optional frost-control method for winter heat recovery, such as None, ExhaustOnly, or MinimumExhaustTemperature; maps to FrostControlType.'),
        ] = None,
        threshold_temperature: Annotated[
            float | None,
            Field(description='Optional ThresholdTemperature value; maps to Ironbug IB_HeatExchangerAirToAirSensibleAndLatent field ThresholdTemperature.'),
        ] = None,
        initial_defrost_time_fraction: Annotated[
            float | None,
            Field(description='Optional InitialDefrostTimeFraction value; maps to Ironbug IB_HeatExchangerAirToAirSensibleAndLatent field InitialDefrostTimeFraction.'),
        ] = None,
        rateof_defrost_time_fraction_increase: Annotated[
            float | None,
            Field(description='Optional RateofDefrostTimeFractionIncrease value; maps to Ironbug IB_HeatExchangerAirToAirSensibleAndLatent field RateofDefrostTimeFractionIncrease.'),
        ] = None,
        economizer_lockout: Annotated[
            bool | str | None,
            Field(description='Optional air-side economizer lockout flag for bypassing heat recovery during economizer operation; maps to EconomizerLockout.'),
        ] = None,
        sensible_effectivenessof_heating_air_flow_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for SensibleEffectivenessofHeatingAirFlowCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_HeatExchangerAirToAirSensibleAndLatent field SensibleEffectivenessofHeatingAirFlowCurve (IB_Curve).'),
        ] = None,
        latent_effectivenessof_heating_air_flow_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for LatentEffectivenessofHeatingAirFlowCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_HeatExchangerAirToAirSensibleAndLatent field LatentEffectivenessofHeatingAirFlowCurve (IB_Curve).'),
        ] = None,
        sensible_effectivenessof_cooling_air_flow_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for SensibleEffectivenessofCoolingAirFlowCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_HeatExchangerAirToAirSensibleAndLatent field SensibleEffectivenessofCoolingAirFlowCurve (IB_Curve).'),
        ] = None,
        latent_effectivenessof_cooling_air_flow_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for LatentEffectivenessofCoolingAirFlowCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_HeatExchangerAirToAirSensibleAndLatent field LatentEffectivenessofCoolingAirFlowCurve (IB_Curve).'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus object name for this sensible/latent air-to-air heat exchanger; maps to Name.'),
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
        """Create IB_HeatExchangerAirToAirSensibleAndLatent as a reviewed Ironbug LoopObjs / AirLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if nominal_supply_air_flow_rate is not None:
            source_fields['NominalSupplyAirFlowRate'] = nominal_supply_air_flow_rate
        if sensible_effectivenessat100_heating_air_flow is not None:
            source_fields['SensibleEffectivenessat100HeatingAirFlow'] = sensible_effectivenessat100_heating_air_flow
        if latent_effectivenessat100_heating_air_flow is not None:
            source_fields['LatentEffectivenessat100HeatingAirFlow'] = latent_effectivenessat100_heating_air_flow
        if sensible_effectivenessat75_heating_air_flow is not None:
            source_fields['SensibleEffectivenessat75HeatingAirFlow'] = sensible_effectivenessat75_heating_air_flow
        if latent_effectivenessat75_heating_air_flow is not None:
            source_fields['LatentEffectivenessat75HeatingAirFlow'] = latent_effectivenessat75_heating_air_flow
        if sensible_effectivenessat100_cooling_air_flow is not None:
            source_fields['SensibleEffectivenessat100CoolingAirFlow'] = sensible_effectivenessat100_cooling_air_flow
        if latent_effectivenessat100_cooling_air_flow is not None:
            source_fields['LatentEffectivenessat100CoolingAirFlow'] = latent_effectivenessat100_cooling_air_flow
        if sensible_effectivenessat75_cooling_air_flow is not None:
            source_fields['SensibleEffectivenessat75CoolingAirFlow'] = sensible_effectivenessat75_cooling_air_flow
        if latent_effectivenessat75_cooling_air_flow is not None:
            source_fields['LatentEffectivenessat75CoolingAirFlow'] = latent_effectivenessat75_cooling_air_flow
        if nominal_electric_power is not None:
            source_fields['NominalElectricPower'] = nominal_electric_power
        if supply_air_outlet_temperature_control is not None:
            source_fields['SupplyAirOutletTemperatureControl'] = supply_air_outlet_temperature_control
        if heat_exchanger_type is not None:
            source_fields['HeatExchangerType'] = heat_exchanger_type
        if frost_control_type is not None:
            source_fields['FrostControlType'] = frost_control_type
        if threshold_temperature is not None:
            source_fields['ThresholdTemperature'] = threshold_temperature
        if initial_defrost_time_fraction is not None:
            source_fields['InitialDefrostTimeFraction'] = initial_defrost_time_fraction
        if rateof_defrost_time_fraction_increase is not None:
            source_fields['RateofDefrostTimeFractionIncrease'] = rateof_defrost_time_fraction_increase
        if economizer_lockout is not None:
            source_fields['EconomizerLockout'] = economizer_lockout
        if sensible_effectivenessof_heating_air_flow_curve_target is not None:
            source_field_targets['SensibleEffectivenessofHeatingAirFlowCurve'] = sensible_effectivenessof_heating_air_flow_curve_target
        if latent_effectivenessof_heating_air_flow_curve_target is not None:
            source_field_targets['LatentEffectivenessofHeatingAirFlowCurve'] = latent_effectivenessof_heating_air_flow_curve_target
        if sensible_effectivenessof_cooling_air_flow_curve_target is not None:
            source_field_targets['SensibleEffectivenessofCoolingAirFlowCurve'] = sensible_effectivenessof_cooling_air_flow_curve_target
        if latent_effectivenessof_cooling_air_flow_curve_target is not None:
            source_field_targets['LatentEffectivenessofCoolingAirFlowCurve'] = latent_effectivenessof_cooling_air_flow_curve_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_HeatExchangerAirToAirSensibleAndLatent',
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
