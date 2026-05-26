"""Get Dragonfly Model Summary MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.summary import get_dragonfly_model_summary as service


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_get_model_summary tool.'

    @mcp.tool(
        name="get_model_summary",
        description=(
            "Return compact counts and metadata for the Garden base Dragonfly model "
            "or an explicit Dragonfly model target. This does not return the full "
            "DFJSON body or mutate the model."
        ),
        tags={"dragonfly", "model", "summary", "search", "inventory"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_dragonfly_model_summary(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually dragonfly_create_model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Get compact Dragonfly model counts and metadata."""
        return service(garden_root=garden_root, model_target=model_target)
