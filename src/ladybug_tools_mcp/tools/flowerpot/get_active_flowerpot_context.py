"""Get active Flowerpot context MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from flowerpot.active_context import read_active_context, read_latest_active_context


def get_active_flowerpot_context(
    garden_root: str | None = None,
    platform: str = "grasshopper",
    root_folder: str | None = None,
) -> dict[str, Any]:
    """Read the active Garden-local Flowerpot context."""
    if garden_root:
        return read_active_context(garden_root=garden_root, platform=platform)
    if root_folder:
        return read_latest_active_context(root_folder=root_folder, platform=platform)
    raise ValueError("garden_root or root_folder is required.")


def register(mcp: FastMCP) -> None:
    """Register the get_active_flowerpot_context tool."""

    @mcp.tool(
        name="get_active_flowerpot_context",
        description="Read the Garden-local active Flowerpot context for prompts about grasshopper, current model, active Grasshopper model, 当前模型, or 正在编辑的模型. This read-only tool returns lightweight context, Flowerpot, and model target references only; it does not return full HBJSON or full model bodies.",
        tags={
            "flowerpot",
            "grasshopper",
            "current-model",
            "active-context",
            "read",
            "read-only",
            "garden-mode",
        },
        timeout=20,
        annotations={"readOnlyHint": True},
    )
    def _tool(
        garden_root: Annotated[
            str | None,
            Field(description="Optional exact Garden root path string containing garden.json."),
        ] = None,
        platform: Annotated[
            str,
            Field(
                description="Platform active-context key. Defaults to grasshopper for the active Grasshopper model."
            ),
        ] = "grasshopper",
        root_folder: Annotated[
            str | None,
            Field(
                description="Optional folder to search for the most recently updated active Grasshopper context when garden_root is not known."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Read active Flowerpot context."""
        return get_active_flowerpot_context(
            garden_root=garden_root,
            platform=platform,
            root_folder=root_folder,
        )
