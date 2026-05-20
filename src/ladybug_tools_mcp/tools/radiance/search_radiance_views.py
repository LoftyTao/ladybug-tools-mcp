"""Search Radiance View artifacts MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import list_garden_artifacts


def _target_from_artifact(artifact: dict[str, Any], garden_target: dict[str, Any]) -> dict[str, Any]:
    path = str(artifact.get("path") or "")
    name = artifact.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("radiance_view artifact requires a name.")
    return {
        "target_type": "radiance_view",
        "domain": "honeybee_radiance",
        "garden_id": garden_target.get("garden_id"),
        "identifier": name,
        "path": path,
    }


def register(mcp: FastMCP) -> None:
    """Register the search_radiance_views tool."""

    @mcp.tool(
        name="search_radiance_views",
        description="Search Garden Radiance View artifacts and return compact radiance_view targets for point-in-time view runs.",
        tags={
            "honeybee-radiance",
            "radiance",
            "view",
            "artifact",
            "search",
            "target",
            "garden-mode",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_radiance_views(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        query: Annotated[str | None, Field(description="Optional identifier or path substring filter.")] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """Search Radiance View artifacts."""
        listed = list_garden_artifacts(
            garden_root=garden_root,
            artifact_type="radiance_view",
        )
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
                "artifact_type": "radiance_view",
            },
        }
        if len(matches) == 1:
            result["target"] = matches[0]["target"]
        return result
