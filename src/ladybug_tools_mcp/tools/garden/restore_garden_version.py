"""Restore Garden Version MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.versions import restore_garden_version as service


def register(mcp: FastMCP) -> None:
    'Register the garden_restore_version tool.'

    @mcp.tool(
        name='restore_version',
        description=(
            "Restore, undo, go back, or roll back Garden authoring truth to a "
            "previous Garden version checkpoint and record that restore as a new "
            "history item. Pass either the version_id from garden_list_versions "
            "matches/versions or the nested garden_version target as version_target. "
            "Returns summary_view, restored_from_version, new_version, version_target, "
            "and persistence_receipt metadata only. It refuses dirty authoring "
            "truth, does not rewrite existing history, and never returns diffs, "
            "patches, HBJSON bodies, DFJSON bodies, or full file contents."
        ),
        tags={
            "checkpoint",
            "garden",
            "history",
            "rollback",
            "restore",
            "version",
        },
        timeout=30,
    )
    def restore_garden_version(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "garden_create['garden_root']; restore only this Garden's "
                    "authoring truth paths."
                )
            ),
        ],
        version_id: Annotated[
            str | None,
            Field(
                description=(
                    "Garden version_id string from garden_list_versions "
                    "matches/versions. Required unless version_target is provided; "
                    "do not pass a raw Git hash from another repository."
                )
            ),
        ] = None,
        version_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional nested garden_version target from garden_list_versions, "
                    "garden_create_version, or garden_restore_version. Expected "
                    "shape includes target_type='garden_version', garden_id, and "
                    "version_id; use this instead of the version_id string when "
                    "passing the target handoff is easier."
                )
            ),
        ] = None,
        subject: Annotated[
            str | None,
            Field(
                description=(
                    "Optional short subject for the new Garden restore history "
                    "record. Defaults to restore: garden version <short id>."
                )
            ),
        ] = None,
        summary: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional compact restore summary. Do not include full "
                    "HBJSON/DFJSON model bodies, exported file text, diffs, or "
                    "patches."
                )
            ),
        ] = None,
        source: Annotated[
            str | None,
            Field(
                description=(
                    "Optional source label for the Garden restore history record, "
                    "such as agent, user, grasshopper, manual, or test."
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
