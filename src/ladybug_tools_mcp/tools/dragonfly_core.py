"""dragonfly_core MCP tools."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field, StrictBool, StrictFloat, StrictStr


def register(mcp: FastMCP) -> None:
    """Register dragonfly_core tools."""

    @mcp.tool(
        name="DF_Add_Stories_To_Building",
        description=(
            'Add Dragonfly Story draft targets to an existing Building using Dragonfly '
            'Building.add_stories, then save the DFJSON model. The existing Building is selected '
            'by building_identifier. After adding, the service uses Dragonfly SDK '
            'Building.separate_top_bottom_floors so repeated Story multipliers keep explicit '
            'ground, typical, and top Stories. Returns the updated Dragonfly Building and model '
            'target context.'
        ),
        tags={"dragonfly", "building", "story", "edit", "assembly"},
        timeout=20,
    )
    def add_dragonfly_stories_to_building(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        building_identifier: Annotated[
            str,
            Field(description="Required identifier of the existing Dragonfly Building inside the selected Dragonfly Model."),
        ],
        story_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Required list of Dragonfly Story targets returned by DF_Story or Dragonfly object search."),
        ] = None,
        story_identifiers: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional natural recovery input for draft Story identifiers. "
                    "When used, the service resolves each identifier to the Garden "
                    "draft Story object for the active Dragonfly model."
                )
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Add Dragonfly Stories to a Building."""
        from garden.dragonfly_core.editing import add_dragonfly_stories_to_building as service

        return service(
            garden_root=garden_root,
            building_identifier=building_identifier,
            story_targets=story_targets,
            model_target=model_target,
            story_identifiers=story_identifiers,
        )

    @mcp.tool(
        name="DF_Align_Room2Ds",
        description=(
            "Align Room2D vertices in a Dragonfly Story, Building, or Model to a "
            "list of straight 2D line segments using Story.align. The operation "
            "also removes duplicate/degenerate Room2Ds using Dragonfly SDK methods, "
            "saves at most once only when the model changes, and returns affected "
            "Building, Story, and Room2D counts and identifier summaries."
        ),
        tags={"dragonfly", "room2d", "geometry", "align", "edit"},
        timeout=30,
    )
    def align_dragonfly_room2ds(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        lines: Annotated[
            list[list[list[StrictFloat]]],
            Field(
                description=(
                    "Required straight 2D line segments as "
                    "[[[x1, y1], [x2, y2]], ...]."
                )
            ),
        ],
        distance: Annotated[
            StrictFloat,
            Field(description="Maximum distance from a line for a vertex to be aligned; defaults to 0.5."),
        ] = 0.5,
        tolerance: Annotated[
            StrictFloat,
            Field(description="Positive Dragonfly geometry tolerance; defaults to 0.01."),
        ] = 0.01,
        host_type: Annotated[
            StrictStr | None,
            Field(description="Optional scope type: story, building, or model. Defaults to model."),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(description="Required Story or Building target when host_type is story or building."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
    ) -> dict[str, Any]:
        """Align Dragonfly Room2Ds."""
        from garden.dragonfly_core.geometry import align_dragonfly_room2ds as service

        return service(
            garden_root=garden_root,
            lines=lines,
            distance=distance,
            tolerance=tolerance,
            host_type=host_type,
            host_target=host_target,
            model_target=model_target,
        )

    @mcp.tool(
        name="DF_Apply_Energy_Properties",
        description=(
            'Apply narrow SDK-backed Dragonfly Energy properties to a Room2D, Story, or Building '
            'target. Supports Honeybee Energy library ProgramType and ConstructionSet '
            'identifiers. For whole buildings, pass the Building target once; the service uses '
            'Dragonfly SDK methods to apply room programs across the building. EnergyPlus '
            'simulation remains a downstream workflow after Dragonfly-to-Honeybee conversion.'
        ),
        tags={"dragonfly", "energy", "properties", "edit", "program-type", "construction-set"},
        timeout=20,
    )
    def apply_dragonfly_energy_properties(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Required Dragonfly Room2D, Story, or Building target. Prefer a Building target '
                    'for applying the same ProgramType to all Room2Ds in a building.'
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
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
                    'Optional Honeybee Energy ConstructionSet library identifier from '
                    'EP_Search_Energy_Library_Objects.'
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Apply Dragonfly Energy properties."""
        from garden.dragonfly_core.properties import apply_dragonfly_energy_properties as service

        return service(
            garden_root=garden_root,
            host_target=host_target,
            model_target=model_target,
            program_type_identifier=program_type_identifier,
            construction_set_identifier=construction_set_identifier,
        )

    @mcp.tool(
        name="DF_Apply_Radiance_Properties",
        description=(
            'Apply narrow SDK-backed Dragonfly Radiance properties to a Room2D, Story, or '
            'Building target. Supports Honeybee Radiance ModifierSet library identifiers and '
            'Dragonfly Radiance grid parameters (room_grid, room_radial_grid, exterior_face_grid, '
            'or exterior_aperture_grid). For a whole building, pass the Building target once; '
            'grid parameters apply to Room2D and Building targets.'
        ),
        tags={"dragonfly", "radiance", "properties", "sensor-grid", "modifier-set", "edit"},
        timeout=20,
    )
    def apply_dragonfly_radiance_properties(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Required Dragonfly Room2D, Story, or Building target (grid parameters apply to '
                    'Room2D and Building targets).'
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
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
                    'Optional grid parameter type: room_grid, room_radial_grid, exterior_face_grid, '
                    'or exterior_aperture_grid.'
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
        from garden.dragonfly_core.properties import apply_dragonfly_radiance_properties as service

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

    @mcp.tool(
        name="DF_Apply_Shading_Parameter",
        description=(
            'Apply a Dragonfly ShadingParameter artifact using public Dragonfly SDK '
            'set_outdoor_shading_parameters methods. Supports Room2D, Story, Building, and Model '
            'outdoor application. Returns target, report, and the updated Dragonfly host context.'
        ),
        tags={"dragonfly", "shading", "parameter", "edit", "overhang"},
        timeout=20,
    )
    def apply_dragonfly_shading_parameter(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        shading_parameter: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required parameter dict from DF_Create_Shading_Parameter['parameter'] or "
                    "['shading_parameter']."
                )
            ),
        ],
        host_type: Annotated[
            str | None,
            Field(description="Host type: room2d, story, building, or model."),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(description="Required Dragonfly Room2D, Story, or Building target unless host_type is model."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        application_scope: Annotated[
            str,
            Field(description="Only all_outdoor is supported by the stable Dragonfly SDK shading set methods."),
        ] = "all_outdoor",
    ) -> dict[str, Any]:
        """Apply a Dragonfly ShadingParameter."""
        from garden.dragonfly_core.envelope_parameters import (
            apply_dragonfly_shading_parameter as service,
        )

        return service(
            garden_root=garden_root,
            shading_parameter=shading_parameter,
            host_type=host_type,
            host_target=host_target,
            model_target=model_target,
            application_scope=application_scope,
        )

    @mcp.tool(
        name="DF_Apply_Window_Parameter",
        description=(
            "Apply a Dragonfly WindowParameter artifact using public Dragonfly SDK set "
            "methods. Supports Room2D all outdoor, Room2D segment, Story outdoor, "
            "Building outdoor, and Model outdoor application. Pass host_type explicitly "
            "as room2d, story, building, or model. Returns target, report, and the "
            "updated Dragonfly host context; Honeybee Apertures appear only after "
            "Dragonfly-to-Honeybee conversion."
        ),
        tags={"dragonfly", "window", "parameter", "edit", "aperture-ratio"},
        timeout=20,
    )
    def apply_dragonfly_window_parameter(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        window_parameter: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Required parameter dict from DF_Create_Window_Parameter['parameter'] or "
                    "['window_parameter']."
                )
            ),
        ] = None,
        host_type: Annotated[
            str | None,
            Field(description="Host type: room2d, story, building, or model."),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(description="Required Dragonfly Room2D, Story, or Building target unless host_type is model."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        application_scope: Annotated[
            str,
            Field(description="Application scope: all_outdoor or segment. Segment is Room2D-only."),
        ] = "all_outdoor",
        segment_index: Annotated[
            int | None,
            Field(description="Required Room2D segment index when application_scope is segment."),
        ] = None,
    ) -> dict[str, Any]:
        """Apply a Dragonfly WindowParameter."""
        from garden.dragonfly_core.envelope_parameters import (
            apply_dragonfly_window_parameter as service,
        )

        if window_parameter is None:
            raise ValueError('DF_Apply_Window_Parameter requires window_parameter.')
        return service(
            garden_root=garden_root,
            window_parameter=window_parameter,
            host_type=host_type,
            host_target=host_target,
            model_target=model_target,
            application_scope=application_scope,
            segment_index=segment_index,
        )

    @mcp.tool(
        name="DF_Clean_Room2D_Geometry",
        description=(
            "Clean a model-embedded Dragonfly Room2D boundary using explicit SDK "
            "methods: remove_duplicate_vertices, remove_colinear_vertices, and "
            "optionally remove_short_segments. Saves the updated DFJSON and returns "
            "summary_view, report, and segment-count diagnostics; adjacency solving "
            "and validation use separate Dragonfly tools."
        ),
        tags={"dragonfly", "room2d", "geometry", "cleanup", "repair"},
        timeout=30,
    )
    def clean_dragonfly_room2d_geometry(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        room2d_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Required Dragonfly Room2D target or identifier in the selected Story. "
                    "Prefer room2d_target when available."
                )
            ),
        ] = None,
        room_identifier: Annotated[
            str | None,
            Field(
                description=(
                    "Optional model-embedded Room2D identifier. Use this when the "
                    "room target is not available but the room name is known."
                )
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        remove_duplicate_vertices: Annotated[
            bool,
            Field(description="Whether to call Dragonfly Room2D.remove_duplicate_vertices on the selected Room2D."),
        ] = True,
        remove_colinear_vertices: Annotated[
            bool,
            Field(description="Whether to call Room2D.remove_colinear_vertices."),
        ] = True,
        remove_short_segments_distance: Annotated[
            float | None,
            Field(description="Optional distance for Room2D.remove_short_segments. Leave null to skip."),
        ] = None,
        tolerance: Annotated[
            float,
            Field(description="Tolerance passed to duplicate/colinear cleanup methods."),
        ] = 0.01,
        preserve_wall_props: Annotated[
            bool,
            Field(description="Whether Room2D.remove_colinear_vertices preserves wall properties."),
        ] = True,
        angle_tolerance: Annotated[
            float,
            Field(description="Angle tolerance passed to Room2D.remove_short_segments."),
        ] = 1.0,
    ) -> dict[str, Any]:
        """Clean Dragonfly Room2D geometry."""
        from garden.dragonfly_core.geometry import clean_dragonfly_room2d_geometry as service

        return service(
            garden_root=garden_root,
            room2d_target=room2d_target,
            room_identifier=room_identifier,
            model_target=model_target,
            remove_duplicate_vertices=remove_duplicate_vertices,
            remove_colinear_vertices=remove_colinear_vertices,
            remove_short_segments_distance=remove_short_segments_distance,
            tolerance=tolerance,
            preserve_wall_props=preserve_wall_props,
            angle_tolerance=angle_tolerance,
        )

    @mcp.tool(
        name="DF_Building",
        description=(
            'Create a Dragonfly Building in a Garden Dragonfly model from Dragonfly Story targets '
            'and save the DFJSON model. The service uses Dragonfly SDK '
            'Building.separate_top_bottom_floors before saving so repeated Story multipliers '
            'become explicit ground, typical, and top Stories where needed. Use this after '
            'DF_Room2D and DF_Story when assembling a building story room2d model. Returns '
            'target, summary_view, persistence_receipt, and report.'
        ),
        tags={"dragonfly", "building", "story", "room2d", "author", "model", "assembly"},
        timeout=20,
    )
    def create_dragonfly_building(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        story_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Required list of Dragonfly Story targets. Use story_target "
                    'values returned by DF_Story or target values '
                    "from a Story search."
                )
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Dragonfly Building identifier. If omitted, display_name "
                    "is converted to a stable identifier."
                )
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        sort_stories: Annotated[
            bool,
            Field(description="Whether to sort Dragonfly Stories by floor height before saving the Building."),
        ] = True,
        display_name: Annotated[
            str | None,
            Field(
                description=(
                    "Optional user-facing Building name. If identifier is omitted, "
                    "spaces are converted to underscores for the identifier."
                )
            ),
        ] = None,
        return_object_dict: Annotated[
            bool | None,
            Field(
                description=(
                    "Optional low-cost output control. Set false to omit the full "
                    "Building object_dict while keeping targets, summary, receipt, "
                    "and report."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Building."""
        from garden.dragonfly_core.creation import create_dragonfly_building as service

        result = service(
            garden_root=garden_root,
            identifier=identifier,
            story_targets=story_targets,
            model_target=model_target,
            sort_stories=sort_stories,
            display_name=display_name,
        )
        if return_object_dict is False:
            result.pop("object_dict", None)
        return result

    @mcp.tool(
        name="DF_Building_From_Footprint",
        description=(
            'Create a Dragonfly Building from explicit footprint point loops and floor-to-floor '
            'heights.'
        ),
        tags={"dragonfly", "building", "footprint", "geometry", "author"},
        timeout=60,
    )
    def create_dragonfly_building_from_footprint(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        identifier: Annotated[
            str,
            Field(description="Dragonfly Building identifier or natural name."),
        ],
        footprints: Annotated[
            list[list[list[float]]],
            Field(description="Footprint point loops as [[[x, y], ...], ...]."),
        ],
        floor_to_floor_heights: Annotated[
            list[float],
            Field(description="Floor-to-floor heights for each intended floor."),
        ],
        perimeter_offset: Annotated[
            float | None,
            Field(description="Optional perimeter/core offset passed to Dragonfly SDK."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target; defaults to base_dragonfly_model."),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Building display name."),
        ] = None,
        tolerance: Annotated[
            float | None,
            Field(description="Optional Dragonfly geometry tolerance."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Building from footprint point loops."""
        from garden.dragonfly_core.creation import (
            create_dragonfly_building_from_footprint as service,
        )

        return service(
            garden_root=garden_root,
            identifier=identifier,
            footprints=footprints,
            floor_to_floor_heights=floor_to_floor_heights,
            perimeter_offset=perimeter_offset,
            model_target=model_target,
            display_name=display_name,
            tolerance=tolerance,
        )

    @mcp.tool(
        name="DF_Context_Shade",
        description=(
            'Create a Dragonfly ContextShade in a Garden from one or more 3D shade faces, save it '
            'into the Dragonfly model, and return a context_shade target for search, UWG '
            'vegetation properties, and model summaries. Use this for surrounding buildings, tree '
            'canopy, or other detached urban context geometry.'
        ),
        tags={"dragonfly", "context-shade", "context", "shade", "author"},
        timeout=20,
    )
    def create_dragonfly_context_shade(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        identifier: Annotated[
            str,
            Field(description="Required Dragonfly ContextShade identifier for the saved context object."),
        ],
        geometry: Annotated[
            Any,
            Field(
                description=(
                    "Required ContextShade face geometry as a list of 3D face "
                    "boundaries: [[[x, y, z], ...], ...], or Face3D-style "
                    "dicts with vertices/boundary. Each face needs at least "
                    "three points."
                )
            ),
        ] = None,
        vertices: Annotated[
            Any,
            Field(
                description=(
                    "Optional natural footprint/boundary vertices. Pass 3D vertices "
                    "for one shade face, or 2D vertices with height to extrude a "
                    "simple urban-context mass."
                )
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        is_detached: Annotated[
            bool,
            Field(description="Whether this ContextShade is detached from buildings."),
        ] = True,
        x_dim: Annotated[
            float | None,
            Field(description="Optional rectangular context footprint width."),
        ] = None,
        y_dim: Annotated[
            float | None,
            Field(description="Optional rectangular context footprint depth."),
        ] = None,
        height: Annotated[
            float | None,
            Field(description="Optional rectangular context height."),
        ] = None,
        origin: Annotated[
            list[float] | None,
            Field(description="Optional rectangular context origin [x, y] or [x, y, z]."),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing ContextShade display name."),
        ] = None,
        context_shade_type: Annotated[
            str | None,
            Field(description="Optional natural context type, such as tree or building."),
        ] = None,
        is_vegetation: Annotated[
            bool | None,
            Field(description="Optional UWG vegetation flag when UWG properties are available."),
        ] = None,
        cen_pt: Annotated[
            list[float] | None,
            Field(description="Optional natural center point [x, y] or [x, y, z]."),
        ] = None,
        radius: Annotated[
            float | None,
            Field(description="Optional natural radius used with cen_pt for tree/building shades."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly ContextShade."""
        from garden.dragonfly_core.creation import create_dragonfly_context_shade as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            geometry=geometry,
            vertices=vertices,
            model_target=model_target,
            is_detached=is_detached,
            x_dim=x_dim,
            y_dim=y_dim,
            height=height,
            origin=origin,
            display_name=display_name,
            context_shade_type=context_shade_type,
            is_vegetation=is_vegetation,
            cen_pt=cen_pt,
            radius=radius,
        )

    @mcp.tool(
        name="DF_Model",
        description=(
            'Create an empty Dragonfly model in a Garden and optionally set it as the base '
            'Dragonfly model with set_base. Returns target and model_target for downstream '
            'Dragonfly calls. Add Room2D, Story, and Building objects with the dedicated '
            'Dragonfly authoring tools.'
        ),
        tags={"dragonfly", "model", "author", "garden", "dfjson"},
        timeout=20,
    )
    def create_dragonfly_model(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        identifier: Annotated[
            str,
            Field(
                description=(
                    "Required Dragonfly model identifier or natural project name. "
                    "Spaces and illegal SDK identifier characters are cleaned for "
                    "the stored DFJSON identifier."
                )
            ),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Dragonfly model display name."),
        ] = None,
        units: Annotated[
            str,
            Field(description="Dragonfly model units string, for example Meters."),
        ] = "Meters",
        unit_system: Annotated[
            str | None,
            Field(
                description="Optional natural unit-system selection. Metric maps to Meters; Imperial maps to Feet."
            ),
        ] = None,
        tolerance: Annotated[
            float | None,
            Field(description="Optional model tolerance."),
        ] = None,
        angle_tolerance: Annotated[
            float,
            Field(description="Model angle tolerance."),
        ] = 1.0,
        save_back: Annotated[
            bool,
            Field(description="Whether to save the Dragonfly Model into the Garden and return a Dragonfly model target."),
        ] = True,
        set_base: Annotated[
            bool,
            Field(
                description='Whether to set as the Garden base Dragonfly model.'
            ),
        ] = True,
        include_body: Annotated[
            bool,
            Field(description="Whether to return full model body if not saved."),
        ] = False,
        return_object_dict: Annotated[
            bool | None,
            Field(
                description=(
                    "Optional compact-return flag used across Garden create tools. "
                    "False keeps the default compact model target response; True "
                    "requests the full body only when save_back is false."
                )
            ),
        ] = None,
        latitude: Annotated[
            float | None,
            Field(description="Optional project latitude context saved as model user_data."),
        ] = None,
        longitude: Annotated[
            float | None,
            Field(description="Optional project longitude context saved as model user_data."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Model."""
        from garden.dragonfly_core.creation import create_dragonfly_model as service

        if unit_system is not None:
            normalized_unit_system = unit_system.strip().lower()
            if normalized_unit_system in {"metric", "si"}:
                units = "Meters"
            elif normalized_unit_system in {"imperial", "ip"}:
                units = "Feet"
            else:
                units = unit_system
        if return_object_dict is not None:
            include_body = bool(return_object_dict)
        return service(
            garden_root=garden_root,
            identifier=identifier,
            display_name=display_name,
            units=units,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
            save_back=save_back,
            set_base=set_base,
            include_body=include_body,
            latitude=latitude,
            longitude=longitude,
        )

    @mcp.tool(
        name="DF_Room2D",
        description=(
            'Create a Dragonfly Room2D draft object in a Garden from 2D floor vertices. Use '
            'Room2D targets with DF_Story, then DF_Building, when assembling a building story '
            'room2d model. Returns target, summary_view, persistence_receipt, and report.'
        ),
        tags={"dragonfly", "room2d", "story", "building", "geometry", "author", "floor-plate"},
        timeout=20,
    )
    def create_dragonfly_room2d(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        identifier: Annotated[
            str,
            Field(description="Required Dragonfly Room2D identifier for the saved floor-plate object."),
        ],
        display_name: Annotated[
            str | None,
            Field(
                description=(
                    "Optional human-readable Room2D display name. Use identifier "
                    "for the stable object id."
                )
            ),
        ] = None,
        floor_height: Annotated[
            float | None,
            Field(
                description=(
                    "Floor elevation for the Room2D. If omitted, the service "
                    "infers it from story_number."
                )
            ),
        ] = None,
        vertices: Annotated[
            Any,
            Field(
                description=(
                    "2D floor boundary vertices as [[x, y], ...] in order. "
                    "3D points are accepted and normalized to their [x, y] "
                    "coordinates. For a simple rectangle, omit vertices and "
                    "pass x_dim and y_dim."
                )
            ),
        ] = None,
        floor_to_ceiling_height: Annotated[
            float | None,
            Field(
                description=(
                    "Room2D floor-to-ceiling height. For rectangular input, "
                    "height is also accepted as a short natural-language field. "
                    "Defaults to 3.0 when omitted."
                )
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        is_ground_contact: Annotated[
            bool,
            Field(description="Whether the Room2D floor is ground-contact."),
        ] = False,
        is_top_exposed: Annotated[
            bool,
            Field(description="Whether the Room2D ceiling is top-exposed."),
        ] = False,
        x_dim: Annotated[
            float | None,
            Field(description="Optional rectangle width in the x direction."),
        ] = None,
        y_dim: Annotated[
            float | None,
            Field(description="Optional rectangle depth in the y direction."),
        ] = None,
        origin: Annotated[
            list[float] | None,
            Field(description="Optional rectangle origin [x, y]. Defaults to [0, 0]."),
        ] = None,
        height: Annotated[
            float | None,
            Field(
                description="Optional short field for floor-to-ceiling height in rectangular mode."
            ),
        ] = None,
        story_number: Annotated[
            int | None,
            Field(
                description=(
                    "Optional story number. The geometry service "
                    "does not need it when floor_height is provided."
                )
            ),
        ] = None,
        return_object_dict: Annotated[
            bool | None,
            Field(
                description=(
                    "Optional low-cost output control. Set false to omit the full "
                    "Room2D object_dict while keeping targets, summary, receipt, "
                    "and report."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Room2D."""
        from garden.dragonfly_core.creation import create_dragonfly_room2d as service

        result = service(
            garden_root=garden_root,
            identifier=identifier,
            display_name=display_name,
            vertices=vertices,
            floor_height=floor_height,
            floor_to_ceiling_height=floor_to_ceiling_height,
            model_target=model_target,
            is_ground_contact=is_ground_contact,
            is_top_exposed=is_top_exposed,
            x_dim=x_dim,
            y_dim=y_dim,
            origin=origin,
            height=height,
            story_number=story_number,
        )
        if return_object_dict is False:
            result.pop("object_dict", None)
        return result

    @mcp.tool(
        name="DF_Create_Shading_Parameter",
        description=(
            'Create a compact SDK-backed Dragonfly ShadingParameter artifact for outdoor wall '
            'application. Supports parameter_type overhang and extruded_border only. Returns the '
            'compact artifact as parameter, shading_parameter, target, and object_dict.'
        ),
        tags={"dragonfly", "shading", "parameter", "author", "overhang", "extruded-border"},
        timeout=20,
    )
    def create_dragonfly_shading_parameter(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        parameter_type: Annotated[
            str,
            Field(description="Required Dragonfly shading parameter type: overhang or extruded_border."),
        ],
        depth: Annotated[
            float,
            Field(description="Depth for the Dragonfly overhang or extruded-border shading parameter."),
        ],
        angle: Annotated[
            float,
            Field(description="Overhang angle in degrees. Ignored by extruded_border."),
        ] = 0,
    ) -> dict[str, Any]:
        """Create a Dragonfly ShadingParameter artifact."""
        from garden.dragonfly_core.envelope_parameters import (
            create_dragonfly_shading_parameter as service,
        )

        return service(
            garden_root=garden_root,
            parameter_type=parameter_type,
            depth=depth,
            angle=angle,
        )

    @mcp.tool(
        name="DF_Story",
        description=(
            'Create a Dragonfly Story draft object from Dragonfly Room2D targets. Pass identifier '
            'or display_name; attach the returned Story target to a Building with DF_Building.'
        ),
        tags={"dragonfly", "story", "room2d", "author", "assembly"},
        timeout=20,
    )
    def create_dragonfly_story(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        room2d_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    'Required list of Dragonfly Room2D targets from DF_Room2D or DF_Search_Objects.'
                )
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Dragonfly Story identifier. If omitted, display_name "
                    "is converted to a stable identifier."
                )
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        floor_to_floor_height: Annotated[
            float | None,
            Field(description="Optional Story floor-to-floor height."),
        ] = None,
        floor_height: Annotated[
            float | None,
            Field(description="Optional Story floor height."),
        ] = None,
        multiplier: Annotated[
            int,
            Field(description="Dragonfly Story multiplier for repeated floors."),
        ] = 1,
        story_type: Annotated[
            str,
            Field(
                description=(
                    "Dragonfly Story type; values are case-sensitive. Use Standard for ordinary ground, "
                    "middle, top, or typical floors. Only use CeilingPlenum or "
                    "FloorPlenum for plenum stories."
                )
            ),
        ] = "Standard",
        display_name: Annotated[
            str | None,
            Field(
                description=(
                    "Optional user-facing Story name. If identifier is omitted, "
                    "spaces are converted to underscores for the identifier."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Story."""
        from garden.dragonfly_core.creation import create_dragonfly_story as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            room2d_targets=room2d_targets,
            model_target=model_target,
            floor_to_floor_height=floor_to_floor_height,
            floor_height=floor_height,
            multiplier=multiplier,
            story_type=story_type,
            display_name=display_name,
        )

    @mcp.tool(
        name="DF_Create_Window_Parameter",
        description=(
            'Create a compact SDK-backed Dragonfly WindowParameter artifact for Room2D, Story, '
            'Building, or Model outdoor wall application. Supports parameter_type '
            'simple_window_ratio and repeating_window_ratio only. Returns the compact artifact as '
            'parameter, window_parameter, target, and object_dict.'
        ),
        tags={"dragonfly", "window", "parameter", "author", "aperture-ratio", "wwr"},
        timeout=20,
    )
    def create_dragonfly_window_parameter(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        parameter_type: Annotated[
            str,
            Field(
                description="Required Dragonfly window parameter type: simple_window_ratio or repeating_window_ratio."
            ),
        ],
        window_ratio: Annotated[
            float | None,
            Field(description="Window-to-wall ratio used by the Dragonfly WindowParameter."),
        ] = None,
        rect_split: Annotated[
            bool,
            Field(description="SimpleWindowRatio rect_split flag."),
        ] = True,
        window_height: Annotated[
            float | None,
            Field(description="Required horizontal window width for repeating_window_ratio."),
        ] = None,
        sill_height: Annotated[
            float | None,
            Field(description="Required window height for repeating_window_ratio."),
        ] = None,
        horizontal_separation: Annotated[
            float | None,
            Field(description="Required horizontal separation for repeating_window_ratio."),
        ] = None,
        vertical_separation: Annotated[
            float,
            Field(description="Optional vertical separation for repeating_window_ratio."),
        ] = 0,
    ) -> dict[str, Any]:
        """Create a Dragonfly WindowParameter artifact."""
        from garden.dragonfly_core.envelope_parameters import (
            create_dragonfly_window_parameter as service,
        )

        if window_ratio is None:
            raise ValueError('DF_Create_Window_Parameter requires window_ratio.')
        return service(
            garden_root=garden_root,
            parameter_type=parameter_type,
            window_ratio=window_ratio,
            rect_split=rect_split,
            window_height=window_height,
            sill_height=sill_height,
            horizontal_separation=horizontal_separation,
            vertical_separation=vertical_separation,
        )

    @mcp.tool(
        name="DF_Building_To_Visualization_Set",
        description=(
            "Create a compact VisualizationSet preview for one Dragonfly Building "
            "target. Pass a Dragonfly object target from DF_Search_Objects or a "
            "creation/edit tool. Set return_visualization_set=false to save the "
            "preview and return visualization_set_target for shared exporters like "
            "LB_Set_To_SVG or LB_Set_To_VTKJS. Returns "
            "summary_view, report, and optionally the VisualizationSet body."
        ),
        tags={"dragonfly", "building", "visualization-set", "preview"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def dragonfly_building_to_visualization_set(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json.")],
        target: Annotated[dict[str, Any], Field(description="Dragonfly Building object target.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
        name: Annotated[str | None, Field(description="Optional VisualizationSet identifier/name.")] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Whether to return the full VisualizationSet body. Set false to save and return visualization_set_target."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Dragonfly Building VisualizationSet."""
        from garden.dragonfly_core.display import (
            dragonfly_building_to_visualization_set as service,
        )

        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="DF_Context_Shade_To_Visualization_Set",
        description=(
            "Create a compact VisualizationSet preview for one Dragonfly ContextShade "
            "target. Use ContextShade targets from DF_Search_Objects or creation tools. "
            "Set return_visualization_set=false to save the preview and return "
            "visualization_set_target for shared exporters. Returns summary_view, report, "
            "and optionally the VisualizationSet body."
        ),
        tags={"dragonfly", "context-shade", "visualization-set", "preview"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def dragonfly_context_shade_to_visualization_set(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json.")],
        target: Annotated[dict[str, Any], Field(description="Dragonfly ContextShade object target.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
        name: Annotated[str | None, Field(description="Optional VisualizationSet identifier/name.")] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Whether to return the full VisualizationSet body. Set false to save and return visualization_set_target."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Dragonfly ContextShade VisualizationSet."""
        from garden.dragonfly_core.display import (
            dragonfly_context_shade_to_visualization_set as service,
        )

        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="DF_Model_Envelope_Edges_To_Visualization_Set",
        description=(
            'Create a Ladybug Display VisualizationSet showing Dragonfly model envelope edges '
            'using Dragonfly Display model_envelope_edges_to_vis_set. If Web View mode is active, '
            'this tool refreshes the demo panel; call LB_Set_To_VTKJS only when the user asks for '
            'a saved vtk.js asset. If the SDK edge view is unavailable for the model geometry, '
            'this tool returns report.status=degraded and a wireframe model VisualizationSet '
            'target.'
        ),
        tags={"dragonfly", "visualization-set", "geometry", "visualize", "preview"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def dragonfly_model_envelope_edges_to_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        coplanar_type: Annotated[
            str,
            Field(description="Dragonfly Display coplanar_type: None, FloorPlatesOnly, or All."),
        ] = "FloorPlatesOnly",
        mullion_thickness: Annotated[
            float | None,
            Field(description="Optional mullion thickness threshold."),
        ] = None,
        reset_coordinates: Annotated[
            bool,
            Field(description="Whether to reset model coordinates around the origin."),
        ] = False,
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet identifier/name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Whether to return the VisualizationSet body. False saves and returns a compact visualization_set_target for export tools."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Dragonfly envelope-edge VisualizationSet."""
        from garden.dragonfly_core.display import (
            dragonfly_model_envelope_edges_to_visualization_set as service,
        )

        return service(
            garden_root=garden_root,
            model_target=model_target,
            coplanar_type=coplanar_type,
            mullion_thickness=mullion_thickness,
            reset_coordinates=reset_coordinates,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="DF_Model_To_Honeybee",
        description=(
            "Convert a Garden Dragonfly model into one or more Honeybee HBJSON models "
            "using Dragonfly SDK Model.to_honeybee. Saves Honeybee models into the "
            "Garden without changing the base Dragonfly model. Returns model_target "
            "entries and report for downstream Honeybee Energy or Radiance tools; "
            "EnergyPlus simulation is a later Energy workflow."
        ),
        tags={"dragonfly", "honeybee", "model", "convert", "export"},
        timeout=60,
    )
    def dragonfly_model_to_honeybee(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        object_per_model: Annotated[
            str,
            Field(description="Dragonfly to_honeybee object_per_model option: Building, Story, or District."),
        ] = "Building",
        shade_distance: Annotated[
            float | None,
            Field(description="Optional Dragonfly shade_distance."),
        ] = None,
        use_multiplier: Annotated[
            bool,
            Field(description="Whether to pass Dragonfly story multipliers to Honeybee."),
        ] = True,
        exclude_plenums: Annotated[
            bool,
            Field(description="Whether to exclude Dragonfly plenum Room2Ds."),
        ] = False,
        cap: Annotated[
            bool,
            Field(description="Whether to cap building shade representations."),
        ] = False,
        solve_ceiling_adjacencies: Annotated[
            bool,
            Field(description="Whether to solve interior story ceiling adjacencies."),
        ] = False,
        merge_method: Annotated[
            str | None,
            Field(description="Optional Dragonfly merge_method such as Zones or Stories."),
        ] = None,
        tolerance: Annotated[
            float | None,
            Field(description="Optional conversion tolerance. Defaults to the Dragonfly model tolerance."),
        ] = None,
        enforce_adj: Annotated[
            bool,
            Field(description="Whether invalid Room2D adjacencies should raise during conversion."),
        ] = True,
        enforce_solid: Annotated[
            bool,
            Field(description="Whether translated Honeybee Rooms must be solid."),
        ] = True,
        set_base: Annotated[
            bool,
            Field(description="Whether the first converted Honeybee model becomes the base Honeybee model."),
        ] = False,
    ) -> dict[str, Any]:
        """Convert a Dragonfly Model to Honeybee Models."""
        from garden.dragonfly_core.conversion import dragonfly_model_to_honeybee as service

        return service(
            garden_root=garden_root,
            model_target=model_target,
            object_per_model=object_per_model,
            shade_distance=shade_distance,
            use_multiplier=use_multiplier,
            exclude_plenums=exclude_plenums,
            cap=cap,
            solve_ceiling_adjacencies=solve_ceiling_adjacencies,
            merge_method=merge_method,
            tolerance=tolerance,
            enforce_adj=enforce_adj,
            enforce_solid=enforce_solid,
            set_base=set_base,
        )

    @mcp.tool(
        name="DF_Model_To_Visualization_Set",
        description=(
            'Create a Ladybug Display VisualizationSet from a Garden Dragonfly model using '
            'Dragonfly Display for web 3D, FastMCP App viewer, and geometry asset workflows. Can '
            'return the VisualizationSet body or save it as a Garden visualization_set target '
            'with return_visualization_set=false. If Web View mode is active, this tool refreshes '
            'the demo panel; call LB_Set_To_VTKJS only when the user asks for a saved vtk.js '
            'asset. Grasshopper quick/all/floors/wireframe visualize components are consolidated '
            'through view_mode here. Read-only visualization conversion.'
        ),
        tags={"dragonfly", "visualization-set", "model", "visualize", "preview"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def dragonfly_model_to_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        view_mode: Annotated[
            str | None,
            Field(
                description=(
                    "Optional consolidated Dragonfly-Grasshopper visualize mode: "
                    "quick, all, floors, wireframe, or custom. Use custom or omit "
                    "to control detailed Display options directly."
                )
            ),
        ] = None,
        use_multiplier: Annotated[
            bool,
            Field(description="Whether to display Dragonfly story multipliers."),
        ] = True,
        exclude_plenums: Annotated[
            bool,
            Field(description="Whether to exclude Dragonfly plenum Room2Ds."),
        ] = False,
        solve_ceiling_adjacencies: Annotated[
            bool,
            Field(description="Whether to solve interior story ceiling adjacencies."),
        ] = False,
        merge_method: Annotated[
            str,
            Field(description="Dragonfly Display merge_method. Use the string None for no merging."),
        ] = "None",
        color_by: Annotated[
            str | None,
            Field(description="Dragonfly Display color_by value: type, boundary_condition, or None."),
        ] = "type",
        include_wireframe: Annotated[
            bool,
            Field(description="Whether to include model wireframe geometry."),
        ] = True,
        use_mesh: Annotated[
            bool,
            Field(description="Whether color geometry should use DisplayMesh3D."),
        ] = True,
        hide_color_by: Annotated[
            bool,
            Field(description="Whether color-by geometry is hidden by default."),
        ] = False,
        grid_display_mode: Annotated[
            str,
            Field(description="SensorGrid display mode for Dragonfly Display."),
        ] = "Default",
        hide_grid: Annotated[
            bool,
            Field(description="Whether SensorGrid geometry is hidden by default."),
        ] = False,
        reset_coordinates: Annotated[
            bool,
            Field(description="Whether to reset model coordinates around the origin."),
        ] = False,
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet identifier/name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Whether to return the full VisualizationSet body. Set false to save and return a compact visualization_set_target for export tools."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Dragonfly model VisualizationSet."""
        from garden.dragonfly_core.display import (
            dragonfly_model_to_visualization_set as service,
        )

        return service(
            garden_root=garden_root,
            model_target=model_target,
            view_mode=view_mode,
            use_multiplier=use_multiplier,
            exclude_plenums=exclude_plenums,
            solve_ceiling_adjacencies=solve_ceiling_adjacencies,
            merge_method=merge_method,
            color_by=color_by,
            include_wireframe=include_wireframe,
            use_mesh=use_mesh,
            hide_color_by=hide_color_by,
            grid_display_mode=grid_display_mode,
            hide_grid=hide_grid,
            reset_coordinates=reset_coordinates,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="DF_Models_To_Comparison_Visualization_Set",
        description=(
            "Create a Ladybug Display comparison VisualizationSet for two Garden "
            "Dragonfly models using Dragonfly Display model_comparison_to_vis_set. If "
            "Web View mode is active, this tool refreshes the demo panel; call "
            "LB_Set_To_VTKJS only when the user asks for a saved vtk.js asset. "
            "Returns visualization_set_target when saved and leaves both Dragonfly "
            "source models unchanged."
        ),
        tags={"dragonfly", "visualization-set", "compare", "visualize", "preview"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def dragonfly_models_to_comparison_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        base_model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Required Dragonfly Model target for the base comparison model."),
        ] = None,
        incoming_model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Required Dragonfly Model target for the incoming comparison model."),
        ] = None,
        use_multiplier: Annotated[
            bool,
            Field(description="Whether to display Dragonfly story multipliers."),
        ] = True,
        exclude_plenums: Annotated[
            bool,
            Field(description="Whether to exclude Dragonfly plenum Room2Ds."),
        ] = False,
        solve_ceiling_adjacencies: Annotated[
            bool,
            Field(description="Whether to solve interior story ceiling adjacencies."),
        ] = False,
        merge_method: Annotated[
            str,
            Field(description="Dragonfly Display merge_method. Use the string None for no merging."),
        ] = "None",
        reset_coordinates: Annotated[
            bool,
            Field(description="Whether to reset model coordinates around the origin."),
        ] = False,
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet identifier/name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Whether to return the VisualizationSet body. False saves and returns a compact visualization_set_target."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Dragonfly comparison VisualizationSet."""
        from garden.dragonfly_core.display import (
            dragonfly_models_to_comparison_visualization_set as service,
        )

        if base_model_target is None or incoming_model_target is None:
            raise ValueError(
                "DF_Models_To_Comparison_Visualization_Set requires "
                "base_model_target and incoming_model_target."
            )
        return service(
            garden_root=garden_root,
            base_model_target=base_model_target,
            incoming_model_target=incoming_model_target,
            use_multiplier=use_multiplier,
            exclude_plenums=exclude_plenums,
            solve_ceiling_adjacencies=solve_ceiling_adjacencies,
            merge_method=merge_method,
            reset_coordinates=reset_coordinates,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="DF_Room2D_Attribute_To_Visualization_Set",
        description=(
            "Create a compact VisualizationSet preview from DF_Room2Ds_By_Attribute "
            "output. Use this after Room2D attribute screening to visually inspect the "
            "matched Room2Ds and groups. Set return_visualization_set=false to save the "
            "preview and return visualization_set_target for shared exporters. Returns "
            "summary_view with attribute/group metadata, report, and optionally the "
            "VisualizationSet body."
        ),
        tags={"dragonfly", "room2d", "attribute", "visualization-set", "preview"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def dragonfly_room2d_attribute_to_visualization_set(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json.")],
        attribute_result: Annotated[
            dict[str, Any],
            Field(description="Result dictionary returned by DF_Room2Ds_By_Attribute, including selection and groups."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
        name: Annotated[str | None, Field(description="Optional VisualizationSet identifier/name.")] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Whether to return the full VisualizationSet body. Set false to save and return visualization_set_target."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Dragonfly Room2D attribute VisualizationSet."""
        from garden.dragonfly_core.display import (
            dragonfly_room2d_attribute_to_visualization_set as service,
        )

        return service(
            garden_root=garden_root,
            attribute_result=attribute_result,
            model_target=model_target,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="DF_Room2D_To_Visualization_Set",
        description=(
            "Create a compact VisualizationSet preview for one Dragonfly Room2D "
            "target. Use Room2D targets from DF_Search_Objects, DF_Room2Ds_By_Attribute, "
            "or creation tools. Set return_visualization_set=false to save the preview "
            "and return visualization_set_target for shared exporters. Returns "
            "summary_view, report, and optionally the VisualizationSet body."
        ),
        tags={"dragonfly", "room2d", "visualization-set", "preview"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def dragonfly_room2d_to_visualization_set(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json.")],
        target: Annotated[dict[str, Any], Field(description="Dragonfly Room2D object target.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
        name: Annotated[str | None, Field(description="Optional VisualizationSet identifier/name.")] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Whether to return the full VisualizationSet body. Set false to save and return visualization_set_target."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Dragonfly Room2D VisualizationSet."""
        from garden.dragonfly_core.display import dragonfly_room2d_to_visualization_set as service

        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="DF_Selection_To_Visualization_Set",
        description=(
            "Create a compact VisualizationSet preview from a dragonfly_selection "
            "returned by DF_Search_Objects or DF_Room2Ds_By_Attribute. This is the "
            "preferred bridge from search/list screening into visual review. Set "
            "return_visualization_set=false to save the preview and return "
            "visualization_set_target for shared exporters. Returns summary_view, "
            "report, and optionally the VisualizationSet body."
        ),
        tags={"dragonfly", "selection", "visualization-set", "preview"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def dragonfly_selection_to_visualization_set(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json.")],
        selection: Annotated[dict[str, Any], Field(description="dragonfly_selection dictionary returned by Dragonfly search/list tools.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
        name: Annotated[str | None, Field(description="Optional VisualizationSet identifier/name.")] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Whether to return the full VisualizationSet body. Set false to save and return visualization_set_target."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Dragonfly selection VisualizationSet."""
        from garden.dragonfly_core.display import dragonfly_selection_to_visualization_set as service

        return service(
            garden_root=garden_root,
            selection=selection,
            model_target=model_target,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="DF_Story_To_Visualization_Set",
        description=(
            "Create a compact VisualizationSet preview for one Dragonfly Story target. "
            "Use Story targets from DF_Search_Objects or Dragonfly authoring tools. "
            "Set return_visualization_set=false to save the preview and return "
            "visualization_set_target for shared exporters. Returns summary_view, "
            "report, and optionally the VisualizationSet body."
        ),
        tags={"dragonfly", "story", "visualization-set", "preview"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def dragonfly_story_to_visualization_set(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json.")],
        target: Annotated[dict[str, Any], Field(description="Dragonfly Story object target.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
        name: Annotated[str | None, Field(description="Optional VisualizationSet identifier/name.")] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Whether to return the full VisualizationSet body. Set false to save and return visualization_set_target."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Dragonfly Story VisualizationSet."""
        from garden.dragonfly_core.display import dragonfly_story_to_visualization_set as service

        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="DF_Edit_Building",
        description=(
            'Edit a model-embedded Dragonfly Building using public Dragonfly SDK '
            'properties/methods. Supports display_name and sort_stories. Returns target, '
            'summary_view, and report for the updated Dragonfly model context.'
        ),
        tags={"dragonfly", "building", "edit", "model", "metadata"},
        timeout=20,
    )
    def edit_dragonfly_building(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        building_identifier: Annotated[
            str,
            Field(description="Identifier of the existing Dragonfly Building inside the selected Dragonfly Model."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional Building display name."),
        ] = None,
        sort_stories: Annotated[
            bool,
            Field(description="Whether to run Dragonfly Building.sort_stories after edits."),
        ] = False,
    ) -> dict[str, Any]:
        """Edit a Dragonfly Building."""
        from garden.dragonfly_core.editing import edit_dragonfly_building as service

        return service(
            garden_root=garden_root,
            building_identifier=building_identifier,
            model_target=model_target,
            display_name=display_name,
            sort_stories=sort_stories,
        )

    @mcp.tool(
        name="DF_Edit_Model",
        description=(
            'Edit Dragonfly Model metadata using public Dragonfly SDK properties. Supports '
            'display_name, units, tolerance, and angle_tolerance (to author geometry, create '
            'Story objects from Room2D targets and Buildings from Story targets). Returns the '
            'updated Dragonfly model target and summary.'
        ),
        tags={"dragonfly", "model", "edit", "summary", "metadata", "dfjson"},
        timeout=20,
    )
    def edit_dragonfly_model(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        display_name: Annotated[
            str | None, Field(description="Optional Dragonfly Model display name saved on the Garden model.")
        ] = None,
        units: Annotated[
            str | None,
            Field(description="Optional Dragonfly Model units value accepted by the SDK, such as Meters."),
        ] = None,
        tolerance: Annotated[
            float | None, Field(description="Optional Dragonfly Model tolerance.")
        ] = None,
        angle_tolerance: Annotated[
            float | None,
            Field(description="Optional Dragonfly Model angle tolerance in degrees."),
        ] = None,
    ) -> dict[str, Any]:
        """Edit a Dragonfly Model."""
        from garden.dragonfly_core.editing import edit_dragonfly_model as service

        return service(
            garden_root=garden_root,
            model_target=model_target,
            display_name=display_name,
            units=units,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
        )

    @mcp.tool(
        name="DF_Edit_Room2D",
        description=(
            "Edit a model-embedded Dragonfly Room2D using public Dragonfly SDK methods. "
            "Prefer room2d_target with a Dragonfly Room2D target and garden_root; "
            "room_identifier is accepted when a target is not available. For floor "
            "boundary edits pass vertices. Use the adjacency and cleanup tools for "
            "those separate geometry operations."
        ),
        tags={"dragonfly", "room2d", "geometry", "edit", "metadata", "floor-plate"},
        timeout=20,
    )
    def edit_dragonfly_room2d(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        room2d_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Required Dragonfly Room2D target or identifier in the selected Story. "
                    "Prefer room2d_target when available."
                )
            ),
        ] = None,
        room_identifier: Annotated[
            str | None,
            Field(
                description=(
                    "Optional natural Room2D identifier. Use when a target is not "
                    "available; model_target or the base Dragonfly model is used."
                )
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        vertices: Annotated[
            list[list[float]] | None,
            Field(description="Optional replacement Dragonfly Room2D floor boundary vertices as [[x, y], ...]."),
        ] = None,
        floor_height: Annotated[
            float | None,
            Field(description="Optional floor height used with replacement vertices."),
        ] = None,
        floor_to_ceiling_height: Annotated[
            float | None,
            Field(description="Optional Room2D floor-to-ceiling height."),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional Room2D display name."),
        ] = None,
        zone: Annotated[
            str | None,
            Field(description="Optional Room2D zone name."),
        ] = None,
        is_ground_contact: Annotated[
            bool | None,
            Field(description="Optional ground-contact flag."),
        ] = None,
        is_top_exposed: Annotated[
            bool | None,
            Field(description="Optional top-exposed flag."),
        ] = None,
        projection_distance: Annotated[
            float,
            Field(description="Projection distance passed to Room2D.replace_floor_geometry."),
        ] = 0,
    ) -> dict[str, Any]:
        """Edit a Dragonfly Room2D."""
        from garden.dragonfly_core.editing import edit_dragonfly_room2d as service

        if room2d_target is None and room_identifier is None:
            raise ValueError('DF_Edit_Room2D requires room2d_target or room_identifier.')
        return service(
            garden_root=garden_root,
            room2d_target=room2d_target,
            room_identifier=room_identifier,
            model_target=model_target,
            vertices=vertices,
            floor_height=floor_height,
            floor_to_ceiling_height=floor_to_ceiling_height,
            display_name=display_name,
            zone=zone,
            is_ground_contact=is_ground_contact,
            is_top_exposed=is_top_exposed,
            projection_distance=projection_distance,
        )

    @mcp.tool(
        name="DF_Edit_Story",
        description=(
            "Edit a model-embedded Dragonfly Story using public Dragonfly SDK "
            "properties. Requires story_target or story_identifier; supports "
            "display_name, floor_height, floor_to_floor_height, and multiplier. "
            "Use solve/reset adjacency tools for Story boundary-condition changes."
        ),
        tags={"dragonfly", "story", "edit", "geometry", "metadata", "multiplier"},
        timeout=20,
    )
    def edit_dragonfly_story(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        story_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Required Dragonfly Story target or story identifier in the selected Garden model. "
                    "Prefer story_target when available."
                )
            ),
        ] = None,
        story_identifier: Annotated[
            str | None,
            Field(description="Optional Dragonfly Story identifier when story_target is not available."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional Story display name."),
        ] = None,
        floor_height: Annotated[
            float | None,
            Field(description="Optional Story floor height."),
        ] = None,
        floor_to_floor_height: Annotated[
            float | None,
            Field(description="Optional Story floor-to-floor height."),
        ] = None,
        multiplier: Annotated[
            int | None,
            Field(description="Optional Dragonfly Story multiplier for repeated floors."),
        ] = None,
    ) -> dict[str, Any]:
        """Edit a Dragonfly Story."""
        from garden.dragonfly_core.editing import edit_dragonfly_story as service

        return service(
            garden_root=garden_root,
            story_target=story_target,
            story_identifier=story_identifier,
            model_target=model_target,
            display_name=display_name,
            floor_height=floor_height,
            floor_to_floor_height=floor_to_floor_height,
            multiplier=multiplier,
        )

    @mcp.tool(
        name="DF_Export_Model_File",
        description=(
            "Export a Garden Dragonfly model to a compact Garden file artifact "
            "as DFJSON or geoJSON. This is the MCP artifact/target form of "
            "Grasshopper Dump Objects and Model To geoJSON; the file body is "
            "not returned unless include_body is true."
        ),
        tags={"dragonfly", "dfjson", "geojson", "export", "artifact", "garden"},
        timeout=60,
    )
    def export_dragonfly_model_file(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        file_type: Annotated[
            str,
            Field(description="File type to export: dfjson or geojson."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target; defaults to base_dragonfly_model."),
        ] = None,
        artifact_name: Annotated[
            str | None,
            Field(description="Optional Garden artifact file stem."),
        ] = None,
        include_body: Annotated[
            bool,
            Field(description="Whether to return the exported file body; false keeps response compact."),
        ] = False,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Required geoJSON location dict when file_type is geojson."),
        ] = None,
        point: Annotated[
            list[float] | None,
            Field(description="Required geoJSON origin point as [x, y] when file_type is geojson."),
        ] = None,
        tolerance: Annotated[
            float | None,
            Field(description="Optional Dragonfly geoJSON export tolerance."),
        ] = None,
    ) -> dict[str, Any]:
        """Export a Dragonfly model file."""
        from garden.dragonfly_core.model_files import export_dragonfly_model_file as service

        return service(
            garden_root=garden_root,
            model_target=model_target,
            file_type=file_type,
            artifact_name=artifact_name,
            include_body=include_body,
            location=location,
            point=point,
            tolerance=tolerance,
        )

    @mcp.tool(
        name="DF_Geometry_Properties",
        description=(
            'Return compact Dragonfly geometry property records for Buildings, Stories, Room2Ds, '
            'and ContextShades in the Garden base Dragonfly model or an explicit Dragonfly '
            'model/object target. Summary/query tool; omits full DFJSON object bodies.'
        ),
        tags={"dragonfly", "geometry", "summary", "query"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_dragonfly_geometry_properties(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Dragonfly object target to summarize instead of the whole model."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target; defaults to base_dragonfly_model."),
        ] = None,
        attributes: Annotated[
            list[str] | None,
            Field(
                description="Optional SDK property names to include, such as floor_area or volume."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Get compact Dragonfly geometry properties."""
        from garden.dragonfly_core.queries import get_dragonfly_geometry_properties as service

        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            attributes=attributes,
        )

    @mcp.tool(
        name="DF_Get_Model_Summary",
        description=(
            'Return compact counts and metadata for the Garden base Dragonfly model or an '
            'explicit Dragonfly model target. Read-only; returns compact counts and metadata.'
        ),
        tags={"dragonfly", "model", "summary", "search", "inventory"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_dragonfly_model_summary(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Get compact Dragonfly model counts and metadata."""
        from garden.dragonfly_core.model_io import get_dragonfly_model_summary as service

        return service(garden_root=garden_root, model_target=model_target)

    @mcp.tool(
        name="DF_Get_Properties_Summary",
        description=(
            "Read compact Dragonfly Energy and Radiance extension property summaries "
            "from a Garden Dragonfly model. Imports the official dragonfly_energy and "
            "dragonfly_radiance extension hooks, then reports Model, Building, Story, "
            "and Room2D properties only when SDK to_dict is available. This is a "
            'read-only summary; use DF_Apply_Energy_Properties for the narrow '
            "SDK-backed Energy ProgramType/ConstructionSet identifier path and "
            "DF_Apply_Radiance_Properties for ModifierSet or SensorGrid setup."
        ),
        tags={"dragonfly", "energy", "radiance", "summary", "properties", "inventory"},
        timeout=20,
    )
    def get_dragonfly_properties_summary(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Read Dragonfly properties summaries."""
        from garden.dragonfly_core.properties import get_dragonfly_properties_summary as service

        return service(garden_root=garden_root, model_target=model_target)

    @mcp.tool(
        name="DF_Convert_Honeybee_Model_To_Dragonfly",
        description=(
            "Convert a Garden Honeybee model to a Dragonfly Model using Dragonfly "
            "Model.from_honeybee, save DFJSON, and optionally set base_dragonfly_model. "
            "Returns target, model_target, and report for downstream Dragonfly tools; "
            "the source Honeybee model remains unchanged."
        ),
        tags={"dragonfly", "honeybee", "model", "convert", "import"},
        timeout=60,
    )
    def honeybee_model_to_dragonfly(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        identifier: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Dragonfly model identifier and DFJSON file name. "
                    "Defaults to dragonfly_from_honeybee for natural conversion demos."
                )
            ),
        ] = None,
        honeybee_model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target with target_type=honeybee_model. Defaults to the Garden base Honeybee model."),
        ] = None,
        conversion_method: Annotated[
            str,
            Field(description="Dragonfly Model.from_honeybee conversion_method, for example AllRoom2D."),
        ] = "AllRoom2D",
        set_base: Annotated[
            bool,
            Field(description="Whether to save the converted Dragonfly Model as the Garden base_dragonfly_model."),
        ] = True,
    ) -> dict[str, Any]:
        """Convert a Honeybee model to Dragonfly."""
        from garden.dragonfly_core.conversion import honeybee_model_to_dragonfly as service

        return service(
            garden_root=garden_root,
            identifier=identifier or "dragonfly_from_honeybee",
            honeybee_model_target=honeybee_model_target,
            conversion_method=conversion_method,
            set_base=set_base,
        )

    @mcp.tool(
        name="DF_Import_Model_File",
        description=(
            'Import a Garden-local Dragonfly DFJSON or Dragonfly-compatible geoJSON file and save '
            'it as a Dragonfly model target. Provide a Garden-relative path to a DFJSON or '
            'Dragonfly-compatible GeoJSON file.'
        ),
        tags={"dragonfly", "dfjson", "geojson", "import", "artifact", "garden"},
        timeout=60,
    )
    def import_dragonfly_model_file(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        file_path: Annotated[
            str,
            Field(description="Garden-relative DFJSON or geoJSON file path."),
        ],
        file_type: Annotated[
            str,
            Field(description="File type to import: dfjson or geojson."),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Optional stored Dragonfly model identifier."),
        ] = None,
        set_base: Annotated[
            bool,
            Field(description="Whether to set the imported model as base_dragonfly_model."),
        ] = True,
        include_body: Annotated[
            bool,
            Field(description="Whether to return the full model body; false keeps response compact."),
        ] = False,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Optional geoJSON import location dict with city, latitude, longitude, and time_zone."),
        ] = None,
        point: Annotated[
            list[float] | None,
            Field(description="Optional geoJSON origin point as [x, y]."),
        ] = None,
        all_polygons_to_buildings: Annotated[
            bool,
            Field(description="For geoJSON, convert all polygons to buildings when supported by Dragonfly."),
        ] = False,
        existing_to_context: Annotated[
            bool,
            Field(description="For geoJSON, convert existing polygons to context shade when supported."),
        ] = False,
        units: Annotated[
            str,
            Field(description="Dragonfly model units for geoJSON import."),
        ] = "Meters",
        tolerance: Annotated[
            float | None,
            Field(description="Optional Dragonfly geometry tolerance for geoJSON import."),
        ] = None,
        angle_tolerance: Annotated[
            float,
            Field(description="Dragonfly angle tolerance for geoJSON import."),
        ] = 1.0,
    ) -> dict[str, Any]:
        """Import a Dragonfly model file."""
        from garden.dragonfly_core.model_files import import_dragonfly_model_file as service

        return service(
            garden_root=garden_root,
            file_path=file_path,
            file_type=file_type,
            identifier=identifier,
            set_base=set_base,
            include_body=include_body,
            location=location,
            point=point,
            all_polygons_to_buildings=all_polygons_to_buildings,
            existing_to_context=existing_to_context,
            units=units,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
        )

    @mcp.tool(
        name="DF_Intersect_Room2Ds",
        description=(
            "Intersect adjacent Dragonfly Room2D segments with "
            "Room2D.intersect_adjacency. This operation clears original boundary "
            "conditions, window/glazing parameters, and shading parameters as wall "
            "segments are subdivided; run it before assigning those properties. It "
            "does not restore or automatically preserve them. The tool applies to "
            "all Room2Ds in the selected Story, Building, or Model scope, and saves "
            "at most once only when the model changes. It returns affected "
            "Building, Story, and Room2D counts and identifier summaries."
        ),
        tags={"dragonfly", "room2d", "geometry", "intersect", "adjacency", "edit"},
        timeout=30,
    )
    def intersect_dragonfly_room2ds(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        tolerance: Annotated[
            StrictFloat,
            Field(description="Positive tolerance passed to Room2D.intersect_adjacency; defaults to 0.01."),
        ] = 0.01,
        host_type: Annotated[
            StrictStr | None,
            Field(description="Optional scope type: story, building, or model. Defaults to model."),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Story or Building target restricting the Room2D scope."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
    ) -> dict[str, Any]:
        """Intersect Dragonfly Room2D adjacency segments."""
        from garden.dragonfly_core.geometry import intersect_dragonfly_room2ds as service

        return service(
            garden_root=garden_root,
            tolerance=tolerance,
            host_type=host_type,
            host_target=host_target,
            model_target=model_target,
        )

    @mcp.tool(
        name="DF_Join_Small_Room2Ds",
        description=(
            "Join small Room2Ds in a Dragonfly Story, Building, or Model using "
            "Story.join_small_room_2ds, then reset and solve Story adjacencies. "
            "The operation saves at most once only when the model changes and returns affected Building, Story, and "
            "Room2D counts and identifier summaries."
        ),
        tags={"dragonfly", "room2d", "geometry", "join", "merge", "edit"},
        timeout=30,
    )
    def join_small_dragonfly_room2ds(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        area_threshold: Annotated[
            StrictFloat,
            Field(description="Positive Room2D floor-area threshold below which rooms are joined; defaults to 10.0."),
        ] = 10.0,
        join_into_large: Annotated[
            StrictBool,
            Field(description="Whether small rooms should be merged into neighboring large rooms; defaults to false."),
        ] = False,
        tolerance: Annotated[
            StrictFloat,
            Field(description="Positive Dragonfly geometry tolerance; defaults to 0.01."),
        ] = 0.01,
        host_type: Annotated[
            StrictStr | None,
            Field(description="Optional scope type: story, building, or model. Defaults to model."),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(description="Required Story or Building target when host_type is story or building."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
    ) -> dict[str, Any]:
        """Join small Dragonfly Room2Ds."""
        from garden.dragonfly_core.geometry import join_small_dragonfly_room2ds as service

        return service(
            garden_root=garden_root,
            area_threshold=area_threshold,
            join_into_large=join_into_large,
            tolerance=tolerance,
            host_type=host_type,
            host_target=host_target,
            model_target=model_target,
        )

    @mcp.tool(
        name="DF_Room2D_Attributes",
        description=(
            "List compact Dragonfly Room2D attributes supported by "
            "DF_Room2Ds_By_Attribute, including value type hints and supported "
            "operators. Use this before attribute grouping when the attribute "
            "name is uncertain. Returns attributes, summary_view, and report."
        ),
        tags={"dragonfly", "room2d", "attribute", "query", "list"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_df_room2d_attributes(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly model target; defaults to the Garden "
                    "base Dragonfly Model."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """List compact Room2D attributes supported by attribute grouping."""
        from garden.dragonfly_core.queries import list_dragonfly_room2d_attributes as service

        return service(garden_root=garden_root, model_target=model_target)

    @mcp.tool(
        name="DF_Room2Ds_By_Attribute",
        description=(
            'Return Dragonfly Room2D targets and compact values for one SDK attribute, such as '
            'floor_area, volume, or floor_height. Read-only summary/query tool.'
        ),
        tags={"dragonfly", "geometry", "summary", "query"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def query_dragonfly_room2ds_by_attribute(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        attribute: Annotated[
            str,
            Field(description="Dragonfly Room2D SDK property name, such as floor_area."),
        ],
        operator: Annotated[
            str | None,
            Field(
                description=(
                    "Optional filter operator: equals, contains, gt, lt, gte, or lte. "
                    "Omit it to list and group all values."
                )
            ),
        ] = None,
        value: Annotated[
            Any,
            Field(
                description="Optional comparison value used with operator."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target; defaults to base_dragonfly_model."),
        ] = None,
    ) -> dict[str, Any]:
        """Query Dragonfly Room2Ds by one attribute."""
        from garden.dragonfly_core.queries import query_dragonfly_room2ds_by_attribute as service

        return service(
            garden_root=garden_root,
            attribute=attribute,
            model_target=model_target,
            operator=operator,
            value=value,
        )

    @mcp.tool(
        name="DF_Remove_Buildings",
        description=(
            "Remove Buildings from a Garden Dragonfly Model using Building object "
            "targets or identifiers. Embedded Stories and Room2Ds inside removed "
            "Buildings leave the model with their parent Building and the scope is "
            "reported in relationship_cleanup. Returns target, model_target, "
            "summary_view, persistence_receipt, and report for the updated model."
        ),
        tags={"dragonfly", "building", "remove", "edit"},
        timeout=20,
    )
    def remove_dragonfly_buildings(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json.")],
        object_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional Building object targets from DF_Search_Objects."),
        ] = None,
        building_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional Building identifiers to remove when object targets are not available."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
    ) -> dict[str, Any]:
        """Remove Dragonfly Buildings."""
        from garden.dragonfly_core.editing import remove_dragonfly_buildings as service

        return service(
            garden_root=garden_root,
            object_targets=object_targets,
            building_identifiers=building_identifiers,
            model_target=model_target,
        )

    @mcp.tool(
        name="DF_Remove_Context_Shades",
        description=(
            "Remove ContextShades from a Garden Dragonfly Model using ContextShade "
            "object targets or identifiers. Returns target, model_target, summary_view, "
            "persistence_receipt, and report for the updated Dragonfly Model."
        ),
        tags={"dragonfly", "context-shade", "remove", "edit"},
        timeout=20,
    )
    def remove_dragonfly_context_shades(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json.")],
        object_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional ContextShade object targets from DF_Search_Objects."),
        ] = None,
        context_shade_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional ContextShade identifiers to remove when object targets are not available."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
    ) -> dict[str, Any]:
        """Remove Dragonfly ContextShades."""
        from garden.dragonfly_core.editing import remove_dragonfly_context_shades as service

        return service(
            garden_root=garden_root,
            object_targets=object_targets,
            context_shade_identifiers=context_shade_identifiers,
            model_target=model_target,
        )

    @mcp.tool(
        name="DF_Remove_Room2Ds",
        description=(
            "Remove Room2Ds from a Garden Dragonfly Model using Room2D object targets "
            "or identifiers. Empty parent Stories and Buildings are cleaned from the "
            "saved model and reported in relationship_cleanup. Returns target, "
            "model_target, summary_view, persistence_receipt, and report for the "
            "updated Dragonfly Model."
        ),
        tags={"dragonfly", "room2d", "remove", "edit"},
        timeout=20,
    )
    def remove_dragonfly_room2ds(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json.")],
        object_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional Room2D object targets from DF_Search_Objects or DF_Room2Ds_By_Attribute."),
        ] = None,
        room2d_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional Room2D identifiers to remove when object targets are not available."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly Model target; defaults to the Garden base Dragonfly Model."),
        ] = None,
    ) -> dict[str, Any]:
        """Remove Dragonfly Room2Ds."""
        from garden.dragonfly_core.editing import remove_dragonfly_room2ds as service

        return service(
            garden_root=garden_root,
            object_targets=object_targets,
            room2d_identifiers=room2d_identifiers,
            model_target=model_target,
        )

    @mcp.tool(
        name="DF_Remove_Stories_From_Building",
        description=(
            'Remove Stories from a Dragonfly Building using Dragonfly '
            'Building.remove_stories_by_identifier. Select the Building with building_identifier '
            'and Story IDs with story_identifiers. Use DF_Remove_Buildings or DF_Remove_Room2Ds '
            'to remove Buildings or Room2Ds. After removal, the service uses Dragonfly SDK '
            'Building.separate_top_bottom_floors so the remaining Stories keep explicit ground, '
            'typical, and top semantics. Returns target, summary_view, and report for the updated '
            'Dragonfly Building/model context.'
        ),
        tags={"dragonfly", "building", "story", "remove", "edit"},
        timeout=20,
    )
    def remove_dragonfly_stories_from_building(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        building_identifier: Annotated[
            str,
            Field(description="Required identifier of the existing Dragonfly Building inside the selected Dragonfly Model."),
        ],
        story_identifiers: Annotated[
            list[str],
            Field(description="Required Dragonfly Story identifiers to remove from the Building."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Remove Dragonfly Stories from a Building."""
        from garden.dragonfly_core.editing import (
            remove_dragonfly_stories_from_building as service,
        )

        return service(
            garden_root=garden_root,
            building_identifier=building_identifier,
            story_identifiers=story_identifiers,
            model_target=model_target,
        )

    @mcp.tool(
        name="DF_Reset_Story_Adjacency",
        description=(
            'Reset Surface boundary conditions on a Dragonfly Story using Story.reset_adjacency, '
            'save the updated DFJSON, and return compact adjacency counts plus validation '
            'summary. Pass story_target or story_identifier.'
        ),
        tags={"dragonfly", "story", "geometry", "edit", "adjacency"},
        timeout=30,
    )
    def reset_dragonfly_story_adjacency(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        story_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Required Dragonfly Story target or story identifier in the selected Garden model. "
                    "Prefer story_target when available."
                )
            ),
        ] = None,
        story_identifier: Annotated[
            str | None,
            Field(description="Optional Dragonfly Story identifier when no story_target is available."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Reset Dragonfly Story adjacency."""
        from garden.dragonfly_core.geometry import reset_dragonfly_story_adjacency as service

        return service(
            garden_root=garden_root,
            story_target=story_target,
            story_identifier=story_identifier,
            model_target=model_target,
        )

    @mcp.tool(
        name="DF_Search_Objects",
        description=(
            "Search Dragonfly Buildings, Stories, Room2Ds, and ContextShades in the "
            "Garden base Dragonfly model or an explicit Dragonfly model target. Also "
            "returns draft Room2D and Story objects saved in the Garden before they are "
            "assembled into a Building. Use object_type=building, story, room2d, "
            "context_shade, or all; for Dragonfly rooms, use room2d. Returns compact "
            "matches with nested Dragonfly object targets for follow-up tools. Set "
            "include_geometry=true only when a Room2D floor geometry summary is needed."
        ),
        tags={"dragonfly", "model", "search", "summary", "inventory"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_dragonfly_model_objects(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        object_type: Annotated[
            str,
            Field(
                description='Object type to return: all, building, story, room2d, or context_shade.'
            ),
        ] = "all",
        identifier: Annotated[
            str | None,
            Field(
                description="Optional exact Dragonfly object identifier or display name filter."
            ),
        ] = None,
        query: Annotated[
            str | None,
            Field(description="Optional token query over Dragonfly object identifier and display name."),
        ] = None,
        building_identifier: Annotated[
            str | None,
            Field(description="Optional parent Building identifier filter."),
        ] = None,
        story_identifier: Annotated[
            str | None,
            Field(description="Optional parent Story identifier filter for Room2Ds."),
        ] = None,
        children_scope: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Dragonfly Building or Story object target used to return only child Stories or Room2Ds."
            ),
        ] = None,
        include_counts: Annotated[
            bool,
            Field(
                description="Whether to include compact counts_by_type before any limit is applied."
            ),
        ] = False,
        include_geometry: Annotated[
            bool,
            Field(
                description="Whether to include compact Room2D Face3D floor geometry summaries. Defaults false to avoid large object payloads."
            ),
        ] = False,
        include_properties: Annotated[
            bool,
            Field(
                description="Whether to include compact Dragonfly object property values under a properties field."
            ),
        ] = False,
        limit: Annotated[
            int | None,
            Field(
                description="Optional maximum number of matches to return after filtering. Counts still report the full filtered total."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Search Dragonfly objects and return compact typed targets."""
        from garden.dragonfly_core.search import search_dragonfly_model_objects as service

        return service(
            garden_root=garden_root,
            model_target=model_target,
            object_type=object_type,
            identifier=identifier,
            query=query,
            building_identifier=building_identifier,
            story_identifier=story_identifier,
            children_scope=children_scope,
            include_counts=include_counts,
            include_geometry=include_geometry,
            include_properties=include_properties,
            limit=limit,
        )

    @mcp.tool(
        name="DF_Solve_Story_Adjacency",
        description=(
            "Solve Room2D adjacencies on a Dragonfly Story using "
            "Story.solve_room_2d_adjacency, save the updated DFJSON, and return compact "
            "adjacency counts plus validation summary. Pass story_target from the "
            "Dragonfly create Story/Building workflow or story_identifier; use reset "
            "adjacency when the goal is to clear boundary conditions."
        ),
        tags={"dragonfly", "story", "geometry", "edit", "adjacency"},
        timeout=30,
    )
    def solve_dragonfly_story_adjacency(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        story_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Required Dragonfly Story target or story identifier in the selected Garden model. "
                    "Prefer story_target when available."
                )
            ),
        ] = None,
        story_identifier: Annotated[
            str | None,
            Field(description="Optional Dragonfly Story identifier when no story_target is available."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        tolerance: Annotated[
            float,
            Field(description="Tolerance passed to Dragonfly Story.solve_room_2d_adjacency."),
        ] = 0.01,
        intersect: Annotated[
            bool,
            Field(description="Whether to intersect Room2D adjacency segments before solving."),
        ] = False,
        resolve_window_conflicts: Annotated[
            bool,
            Field(description="Whether SDK should resolve window conflicts on adjacent segments."),
        ] = True,
    ) -> dict[str, Any]:
        """Solve Dragonfly Story adjacency."""
        from garden.dragonfly_core.geometry import solve_dragonfly_story_adjacency as service

        return service(
            garden_root=garden_root,
            story_target=story_target,
            story_identifier=story_identifier,
            model_target=model_target,
            tolerance=tolerance,
            intersect=intersect,
            resolve_window_conflicts=resolve_window_conflicts,
        )

    @mcp.tool(
        name="DF_Validate_Model",
        description=(
            "Validate an existing Dragonfly model already stored in a Garden base "
            "Dragonfly model or explicit model target. Returns validation_status "
            "through is_valid/valid, summary_view, report, structured issues, and "
            "compact object counts. This reports issues only; cleanup and adjacency "
            "tools perform model edits."
        ),
        tags={"dragonfly", "model", "validate", "summary", "check"},
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def validate_dragonfly_model(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually DF_Model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Validate a Dragonfly model."""
        from garden.dragonfly_core.model_io import validate_dragonfly_model as service

        return service(garden_root=garden_root, model_target=model_target)
