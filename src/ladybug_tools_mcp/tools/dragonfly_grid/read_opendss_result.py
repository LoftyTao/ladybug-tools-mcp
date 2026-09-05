"""Read Dragonfly Electric Grid OpenDSS result MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the Grid OpenDSS result reader."""

    @mcp.tool(
        name="DF_grid_read_opendss_result",
        description=(
            "Read a registered Dragonfly Grid OpenDSS CSV result artifact into a "
            "compact preview. The result_target must be a Garden artifact with "
            "artifact_type=dragonfly_grid_opendss_result_csv; arbitrary CSV paths "
            "are rejected."
        ),
        tags={"dragonfly", "electric-grid", "opendss", "result", "read", "target"},
        timeout=20,
    )
    def read_opendss_result(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        result_target: Annotated[dict[str, Any], Field(description="Registered OpenDSS CSV result artifact target.")],
        max_rows: Annotated[int, Field(description="Maximum preview rows to return.")] = 25,
    ) -> dict[str, Any]:
        """Read a registered OpenDSS result artifact."""
        from garden.dragonfly_grid.results import read_opendss_result as service

        return service(garden_root=garden_root, result_target=result_target, max_rows=max_rows)

