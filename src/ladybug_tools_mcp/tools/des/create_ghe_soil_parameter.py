"""Create Dragonfly DES SoilParameter MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_des.authoring import create_ghe_soil_parameter as service


def register(mcp: FastMCP) -> None:
    """Register the DES GHE soil parameter tool."""

    @mcp.tool(
        name="create_ghe_soil_parameter",
        description=(
            "Create a Dragonfly DES SoilParameter for ground heat exchanger design, "
            "including soil and grout conductivity, heat capacity, and optional "
            "undisturbed temperature. Use the returned target in GHE field or loop "
            "authoring. Returns target, summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "district-energy", "author", "geothermal", "ground-loop", "parameter", "target"},
        timeout=20,
    )
    def create_ghe_soil_parameter(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved SoilParameter target.")],
        conductivity: Annotated[float | None, Field(description="Optional soil conductivity in W/m-K; omitted values use the Dragonfly Energy SDK default.")] = None,
        heat_capacity: Annotated[float | None, Field(description="Optional soil heat capacity in J/m3-K; omitted values use the Dragonfly Energy SDK default.")] = None,
        undisturbed_temperature: Annotated[float | None, Field(description="Optional undisturbed ground temperature in Celsius; omit to keep the SDK Autocalculate value.")] = None,
        grout_conductivity: Annotated[float | None, Field(description="Optional grout conductivity in W/m-K; omitted values use the Dragonfly Energy SDK default.")] = None,
        grout_heat_capacity: Annotated[float | None, Field(description="Optional grout heat capacity in J/m3-K; omitted values use the Dragonfly Energy SDK default.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES SoilParameter."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            conductivity=conductivity,
            heat_capacity=heat_capacity,
            undisturbed_temperature=undisturbed_temperature,
            grout_conductivity=grout_conductivity,
            grout_heat_capacity=grout_heat_capacity,
        )
