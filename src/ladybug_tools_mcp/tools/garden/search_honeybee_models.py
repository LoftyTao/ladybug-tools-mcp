"""Search Honeybee model targets in a Garden."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.store import list_garden_models as service


def _identifier(model: dict[str, Any]) -> str:
    return str(model.get("model_identifier") or model.get("identifier") or "")


def register(mcp: FastMCP) -> None:
    """Register the search_honeybee_models alias tool."""

    @mcp.tool(
        name="search_honeybee_models",
        description="Search registered Honeybee model targets in a Garden. This is a natural-language alias for list_garden_models that returns each reusable model target under matches[i].target.",
        tags={
            "garden",
            "garden-mode",
            "honeybee",
            "model",
            "model-targets",
            "search",
            "read-only",
            "safe",
            "alias",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def search_honeybee_models(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        query: Annotated[
            str | None,
            Field(description="Optional model identifier or path substring filter."),
        ] = None,
        include_paths: Annotated[
            bool,
            Field(description="Whether to include Garden-relative model file paths."),
        ] = True,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """Search Garden model targets."""
        result = service(garden_root=garden_root, include_paths=include_paths)
        query_text = (query or "").strip().lower()
        matches: list[dict[str, Any]] = []
        for model in result["matches"]:
            haystack = " ".join(
                str(value)
                for value in (
                    model.get("model_identifier"),
                    model.get("identifier"),
                    model.get("path"),
                    model.get("domain"),
                )
                if value
            ).lower()
            if query_text and query_text not in haystack:
                continue
            matches.append(
                {
                    "identifier": _identifier(model),
                    "model_identifier": model.get("model_identifier"),
                    "path": model.get("path"),
                    "target": model,
                }
            )
        if limit is not None:
            matches = matches[:limit]
        result["matches"] = matches
        result["summary_view"]["count"] = len(matches)
        result["summary_view"]["query"] = query
        if len(matches) == 1:
            result["target"] = matches[0]["target"]
            result["model_target"] = matches[0]["target"]
        return result
