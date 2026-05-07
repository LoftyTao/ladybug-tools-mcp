"""Get Flowerpot MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from flowerpot.registry import get_flowerpot as service


def register(mcp: FastMCP) -> None:
    """Register the get_flowerpot tool."""

    @mcp.tool(
        name="get_flowerpot",
        description="Get a registered Garden-local Flowerpot, list registered Flowerpots for a Garden, or summarize a passed opaque Flowerpot. This is a read-only context tool, not an unpack payload tool; it returns target and summary by default and does not return full model bodies. Use garden_root alone to list registered Flowerpots. Do not pass arguments null.",
        tags={
            "flowerpot",
            "garden-mode",
            "platform-handoff",
            "registered-container",
            "grasshopper",
            "get",
            "list",
            "read",
            "read-only",
            "safe",
        },
        timeout=20,
        annotations={"readOnlyHint": True},
    )
    def get_flowerpot(
        garden_root: Annotated[
            str | None,
            Field(
                description="Optional exact Garden root path string. Required when reading by flowerpot_id or listing registered Flowerpots."
            ),
        ] = None,
        flowerpot_id: Annotated[
            str | None,
            Field(
                description="Optional registered Flowerpot id returned by create_flowerpot. Omit with garden_root to list registered Flowerpots."
            ),
        ] = None,
        flowerpot: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional opaque Flowerpot dict to summarize. Pass the whole Flowerpot unchanged; do not unpack internal fields manually."
            ),
        ] = None,
        include_body: Annotated[
            bool,
            Field(
                description="Whether to request full entity body. Defaults false; first batch returns only target/summary and warns when true."
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Get, list, or summarize Flowerpot context."""
        return service(
            garden_root=garden_root,
            flowerpot_id=flowerpot_id,
            flowerpot=flowerpot,
            include_body=include_body,
        )
