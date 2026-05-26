"""Apply Ironbug DetailedHVAC to Honeybee model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core import apply_ironbug_detailed_hvac_to_honeybee_model as service


def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_apply_to_honeybee_model tool.'

    @mcp.tool(
        name="apply_to_honeybee_model",
        description=(
            "Apply a Garden Ironbug-Core .ibjson model as a Honeybee Energy "
            "DetailedHVAC object on selected Honeybee Rooms. Use ironbug_model_target "
            'from detailed_hvac_create_model, not ironbug_model. Select Rooms with exactly '
            "one mode: room_targets, room_identifiers, or apply_to_all_rooms=true. "
            "For room-serving systems, apply_to_all_rooms only selects Honeybee Rooms; "
            "it does not replace creating one room-linked IB_ThermalZone per Room and "
            "binding zone equipment or air terminals to those thermal zones. "
            "Returns compact targets, summary_view, report, and persistence_receipt. "
            "Before starting a standard Energy run, check summary_view.simulation_ready; "
            "if it is false, repair the listed simulation_readiness_issues first. "
            "This validates DetailedHVAC room binding but does not generate OSM/IDF, "
            "run OpenStudio or EnergyPlus, or provide run_ironbug_energy."
        ),
        tags={"ironbug", "detailed-hvac", "honeybee", "apply"},
        timeout=40,
    )
    def apply_ironbug_detailed_hvac_to_honeybee_model(
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
        honeybee_model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target. Defaults to Garden base Honeybee model."),
        ] = None,
        room_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    'Optional Honeybee Room targets from honeybee_search_model_objects '
                    "matches[i].target. Use this instead of room_identifiers or "
                    "apply_to_all_rooms; do not combine room selection modes. "
                    "Do not pass full search matches."
                )
            ),
        ] = None,
        room_identifiers: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional exact Honeybee Room identifiers to assign. Use this "
                    "instead of room_targets or apply_to_all_rooms; do not combine "
                    "room selection modes."
                )
            ),
        ] = None,
        apply_to_all_rooms: Annotated[
            bool,
            Field(
                description=(
                    "When true, assign the DetailedHVAC to every Room in the Honeybee "
                    "model. Use this instead of room_targets or room_identifiers; "
                    "do not combine room selection modes. This must be explicit; "
                    "omitted selection is rejected. "
                    "Room-serving Ironbug HVAC still requires explicit IB_ThermalZone "
                    "objects in the Ironbug model."
                )
            ),
        ] = False,
        detailed_hvac_identifier: Annotated[
            str | None,
            Field(description="Optional DetailedHVAC identifier. Defaults from the Ironbug model."),
        ] = None,
    ) -> dict[str, Any]:
        """Apply Ironbug DetailedHVAC to selected Honeybee Rooms."""

        return service(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            honeybee_model_target=honeybee_model_target,
            room_targets=room_targets,
            room_identifiers=room_identifiers,
            apply_to_all_rooms=apply_to_all_rooms,
            detailed_hvac_identifier=detailed_hvac_identifier,
        )
