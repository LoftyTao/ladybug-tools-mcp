"""Start Dragonfly Electric Grid REopt MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_grid.runs import start_reopt as service


def register(mcp: FastMCP) -> None:
    """Register the Grid REopt start tool."""

    @mcp.tool(
        name="start_reopt",
        description=(
            "Start or block a Dragonfly Electric Grid REopt post-processing run "
            "from feature GeoJSON and scenario CSV targets. Missing runtime or "
            "credentials returns a blocked ledger; this tool does not hide REopt "
            "cost/API prerequisites."
        ),
        tags={"dragonfly", "electric-grid", "reopt", "run", "runtime", "target"},
        timeout=30,
    )
    def start_reopt(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the run ledger is written inside this Garden.")],
        feature_geojson_target: Annotated[dict[str, Any], Field(description="Feature GeoJSON artifact target for the REopt project.")],
        scenario_csv_target: Annotated[dict[str, Any], Field(description="Scenario CSV artifact target paired with the feature GeoJSON.")],
        urdb_label: Annotated[str, Field(description="URDB utility rate label passed to Dragonfly Energy REopt when runtime is ready.")],
        run_id: Annotated[str | None, Field(description="Optional stable run id; omit to let the Garden create one.")] = None,
        developer_key: Annotated[str | None, Field(description="Optional REopt developer key; do not expose secrets in reports.")] = None,
    ) -> dict[str, Any]:
        """Start or block a REopt run."""
        return service(
            garden_root=garden_root,
            feature_geojson_target=feature_geojson_target,
            scenario_csv_target=scenario_csv_target,
            urdb_label=urdb_label,
            run_id=run_id,
            developer_key=developer_key,
        )

