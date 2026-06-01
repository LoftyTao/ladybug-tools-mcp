"""Create an Ironbug condenser-water loop MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.semantic_loops import create_ironbug_semantic_water_loop

TargetRef = dict[str, Any] | str
BranchTargetRef = TargetRef | list[TargetRef]


def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_plant_loop_condenser_water tool.'

    @mcp.tool(
        name="plant_loop_condenser_water",
        description=(
            "Create a reviewed condenser-water Ironbug loop from pump, heat "
            "rejection, and connected equipment targets. This is a public "
            "condenser-loop authoring path; it does not expose generic PlantLoop "
            "or explicit OperationScheme inputs. If exactly one pump is present, "
            "it is placed as a direct loop supply component before the supply "
            "branch group. If no pump is present in supply_branch_component_targets, "
            "the service adds a source-backed default IB_PumpConstantSpeed for "
            "EnergyPlus-ready topology. Apply DetailedHVAC to Honeybee or "
            "Dragonfly, then run the standard Ladybug Tools MCP Energy workflow."
        ),
        tags={"ironbug", "plant-loop", "condenser-water", "author"},
        timeout=20,
    )
    def create_ironbug_condenser_water_loop(
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
            Field(description="Stable identifier for the condenser-water loop."),
        ],
        loop_name: Annotated[
            str | None,
            Field(description="Optional loop Name; defaults to the identifier."),
        ] = None,
        load_distribution_scheme: Annotated[
            str | None,
            Field(description="Optional IB_PlantLoop ObjParams value LoadDistributionScheme."),
        ] = None,
        fluid_type: Annotated[
            str,
            Field(description="IB_PlantLoop ObjParams value FluidType."),
        ] = "Water",
        glycol_concentration: Annotated[
            int | None,
            Field(description="Optional IB_PlantLoop ObjParams value GlycolConcentration."),
        ] = None,
        maximum_loop_temperature: Annotated[
            float | None,
            Field(description="Optional IB_PlantLoop ObjParams value MaximumLoopTemperature."),
        ] = None,
        minimum_loop_temperature: Annotated[
            float | None,
            Field(description="Optional IB_PlantLoop ObjParams value MinimumLoopTemperature."),
        ] = None,
        maximum_loop_flow_rate: Annotated[
            float | str | None,
            Field(description="Optional IB_PlantLoop ObjParams value MaximumLoopFlowRate."),
        ] = None,
        minimum_loop_flow_rate: Annotated[
            float | None,
            Field(description="Optional IB_PlantLoop ObjParams value MinimumLoopFlowRate."),
        ] = None,
        plant_loop_volume: Annotated[
            float | None,
            Field(description="Optional IB_PlantLoop ObjParams value PlantLoopVolume."),
        ] = None,
        common_pipe_simulation: Annotated[
            str | None,
            Field(description="Optional IB_PlantLoop ObjParams value CommonPipeSimulation."),
        ] = None,
        plant_equipment_operation_heating_load_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Schedule target for IB_PlantLoop ObjParams field PlantEquipmentOperationHeatingLoadSchedule."),
        ] = None,
        plant_equipment_operation_cooling_load_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Schedule target for IB_PlantLoop ObjParams field PlantEquipmentOperationCoolingLoadSchedule."),
        ] = None,
        primary_plant_equipment_operation_scheme_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Schedule target for IB_PlantLoop ObjParams field PrimaryPlantEquipmentOperationSchemeSchedule."),
        ] = None,
        component_setpoint_operation_scheme_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_Schedule target for IB_PlantLoop ObjParams field ComponentSetpointOperationSchemeSchedule."),
        ] = None,
        availability_managers_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional IB_AvailabilityManager targets for IB_PlantLoop ObjParams field AvailabilityManagers."),
        ] = None,
        sizing_plant_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_SizingPlant target for the Grasshopper sizingLoop input; omit to use the semantic loop sizing defaults."),
        ] = None,
        sizing_plant_identifier: Annotated[
            str | None,
            Field(description="Optional inline IB_SizingPlant identifier for the semantic loop SizingPlant source property."),
        ] = None,
        sizing_plant_loop_type: Annotated[
            str | None,
            Field(description="Optional inline IB_SizingPlant ObjParams value LoopType for the semantic loop SizingPlant source property."),
        ] = None,
        sizing_plant_design_loop_exit_temperature: Annotated[
            float | None,
            Field(description="Optional inline IB_SizingPlant ObjParams value DesignLoopExitTemperature for the semantic loop SizingPlant source property."),
        ] = None,
        sizing_plant_loop_design_temperature_difference: Annotated[
            float | None,
            Field(description="Optional inline IB_SizingPlant ObjParams value LoopDesignTemperatureDifference for the semantic loop SizingPlant source property."),
        ] = None,
        sizing_plant_sizing_option: Annotated[
            str | None,
            Field(description="Optional inline IB_SizingPlant ObjParams value SizingOption for the semantic loop SizingPlant source property."),
        ] = None,
        sizing_plant_zone_timestepsin_averaging_window: Annotated[
            int | None,
            Field(description="Optional inline IB_SizingPlant ObjParams value ZoneTimestepsinAveragingWindow for the semantic loop SizingPlant source property."),
        ] = None,
        sizing_plant_coincident_sizing_factor_mode: Annotated[
            str | None,
            Field(description="Optional inline IB_SizingPlant ObjParams value CoincidentSizingFactorMode for the semantic loop SizingPlant source property."),
        ] = None,
        operation_scheme_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional IB_PlantEquipmentOperationSchemeBase target for the Grasshopper Operation Scheme input."),
        ] = None,
        supply_branch_component_targets: Annotated[
            list[BranchTargetRef] | None,
            Field(
                description=(
                    "Ordered supply-side pump and heat-rejection component targets "
                    "or same-model identifiers. Include an explicit pump when "
                    "you need pump-specific settings; otherwise a default "
                    "IB_PumpConstantSpeed is created. When exactly one pump is "
                    "included, the loop places it directly on the supply side "
                    "and keeps the remaining heat-rejection equipment in branch "
                    "groups. A flat list is one serial equipment branch; a "
                    "nested list such as [[source_target_1], [source_target_2, "
                    "source_target_3]] creates multiple parallel branches, "
                    "each preserving its inner serial component order."
                )
            ),
        ] = None,
        demand_branch_component_targets: Annotated[
            list[BranchTargetRef] | None,
            Field(
                description=(
                    "Ordered demand-side chiller or heat-exchanger component targets "
                    "or same-model identifiers. A flat list is one serial "
                    "branch; a nested list such as [[chiller_1_target], "
                    "[chiller_2_target, chiller_3_target]] creates multiple "
                    "parallel branches, each preserving its inner serial "
                    "component order. This branch-shape rule applies to all "
                    "plant-loop components; when separate chillers, heat "
                    "exchangers, towers, tanks, or loads should be parallel, "
                    "use one inner list per component or per intended serial "
                    "group."
                )
            ),
        ] = None,
        setpoint_c: Annotated[
            float,
            Field(description="Condenser-water loop temperature setpoint in Celsius."),
        ] = 29.4,
        loop_design_temperature_difference: Annotated[
            float,
            Field(description="Sizing:Plant loop design temperature difference."),
        ] = 5.6,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing condenser-water loop with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create a condenser-water Ironbug loop."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if fluid_type is not None:
            source_fields["FluidType"] = fluid_type
        if load_distribution_scheme is not None:
            source_fields["LoadDistributionScheme"] = load_distribution_scheme
        if glycol_concentration is not None:
            source_fields["GlycolConcentration"] = glycol_concentration
        if maximum_loop_temperature is not None:
            source_fields["MaximumLoopTemperature"] = maximum_loop_temperature
        if minimum_loop_temperature is not None:
            source_fields["MinimumLoopTemperature"] = minimum_loop_temperature
        if maximum_loop_flow_rate is not None:
            source_fields["MaximumLoopFlowRate"] = maximum_loop_flow_rate
        if minimum_loop_flow_rate is not None:
            source_fields["MinimumLoopFlowRate"] = minimum_loop_flow_rate
        if plant_loop_volume is not None:
            source_fields["PlantLoopVolume"] = plant_loop_volume
        if common_pipe_simulation is not None:
            source_fields["CommonPipeSimulation"] = common_pipe_simulation
        if plant_equipment_operation_heating_load_schedule_target is not None:
            source_field_targets["PlantEquipmentOperationHeatingLoadSchedule"] = plant_equipment_operation_heating_load_schedule_target
        if plant_equipment_operation_cooling_load_schedule_target is not None:
            source_field_targets["PlantEquipmentOperationCoolingLoadSchedule"] = plant_equipment_operation_cooling_load_schedule_target
        if primary_plant_equipment_operation_scheme_schedule_target is not None:
            source_field_targets["PrimaryPlantEquipmentOperationSchemeSchedule"] = primary_plant_equipment_operation_scheme_schedule_target
        if component_setpoint_operation_scheme_schedule_target is not None:
            source_field_targets["ComponentSetpointOperationSchemeSchedule"] = component_setpoint_operation_scheme_schedule_target
        if availability_managers_targets is not None:
            source_field_targets["AvailabilityManagers"] = availability_managers_targets
        sizing_plant_fields: dict[str, Any] = {}
        if sizing_plant_loop_type is not None:
            sizing_plant_fields["LoopType"] = sizing_plant_loop_type
        if sizing_plant_design_loop_exit_temperature is not None:
            sizing_plant_fields["DesignLoopExitTemperature"] = sizing_plant_design_loop_exit_temperature
        if sizing_plant_loop_design_temperature_difference is not None:
            sizing_plant_fields["LoopDesignTemperatureDifference"] = sizing_plant_loop_design_temperature_difference
        if sizing_plant_sizing_option is not None:
            sizing_plant_fields["SizingOption"] = sizing_plant_sizing_option
        if sizing_plant_zone_timestepsin_averaging_window is not None:
            sizing_plant_fields["ZoneTimestepsinAveragingWindow"] = sizing_plant_zone_timestepsin_averaging_window
        if sizing_plant_coincident_sizing_factor_mode is not None:
            sizing_plant_fields["CoincidentSizingFactorMode"] = sizing_plant_coincident_sizing_factor_mode
        if sizing_plant_target is not None and (
            sizing_plant_identifier is not None or sizing_plant_fields
        ):
            raise ValueError(
                "Provide either sizing_plant_target or inline sizing_plant_* parameters, not both."
            )
        return create_ironbug_semantic_water_loop(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            identifier=identifier,
            loop_name=loop_name or identifier,
            loop_type="Condenser",
            supply_branch_component_targets=supply_branch_component_targets,
            demand_branch_component_targets=demand_branch_component_targets,
            setpoint_c=setpoint_c,
            fluid_type=fluid_type,
            loop_design_temperature_difference=loop_design_temperature_difference,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            sizing_plant_target=sizing_plant_target,
            sizing_plant_identifier=sizing_plant_identifier,
            sizing_plant_fields=sizing_plant_fields or None,
            operation_scheme_target=operation_scheme_target,
            overwrite=overwrite,
        )
