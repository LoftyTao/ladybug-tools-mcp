"""Apply Dragonfly Energy properties MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.properties import apply_dragonfly_energy_properties as service


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_apply_energy_properties tool.'

    @mcp.tool(
        name="apply_energy_properties",
        description=(
            "Apply narrow SDK-backed Dragonfly Energy properties to a Room2D, "
            "Story, or Building target. Supports Honeybee Energy library "
            "ProgramType and ConstructionSet identifiers only; this is not a "
            "generic apply-properties-from-dict bridge. For many rooms in one "
            "building, pass the Building target once instead of looping over "
            "each Room2D; the service uses Dragonfly SDK methods to apply room "
            "programs across the building. EnergyPlus simulation remains a downstream "
            "workflow after Dragonfly-to-Honeybee conversion."
        ),
        tags={"dragonfly", "energy", "properties", "edit", "program-type", "construction-set"},
        timeout=20,
    )
    def apply_dragonfly_energy_properties(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required Dragonfly Room2D, Story, or Building target. Prefer "
                    "a Building target for applying the same ProgramType to all "
                    "Room2Ds in a building. Canonical field name is host_target."
                )
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
        program_type_identifier: Annotated[
            str | None,
            Field(description="Optional Honeybee Energy ProgramType library identifier applied to Dragonfly Room2Ds."),
        ] = None,
        construction_set_identifier: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Honeybee Energy ConstructionSet library identifier. "
                    "Use an exact construction_set identifier returned by "
                    'energy_search_energy_library_objects; do not pass material or '
                    "construction identifiers such as ExteriorWall."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Apply Dragonfly Energy properties."""
        return service(
            garden_root=garden_root,
            host_target=host_target,
            model_target=model_target,
            program_type_identifier=program_type_identifier,
            construction_set_identifier=construction_set_identifier,
        )
