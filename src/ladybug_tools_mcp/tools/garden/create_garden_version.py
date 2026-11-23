"""Create Garden Version MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    'Register the GD_create_version tool.'

    @mcp.tool(
        name='GD_create_version',
        description=(
            'Create a compact Garden version checkpoint tracking garden.json, models, and '
            'libraries. Returns target, version_target, summary_view, and persistence_receipt '
            'metadata without file bodies or diffs.'
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
                    "GD_create['garden_root']; this must be the Garden whose "
                    "authoring truth should receive the version checkpoint."
                )
            ),
        ],
        subject: Annotated[
            str,
            Field(
                description=(
                    "Required short checkpoint subject, for example 'add office windows' or 'feat: "
                    "add office windows'."
                )
            ),
        ],
        summary: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    'Optional compact structured summary for the Garden version.'
                )
            ),
        ] = None,
        details: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    'Optional compact structured details merged into summary.'
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
        from garden.versions import create_garden_version as service

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
