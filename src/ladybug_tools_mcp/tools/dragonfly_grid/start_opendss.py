"""Start Dragonfly Electric Grid OpenDSS MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_grid.runs import start_opendss as service


def register(mcp: FastMCP) -> None:
    """Register the Grid OpenDSS start tool."""

    @mcp.tool(
        name="start_opendss",
        description=(
            "Start or block an OpenDSS run from a feature GeoJSON target and "
            "scenario CSV target. Missing OpenDSS returns a blocked run ledger "
            "instead of pretending simulation completed."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "run", "runtime", "target"},
        timeout=30,
    )
    def start_opendss(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the run ledger is written inside this Garden.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="Feature GeoJSON artifact target for the OpenDSS project.")],
        scenario_csv_target: Annotated[dict[str, Any], Field(description="Scenario CSV artifact target paired with the feature GeoJSON.")],
        run_id: Annotated[str | None, Field(description="Optional stable run id; omit to let the Garden create one.")] = None,
        autosize: Annotated[bool, Field(description="Whether to request OpenDSS network upgrade/autosizing when runtime is ready.")] = False,
    ) -> dict[str, Any]:
        """Start or block an OpenDSS run."""
        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            run_id=run_id,
            autosize=autosize,
        )
