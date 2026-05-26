"""Energy result hourly plot HTML MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_energy.results import (
    energy_result_hourly_plot_to_html as service,
)


def register(mcp: FastMCP) -> None:
    'Register the energyplus_result_hourly_plot_to_html tool.'

    @mcp.tool(
        name="result_hourly_plot_to_html",
        description="Create a ready-to-open Garden HTML artifact from one hourly EnergyPlus SQL DataCollection using Ladybug HourlyPlot. Use only when the requested result is an HTML file, not for EUI summaries or raw SQL DataCollection targets. Returns artifact_receipt, summary_view.artifact, summary_view.data_collection, and report; pass artifact_receipt.artifact_path or summary_view.artifact.path to preview/export flows.",
        tags={
            "energy",
            "result",
            "sql",
            "visualize",
            "hourly-plot",
            "artifact",
        },
        timeout=90,
    )
    def energy_result_hourly_plot_to_html(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        output_name: Annotated[
            str,
            Field(description="Exact EnergyPlus SQL output name to plot; choose it from energyplus_list_run_outputs or energyplus_read_result_data inventory."),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Energy run target returned by energyplus_start_simulation; pass run_target for polling unless you provide run_id.'
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
