"""Get Dragonfly Model Summary MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.summary import get_dragonfly_model_summary as service


def register(mcp: FastMCP) -> None:
    """Register the get_dragonfly_model_summary tool."""

    @mcp.tool(
        name="get_dragonfly_model_summary",
        description="Return compact counts and metadata for the Garden base Dragonfly model or an explicit Dragonfly model target. This does not return the full DFJSON body.",
        tags={
            "dragonfly-core",
            "garden-mode",
            "model",
            "summary",
            "read",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_dragonfly_model_summary(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Dragonfly model target dict. Defaults to the Garden base Dragonfly model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Get compact Dragonfly model counts and metadata."""
        return service(garden_root=garden_root, model_target=model_target)
