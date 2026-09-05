"""Create Dragonfly DES FluidParameter MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the DES GHE fluid parameter tool."""

    @mcp.tool(
        name="DF_des_create_ghe_fluid_parameter",
        description=(
            "Create a Dragonfly DES FluidParameter for a ground heat exchanger loop, "
            "including fluid type, concentration, and design temperature. Use the "
            "returned target in GHE thermal loop authoring. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "district-energy", "author", "fluid", "geothermal", "parameter", "target"},
        timeout=20,
    )
    def create_ghe_fluid_parameter(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually GD_create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved FluidParameter target.")],
        fluid_type: Annotated[str | None, Field(description="Optional SDK fluid type such as Water or EthyleneGlycol; omitted values use the Dragonfly Energy SDK default.")] = None,
        concentration: Annotated[float | None, Field(description="Optional fluid concentration percentage; omitted values use the Dragonfly Energy SDK default.")] = None,
        temperature: Annotated[float | None, Field(description="Optional fluid temperature in Celsius; omitted values use the Dragonfly Energy SDK default.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES FluidParameter."""
        from garden.dragonfly_des.authoring import create_ghe_fluid_parameter as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            fluid_type=fluid_type,
            concentration=concentration,
            temperature=temperature,
        )
