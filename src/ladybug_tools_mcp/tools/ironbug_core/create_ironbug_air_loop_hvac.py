'MCP tool for detailed_hvac_air_loop_hvac.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    set_ironbug_air_loop_demand_components,
    set_ironbug_air_loop_supply_components,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_air_loop_hvac tool.'

    @mcp.tool(
        name='air_loop_hvac',
        description=(
            'Create IB_AirLoopHVAC, an air-side HVAC loop with supply and demand components, from the Ironbug Loops / AirLoop source mirror. For DOAS, VAV, CAV, and other zone-serving air loops, create IB_AirLoopBranches with room-linked IB_ThermalZone branches and pass that branch target in demand_component_targets; do not pass loose ThermalZone targets directly when an air-loop demand branch is required. Bind supply equipment such as outdoor-air systems, fans, and coils through supply_component_targets. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={'ironbug', 'detailed-hvac', 'air-loop', 'doas', 'vav', 'central-system', 'hvac', 'author'},
        timeout=20,
    )
    def create_ironbug_air_loop_hvac(
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
            Field(description="Stable identifier for the new IB_AirLoopHVAC object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        night_cycle_control_type: Annotated[
            str | float | int | bool | None,
            Field(
                description="Sets Ironbug field NightCycleControlType for IB_AirLoopHVAC."
            ),
        ] = None,
        sizing_system_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Ironbug object target for source property SizingSystem (IB_SizingSystem) for IB_AirLoopHVAC; pass a target dict or same-model identifier."
            ),
        ] = None,
        supply_component_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description=(
                    "Optional ordered IB_AirLoopHVAC supply component targets, "
                    "such as an outdoor air system, supply fan, coil, or unitary "
                    "system target from the same Ironbug model."
                )
            ),
        ] = None,
        demand_component_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description=(
                    "Optional ordered IB_AirLoopHVAC demand component targets, "
                    "usually an IB_AirLoopBranches target that contains "
                    "IB_ThermalZone demand branches. For DOAS, VAV, CAV, "
                    "and similar zone-serving air loops, create "
                    "IB_AirLoopBranches first instead of passing loose "
                    "ThermalZone targets directly."
                )
            ),
        ] = None,
        design_supply_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional DesignSupplyAirFlowRate value; maps to Ironbug IB_AirLoopHVAC field DesignSupplyAirFlowRate.'),
        ] = None,
        design_return_air_flow_fractionof_supply_air_flow: Annotated[
            float | None,
            Field(description='Optional DesignReturnAirFlowFractionofSupplyAirFlow value; maps to Ironbug IB_AirLoopHVAC field DesignReturnAirFlowFractionofSupplyAirFlow.'),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for AvailabilitySchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirLoopHVAC field AvailabilitySchedule (IB_Schedule).'),
        ] = None,
        availability_managers_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description='Optional Ironbug object target for AvailabilityManagers; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AirLoopHVAC field AvailabilityManagers (IB_AvailabilityManager).'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_AirLoopHVAC field Name.'),
        ] = None,
        sizing_system_identifier: Annotated[
            str | None,
            Field(description='Optional inline IB_SizingSystem identifiers for IB_AirLoopHVAC.SizingSystem.'),
        ] = None,
        sizing_system_typeof_loadto_size_on: Annotated[
            str | None,
            Field(description='Optional inline TypeofLoadtoSizeOn value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field TypeofLoadtoSizeOn.'),
        ] = None,
        sizing_system_design_outdoor_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional inline DesignOutdoorAirFlowRate value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field DesignOutdoorAirFlowRate.'),
        ] = None,
        sizing_system_central_heating_maximum_system_air_flow_ratio: Annotated[
            float | str | None,
            Field(description='Optional inline CentralHeatingMaximumSystemAirFlowRatio value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field CentralHeatingMaximumSystemAirFlowRatio.'),
        ] = None,
        sizing_system_preheat_design_temperature: Annotated[
            float | None,
            Field(description='Optional inline PreheatDesignTemperature value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field PreheatDesignTemperature.'),
        ] = None,
        sizing_system_preheat_design_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional inline PreheatDesignHumidityRatio value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field PreheatDesignHumidityRatio.'),
        ] = None,
        sizing_system_precool_design_temperature: Annotated[
            float | None,
            Field(description='Optional inline PrecoolDesignTemperature value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field PrecoolDesignTemperature.'),
        ] = None,
        sizing_system_precool_design_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional inline PrecoolDesignHumidityRatio value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field PrecoolDesignHumidityRatio.'),
        ] = None,
        sizing_system_central_cooling_design_supply_air_temperature: Annotated[
            float | None,
            Field(description='Optional inline CentralCoolingDesignSupplyAirTemperature value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field CentralCoolingDesignSupplyAirTemperature.'),
        ] = None,
        sizing_system_central_heating_design_supply_air_temperature: Annotated[
            float | None,
            Field(description='Optional inline CentralHeatingDesignSupplyAirTemperature value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field CentralHeatingDesignSupplyAirTemperature.'),
        ] = None,
        sizing_system_sizing_option: Annotated[
            str | None,
            Field(description='Optional inline SizingOption value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field SizingOption.'),
        ] = None,
        sizing_system_all_outdoor_airin_cooling: Annotated[
            str | float | int | bool | None,
            Field(description='Optional inline AllOutdoorAirinCooling value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field AllOutdoorAirinCooling.'),
        ] = None,
        sizing_system_all_outdoor_airin_heating: Annotated[
            str | float | int | bool | None,
            Field(description='Optional inline AllOutdoorAirinHeating value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field AllOutdoorAirinHeating.'),
        ] = None,
        sizing_system_central_cooling_design_supply_air_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional inline CentralCoolingDesignSupplyAirHumidityRatio value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field CentralCoolingDesignSupplyAirHumidityRatio.'),
        ] = None,
        sizing_system_central_heating_design_supply_air_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional inline CentralHeatingDesignSupplyAirHumidityRatio value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field CentralHeatingDesignSupplyAirHumidityRatio.'),
        ] = None,
        sizing_system_cooling_design_air_flow_method: Annotated[
            str | None,
            Field(description='Optional inline CoolingDesignAirFlowMethod value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field CoolingDesignAirFlowMethod.'),
        ] = None,
        sizing_system_cooling_design_air_flow_rate: Annotated[
            float | None,
            Field(description='Optional inline CoolingDesignAirFlowRate value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field CoolingDesignAirFlowRate.'),
        ] = None,
        sizing_system_heating_design_air_flow_method: Annotated[
            str | None,
            Field(description='Optional inline HeatingDesignAirFlowMethod value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field HeatingDesignAirFlowMethod.'),
        ] = None,
        sizing_system_heating_design_air_flow_rate: Annotated[
            float | None,
            Field(description='Optional inline HeatingDesignAirFlowRate value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field HeatingDesignAirFlowRate.'),
        ] = None,
        sizing_system_system_outdoor_air_method: Annotated[
            str | None,
            Field(description='Optional inline SystemOutdoorAirMethod value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field SystemOutdoorAirMethod.'),
        ] = None,
        sizing_system_zone_maximum_outdoor_air_fraction: Annotated[
            float | None,
            Field(description='Optional inline ZoneMaximumOutdoorAirFraction value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field ZoneMaximumOutdoorAirFraction.'),
        ] = None,
        sizing_system_cooling_supply_air_flow_rate_per_floor_area: Annotated[
            float | None,
            Field(description='Optional inline CoolingSupplyAirFlowRatePerFloorArea value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field CoolingSupplyAirFlowRatePerFloorArea.'),
        ] = None,
        sizing_system_cooling_fractionof_autosized_cooling_supply_air_flow_rate: Annotated[
            float | None,
            Field(description='Optional inline CoolingFractionofAutosizedCoolingSupplyAirFlowRate value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field CoolingFractionofAutosizedCoolingSupplyAirFlowRate.'),
        ] = None,
        sizing_system_cooling_supply_air_flow_rate_per_unit_cooling_capacity: Annotated[
            float | None,
            Field(description='Optional inline CoolingSupplyAirFlowRatePerUnitCoolingCapacity value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field CoolingSupplyAirFlowRatePerUnitCoolingCapacity.'),
        ] = None,
        sizing_system_heating_supply_air_flow_rate_per_floor_area: Annotated[
            float | None,
            Field(description='Optional inline HeatingSupplyAirFlowRatePerFloorArea value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field HeatingSupplyAirFlowRatePerFloorArea.'),
        ] = None,
        sizing_system_heating_fractionof_autosized_heating_supply_air_flow_rate: Annotated[
            float | None,
            Field(description='Optional inline HeatingFractionofAutosizedHeatingSupplyAirFlowRate value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field HeatingFractionofAutosizedHeatingSupplyAirFlowRate.'),
        ] = None,
        sizing_system_heating_fractionof_autosized_cooling_supply_air_flow_rate: Annotated[
            float | None,
            Field(description='Optional inline HeatingFractionofAutosizedCoolingSupplyAirFlowRate value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field HeatingFractionofAutosizedCoolingSupplyAirFlowRate.'),
        ] = None,
        sizing_system_heating_supply_air_flow_rate_per_unit_heating_capacity: Annotated[
            float | None,
            Field(description='Optional inline HeatingSupplyAirFlowRatePerUnitHeatingCapacity value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field HeatingSupplyAirFlowRatePerUnitHeatingCapacity.'),
        ] = None,
        sizing_system_cooling_design_capacity_method: Annotated[
            str | None,
            Field(description='Optional inline CoolingDesignCapacityMethod value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field CoolingDesignCapacityMethod.'),
        ] = None,
        sizing_system_cooling_design_capacity: Annotated[
            float | str | None,
            Field(description='Optional inline CoolingDesignCapacity value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field CoolingDesignCapacity.'),
        ] = None,
        sizing_system_cooling_design_capacity_per_floor_area: Annotated[
            float | None,
            Field(description='Optional inline CoolingDesignCapacityPerFloorArea value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field CoolingDesignCapacityPerFloorArea.'),
        ] = None,
        sizing_system_fractionof_autosized_cooling_design_capacity: Annotated[
            float | None,
            Field(description='Optional inline FractionofAutosizedCoolingDesignCapacity value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field FractionofAutosizedCoolingDesignCapacity.'),
        ] = None,
        sizing_system_heating_design_capacity_method: Annotated[
            str | None,
            Field(description='Optional inline HeatingDesignCapacityMethod value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field HeatingDesignCapacityMethod.'),
        ] = None,
        sizing_system_heating_design_capacity: Annotated[
            float | str | None,
            Field(description='Optional inline HeatingDesignCapacity value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field HeatingDesignCapacity.'),
        ] = None,
        sizing_system_heating_design_capacity_per_floor_area: Annotated[
            float | None,
            Field(description='Optional inline HeatingDesignCapacityPerFloorArea value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field HeatingDesignCapacityPerFloorArea.'),
        ] = None,
        sizing_system_fractionof_autosized_heating_design_capacity: Annotated[
            float | None,
            Field(description='Optional inline FractionofAutosizedHeatingDesignCapacity value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field FractionofAutosizedHeatingDesignCapacity.'),
        ] = None,
        sizing_system_central_cooling_capacity_control_method: Annotated[
            str | None,
            Field(description='Optional inline CentralCoolingCapacityControlMethod value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field CentralCoolingCapacityControlMethod.'),
        ] = None,
        sizing_system_occupant_diversity: Annotated[
            float | str | None,
            Field(description='Optional inline OccupantDiversity value for IB_SizingSystem; maps to Ironbug IB_AirLoopHVAC.SizingSystem child field OccupantDiversity.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_AirLoopHVAC as a reviewed Ironbug Loops / AirLoop authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if night_cycle_control_type is not None:
            source_fields['NightCycleControlType'] = night_cycle_control_type
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        inline_source_property_children: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if design_supply_air_flow_rate is not None:
            source_fields['DesignSupplyAirFlowRate'] = design_supply_air_flow_rate
        if design_return_air_flow_fractionof_supply_air_flow is not None:
            source_fields['DesignReturnAirFlowFractionofSupplyAirFlow'] = design_return_air_flow_fractionof_supply_air_flow
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if availability_managers_targets is not None:
            source_field_targets['AvailabilityManagers'] = availability_managers_targets
        if sizing_system_target is not None:
            source_property_targets['SizingSystem'] = sizing_system_target
        inline_sizing_system_fields: dict[str, Any] = {}
        inline_sizing_system_field_targets: dict[str, Any] = {}
        if sizing_system_typeof_loadto_size_on is not None:
            inline_sizing_system_fields['TypeofLoadtoSizeOn'] = sizing_system_typeof_loadto_size_on
        if sizing_system_design_outdoor_air_flow_rate is not None:
            inline_sizing_system_fields['DesignOutdoorAirFlowRate'] = sizing_system_design_outdoor_air_flow_rate
        if sizing_system_central_heating_maximum_system_air_flow_ratio is not None:
            inline_sizing_system_fields['CentralHeatingMaximumSystemAirFlowRatio'] = sizing_system_central_heating_maximum_system_air_flow_ratio
        if sizing_system_preheat_design_temperature is not None:
            inline_sizing_system_fields['PreheatDesignTemperature'] = sizing_system_preheat_design_temperature
        if sizing_system_preheat_design_humidity_ratio is not None:
            inline_sizing_system_fields['PreheatDesignHumidityRatio'] = sizing_system_preheat_design_humidity_ratio
        if sizing_system_precool_design_temperature is not None:
            inline_sizing_system_fields['PrecoolDesignTemperature'] = sizing_system_precool_design_temperature
        if sizing_system_precool_design_humidity_ratio is not None:
            inline_sizing_system_fields['PrecoolDesignHumidityRatio'] = sizing_system_precool_design_humidity_ratio
        if sizing_system_central_cooling_design_supply_air_temperature is not None:
            inline_sizing_system_fields['CentralCoolingDesignSupplyAirTemperature'] = sizing_system_central_cooling_design_supply_air_temperature
        if sizing_system_central_heating_design_supply_air_temperature is not None:
            inline_sizing_system_fields['CentralHeatingDesignSupplyAirTemperature'] = sizing_system_central_heating_design_supply_air_temperature
        if sizing_system_sizing_option is not None:
            inline_sizing_system_fields['SizingOption'] = sizing_system_sizing_option
        if sizing_system_all_outdoor_airin_cooling is not None:
            inline_sizing_system_fields['AllOutdoorAirinCooling'] = sizing_system_all_outdoor_airin_cooling
        if sizing_system_all_outdoor_airin_heating is not None:
            inline_sizing_system_fields['AllOutdoorAirinHeating'] = sizing_system_all_outdoor_airin_heating
        if sizing_system_central_cooling_design_supply_air_humidity_ratio is not None:
            inline_sizing_system_fields['CentralCoolingDesignSupplyAirHumidityRatio'] = sizing_system_central_cooling_design_supply_air_humidity_ratio
        if sizing_system_central_heating_design_supply_air_humidity_ratio is not None:
            inline_sizing_system_fields['CentralHeatingDesignSupplyAirHumidityRatio'] = sizing_system_central_heating_design_supply_air_humidity_ratio
        if sizing_system_cooling_design_air_flow_method is not None:
            inline_sizing_system_fields['CoolingDesignAirFlowMethod'] = sizing_system_cooling_design_air_flow_method
        if sizing_system_cooling_design_air_flow_rate is not None:
            inline_sizing_system_fields['CoolingDesignAirFlowRate'] = sizing_system_cooling_design_air_flow_rate
        if sizing_system_heating_design_air_flow_method is not None:
            inline_sizing_system_fields['HeatingDesignAirFlowMethod'] = sizing_system_heating_design_air_flow_method
        if sizing_system_heating_design_air_flow_rate is not None:
            inline_sizing_system_fields['HeatingDesignAirFlowRate'] = sizing_system_heating_design_air_flow_rate
        if sizing_system_system_outdoor_air_method is not None:
            inline_sizing_system_fields['SystemOutdoorAirMethod'] = sizing_system_system_outdoor_air_method
        if sizing_system_zone_maximum_outdoor_air_fraction is not None:
            inline_sizing_system_fields['ZoneMaximumOutdoorAirFraction'] = sizing_system_zone_maximum_outdoor_air_fraction
        if sizing_system_cooling_supply_air_flow_rate_per_floor_area is not None:
            inline_sizing_system_fields['CoolingSupplyAirFlowRatePerFloorArea'] = sizing_system_cooling_supply_air_flow_rate_per_floor_area
        if sizing_system_cooling_fractionof_autosized_cooling_supply_air_flow_rate is not None:
            inline_sizing_system_fields['CoolingFractionofAutosizedCoolingSupplyAirFlowRate'] = sizing_system_cooling_fractionof_autosized_cooling_supply_air_flow_rate
        if sizing_system_cooling_supply_air_flow_rate_per_unit_cooling_capacity is not None:
            inline_sizing_system_fields['CoolingSupplyAirFlowRatePerUnitCoolingCapacity'] = sizing_system_cooling_supply_air_flow_rate_per_unit_cooling_capacity
        if sizing_system_heating_supply_air_flow_rate_per_floor_area is not None:
            inline_sizing_system_fields['HeatingSupplyAirFlowRatePerFloorArea'] = sizing_system_heating_supply_air_flow_rate_per_floor_area
        if sizing_system_heating_fractionof_autosized_heating_supply_air_flow_rate is not None:
            inline_sizing_system_fields['HeatingFractionofAutosizedHeatingSupplyAirFlowRate'] = sizing_system_heating_fractionof_autosized_heating_supply_air_flow_rate
        if sizing_system_heating_fractionof_autosized_cooling_supply_air_flow_rate is not None:
            inline_sizing_system_fields['HeatingFractionofAutosizedCoolingSupplyAirFlowRate'] = sizing_system_heating_fractionof_autosized_cooling_supply_air_flow_rate
        if sizing_system_heating_supply_air_flow_rate_per_unit_heating_capacity is not None:
            inline_sizing_system_fields['HeatingSupplyAirFlowRatePerUnitHeatingCapacity'] = sizing_system_heating_supply_air_flow_rate_per_unit_heating_capacity
        if sizing_system_cooling_design_capacity_method is not None:
            inline_sizing_system_fields['CoolingDesignCapacityMethod'] = sizing_system_cooling_design_capacity_method
        if sizing_system_cooling_design_capacity is not None:
            inline_sizing_system_fields['CoolingDesignCapacity'] = sizing_system_cooling_design_capacity
        if sizing_system_cooling_design_capacity_per_floor_area is not None:
            inline_sizing_system_fields['CoolingDesignCapacityPerFloorArea'] = sizing_system_cooling_design_capacity_per_floor_area
        if sizing_system_fractionof_autosized_cooling_design_capacity is not None:
            inline_sizing_system_fields['FractionofAutosizedCoolingDesignCapacity'] = sizing_system_fractionof_autosized_cooling_design_capacity
        if sizing_system_heating_design_capacity_method is not None:
            inline_sizing_system_fields['HeatingDesignCapacityMethod'] = sizing_system_heating_design_capacity_method
        if sizing_system_heating_design_capacity is not None:
            inline_sizing_system_fields['HeatingDesignCapacity'] = sizing_system_heating_design_capacity
        if sizing_system_heating_design_capacity_per_floor_area is not None:
            inline_sizing_system_fields['HeatingDesignCapacityPerFloorArea'] = sizing_system_heating_design_capacity_per_floor_area
        if sizing_system_fractionof_autosized_heating_design_capacity is not None:
            inline_sizing_system_fields['FractionofAutosizedHeatingDesignCapacity'] = sizing_system_fractionof_autosized_heating_design_capacity
        if sizing_system_central_cooling_capacity_control_method is not None:
            inline_sizing_system_fields['CentralCoolingCapacityControlMethod'] = sizing_system_central_cooling_capacity_control_method
        if sizing_system_occupant_diversity is not None:
            inline_sizing_system_fields['OccupantDiversity'] = sizing_system_occupant_diversity
        if sizing_system_identifier is not None or inline_sizing_system_fields or inline_sizing_system_field_targets:
            if sizing_system_target is not None:
                raise ValueError("Provide either sizing_system_target or inline sizing_system_* parameters, not both.")
            inline_source_property_children['SizingSystem'] = {
                'source_class': 'IB_SizingSystem',
                'is_list': False,
                'identifiers': sizing_system_identifier,
                'source_fields': inline_sizing_system_fields,
                'source_field_targets': inline_sizing_system_field_targets,
            }
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_AirLoopHVAC',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            source_property_targets=source_property_targets or None,
            inline_source_property_children=inline_source_property_children or None,
            overwrite=overwrite,
        )
        latest_model_target = created["updated_model_target"]
        binding_summary: dict[str, Any] = {}
        if supply_component_targets is not None:
            supply = set_ironbug_air_loop_supply_components(
                garden_root=garden_root,
                ironbug_model_target=latest_model_target,
                air_loop_target=created["target"],
                supply_component_targets=supply_component_targets,
            )
            latest_model_target = supply["updated_model_target"]
            created["target"] = supply["target"]
            binding_summary["supply_components_bound"] = True
            binding_summary["supply_component_count"] = supply["summary_view"][
                "supply_component_count"
            ]
        else:
            binding_summary["supply_components_bound"] = False
        if demand_component_targets is not None:
            demand = set_ironbug_air_loop_demand_components(
                garden_root=garden_root,
                ironbug_model_target=latest_model_target,
                air_loop_target=created["target"],
                demand_component_targets=demand_component_targets,
            )
            latest_model_target = demand["updated_model_target"]
            created["target"] = demand["target"]
            binding_summary["demand_components_bound"] = True
            binding_summary["demand_component_count"] = demand["summary_view"][
                "demand_component_count"
            ]
        else:
            binding_summary["demand_components_bound"] = False
        created["updated_model_target"] = latest_model_target
        created["summary_view"] = {**created["summary_view"], **binding_summary}
        return created
