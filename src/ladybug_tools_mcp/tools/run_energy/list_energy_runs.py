"""List Energy simulation runs MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.annual import list_energy_runs as service


def register(mcp: FastMCP) -> None:
    'Register the energyplus_list_runs tool.'

    @mcp.tool(
        name="list_runs",
        description=(
            "List annual energy-use simulation runs recorded in a Garden run "
            "ledger. Use this to find run_id, run_target, status, or run "
            "folder metadata before polling or reading results. Returns "
            "matches, summary_view, and report; it does not read SQL, ERR, "
            "HTML, or EUI result files."
        ),
        tags={
            "energy",
            "simulate",
            "poll",
            "ledger",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_energy_runs(
        garden_root: Annotated[
            str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")
        ],
        status: Annotated[
            str | None,
            Field(
                description="Optional runtime_status filter for Garden Energy run ledger records, such as running, completed, failed, or cancelled."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """List Energy simulation runs."""
        return service(garden_root=garden_root, status=status)
