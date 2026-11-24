"""Consolidated MCP tools for Dragonfly models, geometry, properties, and display."""

from __future__ import annotations

from typing import Any, Literal

from fastmcp import FastMCP

from garden.dragonfly_core.conversion import (
    dragonfly_model_to_honeybee,
    honeybee_model_to_dragonfly,
)
from garden.dragonfly_core.creation import (
    create_dragonfly_building,
    create_dragonfly_building_from_all_story_geometry,
    create_dragonfly_building_from_footprint,
    create_dragonfly_context_shade,
    create_dragonfly_model,
    create_dragonfly_room2d,
    create_dragonfly_story,
)
from garden.dragonfly_core.display import (
    dragonfly_model_envelope_edges_to_visualization_set,
    dragonfly_model_to_visualization_set,
    dragonfly_models_to_comparison_visualization_set,
    dragonfly_opening_projection_to_visualization_set,
    dragonfly_room2d_attribute_to_visualization_set,
    dragonfly_targets_to_visualization_set,
)
from garden.dragonfly_core.editing import (
    add_dragonfly_stories_to_building,
    edit_dragonfly_object,
    remove_dragonfly_objects,
)
from garden.dragonfly_core.envelope_parameters import (
    apply_dragonfly_clerestory_parameter,
    apply_dragonfly_shading_parameter,
    apply_dragonfly_skylight_parameter,
    apply_dragonfly_wall_properties,
    apply_dragonfly_window_parameter,
    create_dragonfly_shading_parameter,
    create_dragonfly_skylight_parameter,
    create_dragonfly_window_parameter,
)
from garden.dragonfly_core.geometry import process_dragonfly_geometry
from garden.dragonfly_core.model_files import (
    export_dragonfly_model_file,
    import_dragonfly_model_file,
)
from garden.dragonfly_core.model_io import (
    get_dragonfly_model_summary,
    validate_dragonfly_model,
)
from garden.dragonfly_core.properties import (
    apply_dragonfly_energy_properties,
    apply_dragonfly_radiance_properties,
    get_dragonfly_properties_summary,
)
from garden.dragonfly_core.queries import (
    get_dragonfly_geometry_properties,
    list_dragonfly_room2d_attributes,
    query_dragonfly_room2ds_by_attribute,
)
from garden.dragonfly_core.search import search_dragonfly_model_objects
from ladybug_tools_mcp.contracts import make_report


_ROOM2D_BATCH_KEYS = (
    "identifier",
    "display_name",
    "floor_height",
    "vertices",
    "floor_to_ceiling_height",
    "model_target",
    "is_ground_contact",
    "is_top_exposed",
    "x_dim",
    "y_dim",
    "origin",
    "height",
    "story_number",
    "ceiling_plenum_depth",
    "floor_plenum_depth",
)

_CONTEXT_SHADE_BATCH_KEYS = (
    "identifier",
    "geometry",
    "vertices",
    "model_target",
    "is_detached",
    "x_dim",
    "y_dim",
    "height",
    "origin",
    "display_name",
    "context_shade_type",
    "is_vegetation",
    "cen_pt",
    "radius",
)


def _strip_object_dict(result: dict[str, Any], return_object_dict: bool) -> dict[str, Any]:
    if not return_object_dict:
        result.pop("object_dict", None)
    return result


def _create_batch_objects(
    *,
    garden_root: str,
    object_type: Literal["room2d", "context_shade"],
    items: list[dict[str, Any]],
    model_target: dict[str, Any] | None,
    return_object_dict: bool,
) -> dict[str, Any]:
    if not items:
        raise ValueError("items must contain at least one object definition.")
    allowed_keys = _ROOM2D_BATCH_KEYS if object_type == "room2d" else _CONTEXT_SHADE_BATCH_KEYS
    creator = create_dragonfly_room2d if object_type == "room2d" else create_dragonfly_context_shade
    current_model_target = model_target
    results: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []

    for index, raw_item in enumerate(items):
        if not isinstance(raw_item, dict):
            raise ValueError(f"items[{index}] must be an object definition dictionary.")
        unknown_keys = sorted(set(raw_item) - set(allowed_keys))
        if unknown_keys:
            raise ValueError(
                f"Unsupported keys in items[{index}] for {object_type}: {', '.join(unknown_keys)}"
            )
        kwargs: dict[str, Any] = {
            "garden_root": garden_root,
            "model_target": raw_item.get("model_target", current_model_target),
        }
        for key in allowed_keys:
            if key != "model_target" and key in raw_item:
                kwargs[key] = raw_item[key]
        if not kwargs.get("identifier"):
            raise ValueError(f"items[{index}].identifier is required for {object_type}.")
        created = creator(**kwargs)
        _strip_object_dict(created, return_object_dict)
        if isinstance(created.get("model_target"), dict):
            current_model_target = created["model_target"]
        results.append(created)
        if isinstance(created.get("target"), dict):
            targets.append(created["target"])

    return {
        "results": results,
        "targets": targets,
        "model_target": current_model_target,
        "summary_view": {
            "object_type": object_type,
            "created_count": len(results),
            "targets": targets,
        },
        "report": make_report(
            status="ok",
            message=f"Created {len(results)} Dragonfly {object_type} objects.",
        ),
    }


