"""Honeybee to Dragonfly conversion MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.conversion import honeybee_model_to_dragonfly as service


def register(mcp: FastMCP) -> None:
    """Register the honeybee_model_to_dragonfly tool."""

    @mcp.tool(
        name="honeybee_model_to_dragonfly",
        description="Convert a Garden Honeybee model to a Dragonfly Model using Dragonfly Model.from_honeybee, save DFJSON, and optionally set base_dragonfly_model.",
        tags={"dragonfly-core", "honeybee-core", "garden-mode", "model", "convert", "write", "safe"},
        timeout=60,
    )
    def honeybee_model_to_dragonfly(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        identifier: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Dragonfly model identifier and DFJSON file name. "
                    "Defaults to dragonfly_from_honeybee for natural conversion demos."
                )
            ),
        ] = None,
        honeybee_model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target. Defaults to base Honeybee model."),
        ] = None,
        conversion_method: Annotated[
            str,
            Field(description="Dragonfly Model.from_honeybee conversion_method, for example AllRoom2D."),
        ] = "AllRoom2D",
        set_base: Annotated[
            bool,
            Field(description="Whether to set this as Garden base_dragonfly_model."),
        ] = True,
    ) -> dict[str, Any]:
        """Convert a Honeybee model to Dragonfly."""
        return service(
            garden_root=garden_root,
            identifier=identifier or "dragonfly_from_honeybee",
            honeybee_model_target=honeybee_model_target,
            conversion_method=conversion_method,
            set_base=set_base,
        )
