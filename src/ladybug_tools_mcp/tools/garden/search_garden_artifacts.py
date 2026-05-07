"""Search Garden artifacts alias tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import list_garden_artifacts as service


def register(mcp: FastMCP) -> None:
    """Register the search_garden_artifacts alias tool."""

    @mcp.tool(
        name="search_garden_artifacts",
        description="Alias for list_garden_artifacts. Search persisted Garden artifacts by artifact_type and optional name/path query.",
        tags={
            "garden",
            "garden-mode",
            "artifact",
            "search",
            "read-only",
            "safe",
            "alias",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def search_garden_artifacts(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        artifact_type: Annotated[str | None, Field(description="Optional artifact type filter.")] = None,
        object_type: Annotated[
            str | None,
            Field(description="Alias for artifact_type accepted for Agent compatibility."),
        ] = None,
        query: Annotated[str | None, Field(description="Optional name/path substring query.")] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """Search Garden artifact records."""
        if artifact_type is None and object_type is not None:
            artifact_type = object_type
        result = service(garden_root=garden_root, artifact_type=artifact_type)
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
        result["summary_view"]["count"] = len(matches)
        result["summary_view"]["query"] = query
        if len(matches) == 1:
            result["artifact"] = matches[0]
        return result
