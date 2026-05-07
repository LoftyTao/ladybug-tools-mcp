"""Search Radiance visualization/image artifacts alias MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.tools.radiance.list_radiance_artifact_files import (
    _normalize_artifact_type,
)
from garden.store import list_garden_artifacts as service


def register(mcp: FastMCP) -> None:
    """Register the search_radiance_visualizations alias tool."""

    @mcp.tool(
        name="search_radiance_visualizations",
        description="Search Garden-managed Radiance image/visualization artifacts such as HDR falsecolor images and GIF previews. For raw run HDR outputs, prefer list_radiance_hdr_images with a run target or run_id.",
        tags={
            "honeybee-radiance",
            "radiance",
            "visualization",
            "image",
            "artifact",
            "search",
            "read-only",
            "safe",
            "alias",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_radiance_visualizations(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        object_type: Annotated[
            str | None,
            Field(description="Optional artifact hint such as hdr_image, falsecolor, gif, view, or sensor_grid."),
        ] = None,
        artifact_type: Annotated[str | None, Field(description="Alias for object_type.")] = None,
        query: Annotated[str | None, Field(description="Optional name/path substring filter.")] = None,
        identifier: Annotated[
            str | None,
            Field(description="Alias for query accepted for Agent compatibility."),
        ] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """Search Radiance visualization artifacts."""
        if artifact_type is None:
            artifact_type = object_type
        normalized_artifact_type = _normalize_artifact_type(artifact_type)
        if query is None and identifier is not None:
            query = identifier
        result = service(garden_root=garden_root, artifact_type=normalized_artifact_type)
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
        result["summary_view"]["artifact_type"] = normalized_artifact_type
        result["summary_view"]["artifact_type_hint"] = artifact_type
        result["summary_view"]["query"] = query
        result["summary_view"]["count"] = len(matches)
        if len(matches) == 1:
            result["artifact"] = matches[0]
        return result
