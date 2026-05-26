"""Create Garden Version MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.versions import create_garden_version as service


def register(mcp: FastMCP) -> None:
    'Register the garden_create_version tool.'

    @mcp.tool(
        name='create_version',
        description=(
            "Create a compact Garden version checkpoint after a user or Agent "
            "workflow changes Garden authoring truth. Use once at the end of a "
            "modeling, edit, or library workflow, before the user may need undo, "
            "rollback, or restore history. The checkpoint tracks only garden.json, "
            "models, and libraries. Returns target, version_target, summary_view, "
            "and persistence_receipt metadata only; never returns Git diff, patch "
            "text, HBJSON bodies, DFJSON bodies, or full file contents."
        ),
        tags={
            "checkpoint",
            "garden",
            "history",
            "version",
        },
        timeout=20,
    )
    def create_garden_version(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "garden_create['garden_root']; this must be the Garden whose "
                    "authoring truth should receive the version checkpoint."
                )
            ),
        ],
        subject: Annotated[
            str,
            Field(
                description=(
                    "Required short checkpoint subject, for example "
                    "'add office windows' or 'feat: add office windows'. This is "
                    "metadata for the Garden version record, not a model body."
                )
            ),
        ],
        summary: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional compact structured summary for the Garden version. "
                    "Do not include full HBJSON/DFJSON model bodies, exported "
                    "file text, diffs, or patches."
                )
            ),
        ] = None,
        details: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional compact structured details. Merged into summary when "
                    "summary is structured; never include full file bodies, model "
                    "snapshots, diffs, or patches."
                )
            ),
        ] = None,
        source: Annotated[
            str | None,
            Field(
                description=(
                    "Optional source label for the Garden history record, such as "
                    "agent, user, grasshopper, manual, or test."
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
