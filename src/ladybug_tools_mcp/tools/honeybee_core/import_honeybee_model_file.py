"""Import Honeybee model file MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the HB_import_model_file tool."""

    @mcp.tool(
        name="HB_import_model_file",
        description=(
            "Import a Garden-local Honeybee HBJSON file and save it as a Honeybee "
            "model target. The file path must be relative to the Garden; the full "
            "model body is not returned."
        ),
        tags={"author", "honeybee", "model", "hbjson", "import", "garden"},
        timeout=60,
    )
    def import_honeybee_model_file(
        garden_root: Annotated[
            str, Field(description="Required Garden root path containing garden.json.")
        ],
        file_path: Annotated[
            str, Field(description="Garden-relative .hbjson file path to import.")
        ],
        identifier: Annotated[
            str | None, Field(description="Optional identifier for the stored model.")
        ] = None,
        set_base: Annotated[
            bool,
            Field(description="Whether to set the imported model as the base Honeybee model."),
        ] = True,
    ) -> dict[str, Any]:
        """Import a Honeybee HBJSON model file."""
        from garden.honeybee_core.model_files import import_honeybee_model_file as service

        return service(
            garden_root=garden_root,
            file_path=file_path,
            identifier=identifier,
            set_base=set_base,
        )
