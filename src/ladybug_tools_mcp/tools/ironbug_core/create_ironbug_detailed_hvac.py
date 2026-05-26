"""Create Ironbug DetailedHVAC bridge summary MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core import create_ironbug_detailed_hvac as service


def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_create_detailed_hvac_system tool.'

    @mcp.tool(
        name="create_detailed_hvac_system",
        description=(
            "Create a compact Honeybee Energy DetailedHVAC bridge summary from a "
            "Garden Ironbug-Core .ibjson model and exact Honeybee Room identifiers. "
            'Use the argument ironbug_model_target from detailed_hvac_create_model, not '
            "ironbug_model. This constructs the minimal Ironbug.HVAC.IB_NoAirLoop "
            "DetailedHVAC specification for recognition/room-binding inspection only; "
            "it does not mutate a Honeybee model, generate OSM/IDF, run OpenStudio or "
            "EnergyPlus, and it is not run_ironbug_energy. Returns target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"ironbug", "detailed-hvac", "model", "author"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def create_ironbug_detailed_hvac(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required Ironbug model target named ironbug_model_target; pass "
                    "detailed_hvac_create_model['target'], not ironbug_model."
                )
            ),
        ],
        room_identifiers: Annotated[
            list[str],
            Field(
                description=(
                    "Exact Honeybee Room identifiers that should become DetailedHVAC "
                    "ThermalZone names."
                )
            ),
        ],
        detailed_hvac_identifier: Annotated[
            str | None,
            Field(description="Optional DetailedHVAC identifier. Defaults from the Ironbug model."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a compact DetailedHVAC bridge summary."""

        return service(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            room_identifiers=room_identifiers,
            detailed_hvac_identifier=detailed_hvac_identifier,
        )
