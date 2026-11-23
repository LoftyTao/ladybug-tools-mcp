"""Configure Ironbug thermal zones, air loops, plant loops, and VRF topologies."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.tools.ironbug._schemas import (
    AirLoopConfig,
    IronbugModelTargetRef,
    IronbugSystemMutationResult,
    PlantLoopConfig,
    ThermalZoneConfig,
    VrfSystemConfig,
    dump_models,
    dump_target,
)


def register(mcp: FastMCP) -> None:
    """Register IB_configure_loops."""

    @mcp.tool(
        name="IB_configure_loops",
        description=(
            "Wire Ironbug components into thermal_zones, air_loops, plant_loops, "
            "vrf_systems, energy_management_system, and electric_load_center, then serialize "
            "the IB_HVACSystem. Zones omitted from air_loops use IB_NoAirLoop; parallel "
            "plant branches use nested lists such as [['coil1'], ['coil2']]."
        ),
        tags={"ironbug", "detailed-hvac", "hvac", "author", "edit"},
        annotations={"read_only_hint": False, "destructive_hint": False},
        timeout=30,
    )
    def ib_configure_loops(
        garden_root: Annotated[
            str,
            Field(min_length=1, description="Required Garden root path containing garden.json."),
        ],
        ironbug_model_target: Annotated[
            IronbugModelTargetRef | None,
            Field(description="Target returned by IB_create_system. Optional when only one Ironbug system exists."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional Ironbug system identifier when ironbug_model_target is omitted."),
        ] = None,
        thermal_zones: Annotated[
            list[ThermalZoneConfig] | None,
            Field(description="Optional zone-to-equipment / air-terminal bindings."),
        ] = None,
        air_loops: Annotated[
            list[AirLoopConfig] | None,
            Field(description="Optional central AirLoopHVAC topology configurations."),
        ] = None,
        plant_loops: Annotated[
            list[PlantLoopConfig] | None,
            Field(description="Optional hydronic PlantLoop configurations."),
        ] = None,
        vrf_systems: Annotated[
            list[VrfSystemConfig] | None,
            Field(description="Optional VRF outdoor unit to terminal bindings."),
        ] = None,
        energy_management_system: Annotated[
            str | None,
            Field(
                description=(
                    "Optional IB_EnergyManagementSystem component ID to attach on IB_HVACSystem; "
                    "pass '' to clear."
                )
            ),
        ] = None,
        electric_load_center: Annotated[
            str | None,
            Field(
                description=(
                    "Optional IB_ElectricLoadCenter component ID to attach on IB_HVACSystem; "
                    "pass '' to clear."
                )
            ),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional updated DisplayName on IB_HVACSystem."),
        ] = None,
        replace: Annotated[
            bool,
            Field(
                description=(
                    "If true, reset existing loop/system bindings (or replace an imported-only "
                    "specification) before applying provided configurations."
                )
            ),
        ] = False,
    ) -> IronbugSystemMutationResult:
        """Configure loops and thermal zone bindings on an Ironbug system."""
        from garden.ironbug.service import configure_ironbug_loops

        return IronbugSystemMutationResult.model_validate(
            configure_ironbug_loops(
                garden_root=garden_root,
                ironbug_model_target=dump_target(ironbug_model_target),
                identifier=identifier,
                thermal_zones=dump_models(thermal_zones),
                air_loops=dump_models(air_loops),
                plant_loops=dump_models(plant_loops),
                vrf_systems=dump_models(vrf_systems),
                energy_management_system=energy_management_system,
                electric_load_center=electric_load_center,
                display_name=display_name,
                replace=replace,
            )
        )
