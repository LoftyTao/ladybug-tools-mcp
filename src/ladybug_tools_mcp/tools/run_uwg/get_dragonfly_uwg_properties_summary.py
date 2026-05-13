"""Get Dragonfly UWG properties summary MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.uwg_properties import (
    get_dragonfly_uwg_properties_summary as service,
)


def register(mcp: FastMCP) -> None:
    """Register the get_dragonfly_uwg_properties_summary tool."""

    @mcp.tool(
        name="get_dragonfly_uwg_properties_summary",
        description=(
            "Read compact Dragonfly Urban Weather Generator (UWG) extension "
            "properties for the model, buildings, and context shades. This is "
            "for Alternative Weather/UWG setup, not full URBANopt Energy, "
            "Electric Grid, or District Thermal."
        ),
        tags={
            "run-uwg",
            "uwg",
            "alternative-weather",
            "dragonfly",
            "properties",
            "read",
            "safe",
        },
        timeout=20,
    )
    def get_dragonfly_uwg_properties_summary(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target. Defaults to base Dragonfly model."),
        ] = None,
    ) -> dict[str, Any]:
        """Read Dragonfly UWG properties."""
        return service(garden_root=garden_root, model_target=model_target)
