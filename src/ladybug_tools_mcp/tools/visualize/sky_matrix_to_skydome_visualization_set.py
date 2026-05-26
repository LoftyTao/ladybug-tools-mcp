"""SkyMatrix to SkyDome VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.visualize.sky import sky_matrix_to_skydome_visualization_set as service


def register(mcp: FastMCP) -> None:
    'Register the visualization_sky_matrix_to_skydome_visualization_set tool.'

    @mcp.tool(
        name='sky_matrix_to_skydome_visualization_set',
        description=(
            "Create a Ladybug Display Sky Dome VisualizationSet from a Garden "
            "sky_matrix target. Use this to compose cumulative sky radiation "
            "context with model, sunpath, or analysis VisualizationSets. This "
            "visualizes existing sky-matrix data; it does not create weather, "
            "sky matrices, or Radiance runs."
        ),
        tags={
            "radiation",
            "radiance",
            "sky",
            "visualize",
            "visualization-set",
        },
        timeout=120,
    )
    def sky_matrix_to_skydome_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        sky_matrix_target: Annotated[
            dict[str, Any],
            Field(description='Existing Garden sky_matrix target returned by radiance_create_sky_matrix.'),
        ],
        legend_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Ladybug LegendParameters dictionary."),
        ] = None,
        plot_irradiance: Annotated[
            bool,
            Field(description="When true, plot irradiance values; when false, plot radiation values."),
        ] = False,
        radius: Annotated[
            float,
            Field(description="Sky dome radius."),
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
        ] = "sky_dome",
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
        """Create a SkyDome VisualizationSet from a SkyMatrix target."""
        return service(
            garden_root=garden_root,
            sky_matrix_target=sky_matrix_target,
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
