"""Start Dragonfly Electric Grid RNM MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_grid.runs import start_rnm as service


def register(mcp: FastMCP) -> None:
    """Register the Grid RNM start tool."""

    @mcp.tool(
        name="start_rnm",
        description=(
            "Start or block a Dragonfly Electric Grid RNM run from a feature "
            "GeoJSON target and scenario CSV target. Missing runtime returns a "
            "blocked run ledger with config_get_runtime_config as the next check."
        ),
        tags={"dragonfly", "electric-grid", "rnm", "run", "runtime", "target"},
        timeout=30,
    )
    def start_rnm(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the run ledger is written inside this Garden.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="Feature GeoJSON artifact target for the URBANopt/RNM project.")],
        scenario_csv_target: Annotated[dict[str, Any], Field(description="Scenario CSV artifact target paired with the feature GeoJSON.")],
        run_id: Annotated[str | None, Field(description="Optional stable run id; omit to let the Garden create one.")] = None,
        underground_ratio: Annotated[float, Field(description="RNM underground ratio passed to Dragonfly Energy when runtime is ready.")] = 0.9,
        lv_only: Annotated[bool, Field(description="Whether RNM should run low-voltage-only network generation.")] = True,
        nodes_per_building: Annotated[int, Field(description="RNM nodes per building.")] = 1,
    ) -> dict[str, Any]:
        """Start or block an RNM run."""
        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            run_id=run_id,
            underground_ratio=underground_ratio,
            lv_only=lv_only,
            nodes_per_building=nodes_per_building,
        )

