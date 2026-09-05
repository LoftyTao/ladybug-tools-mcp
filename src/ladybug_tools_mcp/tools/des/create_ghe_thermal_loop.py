"""Create Dragonfly DES GHEThermalLoop MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the GHE DES thermal loop tool."""

    @mcp.tool(
        name="DF_des_create_ghe_thermal_loop",
        description=(
            "Create a Dragonfly DES GHEThermalLoop from GroundHeatExchanger and "
            "ThermalConnector targets plus optional soil, fluid, pipe, borehole, "
            "design, and horizontal-pipe parameter targets. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"borehole", "dragonfly", "district-energy", "author", "geothermal", "ground-heat-exchanger", "ground-loop", "loop", "target"},
        timeout=20,
    )
    def create_ghe_thermal_loop(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually GD_create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved GHEThermalLoop target.")],
        ground_heat_exchanger_targets: Annotated[list[dict[str, Any]], Field(description="One or more Dragonfly DES GroundHeatExchanger targets for the loop.")],
        connector_targets: Annotated[list[dict[str, Any]], Field(description="One or more Dragonfly DES ThermalConnector targets for the loop piping.")],
        clockwise_flow: Annotated[bool, Field(description="Whether loop connector flow should be interpreted as clockwise.")] = False,
        soil_parameter_target: Annotated[dict[str, Any] | None, Field(description="Optional Dragonfly DES SoilParameter target for the GHE loop.")] = None,
        fluid_parameter_target: Annotated[dict[str, Any] | None, Field(description="Optional Dragonfly DES FluidParameter target for the GHE loop.")] = None,
        pipe_parameter_target: Annotated[dict[str, Any] | None, Field(description="Optional Dragonfly DES PipeParameter target for borehole pipe properties.")] = None,
        borehole_parameter_target: Annotated[dict[str, Any] | None, Field(description="Optional Dragonfly DES BoreholeParameter target for borehole depth and spacing.")] = None,
        design_parameter_target: Annotated[dict[str, Any] | None, Field(description="Optional Dragonfly DES GHEDesignParameter target for GHE sizing criteria.")] = None,
        horizontal_pipe_parameter_target: Annotated[dict[str, Any] | None, Field(description="Optional Dragonfly DES HorizontalPipeParameter target for connector pipe properties.")] = None,
        heat_rejection_type: Annotated[str, Field(description="Dragonfly Energy heat rejection type for the GHE thermal loop: CoolingTower, FluidCooler, EvaporativeFluidCooler, DistrictCooling, or None.")] = "CoolingTower",
        supplemental_heat_type: Annotated[str, Field(description="Dragonfly Energy supplemental heat type for the GHE thermal loop: Electricity, NaturalGas, DistrictHeating, or None.")] = "Electricity",
        display_name: Annotated[str | None, Field(description="Optional display name stored on SDK objects that support display_name.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES GHEThermalLoop."""
        from garden.dragonfly_des.authoring import create_ghe_thermal_loop as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            ground_heat_exchanger_targets=ground_heat_exchanger_targets,
            connector_targets=connector_targets,
            clockwise_flow=clockwise_flow,
            soil_parameter_target=soil_parameter_target,
            fluid_parameter_target=fluid_parameter_target,
            pipe_parameter_target=pipe_parameter_target,
            borehole_parameter_target=borehole_parameter_target,
            design_parameter_target=design_parameter_target,
            horizontal_pipe_parameter_target=horizontal_pipe_parameter_target,
            heat_rejection_type=heat_rejection_type,
            supplemental_heat_type=supplemental_heat_type,
            display_name=display_name,
        )
