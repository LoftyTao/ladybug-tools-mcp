'MCP tool for detailed_hvac_hvac_system.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_hvac_system tool.'

    @mcp.tool(
        name='hvac_system',
        description=(
            'Create IB_HVACSystem, the top-level Ironbug DetailedHVAC system object that groups AirLoops, PlantLoops, and VRF systems for export/application to OpenStudio. Most projects should use detailed_hvac_create_model because it creates this root automatically; call this only for an intentionally missing or replaced HVACSystem. This does not create Honeybee template HVAC or run Energy. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'hvac-system', 'model', 'air-loop', 'plant-loop', 'vrf', 'author', 'component'},
        timeout=20,
    )
    def create_ironbug_hvac_system(
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
            Field(description="Stable identifier for the new IB_HVACSystem object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        display_name_value: Annotated[
            str | None,
            Field(
                description="Optional alternate DisplayName string stored on the IB_HVACSystem root collection."
            ),
        ] = None,
        air_loops_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_AirLoopHVAC or IB_NoAirLoop targets or same-model identifiers to place in this HVACSystem AirLoops list."
            ),
        ] = None,
        plant_loops_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_PlantLoop targets or same-model identifiers to place in this HVACSystem PlantLoops list."
            ),
        ] = None,
        vrf_systems_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_AirConditionerVariableRefrigerantFlow targets or same-model identifiers to place in this HVACSystem VariableRefrigerantFlows list."
            ),
        ] = None,
        ib_version: Annotated[
            str | None,
            Field(
                description="Optional Ironbug version string stored as HVACSystem metadata; leave unset unless migrating or inspecting a specific .ibjson version."
            ),
        ] = None,
        air_loops_identifiers: Annotated[
            list[str] | None,
            Field(description='Optional inline IB_AirLoopHVAC identifiers for IB_HVACSystem.AirLoops.'),
        ] = None,
        air_loops_name_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline Name value for IB_AirLoopHVAC; maps to Ironbug IB_HVACSystem.AirLoops child field Name.'),
        ] = None,
        air_loops_design_supply_air_flow_rate_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline DesignSupplyAirFlowRate value for IB_AirLoopHVAC; maps to Ironbug IB_HVACSystem.AirLoops child field DesignSupplyAirFlowRate.'),
        ] = None,
        air_loops_design_return_air_flow_fractionof_supply_air_flow_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline DesignReturnAirFlowFractionofSupplyAirFlow value for IB_AirLoopHVAC; maps to Ironbug IB_HVACSystem.AirLoops child field DesignReturnAirFlowFractionofSupplyAirFlow.'),
        ] = None,
        air_loops_availability_schedule_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for AvailabilitySchedule; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.AirLoops child IB_AirLoopHVAC field AvailabilitySchedule.'),
        ] = None,
        air_loops_night_cycle_control_type_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline NightCycleControlType value for IB_AirLoopHVAC; maps to Ironbug IB_HVACSystem.AirLoops child field NightCycleControlType.'),
        ] = None,
        air_loops_availability_managers_targets: Annotated[
            list[list[dict[str, Any] | str] | None] | None,
            Field(description='Optional inline Ironbug object target for AvailabilityManagers; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.AirLoops child IB_AirLoopHVAC field AvailabilityManagers.'),
        ] = None,
        plant_loops_identifiers: Annotated[
            list[str] | None,
            Field(description='Optional inline IB_PlantLoop identifiers for IB_HVACSystem.PlantLoops.'),
        ] = None,
        plant_loops_name_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline Name value for IB_PlantLoop; maps to Ironbug IB_HVACSystem.PlantLoops child field Name.'),
        ] = None,
        plant_loops_load_distribution_scheme_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline LoadDistributionScheme value for IB_PlantLoop; maps to Ironbug IB_HVACSystem.PlantLoops child field LoadDistributionScheme.'),
        ] = None,
        plant_loops_fluid_type_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline FluidType value for IB_PlantLoop; maps to Ironbug IB_HVACSystem.PlantLoops child field FluidType.'),
        ] = None,
        plant_loops_glycol_concentration_values: Annotated[
            list[int | None] | None,
            Field(description='Optional inline GlycolConcentration value for IB_PlantLoop; maps to Ironbug IB_HVACSystem.PlantLoops child field GlycolConcentration.'),
        ] = None,
        plant_loops_maximum_loop_temperature_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline MaximumLoopTemperature value for IB_PlantLoop; maps to Ironbug IB_HVACSystem.PlantLoops child field MaximumLoopTemperature.'),
        ] = None,
        plant_loops_minimum_loop_temperature_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline MinimumLoopTemperature value for IB_PlantLoop; maps to Ironbug IB_HVACSystem.PlantLoops child field MinimumLoopTemperature.'),
        ] = None,
        plant_loops_maximum_loop_flow_rate_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline MaximumLoopFlowRate value for IB_PlantLoop; maps to Ironbug IB_HVACSystem.PlantLoops child field MaximumLoopFlowRate.'),
        ] = None,
        plant_loops_minimum_loop_flow_rate_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline MinimumLoopFlowRate value for IB_PlantLoop; maps to Ironbug IB_HVACSystem.PlantLoops child field MinimumLoopFlowRate.'),
        ] = None,
        plant_loops_plant_loop_volume_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline PlantLoopVolume value for IB_PlantLoop; maps to Ironbug IB_HVACSystem.PlantLoops child field PlantLoopVolume.'),
        ] = None,
        plant_loops_common_pipe_simulation_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline CommonPipeSimulation value for IB_PlantLoop; maps to Ironbug IB_HVACSystem.PlantLoops child field CommonPipeSimulation.'),
        ] = None,
        plant_loops_plant_equipment_operation_heating_load_schedule_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for PlantEquipmentOperationHeatingLoadSchedule; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.PlantLoops child IB_PlantLoop field PlantEquipmentOperationHeatingLoadSchedule.'),
        ] = None,
        plant_loops_plant_equipment_operation_cooling_load_schedule_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for PlantEquipmentOperationCoolingLoadSchedule; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.PlantLoops child IB_PlantLoop field PlantEquipmentOperationCoolingLoadSchedule.'),
        ] = None,
        plant_loops_primary_plant_equipment_operation_scheme_schedule_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for PrimaryPlantEquipmentOperationSchemeSchedule; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.PlantLoops child IB_PlantLoop field PrimaryPlantEquipmentOperationSchemeSchedule.'),
        ] = None,
        plant_loops_component_setpoint_operation_scheme_schedule_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for ComponentSetpointOperationSchemeSchedule; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.PlantLoops child IB_PlantLoop field ComponentSetpointOperationSchemeSchedule.'),
        ] = None,
        plant_loops_availability_managers_targets: Annotated[
            list[list[dict[str, Any] | str] | None] | None,
            Field(description='Optional inline Ironbug object target for AvailabilityManagers; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.PlantLoops child IB_PlantLoop field AvailabilityManagers.'),
        ] = None,
        variable_refrigerant_flows_identifiers: Annotated[
            list[str] | None,
            Field(description='Optional inline IB_AirConditionerVariableRefrigerantFlow identifiers for IB_HVACSystem.VariableRefrigerantFlows.'),
        ] = None,
        variable_refrigerant_flows_name_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline Name value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field Name.'),
        ] = None,
        variable_refrigerant_flows_availability_schedule_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for AvailabilitySchedule; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field AvailabilitySchedule.'),
        ] = None,
        variable_refrigerant_flows_gross_rated_total_cooling_capacity_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline GrossRatedTotalCoolingCapacity value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field GrossRatedTotalCoolingCapacity.'),
        ] = None,
        variable_refrigerant_flows_gross_rated_cooling_cop_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline GrossRatedCoolingCOP value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field GrossRatedCoolingCOP.'),
        ] = None,
        variable_refrigerant_flows_rated_total_cooling_capacity_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline RatedTotalCoolingCapacity value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field RatedTotalCoolingCapacity.'),
        ] = None,
        variable_refrigerant_flows_rated_cooling_cop_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline RatedCoolingCOP value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field RatedCoolingCOP.'),
        ] = None,
        variable_refrigerant_flows_minimum_outdoor_temperaturein_cooling_mode_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline MinimumOutdoorTemperatureinCoolingMode value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field MinimumOutdoorTemperatureinCoolingMode.'),
        ] = None,
        variable_refrigerant_flows_maximum_outdoor_temperaturein_cooling_mode_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline MaximumOutdoorTemperatureinCoolingMode value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field MaximumOutdoorTemperatureinCoolingMode.'),
        ] = None,
        variable_refrigerant_flows_cooling_capacity_ratio_modifier_functionof_low_temperature_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for CoolingCapacityRatioModifierFunctionofLowTemperatureCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field CoolingCapacityRatioModifierFunctionofLowTemperatureCurve.'),
        ] = None,
        variable_refrigerant_flows_cooling_capacity_ratio_boundary_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for CoolingCapacityRatioBoundaryCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field CoolingCapacityRatioBoundaryCurve.'),
        ] = None,
        variable_refrigerant_flows_cooling_capacity_ratio_modifier_functionof_high_temperature_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for CoolingCapacityRatioModifierFunctionofHighTemperatureCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field CoolingCapacityRatioModifierFunctionofHighTemperatureCurve.'),
        ] = None,
        variable_refrigerant_flows_cooling_energy_input_ratio_modifier_functionof_low_temperature_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for CoolingEnergyInputRatioModifierFunctionofLowTemperatureCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field CoolingEnergyInputRatioModifierFunctionofLowTemperatureCurve.'),
        ] = None,
        variable_refrigerant_flows_cooling_energy_input_ratio_boundary_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for CoolingEnergyInputRatioBoundaryCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field CoolingEnergyInputRatioBoundaryCurve.'),
        ] = None,
        variable_refrigerant_flows_cooling_energy_input_ratio_modifier_functionof_high_temperature_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for CoolingEnergyInputRatioModifierFunctionofHighTemperatureCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field CoolingEnergyInputRatioModifierFunctionofHighTemperatureCurve.'),
        ] = None,
        variable_refrigerant_flows_cooling_energy_input_ratio_modifier_functionof_low_part_load_ratio_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for CoolingEnergyInputRatioModifierFunctionofLowPartLoadRatioCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field CoolingEnergyInputRatioModifierFunctionofLowPartLoadRatioCurve.'),
        ] = None,
        variable_refrigerant_flows_cooling_energy_input_ratio_modifier_functionof_high_part_load_ratio_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for CoolingEnergyInputRatioModifierFunctionofHighPartLoadRatioCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field CoolingEnergyInputRatioModifierFunctionofHighPartLoadRatioCurve.'),
        ] = None,
        variable_refrigerant_flows_cooling_combination_ratio_correction_factor_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for CoolingCombinationRatioCorrectionFactorCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field CoolingCombinationRatioCorrectionFactorCurve.'),
        ] = None,
        variable_refrigerant_flows_cooling_part_load_fraction_correlation_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for CoolingPartLoadFractionCorrelationCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field CoolingPartLoadFractionCorrelationCurve.'),
        ] = None,
        variable_refrigerant_flows_gross_rated_heating_capacity_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline GrossRatedHeatingCapacity value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field GrossRatedHeatingCapacity.'),
        ] = None,
        variable_refrigerant_flows_rated_heating_capacity_sizing_ratio_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline RatedHeatingCapacitySizingRatio value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field RatedHeatingCapacitySizingRatio.'),
        ] = None,
        variable_refrigerant_flows_rated_total_heating_capacity_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline RatedTotalHeatingCapacity value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field RatedTotalHeatingCapacity.'),
        ] = None,
        variable_refrigerant_flows_rated_total_heating_capacity_sizing_ratio_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline RatedTotalHeatingCapacitySizingRatio value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field RatedTotalHeatingCapacitySizingRatio.'),
        ] = None,
        variable_refrigerant_flows_rated_heating_cop_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline RatedHeatingCOP value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field RatedHeatingCOP.'),
        ] = None,
        variable_refrigerant_flows_minimum_outdoor_temperaturein_heating_mode_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline MinimumOutdoorTemperatureinHeatingMode value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field MinimumOutdoorTemperatureinHeatingMode.'),
        ] = None,
        variable_refrigerant_flows_maximum_outdoor_temperaturein_heating_mode_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline MaximumOutdoorTemperatureinHeatingMode value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field MaximumOutdoorTemperatureinHeatingMode.'),
        ] = None,
        variable_refrigerant_flows_heating_capacity_ratio_modifier_functionof_low_temperature_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for HeatingCapacityRatioModifierFunctionofLowTemperatureCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field HeatingCapacityRatioModifierFunctionofLowTemperatureCurve.'),
        ] = None,
        variable_refrigerant_flows_heating_capacity_ratio_boundary_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for HeatingCapacityRatioBoundaryCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field HeatingCapacityRatioBoundaryCurve.'),
        ] = None,
        variable_refrigerant_flows_heating_capacity_ratio_modifier_functionof_high_temperature_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for HeatingCapacityRatioModifierFunctionofHighTemperatureCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field HeatingCapacityRatioModifierFunctionofHighTemperatureCurve.'),
        ] = None,
        variable_refrigerant_flows_heating_energy_input_ratio_modifier_functionof_low_temperature_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for HeatingEnergyInputRatioModifierFunctionofLowTemperatureCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field HeatingEnergyInputRatioModifierFunctionofLowTemperatureCurve.'),
        ] = None,
        variable_refrigerant_flows_heating_energy_input_ratio_boundary_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for HeatingEnergyInputRatioBoundaryCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field HeatingEnergyInputRatioBoundaryCurve.'),
        ] = None,
        variable_refrigerant_flows_heating_energy_input_ratio_modifier_functionof_high_temperature_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for HeatingEnergyInputRatioModifierFunctionofHighTemperatureCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field HeatingEnergyInputRatioModifierFunctionofHighTemperatureCurve.'),
        ] = None,
        variable_refrigerant_flows_heating_performance_curve_outdoor_temperature_type_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for HeatingPerformanceCurveOutdoorTemperatureType; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field HeatingPerformanceCurveOutdoorTemperatureType.'),
        ] = None,
        variable_refrigerant_flows_heating_energy_input_ratio_modifier_functionof_low_part_load_ratio_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for HeatingEnergyInputRatioModifierFunctionofLowPartLoadRatioCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field HeatingEnergyInputRatioModifierFunctionofLowPartLoadRatioCurve.'),
        ] = None,
        variable_refrigerant_flows_heating_energy_input_ratio_modifier_functionof_high_part_load_ratio_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for HeatingEnergyInputRatioModifierFunctionofHighPartLoadRatioCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field HeatingEnergyInputRatioModifierFunctionofHighPartLoadRatioCurve.'),
        ] = None,
        variable_refrigerant_flows_heating_combination_ratio_correction_factor_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for HeatingCombinationRatioCorrectionFactorCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field HeatingCombinationRatioCorrectionFactorCurve.'),
        ] = None,
        variable_refrigerant_flows_heating_part_load_fraction_correlation_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for HeatingPartLoadFractionCorrelationCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field HeatingPartLoadFractionCorrelationCurve.'),
        ] = None,
        variable_refrigerant_flows_minimum_heat_pump_part_load_ratio_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline MinimumHeatPumpPartLoadRatio value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field MinimumHeatPumpPartLoadRatio.'),
        ] = None,
        variable_refrigerant_flows_master_thermostat_priority_control_type_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline MasterThermostatPriorityControlType value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field MasterThermostatPriorityControlType.'),
        ] = None,
        variable_refrigerant_flows_thermostat_priority_schedule_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for ThermostatPrioritySchedule; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field ThermostatPrioritySchedule.'),
        ] = None,
        variable_refrigerant_flows_heat_pump_waste_heat_recovery_values: Annotated[
            list[bool | str | None] | None,
            Field(description='Optional inline HeatPumpWasteHeatRecovery value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field HeatPumpWasteHeatRecovery.'),
        ] = None,
        variable_refrigerant_flows_equivalent_piping_lengthusedfor_piping_correction_factorin_cooling_mode_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline EquivalentPipingLengthusedforPipingCorrectionFactorinCoolingMode value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field EquivalentPipingLengthusedforPipingCorrectionFactorinCoolingMode.'),
        ] = None,
        variable_refrigerant_flows_vertical_heightusedfor_piping_correction_factor_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline VerticalHeightusedforPipingCorrectionFactor value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field VerticalHeightusedforPipingCorrectionFactor.'),
        ] = None,
        variable_refrigerant_flows_piping_correction_factorfor_lengthin_cooling_mode_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for PipingCorrectionFactorforLengthinCoolingModeCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field PipingCorrectionFactorforLengthinCoolingModeCurve.'),
        ] = None,
        variable_refrigerant_flows_piping_correction_factorfor_heightin_cooling_mode_coefficient_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline PipingCorrectionFactorforHeightinCoolingModeCoefficient value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field PipingCorrectionFactorforHeightinCoolingModeCoefficient.'),
        ] = None,
        variable_refrigerant_flows_equivalent_piping_lengthusedfor_piping_correction_factorin_heating_mode_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline EquivalentPipingLengthusedforPipingCorrectionFactorinHeatingMode value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field EquivalentPipingLengthusedforPipingCorrectionFactorinHeatingMode.'),
        ] = None,
        variable_refrigerant_flows_piping_correction_factorfor_lengthin_heating_mode_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for PipingCorrectionFactorforLengthinHeatingModeCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field PipingCorrectionFactorforLengthinHeatingModeCurve.'),
        ] = None,
        variable_refrigerant_flows_piping_correction_factorfor_heightin_heating_mode_coefficient_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline PipingCorrectionFactorforHeightinHeatingModeCoefficient value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field PipingCorrectionFactorforHeightinHeatingModeCoefficient.'),
        ] = None,
        variable_refrigerant_flows_crankcase_heater_powerper_compressor_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline CrankcaseHeaterPowerperCompressor value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field CrankcaseHeaterPowerperCompressor.'),
        ] = None,
        variable_refrigerant_flows_numberof_compressors_values: Annotated[
            list[int | None] | None,
            Field(description='Optional inline NumberofCompressors value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field NumberofCompressors.'),
        ] = None,
        variable_refrigerant_flows_ratioof_compressor_sizeto_total_compressor_capacity_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline RatioofCompressorSizetoTotalCompressorCapacity value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field RatioofCompressorSizetoTotalCompressorCapacity.'),
        ] = None,
        variable_refrigerant_flows_maximum_outdoor_drybulb_temperaturefor_crankcase_heater_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline MaximumOutdoorDrybulbTemperatureforCrankcaseHeater value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field MaximumOutdoorDrybulbTemperatureforCrankcaseHeater.'),
        ] = None,
        variable_refrigerant_flows_defrost_strategy_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline DefrostStrategy value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field DefrostStrategy.'),
        ] = None,
        variable_refrigerant_flows_defrost_control_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline DefrostControl value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field DefrostControl.'),
        ] = None,
        variable_refrigerant_flows_defrost_energy_input_ratio_modifier_functionof_temperature_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for DefrostEnergyInputRatioModifierFunctionofTemperatureCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field DefrostEnergyInputRatioModifierFunctionofTemperatureCurve.'),
        ] = None,
        variable_refrigerant_flows_defrost_time_period_fraction_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline DefrostTimePeriodFraction value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field DefrostTimePeriodFraction.'),
        ] = None,
        variable_refrigerant_flows_resistive_defrost_heater_capacity_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline ResistiveDefrostHeaterCapacity value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field ResistiveDefrostHeaterCapacity.'),
        ] = None,
        variable_refrigerant_flows_maximum_outdoor_drybulb_temperaturefor_defrost_operation_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline MaximumOutdoorDrybulbTemperatureforDefrostOperation value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field MaximumOutdoorDrybulbTemperatureforDefrostOperation.'),
        ] = None,
        variable_refrigerant_flows_condenser_type_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline CondenserType value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field CondenserType.'),
        ] = None,
        variable_refrigerant_flows_water_condenser_volume_flow_rate_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline WaterCondenserVolumeFlowRate value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field WaterCondenserVolumeFlowRate.'),
        ] = None,
        variable_refrigerant_flows_evaporative_condenser_effectiveness_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline EvaporativeCondenserEffectiveness value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field EvaporativeCondenserEffectiveness.'),
        ] = None,
        variable_refrigerant_flows_evaporative_condenser_air_flow_rate_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline EvaporativeCondenserAirFlowRate value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field EvaporativeCondenserAirFlowRate.'),
        ] = None,
        variable_refrigerant_flows_evaporative_condenser_pump_rated_power_consumption_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline EvaporativeCondenserPumpRatedPowerConsumption value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field EvaporativeCondenserPumpRatedPowerConsumption.'),
        ] = None,
        variable_refrigerant_flows_basin_heater_capacity_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline BasinHeaterCapacity value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field BasinHeaterCapacity.'),
        ] = None,
        variable_refrigerant_flows_basin_heater_setpoint_temperature_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline BasinHeaterSetpointTemperature value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field BasinHeaterSetpointTemperature.'),
        ] = None,
        variable_refrigerant_flows_basin_heater_operating_schedule_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for BasinHeaterOperatingSchedule; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field BasinHeaterOperatingSchedule.'),
        ] = None,
        variable_refrigerant_flows_fuel_type_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline FuelType value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field FuelType.'),
        ] = None,
        variable_refrigerant_flows_minimum_outdoor_temperaturein_heat_recovery_mode_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline MinimumOutdoorTemperatureinHeatRecoveryMode value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field MinimumOutdoorTemperatureinHeatRecoveryMode.'),
        ] = None,
        variable_refrigerant_flows_maximum_outdoor_temperaturein_heat_recovery_mode_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline MaximumOutdoorTemperatureinHeatRecoveryMode value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field MaximumOutdoorTemperatureinHeatRecoveryMode.'),
        ] = None,
        variable_refrigerant_flows_heat_recovery_cooling_capacity_modifier_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for HeatRecoveryCoolingCapacityModifierCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field HeatRecoveryCoolingCapacityModifierCurve.'),
        ] = None,
        variable_refrigerant_flows_initial_heat_recovery_cooling_capacity_fraction_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline InitialHeatRecoveryCoolingCapacityFraction value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field InitialHeatRecoveryCoolingCapacityFraction.'),
        ] = None,
        variable_refrigerant_flows_heat_recovery_cooling_capacity_time_constant_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline HeatRecoveryCoolingCapacityTimeConstant value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field HeatRecoveryCoolingCapacityTimeConstant.'),
        ] = None,
        variable_refrigerant_flows_heat_recovery_cooling_energy_modifier_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for HeatRecoveryCoolingEnergyModifierCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field HeatRecoveryCoolingEnergyModifierCurve.'),
        ] = None,
        variable_refrigerant_flows_initial_heat_recovery_cooling_energy_fraction_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline InitialHeatRecoveryCoolingEnergyFraction value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field InitialHeatRecoveryCoolingEnergyFraction.'),
        ] = None,
        variable_refrigerant_flows_heat_recovery_cooling_energy_time_constant_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline HeatRecoveryCoolingEnergyTimeConstant value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field HeatRecoveryCoolingEnergyTimeConstant.'),
        ] = None,
        variable_refrigerant_flows_heat_recovery_heating_capacity_modifier_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for HeatRecoveryHeatingCapacityModifierCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field HeatRecoveryHeatingCapacityModifierCurve.'),
        ] = None,
        variable_refrigerant_flows_initial_heat_recovery_heating_capacity_fraction_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline InitialHeatRecoveryHeatingCapacityFraction value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field InitialHeatRecoveryHeatingCapacityFraction.'),
        ] = None,
        variable_refrigerant_flows_heat_recovery_heating_capacity_time_constant_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline HeatRecoveryHeatingCapacityTimeConstant value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field HeatRecoveryHeatingCapacityTimeConstant.'),
        ] = None,
        variable_refrigerant_flows_heat_recovery_heating_energy_modifier_curve_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for HeatRecoveryHeatingEnergyModifierCurve; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child IB_AirConditionerVariableRefrigerantFlow field HeatRecoveryHeatingEnergyModifierCurve.'),
        ] = None,
        variable_refrigerant_flows_initial_heat_recovery_heating_energy_fraction_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline InitialHeatRecoveryHeatingEnergyFraction value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field InitialHeatRecoveryHeatingEnergyFraction.'),
        ] = None,
        variable_refrigerant_flows_heat_recovery_heating_energy_time_constant_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline HeatRecoveryHeatingEnergyTimeConstant value for IB_AirConditionerVariableRefrigerantFlow; maps to Ironbug IB_HVACSystem.VariableRefrigerantFlows child field HeatRecoveryHeatingEnergyTimeConstant.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_HVACSystem as a reviewed Ironbug Root authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        inline_source_property_children: dict[str, Any] = {}
        if display_name_value is not None:
            source_properties['DisplayName'] = display_name_value
        if air_loops_targets is not None:
            source_property_targets['AirLoops'] = air_loops_targets
        if plant_loops_targets is not None:
            source_property_targets['PlantLoops'] = plant_loops_targets
        if vrf_systems_targets is not None:
            source_property_targets['VariableRefrigerantFlows'] = vrf_systems_targets
        if ib_version is not None:
            source_properties['IBVersion'] = ib_version
        inline_air_loops_fields: dict[str, Any] = {}
        inline_air_loops_field_targets: dict[str, Any] = {}
        if air_loops_name_values is not None:
            inline_air_loops_fields['Name'] = air_loops_name_values
        if air_loops_design_supply_air_flow_rate_values is not None:
            inline_air_loops_fields['DesignSupplyAirFlowRate'] = air_loops_design_supply_air_flow_rate_values
        if air_loops_design_return_air_flow_fractionof_supply_air_flow_values is not None:
            inline_air_loops_fields['DesignReturnAirFlowFractionofSupplyAirFlow'] = air_loops_design_return_air_flow_fractionof_supply_air_flow_values
        if air_loops_availability_schedule_targets is not None:
            inline_air_loops_field_targets['AvailabilitySchedule'] = air_loops_availability_schedule_targets
        if air_loops_night_cycle_control_type_values is not None:
            inline_air_loops_fields['NightCycleControlType'] = air_loops_night_cycle_control_type_values
        if air_loops_availability_managers_targets is not None:
            inline_air_loops_field_targets['AvailabilityManagers'] = air_loops_availability_managers_targets
        if air_loops_identifiers is not None or inline_air_loops_fields or inline_air_loops_field_targets:
            if air_loops_targets is not None:
                raise ValueError("Provide either air_loops_targets or inline air_loops_* parameters, not both.")
            inline_source_property_children['AirLoops'] = {
                'source_class': 'IB_AirLoopHVAC',
                'is_list': True,
                'identifiers': air_loops_identifiers,
                'source_fields': inline_air_loops_fields,
                'source_field_targets': inline_air_loops_field_targets,
            }
        inline_plant_loops_fields: dict[str, Any] = {}
        inline_plant_loops_field_targets: dict[str, Any] = {}
        if plant_loops_name_values is not None:
            inline_plant_loops_fields['Name'] = plant_loops_name_values
        if plant_loops_load_distribution_scheme_values is not None:
            inline_plant_loops_fields['LoadDistributionScheme'] = plant_loops_load_distribution_scheme_values
        if plant_loops_fluid_type_values is not None:
            inline_plant_loops_fields['FluidType'] = plant_loops_fluid_type_values
        if plant_loops_glycol_concentration_values is not None:
            inline_plant_loops_fields['GlycolConcentration'] = plant_loops_glycol_concentration_values
        if plant_loops_maximum_loop_temperature_values is not None:
            inline_plant_loops_fields['MaximumLoopTemperature'] = plant_loops_maximum_loop_temperature_values
        if plant_loops_minimum_loop_temperature_values is not None:
            inline_plant_loops_fields['MinimumLoopTemperature'] = plant_loops_minimum_loop_temperature_values
        if plant_loops_maximum_loop_flow_rate_values is not None:
            inline_plant_loops_fields['MaximumLoopFlowRate'] = plant_loops_maximum_loop_flow_rate_values
        if plant_loops_minimum_loop_flow_rate_values is not None:
            inline_plant_loops_fields['MinimumLoopFlowRate'] = plant_loops_minimum_loop_flow_rate_values
        if plant_loops_plant_loop_volume_values is not None:
            inline_plant_loops_fields['PlantLoopVolume'] = plant_loops_plant_loop_volume_values
        if plant_loops_common_pipe_simulation_values is not None:
            inline_plant_loops_fields['CommonPipeSimulation'] = plant_loops_common_pipe_simulation_values
        if plant_loops_plant_equipment_operation_heating_load_schedule_targets is not None:
            inline_plant_loops_field_targets['PlantEquipmentOperationHeatingLoadSchedule'] = plant_loops_plant_equipment_operation_heating_load_schedule_targets
        if plant_loops_plant_equipment_operation_cooling_load_schedule_targets is not None:
            inline_plant_loops_field_targets['PlantEquipmentOperationCoolingLoadSchedule'] = plant_loops_plant_equipment_operation_cooling_load_schedule_targets
        if plant_loops_primary_plant_equipment_operation_scheme_schedule_targets is not None:
            inline_plant_loops_field_targets['PrimaryPlantEquipmentOperationSchemeSchedule'] = plant_loops_primary_plant_equipment_operation_scheme_schedule_targets
        if plant_loops_component_setpoint_operation_scheme_schedule_targets is not None:
            inline_plant_loops_field_targets['ComponentSetpointOperationSchemeSchedule'] = plant_loops_component_setpoint_operation_scheme_schedule_targets
        if plant_loops_availability_managers_targets is not None:
            inline_plant_loops_field_targets['AvailabilityManagers'] = plant_loops_availability_managers_targets
        if plant_loops_identifiers is not None or inline_plant_loops_fields or inline_plant_loops_field_targets:
            if plant_loops_targets is not None:
                raise ValueError("Provide either plant_loops_targets or inline plant_loops_* parameters, not both.")
            inline_source_property_children['PlantLoops'] = {
                'source_class': 'IB_PlantLoop',
                'is_list': True,
                'identifiers': plant_loops_identifiers,
                'source_fields': inline_plant_loops_fields,
                'source_field_targets': inline_plant_loops_field_targets,
            }
        inline_variable_refrigerant_flows_fields: dict[str, Any] = {}
        inline_variable_refrigerant_flows_field_targets: dict[str, Any] = {}
        if variable_refrigerant_flows_name_values is not None:
            inline_variable_refrigerant_flows_fields['Name'] = variable_refrigerant_flows_name_values
        if variable_refrigerant_flows_availability_schedule_targets is not None:
            inline_variable_refrigerant_flows_field_targets['AvailabilitySchedule'] = variable_refrigerant_flows_availability_schedule_targets
        if variable_refrigerant_flows_gross_rated_total_cooling_capacity_values is not None:
            inline_variable_refrigerant_flows_fields['GrossRatedTotalCoolingCapacity'] = variable_refrigerant_flows_gross_rated_total_cooling_capacity_values
        if variable_refrigerant_flows_gross_rated_cooling_cop_values is not None:
            inline_variable_refrigerant_flows_fields['GrossRatedCoolingCOP'] = variable_refrigerant_flows_gross_rated_cooling_cop_values
        if variable_refrigerant_flows_rated_total_cooling_capacity_values is not None:
            inline_variable_refrigerant_flows_fields['RatedTotalCoolingCapacity'] = variable_refrigerant_flows_rated_total_cooling_capacity_values
        if variable_refrigerant_flows_rated_cooling_cop_values is not None:
            inline_variable_refrigerant_flows_fields['RatedCoolingCOP'] = variable_refrigerant_flows_rated_cooling_cop_values
        if variable_refrigerant_flows_minimum_outdoor_temperaturein_cooling_mode_values is not None:
            inline_variable_refrigerant_flows_fields['MinimumOutdoorTemperatureinCoolingMode'] = variable_refrigerant_flows_minimum_outdoor_temperaturein_cooling_mode_values
        if variable_refrigerant_flows_maximum_outdoor_temperaturein_cooling_mode_values is not None:
            inline_variable_refrigerant_flows_fields['MaximumOutdoorTemperatureinCoolingMode'] = variable_refrigerant_flows_maximum_outdoor_temperaturein_cooling_mode_values
        if variable_refrigerant_flows_cooling_capacity_ratio_modifier_functionof_low_temperature_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['CoolingCapacityRatioModifierFunctionofLowTemperatureCurve'] = variable_refrigerant_flows_cooling_capacity_ratio_modifier_functionof_low_temperature_curve_targets
        if variable_refrigerant_flows_cooling_capacity_ratio_boundary_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['CoolingCapacityRatioBoundaryCurve'] = variable_refrigerant_flows_cooling_capacity_ratio_boundary_curve_targets
        if variable_refrigerant_flows_cooling_capacity_ratio_modifier_functionof_high_temperature_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['CoolingCapacityRatioModifierFunctionofHighTemperatureCurve'] = variable_refrigerant_flows_cooling_capacity_ratio_modifier_functionof_high_temperature_curve_targets
        if variable_refrigerant_flows_cooling_energy_input_ratio_modifier_functionof_low_temperature_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['CoolingEnergyInputRatioModifierFunctionofLowTemperatureCurve'] = variable_refrigerant_flows_cooling_energy_input_ratio_modifier_functionof_low_temperature_curve_targets
        if variable_refrigerant_flows_cooling_energy_input_ratio_boundary_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['CoolingEnergyInputRatioBoundaryCurve'] = variable_refrigerant_flows_cooling_energy_input_ratio_boundary_curve_targets
        if variable_refrigerant_flows_cooling_energy_input_ratio_modifier_functionof_high_temperature_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['CoolingEnergyInputRatioModifierFunctionofHighTemperatureCurve'] = variable_refrigerant_flows_cooling_energy_input_ratio_modifier_functionof_high_temperature_curve_targets
        if variable_refrigerant_flows_cooling_energy_input_ratio_modifier_functionof_low_part_load_ratio_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['CoolingEnergyInputRatioModifierFunctionofLowPartLoadRatioCurve'] = variable_refrigerant_flows_cooling_energy_input_ratio_modifier_functionof_low_part_load_ratio_curve_targets
        if variable_refrigerant_flows_cooling_energy_input_ratio_modifier_functionof_high_part_load_ratio_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['CoolingEnergyInputRatioModifierFunctionofHighPartLoadRatioCurve'] = variable_refrigerant_flows_cooling_energy_input_ratio_modifier_functionof_high_part_load_ratio_curve_targets
        if variable_refrigerant_flows_cooling_combination_ratio_correction_factor_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['CoolingCombinationRatioCorrectionFactorCurve'] = variable_refrigerant_flows_cooling_combination_ratio_correction_factor_curve_targets
        if variable_refrigerant_flows_cooling_part_load_fraction_correlation_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['CoolingPartLoadFractionCorrelationCurve'] = variable_refrigerant_flows_cooling_part_load_fraction_correlation_curve_targets
        if variable_refrigerant_flows_gross_rated_heating_capacity_values is not None:
            inline_variable_refrigerant_flows_fields['GrossRatedHeatingCapacity'] = variable_refrigerant_flows_gross_rated_heating_capacity_values
        if variable_refrigerant_flows_rated_heating_capacity_sizing_ratio_values is not None:
            inline_variable_refrigerant_flows_fields['RatedHeatingCapacitySizingRatio'] = variable_refrigerant_flows_rated_heating_capacity_sizing_ratio_values
        if variable_refrigerant_flows_rated_total_heating_capacity_values is not None:
            inline_variable_refrigerant_flows_fields['RatedTotalHeatingCapacity'] = variable_refrigerant_flows_rated_total_heating_capacity_values
        if variable_refrigerant_flows_rated_total_heating_capacity_sizing_ratio_values is not None:
            inline_variable_refrigerant_flows_fields['RatedTotalHeatingCapacitySizingRatio'] = variable_refrigerant_flows_rated_total_heating_capacity_sizing_ratio_values
        if variable_refrigerant_flows_rated_heating_cop_values is not None:
            inline_variable_refrigerant_flows_fields['RatedHeatingCOP'] = variable_refrigerant_flows_rated_heating_cop_values
        if variable_refrigerant_flows_minimum_outdoor_temperaturein_heating_mode_values is not None:
            inline_variable_refrigerant_flows_fields['MinimumOutdoorTemperatureinHeatingMode'] = variable_refrigerant_flows_minimum_outdoor_temperaturein_heating_mode_values
        if variable_refrigerant_flows_maximum_outdoor_temperaturein_heating_mode_values is not None:
            inline_variable_refrigerant_flows_fields['MaximumOutdoorTemperatureinHeatingMode'] = variable_refrigerant_flows_maximum_outdoor_temperaturein_heating_mode_values
        if variable_refrigerant_flows_heating_capacity_ratio_modifier_functionof_low_temperature_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['HeatingCapacityRatioModifierFunctionofLowTemperatureCurve'] = variable_refrigerant_flows_heating_capacity_ratio_modifier_functionof_low_temperature_curve_targets
        if variable_refrigerant_flows_heating_capacity_ratio_boundary_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['HeatingCapacityRatioBoundaryCurve'] = variable_refrigerant_flows_heating_capacity_ratio_boundary_curve_targets
        if variable_refrigerant_flows_heating_capacity_ratio_modifier_functionof_high_temperature_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['HeatingCapacityRatioModifierFunctionofHighTemperatureCurve'] = variable_refrigerant_flows_heating_capacity_ratio_modifier_functionof_high_temperature_curve_targets
        if variable_refrigerant_flows_heating_energy_input_ratio_modifier_functionof_low_temperature_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['HeatingEnergyInputRatioModifierFunctionofLowTemperatureCurve'] = variable_refrigerant_flows_heating_energy_input_ratio_modifier_functionof_low_temperature_curve_targets
        if variable_refrigerant_flows_heating_energy_input_ratio_boundary_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['HeatingEnergyInputRatioBoundaryCurve'] = variable_refrigerant_flows_heating_energy_input_ratio_boundary_curve_targets
        if variable_refrigerant_flows_heating_energy_input_ratio_modifier_functionof_high_temperature_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['HeatingEnergyInputRatioModifierFunctionofHighTemperatureCurve'] = variable_refrigerant_flows_heating_energy_input_ratio_modifier_functionof_high_temperature_curve_targets
        if variable_refrigerant_flows_heating_performance_curve_outdoor_temperature_type_targets is not None:
            inline_variable_refrigerant_flows_field_targets['HeatingPerformanceCurveOutdoorTemperatureType'] = variable_refrigerant_flows_heating_performance_curve_outdoor_temperature_type_targets
        if variable_refrigerant_flows_heating_energy_input_ratio_modifier_functionof_low_part_load_ratio_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['HeatingEnergyInputRatioModifierFunctionofLowPartLoadRatioCurve'] = variable_refrigerant_flows_heating_energy_input_ratio_modifier_functionof_low_part_load_ratio_curve_targets
        if variable_refrigerant_flows_heating_energy_input_ratio_modifier_functionof_high_part_load_ratio_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['HeatingEnergyInputRatioModifierFunctionofHighPartLoadRatioCurve'] = variable_refrigerant_flows_heating_energy_input_ratio_modifier_functionof_high_part_load_ratio_curve_targets
        if variable_refrigerant_flows_heating_combination_ratio_correction_factor_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['HeatingCombinationRatioCorrectionFactorCurve'] = variable_refrigerant_flows_heating_combination_ratio_correction_factor_curve_targets
        if variable_refrigerant_flows_heating_part_load_fraction_correlation_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['HeatingPartLoadFractionCorrelationCurve'] = variable_refrigerant_flows_heating_part_load_fraction_correlation_curve_targets
        if variable_refrigerant_flows_minimum_heat_pump_part_load_ratio_values is not None:
            inline_variable_refrigerant_flows_fields['MinimumHeatPumpPartLoadRatio'] = variable_refrigerant_flows_minimum_heat_pump_part_load_ratio_values
        if variable_refrigerant_flows_master_thermostat_priority_control_type_values is not None:
            inline_variable_refrigerant_flows_fields['MasterThermostatPriorityControlType'] = variable_refrigerant_flows_master_thermostat_priority_control_type_values
        if variable_refrigerant_flows_thermostat_priority_schedule_targets is not None:
            inline_variable_refrigerant_flows_field_targets['ThermostatPrioritySchedule'] = variable_refrigerant_flows_thermostat_priority_schedule_targets
        if variable_refrigerant_flows_heat_pump_waste_heat_recovery_values is not None:
            inline_variable_refrigerant_flows_fields['HeatPumpWasteHeatRecovery'] = variable_refrigerant_flows_heat_pump_waste_heat_recovery_values
        if variable_refrigerant_flows_equivalent_piping_lengthusedfor_piping_correction_factorin_cooling_mode_values is not None:
            inline_variable_refrigerant_flows_fields['EquivalentPipingLengthusedforPipingCorrectionFactorinCoolingMode'] = variable_refrigerant_flows_equivalent_piping_lengthusedfor_piping_correction_factorin_cooling_mode_values
        if variable_refrigerant_flows_vertical_heightusedfor_piping_correction_factor_values is not None:
            inline_variable_refrigerant_flows_fields['VerticalHeightusedforPipingCorrectionFactor'] = variable_refrigerant_flows_vertical_heightusedfor_piping_correction_factor_values
        if variable_refrigerant_flows_piping_correction_factorfor_lengthin_cooling_mode_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['PipingCorrectionFactorforLengthinCoolingModeCurve'] = variable_refrigerant_flows_piping_correction_factorfor_lengthin_cooling_mode_curve_targets
        if variable_refrigerant_flows_piping_correction_factorfor_heightin_cooling_mode_coefficient_values is not None:
            inline_variable_refrigerant_flows_fields['PipingCorrectionFactorforHeightinCoolingModeCoefficient'] = variable_refrigerant_flows_piping_correction_factorfor_heightin_cooling_mode_coefficient_values
        if variable_refrigerant_flows_equivalent_piping_lengthusedfor_piping_correction_factorin_heating_mode_values is not None:
            inline_variable_refrigerant_flows_fields['EquivalentPipingLengthusedforPipingCorrectionFactorinHeatingMode'] = variable_refrigerant_flows_equivalent_piping_lengthusedfor_piping_correction_factorin_heating_mode_values
        if variable_refrigerant_flows_piping_correction_factorfor_lengthin_heating_mode_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['PipingCorrectionFactorforLengthinHeatingModeCurve'] = variable_refrigerant_flows_piping_correction_factorfor_lengthin_heating_mode_curve_targets
        if variable_refrigerant_flows_piping_correction_factorfor_heightin_heating_mode_coefficient_values is not None:
            inline_variable_refrigerant_flows_fields['PipingCorrectionFactorforHeightinHeatingModeCoefficient'] = variable_refrigerant_flows_piping_correction_factorfor_heightin_heating_mode_coefficient_values
        if variable_refrigerant_flows_crankcase_heater_powerper_compressor_values is not None:
            inline_variable_refrigerant_flows_fields['CrankcaseHeaterPowerperCompressor'] = variable_refrigerant_flows_crankcase_heater_powerper_compressor_values
        if variable_refrigerant_flows_numberof_compressors_values is not None:
            inline_variable_refrigerant_flows_fields['NumberofCompressors'] = variable_refrigerant_flows_numberof_compressors_values
        if variable_refrigerant_flows_ratioof_compressor_sizeto_total_compressor_capacity_values is not None:
            inline_variable_refrigerant_flows_fields['RatioofCompressorSizetoTotalCompressorCapacity'] = variable_refrigerant_flows_ratioof_compressor_sizeto_total_compressor_capacity_values
        if variable_refrigerant_flows_maximum_outdoor_drybulb_temperaturefor_crankcase_heater_values is not None:
            inline_variable_refrigerant_flows_fields['MaximumOutdoorDrybulbTemperatureforCrankcaseHeater'] = variable_refrigerant_flows_maximum_outdoor_drybulb_temperaturefor_crankcase_heater_values
        if variable_refrigerant_flows_defrost_strategy_values is not None:
            inline_variable_refrigerant_flows_fields['DefrostStrategy'] = variable_refrigerant_flows_defrost_strategy_values
        if variable_refrigerant_flows_defrost_control_values is not None:
            inline_variable_refrigerant_flows_fields['DefrostControl'] = variable_refrigerant_flows_defrost_control_values
        if variable_refrigerant_flows_defrost_energy_input_ratio_modifier_functionof_temperature_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['DefrostEnergyInputRatioModifierFunctionofTemperatureCurve'] = variable_refrigerant_flows_defrost_energy_input_ratio_modifier_functionof_temperature_curve_targets
        if variable_refrigerant_flows_defrost_time_period_fraction_values is not None:
            inline_variable_refrigerant_flows_fields['DefrostTimePeriodFraction'] = variable_refrigerant_flows_defrost_time_period_fraction_values
        if variable_refrigerant_flows_resistive_defrost_heater_capacity_values is not None:
            inline_variable_refrigerant_flows_fields['ResistiveDefrostHeaterCapacity'] = variable_refrigerant_flows_resistive_defrost_heater_capacity_values
        if variable_refrigerant_flows_maximum_outdoor_drybulb_temperaturefor_defrost_operation_values is not None:
            inline_variable_refrigerant_flows_fields['MaximumOutdoorDrybulbTemperatureforDefrostOperation'] = variable_refrigerant_flows_maximum_outdoor_drybulb_temperaturefor_defrost_operation_values
        if variable_refrigerant_flows_condenser_type_values is not None:
            inline_variable_refrigerant_flows_fields['CondenserType'] = variable_refrigerant_flows_condenser_type_values
        if variable_refrigerant_flows_water_condenser_volume_flow_rate_values is not None:
            inline_variable_refrigerant_flows_fields['WaterCondenserVolumeFlowRate'] = variable_refrigerant_flows_water_condenser_volume_flow_rate_values
        if variable_refrigerant_flows_evaporative_condenser_effectiveness_values is not None:
            inline_variable_refrigerant_flows_fields['EvaporativeCondenserEffectiveness'] = variable_refrigerant_flows_evaporative_condenser_effectiveness_values
        if variable_refrigerant_flows_evaporative_condenser_air_flow_rate_values is not None:
            inline_variable_refrigerant_flows_fields['EvaporativeCondenserAirFlowRate'] = variable_refrigerant_flows_evaporative_condenser_air_flow_rate_values
        if variable_refrigerant_flows_evaporative_condenser_pump_rated_power_consumption_values is not None:
            inline_variable_refrigerant_flows_fields['EvaporativeCondenserPumpRatedPowerConsumption'] = variable_refrigerant_flows_evaporative_condenser_pump_rated_power_consumption_values
        if variable_refrigerant_flows_basin_heater_capacity_values is not None:
            inline_variable_refrigerant_flows_fields['BasinHeaterCapacity'] = variable_refrigerant_flows_basin_heater_capacity_values
        if variable_refrigerant_flows_basin_heater_setpoint_temperature_values is not None:
            inline_variable_refrigerant_flows_fields['BasinHeaterSetpointTemperature'] = variable_refrigerant_flows_basin_heater_setpoint_temperature_values
        if variable_refrigerant_flows_basin_heater_operating_schedule_targets is not None:
            inline_variable_refrigerant_flows_field_targets['BasinHeaterOperatingSchedule'] = variable_refrigerant_flows_basin_heater_operating_schedule_targets
        if variable_refrigerant_flows_fuel_type_values is not None:
            inline_variable_refrigerant_flows_fields['FuelType'] = variable_refrigerant_flows_fuel_type_values
        if variable_refrigerant_flows_minimum_outdoor_temperaturein_heat_recovery_mode_values is not None:
            inline_variable_refrigerant_flows_fields['MinimumOutdoorTemperatureinHeatRecoveryMode'] = variable_refrigerant_flows_minimum_outdoor_temperaturein_heat_recovery_mode_values
        if variable_refrigerant_flows_maximum_outdoor_temperaturein_heat_recovery_mode_values is not None:
            inline_variable_refrigerant_flows_fields['MaximumOutdoorTemperatureinHeatRecoveryMode'] = variable_refrigerant_flows_maximum_outdoor_temperaturein_heat_recovery_mode_values
        if variable_refrigerant_flows_heat_recovery_cooling_capacity_modifier_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['HeatRecoveryCoolingCapacityModifierCurve'] = variable_refrigerant_flows_heat_recovery_cooling_capacity_modifier_curve_targets
        if variable_refrigerant_flows_initial_heat_recovery_cooling_capacity_fraction_values is not None:
            inline_variable_refrigerant_flows_fields['InitialHeatRecoveryCoolingCapacityFraction'] = variable_refrigerant_flows_initial_heat_recovery_cooling_capacity_fraction_values
        if variable_refrigerant_flows_heat_recovery_cooling_capacity_time_constant_values is not None:
            inline_variable_refrigerant_flows_fields['HeatRecoveryCoolingCapacityTimeConstant'] = variable_refrigerant_flows_heat_recovery_cooling_capacity_time_constant_values
        if variable_refrigerant_flows_heat_recovery_cooling_energy_modifier_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['HeatRecoveryCoolingEnergyModifierCurve'] = variable_refrigerant_flows_heat_recovery_cooling_energy_modifier_curve_targets
        if variable_refrigerant_flows_initial_heat_recovery_cooling_energy_fraction_values is not None:
            inline_variable_refrigerant_flows_fields['InitialHeatRecoveryCoolingEnergyFraction'] = variable_refrigerant_flows_initial_heat_recovery_cooling_energy_fraction_values
        if variable_refrigerant_flows_heat_recovery_cooling_energy_time_constant_values is not None:
            inline_variable_refrigerant_flows_fields['HeatRecoveryCoolingEnergyTimeConstant'] = variable_refrigerant_flows_heat_recovery_cooling_energy_time_constant_values
        if variable_refrigerant_flows_heat_recovery_heating_capacity_modifier_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['HeatRecoveryHeatingCapacityModifierCurve'] = variable_refrigerant_flows_heat_recovery_heating_capacity_modifier_curve_targets
        if variable_refrigerant_flows_initial_heat_recovery_heating_capacity_fraction_values is not None:
            inline_variable_refrigerant_flows_fields['InitialHeatRecoveryHeatingCapacityFraction'] = variable_refrigerant_flows_initial_heat_recovery_heating_capacity_fraction_values
        if variable_refrigerant_flows_heat_recovery_heating_capacity_time_constant_values is not None:
            inline_variable_refrigerant_flows_fields['HeatRecoveryHeatingCapacityTimeConstant'] = variable_refrigerant_flows_heat_recovery_heating_capacity_time_constant_values
        if variable_refrigerant_flows_heat_recovery_heating_energy_modifier_curve_targets is not None:
            inline_variable_refrigerant_flows_field_targets['HeatRecoveryHeatingEnergyModifierCurve'] = variable_refrigerant_flows_heat_recovery_heating_energy_modifier_curve_targets
        if variable_refrigerant_flows_initial_heat_recovery_heating_energy_fraction_values is not None:
            inline_variable_refrigerant_flows_fields['InitialHeatRecoveryHeatingEnergyFraction'] = variable_refrigerant_flows_initial_heat_recovery_heating_energy_fraction_values
        if variable_refrigerant_flows_heat_recovery_heating_energy_time_constant_values is not None:
            inline_variable_refrigerant_flows_fields['HeatRecoveryHeatingEnergyTimeConstant'] = variable_refrigerant_flows_heat_recovery_heating_energy_time_constant_values
        if variable_refrigerant_flows_identifiers is not None or inline_variable_refrigerant_flows_fields or inline_variable_refrigerant_flows_field_targets:
            if vrf_systems_targets is not None:
                raise ValueError("Provide either vrf_systems_targets or inline variable_refrigerant_flows_* parameters, not both.")
            inline_source_property_children['VariableRefrigerantFlows'] = {
                'source_class': 'IB_AirConditionerVariableRefrigerantFlow',
                'is_list': True,
                'identifiers': variable_refrigerant_flows_identifiers,
                'source_fields': inline_variable_refrigerant_flows_fields,
                'source_field_targets': inline_variable_refrigerant_flows_field_targets,
            }
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_HVACSystem',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            source_property_targets=source_property_targets or None,
            inline_source_property_children=inline_source_property_children or None,
            overwrite=overwrite,
        )
