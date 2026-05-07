"""Generic Garden object search alias MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import list_garden_artifacts
from garden.radiance.run import list_radiance_runs, list_radiance_run_outputs
from garden.radiance.visual import list_radiance_hdr_images


_OBJECT_TYPE_ALIASES = {
    "hdr": "radiance_hdr_image",
    "hdr_image": "radiance_hdr_image",
    "hdr_images": "radiance_hdr_image",
    "radiance_hdr": "radiance_hdr_image",
    "radiance_image": "radiance_hdr_image",
    "image": "image",
    "images": "image",
    "radiance_output": "radiance_output",
    "radiance_outputs": "radiance_output",
    "radiance_result": "radiance_output",
    "radiance_results": "radiance_output",
    "radiance_run": "radiance_run",
    "radiance_runs": "radiance_run",
    "sky": "radiance_sky_file",
    "radiance_sky": "radiance_sky_file",
}


def _normalize_object_type(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    return _OBJECT_TYPE_ALIASES.get(normalized, normalized or None)


def _query_filter(
    matches: list[dict[str, Any]],
    query: str | None,
    *,
    limit: int | None,
) -> list[dict[str, Any]]:
    query_text = (query or "").strip().lower()
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
                    artifact.get("run_id"),
                    artifact.get("recipe"),
                    artifact.get("status"),
                )
                if value
            ).lower()
        ]
    if limit is not None:
        matches = matches[:limit]
    return matches


def _radiance_run_matches(garden_root: str, status: str | None) -> list[dict[str, Any]]:
    return list(list_radiance_runs(garden_root=garden_root, status=status).get("matches", []))


def _radiance_output_matches(garden_root: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for run in _radiance_run_matches(garden_root, None):
        run_id = run.get("run_id") or run.get("target", {}).get("run_id")
        if not run_id:
            continue
        try:
            outputs = list_radiance_run_outputs(garden_root=garden_root, run_id=str(run_id))
        except Exception:
            continue
        for output in outputs.get("matches", []):
            output = dict(output)
            output.setdefault("run_id", run_id)
            output.setdefault("target", run.get("target"))
            matches.append(output)
    return matches


def _radiance_image_matches(garden_root: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for run in _radiance_run_matches(garden_root, "completed"):
        run_id = run.get("run_id") or run.get("target", {}).get("run_id")
        if not run_id:
            continue
        try:
            hdrs = list_radiance_hdr_images(garden_root=garden_root, run_id=str(run_id))
        except Exception:
            continue
        matches.extend(hdrs.get("matches", []))
    artifact_images = list_garden_artifacts(garden_root=garden_root, artifact_type=None)
    for artifact in artifact_images.get("matches", []):
        if artifact.get("artifact_type") in {"radiance_hdr_image", "radiance_gif_image"}:
            matches.append(artifact)
    return matches


def register(mcp: FastMCP) -> None:
    """Register the search_garden_objects alias tool."""

    @mcp.tool(
        name="search_garden_objects",
        description="Generic read-only Garden search alias for persisted artifact records. Prefer domain-specific search tools when known.",
        tags={"garden", "garden-mode", "search", "artifact", "read-only", "safe", "alias"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_garden_objects(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        object_type: Annotated[str | None, Field(description="Optional artifact/object type filter.")] = None,
        artifact_type: Annotated[str | None, Field(description="Alias for object_type.")] = None,
        query: Annotated[str | None, Field(description="Optional name/path substring filter.")] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """Search Garden artifact records."""
        if artifact_type is None:
            artifact_type = object_type
        artifact_type = _normalize_object_type(artifact_type)
        if artifact_type == "radiance_run":
            matches = _query_filter(
                _radiance_run_matches(garden_root, None),
                query,
                limit=limit,
            )
            result = {"matches": matches, "summary_view": {}}
        elif artifact_type == "radiance_output":
            matches = _query_filter(_radiance_output_matches(garden_root), query, limit=limit)
            result = {"matches": matches, "summary_view": {}}
        elif artifact_type in {"radiance_hdr_image", "image"}:
            matches = _query_filter(_radiance_image_matches(garden_root), query, limit=limit)
            result = {"matches": matches, "summary_view": {}}
        else:
            result = list_garden_artifacts(garden_root=garden_root, artifact_type=artifact_type)
            matches = _query_filter(list(result.get("matches", [])), query, limit=limit)
        result["matches"] = matches
        result["objects"] = matches
        result["files"] = matches
        if artifact_type in {"radiance_hdr_image", "image"}:
            result["hdr_images"] = [
                item
                for item in matches
                if str(item.get("path", "")).lower().endswith(".hdr")
                or item.get("artifact_type") == "radiance_hdr_image"
            ]
            result["images"] = matches
        if artifact_type == "radiance_output":
            result["outputs"] = matches
        if artifact_type == "radiance_run":
            result["runs"] = matches
        result.setdefault("summary_view", {})
        result["summary_view"]["object_type"] = artifact_type
        result["summary_view"]["count"] = len(matches)
        result["summary_view"]["query"] = query
        return result
