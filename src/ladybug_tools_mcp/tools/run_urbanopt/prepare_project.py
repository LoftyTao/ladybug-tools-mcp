"""Prepare URBANopt Energy project MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_urbanopt.run import prepare_project as service


def register(mcp: FastMCP) -> None:
    """Register the URBANopt project preparation tool."""

    @mcp.tool(
        name="prepare_project",
        description=(
            "Prepare a Garden-managed URBANopt Energy project from a Dragonfly "
            "URBANopt feature GeoJSON artifact. The tool records a project "
            "folder target and scenario CSV target, then returns runtime_status, "
            "summary_view, persistence_receipt, and report. Missing URBANopt is "
            "reported as blocked with config_get_runtime_config as the next check."
        ),
        tags={"dragonfly", "urbanopt", "energy", "project", "artifact", "runtime", "target"},
        timeout=30,
    )
    def prepare_project(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; URBANopt project setup is written inside this Garden.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="Dragonfly URBANopt feature GeoJSON artifact target to prepare for URBANopt Energy simulation.")],
        cpu_count: Annotated[int | None, Field(description="Optional positive CPU count for the URBANopt project preparation step.") ] = None,
        verbose: Annotated[bool, Field(description="Ask the URBANopt project preparation step to emit verbose progress output.") ] = False,
    ) -> dict[str, Any]:
        """Prepare an URBANopt Energy project folder."""
        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            cpu_count=cpu_count,
            verbose=verbose,
        )
