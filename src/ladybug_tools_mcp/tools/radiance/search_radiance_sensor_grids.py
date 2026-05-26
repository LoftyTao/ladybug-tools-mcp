"""Search Radiance SensorGrid artifacts."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import list_garden_artifacts


def _target_from_artifact(artifact: dict[str, Any], garden_target: dict[str, Any]) -> dict[str, Any]:
    path = str(artifact.get("path") or "")
    name = artifact.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("radiance_sensor_grid artifact requires a name.")
    return {
        "target_type": "radiance_sensor_grid",
        "domain": "honeybee_radiance",
        "garden_id": garden_target.get("garden_id"),
        "identifier": name,
        "path": path,
    }


def register(mcp: FastMCP) -> None:
    'Register the radiance_search_sensor_grids tool.'

    @mcp.tool(
        name="search_sensor_grids",
        description=(
            "Search Garden Radiance SensorGrid .pts artifacts and return "
            "compact radiance_sensor_grid targets for grid recipe handoff. "
            "This searches saved sensor-grid artifacts; it does not create "
            "sensor points, attach grids to models, or read grid results."
        ),
        tags={
            "artifact",
            "radiance",
            "sensor-grid",
            "author",
            "search",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_radiance_sensor_grids(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")],
        query: Annotated[str | None, Field(description="Optional SensorGrid identifier or Garden-relative .pts path substring filter.")] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """Search Radiance SensorGrid artifacts."""
        listed = list_garden_artifacts(
            garden_root=garden_root,
            artifact_type="radiance_sensor_grid",
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
                "artifact_type": "radiance_sensor_grid",
            },
        }
        if len(matches) == 1:
            result["target"] = matches[0]["target"]
        return result
