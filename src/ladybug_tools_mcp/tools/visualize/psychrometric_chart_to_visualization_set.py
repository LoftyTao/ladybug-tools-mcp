"""Psychrometric chart VisualizationSet MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the LB_psychrometric_chart_to_visualization_set tool."""

    @mcp.tool(
        name="LB_psychrometric_chart_to_visualization_set",
        description=(
            "Create a Ladybug PsychrometricChart VisualizationSet from two "
            "Garden ladybug_data_collection targets: temperature in C and "
            "relative humidity in %. Optional strategy_layers overlay aligned "
            "comfort result targets such as UTCI, Adaptive, or PMV on the same "
            "psychrometric chart. Each layer is a dictionary with "
            "data_collection_target, optional label, and optional "
            "LegendParameters dictionary. The chart uses the SDK-native "
            "psychrometric_chart_to_vis_set path, persists a compact "
            "visualization_set target, and returns summary_view plus a Garden "
            "persistence_receipt. Set return_visualization_set=false to omit "
            "the full VisualizationSet body before passing the target to "
            "LB_set_to_html, LB_set_to_svg, or LB_set_to_vtkjs. It does not "
            "run comfort calculations or recreate Grasshopper data trees."
        ),
        tags={
            "ladybug",
            "psychrometric-chart",
            "thermal-comfort",
            "strategy",
            "visualize",
            "visualization-set",
        },
        timeout=60,
    )
    def psychrometric_chart_to_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        temperature_target: Annotated[
            dict[str, Any],
            Field(description="Garden ladybug_data_collection target for dry-bulb temperature in C."),
        ],
        relative_humidity_target: Annotated[
            dict[str, Any],
            Field(description="Garden ladybug_data_collection target for relative humidity in percent."),
        ],
        strategy_layers: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional aligned comfort strategy layers. Each item must include data_collection_target and may include label and legend_parameter."),
        ] = None,
        average_pressure: Annotated[
            float,
            Field(description="Average air pressure in Pa; default 101325."),
        ] = 101325,
        legend_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional SDK LegendParameters dictionary for the chart hour-frequency mesh."),
        ] = None,
        base_point: Annotated[
            dict[str, Any] | list[float] | None,
            Field(description="Optional chart base point as {x, y} or [x, y]."),
        ] = None,
        x_dim: Annotated[
            float,
            Field(description="SDK chart X scale per temperature degree; default 1."),
        ] = 1,
        y_dim: Annotated[
            float,
            Field(description="SDK chart Y scale per humidity-ratio unit; default 1500."),
        ] = 1500,
        min_temperature: Annotated[
            float,
            Field(description="Chart minimum temperature in C, or F when use_ip=true; default -20."),
        ] = -20,
        max_temperature: Annotated[
            float,
            Field(description="Chart maximum temperature in C, or F when use_ip=true; default 50."),
        ] = 50,
        max_humidity_ratio: Annotated[
            float,
            Field(description="Chart maximum humidity ratio in kg water/kg dry air; minimum 0.005."),
        ] = 0.03,
        use_ip: Annotated[
            bool,
            Field(description="Plot temperature in Fahrenheit instead of Celsius; default false."),
        ] = False,
        z: Annotated[
            float,
            Field(description="Z coordinate for the chart geometry; default 0."),
        ] = 0,
        plot_wet_bulb: Annotated[
            bool,
            Field(description="Plot constant wet-bulb lines instead of enthalpy lines; default false."),
        ] = False,
        name: Annotated[
            str,
            Field(description="Persisted VisualizationSet identifier and display name."),
        ] = "psychrometric_chart",
        return_visualization_set: Annotated[
            bool,
            Field(description="Return the full VisualizationSet body in addition to its persisted target; default true."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Garden-backed psychrometric chart VisualizationSet."""
        from garden.visualize.psychrometric_chart import (
            psychrometric_chart_to_visualization_set as service,
        )

        return service(
            garden_root=garden_root,
            temperature_target=temperature_target,
            relative_humidity_target=relative_humidity_target,
            strategy_layers=strategy_layers,
            average_pressure=average_pressure,
            legend_parameter=legend_parameter,
            base_point=base_point,
            x_dim=x_dim,
            y_dim=y_dim,
            min_temperature=min_temperature,
            max_temperature=max_temperature,
            max_humidity_ratio=max_humidity_ratio,
            use_ip=use_ip,
            z=z,
            plot_wet_bulb=plot_wet_bulb,
            name=name,
            return_visualization_set=return_visualization_set,
        )
