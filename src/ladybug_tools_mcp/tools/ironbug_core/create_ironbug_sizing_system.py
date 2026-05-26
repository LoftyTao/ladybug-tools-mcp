'MCP tool for detailed_hvac_sizing_system.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_sizing_system tool.'

    @mcp.tool(
        name='sizing_system',
        description=(
            'Create IB_SizingSystem, the Ironbug and EnergyPlus Sizing:System object for central forced-air AirLoopHVAC sizing inputs. It controls system design airflow, outdoor-air method, supply-air temperatures and humidity ratios, and heating/cooling design capacity methods; it does not create an air loop, coil, fan, or simulation result. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'sizing', 'air-loop', 'ventilation', 'outdoor-air', 'heating', 'cooling', 'humidity-ratio', 'author', 'component'},
        timeout=20,
    )
    def create_ironbug_sizing_system(
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
            Field(description="Stable identifier for the new IB_SizingSystem object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        typeof_loadto_size_on: Annotated[
            str | None,
            Field(
                description="Optional system sizing load basis, such as Sensible, Latent, Total, or VentilationRequirement."
            ),
        ] = None,
        design_outdoor_air_flow_rate: Annotated[
            float | str | None,
            Field(
                description="Optional system design outdoor-air flow rate in m3/s, or autosize text accepted by the source field."
            ),
        ] = None,
        central_heating_maximum_system_air_flow_ratio: Annotated[
            float | str | None,
            Field(description='Optional CentralHeatingMaximumSystemAirFlowRatio value; maps to Ironbug IB_SizingSystem field CentralHeatingMaximumSystemAirFlowRatio.'),
        ] = None,
        preheat_design_temperature: Annotated[
            float | None,
            Field(description='Optional PreheatDesignTemperature value; maps to Ironbug IB_SizingSystem field PreheatDesignTemperature.'),
        ] = None,
        preheat_design_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional PreheatDesignHumidityRatio value; maps to Ironbug IB_SizingSystem field PreheatDesignHumidityRatio.'),
        ] = None,
        precool_design_temperature: Annotated[
            float | None,
            Field(description='Optional PrecoolDesignTemperature value; maps to Ironbug IB_SizingSystem field PrecoolDesignTemperature.'),
        ] = None,
        precool_design_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional PrecoolDesignHumidityRatio value; maps to Ironbug IB_SizingSystem field PrecoolDesignHumidityRatio.'),
        ] = None,
        central_cooling_design_supply_air_temperature: Annotated[
            float | None,
            Field(description='Optional CentralCoolingDesignSupplyAirTemperature value; maps to Ironbug IB_SizingSystem field CentralCoolingDesignSupplyAirTemperature.'),
        ] = None,
        central_heating_design_supply_air_temperature: Annotated[
            float | None,
            Field(description='Optional CentralHeatingDesignSupplyAirTemperature value; maps to Ironbug IB_SizingSystem field CentralHeatingDesignSupplyAirTemperature.'),
        ] = None,
        sizing_option: Annotated[
            str | None,
            Field(description='Optional SizingOption value; maps to Ironbug IB_SizingSystem field SizingOption.'),
        ] = None,
        all_outdoor_airin_cooling: Annotated[
            str | float | int | bool | None,
            Field(description='Optional AllOutdoorAirinCooling value; maps to Ironbug IB_SizingSystem field AllOutdoorAirinCooling.'),
        ] = None,
        all_outdoor_airin_heating: Annotated[
            str | float | int | bool | None,
            Field(description='Optional AllOutdoorAirinHeating value; maps to Ironbug IB_SizingSystem field AllOutdoorAirinHeating.'),
        ] = None,
        central_cooling_design_supply_air_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional CentralCoolingDesignSupplyAirHumidityRatio value; maps to Ironbug IB_SizingSystem field CentralCoolingDesignSupplyAirHumidityRatio.'),
        ] = None,
        central_heating_design_supply_air_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional CentralHeatingDesignSupplyAirHumidityRatio value; maps to Ironbug IB_SizingSystem field CentralHeatingDesignSupplyAirHumidityRatio.'),
        ] = None,
        cooling_design_air_flow_method: Annotated[
            str | None,
            Field(description='Optional CoolingDesignAirFlowMethod value; maps to Ironbug IB_SizingSystem field CoolingDesignAirFlowMethod.'),
        ] = None,
        cooling_design_air_flow_rate: Annotated[
            float | None,
            Field(description='Optional CoolingDesignAirFlowRate value; maps to Ironbug IB_SizingSystem field CoolingDesignAirFlowRate.'),
        ] = None,
        heating_design_air_flow_method: Annotated[
            str | None,
            Field(description='Optional HeatingDesignAirFlowMethod value; maps to Ironbug IB_SizingSystem field HeatingDesignAirFlowMethod.'),
        ] = None,
        heating_design_air_flow_rate: Annotated[
            float | None,
            Field(description='Optional HeatingDesignAirFlowRate value; maps to Ironbug IB_SizingSystem field HeatingDesignAirFlowRate.'),
        ] = None,
        system_outdoor_air_method: Annotated[
            str | None,
            Field(description='Optional SystemOutdoorAirMethod value; maps to Ironbug IB_SizingSystem field SystemOutdoorAirMethod.'),
        ] = None,
        zone_maximum_outdoor_air_fraction: Annotated[
            float | None,
            Field(description='Optional ZoneMaximumOutdoorAirFraction value; maps to Ironbug IB_SizingSystem field ZoneMaximumOutdoorAirFraction.'),
        ] = None,
        cooling_supply_air_flow_rate_per_floor_area: Annotated[
            float | None,
            Field(description='Optional CoolingSupplyAirFlowRatePerFloorArea value; maps to Ironbug IB_SizingSystem field CoolingSupplyAirFlowRatePerFloorArea.'),
        ] = None,
        cooling_fractionof_autosized_cooling_supply_air_flow_rate: Annotated[
            float | None,
            Field(description='Optional CoolingFractionofAutosizedCoolingSupplyAirFlowRate value; maps to Ironbug IB_SizingSystem field CoolingFractionofAutosizedCoolingSupplyAirFlowRate.'),
        ] = None,
        cooling_supply_air_flow_rate_per_unit_cooling_capacity: Annotated[
            float | None,
            Field(description='Optional CoolingSupplyAirFlowRatePerUnitCoolingCapacity value; maps to Ironbug IB_SizingSystem field CoolingSupplyAirFlowRatePerUnitCoolingCapacity.'),
        ] = None,
        heating_supply_air_flow_rate_per_floor_area: Annotated[
            float | None,
            Field(description='Optional HeatingSupplyAirFlowRatePerFloorArea value; maps to Ironbug IB_SizingSystem field HeatingSupplyAirFlowRatePerFloorArea.'),
        ] = None,
        heating_fractionof_autosized_heating_supply_air_flow_rate: Annotated[
            float | None,
            Field(description='Optional HeatingFractionofAutosizedHeatingSupplyAirFlowRate value; maps to Ironbug IB_SizingSystem field HeatingFractionofAutosizedHeatingSupplyAirFlowRate.'),
        ] = None,
        heating_fractionof_autosized_cooling_supply_air_flow_rate: Annotated[
            float | None,
            Field(description='Optional HeatingFractionofAutosizedCoolingSupplyAirFlowRate value; maps to Ironbug IB_SizingSystem field HeatingFractionofAutosizedCoolingSupplyAirFlowRate.'),
        ] = None,
        heating_supply_air_flow_rate_per_unit_heating_capacity: Annotated[
            float | None,
            Field(description='Optional HeatingSupplyAirFlowRatePerUnitHeatingCapacity value; maps to Ironbug IB_SizingSystem field HeatingSupplyAirFlowRatePerUnitHeatingCapacity.'),
        ] = None,
        cooling_design_capacity_method: Annotated[
            str | None,
            Field(description='Optional CoolingDesignCapacityMethod value; maps to Ironbug IB_SizingSystem field CoolingDesignCapacityMethod.'),
        ] = None,
        cooling_design_capacity: Annotated[
            float | str | None,
            Field(description='Optional CoolingDesignCapacity value; maps to Ironbug IB_SizingSystem field CoolingDesignCapacity.'),
        ] = None,
        cooling_design_capacity_per_floor_area: Annotated[
            float | None,
            Field(description='Optional CoolingDesignCapacityPerFloorArea value; maps to Ironbug IB_SizingSystem field CoolingDesignCapacityPerFloorArea.'),
        ] = None,
        fractionof_autosized_cooling_design_capacity: Annotated[
            float | None,
            Field(description='Optional FractionofAutosizedCoolingDesignCapacity value; maps to Ironbug IB_SizingSystem field FractionofAutosizedCoolingDesignCapacity.'),
        ] = None,
        heating_design_capacity_method: Annotated[
            str | None,
            Field(description='Optional HeatingDesignCapacityMethod value; maps to Ironbug IB_SizingSystem field HeatingDesignCapacityMethod.'),
        ] = None,
        heating_design_capacity: Annotated[
            float | str | None,
            Field(description='Optional HeatingDesignCapacity value; maps to Ironbug IB_SizingSystem field HeatingDesignCapacity.'),
        ] = None,
        heating_design_capacity_per_floor_area: Annotated[
            float | None,
            Field(description='Optional HeatingDesignCapacityPerFloorArea value; maps to Ironbug IB_SizingSystem field HeatingDesignCapacityPerFloorArea.'),
        ] = None,
        fractionof_autosized_heating_design_capacity: Annotated[
            float | None,
            Field(description='Optional FractionofAutosizedHeatingDesignCapacity value; maps to Ironbug IB_SizingSystem field FractionofAutosizedHeatingDesignCapacity.'),
        ] = None,
        central_cooling_capacity_control_method: Annotated[
            str | None,
            Field(description='Optional CentralCoolingCapacityControlMethod value; maps to Ironbug IB_SizingSystem field CentralCoolingCapacityControlMethod.'),
        ] = None,
        occupant_diversity: Annotated[
            float | str | None,
            Field(description='Optional OccupantDiversity value; maps to Ironbug IB_SizingSystem field OccupantDiversity.'),
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
        """Create Ironbug central air-loop sizing inputs."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if typeof_loadto_size_on is not None:
            source_fields['TypeofLoadtoSizeOn'] = typeof_loadto_size_on
        if design_outdoor_air_flow_rate is not None:
            source_fields['DesignOutdoorAirFlowRate'] = design_outdoor_air_flow_rate
        source_properties: dict[str, Any] = {}
        if central_heating_maximum_system_air_flow_ratio is not None:
            source_fields['CentralHeatingMaximumSystemAirFlowRatio'] = central_heating_maximum_system_air_flow_ratio
        if preheat_design_temperature is not None:
            source_fields['PreheatDesignTemperature'] = preheat_design_temperature
        if preheat_design_humidity_ratio is not None:
            source_fields['PreheatDesignHumidityRatio'] = preheat_design_humidity_ratio
        if precool_design_temperature is not None:
            source_fields['PrecoolDesignTemperature'] = precool_design_temperature
        if precool_design_humidity_ratio is not None:
            source_fields['PrecoolDesignHumidityRatio'] = precool_design_humidity_ratio
        if central_cooling_design_supply_air_temperature is not None:
            source_fields['CentralCoolingDesignSupplyAirTemperature'] = central_cooling_design_supply_air_temperature
        if central_heating_design_supply_air_temperature is not None:
            source_fields['CentralHeatingDesignSupplyAirTemperature'] = central_heating_design_supply_air_temperature
        if sizing_option is not None:
            source_fields['SizingOption'] = sizing_option
        if all_outdoor_airin_cooling is not None:
            source_fields['AllOutdoorAirinCooling'] = all_outdoor_airin_cooling
        if all_outdoor_airin_heating is not None:
            source_fields['AllOutdoorAirinHeating'] = all_outdoor_airin_heating
        if central_cooling_design_supply_air_humidity_ratio is not None:
            source_fields['CentralCoolingDesignSupplyAirHumidityRatio'] = central_cooling_design_supply_air_humidity_ratio
        if central_heating_design_supply_air_humidity_ratio is not None:
            source_fields['CentralHeatingDesignSupplyAirHumidityRatio'] = central_heating_design_supply_air_humidity_ratio
        if cooling_design_air_flow_method is not None:
            source_fields['CoolingDesignAirFlowMethod'] = cooling_design_air_flow_method
        if cooling_design_air_flow_rate is not None:
            source_fields['CoolingDesignAirFlowRate'] = cooling_design_air_flow_rate
        if heating_design_air_flow_method is not None:
            source_fields['HeatingDesignAirFlowMethod'] = heating_design_air_flow_method
        if heating_design_air_flow_rate is not None:
            source_fields['HeatingDesignAirFlowRate'] = heating_design_air_flow_rate
        if system_outdoor_air_method is not None:
            source_fields['SystemOutdoorAirMethod'] = system_outdoor_air_method
        if zone_maximum_outdoor_air_fraction is not None:
            source_fields['ZoneMaximumOutdoorAirFraction'] = zone_maximum_outdoor_air_fraction
        if cooling_supply_air_flow_rate_per_floor_area is not None:
            source_fields['CoolingSupplyAirFlowRatePerFloorArea'] = cooling_supply_air_flow_rate_per_floor_area
        if cooling_fractionof_autosized_cooling_supply_air_flow_rate is not None:
            source_fields['CoolingFractionofAutosizedCoolingSupplyAirFlowRate'] = cooling_fractionof_autosized_cooling_supply_air_flow_rate
        if cooling_supply_air_flow_rate_per_unit_cooling_capacity is not None:
            source_fields['CoolingSupplyAirFlowRatePerUnitCoolingCapacity'] = cooling_supply_air_flow_rate_per_unit_cooling_capacity
        if heating_supply_air_flow_rate_per_floor_area is not None:
            source_fields['HeatingSupplyAirFlowRatePerFloorArea'] = heating_supply_air_flow_rate_per_floor_area
        if heating_fractionof_autosized_heating_supply_air_flow_rate is not None:
            source_fields['HeatingFractionofAutosizedHeatingSupplyAirFlowRate'] = heating_fractionof_autosized_heating_supply_air_flow_rate
        if heating_fractionof_autosized_cooling_supply_air_flow_rate is not None:
            source_fields['HeatingFractionofAutosizedCoolingSupplyAirFlowRate'] = heating_fractionof_autosized_cooling_supply_air_flow_rate
        if heating_supply_air_flow_rate_per_unit_heating_capacity is not None:
            source_fields['HeatingSupplyAirFlowRatePerUnitHeatingCapacity'] = heating_supply_air_flow_rate_per_unit_heating_capacity
        if cooling_design_capacity_method is not None:
            source_fields['CoolingDesignCapacityMethod'] = cooling_design_capacity_method
        if cooling_design_capacity is not None:
            source_fields['CoolingDesignCapacity'] = cooling_design_capacity
        if cooling_design_capacity_per_floor_area is not None:
            source_fields['CoolingDesignCapacityPerFloorArea'] = cooling_design_capacity_per_floor_area
        if fractionof_autosized_cooling_design_capacity is not None:
            source_fields['FractionofAutosizedCoolingDesignCapacity'] = fractionof_autosized_cooling_design_capacity
        if heating_design_capacity_method is not None:
            source_fields['HeatingDesignCapacityMethod'] = heating_design_capacity_method
        if heating_design_capacity is not None:
            source_fields['HeatingDesignCapacity'] = heating_design_capacity
        if heating_design_capacity_per_floor_area is not None:
            source_fields['HeatingDesignCapacityPerFloorArea'] = heating_design_capacity_per_floor_area
        if fractionof_autosized_heating_design_capacity is not None:
            source_fields['FractionofAutosizedHeatingDesignCapacity'] = fractionof_autosized_heating_design_capacity
        if central_cooling_capacity_control_method is not None:
            source_fields['CentralCoolingCapacityControlMethod'] = central_cooling_capacity_control_method
        if occupant_diversity is not None:
            source_fields['OccupantDiversity'] = occupant_diversity
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SizingSystem',
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
