"""DataCollection native JSON/CSV export MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.data_collection import export_data_collection_file as service


def register(mcp: FastMCP) -> None:
    'Register the visualization_data_collection_to_file tool.'

    @mcp.tool(
        name='data_collection_to_file',
        description=(
            "Export one Ladybug DataCollection to a Garden artifact using "
            "Ladybug SDK native collections_to_json or collections_to_csv. Use "
            "this for result dump/export workflows after energyplus result, "
            "schedule, or weather tools return a ladybug_data_collection "
            "target. Preferred Agent path is garden_root plus "
            "data_collection_target and file_format=json or csv. This writes "
            "a data artifact and does not query source simulations."
        ),
        tags={
            "data-collection",
            "chart",
            "visualize",
            "artifact",
            "export",
        },
        timeout=60,
    )
    def data_collection_to_file(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        file_format: Annotated[
            str,
            Field(
                description="Required native SDK export format: json uses ladybug.datautil.collections_to_json; csv uses collections_to_csv. Set csv when the user asks for a spreadsheet/table-friendly file."
            ),
        ],
        data_collection: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Ladybug DataCollection dictionary. Use data_collection_target for normal Agent workflows to avoid copying values."
            ),
        ] = None,
        data_collection_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional ladybug_data_collection target returned by an upstream Garden-backed tool. Preferred for token-saving export workflows."
            ),
        ] = None,
        name: Annotated[
            str,
            Field(description="DataCollection artifact file name without extension."),
        ] = "data_collection",
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative artifact output directory."),
        ] = "artifacts/data_collections",
    ) -> dict[str, Any]:
        """Export a Ladybug DataCollection to a native SDK JSON or CSV artifact."""
        return service(
            garden_root=garden_root,
            data_collection=data_collection,
            data_collection_target=data_collection_target,
            file_format=file_format,
            name=name,
            output_subdir=output_subdir,
            source={"producer": 'visualization_data_collection_to_file'},
        )
