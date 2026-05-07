"""Get Honeybee model alias MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import get_base_model as service


def register(mcp: FastMCP) -> None:
    """Register the get_honeybee_model alias tool."""

    @mcp.tool(
        name="get_honeybee_model",
        description="Alias for get_base_model. Read the compact Garden Honeybee base model target and summary without returning full HBJSON.",
        tags={"garden", "honeybee", "model", "base-model", "summary", "target", "read", "safe", "alias"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_honeybee_model(
        garden_root: Annotated[str, Field(description="Exact Garden root path containing garden.json.")],
        model_target: Annotated[dict[str, Any] | None, Field(description="Optional Agent context hint. Ignored; use Garden base model.")] = None,
        return_object_dict: Annotated[bool | None, Field(description="Ignored compatibility hint.")] = None,
    ) -> dict[str, Any]:
        """Return compact Honeybee model target and summary."""
        _ = (model_target, return_object_dict)
        return service(garden_root=garden_root)
