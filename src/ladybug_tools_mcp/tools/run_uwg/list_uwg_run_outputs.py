"""List UWG run outputs MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_uwg.run import list_uwg_run_outputs as service


def register(mcp: FastMCP) -> None:
    'Register the uwg_list_run_outputs tool.'

    @mcp.tool(
        name="list_run_outputs",
        description=(
            "List compact output records for one UWG Alternative Weather run. Use this "
            "after uwg_poll_simulation reports a finished runtime_status to find the "
            "morphed EPW weather target for downstream Energy simulation. Returns "
            "matches, summary_view, and report."
        ),
        tags={
            "dragonfly",
            "uwg",
            "weather",
            "result",
            "outputs",
        },
        timeout=20,
    )
    def list_uwg_run_outputs(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='UWG run target returned by uwg_start_simulation; poll the run before listing morphed weather outputs.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional UWG run id when run_target is not passed."),
        ] = None,
    ) -> dict[str, Any]:
        """List UWG run outputs."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
