"""List Garden files alias MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import list_garden_artifacts as service

_FILE_TYPE_ALIASES = {
    "hdr": "radiance_hdr_image",
    "hdr_image": "radiance_hdr_image",
    "gif": "radiance_gif_image",
    "sky": "radiance_sky_file",
    "view": "radiance_view",
}


def register(mcp: FastMCP) -> None:
    """Register the list_garden_files alias tool."""

    @mcp.tool(
        name="list_garden_files",
        description="Alias for list_garden_artifacts. List Garden-managed artifact files from the manifest; does not read file bodies.",
        tags={"garden", "garden-mode", "artifact", "file", "manifest", "list", "read", "safe", "alias"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_garden_files(
        garden_root: Annotated[str, Field(description="Garden root directory containing garden.json.")],
        artifact_type: Annotated[str | None, Field(description="Optional artifact type filter.")] = None,
        file_type: Annotated[
            str | None,
            Field(description="Alias for artifact_type accepted for Agent compatibility."),
        ] = None,
        query: Annotated[str | None, Field(description="Optional path/name substring filter.")] = None,
        path: Annotated[
            str | None,
            Field(description="Alias for query accepted when Agents use list_garden_files as a directory/path filter."),
        ] = None,
    ) -> dict[str, Any]:
        """List Garden artifact files."""
        if artifact_type is None and file_type is not None:
            artifact_type = file_type
        if query is None and path is not None:
            query = path
        if artifact_type is not None:
            artifact_type = _FILE_TYPE_ALIASES.get(
                artifact_type.strip().lower().replace("-", "_").replace(" ", "_"),
                artifact_type,
            )
        result = service(garden_root=garden_root, artifact_type=artifact_type)
        query_text = (query or "").strip().lower()
        if query_text:
            result["matches"] = [
                artifact
                for artifact in result["matches"]
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
            result["summary_view"]["count"] = len(result["matches"])
            result["summary_view"]["query"] = query
        return result
