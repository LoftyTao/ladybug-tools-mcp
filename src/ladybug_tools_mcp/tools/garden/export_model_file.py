"""Central Garden model file export MCP tool."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.model_export import export_model_file as service


def register(mcp: FastMCP) -> None:
    """Register the export_model_file tool."""

    @mcp.tool(
        name="export_model_file",
        description=(
            "Export an explicit Garden Honeybee Model or Dragonfly Model target to "
            "a DOE INP or DesignBuilder dsbXML file artifact inside the Garden. "
            "Requires garden_root, export_format, and model_target; pass a model "
            "target returned by create_honeybee_model, create_dragonfly_model, "
            "list_garden_models, get_base_honeybee_model, or get_base_dragonfly_model. "
            "The tool derives Honeybee vs Dragonfly from model_target and records the "
            "output under Garden artifacts. Do not pass arguments null or {}."
        ),
        tags={
            "garden",
            "model-export",
            "artifact",
            "honeybee",
            "dragonfly",
            "doe-inp",
            "designbuilder-dsbxml",
            "write",
            "safe",
        },
        timeout=60,
    )
    def export_model_file(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        export_format: Annotated[
            Literal["doe_inp", "designbuilder_dsbxml"],
            Field(description="Required export format: doe_inp or designbuilder_dsbxml."),
        ],
        model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required exact Honeybee Model or Dragonfly Model target. Pass the "
                    "nested model_target dict from a model create/list/base-model tool, "
                    "not a full tool response and not an identifier string."
                )
            ),
        ],
        name: Annotated[
            str | None,
            Field(description="Optional artifact file name without extension."),
        ] = None,
        include_body: Annotated[
            bool,
            Field(
                description=(
                    "Return the exported file text as file_body. Keep False for ordinary "
                    "Agent workflows."
                )
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Export a Honeybee or Dragonfly model file artifact."""
        return service(
            garden_root=garden_root,
            export_format=export_format,
            model_target=model_target,
            name=name,
            include_body=include_body,
        )
