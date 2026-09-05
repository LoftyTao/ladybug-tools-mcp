"""WindRose statistics and VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the LB_windrose_to_visualization_set tool."""

    @mcp.tool(
        name="LB_windrose_to_visualization_set",
        description=(
            "Create a Ladybug WindRose from aligned hourly wind-direction "
            "and analysis DataCollections, returning compact directional "
            "frequency statistics and a native VisualizationSet. The analysis "
            "collection is usually wind_speed, but other hourly numeric data "
            "can also be binned by direction. Use Garden targets for compact "
            "agent handoff; set return_visualization_set=false to persist a "
            "visualization_set target for LB_set_to_html, LB_set_to_svg, or "
            "LB_set_to_vtkjs. For wind speed, calm_threshold marks values at "
            "or below the threshold as calm and reports their count and "
            "percentage. This tool does not read EPW files; use "
            "EP_read_weather_file_data first. An optional analysis_period "
            "filters both inputs before calculating the rose."
        ),
        tags={
            "ladybug",
            "wind",
            "windrose",
            "weather",
            "visualize",
            "visualization-set",
        },
        timeout=60,
    )
    def windrose_to_visualization_set(
        garden_root: Annotated[
            str,
            Field(
                description="Garden root path containing garden.json, required for Garden DataCollection targets and persisted VisualizationSets."
            ),
        ],
        direction_data_collection: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional direct hourly Ladybug DataCollection dictionary of wind directions in degrees. Provide exactly one direction input with direction_data_collection_target."
            ),
        ] = None,
        direction_data_collection_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Garden ladybug_data_collection target for hourly wind directions. Preferred over a full dictionary."
            ),
        ] = None,
        analysis_data_collection: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional direct hourly Ladybug DataCollection dictionary to bin by direction, usually wind speed. Provide exactly one analysis input with analysis_data_collection_target."
            ),
        ] = None,
        analysis_data_collection_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Garden ladybug_data_collection target to bin by direction, usually the wind_speed target returned by EP_read_weather_file_data. Preferred over a full dictionary."
            ),
        ] = None,
        direction_count: Annotated[
            int,
            Field(description="Number of directional sectors; must be at least 3. Defaults to 36."),
        ] = 36,
        calm_threshold: Annotated[
            float,
            Field(
                description="Wind-speed values at or below this threshold are counted as calm. Applies only when the analysis data type is Speed; defaults to the SDK threshold 1e-10 m/s."
            ),
        ] = 1e-10,
        analysis_period: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Ladybug AnalysisPeriod dictionary or string applied to both input collections before binning, for example '7/1 to 7/31 between 0 and 23 @1'."
            ),
        ] = None,
        north: Annotated[
            float,
            Field(description="Counterclockwise north orientation in degrees; defaults to 0."),
        ] = 0.0,
        show_zeros: Annotated[
            bool,
            Field(description="Show calm wind as the central zero-value ring when analysis data is wind speed."),
        ] = False,
        frequency_labels: Annotated[
            bool,
            Field(description="Include frequency labels in the native VisualizationSet."),
        ] = True,
        name: Annotated[
            str,
            Field(description="VisualizationSet identifier and display name."),
        ] = "wind_rose",
        return_visualization_set: Annotated[
            bool,
            Field(
                description="Return the full VisualizationSet body. Set false to save and return visualization_set_target for existing exporters."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create WindRose statistics and a VisualizationSet."""
        from garden.visualize.windrose import windrose_to_visualization_set as service

        return service(
            garden_root=garden_root,
            direction_data_collection=direction_data_collection,
            direction_data_collection_target=direction_data_collection_target,
            analysis_data_collection=analysis_data_collection,
            analysis_data_collection_target=analysis_data_collection_target,
            direction_count=direction_count,
            calm_threshold=calm_threshold,
            analysis_period=analysis_period,
            north=north,
            show_zeros=show_zeros,
            frequency_labels=frequency_labels,
            name=name,
            return_visualization_set=return_visualization_set,
        )
