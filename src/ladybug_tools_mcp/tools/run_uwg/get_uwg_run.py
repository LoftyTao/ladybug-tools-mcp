"""Get UWG run MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_uwg.run import get_uwg_run as service


def register(mcp: FastMCP) -> None:
    'Register the uwg_poll_simulation tool.'

    @mcp.tool(
        name="poll_simulation",
        description=(
            "Read one Garden UWG Alternative Weather run ledger record by uwg_run target "
            "or run_id. Use after uwg_start_simulation to poll runtime_status and locate "
            "morphed weather outputs. Returns run_target, runtime_status through "
            "summary_view.status, poll_next, and report. Treat a failed runtime_status "
            "as requiring report review before using any weather target."
        ),
        tags={
            "dragonfly",
            "uwg",
            "weather",
            "poll",
            "ledger",
        },
        timeout=20,
    )
    def get_uwg_run(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='UWG run target returned by uwg_start_simulation; pass run_target for polling when available.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional UWG run id when run_target is not passed."),
        ] = None,
    ) -> dict[str, Any]:
        """Read a UWG run."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
