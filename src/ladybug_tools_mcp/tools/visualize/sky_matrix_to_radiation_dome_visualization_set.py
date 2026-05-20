"""SkyMatrix to cumulative RadiationDome VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.visualize.sky import (
    sky_matrix_to_radiation_dome_visualization_set as service,
)


def register(mcp: FastMCP) -> None:
    """Register the sky_matrix_to_radiation_dome_visualization_set tool."""

    @mcp.tool(
        name="sky_matrix_to_radiation_dome_visualization_set",
        description=(
            "Create a cumulative Ladybug Radiance Radiation Dome VisualizationSet "
            "from a Garden sky_matrix target. This tool intentionally supports "
            "only cumulative sky matrix mode, not benefit sky matrix mode."
        ),
        tags={
            "visualize",
            "visualization-set",
            "sky-matrix",
            "radiation-dome",
            "cumulative",
            "radiance",
            "ladybug-radiance",
            "solar",
            "target",
            "safe",
        },
        timeout=120,
    )
    def sky_matrix_to_radiation_dome_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
        ],
        sky_matrix_target: Annotated[
            dict[str, Any],
            Field(description="Garden sky_matrix target returned by create_sky_matrix."),
        ],
        azimuth_count: Annotated[
            int,
            Field(description="Number of azimuth subdivisions for the dome mesh."),
        ] = 72,
        altitude_count: Annotated[
            int,
            Field(description="Number of altitude subdivisions for the dome mesh."),
        ] = 18,
        legend_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Ladybug LegendParameters dictionary."),
        ] = None,
        plot_irradiance: Annotated[
            bool,
            Field(description="Plot irradiance instead of radiation."),
        ] = False,
        radius: Annotated[
            float,
            Field(description="Radiation dome radius."),
        ] = 100,
        center_point: Annotated[
            dict[str, Any] | list[float] | None,
            Field(description="Optional center point as {x,y,z} or [x,y,z]."),
        ] = None,
        projection: Annotated[
            str | None,
            Field(description="Optional 2D projection: Orthographic or Stereographic."),
        ] = None,
        show_components: Annotated[
            bool,
            Field(description="Show total, direct, and diffuse component domes."),
        ] = False,
        include_title: Annotated[
            bool,
            Field(description="Include the generated dome title text."),
        ] = True,
        name: Annotated[
            str,
            Field(description="VisualizationSet identifier and display name."),
        ] = "radiation_dome",
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
        """Create a cumulative RadiationDome VisualizationSet."""
        return service(
            garden_root=garden_root,
            sky_matrix_target=sky_matrix_target,
            azimuth_count=azimuth_count,
            altitude_count=altitude_count,
            legend_parameter=legend_parameter,
            plot_irradiance=plot_irradiance,
            radius=radius,
            center_point=center_point,
            projection=projection,
            show_components=show_components,
            include_title=include_title,
            name=name,
            return_visualization_set=return_visualization_set,
        )
