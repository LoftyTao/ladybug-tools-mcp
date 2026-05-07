"""Search Radiance run results alias MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.run import list_radiance_runs, list_radiance_run_outputs
from garden.radiance.visual import list_radiance_hdr_images


def register(mcp: FastMCP) -> None:
    """Register the search_radiance_results alias tool."""

    @mcp.tool(
        name="search_radiance_results",
        description="Search Radiance run records and compact outputs in a Garden. For view runs this also tries to include HDR image matches.",
        tags={
            "honeybee-radiance",
            "radiance",
            "results",
            "run",
            "search",
            "read-only",
            "safe",
            "alias",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_radiance_results(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional radiance_run target accepted for Agent compatibility."),
        ] = None,
        run_id: Annotated[str | None, Field(description="Optional run identifier.")] = None,
        query: Annotated[str | None, Field(description="Optional run/output substring filter.")] = None,
        recipe: Annotated[
            str | None,
            Field(description="Optional recipe filter/hint accepted for Agent compatibility."),
        ] = None,
        status: Annotated[str | None, Field(description="Optional run status filter.")] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of run matches.")] = None,
    ) -> dict[str, Any]:
        """Search Radiance run results."""
        if run_id is None and run_target is not None:
            run_id = str(run_target.get("run_id") or "") or None
        query_text = (query or run_id or "").strip().lower()
        if run_id:
            runs = {"matches": []}
            try:
                outputs = list_radiance_run_outputs(garden_root=garden_root, run_id=run_id)
                run_match = {
                    "run_id": run_id,
                    "outputs": outputs.get("matches", []),
                    "target": {"target_type": "radiance_run", "run_id": run_id},
                }
                runs["matches"] = [run_match]
            except Exception:
                runs["matches"] = []
        else:
            runs = list_radiance_runs(garden_root=garden_root, status=status)
        matches = list(runs.get("matches", []))
        if query_text:
            matches = [
                match
                for match in matches
                if query_text
                in " ".join(str(value) for value in match.values() if value).lower()
            ]
        if recipe:
            recipe_text = recipe.strip().lower().replace("_", "-")
            matches = [
                match
                for match in matches
                if not match.get("recipe")
                or recipe_text in str(match.get("recipe")).lower().replace("_", "-")
            ]
        if limit is not None:
            matches = matches[:limit]
        hdr_images: list[dict[str, Any]] = []
        for match in matches:
            matched_run_id = match.get("run_id") or match.get("target", {}).get("run_id")
            if not matched_run_id:
                continue
            try:
                hdr_images.extend(
                    list_radiance_hdr_images(
                        garden_root=garden_root,
                        run_id=str(matched_run_id),
                    ).get("matches", [])
                )
            except Exception:
                pass
        return {
            "matches": matches,
            "results": matches,
            "hdr_images": hdr_images,
            "images": hdr_images,
            "summary_view": {
                "count": len(matches),
                "hdr_count": len(hdr_images),
                "query": query,
                "run_id": run_id,
                "status": status or "all",
            },
        }
