"""Natural-language alias for Radiance sky artifact search."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from garden.store import list_garden_artifacts


def register(mcp: FastMCP) -> None:
    """Register search_radiance_sky as an alias."""

    @mcp.tool(
        name="search_radiance_sky",
        description="Alias for searching Garden-managed Radiance sky files. Prefer search_radiance_sky_files in planned calls.",
        tags={
            "honeybee-radiance",
            "radiance",
            "sky",
            "search",
            "read-only",
            "safe",
            "alias",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_radiance_sky(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        query: Annotated[str | None, Field(description="Optional name/path substring filter.")] = None,
        identifier: Annotated[
            str | None,
            Field(description="Alias for query accepted for Agent compatibility."),
        ] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict:
        """Search Radiance sky artifacts."""
        if query is None and identifier is not None:
            query = identifier
        query_text = (query or "").strip().lower()
        result = list_garden_artifacts(garden_root=garden_root, artifact_type="radiance_sky_file")
        matches = list(result.get("matches", []))
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
        result["sky_files"] = matches
        result["summary_view"]["count"] = len(matches)
        result["summary_view"]["query"] = query
        return result
