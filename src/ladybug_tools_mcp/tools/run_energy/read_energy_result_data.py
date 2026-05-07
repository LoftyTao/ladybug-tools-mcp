"""Read Energy SQL result DataCollections MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_energy.results import read_energy_result_data as service


def register(mcp: FastMCP) -> None:
    """Register the read_energy_result_data tool."""

    @mcp.tool(
        name="read_energy_result_data",
        description="Read EnergyPlus SQL results from a completed Garden energy_run as compact Ladybug DataCollection summaries with result_context provenance from the run ledger and create_energy_output_request when available. Use this for user result terms such as heating energy, cooling energy, HVAC power, zone load, unmet hours, surface temperature, humidity, hourly, daily, monthly, timestep, and custom output variables. If output_name, output_names, and filters are omitted, returns the available SQL output inventory. Query path: use output_query and filter by unit, data_type, or object_type to select outputs without copying SQL metadata. Agent chart path: set output_name for one result or output_names/output_query for multi-series result charts, save_data_collections=true, and include_values=false to persist returned collections as ladybug_data_collection targets for generic visualize tools such as data_collection_monthly_chart_to_visualization_set and data_collection_hourly_plot_to_visualization_set.",
        tags={
            "run-energy",
            "energy",
            "simulation",
            "result",
            "results",
            "sql",
            "data-collection",
            "data-collection-target",
            "visualize",
            "timeseries",
            "hourly",
            "daily",
            "monthly",
            "heating-energy",
            "cooling-energy",
            "hvac-power",
            "temperature",
            "chart",
            "custom-output",
            "output-query",
            "provenance",
            "metadata",
            "unit",
            "data-type",
            "read",
            "write",
            "safe",
        },
        timeout=60,
    )
    def read_energy_result_data(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
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
        output_name: Annotated[
            str | None,
            Field(
                description="Optional exact EnergyPlus SQL output name to read as DataCollections. Omit to list available outputs."
            ),
        ] = None,
        output_names: Annotated[
            list[str] | None,
            Field(
                description="Optional exact EnergyPlus SQL output names to read in one call for multi-series charts. Provide only one of output_name or output_names."
            ),
        ] = None,
        output_query: Annotated[
            str | None,
            Field(
                description="Optional case-insensitive substring query for SQL output names, used when output_name and output_names are omitted."
            ),
        ] = None,
        unit: Annotated[
            str | None,
            Field(
                description="Optional exact unit filter for SQL outputs, for example kWh, kW, C, or %."
            ),
        ] = None,
        data_type: Annotated[
            str | None,
            Field(
                description="Optional exact Ladybug data_type filter for SQL outputs, for example Energy, Power, Temperature, or Fraction."
            ),
        ] = None,
        object_type: Annotated[
            str | None,
            Field(
                description="Optional case-insensitive object_type filter from SQL output metadata, for example Zone or System."
            ),
        ] = None,
        run_period_index: Annotated[
            int | None,
            Field(description="Optional EnergyPlus run period index."),
        ] = None,
        include_values: Annotated[
            bool,
            Field(
                description="Whether to include bounded raw values from each DataCollection. Default false to keep Agent context small."
            ),
        ] = False,
        max_values: Annotated[
            int,
            Field(
                description="Maximum values per DataCollection when include_values is true."
            ),
        ] = 24,
        max_collections: Annotated[
            int,
            Field(description="Maximum DataCollection summaries to return."),
        ] = 10,
        max_outputs: Annotated[
            int,
            Field(
                description="Maximum SQL outputs selected by output_query/unit/data_type/object_type filters."
            ),
        ] = 25,
        save_data_collections: Annotated[
            bool,
            Field(
                description="Persist each returned DataCollection as a Garden ladybug_data_collection target and return data_collection_targets. Keep false for inventory-only reads; set true with include_values=false before passing targets into generic visualize tools."
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Read Energy result DataCollection summaries."""
        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            output_name=output_name,
            output_names=output_names,
            output_query=output_query,
            unit=unit,
            data_type=data_type,
            object_type=object_type,
            run_period_index=run_period_index,
            include_values=include_values,
            max_values=max_values,
            max_collections=max_collections,
            max_outputs=max_outputs,
            save_data_collections=save_data_collections,
        )
