"""List Radiance runs MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.run import list_radiance_runs as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_list_runs tool.'

    @mcp.tool(
        name="list_runs",
        description=(
            "List Radiance simulation runs recorded in a Garden run ledger. "
            "Use this to find run_id, run_target, status, or run folder "
            "metadata before polling or reading results. This reads the run "
            "ledger only; it does not open grid, HDR, matrix, or report "
            "artifacts. Returns matches, summary_view, and report."
        ),
        tags={
            "ledger",
            "radiance",
            "simulate",
            "poll",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_runs(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")],
        status: Annotated[
            str | None,
            Field(description="Optional runtime_status filter for Garden run ledger records, such as running, completed, failed, or cancelled."),
        ] = None,
    ) -> dict[str, Any]:
        """List Radiance simulation runs."""
        return service(garden_root=garden_root, status=status)
