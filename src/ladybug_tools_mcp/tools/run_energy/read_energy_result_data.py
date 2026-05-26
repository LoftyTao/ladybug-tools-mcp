"""Read Energy SQL result DataCollections MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.run_energy.results import read_energy_result_data as service


def register(mcp: FastMCP) -> None:
    'Register the energyplus_read_result_data tool.'

    @mcp.tool(
        name="read_result_data",
        description='Read EnergyPlus SQL results from a completed Garden energy_run as compact Ladybug DataCollection summaries with result_context provenance. Use output names from energyplus_list_run_outputs or SQL output inventory filters. Without output_name/output_names/filters, returns available_outputs only. With save_data_collections=true, returns data_collection_targets and summary_view.first_data_collection_target for visualization tools; there is no top-level target or single data_collection_target.',
        tags={
            "energy",
            "result",
            "sql",
            "data-collection",
        },
        timeout=60,
    )
    def read_energy_result_data(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Energy run target returned by energyplus_start_simulation; pass run_target unless you provide run_id.'
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        output_name: Annotated[
            str | None,
            Field(
                description="Optional exact EnergyPlus SQL output name to read as DataCollections. Omit to list or filter available SQL outputs."
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
