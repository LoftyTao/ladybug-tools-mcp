'MCP tool for detailed_hvac_zone_equipment_ideal_loads_air_system.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    add_ironbug_thermal_zone_equipment,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_zone_equipment_ideal_loads_air_system tool.'

    @mcp.tool(
        name='zone_equipment_ideal_loads_air_system',
        description=(
            'Create IB_ZoneHVACIdealLoadsAirSystem, the Ironbug and EnergyPlus ZoneHVAC:IdealLoadsAirSystem zone equipment for ideal heating/cooling loads, outdoor-air controls, humidity controls, and heat-recovery assumptions. Use it as an ideal air system on an IB_ThermalZone, not as a real fan/coil loop, HVAC template, or result reader. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'zone-equipment', 'ideal-air', 'heating', 'cooling', 'outdoor-air', 'heat-recovery', 'thermal-zone', 'author'},
        timeout=20,
    )
    def create_ironbug_zone_hvac_ideal_loads_air_system(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json where the Ironbug model and created ideal-loads zone equipment are stored."),
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
            Field(description="Stable identifier for the new IB_ZoneHVACIdealLoadsAirSystem object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for IdealLoadsAirSystem availability; pass a detailed_hvac_schedule_* target or same-model identifier.'),
        ] = None,
        maximum_heating_supply_air_temperature: Annotated[
            float | None,
            Field(description='Optional MaximumHeatingSupplyAirTemperature value; maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field MaximumHeatingSupplyAirTemperature.'),
        ] = None,
        minimum_cooling_supply_air_temperature: Annotated[
            float | None,
            Field(description='Optional MinimumCoolingSupplyAirTemperature value; maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field MinimumCoolingSupplyAirTemperature.'),
        ] = None,
        maximum_heating_supply_air_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional MaximumHeatingSupplyAirHumidityRatio value; maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field MaximumHeatingSupplyAirHumidityRatio.'),
        ] = None,
        minimum_cooling_supply_air_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional MinimumCoolingSupplyAirHumidityRatio value; maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field MinimumCoolingSupplyAirHumidityRatio.'),
        ] = None,
        heating_limit: Annotated[
            str | None,
            Field(description='Optional heating limit mode for ZoneHVAC:IdealLoadsAirSystem, such as no limit, flow-rate limit, capacity limit, or both when supported by EnergyPlus/Ironbug.'),
        ] = None,
        maximum_heating_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MaximumHeatingAirFlowRate value; maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field MaximumHeatingAirFlowRate.'),
        ] = None,
        maximum_sensible_heating_capacity: Annotated[
            float | str | None,
            Field(description='Optional MaximumSensibleHeatingCapacity value; maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field MaximumSensibleHeatingCapacity.'),
        ] = None,
        cooling_limit: Annotated[
            str | None,
            Field(description='Optional cooling limit mode for ZoneHVAC:IdealLoadsAirSystem, such as no limit, flow-rate limit, capacity limit, or both when supported by EnergyPlus/Ironbug.'),
        ] = None,
        maximum_cooling_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MaximumCoolingAirFlowRate value; maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field MaximumCoolingAirFlowRate.'),
        ] = None,
        maximum_total_cooling_capacity: Annotated[
            float | str | None,
            Field(description='Optional MaximumTotalCoolingCapacity value; maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field MaximumTotalCoolingCapacity.'),
        ] = None,
        heating_availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for HeatingAvailabilitySchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field HeatingAvailabilitySchedule (IB_Schedule).'),
        ] = None,
        cooling_availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for CoolingAvailabilitySchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field CoolingAvailabilitySchedule (IB_Schedule).'),
        ] = None,
        dehumidification_control_type: Annotated[
            str | None,
            Field(description='Optional DehumidificationControlType value; maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field DehumidificationControlType.'),
        ] = None,
        cooling_sensible_heat_ratio: Annotated[
            float | None,
            Field(description='Optional CoolingSensibleHeatRatio value; maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field CoolingSensibleHeatRatio.'),
        ] = None,
        humidification_control_type: Annotated[
            str | None,
            Field(description='Optional HumidificationControlType value; maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field HumidificationControlType.'),
        ] = None,
        demand_controlled_ventilation_type: Annotated[
            str | None,
            Field(description='Optional DemandControlledVentilationType value; maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field DemandControlledVentilationType.'),
        ] = None,
        outdoor_air_economizer_type: Annotated[
            str | None,
            Field(description='Optional OutdoorAirEconomizerType value; maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field OutdoorAirEconomizerType.'),
        ] = None,
        heat_recovery_type: Annotated[
            str | None,
            Field(description='Optional ideal-loads heat-recovery type assumption, used with sensible and latent heat-recovery effectiveness fields.'),
        ] = None,
        sensible_heat_recovery_effectiveness: Annotated[
            float | None,
            Field(description='Optional SensibleHeatRecoveryEffectiveness value; maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field SensibleHeatRecoveryEffectiveness.'),
        ] = None,
        latent_heat_recovery_effectiveness: Annotated[
            float | None,
            Field(description='Optional LatentHeatRecoveryEffectiveness value; maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field LatentHeatRecoveryEffectiveness.'),
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
            Field(description='Optional Name value; maps to Ironbug IB_ZoneHVACIdealLoadsAirSystem field Name.'),
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
        """Create an Ironbug ZoneHVAC:IdealLoadsAirSystem zone-equipment object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if maximum_heating_supply_air_temperature is not None:
            source_fields['MaximumHeatingSupplyAirTemperature'] = maximum_heating_supply_air_temperature
        if minimum_cooling_supply_air_temperature is not None:
            source_fields['MinimumCoolingSupplyAirTemperature'] = minimum_cooling_supply_air_temperature
        if maximum_heating_supply_air_humidity_ratio is not None:
            source_fields['MaximumHeatingSupplyAirHumidityRatio'] = maximum_heating_supply_air_humidity_ratio
        if minimum_cooling_supply_air_humidity_ratio is not None:
            source_fields['MinimumCoolingSupplyAirHumidityRatio'] = minimum_cooling_supply_air_humidity_ratio
        if heating_limit is not None:
            source_fields['HeatingLimit'] = heating_limit
        if maximum_heating_air_flow_rate is not None:
            source_fields['MaximumHeatingAirFlowRate'] = maximum_heating_air_flow_rate
        if maximum_sensible_heating_capacity is not None:
            source_fields['MaximumSensibleHeatingCapacity'] = maximum_sensible_heating_capacity
        if cooling_limit is not None:
            source_fields['CoolingLimit'] = cooling_limit
        if maximum_cooling_air_flow_rate is not None:
            source_fields['MaximumCoolingAirFlowRate'] = maximum_cooling_air_flow_rate
        if maximum_total_cooling_capacity is not None:
            source_fields['MaximumTotalCoolingCapacity'] = maximum_total_cooling_capacity
        if heating_availability_schedule_target is not None:
            source_field_targets['HeatingAvailabilitySchedule'] = heating_availability_schedule_target
        if cooling_availability_schedule_target is not None:
            source_field_targets['CoolingAvailabilitySchedule'] = cooling_availability_schedule_target
        if dehumidification_control_type is not None:
            source_fields['DehumidificationControlType'] = dehumidification_control_type
        if cooling_sensible_heat_ratio is not None:
            source_fields['CoolingSensibleHeatRatio'] = cooling_sensible_heat_ratio
        if humidification_control_type is not None:
            source_fields['HumidificationControlType'] = humidification_control_type
        if demand_controlled_ventilation_type is not None:
            source_fields['DemandControlledVentilationType'] = demand_controlled_ventilation_type
        if outdoor_air_economizer_type is not None:
            source_fields['OutdoorAirEconomizerType'] = outdoor_air_economizer_type
        if heat_recovery_type is not None:
            source_fields['HeatRecoveryType'] = heat_recovery_type
        if sensible_heat_recovery_effectiveness is not None:
            source_fields['SensibleHeatRecoveryEffectiveness'] = sensible_heat_recovery_effectiveness
        if latent_heat_recovery_effectiveness is not None:
            source_fields['LatentHeatRecoveryEffectiveness'] = latent_heat_recovery_effectiveness
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ZoneHVACIdealLoadsAirSystem',
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
