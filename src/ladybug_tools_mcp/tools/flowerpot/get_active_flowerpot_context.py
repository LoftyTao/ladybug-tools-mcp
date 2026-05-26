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
    'Register the flowerpot_get_active_context tool.'

    @mcp.tool(
        name="get_active_context",
        description=(
            "Read the Garden-local active Flowerpot context file for prompts about "
            "Grasshopper, current model, active model, 当前模型, or 正在编辑的模型. Use "
            "garden_root for an exact Garden or root_folder to find the most "
            "recent active-context file under a folder of Gardens. Returns exists, "
            "active_context, flowerpot, model_target, summary_view, and report with "
            "sanitized context only. It does not read full HBJSON/DFJSON bodies, "
            "export the model, or fall back to the latest registry entry when no "
            "active-context file exists."
        ),
        tags={
            "context",
            "flowerpot",
            "grasshopper",
            "handoff",
        },
        timeout=20,
        annotations={"readOnlyHint": True},
    )
    def _tool(
        garden_root: Annotated[
            str | None,
            Field(description="Optional Garden root path containing garden.json, usually garden_create['garden_root']."),
        ] = None,
        platform: Annotated[
            str,
            Field(
                description=(
                    "Platform active-context key. Defaults to grasshopper for the "
                    "active Grasshopper model context file."
                )
            ),
        ] = "grasshopper",
        root_folder: Annotated[
            str | None,
            Field(
                description=(
                    "Optional folder containing one or more Gardens. When "
                    "garden_root is unknown, this searches for the most recently "
                    "updated flowerpots/active_context/<platform>.json file and "
                    "derives its Garden root from the file path."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Read active Flowerpot context."""
        return get_active_flowerpot_context(
            garden_root=garden_root,
            platform=platform,
            root_folder=root_folder,
        )
