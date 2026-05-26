"""Get Dragonfly UWG properties summary MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.uwg_properties import (
    get_dragonfly_uwg_properties_summary as service,
)


def register(mcp: FastMCP) -> None:
    'Register the uwg_get_dragonfly_properties_summary tool.'

    @mcp.tool(
        name='get_dragonfly_properties_summary',
        description=(
            "Read compact Dragonfly Urban Weather Generator extension properties for "
            "the model, Buildings, and ContextShades. Use this to inspect UWG setup "
            "before weather morphing; this is adjacent to URBANopt concepts but not a "
            "URBANopt Scenario. Returns summary_view and report without changing the model."
        ),
        tags={
            "dragonfly",
            "uwg",
            "weather",
            "summary",
            "inventory",
        },
        timeout=20,
    )
    def get_dragonfly_uwg_properties_summary(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target with target_type=dragonfly_model. Defaults to the Garden base Dragonfly model."),
        ] = None,
    ) -> dict[str, Any]:
        """Read Dragonfly UWG properties."""
        return service(garden_root=garden_root, model_target=model_target)
