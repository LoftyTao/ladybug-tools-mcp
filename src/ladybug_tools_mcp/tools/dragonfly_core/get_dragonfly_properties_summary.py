"""Get Dragonfly Energy/Radiance properties summary MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.properties import get_dragonfly_properties_summary as service


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_get_properties_summary tool.'

    @mcp.tool(
        name="get_properties_summary",
        description=(
            "Read compact Dragonfly Energy and Radiance extension property summaries "
            "from a Garden Dragonfly model. Imports the official dragonfly_energy and "
            "dragonfly_radiance extension hooks, then reports Model, Building, Story, "
            "and Room2D properties only when SDK to_dict is available. This is a "
            'read-only summary; use dragonfly_apply_energy_properties for the narrow '
            "SDK-backed Energy ProgramType/ConstructionSet identifier path and "
            "dragonfly_apply_radiance_properties for ModifierSet or SensorGrid setup."
        ),
        tags={"dragonfly", "energy", "radiance", "summary", "properties", "inventory"},
        timeout=20,
    )
    def get_dragonfly_properties_summary(
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
        """Read Dragonfly properties summaries."""
        return service(garden_root=garden_root, model_target=model_target)
