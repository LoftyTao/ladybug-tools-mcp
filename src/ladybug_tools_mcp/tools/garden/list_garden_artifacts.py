"""List Garden Artifacts MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    'Register the GD_list_artifacts tool.'

    @mcp.tool(
        name='GD_list_artifacts',
        description='List visualization, report, validation, export, weather, Radiance, THERM, UWG, and simulation-run artifacts recorded in a Garden manifest. Pass garden_root from GD_create/GD_get and optional artifact_type to narrow results to one artifact family such as vtkjs, html, epw, sql, err, wea, sky, or therm output when those records exist. Returns matches plus summary_view and report; each match is an artifact_target-style record for follow-up export, inspection, visualization, or result-reading tools.',
        tags={
            "artifact",
            "garden",
            "result",
        },
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def list_garden_artifacts(
        garden_root: Annotated[
            str, Field(description="Required Garden root path containing garden.json, usually GD_create['garden_root'] or GD_get['garden_root'].")
        ],
        artifact_type: Annotated[
            str | None, Field(description="Optional artifact type filter matching artifact records in garden.json, for example vtkjs, html, epw, sql, err, wea, radiance_sky_file, or fairyfly_therm_result when present.")
        ] = None,
    ) -> dict[str, Any]:
        """List Garden artifacts."""
        from garden.store import list_garden_artifacts as service

        return service(garden_root=garden_root, artifact_type=artifact_type)
