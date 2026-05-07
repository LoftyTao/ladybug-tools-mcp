"""Get Base Model MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.store import get_base_model as get_base_model_service


def register(mcp: FastMCP) -> None:
    """Register the get_base_model tool."""

    @mcp.tool(
        name="get_base_model",
        description="Read a Garden base model target and minimal context. This is not a validation tool; use validate_honeybee_model for validation, validation flags, is_valid, or issue checks. Returns top-level garden_root plus target/model_target/model_identifier for follow-up calls. By default this does not return the full Honeybee or Dragonfly model body.",
        tags={"garden", "garden-mode", "model", "base-model", "read", "safe"},
        annotations={"readOnlyHint": True},
        timeout=10,
    )
    def get_base_model(
        garden_root: Annotated[
            str, Field(description="Garden root directory containing garden.json.")
        ],
        include_body: Annotated[
            bool,
            Field(description="Explicitly request full model body. Defaults to false."),
        ] = False,
        return_object_dict: Annotated[
            bool | None,
            Field(description="Agent compatibility alias for include_body."),
        ] = None,
    ) -> dict[str, Any]:
        """Return the Garden base model target without model body unless requested."""
        if return_object_dict is not None:
            include_body = return_object_dict
        return get_base_model_service(
            garden_root=garden_root, include_body=include_body
        )
