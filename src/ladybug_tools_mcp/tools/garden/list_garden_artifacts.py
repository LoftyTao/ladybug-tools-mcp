"""List Garden Artifacts MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.store import list_garden_artifacts as service


def register(mcp: FastMCP) -> None:
    """Register the list_garden_artifacts tool."""

    @mcp.tool(
        name="list_garden_artifacts",
        description="List visualization, report, validation, export, and run artifacts recorded in a Garden.",
        tags={"garden", "garden-mode", "artifact", "read", "safe"},
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def list_garden_artifacts(
        garden_root: Annotated[
            str, Field(description="Garden root directory containing garden.json.")
        ],
        artifact_type: Annotated[
            str | None, Field(description="Optional artifact type filter.")
        ] = None,
    ) -> dict[str, Any]:
        """List Garden artifacts."""
        return service(garden_root=garden_root, artifact_type=artifact_type)
