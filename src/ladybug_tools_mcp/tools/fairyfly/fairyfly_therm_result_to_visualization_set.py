"""Create VisualizationSet from Fairyfly THERM result MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.display import fairyfly_therm_result_to_visualization_set as service


def register(mcp: FastMCP) -> None:
    'Register the therm_result_to_visualization_set tool.'

    @mcp.tool(
        name="result_to_visualization_set",
        description=(
            "Create a Ladybug Display VisualizationSet from Fairyfly THERM "
            "temperature or heat-flux results. Poll therm_poll_simulation before "
            "visualizing results from a run_target. If the THMZ has no result "
            "arrays, returns no_results instead of creating an empty view. "
            "Returns visualization_set_target when saved and does not start THERM."
        ),
        tags={"fairyfly", "therm", "visualization-set", "result", "visualize", "preview"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def fairyfly_therm_result_to_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        thmz_target: Annotated[
            dict[str, Any] | None,
            Field(description='Optional fairyfly_thmz target returned by therm_write_model_to_thmz.'),
        ] = None,
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='Optional completed fairyfly_therm_run target returned by therm_start_simulation. Poll before visualizing results.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when thmz_target/run_target are omitted."),
        ] = None,
        data_type: Annotated[
            str,
            Field(description="Result data type to visualize: temperature or heat_flux."),
        ] = "temperature",
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet identifier/name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(
                description="Whether to return the VisualizationSet body. Set false to save a Garden VisualizationSet target."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a VisualizationSet from a Fairyfly THERM result."""
        return service(
            garden_root=garden_root,
            thmz_target=thmz_target,
            run_target=run_target,
            run_id=run_id,
            data_type=data_type,
            name=name,
            return_visualization_set=return_visualization_set,
        )
