"""Search Radiance SensorGrid artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import list_garden_artifacts


def _target_from_artifact(artifact: dict[str, Any], garden_target: dict[str, Any]) -> dict[str, Any]:
    path = str(artifact.get("path") or "")
    return {
        "target_type": "radiance_sensor_grid",
        "domain": "honeybee_radiance",
        "garden_id": garden_target.get("garden_id"),
        "identifier": str(artifact.get("name") or Path(path).stem),
        "path": path,
    }


def register(mcp: FastMCP) -> None:
    """Register the search_radiance_sensor_grids tool."""

    @mcp.tool(
        name="search_radiance_sensor_grids",
        description="Search Garden Radiance SensorGrid .pts artifacts and return compact radiance_sensor_grid targets for grid recipe handoff.",
        tags={
            "honeybee-radiance",
            "radiance",
            "sensor-grid",
            "pts",
            "artifact",
            "search",
            "target",
            "garden-mode",
            "read",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_radiance_sensor_grids(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        query: Annotated[str | None, Field(description="Optional identifier or path substring filter.")] = None,
        object_type: Annotated[
            str | None,
            Field(description="Optional object-type hint accepted for Agent compatibility. This tool always searches radiance_sensor_grid artifacts."),
        ] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
        return_object_dict: Annotated[bool | None, Field(description="Ignored compatibility hint.")] = None,
    ) -> dict[str, Any]:
        """Search Radiance SensorGrid artifacts."""
        _ = (object_type, return_object_dict)
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
                "object_type_hint": object_type,
                "artifact_type": "radiance_sensor_grid",
            },
        }
        if len(matches) == 1:
            result["target"] = matches[0]["target"]
        return result
