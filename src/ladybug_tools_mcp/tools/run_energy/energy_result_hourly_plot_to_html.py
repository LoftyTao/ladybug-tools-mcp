"""Energy result hourly plot HTML MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_energy.results import (
    energy_result_hourly_plot_to_html as service,
)


def register(mcp: FastMCP) -> None:
    """Register the energy_result_hourly_plot_to_html tool."""

    @mcp.tool(
        name="energy_result_hourly_plot_to_html",
        description="Compatibility path: create an interactive Garden HTML artifact directly from one hourly EnergyPlus SQL DataCollection using Ladybug HourlyPlot and VisualizationSet. Prefer read_energy_result_data with save_data_collections=true, then data_collection_hourly_plot_to_visualization_set with return_visualization_set=false, then visualization_set_to_html with visualization_set_target. Keep this direct tool for legacy/debug clients that need one Energy-owned chart-to-HTML call after read_energy_result_data finds an output_name such as zone loads, HVAC demand, unmet hours, or a custom output variable.",
        tags={
            "run-energy",
            "energy",
            "simulation",
            "result",
            "visualize",
            "hourly-plot",
            "data-collection",
            "sql",
            "html",
            "artifact",
            "write",
            "safe",
        },
        timeout=90,
    )
    def energy_result_hourly_plot_to_html(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
        ],
        output_name: Annotated[
            str,
            Field(description="Exact EnergyPlus SQL output name to plot."),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional energy_run target returned by start_energy_run or run_energy."
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        collection_index: Annotated[
            int,
            Field(
                description="Which DataCollection returned for the output_name to plot."
            ),
        ] = 0,
        name: Annotated[
            str,
            Field(description="HTML artifact file name without extension."),
        ] = "energy_result_hourly_plot",
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative artifact output directory."),
        ] = "artifacts/energy/results/html",
    ) -> dict[str, Any]:
        """Export one Energy result DataCollection to an HourlyPlot HTML artifact."""
        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            output_name=output_name,
            collection_index=collection_index,
            name=name,
            output_subdir=output_subdir,
        )
