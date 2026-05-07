"""Ladybug Tools SDK runtime configuration MCP tool."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from garden.ladybug_tools_config import get_ladybug_tools_config as service


def register(mcp: FastMCP) -> None:
    """Register the get_ladybug_tools_config tool."""

    @mcp.tool(
        name="get_ladybug_tools_config",
        description=(
            "Return compact Ladybug Tools SDK runtime configuration for Radiance, "
            "OpenStudio, and EnergyPlus. Use this when a simulation or postprocess "
            "cannot find local runtime commands, or before long Agent tests. The "
            "result includes engine paths, executable existence flags, versions, and "
            "path_updates.prepend values that can be prepended to PATH. This tool is "
            "read-only and does not create Gardens or run simulations."
        ),
        tags={
            "config",
            "runtime",
            "ladybug-tools",
            "radiance",
            "openstudio",
            "energyplus",
            "path",
            "environment",
        },
    )
    def get_ladybug_tools_config(
        include_path_updates: Annotated[
            bool,
            Field(
                description=(
                    "Include compact PATH prepend hints for local shells and Agent "
                    "test harnesses."
                )
            ),
        ] = True,
        garden_root: Annotated[
            str | None,
            Field(description="Optional Garden context hint accepted for Agent compatibility. Ignored."),
        ] = None,
    ) -> dict:
        """Return compact local Ladybug Tools SDK runtime configuration."""
        _ = garden_root
        result = service()
        if not include_path_updates:
            result["summary_view"].pop("path_updates", None)
        return result
