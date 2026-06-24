"""Create Dragonfly DES FourthGenThermalLoop MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_des.authoring import create_fourth_gen_thermal_loop as service


def register(mcp: FastMCP) -> None:
    """Register the fourth-generation DES thermal loop tool."""

    @mcp.tool(
        name="create_fourth_gen_thermal_loop",
        description=(
            "Create a Dragonfly DES FourthGenThermalLoop target for high-temperature "
            "district heating or cooling loop authoring. Slice 1 omits plant target "
            "binding and records that boundary in the report. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "district-energy", "author", "heating", "cooling", "loop", "target"},
        timeout=20,
    )
    def create_fourth_gen_thermal_loop(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved FourthGenThermalLoop target.")],
        economizer_type: Annotated[str, Field(description="Dragonfly Energy economizer type for the fourth-generation loop.")] = "None",
        heating_type: Annotated[str, Field(description="Dragonfly Energy heating type for the fourth-generation loop.")] = "NaturalGas",
        display_name: Annotated[str | None, Field(description="Optional display name stored on SDK objects that support display_name.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES FourthGenThermalLoop."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            economizer_type=economizer_type,
            heating_type=heating_type,
            display_name=display_name,
        )
