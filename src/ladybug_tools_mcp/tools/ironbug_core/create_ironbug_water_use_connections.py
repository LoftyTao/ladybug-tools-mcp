'MCP tool for detailed_hvac_water_use_connections.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_water_use_connections tool.'

    @mcp.tool(
        name='water_use_connections',
        description=(
            'Create IB_WaterUseConnections, the Ironbug and EnergyPlus WaterUse:Connections plant-loop subsystem that groups one or more WaterUse:Equipment fixtures. It provides shared hot/cold supply schedules, plant-loop inlet/outlet connection context, optional storage links, and drainwater heat recovery fields; it is not a water heater or fixture definition. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'plant-component', 'plant-loop', 'water-use', 'service-hot-water', 'schedule', 'heat-recovery', 'author', 'component'},
        timeout=20,
    )
    def create_ironbug_water_use_connections(
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
            Field(description="Stable identifier for the new IB_WaterUseConnections object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        water_use_equipment_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional IB_WaterUseEquipment targets grouped by this WaterUse:Connections object."),
        ] = None,
        hot_water_supply_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for HotWaterSupplyTemperatureSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_WaterUseConnections field HotWaterSupplyTemperatureSchedule (IB_Schedule).'),
        ] = None,
        cold_water_supply_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for ColdWaterSupplyTemperatureSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_WaterUseConnections field ColdWaterSupplyTemperatureSchedule (IB_Schedule).'),
        ] = None,
        drain_water_heat_exchanger_type: Annotated[
            str | None,
            Field(description='Optional DrainWaterHeatExchangerType value; maps to Ironbug IB_WaterUseConnections field DrainWaterHeatExchangerType.'),
        ] = None,
        drain_water_heat_exchanger_destination: Annotated[
            str | None,
            Field(description='Optional DrainWaterHeatExchangerDestination value; maps to Ironbug IB_WaterUseConnections field DrainWaterHeatExchangerDestination.'),
        ] = None,
        drain_water_heat_exchanger_u_factor_times_area: Annotated[
            float | None,
            Field(description='Optional DrainWaterHeatExchangerUFactorTimesArea value; maps to Ironbug IB_WaterUseConnections field DrainWaterHeatExchangerUFactorTimesArea.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_WaterUseConnections field Name.'),
        ] = None,
        water_use_equips_identifiers: Annotated[
            list[str] | None,
            Field(description='Optional inline IB_WaterUseEquipment identifiers for IB_WaterUseConnections.WaterUseEquips.'),
        ] = None,
        water_use_equips_name_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline Name value for IB_WaterUseEquipment; maps to Ironbug IB_WaterUseConnections.WaterUseEquips child field Name.'),
        ] = None,
        water_use_equips_flow_rate_fraction_schedule_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug object target for FlowRateFractionSchedule; pass target dicts from compatible create_ironbug_* tools or same-model identifiers. Maps to Ironbug IB_WaterUseConnections.WaterUseEquips child IB_WaterUseEquipment field FlowRateFractionSchedule.'),
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
        """Create Ironbug water-use connection grouping."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        inline_source_property_children: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if hot_water_supply_temperature_schedule_target is not None:
            source_field_targets['HotWaterSupplyTemperatureSchedule'] = hot_water_supply_temperature_schedule_target
        if cold_water_supply_temperature_schedule_target is not None:
            source_field_targets['ColdWaterSupplyTemperatureSchedule'] = cold_water_supply_temperature_schedule_target
        if drain_water_heat_exchanger_type is not None:
            source_fields['DrainWaterHeatExchangerType'] = drain_water_heat_exchanger_type
        if drain_water_heat_exchanger_destination is not None:
            source_fields['DrainWaterHeatExchangerDestination'] = drain_water_heat_exchanger_destination
        if drain_water_heat_exchanger_u_factor_times_area is not None:
            source_fields['DrainWaterHeatExchangerUFactorTimesArea'] = drain_water_heat_exchanger_u_factor_times_area
        if water_use_equipment_targets is not None:
            source_property_targets['WaterUseEquips'] = water_use_equipment_targets
        inline_water_use_equips_fields: dict[str, Any] = {}
        inline_water_use_equips_field_targets: dict[str, Any] = {}
        if water_use_equips_name_values is not None:
            inline_water_use_equips_fields['Name'] = water_use_equips_name_values
        if water_use_equips_flow_rate_fraction_schedule_targets is not None:
            inline_water_use_equips_field_targets['FlowRateFractionSchedule'] = water_use_equips_flow_rate_fraction_schedule_targets
        if water_use_equips_identifiers is not None or inline_water_use_equips_fields or inline_water_use_equips_field_targets:
            if water_use_equipment_targets is not None:
                raise ValueError("Provide either water_use_equipment_targets or inline water_use_equips_* parameters, not both.")
            inline_source_property_children['WaterUseEquips'] = {
                'source_class': 'IB_WaterUseEquipment',
                'is_list': True,
                'identifiers': water_use_equips_identifiers,
                'source_fields': inline_water_use_equips_fields,
                'source_field_targets': inline_water_use_equips_field_targets,
            }
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_WaterUseConnections',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            source_property_targets=source_property_targets or None,
            inline_source_property_children=inline_source_property_children or None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
