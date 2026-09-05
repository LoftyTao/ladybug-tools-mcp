"""Apply shared Honeybee Room Energy properties MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the HB_apply_room_energy_properties tool."""

    @mcp.tool(
        name="HB_apply_room_energy_properties",
        description=(
            "Apply one shared set of Honeybee Energy properties atomically to "
            "multiple Room targets in one Garden Honeybee Model. Provide exactly "
            "one of room_targets (typed targets from HB_search_model_objects) or "
            "room_identifiers, plus energy_properties containing only "
            "program_type, construction_set, template hvac, ventilation, setpoint, "
            "or zone_ventilation_fans. The tool resolves and validates every Room "
            "and property reference before one Garden save; any missing Room, "
            "cross-model target, invalid reference, or revision conflict leaves "
            "the model unchanged. Returns updated_room_count, a limited Room "
            "identifier sample, model_target, persistence_receipt, and report. "
            "Identical values return no_change without another model revision. "
            "This is not a Face/Aperture/Door/Radiance batch editor or an Ironbug "
            "DetailedHVAC placement tool."
        ),
        tags={
            "apply",
            "batch",
            "construction-set",
            "energy",
            "honeybee",
            "hvac-template",
            "program-type",
            "room",
            "setpoint",
            "ventilation",
        },
        timeout=30,
    )
    def apply_room_energy_properties(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_create['garden_root']."
                )
            ),
        ],
        energy_properties: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required shared property changes. Supported keys are only "
                    "program_type, construction_set, hvac, ventilation, setpoint, "
                    "and zone_ventilation_fans; values may be SDK dictionaries, "
                    "Garden property targets, or supported standard identifiers."
                )
            ),
        ],
        room_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Optional non-empty list of Honeybee Room typed targets from "
                    "HB_search_model_objects.matches[i].target. Do not provide "
                    "this together with room_identifiers."
                )
            ),
        ] = None,
        room_identifiers: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional non-empty list of exact Room identifiers in the "
                    "selected Honeybee Model. Do not provide this together with "
                    "room_targets."
                )
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Honeybee Model target, usually HB_create_model['target']; "
                    "defaults to the Garden base Honeybee Model. Every typed Room "
                    "target must belong to this same model and Garden."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Apply shared Honeybee Room Energy properties."""
        from garden.honeybee_core.room_energy import (
            apply_room_energy_properties as service,
        )

        return service(
            garden_root=garden_root,
            energy_properties=energy_properties,
            room_targets=room_targets,
            room_identifiers=room_identifiers,
            model_target=model_target,
        )
