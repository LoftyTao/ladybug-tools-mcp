"""Apply Dragonfly Radiance properties MCP tool."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.model_io import resolve_model_target
from garden.dragonfly_core.properties import apply_dragonfly_radiance_properties as service
from garden.dragonfly_core.targets import make_dragonfly_object_target


def register(mcp: FastMCP) -> None:
    """Register the apply_dragonfly_radiance_properties tool."""

    @mcp.tool(
        name="apply_dragonfly_radiance_properties",
        description=(
            "Apply narrow SDK-backed Dragonfly Radiance properties to a Room2D, "
            "Story, or Building target. Supports Honeybee Radiance ModifierSet "
            "library identifiers and Dragonfly Radiance grid parameters; this "
            "is not a Radiance simulation setup or generic properties-dict bridge. "
            "For a whole building, pass the Building target once; grid parameters "
            "are applied across its Room2Ds. Do not use Story targets for grid "
            "parameters. Allowed grid_parameter_type values are exactly room_grid, "
            "room_radial_grid, exterior_face_grid, or exterior_aperture_grid; do "
            "not pass grid_from_room_2d or radial_grid."
        ),
        tags={
            "dragonfly-core",
            "garden-mode",
            "radiance",
            "properties",
            "edit",
            "write",
            "safe",
        },
        timeout=20,
    )
    def apply_dragonfly_radiance_properties(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        host_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Required Dragonfly Room2D, Story, or Building target. Prefer "
                    "Building for the same Radiance setup across all rooms; grid "
                    "parameters support Room2D and Building, not Story. Canonical "
                    "field name is host_target."
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
        modifier_set_identifier: Annotated[
            str | None,
            Field(description="Optional Honeybee Radiance ModifierSet library identifier."),
        ] = None,
        modifier_set: Annotated[
            str | None,
            Field(description="Optional natural alias for modifier_set_identifier."),
        ] = None,
        grid_parameter_type: Annotated[
            str | None,
            Field(
                description=(
                    "Optional grid parameter type: room_grid, room_radial_grid, "
                    "exterior_face_grid, or exterior_aperture_grid. Use room_grid "
                    "for ordinary workplane sensor grids; use room_radial_grid "
                    "for radial grids. Do not pass radial_grid."
                )
            ),
        ] = None,
        grid_dimension: Annotated[
            float | None,
            Field(description="Required grid dimension when grid_parameter_type is provided."),
        ] = None,
        grid_size: Annotated[
            float | None,
            Field(description="Optional natural alias for grid_dimension."),
        ] = None,
        grid_spacing: Annotated[
            float | None,
            Field(description="Optional natural alias for grid_dimension."),
        ] = None,
        grid_offset: Annotated[
            float | None,
            Field(description="Optional grid offset. Defaults follow the Dragonfly SDK class."),
        ] = None,
        wall_offset: Annotated[
            float,
            Field(description="Wall offset for room_grid and room_radial_grid parameters."),
        ] = 0,
        face_type: Annotated[
            str,
            Field(description="Face type for exterior_face_grid: Wall, Roof, Floor, or All."),
        ] = "Wall",
        aperture_type: Annotated[
            str,
            Field(description="Aperture type for exterior_aperture_grid: Window, Skylight, or All."),
        ] = "All",
        punched_geometry: Annotated[
            bool,
            Field(description="Whether exterior_face_grid should use punched face geometry."),
        ] = False,
        dir_count: Annotated[
            int,
            Field(description="Direction count for room_radial_grid."),
        ] = 8,
        start_vector: Annotated[
            list[float] | None,
            Field(description="Optional [x, y, z] start vector for room_radial_grid."),
        ] = None,
        mesh_radius: Annotated[
            float | None,
            Field(description="Optional mesh radius for room_radial_grid."),
        ] = None,
        include_mesh: Annotated[
            bool,
            Field(description="Whether generated SensorGrid instructions should include mesh."),
        ] = True,
        remove_existing_grid_parameters: Annotated[
            bool,
            Field(description="Whether to remove existing Room2D grid parameters before adding."),
        ] = False,
    ) -> dict[str, Any]:
        """Apply Dragonfly Radiance properties."""
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
                "apply_dragonfly_radiance_properties requires host_target or a "
                "building/story/room2d identifier alias."
            )
        modifier_set_identifier = modifier_set_identifier or modifier_set
        grid_dimension = grid_dimension or grid_size or grid_spacing
        return service(
            garden_root=garden_root,
            host_target=host_target,
            model_target=model_target,
            modifier_set_identifier=modifier_set_identifier,
            grid_parameter_type=grid_parameter_type,
            grid_dimension=grid_dimension,
            grid_offset=grid_offset,
            wall_offset=wall_offset,
            face_type=face_type,
            aperture_type=aperture_type,
            punched_geometry=punched_geometry,
            dir_count=dir_count,
            start_vector=start_vector,
            mesh_radius=mesh_radius,
            include_mesh=include_mesh,
            remove_existing_grid_parameters=remove_existing_grid_parameters,
        )
