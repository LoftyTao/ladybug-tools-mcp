"""Search Radiance runs alias MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.run import list_radiance_runs as service


def register(mcp: FastMCP) -> None:
    """Register the search_radiance_runs alias tool."""

    @mcp.tool(
        name="search_radiance_runs",
        description="Alias for list_radiance_runs. Search Garden radiance_run records for Radiance grid, view, and annual/matrix simulations.",
        tags={
            "honeybee-radiance",
            "radiance",
            "run-radiance",
            "daylight",
            "simulation",
            "run",
            "ledger",
            "search",
            "read-only",
            "safe",
            "alias",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_radiance_runs(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        status: Annotated[
            str | None,
            Field(description="Optional status filter, for example running, completed, or failed."),
        ] = None,
        query: Annotated[
            str | None,
            Field(description="Optional run_id or recipe substring filter."),
        ] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """Search Radiance simulation runs."""
        result = service(garden_root=garden_root, status=status)
        query_text = (query or "").strip().lower()
        matches = list(result["matches"])
        if query_text:
            matches = [
                run
                for run in matches
                if query_text
                in " ".join(
                    str(value)
                    for value in (
                        run.get("run_id"),
                        run.get("recipe"),
                        run.get("calculation_family"),
                        run.get("status"),
                    )
                    if value
                ).lower()
            ]
        if limit is not None:
            matches = matches[:limit]
        result["matches"] = matches
        result["summary_view"]["count"] = len(matches)
        result["summary_view"]["query"] = query
        if len(matches) == 1:
            result["target"] = matches[0].get("target")
        return result
