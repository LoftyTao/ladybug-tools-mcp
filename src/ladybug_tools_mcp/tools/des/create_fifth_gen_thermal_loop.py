"""Create Dragonfly DES FifthGenThermalLoop MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_des.authoring import create_fifth_gen_thermal_loop as service


def register(mcp: FastMCP) -> None:
    """Register the fifth-generation DES thermal loop tool."""

    @mcp.tool(
        name="create_fifth_gen_thermal_loop",
        description=(
            "Create a Dragonfly DES FifthGenThermalLoop from ThermalConnector targets "
            "plus optional soil and horizontal-pipe parameter targets. Use it for "
            "ambient-water district loops without a GHE field. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "district-energy", "author", "ground-loop", "loop", "pipe", "target"},
        timeout=20,
    )
    def create_fifth_gen_thermal_loop(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved FifthGenThermalLoop target.")],
        connector_targets: Annotated[list[dict[str, Any]], Field(description="One or more Dragonfly DES ThermalConnector targets to include in the loop.")],
        clockwise_flow: Annotated[bool, Field(description="Whether loop connector flow should be interpreted as clockwise.")] = False,
        soil_parameter_target: Annotated[dict[str, Any] | None, Field(description="Optional Dragonfly DES SoilParameter target for horizontal-pipe heat transfer context.")] = None,
        horizontal_pipe_parameter_target: Annotated[dict[str, Any] | None, Field(description="Optional Dragonfly DES HorizontalPipeParameter target for connector pipe properties.")] = None,
        heat_rejection_type: Annotated[str, Field(description="Dragonfly Energy heat rejection type for the fifth-generation loop: CoolingTower, FluidCooler, EvaporativeFluidCooler, DistrictCooling, or None.")] = "CoolingTower",
        supplemental_heat_type: Annotated[str, Field(description="Dragonfly Energy supplemental heat type for the fifth-generation loop: Electricity, NaturalGas, DistrictHeating, or None.")] = "Electricity",
        display_name: Annotated[str | None, Field(description="Optional display name stored on SDK objects that support display_name.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES FifthGenThermalLoop."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            connector_targets=connector_targets,
            clockwise_flow=clockwise_flow,
            soil_parameter_target=soil_parameter_target,
            horizontal_pipe_parameter_target=horizontal_pipe_parameter_target,
            heat_rejection_type=heat_rejection_type,
            supplemental_heat_type=supplemental_heat_type,
            display_name=display_name,
        )
