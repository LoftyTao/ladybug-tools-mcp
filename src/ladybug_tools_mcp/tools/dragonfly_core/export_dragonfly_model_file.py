"""Export Dragonfly model file MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.model_files import export_dragonfly_model_file as service


def register(mcp: FastMCP) -> None:
    """Register the dragonfly_export_model_file tool."""

    @mcp.tool(
        name="export_model_file",
        description=(
            "Export a Garden Dragonfly model to a compact Garden file artifact "
            "as DFJSON or geoJSON. This is the MCP artifact/target form of "
            "Grasshopper Dump Objects and Model To geoJSON; the file body is "
            "not returned unless include_body is true."
        ),
        tags={"dragonfly", "dfjson", "geojson", "export", "artifact", "garden"},
        timeout=60,
    )
    def export_dragonfly_model_file(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        file_type: Annotated[
            str,
            Field(description="File type to export: dfjson or geojson."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target; defaults to base_dragonfly_model."),
        ] = None,
        artifact_name: Annotated[
            str | None,
            Field(description="Optional Garden artifact file stem."),
        ] = None,
        include_body: Annotated[
            bool,
            Field(description="Whether to return the exported file body; false keeps response compact."),
        ] = False,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Required geoJSON location dict when file_type is geojson."),
        ] = None,
        point: Annotated[
            list[float] | None,
            Field(description="Required geoJSON origin point as [x, y] when file_type is geojson."),
        ] = None,
        tolerance: Annotated[
            float | None,
            Field(description="Optional Dragonfly geoJSON export tolerance."),
        ] = None,
    ) -> dict[str, Any]:
        """Export a Dragonfly model file."""
        return service(
            garden_root=garden_root,
            model_target=model_target,
            file_type=file_type,
            artifact_name=artifact_name,
            include_body=include_body,
            location=location,
            point=point,
            tolerance=tolerance,
        )
