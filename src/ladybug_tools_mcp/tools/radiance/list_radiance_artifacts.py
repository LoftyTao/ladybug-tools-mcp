"""Alias for listing Radiance Garden artifact files."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.tools.radiance.list_radiance_artifact_files import (
    _normalize_artifact_type,
)
from garden.store import list_garden_artifacts as service


def register(mcp: FastMCP) -> None:
    """Register the list_radiance_artifacts alias tool."""

    @mcp.tool(
        name="list_radiance_artifacts",
        description="Alias for list_radiance_artifact_files. List Garden-managed Radiance artifact records and compact artifact_paths.",
        tags={
            "honeybee-radiance",
            "radiance",
            "garden-mode",
            "artifact",
            "list",
            "read-only",
            "safe",
            "alias",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_artifacts(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        artifact_type: Annotated[str | None, Field(description="Optional Radiance artifact type filter.")] = None,
        object_type: Annotated[
            str | None,
            Field(description="Alias for artifact_type accepted for Agent compatibility."),
        ] = None,
        query: Annotated[str | None, Field(description="Optional name/path substring filter.")] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """List Radiance artifacts."""
        if artifact_type is None and object_type is not None:
            artifact_type = object_type
        result = service(
            garden_root=garden_root,
            artifact_type=_normalize_artifact_type(artifact_type),
        )
        query_text = (query or "").strip().lower()
        matches = list(result["matches"])
        if query_text:
            matches = [
                artifact
                for artifact in matches
                if query_text
                in " ".join(
                    str(value)
                    for value in (
                        artifact.get("name"),
                        artifact.get("path"),
                        artifact.get("artifact_type"),
                    )
                    if value
                ).lower()
            ]
        if limit is not None:
            matches = matches[:limit]
        result["matches"] = matches
        result["artifact_paths"] = [item.get("path") for item in matches if item.get("path")]
        result["summary_view"]["count"] = len(matches)
        result["summary_view"]["query"] = query
        return result
