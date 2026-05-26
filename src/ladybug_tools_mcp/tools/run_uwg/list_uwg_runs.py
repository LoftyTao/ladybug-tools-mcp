"""List UWG runs MCP tool."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from garden.run_uwg.run import list_uwg_runs as service


def register(mcp: FastMCP) -> None:
    'Register the uwg_list_runs tool.'

    @mcp.tool(
        name="list_runs",
        description=(
            "List UWG Alternative Weather runs recorded in a Garden ledger. Use this "
            "to find run_id or run_target before polling or reading outputs. Returns "
            "matches, summary_view, and report; it does not inspect morphed EPW file "
            "contents."
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
    def list_uwg_runs(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")],
        status: Annotated[
            str | None,
            Field(description="Optional runtime_status filter for Garden UWG run ledger records, such as running, completed, failed, or cancelled."),
        ] = None,
    ) -> dict:
        """List UWG runs."""
        return service(garden_root=garden_root, status=status)
