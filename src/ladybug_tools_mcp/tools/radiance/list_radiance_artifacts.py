"""List Radiance Garden artifacts."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.tools.radiance.list_radiance_artifact_files import (
    _normalize_artifact_type,
)
from garden.store import list_garden_artifacts as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_list_artifacts tool.'

    @mcp.tool(
        name="list_artifacts",
        description=(
            "List Garden-managed Radiance artifact records and compact "
            "artifact_paths. Use this to find saved Radiance files without "
            "reading large image, matrix, or grid payloads. This is artifact "
            "inventory only; it does not convert files or run recipes. Returns "
            "matches, artifact_paths, summary_view, and report."
        ),
        tags={
            "artifact",
            "radiance",
            "result",
            "search",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_artifacts(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")],
        artifact_type: Annotated[str | None, Field(description="Optional formal Radiance artifact target_type filter. Omit to list every registered Radiance artifact.")] = None,
        query: Annotated[str | None, Field(description="Optional artifact name or Garden-relative path substring filter.")] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """List Radiance artifacts."""
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
