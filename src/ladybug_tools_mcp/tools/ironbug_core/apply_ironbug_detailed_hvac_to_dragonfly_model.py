"""Apply Ironbug DetailedHVAC through Dragonfly conversion MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core import apply_ironbug_detailed_hvac_to_dragonfly_model as service


def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_apply_to_dragonfly_model tool.'

    @mcp.tool(
        name="apply_to_dragonfly_model",
        description=(
            "Convert a Garden Dragonfly model to Honeybee first, then apply a Garden "
            "Ironbug-Core .ibjson model as Honeybee Energy DetailedHVAC. Use "
            'ironbug_model_target from detailed_hvac_create_model, not ironbug_model. '
            "Select converted Honeybee Rooms with exact room_identifiers, or set "
            "apply_to_all_rooms=true explicitly. This does not mutate Dragonfly HVAC "
            "directly, generate OSM/IDF, run OpenStudio or EnergyPlus, or provide "
            "run_ironbug_energy. Returns model_target, summary_view, "
            "persistence_receipt, and report."
        ),
        tags={"ironbug", "detailed-hvac", "dragonfly", "apply"},
        timeout=60,
    )
    def apply_ironbug_detailed_hvac_to_dragonfly_model(
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
        dragonfly_model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target. Defaults to Garden base Dragonfly model."),
        ] = None,
        room_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional exact converted Honeybee Room identifiers to assign."),
        ] = None,
        apply_to_all_rooms: Annotated[
            bool,
            Field(
                description=(
                    "When true, assign the DetailedHVAC to every Room in the converted "
                    "Honeybee model. This must be explicit; omitted selection is rejected."
                )
            ),
        ] = False,
        detailed_hvac_identifier: Annotated[
            str | None,
            Field(description="Optional DetailedHVAC identifier. Defaults from the Ironbug model."),
        ] = None,
    ) -> dict[str, Any]:
        """Apply Ironbug DetailedHVAC after Dragonfly-to-Honeybee conversion."""

        return service(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            dragonfly_model_target=dragonfly_model_target,
            room_identifiers=room_identifiers,
            apply_to_all_rooms=apply_to_all_rooms,
            detailed_hvac_identifier=detailed_hvac_identifier,
        )
