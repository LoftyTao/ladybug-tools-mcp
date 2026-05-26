"""Central Garden model file export MCP tool."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.model_export import export_model_file as service


def register(mcp: FastMCP) -> None:
    'Register the garden_export_model_file tool.'

    @mcp.tool(
        name='export_model_file',
        description=(
            "Export an explicit Garden Honeybee Model or Dragonfly Model target to "
            "a Garden-managed DOE-2 INP or DesignBuilder dsbXML export artifact. "
            "Requires garden_root, export_format, and a nested model_target from "
            "a Honeybee/Dragonfly create tool, garden_list_models, "
            "garden_get_base_honeybee_model, or garden_get_base_dragonfly_model. "
            "The tool derives Honeybee vs Dragonfly from model_target, validates "
            "that the source is a Garden-relative .hbjson or .dfjson file, and "
            "returns target, model_export_artifact_target, artifact_receipt, "
            "summary_view, and report. It does not export arbitrary files and "
            "does not return file_body unless include_body is true."
        ),
        tags={
            "artifact",
            "designbuilder",
            "doe2",
            "export",
            "garden",
            "honeybee",
            "model",
            "dragonfly",
        },
        timeout=60,
    )
    def export_model_file(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "garden_create['garden_root']; the model target and export "
                    "artifact must belong to this Garden."
                )
            ),
        ],
        export_format: Annotated[
            Literal["doe_inp", "designbuilder_dsbxml"],
            Field(
                description=(
                    "Required export format enum. Use doe_inp for a DOE-2 .inp "
                    "artifact or designbuilder_dsbxml for a DesignBuilder .dsbxml "
                    "artifact; the same value becomes the artifact type."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required exact Honeybee Model or Dragonfly Model target. Pass the "
                    "nested model_target dict from a model create/list/base-model tool, "
                    "not a full tool response and not an identifier string. Targets "
                    "from garden_list_models must include a Garden-relative path to "
                    ".hbjson or .dfjson."
                )
            ),
        ],
        name: Annotated[
            str | None,
            Field(
                description=(
                    "Optional export artifact file stem without extension; the "
                    "extension is chosen from export_format."
                )
            ),
        ] = None,
        include_body: Annotated[
            bool,
            Field(
                description=(
                    "Return the exported DOE-2 INP or DesignBuilder dsbXML text as "
                    "file_body. Keep False for ordinary Agent workflows that only "
                    "need the artifact target."
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
