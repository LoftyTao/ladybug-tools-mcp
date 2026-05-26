"""Ladybug Tools SDK runtime configuration MCP tool."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from garden.ladybug_tools_config import get_ladybug_tools_config as service


def register(mcp: FastMCP) -> None:
    'Register the config_get_runtime_config tool.'

    @mcp.tool(
        name="get_runtime_config",
        description=(
            "Diagnose the local Ladybug Tools runtime configuration for Radiance, "
            "OpenStudio, EnergyPlus, URBANopt, THERM, and Ironbug.Console. Use this "
            "read-only tool when an engine command is missing, before a long Agent "
            "test, or when a user asks which simulation runtimes the installed SDK "
            "can currently see. Returns summary_view.engines, summary_view.measures, "
            "missing_engine_guidance, runtime_requirement_guidance, report, and "
            "optional path_updates.prepend values for shell or Agent harness PATH "
            "setup. It does not install engines, create Gardens, run setup-env, or "
            "start simulations."
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
                    "When true, include summary_view.path_updates.prepend entries "
                    "for local shells and Agent test harnesses; when false, omit "
                    "PATH guidance to keep the diagnostic response compact. The "
                    "tool never mutates the current process PATH."
                )
            ),
        ] = True,
    ) -> dict:
        """Return compact local Ladybug Tools SDK runtime configuration."""
        result = service()
        if not include_path_updates:
            result["summary_view"].pop("path_updates", None)
        return result
