"""Create Garden Version MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.versions import create_garden_version as service


def register(mcp: FastMCP) -> None:
    """Register the create_garden_version tool."""

    @mcp.tool(
        name="create_garden_version",
        description=(
            "Create and save a compact Git-backed Garden version after an Agent "
            "prompt, user prompt, undo checkpoint, version checkpoint, or history "
            "checkpoint changes Garden authoring truth. Use once at the end of a "
            "modeling/edit/library workflow, not after every low-level write. "
            "Tracks only garden.json, models, and libraries. Returns version "
            "metadata only; never returns Git diff, patch text, HBJSON bodies, "
            "or full file contents."
        ),
        tags={
            "garden",
            "garden-mode",
            "version",
            "history",
            "checkpoint",
            "undo",
            "write",
            "safe",
        },
        timeout=20,
    )
    def create_garden_version(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        subject: Annotated[
            str,
            Field(
                description=(
                    "Required concise version subject, for example "
                    "'feat: add office windows'."
                )
            ),
        ],
        summary: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional compact structured summary. Do not include full model "
                    "bodies or diffs."
                )
            ),
        ] = None,
        details: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional compact structured details. Merged into summary when "
                    "summary is structured; never include full file bodies or diffs."
                )
            ),
        ] = None,
        source: Annotated[
            str | None,
            Field(
                description=(
                    "Optional source label such as agent, user, grasshopper, "
                    "manual, or test."
                )
            ),
        ] = "agent",
    ) -> dict[str, Any]:
        """Create a Garden version."""
        if isinstance(summary, str):
            summary = {"note": summary}
        if details is not None:
            if summary is None:
                summary = {"details": details}
            elif isinstance(summary, dict) and "details" not in summary:
                summary = {**summary, "details": details}
        return service(
            garden_root=garden_root,
            subject=subject,
            summary=summary,
            source=source,
        )
