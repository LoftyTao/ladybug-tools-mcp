"""List Radiance grid result folders MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.visual import list_radiance_grid_results as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_list_grid_results tool.'

    @mcp.tool(
        name="list_grid_results",
        description=(
            "List SensorGrid result folders from a completed Radiance run "
            "using SDK folder conventions: folders with grids_info.json and "
            "result files such as .res or .ill. Use before "
            "radiance_grid_result_to_visualization_set. This lists result "
            "folders and metadata; it does not create VisualizationSets, "
            "export HTML/SVG, or read full result arrays."
        ),
        tags={
            "artifact",
            "radiance",
            "sensor-grid",
            "result",
            "visualize",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_grid_results(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional completed radiance_run target from a grid or matrix recipe. Poll the run before listing result folders."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier for a completed grid or matrix run when run_target is not supplied."),
        ] = None,
    ) -> dict[str, Any]:
        """List Radiance SensorGrid result folders."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