def register(mcp: FastMCP) -> None:
    """Register consolidated Dragonfly core MCP tools."""

    @mcp.tool(
        name="DF_Model",
        tags={"dragonfly", "author", "model", "garden", "target"},
        timeout=30,
    )
    def DF_Model(
        garden_root: str,
        identifier: str,
        display_name: str | None = None,
        unit_system: Literal["Metric", "Imperial"] | None = None,
        units: Literal["Meters", "Millimeters", "Feet", "Inches", "Centimeters"] | None = None,
        tolerance: float | None = None,
        angle_tolerance: float = 1.0,
        save_back: bool = True,
        set_base: bool = True,
        return_object_dict: bool = False,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly Model in the Garden workspace.

        Uses ``units`` when specified, or derives Meters/Feet from ``unit_system``.
        Returns a Garden target and summary_view; set ``return_object_dict=True``
        to include the full DFJSON dictionary.
        """
        resolved_units = units
        if resolved_units is None:
            resolved_units = "Feet" if unit_system == "Imperial" else "Meters"
        return create_dragonfly_model(
            garden_root=garden_root,
            identifier=identifier,
            display_name=display_name,
            units=resolved_units,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
            save_back=save_back,
            set_base=set_base,
            include_body=return_object_dict,
            latitude=latitude,
            longitude=longitude,
        )

    @mcp.tool(
        name="DF_Create_Objects",
        tags={"dragonfly", "author", "room2d", "story", "building", "context-shade", "target"},
        timeout=30,
    )
    def DF_Create_Objects(
        garden_root: str,
        object_type: Literal[
            "room2d",
            "story",
            "building",
            "building_from_footprint",
            "building_from_all_story_geometry",
            "context_shade",
            "add_stories_to_building",
        ],
        identifier: str | None = None,
        display_name: str | None = None,
        model_target: dict[str, Any] | None = None,
        items: list[dict[str, Any]] | None = None,
        return_object_dict: bool = False,
        # room2d parameters
        floor_height: float | None = None,
        vertices: list[list[float]] | None = None,
        floor_to_ceiling_height: float | None = None,
        is_ground_contact: bool = False,
        is_top_exposed: bool = False,
        x_dim: float | None = None,
        y_dim: float | None = None,
        origin: list[float] | None = None,
        height: float | None = None,
        story_number: int | None = None,
        ceiling_plenum_depth: float | None = None,
        floor_plenum_depth: float | None = None,
        # story parameters
        room2d_targets: list[dict[str, Any]] | None = None,
        floor_to_floor_height: float | None = None,
        multiplier: int = 1,
        story_type: str = "Standard",
        # building / add_stories_to_building parameters
        story_targets: list[dict[str, Any]] | None = None,
        sort_stories: bool = True,
        separate_top_bottom_floors: bool = False,
        roof_geometry: Any = None,
        basement_count: int = 0,
        basement_remove_windows: bool = False,
        building_identifier: str | None = None,
        story_identifiers: list[str] | None = None,
        # building_from_footprint / building_from_all_story_geometry parameters
        footprints: list[Any] | None = None,
        all_story_geometry: list[list[Any]] | None = None,
        floor_to_floor_heights: list[float] | None = None,
        perimeter_offset: float | None = None,
        tolerance: float | None = None,
        # context_shade parameters
        geometry: Any = None,
        is_detached: bool = True,
        context_shade_type: str | None = None,
        is_vegetation: bool | None = None,
        cen_pt: list[float] | None = None,
        radius: float | None = None,
    ) -> dict[str, Any]:
        """Create Dragonfly Room2Ds, Stories, Buildings, ContextShades, or attach Stories.

        Supports batch ``items`` creation for ``object_type='room2d'`` and
        ``object_type='context_shade'``.
        """
        if items is not None:
            if object_type not in {"room2d", "context_shade"}:
                raise ValueError(
                    "items batch creation is only supported for object_type 'room2d' or 'context_shade'."
                )
            return _create_batch_objects(
                garden_root=garden_root,
                object_type=object_type,
                items=items,
                model_target=model_target,
                return_object_dict=return_object_dict,
            )

        if object_type == "room2d":
            if not identifier:
                raise ValueError("identifier is required for object_type='room2d'.")
            result = create_dragonfly_room2d(
                garden_root=garden_root,
                identifier=identifier,
                display_name=display_name,
                floor_height=floor_height,
                vertices=vertices,
                floor_to_ceiling_height=floor_to_ceiling_height,
                model_target=model_target,
                is_ground_contact=is_ground_contact,
                is_top_exposed=is_top_exposed,
                x_dim=x_dim,
                y_dim=y_dim,
                origin=origin,
                height=height,
                story_number=story_number,
                ceiling_plenum_depth=ceiling_plenum_depth,
                floor_plenum_depth=floor_plenum_depth,
            )
            return _strip_object_dict(result, return_object_dict)

        if object_type == "story":
            return create_dragonfly_story(
                garden_root=garden_root,
                room2d_targets=room2d_targets,
                identifier=identifier,
                model_target=model_target,
                floor_to_floor_height=floor_to_floor_height,
                floor_height=floor_height,
                multiplier=multiplier,
                story_type=story_type,
                display_name=display_name,
            )

        if object_type == "building":
            result = create_dragonfly_building(
                garden_root=garden_root,
                story_targets=story_targets,
                identifier=identifier,
                model_target=model_target,
                sort_stories=sort_stories,
                display_name=display_name,
                separate_top_bottom_floors=separate_top_bottom_floors,
                roof_geometry=roof_geometry,
                basement_count=basement_count,
                basement_remove_windows=basement_remove_windows,
                tolerance=tolerance,
            )
            return _strip_object_dict(result, return_object_dict)

        if object_type == "building_from_footprint":
            if not identifier:
                raise ValueError(
                    "identifier is required for object_type='building_from_footprint'."
                )
            if footprints is None or floor_to_floor_heights is None:
                raise ValueError(
                    "footprints and floor_to_floor_heights are required for object_type='building_from_footprint'."
                )
            return create_dragonfly_building_from_footprint(
                garden_root=garden_root,
                identifier=identifier,
                footprints=footprints,
                floor_to_floor_heights=floor_to_floor_heights,
                perimeter_offset=perimeter_offset,
                model_target=model_target,
                display_name=display_name,
                tolerance=tolerance,
                roof_geometry=roof_geometry,
                basement_count=basement_count,
                basement_remove_windows=basement_remove_windows,
            )

        if object_type == "building_from_all_story_geometry":
            if not identifier:
                raise ValueError(
                    "identifier is required for object_type='building_from_all_story_geometry'."
                )
            if all_story_geometry is None or floor_to_floor_heights is None:
                raise ValueError(
                    "all_story_geometry and floor_to_floor_heights are required for "
                    "object_type='building_from_all_story_geometry'."
                )
            return create_dragonfly_building_from_all_story_geometry(
                garden_root=garden_root,
                identifier=identifier,
                all_story_geometry=all_story_geometry,
                floor_to_floor_heights=floor_to_floor_heights,
                perimeter_offset=perimeter_offset,
                model_target=model_target,
                display_name=display_name,
                tolerance=tolerance,
                roof_geometry=roof_geometry,
                basement_count=basement_count,
                basement_remove_windows=basement_remove_windows,
            )

        if object_type == "context_shade":
            if not identifier:
                raise ValueError("identifier is required for object_type='context_shade'.")
            result = create_dragonfly_context_shade(
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
            return _strip_object_dict(result, return_object_dict)

        resolved_building_identifier = building_identifier or identifier
        if not resolved_building_identifier:
            raise ValueError(
                "building_identifier (or identifier) is required for object_type='add_stories_to_building'."
            )
        return add_dragonfly_stories_to_building(
            garden_root=garden_root,
            building_identifier=resolved_building_identifier,
            story_targets=story_targets,
            model_target=model_target,
            story_identifiers=story_identifiers,
            separate_top_bottom_floors=separate_top_bottom_floors,
        )

    @mcp.tool(
        name="DF_Edit_Object",
        tags={"dragonfly", "edit", "model", "building", "story", "room2d", "target"},
        timeout=30,
    )
    def DF_Edit_Object(
        garden_root: str,
        object_type: Literal["model", "building", "story", "room2d"] | None = None,
        target: dict[str, Any] | None = None,
        model_target: dict[str, Any] | None = None,
        building_identifier: str | None = None,
        story_target: dict[str, Any] | None = None,
        story_identifier: str | None = None,
        room2d_target: dict[str, Any] | None = None,
        room_identifier: str | None = None,
        display_name: str | None = None,
        units: str | None = None,
        convert_geometry: bool = True,
        tolerance: float | None = None,
        angle_tolerance: float | None = None,
        sort_stories: bool = False,
        separate_top_bottom_floors: bool = False,
        floor_height: float | None = None,
        floor_to_floor_height: float | None = None,
        multiplier: int | None = None,
        vertices: list[list[float]] | None = None,
        floor_to_ceiling_height: float | None = None,
        zone: str | None = None,
        is_ground_contact: bool | None = None,
        is_top_exposed: bool | None = None,
        projection_distance: float = 0,
    ) -> dict[str, Any]:
        """Edit properties of a Dragonfly Model, Building, Story, or Room2D."""
        return edit_dragonfly_object(
            garden_root=garden_root,
            object_type=object_type,
            target=target,
            model_target=model_target,
            building_identifier=building_identifier,
            story_target=story_target,
            story_identifier=story_identifier,
            room2d_target=room2d_target,
            room_identifier=room_identifier,
            display_name=display_name,
            units=units,
            convert_geometry=convert_geometry,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
            sort_stories=sort_stories,
            separate_top_bottom_floors=separate_top_bottom_floors,
            floor_height=floor_height,
            floor_to_floor_height=floor_to_floor_height,
            multiplier=multiplier,
            vertices=vertices,
            floor_to_ceiling_height=floor_to_ceiling_height,
            zone=zone,
            is_ground_contact=is_ground_contact,
            is_top_exposed=is_top_exposed,
            projection_distance=projection_distance,
        )

    @mcp.tool(
        name="DF_Remove_Objects",
        tags={"dragonfly", "edit", "remove", "building", "story", "room2d", "context-shade", "target"},
        timeout=30,
    )
    def DF_Remove_Objects(
        garden_root: str,
        object_type: Literal["building", "story", "room2d", "context_shade"] | None = None,
        object_targets: list[dict[str, Any]] | None = None,
        identifiers: list[str] | None = None,
        building_identifier: str | None = None,
        story_identifiers: list[str] | None = None,
        building_identifiers: list[str] | None = None,
        room2d_identifiers: list[str] | None = None,
        context_shade_identifiers: list[str] | None = None,
        model_target: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Remove Buildings, Stories from a Building, Room2Ds, or ContextShades."""
        return remove_dragonfly_objects(
            garden_root=garden_root,
            object_type=object_type,
            object_targets=object_targets,
            identifiers=identifiers,
            building_identifier=building_identifier,
            story_identifiers=story_identifiers,
            building_identifiers=building_identifiers,
            room2d_identifiers=room2d_identifiers,
            context_shade_identifiers=context_shade_identifiers,
            model_target=model_target,
        )

    @mcp.tool(
        name="DF_Process_Geometry",
        tags={"dragonfly", "geometry", "align", "clean", "intersect", "adjacency", "target"},
        timeout=45,
    )
    def DF_Process_Geometry(
        garden_root: str,
        operation: Literal[
            "align",
            "clean",
            "intersect",
            "join_small",
            "solve_adjacency",
            "reset_adjacency",
            "core_perimeter",
            "pull_to_story",
            "fill_holes",
            "join_room_2ds",
            "split_with_story_above",
            "convert_multipliers",
            "separate_plenums",
            "transform",
            "merge_model",
        ],
        model_target: dict[str, Any] | None = None,
        host_type: str | None = None,
        host_target: dict[str, Any] | None = None,
        story_target: dict[str, Any] | None = None,
        story_identifier: str | None = None,
        room2d_target: dict[str, Any] | None = None,
        room_identifier: str | None = None,
        building_identifier: str | None = None,
        lines: list[list[list[float]]] | list[dict[str, Any]] | None = None,
        distance: float = 0.5,
        area_threshold: float = 10.0,
        join_into_large: bool = False,
        tolerance: float = 0.01,
        intersect: bool = False,
        resolve_window_conflicts: bool = True,
        remove_duplicate_vertices: bool = True,
        remove_colinear_vertices: bool = True,
        remove_short_segments_distance: float | None = None,
        preserve_wall_props: bool = True,
        angle_tolerance: float = 1.0,
        perimeter_offset: float | None = None,
        air_boundary: bool = False,
        base_story_id: str | None = None,
        pulled_story_ids: list[str] | None = None,
        coordinate_vertices: bool = True,
        constrain_edges: bool = False,
        base_name: str = "Room",
        room_identifiers: list[str] | None = None,
        story_above_identifier: str | None = None,
        target_floor_to_ceiling: float | None = None,
        floor_plenum: bool = False,
        transform_type: Literal["move", "rotate_xy", "scale"] | None = None,
        vector: list[float] | None = None,
        angle: float | None = None,
        factor: float | None = None,
        origin: list[float] | None = None,
        incoming_model_target: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run Room2D/Story/Building/Model geometry processing, transforms, or model merge."""
        return process_dragonfly_geometry(
            garden_root=garden_root,
            operation=operation,
            model_target=model_target,
            host_type=host_type,
            host_target=host_target,
            story_target=story_target,
            story_identifier=story_identifier,
            room2d_target=room2d_target,
            room_identifier=room_identifier,
            building_identifier=building_identifier,
            lines=lines,
            distance=distance,
            area_threshold=area_threshold,
            join_into_large=join_into_large,
            tolerance=tolerance,
            intersect=intersect,
            resolve_window_conflicts=resolve_window_conflicts,
            remove_duplicate_vertices=remove_duplicate_vertices,
            remove_colinear_vertices=remove_colinear_vertices,
            remove_short_segments_distance=remove_short_segments_distance,
            preserve_wall_props=preserve_wall_props,
            angle_tolerance=angle_tolerance,
            perimeter_offset=perimeter_offset,
            air_boundary=air_boundary,
            base_story_id=base_story_id,
            pulled_story_ids=pulled_story_ids,
            coordinate_vertices=coordinate_vertices,
            constrain_edges=constrain_edges,
            base_name=base_name,
            room_identifiers=room_identifiers,
            story_above_identifier=story_above_identifier,
            target_floor_to_ceiling=target_floor_to_ceiling,
            floor_plenum=floor_plenum,
            transform_type=transform_type,
            vector=vector,
            angle=angle,
            factor=factor,
            origin=origin,
            incoming_model_target=incoming_model_target,
        )

    @mcp.tool(
        name="DF_Apply_Properties",
        tags={"dragonfly", "properties", "energy", "radiance", "window", "shading", "target"},
        timeout=30,
    )
    def DF_Apply_Properties(
        garden_root: str,
        property_domain: Literal["energy", "radiance", "window", "shading", "skylight", "clerestory", "wall"],
        host_target: dict[str, Any] | None = None,
        host_type: Literal["room2d", "story", "building", "context_shade", "model"] | None = None,
        model_target: dict[str, Any] | None = None,
        # Energy properties
        program_type_identifier: str | None = None,
        construction_set_identifier: str | None = None,
        program_type: Any = None,
        construction_set: Any = None,
        hvac: Any = None,
        shw: Any = None,
        person_count: float | None = None,
        lighting_watts: float | None = None,
        electric_equipment_watts: float | None = None,
        gas_equipment_watts: float | None = None,
        hot_water_flow: float | None = None,
        infiltration_ach: float | None = None,
        daylighting_control: dict[str, Any] | None = None,
        daylight_center: dict[str, Any] | None = None,
        window_vent_control: dict[str, Any] | None = None,
        window_vent_opening: dict[str, Any] | None = None,
        fans: list[Any] | None = None,
        remove_existing_fans: bool = False,
        process_loads: list[Any] | None = None,
        remove_existing_process_loads: bool = False,
        diversify: dict[str, Any] | bool | None = None,
        ceiling_plenum_construction: Any = None,
        floor_plenum_construction: Any = None,
        construction: Any = None,
        transmittance_schedule: Any = None,
        # Radiance properties
        modifier_set_identifier: str | None = None,
        modifier_set: Any = None,
        modifier: Any = None,
        grid_parameter_type: str | None = None,
        grid_dimension: float | None = None,
        grid_offset: float | None = None,
        wall_offset: float = 0,
        face_type: str = "Wall",
        aperture_type: str = "All",
        punched_geometry: bool = False,
        dir_count: int = 8,
        start_vector: list[float] | None = None,
        mesh_radius: float | None = None,
        include_mesh: bool = True,
        remove_existing_grid_parameters: bool = False,
        # Window / Shading / Skylight / Clerestory / Wall parameters
        window_parameter: dict[str, Any] | None = None,
        shading_parameter: dict[str, Any] | None = None,
        skylight_parameter: dict[str, Any] | None = None,
        clerestory_parameter: dict[str, Any] | None = None,
        parameter_type: str | None = None,
        application_scope: str = "all_outdoor",
        segment_index: int | list[int] | None = None,
        window_ratio: float | None = None,
        rect_split: bool = True,
        window_height: float | None = None,
        sill_height: float | None = None,
        horizontal_separation: float | None = None,
        vertical_separation: float = 0,
        width: float | None = None,
        height: float | None = None,
        window_area: float | None = None,
        window_width: float | None = None,
        origins: list[list[float]] | None = None,
        widths: list[float] | None = None,
        heights: list[float] | None = None,
        polygons: list[list[list[float]]] | None = None,
        are_doors: list[bool] | None = None,
        depth: float | None = None,
        angle: float = 0,
        distance: float | None = None,
        louver_count: int | None = None,
        offset: float = 0,
        contour_vector: list[float] | None = None,
        flip_start_side: bool = False,
        skylight_area: float | None = None,
        skylight_ratio: float | None = None,
        spacing: float | str | None = None,
        story_identifier: str | None = None,
        air_boundary: bool | None = None,
        air_boundaries: list[bool] | None = None,
        boundary_condition: str | dict[str, Any] | None = None,
        guide_lines: list[list[list[float]]] | None = None,
        room_identifiers: list[str] | None = None,
        wall_modifiers: dict[str, Any] | None = None,
        tolerance: float = 0.01,
    ) -> dict[str, Any]:
        """Apply Energy, Radiance, Window, Shading, Skylight, Clerestory, or Wall properties."""
        if property_domain == "energy":
            if host_target is None and host_type != "model":
                raise ValueError(
                    "host_target is required for property_domain='energy' (or set host_type='model')."
                )
            return apply_dragonfly_energy_properties(
                garden_root=garden_root,
                host_target=host_target,
                model_target=model_target,
                program_type_identifier=program_type_identifier,
                construction_set_identifier=construction_set_identifier,
                program_type=program_type,
                construction_set=construction_set,
                hvac=hvac,
                shw=shw,
                person_count=person_count,
                lighting_watts=lighting_watts,
                electric_equipment_watts=electric_equipment_watts,
                gas_equipment_watts=gas_equipment_watts,
                hot_water_flow=hot_water_flow,
                infiltration_ach=infiltration_ach,
                daylighting_control=daylighting_control,
                daylight_center=daylight_center,
                window_vent_control=window_vent_control,
                window_vent_opening=window_vent_opening,
                fans=fans,
                remove_existing_fans=remove_existing_fans,
                process_loads=process_loads,
                remove_existing_process_loads=remove_existing_process_loads,
                diversify=diversify,
                ceiling_plenum_construction=ceiling_plenum_construction,
                floor_plenum_construction=floor_plenum_construction,
                construction=construction,
                transmittance_schedule=transmittance_schedule,
            )

        if property_domain == "radiance":
            if host_target is None:
                raise ValueError("host_target is required for property_domain='radiance'.")
            return apply_dragonfly_radiance_properties(
                garden_root=garden_root,
                host_target=host_target,
                model_target=model_target,
                modifier_set_identifier=modifier_set_identifier,
                modifier_set=modifier_set,
                modifier=modifier,
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

        if property_domain == "window":
            resolved_window = window_parameter
            if resolved_window is None:
                if parameter_type is None:
                    raise ValueError(
                        "Provide window_parameter dict or parameter_type with its fields."
                    )
                if host_target is None and host_type is None:
                    return create_dragonfly_window_parameter(
                        garden_root=garden_root,
                        parameter_type=parameter_type,
                        window_ratio=window_ratio,
                        rect_split=rect_split,
                        window_height=window_height,
                        sill_height=sill_height,
                        horizontal_separation=horizontal_separation,
                        vertical_separation=vertical_separation,
                        width=width,
                        height=height,
                        window_area=window_area,
                        window_width=window_width,
                        origins=origins,
                        widths=widths,
                        heights=heights,
                        polygons=polygons,
                        are_doors=are_doors,
                    )
                resolved_window = {
                    k: v
                    for k, v in {
                        "parameter_type": parameter_type,
                        "window_ratio": window_ratio,
                        "rect_split": rect_split,
                        "window_height": window_height,
                        "sill_height": sill_height,
                        "horizontal_separation": horizontal_separation,
                        "vertical_separation": vertical_separation,
                        "width": width,
                        "height": height,
                        "window_area": window_area,
                        "window_width": window_width,
                        "origins": origins,
                        "widths": widths,
                        "heights": heights,
                        "polygons": polygons,
                        "are_doors": are_doors,
                    }.items()
                    if v is not None
                }
            return apply_dragonfly_window_parameter(
                garden_root=garden_root,
                window_parameter=resolved_window,
                host_type=host_type,
                host_target=host_target,
                model_target=model_target,
                application_scope=application_scope,
                segment_index=segment_index,
            )

        if property_domain == "shading":
            resolved_shading = shading_parameter
            if resolved_shading is None:
                if parameter_type is None or depth is None:
                    raise ValueError(
                        "Provide shading_parameter dict or both parameter_type and depth."
                    )
                if host_target is None and host_type is None:
                    return create_dragonfly_shading_parameter(
                        garden_root=garden_root,
                        parameter_type=parameter_type,
                        depth=depth,
                        angle=angle,
                        distance=distance,
                        louver_count=louver_count,
                        offset=offset,
                        contour_vector=contour_vector,
                        flip_start_side=flip_start_side,
                    )
                resolved_shading = {
                    k: v
                    for k, v in {
                        "parameter_type": parameter_type,
                        "depth": depth,
                        "angle": angle,
                        "distance": distance,
                        "louver_count": louver_count,
                        "offset": offset,
                        "contour_vector": contour_vector,
                        "flip_start_side": flip_start_side,
                    }.items()
                    if v is not None
                }
            return apply_dragonfly_shading_parameter(
                garden_root=garden_root,
                shading_parameter=resolved_shading,
                host_type=host_type,
                host_target=host_target,
                model_target=model_target,
                application_scope=application_scope,
                segment_index=segment_index,
            )

        if property_domain == "skylight":
            resolved_skylight = skylight_parameter
            if resolved_skylight is None:
                if parameter_type is None:
                    raise ValueError(
                        "Provide skylight_parameter dict or parameter_type with its fields."
                    )
                if host_target is None and host_type is None:
                    return create_dragonfly_skylight_parameter(
                        garden_root=garden_root,
                        parameter_type=parameter_type,
                        skylight_area=skylight_area,
                        skylight_ratio=skylight_ratio,
                        spacing=spacing,
                        polygons=polygons,
                        are_doors=are_doors,
                    )
                resolved_skylight = {
                    k: v
                    for k, v in {
                        "parameter_type": parameter_type,
                        "skylight_area": skylight_area,
                        "skylight_ratio": skylight_ratio,
                        "spacing": spacing,
                        "polygons": polygons,
                        "are_doors": are_doors,
                    }.items()
                    if v is not None
                }
            return apply_dragonfly_skylight_parameter(
                garden_root=garden_root,
                skylight_parameter=resolved_skylight,
                host_type=host_type,
                host_target=host_target,
                model_target=model_target,
            )

        if property_domain == "clerestory":
            if clerestory_parameter is None:
                raise ValueError("clerestory_parameter dict is required for property_domain='clerestory'.")
            return apply_dragonfly_clerestory_parameter(
                garden_root=garden_root,
                clerestory_parameter=clerestory_parameter,
                host_target=host_target,
                story_identifier=story_identifier,
                model_target=model_target,
            )

        return apply_dragonfly_wall_properties(
            garden_root=garden_root,
            host_target=host_target,
            host_type=host_type,
            model_target=model_target,
            segment_index=segment_index,
            air_boundary=air_boundary,
            air_boundaries=air_boundaries,
            boundary_condition=boundary_condition,
            guide_lines=guide_lines,
            room_identifiers=room_identifiers,
            wall_modifiers=wall_modifiers,
            tolerance=tolerance,
        )

    @mcp.tool(
        name="DF_Inspect_Model",
        tags={"dragonfly", "inspect", "summary", "geometry", "attributes", "query", "target"},
        timeout=30,
    )
    def DF_Inspect_Model(
        garden_root: str,
        view: Literal[
            "model_summary",
            "properties_summary",
            "geometry_properties",
            "list_attributes",
            "query_by_attribute",
        ] = "model_summary",
        model_target: dict[str, Any] | None = None,
        target: dict[str, Any] | None = None,
        attributes: list[str] | None = None,
        attribute: str | None = None,
        operator: Literal[
            "==",
            "!=",
            "<",
            "<=",
            ">",
            ">=",
            "in",
            "contains",
            "equals",
            "not_equals",
            "gt",
            "lt",
            "gte",
            "lte",
        ]
        | None = None,
        value: Any = None,
    ) -> dict[str, Any]:
        """Inspect Dragonfly model summaries, Energy/Radiance properties, geometry, or Room2D attributes."""
        if view == "model_summary":
            return get_dragonfly_model_summary(
                garden_root=garden_root,
                model_target=model_target,
            )
        if view == "properties_summary":
            return get_dragonfly_properties_summary(
                garden_root=garden_root,
                model_target=model_target,
            )
        if view == "geometry_properties":
            return get_dragonfly_geometry_properties(
                garden_root=garden_root,
                target=target,
                model_target=model_target,
                attributes=attributes,
            )
        if view == "list_attributes":
            return list_dragonfly_room2d_attributes(
                garden_root=garden_root,
                model_target=model_target,
            )
        if not attribute:
            raise ValueError("attribute is required for view='query_by_attribute'.")
        return query_dragonfly_room2ds_by_attribute(
            garden_root=garden_root,
            attribute=attribute,
            model_target=model_target,
            operator=operator,
            value=value,
        )

    @mcp.tool(
        name="DF_Search_Objects",
        tags={"dragonfly", "search", "building", "story", "room2d", "context-shade", "target"},
        timeout=20,
    )
    def DF_Search_Objects(
        garden_root: str,
        model_target: dict[str, Any] | None = None,
        object_type: Literal["all", "building", "story", "room2d", "context_shade"] = "all",
        identifier: str | None = None,
        query: str | None = None,
        building_identifier: str | None = None,
        story_identifier: str | None = None,
        children_scope: Literal["none", "direct", "all"] | None = None,
        include_counts: bool = False,
        include_geometry: bool = False,
        include_properties: bool = False,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Search and inspect Dragonfly Buildings, Stories, Room2Ds, or ContextShades."""
        return search_dragonfly_model_objects(
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
        name="DF_Transfer_Model",
        tags={"dragonfly", "honeybee", "import", "export", "dfjson", "geojson", "convert", "target"},
        timeout=60,
    )
    def DF_Transfer_Model(
        garden_root: str,
        operation: Literal["import_file", "export_file", "to_honeybee", "from_honeybee"],
        model_target: dict[str, Any] | None = None,
        # import_file / export_file parameters
        file_path: str | None = None,
        file_type: Literal[
            "dfjson",
            "geojson",
            "dfpkl",
            "pomf",
            "osm",
            "idf",
            "gbxml",
            "sdd",
            "rad",
            "rad_folder",
        ]
        | None = None,
        identifier: str | None = None,
        artifact_name: str | None = None,
        set_base: bool = True,
        include_body: bool = False,
        location: dict[str, Any] | None = None,
        point: list[float] | None = None,
        all_polygons_to_buildings: bool = False,
        existing_to_context: bool = False,
        units: str = "Meters",
        tolerance: float | None = None,
        angle_tolerance: float = 1.0,
        # to_honeybee parameters
        object_per_model: Literal["District", "Building", "Story", "Room2D"] = "Building",
        shade_distance: float | None = None,
        use_multiplier: bool = True,
        exclude_plenums: bool = False,
        cap: bool = False,
        solve_ceiling_adjacencies: bool = False,
        merge_method: str | None = None,
        enforce_adj: bool = True,
        enforce_solid: bool = True,
        # from_honeybee parameters
        honeybee_model_target: dict[str, Any] | None = None,
        conversion_method: Literal["AllRoom2D", "ExtrudedOnly"] = "AllRoom2D",
    ) -> dict[str, Any]:
        """Import or export DFJSON/GeoJSON/DFPKL/POMF/OSM/IDF/gbXML/SDD/RAD files, or convert between Dragonfly and Honeybee."""
        if operation == "import_file":
            if not file_path or not file_type:
                raise ValueError(
                    "file_path and file_type are required for operation='import_file'."
                )
            return import_dragonfly_model_file(
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
                conversion_method=conversion_method,
            )

        if operation == "export_file":
            if not file_type:
                raise ValueError("file_type is required for operation='export_file'.")
            return export_dragonfly_model_file(
                garden_root=garden_root,
                model_target=model_target,
                file_type=file_type,
                artifact_name=artifact_name,
                include_body=include_body,
                location=location,
                point=point,
                tolerance=tolerance,
            )

        if operation == "to_honeybee":
            return dragonfly_model_to_honeybee(
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

        return honeybee_model_to_dragonfly(
            garden_root=garden_root,
            identifier=identifier or "dragonfly_from_honeybee",
            honeybee_model_target=honeybee_model_target,
            conversion_method=conversion_method,
            set_base=set_base,
        )

    @mcp.tool(
        name="DF_To_Visualization_Set",
        tags={"dragonfly", "visualization", "visualization-set", "display", "target"},
        timeout=45,
    )
    def DF_To_Visualization_Set(
        garden_root: str,
        mode: Literal[
            "model",
            "targets",
            "attribute",
            "envelope_edges",
            "comparison",
            "opening_projection",
        ] = "model",
        model_target: dict[str, Any] | None = None,
        # targets mode
        target: dict[str, Any] | None = None,
        targets: list[dict[str, Any]] | None = None,
        selection: dict[str, Any] | None = None,
        # attribute mode
        attribute_result: dict[str, Any] | None = None,
        attribute: str | None = None,
        room_attrs: list[Any] | None = None,
        face_attrs: list[Any] | None = None,
        # comparison / opening_projection mode
        base_model_target: dict[str, Any] | None = None,
        incoming_model_target: dict[str, Any] | None = None,
        honeybee_model_target: dict[str, Any] | None = None,
        wall_modifier_data: Any = None,
        projection_distance: float = 0,
        angle_tolerance: float | None = None,
        exclude_existing_openings: bool = True,
        # model mode options
        view_mode: str | None = None,
        use_multiplier: bool = True,
        exclude_plenums: bool = False,
        solve_ceiling_adjacencies: bool = False,
        merge_method: str = "None",
        color_by: str | None = "type",
        include_wireframe: bool = True,
        use_mesh: bool = True,
        hide_color_by: bool = False,
        grid_display_mode: str = "Default",
        hide_grid: bool = False,
        reset_coordinates: bool = False,
        # envelope_edges options
        coplanar_type: str = "FloorPlatesOnly",
        mullion_thickness: float | None = None,
        # common output options
        name: str | None = None,
        return_visualization_set: bool = True,
    ) -> dict[str, Any]:
        """Convert a Dragonfly Model, targets/selection, attributes, edges, opening projection, or diff to VisualizationSet."""
        if mode == "model":
            return dragonfly_model_to_visualization_set(
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

        if mode == "targets":
            return dragonfly_targets_to_visualization_set(
                garden_root=garden_root,
                target=target,
                selection=selection,
                targets=targets,
                model_target=model_target,
                name=name,
                return_visualization_set=return_visualization_set,
            )

        if mode == "attribute":
            if (
                attribute_result is None
                and attribute is None
                and room_attrs is None
                and face_attrs is None
            ):
                raise ValueError(
                    "Provide attribute_result, attribute, room_attrs, or face_attrs for mode='attribute'."
                )
            return dragonfly_room2d_attribute_to_visualization_set(
                garden_root=garden_root,
                attribute_result=attribute_result,
                attribute=attribute,
                room_attrs=room_attrs,
                face_attrs=face_attrs,
                model_target=model_target,
                name=name,
                return_visualization_set=return_visualization_set,
            )

        if mode == "envelope_edges":
            return dragonfly_model_envelope_edges_to_visualization_set(
                garden_root=garden_root,
                model_target=model_target,
                coplanar_type=coplanar_type,
                mullion_thickness=mullion_thickness,
                reset_coordinates=reset_coordinates,
                name=name,
                return_visualization_set=return_visualization_set,
            )

        if mode == "opening_projection":
            return dragonfly_opening_projection_to_visualization_set(
                garden_root=garden_root,
                honeybee_model_target=honeybee_model_target,
                model_target=model_target,
                wall_modifier_data=wall_modifier_data,
                projection_distance=projection_distance,
                angle_tolerance=angle_tolerance,
                exclude_existing_openings=exclude_existing_openings,
                reset_coordinates=reset_coordinates,
                name=name,
                return_visualization_set=return_visualization_set,
            )

        if base_model_target is None or incoming_model_target is None:
            raise ValueError(
                "base_model_target and incoming_model_target are required for mode='comparison'."
            )
        return dragonfly_models_to_comparison_visualization_set(
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
        name="DF_Validate_Model",
        tags={"dragonfly", "validate", "qa", "target"},
        timeout=30,
    )
    def DF_Validate_Model(
        garden_root: str,
        model_target: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate a Dragonfly Model for geometry, adjacency, and property issues."""
        return validate_dragonfly_model(
            garden_root=garden_root,
            model_target=model_target,
        )
