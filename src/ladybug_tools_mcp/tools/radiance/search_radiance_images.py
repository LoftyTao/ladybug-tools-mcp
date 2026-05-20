"""Search Radiance image artifacts and run HDR outputs."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.visual import list_radiance_hdr_images
from garden.store import list_garden_artifacts
from ladybug_tools_mcp.tools.radiance.list_radiance_artifact_files import (
    _normalize_artifact_type,
)


def _run_id_from_target(value: Any) -> str | None:
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
            return _run_id_from_target(target)
    return None


def register(mcp: FastMCP) -> None:
    """Register the search_radiance_images tool."""

    @mcp.tool(
        name="search_radiance_images",
        description="Search Radiance image outputs. Returns raw HDR images from completed point-in-time view runs plus Garden-managed image artifacts such as falsecolor HDRs and GIFs.",
        tags={
            "honeybee-radiance",
            "radiance",
            "image",
            "hdr",
            "gif",
            "search",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_radiance_images(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        run_id: Annotated[str | None, Field(description="Optional Radiance view run identifier.")] = None,
        run_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional radiance_run target used to identify a view run."),
        ] = None,
        file_type: Annotated[
            str | None,
            Field(description="Optional formal image artifact type such as radiance_hdr_image or radiance_gif_image."),
        ] = None,
        query: Annotated[str | None, Field(description="Optional name/path substring filter.")] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """Search Radiance images."""
        if run_id is None:
            run_id = _run_id_from_target(run_target)
        query_text = (query or "").strip().lower()
        matches: list[dict[str, Any]] = []

        normalized_artifact_type = _normalize_artifact_type(file_type)
        if normalized_artifact_type in {None, "radiance_hdr_image"}:
            try:
                hdrs = list_radiance_hdr_images(garden_root=garden_root, run_id=run_id)
            except Exception:
                hdrs = {"matches": []}
            for image in hdrs.get("matches", []):
                searchable = " ".join(str(value) for value in image.values() if value).lower()
                if query_text and query_text not in searchable:
                    continue
                matches.append(
                    {
                        "kind": "run_hdr",
                        "image_type": "hdr",
                        "path": image.get("path"),
                        "name": image.get("name"),
                        "run_id": image.get("run_id"),
                        "image": image,
                    }
                )

        listed = list_garden_artifacts(
            garden_root=garden_root,
            artifact_type=normalized_artifact_type,
        )
        for artifact in listed.get("matches", []):
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
            matches.append(
                {
                    "kind": "artifact",
                    "image_type": artifact.get("artifact_type"),
                    "path": artifact.get("path"),
                    "name": artifact.get("name"),
                    "artifact": artifact,
                }
            )
        if limit is not None:
            matches = matches[:limit]
        hdr_images = [item for item in matches if item.get("image_type") == "hdr"]
        return {
            "matches": matches,
            "images": matches,
            "hdr_images": hdr_images,
            "summary_view": {
                "garden_target": listed.get("summary_view", {}).get("garden_target"),
                "count": len(matches),
                "query": query,
                "file_type": file_type,
                "recommended_hdr_tool": "list_radiance_hdr_images",
            },
        }
