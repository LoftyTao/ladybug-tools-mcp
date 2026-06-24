"""Prepare Dragonfly DES URBANopt project MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_des.runs import prepare_urbanopt_project as service


def register(mcp: FastMCP) -> None:
    """Register the URBANopt project preparation tool."""

    @mcp.tool(
        name="prepare_urbanopt_project",
        description=(
            "Create the URBANopt runner setup for a DES feature GeoJSON artifact "
            "that does not yet have a scenario CSV target. The tool records the "
            "scenario CSV as a Garden artifact and reports runtime_status, "
            "summary_view, persistence_receipt, and report. When the URBANopt "
            "runtime is unavailable it returns blocked with config guidance."
        ),
        tags={"dragonfly", "district-energy", "urbanopt", "project", "artifact", "runtime", "target"},
        timeout=30,
    )
    def prepare_urbanopt_project(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; runner setup is written inside this Garden.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="DES feature GeoJSON artifact target to prepare as an URBANopt project.")],
        cpu_count: Annotated[int | None, Field(description="Optional positive CPU count for the URBANopt runner configuration.") ] = None,
        verbose: Annotated[bool, Field(description="Ask the generated runner configuration to emit verbose progress output.") ] = False,
    ) -> dict[str, Any]:
        """Prepare an URBANopt project folder."""
        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            cpu_count=cpu_count,
            verbose=verbose,
        )
