"""List Radiance Garden artifact files alias MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import list_garden_artifacts as service


_ARTIFACT_TYPE_ALIASES = {
    "sky": "radiance_sky_file",
    "skies": "radiance_sky_file",
    "sky_file": "radiance_sky_file",
    "sky_files": "radiance_sky_file",
    "radiance_sky": "radiance_sky_file",
    "view": "radiance_view",
    "views": "radiance_view",
    "radiance_view": "radiance_view",
    "sensor_grid": "radiance_sensor_grid",
    "sensor_grids": "radiance_sensor_grid",
    "radiance_sensor_grid": "radiance_sensor_grid",
    "hdr": "radiance_hdr_image",
    "hdr_image": "radiance_hdr_image",
    "hdr_images": "radiance_hdr_image",
    "hdri": "radiance_hdr_image",
    "radiance_hdr": "radiance_hdr_image",
    "radiance_image": "radiance_hdr_image",
    "falsecolor": "radiance_hdr_image",
    "radiance_falsecolor": "radiance_hdr_image",
    "gif": "radiance_gif_image",
    "radiance_gif": "radiance_gif_image",
}


def _normalize_artifact_type(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    return _ARTIFACT_TYPE_ALIASES.get(normalized, normalized or None)


def _query_from_run_target(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("run_id", "identifier", "id"):
            found = value.get(key)
            if found:
                return str(found)
        target = value.get("target")
        if target is not None:
            return _query_from_run_target(target)
    return None


def register(mcp: FastMCP) -> None:
    """Register the list_radiance_artifact_files alias tool."""

    @mcp.tool(
        name="list_radiance_artifact_files",
        description="List Garden-managed Radiance artifact files such as sky files, views, sensor grids, HDR images, falsecolor images, and GIFs. This is an alias over the Garden manifest and does not read file bodies.",
        tags={
            "honeybee-radiance",
            "radiance",
            "garden-mode",
            "artifact",
            "file",
            "list",
            "read-only",
            "safe",
            "alias",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_artifact_files(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        artifact_type: Annotated[str | None, Field(description="Optional Radiance artifact type such as sky, view, sensor_grid, hdr, falsecolor, or gif.")] = None,
        file_type: Annotated[
            str | None,
            Field(description="Alias for artifact_type accepted for Agent compatibility, for example hdr or gif."),
        ] = None,
        object_type: Annotated[
            str | None,
            Field(description="Alias for artifact_type accepted for Agent compatibility."),
        ] = None,
        query: Annotated[str | None, Field(description="Optional name/path substring filter.")] = None,
        run_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional radiance_run target accepted as a search hint for Agent compatibility."),
        ] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """List Radiance artifact records from the Garden manifest."""
        if artifact_type is None and object_type is not None:
            artifact_type = object_type
        if artifact_type is None and file_type is not None:
            artifact_type = file_type
        if query is None and run_target is not None:
            query = _query_from_run_target(run_target)
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
        result["summary_view"]["artifact_type_hint"] = artifact_type
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
