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
            "OpenStudio, EnergyPlus, URBANopt, and THERM. Use this when a simulation or "
            "postprocess cannot find local runtime commands, before long Agent "
            "tests, or when checking whether the URBANopt CLI/Gemfile setup for "
            "Dragonfly Energy district workflows or the Windows-only THERM runtime "
            "for Fairyfly workflows is available. The result returns "
            "radiance, openstudio, energyplus, urbanopt, and therm together under "
            "summary_view.engines, including engine paths, executable existence "
            "flags, versions, URBANopt CLI and Gemfile paths, setup-env candidates, "
            "THERM executable status, and path_updates.prepend values that can be "
            "prepended to PATH. This "
            "tool is read-only and does not create Gardens, run setup-env, or run "
            "simulations."
        ),
        tags={
            "config",
            "runtime",
            "ladybug-tools",
            "urbanopt",
            "therm",
            "fairyfly",
            "dragonfly-energy",
            "district",
            "geojson",
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
