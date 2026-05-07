"""Search Radiance WEA file artifacts alias MCP tool."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import list_garden_artifacts


def _target_from_artifact(artifact: dict[str, Any], garden_target: dict[str, Any]) -> dict[str, Any]:
    path = str(artifact.get("path") or "")
    return {
        "target_type": "wea_file",
        "domain": "honeybee_radiance",
        "garden_id": garden_target.get("garden_id"),
        "identifier": str(artifact.get("name") or Path(path).stem),
        "path": path,
    }


def register(mcp: FastMCP) -> None:
    """Register the search_wea_files alias tool."""

    @mcp.tool(
        name="search_wea_files",
        description="Search Garden Radiance WEA file artifacts and return compact wea_file targets.",
        tags={
            "honeybee-radiance",
            "radiance",
            "wea",
            "weather",
            "artifact",
            "search",
            "read-only",
            "safe",
            "alias",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_wea_files(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        query: Annotated[str | None, Field(description="Optional identifier or path substring filter.")] = None,
        identifier: Annotated[
            str | None,
            Field(description="Alias for query accepted for Agent compatibility."),
        ] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """Search Radiance WEA file artifacts."""
        if query is None and identifier is not None:
            query = identifier
        listed = list_garden_artifacts(garden_root=garden_root, artifact_type="wea_file")
        garden_target = listed["summary_view"]["garden_target"]
        query_text = (query or "").strip().lower()
        matches: list[dict[str, Any]] = []
        for artifact in listed["matches"]:
            searchable = " ".join(
                str(value)
                for value in (
                    artifact.get("name"),
                    artifact.get("path"),
                    artifact.get("artifact_type"),
                )
                if value
            ).lower()
            if query_text and query_text not in searchable:
                continue
            target = _target_from_artifact(artifact, garden_target)
            matches.append({"artifact": artifact, "target": target, **target})
            if limit is not None and len(matches) >= limit:
                break
        result: dict[str, Any] = {
            "matches": matches,
            "summary_view": {
                "garden_target": garden_target,
                "count": len(matches),
                "query": query,
                "artifact_type": "wea_file",
            },
        }
        if len(matches) == 1:
            result["target"] = matches[0]["target"]
        return result
