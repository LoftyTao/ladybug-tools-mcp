"""Apply Dragonfly Energy properties MCP tool."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.model_io import resolve_model_target
from garden.dragonfly_core.properties import apply_dragonfly_energy_properties as service
from garden.dragonfly_core.targets import make_dragonfly_object_target


def register(mcp: FastMCP) -> None:
    """Register the apply_dragonfly_energy_properties tool."""

    @mcp.tool(
        name="apply_dragonfly_energy_properties",
        description=(
            "Apply narrow SDK-backed Dragonfly Energy properties to a Room2D, "
            "Story, or Building target. Supports Honeybee Energy library "
            "ProgramType and ConstructionSet identifiers only; this is not a "
            "generic apply-properties-from-dict bridge. For many rooms in one "
            "building, pass the Building target once instead of looping over "
            "each Room2D; the service uses Dragonfly SDK methods to apply room "
            "programs across the building."
        ),
        tags={
            "dragonfly-core",
            "garden-mode",
            "energy",
            "properties",
            "edit",
            "write",
            "safe",
        },
        timeout=20,
    )
    def apply_dragonfly_energy_properties(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        host_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Required Dragonfly Room2D, Story, or Building target. Prefer "
                    "a Building target for applying the same ProgramType to all "
                    "Room2Ds in a building. Canonical field name is host_target."
                )
            ),
        ] = None,
        target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional natural alias for host_target."),
        ] = None,
        building_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional natural alias for host_target when applying to a Building."),
        ] = None,
        story_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional natural alias for host_target when applying to a Story."),
        ] = None,
        room2d_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional natural alias for host_target when applying to a Room2D."),
        ] = None,
        building_identifier: Annotated[
            str | None,
            Field(description="Optional natural alias for a Building host identifier."),
        ] = None,
        story_identifier: Annotated[
            str | None,
            Field(description="Optional natural alias for a Story host identifier."),
        ] = None,
        room2d_identifier: Annotated[
            str | None,
            Field(description="Optional natural alias for a Room2D host identifier."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target. Defaults to base Dragonfly model."),
        ] = None,
        program_type_identifier: Annotated[
            str | None,
            Field(description="Optional Honeybee Energy ProgramType library identifier."),
        ] = None,
        construction_set_identifier: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Honeybee Energy ConstructionSet library identifier. "
                    "Use an exact construction_set identifier returned by "
                    "search_energy_library_objects; do not pass material or "
                    "construction identifiers such as ExteriorWall."
                )
            ),
        ] = None,
        program_type: Annotated[
            str | None,
            Field(description="Optional natural alias for program_type_identifier."),
        ] = None,
        construction_set: Annotated[
            str | None,
            Field(description="Optional natural alias for construction_set_identifier."),
        ] = None,
    ) -> dict[str, Any]:
        """Apply Dragonfly Energy properties."""
        host_target = (
            host_target
            or target
            or building_target
            or story_target
            or room2d_target
        )
        if host_target is None:
            identifier_aliases = (
                ("building", building_identifier),
                ("story", story_identifier),
                ("room2d", room2d_identifier),
            )
            object_type, object_identifier = next(
                (
                    (object_type, identifier)
                    for object_type, identifier in identifier_aliases
                    if identifier
                ),
                (None, None),
            )
            if object_type and object_identifier:
                manifest, resolved_model_target = resolve_model_target(
                    Path(garden_root).expanduser().resolve(),
                    model_target,
                )
                model_target = resolved_model_target
                host_target = make_dragonfly_object_target(
                    garden_id=manifest.garden_id,
                    model_identifier=str(resolved_model_target["model_identifier"]),
                    object_type=object_type,
                    object_identifier=object_identifier,
                )
        if host_target is None:
            raise ValueError(
                "apply_dragonfly_energy_properties requires host_target or a "
                "building/story/room2d identifier alias."
            )
        program_type_identifier = program_type_identifier or program_type
        construction_set_identifier = construction_set_identifier or construction_set
        return service(
            garden_root=garden_root,
            host_target=host_target,
            model_target=model_target,
            program_type_identifier=program_type_identifier,
            construction_set_identifier=construction_set_identifier,
        )
