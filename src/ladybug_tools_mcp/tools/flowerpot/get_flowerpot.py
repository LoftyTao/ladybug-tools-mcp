"""Get Flowerpot MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from flowerpot.registry import get_flowerpot as service


def register(mcp: FastMCP) -> None:
    'Register the flowerpot_get tool.'

    @mcp.tool(
        name='get',
        description=(
            "Read, list, or summarize Garden-local Flowerpot handoff context while "
            "keeping Flowerpot dictionaries opaque. Use garden_root alone to list "
            "registered Flowerpots, garden_root plus flowerpot_id to read one "
            "registered item, or flowerpot to summarize a passed handoff dict. "
            "Returns flowerpot, target, matches, summary_view, and report. It does "
            "not unpack payload internals or return full Honeybee/Dragonfly model "
            "bodies; include_body currently only adds a warning. Do not pass "
            "arguments null."
        ),
        tags={
            "context",
            "flowerpot",
            "handoff",
            "target",
        },
        timeout=20,
        annotations={"readOnlyHint": True},
    )
    def get_flowerpot(
        garden_root: Annotated[
            str | None,
            Field(
                description="Optional Garden root path containing garden.json, usually garden_create['garden_root']; required when using flowerpot_id or listing registered Flowerpots."
            ),
        ] = None,
        flowerpot_id: Annotated[
            str | None,
            Field(
                description='Optional registered Flowerpot id returned by flowerpot_create. Omit with garden_root to list registered Flowerpots.'
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
                description=(
                    "Requesting full body is not supported in the current "
                    "Flowerpot contract. Leave false for target/summary handoff; "
                    "true returns the same lightweight context with a warning."
                )
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
