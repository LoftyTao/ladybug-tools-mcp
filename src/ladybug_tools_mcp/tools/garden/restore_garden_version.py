"""Restore Garden Version MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.versions import restore_garden_version as service


def register(mcp: FastMCP) -> None:
    """Register the restore_garden_version tool."""

    @mcp.tool(
        name="restore_garden_version",
        description=(
            "Safely restore, undo, go back, roll back, or return Garden authoring "
            "truth to a previous version/checkpoint and record the restore as a "
            "new version. This is the GUI-like undo path. Pass either the "
            "version_id string from list_garden_versions matches/versions or a "
            "garden version target as version_target. It refuses dirty authoring "
            "truth, never rewrites Git history, and never returns diffs, patches, "
            "HBJSON bodies, or full file contents."
        ),
        tags={
            "garden",
            "garden-mode",
            "version",
            "history",
            "checkpoint",
            "undo",
            "restore",
            "rollback",
            "write",
            "safe",
        },
        timeout=30,
    )
    def restore_garden_version(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        version_id: Annotated[
            str | None,
            Field(
                description=(
                    "Garden version id string from list_garden_versions "
                    "matches/versions. Required unless version_target is provided."
                )
            ),
        ] = None,
        version_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional garden_version target from list_garden_versions. "
                    "Use when the version record target is easier to pass than "
                    "the version_id string."
                )
            ),
        ] = None,
        subject: Annotated[
            str | None,
            Field(
                description=(
                    "Optional restore commit subject. Defaults to "
                    "restore: garden version <short id>."
                )
            ),
        ] = None,
        summary: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional compact restore summary. Do not include full model "
                    "bodies or diffs."
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
        """Restore a Garden version as a new history entry."""
        resolved_version_id = version_id
        if resolved_version_id is None and version_target:
            raw_id = version_target.get("version_id")
            resolved_version_id = str(raw_id) if raw_id else None
        if not resolved_version_id:
            raise ValueError("version_id or version_target is required.")
        return service(
            garden_root=garden_root,
            version_id=resolved_version_id,
            subject=subject,
            summary=summary,
            source=source,
        )
