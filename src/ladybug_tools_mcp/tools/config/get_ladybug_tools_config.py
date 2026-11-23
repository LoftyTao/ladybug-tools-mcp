"""Ladybug Tools SDK runtime configuration MCP tool."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    'Register the LB_get_runtime_config tool.'

    @mcp.tool(
        name="LB_get_runtime_config",
        description=(
            'Diagnose the local Ladybug Tools runtime configuration for Radiance, OpenStudio, '
            'EnergyPlus, URBANopt, THERM, and Ironbug.Console. Use this read-only tool to inspect '
            'which simulation runtimes and executables the installed SDK can currently see. '
            'Returns summary_view.engines, summary_view.measures, missing_engine_guidance, '
            'runtime_requirement_guidance, report, and optional path_updates.prepend values for '
            'local shell PATH setup.'
        ),
        tags={
            "check",
            "config",
            "energyplus",
            "openstudio",
            "radiance",
            "runtime",
            "therm",
            "urbanopt",
        },
    )
    def get_ladybug_tools_config(
        include_path_updates: Annotated[
            bool,
            Field(
                description=(
                    'When true, include summary_view.path_updates.prepend entries for local shell '
                    'PATH setup; when false, omit PATH guidance for a compact response.'
                )
            ),
        ] = True,
    ) -> dict:
        """Return compact local Ladybug Tools SDK runtime configuration."""
        from garden.ladybug_tools_config import get_ladybug_tools_config as service

        result = service()
        if not include_path_updates:
            result["summary_view"].pop("path_updates", None)
        return result
