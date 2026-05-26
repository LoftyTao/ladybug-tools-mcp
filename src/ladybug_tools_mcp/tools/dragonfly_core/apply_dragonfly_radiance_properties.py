"""Apply Dragonfly Radiance properties MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.properties import apply_dragonfly_radiance_properties as service


def register(mcp: FastMCP) -> None:
    'Register the dragonfly_apply_radiance_properties tool.'

    @mcp.tool(
        name="apply_radiance_properties",
        description=(
            "Apply narrow SDK-backed Dragonfly Radiance properties to a Room2D, "
            "Story, or Building target. Supports Honeybee Radiance ModifierSet "
            "library identifiers and Dragonfly Radiance grid parameters; this "
            "is not a Radiance simulation setup or generic properties-dict bridge. "
            "For a whole building, pass the Building target once; grid parameters "
            "are applied across its Room2Ds. Do not use Story targets for grid "
            "parameters. Allowed grid_parameter_type values are exactly room_grid, "
            "room_radial_grid, exterior_face_grid, or exterior_aperture_grid; do "
            "not pass grid_from_room_2d or radial_grid. Radiance recipe runs stay in "
            "the Radiance simulation tools."
        ),
        tags={"dragonfly", "radiance", "properties", "sensor-grid", "modifier-set", "edit"},
        timeout=20,
    )
    def apply_dragonfly_radiance_properties(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required Dragonfly Room2D, Story, or Building target. Prefer "
                    "Building for the same Radiance setup across all rooms; grid "
                    "parameters support Room2D and Building, not Story. Canonical "
                    "field name is host_target."
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
        modifier_set_identifier: Annotated[
            str | None,
            Field(description="Optional Honeybee Radiance ModifierSet library identifier applied to Dragonfly Room2Ds or parent objects."),
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
            Field(description="Required Radiance SensorGrid spacing when grid_parameter_type is provided."),
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
