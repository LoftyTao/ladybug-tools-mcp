"""List Radiance Garden artifact files MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import list_garden_artifacts as service


_FORMAL_ARTIFACT_TYPES = {
    "radiance_sky_file",
    "radiance_view",
    "radiance_sensor_grid",
    "radiance_hdr_image",
    "radiance_gif_image",
}


def _normalize_artifact_type(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized:
        return None
    if normalized not in _FORMAL_ARTIFACT_TYPES:
        allowed = ", ".join(sorted(_FORMAL_ARTIFACT_TYPES))
        raise ValueError(f"artifact_type must be one of: {allowed}.")
    return normalized


def register(mcp: FastMCP) -> None:
    """Register the list_radiance_artifact_files tool."""

    @mcp.tool(
        name="list_radiance_artifact_files",
        description="List Garden-managed Radiance artifact files such as sky files, views, sensor grids, HDR images, falsecolor images, and GIFs. This reads Garden manifest records and does not read file bodies.",
        tags={
            "honeybee-radiance",
            "radiance",
            "garden-mode",
            "artifact",
            "file",
            "list",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_artifact_files(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        artifact_type: Annotated[str | None, Field(description="Optional formal Radiance artifact type: radiance_sky_file, radiance_view, radiance_sensor_grid, radiance_hdr_image, or radiance_gif_image.")] = None,
        query: Annotated[str | None, Field(description="Optional name/path substring filter.")] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """List Radiance artifact records from the Garden manifest."""
        normalized_artifact_type = _normalize_artifact_type(artifact_type)
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
        result["files"] = matches
        result["summary_view"]["artifact_type"] = normalized_artifact_type
        result["summary_view"]["requested_artifact_type"] = artifact_type
        result["summary_view"]["query"] = query
        result["summary_view"]["count"] = len(matches)
        grouped: dict[str, list[dict[str, Any]]] = {
            "sky_files": [],
            "views": [],
            "sensor_grids": [],
            "hdr_images": [],
            "falsecolor": [],
            "gifs": [],
        }
        for artifact in matches:
            artifact_type_value = artifact.get("artifact_type")
            if artifact_type_value == "radiance_sky_file":
                grouped["sky_files"].append(artifact)
            elif artifact_type_value == "radiance_view":
                grouped["views"].append(artifact)
            elif artifact_type_value == "radiance_sensor_grid":
                grouped["sensor_grids"].append(artifact)
            elif artifact_type_value == "radiance_hdr_image":
                grouped["hdr_images"].append(artifact)
                producer = artifact.get("source", {}).get("producer") if isinstance(artifact.get("source"), dict) else None
                if producer == "radiance_hdr_to_falsecolor":
                    grouped["falsecolor"].append(artifact)
            elif artifact_type_value == "radiance_gif_image":
                grouped["gifs"].append(artifact)
        result.update(grouped)
        if len(matches) == 1:
            result["artifact"] = matches[0]
        return result
