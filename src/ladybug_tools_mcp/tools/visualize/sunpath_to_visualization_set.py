"""Sunpath VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.visualize.sky import sunpath_to_visualization_set as service


def register(mcp: FastMCP) -> None:
    """Register the sunpath_to_visualization_set tool."""

    @mcp.tool(
        name="sunpath_to_visualization_set",
        description=(
            "Create a Ladybug Display Sunpath VisualizationSet from a Location, "
            "Garden weather_file target, or Garden-relative EPW path. Use this "
            "for solar-analysis scenes that need to compose sunpath geometry with "
            "model or analysis Visualization Sets."
        ),
        tags={
            "visualize",
            "visualization-set",
            "sunpath",
            "ladybug",
            "weather",
            "location",
            "solar",
            "target",
            "safe",
        },
        timeout=60,
    )
    def sunpath_to_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
        ],
        location: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Ladybug Location dictionary. Use instead of "
                    "weather_target or epw_path."
                )
            ),
        ] = None,
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Garden weather_file target. Use instead of "
                    "location or epw_path."
                )
            ),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Garden-relative EPW path. Use instead of location "
                    "or weather_target."
                )
            ),
        ] = None,
        north_angle: Annotated[
            float,
            Field(description="Counterclockwise north angle in degrees."),
        ] = 0,
        hoys: Annotated[
            list[float] | None,
            Field(description="Optional hours of year for displayed sun positions."),
        ] = None,
        radius: Annotated[
            float,
            Field(description="Sunpath radius."),
        ] = 100,
        center_point: Annotated[
            dict[str, Any] | list[float] | None,
            Field(description="Optional center point as {x,y,z} or [x,y,z]."),
        ] = None,
        solar_time: Annotated[
            bool,
            Field(description="Draw hour labels using solar time."),
        ] = False,
        daily: Annotated[
            bool,
            Field(description="Draw only daily arcs for provided hoys."),
        ] = False,
        projection: Annotated[
            str | None,
            Field(description="Optional 2D projection: Orthographic or Stereographic."),
        ] = None,
        sun_spheres: Annotated[
            bool,
            Field(description="Render sun positions as spheres instead of points."),
        ] = False,
        name: Annotated[
            str,
            Field(description="VisualizationSet identifier and display name."),
        ] = "sunpath",
        return_visualization_set: Annotated[
            bool,
            Field(
                description=(
                    "Return the full VisualizationSet dict. Set false with "
                    "garden_root to save and return a compact visualization_set_target."
                )
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Sunpath VisualizationSet."""
        return service(
            garden_root=garden_root,
            location=location,
            weather_target=weather_target,
            epw_path=epw_path,
            north_angle=north_angle,
            hoys=hoys,
            radius=radius,
            center_point=center_point,
            solar_time=solar_time,
            daily=daily,
            projection=projection,
            sun_spheres=sun_spheres,
            name=name,
            return_visualization_set=return_visualization_set,
        )
