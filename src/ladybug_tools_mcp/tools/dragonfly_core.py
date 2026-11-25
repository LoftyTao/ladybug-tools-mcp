"""Consolidated MCP tools for Dragonfly models, geometry, properties, and display."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core._schemas import (
    validate_df_apply_properties_inputs,
    validate_dragonfly_batch_item,
)
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
from ladybug_tools_mcp.contracts import (
    ArtifactResultModel,
    BuildingModelTargetRef,
    BuildingObjectTargetRef,
    MutationResultModel,
    QueryResultModel,
    ValidationResultModel,
    dump_input,
    dump_target,
    dump_targets,
    make_report,
    validate_output,
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
    creator = create_dragonfly_room2d if object_type == "room2d" else create_dragonfly_context_shade
    current_model_target = model_target
    results: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []

    for index, raw_item in enumerate(items):
        try:
            validated_item = validate_dragonfly_batch_item(object_type, raw_item)
        except ValueError as exc:
            raise ValueError(f"items[{index}]: {exc}") from exc
        item_model_target = dump_target(validated_item.pop("model_target", current_model_target))
        kwargs: dict[str, Any] = {
            "garden_root": garden_root,
            "model_target": item_model_target,
            **validated_item,
        }
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
        garden_root: Annotated[
            str,
            Field(description="Garden root directory."),
        ],
        identifier: Annotated[
            str,
            Field(description="Unique Dragonfly Model identifier."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional human-readable Model display name."),
        ] = None,
        unit_system: Annotated[
            Literal["Metric", "Imperial"] | None,
            Field(description="Unit system preset ('Metric' or 'Imperial') when units is omitted."),
        ] = None,
        units: Annotated[
            Literal["Meters", "Millimeters", "Feet", "Inches", "Centimeters"] | None,
            Field(description="Explicit Model length units (overrides unit_system)."),
        ] = None,
        tolerance: Annotated[
            float | None,
            Field(gt=0.0, description="Model geometric tolerance in model units."),
        ] = None,
        angle_tolerance: Annotated[
            float,
            Field(gt=0.0, description="Model angular tolerance in degrees."),
        ] = 1.0,
        save_back: Annotated[
            bool,
            Field(description="Persist the created Model into the Garden."),
        ] = True,
        set_base: Annotated[
            bool,
            Field(description="Register this Model as the active Garden base Dragonfly model."),
        ] = True,
        return_object_dict: Annotated[
            bool,
            Field(description="Include full serialized DFJSON dictionary in response."),
        ] = False,
        latitude: Annotated[
            float | None,
            Field(ge=-90.0, le=90.0, description="Optional site latitude in degrees for geographic properties."),
        ] = None,
        longitude: Annotated[
            float | None,
            Field(ge=-180.0, le=180.0, description="Optional site longitude in degrees for geographic properties."),
        ] = None,
    ) -> MutationResultModel:
        """Create a Dragonfly Model in the Garden workspace.

        Uses ``units`` when specified, or derives Meters/Feet from ``unit_system``.
        Returns a Garden target and summary_view; set ``return_object_dict=True``
        to include the full DFJSON dictionary.
        """
        resolved_units = units
        if resolved_units is None:
            resolved_units = "Feet" if unit_system == "Imperial" else "Meters"
        return validate_output(
            MutationResultModel,
            create_dragonfly_model(
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
            ),
        )

    @mcp.tool(
        name="DF_Create_Objects",
        tags={"dragonfly", "author", "room2d", "story", "building", "context-shade", "target"},
        timeout=30,
    )
    def DF_Create_Objects(
        garden_root: Annotated[
            str,
            Field(description="Garden root directory."),
        ],
        object_type: Annotated[
            Literal[
                "room2d",
                "story",
                "building",
                "building_from_footprint",
                "building_from_all_story_geometry",
                "context_shade",
                "add_stories_to_building",
            ],
            Field(description="Dragonfly object category or builder mode to execute."),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Object identifier (required for single-object modes)."),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional human-readable display name."),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Dragonfly Model target (defaults to active model)."),
        ] = None,
        items: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Batch object definitions for room2d or context_shade creation."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Include full DFJSON object_dict in response."),
        ] = False,
        # room2d parameters
        floor_height: Annotated[
            float | None,
            Field(description="Floor elevation in model units for room2d or story."),
        ] = None,
        vertices: Annotated[
            list[list[float]] | None,
            Field(description="2D/3D polygon footprint vertices for room2d or context_shade."),
        ] = None,
        floor_to_ceiling_height: Annotated[
            float | None,
            Field(gt=0.0, description="Floor-to-ceiling height of the Room2D."),
        ] = None,
        is_ground_contact: Annotated[
            bool,
            Field(description="Mark Room2D bottom face as ground-contact."),
        ] = False,
        is_top_exposed: Annotated[
            bool,
            Field(description="Mark Room2D top face as exposed to outdoors."),
        ] = False,
        x_dim: Annotated[
            float | None,
            Field(gt=0.0, description="Rectangular footprint X dimension."),
        ] = None,
        y_dim: Annotated[
            float | None,
            Field(gt=0.0, description="Rectangular footprint Y dimension."),
        ] = None,
        origin: Annotated[
            list[float] | None,
            Field(description="Origin [x, y] or [x, y, z] for rectangular Room2D/ContextShade."),
        ] = None,
        height: Annotated[
            float | None,
            Field(gt=0.0, description="Extrusion height for Room2D box or ContextShade."),
        ] = None,
        story_number: Annotated[
            int | None,
            Field(description="Optional story index associated with Room2D."),
        ] = None,
        ceiling_plenum_depth: Annotated[
            float | None,
            Field(ge=0.0, description="Ceiling plenum depth in model units."),
        ] = None,
        floor_plenum_depth: Annotated[
            float | None,
            Field(ge=0.0, description="Floor plenum depth in model units."),
        ] = None,
        # story parameters
        room2d_targets: Annotated[
            list[BuildingObjectTargetRef] | None,
            Field(description="Room2D targets grouped into the new Story."),
        ] = None,
        floor_to_floor_height: Annotated[
            float | None,
            Field(gt=0.0, description="Story floor-to-floor height in model units."),
        ] = None,
        multiplier: Annotated[
            int,
            Field(ge=1, description="Story vertical multiplier count (>= 1)."),
        ] = 1,
        story_type: Annotated[
            Literal["Standard", "CeilingPlenum", "FloorPlenum"],
            Field(description="Story classification: Standard, CeilingPlenum, or FloorPlenum."),
        ] = "Standard",
        # building / add_stories_to_building parameters
        story_targets: Annotated[
            list[BuildingObjectTargetRef] | None,
            Field(description="Story targets attached to the Building."),
        ] = None,
        sort_stories: Annotated[
            bool,
            Field(description="Sort building stories by floor_height from bottom to top."),
        ] = True,
        separate_top_bottom_floors: Annotated[
            bool,
            Field(description="Split multiplier stories into separate bottom/middle/top stories."),
        ] = False,
        roof_geometry: Annotated[
            Any,
            Field(description="Optional pitched/custom roof Face3D geometry for building."),
        ] = None,
        basement_count: Annotated[
            int,
            Field(ge=0, description="Number of bottom stories marked as basements (>= 0)."),
        ] = 0,
        basement_remove_windows: Annotated[
            bool,
            Field(description="Remove exterior windows on basement stories."),
        ] = False,
        building_identifier: Annotated[
            str | None,
            Field(description="Target Building ID for add_stories_to_building."),
        ] = None,
        story_identifiers: Annotated[
            list[str] | None,
            Field(description="Story identifiers to attach to the Building."),
        ] = None,
        # building_from_footprint / building_from_all_story_geometry parameters
        footprints: Annotated[
            list[Any] | None,
            Field(description="Massing footprint polygons per story for building_from_footprint."),
        ] = None,
        all_story_geometry: Annotated[
            list[list[Any]] | None,
            Field(description="Per-story Face3D/polygon room footprints for building_from_all_story_geometry."),
        ] = None,
        floor_to_floor_heights: Annotated[
            list[float] | None,
            Field(description="Floor-to-floor heights matching footprints or all_story_geometry."),
        ] = None,
        perimeter_offset: Annotated[
            float | None,
            Field(ge=0.0, description="Core-perimeter split offset when building from footprint."),
        ] = None,
        tolerance: Annotated[
            float | None,
            Field(ge=0.0, description="Geometric tolerance for building creation."),
        ] = None,
        # context_shade parameters
        geometry: Annotated[
            Any,
            Field(description="Explicit Face3D/Mesh3D geometry for ContextShade."),
        ] = None,
        is_detached: Annotated[
            bool,
            Field(description="Mark ContextShade as site/context rather than building-attached."),
        ] = True,
        context_shade_type: Annotated[
            str | None,
            Field(description="Optional ContextShade preset (e.g., 'tree' or box)."),
        ] = None,
        is_vegetation: Annotated[
            bool | None,
            Field(description="Flag ContextShade as vegetation."),
        ] = None,
        cen_pt: Annotated[
            list[float] | None,
            Field(description="Center point [x, y, z] for tree ContextShade."),
        ] = None,
        radius: Annotated[
            float | None,
            Field(gt=0.0, description="Canopy radius for tree ContextShade."),
        ] = None,
    ) -> MutationResultModel:
        """Create Dragonfly Room2Ds, Stories, Buildings, ContextShades, or attach Stories.

        Supports batch ``items`` creation for ``object_type='room2d'`` and
        ``object_type='context_shade'``.
        """
        dumped_model_target = dump_target(model_target)
        dumped_room2d_targets = dump_targets(room2d_targets)
        dumped_story_targets = dump_targets(story_targets)

        if items is not None:
            if object_type not in {"room2d", "context_shade"}:
                raise ValueError(
                    "items batch creation is only supported for object_type 'room2d' or 'context_shade'."
                )
            return validate_output(
                MutationResultModel,
                _create_batch_objects(
                    garden_root=garden_root,
                    object_type=object_type,
                    items=dump_input(items),
                    model_target=dumped_model_target,
                    return_object_dict=return_object_dict,
                ),
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
                model_target=dumped_model_target,
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
            return validate_output(MutationResultModel, _strip_object_dict(result, return_object_dict))

        if object_type == "story":
            return validate_output(
                MutationResultModel,
                create_dragonfly_story(
                    garden_root=garden_root,
                    room2d_targets=dumped_room2d_targets,
                    identifier=identifier,
                    model_target=dumped_model_target,
                    floor_to_floor_height=floor_to_floor_height,
                    floor_height=floor_height,
                    multiplier=multiplier,
                    story_type=story_type,
                    display_name=display_name,
                ),
            )

        if object_type == "building":
            result = create_dragonfly_building(
                garden_root=garden_root,
                story_targets=dumped_story_targets,
                identifier=identifier,
                model_target=dumped_model_target,
                sort_stories=sort_stories,
                display_name=display_name,
                separate_top_bottom_floors=separate_top_bottom_floors,
                roof_geometry=dump_input(roof_geometry),
                basement_count=basement_count,
                basement_remove_windows=basement_remove_windows,
                tolerance=tolerance,
            )
            return validate_output(MutationResultModel, _strip_object_dict(result, return_object_dict))

        if object_type == "building_from_footprint":
            if not identifier:
                raise ValueError(
                    "identifier is required for object_type='building_from_footprint'."
                )
            if footprints is None or floor_to_floor_heights is None:
                raise ValueError(
                    "footprints and floor_to_floor_heights are required for object_type='building_from_footprint'."
                )
            return validate_output(
                MutationResultModel,
                create_dragonfly_building_from_footprint(
                    garden_root=garden_root,
                    identifier=identifier,
                    footprints=footprints,
                    floor_to_floor_heights=floor_to_floor_heights,
                    perimeter_offset=perimeter_offset,
                    model_target=dumped_model_target,
                    display_name=display_name,
                    tolerance=tolerance,
                    roof_geometry=dump_input(roof_geometry),
                    basement_count=basement_count,
                    basement_remove_windows=basement_remove_windows,
                ),
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
            return validate_output(
                MutationResultModel,
                create_dragonfly_building_from_all_story_geometry(
                    garden_root=garden_root,
                    identifier=identifier,
                    all_story_geometry=all_story_geometry,
                    floor_to_floor_heights=floor_to_floor_heights,
                    perimeter_offset=perimeter_offset,
                    model_target=dumped_model_target,
                    display_name=display_name,
                    tolerance=tolerance,
                    roof_geometry=dump_input(roof_geometry),
                    basement_count=basement_count,
                    basement_remove_windows=basement_remove_windows,
                ),
            )

        if object_type == "context_shade":
            if not identifier:
                raise ValueError("identifier is required for object_type='context_shade'.")
            result = create_dragonfly_context_shade(
                garden_root=garden_root,
                identifier=identifier,
                geometry=dump_input(geometry),
                vertices=vertices,
                model_target=dumped_model_target,
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
            return validate_output(MutationResultModel, _strip_object_dict(result, return_object_dict))

        resolved_building_identifier = building_identifier or identifier
        if not resolved_building_identifier:
            raise ValueError(
                "building_identifier (or identifier) is required for object_type='add_stories_to_building'."
            )
        return validate_output(
            MutationResultModel,
            add_dragonfly_stories_to_building(
                garden_root=garden_root,
                building_identifier=resolved_building_identifier,
                story_targets=dumped_story_targets,
                model_target=dumped_model_target,
                story_identifiers=story_identifiers,
                separate_top_bottom_floors=separate_top_bottom_floors,
            ),
        )

    @mcp.tool(
        name="DF_Edit_Object",
        tags={"dragonfly", "edit", "model", "building", "story", "room2d", "target"},
        timeout=30,
    )
    def DF_Edit_Object(
        garden_root: Annotated[
            str,
            Field(description="Garden root directory."),
        ],
        object_type: Annotated[
            Literal["model", "building", "story", "room2d"] | None,
            Field(description="Target Dragonfly object type: model, building, story, or room2d."),
        ] = None,
        target: Annotated[
            BuildingObjectTargetRef | None,
            Field(description="Explicit Dragonfly object or model target reference."),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Dragonfly Model target (defaults to active model)."),
        ] = None,
        building_identifier: Annotated[
            str | None,
            Field(description="Building identifier when editing a Building without target."),
        ] = None,
        story_target: Annotated[
            BuildingObjectTargetRef | None,
            Field(description="Optional Story target reference."),
        ] = None,
        story_identifier: Annotated[
            str | None,
            Field(description="Story identifier when editing a Story without target."),
        ] = None,
        room2d_target: Annotated[
            BuildingObjectTargetRef | None,
            Field(description="Optional Room2D target reference."),
        ] = None,
        room_identifier: Annotated[
            str | None,
            Field(description="Room2D identifier when editing a Room2D without target."),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Updated display_name on the target object."),
        ] = None,
        units: Annotated[
            Literal["Meters", "Millimeters", "Feet", "Inches", "Centimeters"] | None,
            Field(description="Updated Model length units."),
        ] = None,
        convert_geometry: Annotated[
            bool,
            Field(description="Scale geometry coordinates when changing Model units."),
        ] = True,
        tolerance: Annotated[
            float | None,
            Field(gt=0.0, description="Updated Model geometric tolerance."),
        ] = None,
        angle_tolerance: Annotated[
            float | None,
            Field(gt=0.0, description="Updated Model angular tolerance in degrees."),
        ] = None,
        sort_stories: Annotated[
            bool,
            Field(description="Re-sort Building stories from bottom to top."),
        ] = False,
        separate_top_bottom_floors: Annotated[
            bool,
            Field(description="Separate multiplied Building stories into unique top/bottom floors."),
        ] = False,
        floor_height: Annotated[
            float | None,
            Field(description="Updated floor elevation in model units."),
        ] = None,
        floor_to_floor_height: Annotated[
            float | None,
            Field(gt=0.0, description="Updated Story floor-to-floor height."),
        ] = None,
        multiplier: Annotated[
            int | None,
            Field(ge=1, description="Updated Story multiplier count (>= 1)."),
        ] = None,
        vertices: Annotated[
            list[list[float]] | None,
            Field(description="Updated 2D/3D polygon footprint vertices for Room2D."),
        ] = None,
        floor_to_ceiling_height: Annotated[
            float | None,
            Field(gt=0.0, description="Updated Room2D floor-to-ceiling height."),
        ] = None,
        zone: Annotated[
            str | None,
            Field(description="Updated Room2D zone identifier."),
        ] = None,
        is_ground_contact: Annotated[
            bool | None,
            Field(description="Updated ground-contact flag on Room2D."),
        ] = None,
        is_top_exposed: Annotated[
            bool | None,
            Field(description="Updated top-exposed flag on Room2D."),
        ] = None,
        projection_distance: Annotated[
            float,
            Field(description="Optional projection distance when resetting Room2D properties."),
        ] = 0,
    ) -> MutationResultModel:
        """Edit properties of a Dragonfly Model, Building, Story, or Room2D."""
        return validate_output(
            MutationResultModel,
            edit_dragonfly_object(
                garden_root=garden_root,
                object_type=object_type,
                target=dump_target(target),
                model_target=dump_target(model_target),
                building_identifier=building_identifier,
                story_target=dump_target(story_target),
                story_identifier=story_identifier,
                room2d_target=dump_target(room2d_target),
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
            ),
        )

    @mcp.tool(
        name="DF_Remove_Objects",
        tags={"dragonfly", "edit", "remove", "building", "story", "room2d", "context-shade", "target"},
        timeout=30,
    )
    def DF_Remove_Objects(
        garden_root: Annotated[
            str,
            Field(description="Garden root directory."),
        ],
        object_type: Annotated[
            Literal["building", "story", "room2d", "context_shade"] | None,
            Field(description="Object category to remove: building, story, room2d, or context_shade."),
        ] = None,
        object_targets: Annotated[
            list[BuildingObjectTargetRef] | None,
            Field(description="Explicit Dragonfly object target references to remove."),
        ] = None,
        identifiers: Annotated[
            list[str] | None,
            Field(description="Generic object identifiers to remove for object_type."),
        ] = None,
        building_identifier: Annotated[
            str | None,
            Field(description="Parent Building ID when removing Stories."),
        ] = None,
        story_identifiers: Annotated[
            list[str] | None,
            Field(description="Story identifiers to remove."),
        ] = None,
        building_identifiers: Annotated[
            list[str] | None,
            Field(description="Building identifiers to remove."),
        ] = None,
        room2d_identifiers: Annotated[
            list[str] | None,
            Field(description="Room2D identifiers to remove."),
        ] = None,
        context_shade_identifiers: Annotated[
            list[str] | None,
            Field(description="ContextShade identifiers to remove."),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Dragonfly Model target (defaults to active model)."),
        ] = None,
    ) -> MutationResultModel:
        """Remove Buildings, Stories from a Building, Room2Ds, or ContextShades."""
        return validate_output(
            MutationResultModel,
            remove_dragonfly_objects(
                garden_root=garden_root,
                object_type=object_type,
                object_targets=dump_targets(object_targets),
                identifiers=identifiers,
                building_identifier=building_identifier,
                story_identifiers=story_identifiers,
                building_identifiers=building_identifiers,
                room2d_identifiers=room2d_identifiers,
                context_shade_identifiers=context_shade_identifiers,
                model_target=dump_target(model_target),
            ),
        )

    @mcp.tool(
        name="DF_Process_Geometry",
        tags={"dragonfly", "geometry", "align", "clean", "intersect", "adjacency", "target"},
        timeout=45,
    )
    def DF_Process_Geometry(
        garden_root: Annotated[
            str,
            Field(description="Garden root directory."),
        ],
        operation: Annotated[
            Literal[
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
            Field(description="Dragonfly geometry processing, transform, or model-merge operation."),
        ],
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Dragonfly Model target (defaults to active model)."),
        ] = None,
        host_type: Annotated[
            str | None,
            Field(description="Host scope type: 'room2d', 'story', 'building', or 'model'."),
        ] = None,
        host_target: Annotated[
            BuildingObjectTargetRef | None,
            Field(description="Optional host target scope (Room2D, Story, Building, or Model)."),
        ] = None,
        story_target: Annotated[
            BuildingObjectTargetRef | None,
            Field(description="Optional Story target scope."),
        ] = None,
        story_identifier: Annotated[
            str | None,
            Field(description="Story identifier scope."),
        ] = None,
        room2d_target: Annotated[
            BuildingObjectTargetRef | None,
            Field(description="Optional Room2D target scope."),
        ] = None,
        room_identifier: Annotated[
            str | None,
            Field(description="Room2D identifier scope."),
        ] = None,
        building_identifier: Annotated[
            str | None,
            Field(description="Building identifier scope."),
        ] = None,
        lines: Annotated[
            list[list[list[float]]] | list[dict[str, Any]] | None,
            Field(description="2D alignment lines or LineSegment2D dicts for align operation."),
        ] = None,
        distance: Annotated[
            float,
            Field(ge=0.0, description="Snap/pull distance threshold in model units."),
        ] = 0.5,
        area_threshold: Annotated[
            float,
            Field(ge=0.0, description="Minimum room/hole area threshold in model square units."),
        ] = 10.0,
        join_into_large: Annotated[
            bool,
            Field(description="Merge small rooms into larger neighbors in join_small."),
        ] = False,
        tolerance: Annotated[
            float,
            Field(gt=0.0, description="Geometric tolerance in model units."),
        ] = 0.01,
        intersect: Annotated[
            bool,
            Field(description="Intersect collinear Room2D segments during solve_adjacency."),
        ] = False,
        resolve_window_conflicts: Annotated[
            bool,
            Field(description="Resolve conflicting window parameters across adjacent walls."),
        ] = True,
        remove_duplicate_vertices: Annotated[
            bool,
            Field(description="Remove duplicate consecutive vertices during clean."),
        ] = True,
        remove_colinear_vertices: Annotated[
            bool,
            Field(description="Remove colinear vertices during clean."),
        ] = True,
        remove_short_segments_distance: Annotated[
            float | None,
            Field(gt=0.0, description="Optional minimum segment length for short-edge cleanup."),
        ] = None,
        preserve_wall_props: Annotated[
            bool,
            Field(description="Preserve wall/window parameters across vertex cleanup or joins."),
        ] = True,
        angle_tolerance: Annotated[
            float,
            Field(gt=0.0, description="Angular tolerance in degrees."),
        ] = 1.0,
        perimeter_offset: Annotated[
            float | None,
            Field(gt=0.0, description="Zone depth offset for core_perimeter splitting."),
        ] = None,
        air_boundary: Annotated[
            bool,
            Field(description="Assign AirBoundary between core and perimeter zones."),
        ] = False,
        base_story_id: Annotated[
            str | None,
            Field(description="Reference Story ID for pull_to_story alignment."),
        ] = None,
        pulled_story_ids: Annotated[
            list[str] | None,
            Field(description="Subset of Story IDs pulled toward base_story_id."),
        ] = None,
        coordinate_vertices: Annotated[
            bool,
            Field(description="Coordinate footprint vertices during pull_to_story."),
        ] = True,
        constrain_edges: Annotated[
            bool,
            Field(description="Constrain vertices along existing footprint edges in pull_to_story."),
        ] = False,
        base_name: Annotated[
            str,
            Field(description="Identifier prefix for rooms created by fill_holes."),
        ] = "Room",
        room_identifiers: Annotated[
            list[str] | None,
            Field(description="Room2D identifiers to merge in join_room_2ds."),
        ] = None,
        story_above_identifier: Annotated[
            str | None,
            Field(description="Upper Story ID for split_with_story_above."),
        ] = None,
        target_floor_to_ceiling: Annotated[
            float | None,
            Field(gt=0.0, description="Clear ceiling height target for separate_plenums."),
        ] = None,
        floor_plenum: Annotated[
            bool,
            Field(description="Create floor plenums instead of ceiling plenums in separate_plenums."),
        ] = False,
        transform_type: Annotated[
            Literal["move", "rotate_xy", "scale"] | None,
            Field(description="Geometric transform kind: 'move', 'rotate_xy', or 'scale'."),
        ] = None,
        vector: Annotated[
            list[float] | None,
            Field(description="Translation vector [dx, dy, dz] for transform_type='move'."),
        ] = None,
        angle: Annotated[
            float | None,
            Field(description="Rotation angle in degrees for transform_type='rotate_xy'."),
        ] = None,
        factor: Annotated[
            float | None,
            Field(description="Scale multiplier for transform_type='scale'."),
        ] = None,
        origin: Annotated[
            list[float] | None,
            Field(description="Origin [x, y, z] for rotate_xy or scale transforms."),
        ] = None,
        incoming_model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Second Dragonfly Model target merged by operation='merge_model'."),
        ] = None,
    ) -> MutationResultModel:
        """Run Room2D/Story/Building/Model geometry processing, transforms, or model merge."""
        return validate_output(
            MutationResultModel,
            process_dragonfly_geometry(
                garden_root=garden_root,
                operation=operation,
                model_target=dump_target(model_target),
                host_type=host_type,
                host_target=dump_target(host_target),
                story_target=dump_target(story_target),
                story_identifier=story_identifier,
                room2d_target=dump_target(room2d_target),
                room_identifier=room_identifier,
                building_identifier=building_identifier,
                lines=dump_input(lines),
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
                incoming_model_target=dump_target(incoming_model_target),
            ),
        )

    @mcp.tool(
        name="DF_Apply_Properties",
        tags={"dragonfly", "properties", "energy", "radiance", "window", "shading", "target"},
        timeout=30,
    )
    def DF_Apply_Properties(
        garden_root: Annotated[
            str,
            Field(description="Garden root path."),
        ],
        property_domain: Annotated[
            Literal["energy", "radiance", "window", "shading", "skylight", "clerestory", "wall"],
            Field(description="Property domain."),
        ],
        host_target: Annotated[
            BuildingObjectTargetRef | None,
            Field(description="Target object."),
        ] = None,
        host_type: Annotated[
            Any,
            Field(description="Host scope."),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Model target."),
        ] = None,
        # Energy properties
        program_type_identifier: Annotated[
            Any,
            Field(description="ProgramType ID."),
        ] = None,
        construction_set_identifier: Annotated[
            Any,
            Field(description="ConstructionSet ID."),
        ] = None,
        program_type: Annotated[
            Any,
            Field(description="ProgramType."),
        ] = None,
        construction_set: Annotated[
            Any,
            Field(description="ConstructionSet."),
        ] = None,
        hvac: Annotated[
            Any,
            Field(description="HVAC."),
        ] = None,
        shw: Annotated[
            Any,
            Field(description="SHW."),
        ] = None,
        person_count: Annotated[
            Any,
            Field(description="Occupants."),
        ] = None,
        lighting_watts: Annotated[
            Any,
            Field(description="Lighting W."),
        ] = None,
        electric_equipment_watts: Annotated[
            Any,
            Field(description="Electric W."),
        ] = None,
        gas_equipment_watts: Annotated[
            Any,
            Field(description="Gas W."),
        ] = None,
        hot_water_flow: Annotated[
            Any,
            Field(description="SHW flow."),
        ] = None,
        infiltration_ach: Annotated[
            Any,
            Field(description="Infil. ACH."),
        ] = None,
        daylighting_control: Annotated[
            Any,
            Field(description="Daylight ctrl."),
        ] = None,
        daylight_center: Annotated[
            Any,
            Field(description="Daylight pt."),
        ] = None,
        window_vent_control: Annotated[
            Any,
            Field(description="Vent ctrl."),
        ] = None,
        window_vent_opening: Annotated[
            Any,
            Field(description="Vent open."),
        ] = None,
        fans: Annotated[
            Any,
            Field(description="Vent fans list."),
        ] = None,
        remove_existing_fans: Annotated[
            bool,
            Field(description="Clear fans."),
        ] = False,
        process_loads: Annotated[
            Any,
            Field(description="Process loads list."),
        ] = None,
        remove_existing_process_loads: Annotated[
            bool,
            Field(description="Clear loads."),
        ] = False,
        diversify: Annotated[
            Any,
            Field(description="Diversify."),
        ] = None,
        ceiling_plenum_construction: Annotated[
            Any,
            Field(description="Ceiling plenum."),
        ] = None,
        floor_plenum_construction: Annotated[
            Any,
            Field(description="Floor plenum."),
        ] = None,
        construction: Annotated[
            Any,
            Field(description="Construction."),
        ] = None,
        transmittance_schedule: Annotated[
            Any,
            Field(description="Schedule."),
        ] = None,
        # Radiance properties
        modifier_set_identifier: Annotated[
            Any,
            Field(description="ModifierSet ID."),
        ] = None,
        modifier_set: Annotated[
            Any,
            Field(description="ModifierSet."),
        ] = None,
        modifier: Annotated[
            Any,
            Field(description="Modifier."),
        ] = None,
        grid_parameter_type: Annotated[
            Any,
            Field(description="Grid type."),
        ] = None,
        grid_dimension: Annotated[
            Any,
            Field(description="Grid size."),
        ] = None,
        grid_offset: Annotated[
            Any,
            Field(description="Grid offset."),
        ] = None,
        wall_offset: Annotated[
            float,
            Field(description="Wall inset."),
        ] = 0,
        face_type: Annotated[
            str,
            Field(description="Face type."),
        ] = "Wall",
        aperture_type: Annotated[
            str,
            Field(description="Aperture type."),
        ] = "All",
        punched_geometry: Annotated[
            bool,
            Field(description="Punched."),
        ] = False,
        dir_count: Annotated[
            int,
            Field(description="Dirs."),
        ] = 8,
        start_vector: Annotated[
            Any,
            Field(description="Start vec."),
        ] = None,
        mesh_radius: Annotated[
            Any,
            Field(description="Mesh rad."),
        ] = None,
        include_mesh: Annotated[
            bool,
            Field(description="Mesh."),
        ] = True,
        remove_existing_grid_parameters: Annotated[
            bool,
            Field(description="Clear grids."),
        ] = False,
        # Window / Shading / Skylight / Clerestory / Wall parameters
        window_parameter: Annotated[
            Any,
            Field(description="WindowParam."),
        ] = None,
        shading_parameter: Annotated[
            Any,
            Field(description="ShadingParam."),
        ] = None,
        skylight_parameter: Annotated[
            Any,
            Field(description="SkylightParam."),
        ] = None,
        clerestory_parameter: Annotated[
            Any,
            Field(description="ClerestoryParam."),
        ] = None,
        parameter_type: Annotated[
            Any,
            Field(description="Param type."),
        ] = None,
        application_scope: Annotated[
            str,
            Field(description="Apply scope."),
        ] = "all_outdoor",
        segment_index: Annotated[
            Any,
            Field(description="Seg idx."),
        ] = None,
        window_ratio: Annotated[
            Any,
            Field(description="Win ratio."),
        ] = None,
        rect_split: Annotated[
            bool,
            Field(description="Rect split."),
        ] = True,
        window_height: Annotated[
            Any,
            Field(description="Win height."),
        ] = None,
        sill_height: Annotated[
            Any,
            Field(description="Sill height."),
        ] = None,
        horizontal_separation: Annotated[
            Any,
            Field(description="Horiz gap."),
        ] = None,
        vertical_separation: Annotated[
            float,
            Field(description="Vert gap."),
        ] = 0,
        width: Annotated[
            Any,
            Field(description="Width."),
        ] = None,
        height: Annotated[
            Any,
            Field(description="Win height."),
        ] = None,
        window_area: Annotated[
            Any,
            Field(description="Win area."),
        ] = None,
        window_width: Annotated[
            Any,
            Field(description="Win width."),
        ] = None,
        origins: Annotated[
            Any,
            Field(description="Origins."),
        ] = None,
        widths: Annotated[
            Any,
            Field(description="Widths."),
        ] = None,
        heights: Annotated[
            Any,
            Field(description="Heights."),
        ] = None,
        polygons: Annotated[
            Any,
            Field(description="Polygons."),
        ] = None,
        are_doors: Annotated[
            Any,
            Field(description="Are doors."),
        ] = None,
        depth: Annotated[
            Any,
            Field(description="Depth."),
        ] = None,
        angle: Annotated[
            float,
            Field(description="Angle deg."),
        ] = 0,
        distance: Annotated[
            Any,
            Field(description="Distance."),
        ] = None,
        louver_count: Annotated[
            Any,
            Field(description="Louvers."),
        ] = None,
        offset: Annotated[
            float,
            Field(description="Offset."),
        ] = 0,
        contour_vector: Annotated[
            Any,
            Field(description="Contour vec."),
        ] = None,
        flip_start_side: Annotated[
            bool,
            Field(description="Flip start."),
        ] = False,
        skylight_area: Annotated[
            Any,
            Field(description="Sky area."),
        ] = None,
        skylight_ratio: Annotated[
            Any,
            Field(description="Sky ratio."),
        ] = None,
        spacing: Annotated[
            Any,
            Field(description="Spacing."),
        ] = None,
        story_identifier: Annotated[
            Any,
            Field(description="Story ID."),
        ] = None,
        air_boundary: Annotated[
            Any,
            Field(description="Air bnd."),
        ] = None,
        air_boundaries: Annotated[
            Any,
            Field(description="Air bnds."),
        ] = None,
        boundary_condition: Annotated[
            Any,
            Field(description="Boundary cond."),
        ] = None,
        guide_lines: Annotated[
            Any,
            Field(description="Guide lines."),
        ] = None,
        room_identifiers: Annotated[
            Any,
            Field(description="Room IDs."),
        ] = None,
        wall_modifiers: Annotated[
            Any,
            Field(description="Wall mods."),
        ] = None,
        tolerance: Annotated[
            float,
            Field(description="Tolerance."),
        ] = 0.01,
    ) -> MutationResultModel:
        """Apply Energy, Radiance, Window, Shading, Skylight, Clerestory, or Wall properties."""
        dumped_host_target = dump_target(host_target)
        dumped_model_target = dump_target(model_target)
        dumped_daylighting_control = dump_input(daylighting_control)
        dumped_daylight_center = dump_input(daylight_center)
        dumped_window_vent_control = dump_input(window_vent_control)
        dumped_window_vent_opening = dump_input(window_vent_opening)
        dumped_fans = dump_input(fans)
        dumped_process_loads = dump_input(process_loads)
        dumped_diversify = dump_input(diversify)
        dumped_window_param = dump_input(window_parameter)
        dumped_shading_param = dump_input(shading_parameter)
        dumped_skylight_param = dump_input(skylight_parameter)
        dumped_clerestory_param = dump_input(clerestory_parameter)
        dumped_boundary_condition = dump_input(boundary_condition)
        dumped_wall_modifiers = dump_input(wall_modifiers)

        validated = validate_df_apply_properties_inputs(
            host_type=host_type,
            program_type_identifier=program_type_identifier,
            construction_set_identifier=construction_set_identifier,
            person_count=person_count,
            lighting_watts=lighting_watts,
            electric_equipment_watts=electric_equipment_watts,
            gas_equipment_watts=gas_equipment_watts,
            hot_water_flow=hot_water_flow,
            infiltration_ach=infiltration_ach,
            daylighting_control=dumped_daylighting_control,
            daylight_center=dumped_daylight_center,
            window_vent_control=dumped_window_vent_control,
            window_vent_opening=dumped_window_vent_opening,
            fans=dumped_fans,
            process_loads=dumped_process_loads,
            diversify=dumped_diversify,
            modifier_set_identifier=modifier_set_identifier,
            grid_parameter_type=grid_parameter_type,
            grid_dimension=grid_dimension,
            grid_offset=grid_offset,
            face_type=face_type,
            aperture_type=aperture_type,
            dir_count=dir_count,
            start_vector=start_vector,
            mesh_radius=mesh_radius,
            window_parameter=dumped_window_param,
            shading_parameter=dumped_shading_param,
            skylight_parameter=dumped_skylight_param,
            clerestory_parameter=dumped_clerestory_param,
            parameter_type=parameter_type,
            application_scope=application_scope,
            segment_index=segment_index,
            window_ratio=window_ratio,
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
            depth=depth,
            distance=distance,
            louver_count=louver_count,
            contour_vector=contour_vector,
            skylight_area=skylight_area,
            skylight_ratio=skylight_ratio,
            spacing=spacing,
            story_identifier=story_identifier,
            air_boundary=air_boundary,
            air_boundaries=air_boundaries,
            boundary_condition=dumped_boundary_condition,
            guide_lines=guide_lines,
            room_identifiers=room_identifiers,
            wall_modifiers=dumped_wall_modifiers,
            tolerance=tolerance,
        )
        host_type = validated["host_type"]
        application_scope = validated["application_scope"]
        face_type = validated["face_type"]
        aperture_type = validated["aperture_type"]
        dir_count = validated["dir_count"]
        vertical_separation = validated["vertical_separation"]
        tolerance = validated["tolerance"]

        if property_domain == "energy":
            if dumped_host_target is None and host_type != "model":
                raise ValueError(
                    "host_target is required for property_domain='energy' (or set host_type='model')."
                )
            return validate_output(
                MutationResultModel,
                apply_dragonfly_energy_properties(
                    garden_root=garden_root,
                    host_target=dumped_host_target,
                    model_target=dumped_model_target,
                    program_type_identifier=program_type_identifier,
                    construction_set_identifier=construction_set_identifier,
                    program_type=dump_input(program_type),
                    construction_set=dump_input(construction_set),
                    hvac=dump_input(hvac),
                    shw=dump_input(shw),
                    person_count=person_count,
                    lighting_watts=lighting_watts,
                    electric_equipment_watts=electric_equipment_watts,
                    gas_equipment_watts=gas_equipment_watts,
                    hot_water_flow=hot_water_flow,
                    infiltration_ach=infiltration_ach,
                    daylighting_control=dumped_daylighting_control,
                    daylight_center=dumped_daylight_center,
                    window_vent_control=dumped_window_vent_control,
                    window_vent_opening=dumped_window_vent_opening,
                    fans=dumped_fans,
                    remove_existing_fans=remove_existing_fans,
                    process_loads=dumped_process_loads,
                    remove_existing_process_loads=remove_existing_process_loads,
                    diversify=dumped_diversify,
                    ceiling_plenum_construction=dump_input(ceiling_plenum_construction),
                    floor_plenum_construction=dump_input(floor_plenum_construction),
                    construction=dump_input(construction),
                    transmittance_schedule=dump_input(transmittance_schedule),
                ),
            )

        if property_domain == "radiance":
            if dumped_host_target is None:
                raise ValueError("host_target is required for property_domain='radiance'.")
            return validate_output(
                MutationResultModel,
                apply_dragonfly_radiance_properties(
                    garden_root=garden_root,
                    host_target=dumped_host_target,
                    model_target=dumped_model_target,
                    modifier_set_identifier=modifier_set_identifier,
                    modifier_set=dump_input(modifier_set),
                    modifier=dump_input(modifier),
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
                ),
            )

        if property_domain == "window":
            resolved_window = dumped_window_param
            if resolved_window is None:
                if parameter_type is None:
                    raise ValueError(
                        "Provide window_parameter dict or parameter_type with its fields."
                    )
                if dumped_host_target is None and host_type is None:
                    return validate_output(
                        MutationResultModel,
                        create_dragonfly_window_parameter(
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
                        ),
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
            return validate_output(
                MutationResultModel,
                apply_dragonfly_window_parameter(
                    garden_root=garden_root,
                    window_parameter=resolved_window,
                    host_type=host_type,
                    host_target=dumped_host_target,
                    model_target=dumped_model_target,
                    application_scope=application_scope,
                    segment_index=segment_index,
                ),
            )

        if property_domain == "shading":
            resolved_shading = dumped_shading_param
            if resolved_shading is None:
                if parameter_type is None or depth is None:
                    raise ValueError(
                        "Provide shading_parameter dict or both parameter_type and depth."
                    )
                if dumped_host_target is None and host_type is None:
                    return validate_output(
                        MutationResultModel,
                        create_dragonfly_shading_parameter(
                            garden_root=garden_root,
                            parameter_type=parameter_type,
                            depth=depth,
                            angle=angle,
                            distance=distance,
                            louver_count=louver_count,
                            offset=offset,
                            contour_vector=contour_vector,
                            flip_start_side=flip_start_side,
                        ),
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
            return validate_output(
                MutationResultModel,
                apply_dragonfly_shading_parameter(
                    garden_root=garden_root,
                    shading_parameter=resolved_shading,
                    host_type=host_type,
                    host_target=dumped_host_target,
                    model_target=dumped_model_target,
                    application_scope=application_scope,
                    segment_index=segment_index,
                ),
            )

        if property_domain == "skylight":
            resolved_skylight = dumped_skylight_param
            if resolved_skylight is None:
                if parameter_type is None:
                    raise ValueError(
                        "Provide skylight_parameter dict or parameter_type with its fields."
                    )
                if dumped_host_target is None and host_type is None:
                    return validate_output(
                        MutationResultModel,
                        create_dragonfly_skylight_parameter(
                            garden_root=garden_root,
                            parameter_type=parameter_type,
                            skylight_area=skylight_area,
                            skylight_ratio=skylight_ratio,
                            spacing=spacing,
                            polygons=polygons,
                            are_doors=are_doors,
                        ),
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
            return validate_output(
                MutationResultModel,
                apply_dragonfly_skylight_parameter(
                    garden_root=garden_root,
                    skylight_parameter=resolved_skylight,
                    host_type=host_type,
                    host_target=dumped_host_target,
                    model_target=dumped_model_target,
                ),
            )

        if property_domain == "clerestory":
            if dumped_clerestory_param is None:
                raise ValueError("clerestory_parameter dict is required for property_domain='clerestory'.")
            return validate_output(
                MutationResultModel,
                apply_dragonfly_clerestory_parameter(
                    garden_root=garden_root,
                    clerestory_parameter=dumped_clerestory_param,
                    host_target=dumped_host_target,
                    story_identifier=story_identifier,
                    model_target=dumped_model_target,
                ),
            )

        return validate_output(
            MutationResultModel,
            apply_dragonfly_wall_properties(
                garden_root=garden_root,
                host_target=dumped_host_target,
                host_type=host_type,
                model_target=dumped_model_target,
                segment_index=segment_index,
                air_boundary=air_boundary,
                air_boundaries=air_boundaries,
                boundary_condition=dumped_boundary_condition,
                guide_lines=guide_lines,
                room_identifiers=room_identifiers,
                wall_modifiers=dumped_wall_modifiers,
                tolerance=tolerance,
            ),
        )

    @mcp.tool(
        name="DF_Inspect_Model",
        tags={"dragonfly", "inspect", "summary", "geometry", "attributes", "query", "target"},
        timeout=30,
    )
    def DF_Inspect_Model(
        garden_root: Annotated[
            str,
            Field(description="Garden root directory."),
        ],
        view: Annotated[
            Literal[
                "model_summary",
                "properties_summary",
                "geometry_properties",
                "list_attributes",
                "query_by_attribute",
            ],
            Field(description="Inspection view: model_summary, properties_summary, geometry_properties, list_attributes, or query_by_attribute."),
        ] = "model_summary",
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Dragonfly Model target (defaults to active model)."),
        ] = None,
        target: Annotated[
            BuildingObjectTargetRef | None,
            Field(description="Target Dragonfly object for geometry_properties."),
        ] = None,
        attributes: Annotated[
            list[str] | None,
            Field(description="Specific geometry properties to return in geometry_properties."),
        ] = None,
        attribute: Annotated[
            str | None,
            Field(description="Room2D attribute name for view='query_by_attribute'."),
        ] = None,
        operator: Annotated[
            Literal[
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
            | None,
            Field(description="Comparison operator for query_by_attribute."),
        ] = None,
        value: Annotated[
            Any,
            Field(description="Comparison value for query_by_attribute."),
        ] = None,
    ) -> QueryResultModel:
        """Inspect Dragonfly model summaries, Energy/Radiance properties, geometry, or Room2D attributes."""
        dumped_model_target = dump_target(model_target)
        dumped_target = dump_target(target)

        if view == "model_summary":
            return validate_output(
                QueryResultModel,
                get_dragonfly_model_summary(
                    garden_root=garden_root,
                    model_target=dumped_model_target,
                ),
            )
        if view == "properties_summary":
            return validate_output(
                QueryResultModel,
                get_dragonfly_properties_summary(
                    garden_root=garden_root,
                    model_target=dumped_model_target,
                ),
            )
        if view == "geometry_properties":
            return validate_output(
                QueryResultModel,
                get_dragonfly_geometry_properties(
                    garden_root=garden_root,
                    target=dumped_target,
                    model_target=dumped_model_target,
                    attributes=attributes,
                ),
            )
        if view == "list_attributes":
            return validate_output(
                QueryResultModel,
                list_dragonfly_room2d_attributes(
                    garden_root=garden_root,
                    model_target=dumped_model_target,
                ),
            )
        if not attribute:
            raise ValueError("attribute is required for view='query_by_attribute'.")
        return validate_output(
            QueryResultModel,
            query_dragonfly_room2ds_by_attribute(
                garden_root=garden_root,
                attribute=attribute,
                model_target=dumped_model_target,
                operator=operator,
                value=value,
            ),
        )

    @mcp.tool(
        name="DF_Search_Objects",
        tags={"dragonfly", "search", "building", "story", "room2d", "context-shade", "target"},
        timeout=20,
    )
    def DF_Search_Objects(
        garden_root: Annotated[
            str,
            Field(description="Garden root directory."),
        ],
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Dragonfly Model target (defaults to active model)."),
        ] = None,
        object_type: Annotated[
            Literal["all", "building", "story", "room2d", "context_shade"],
            Field(description="Dragonfly object category filter: all, building, story, room2d, or context_shade."),
        ] = "all",
        identifier: Annotated[
            str | None,
            Field(description="Exact object identifier filter."),
        ] = None,
        query: Annotated[
            str | None,
            Field(description="Case-insensitive substring search across identifiers and display names."),
        ] = None,
        building_identifier: Annotated[
            str | None,
            Field(description="Restrict search to objects within this Building ID."),
        ] = None,
        story_identifier: Annotated[
            str | None,
            Field(description="Restrict search to objects within this Story ID."),
        ] = None,
        children_scope: Annotated[
            Literal["none", "direct", "all"] | BuildingObjectTargetRef | None,
            Field(description="Children expansion depth ('none', 'direct', 'all') or parent object target."),
        ] = None,
        include_counts: Annotated[
            bool,
            Field(description="Include child object counts per match."),
        ] = False,
        include_geometry: Annotated[
            bool,
            Field(description="Include footprint/geometry fields in matches."),
        ] = False,
        include_properties: Annotated[
            bool,
            Field(description="Include Energy/Radiance property summaries in matches."),
        ] = False,
        limit: Annotated[
            int | None,
            Field(ge=1, description="Maximum number of matches returned."),
        ] = None,
    ) -> QueryResultModel:
        """Search and inspect Dragonfly Buildings, Stories, Room2Ds, or ContextShades."""
        return validate_output(
            QueryResultModel,
            search_dragonfly_model_objects(
                garden_root=garden_root,
                model_target=dump_target(model_target),
                object_type=object_type,
                identifier=identifier,
                query=query,
                building_identifier=building_identifier,
                story_identifier=story_identifier,
                children_scope=dump_input(children_scope),
                include_counts=include_counts,
                include_geometry=include_geometry,
                include_properties=include_properties,
                limit=limit,
            ),
        )

    @mcp.tool(
        name="DF_Transfer_Model",
        tags={"dragonfly", "honeybee", "import", "export", "dfjson", "geojson", "convert", "target"},
        timeout=60,
    )
    def DF_Transfer_Model(
        garden_root: Annotated[
            str,
            Field(description="Garden root directory."),
        ],
        operation: Annotated[
            Literal["import_file", "export_file", "to_honeybee", "from_honeybee"],
            Field(description="Transfer mode: import_file, export_file, to_honeybee, or from_honeybee."),
        ],
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Dragonfly Model target (defaults to active model)."),
        ] = None,
        # import_file / export_file parameters
        file_path: Annotated[
            str | None,
            Field(description="Source file path for import_file (or destination path for export_file)."),
        ] = None,
        file_type: Annotated[
            Literal[
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
            | None,
            Field(description="Model interchange format: dfjson, geojson, dfpkl, pomf, osm, idf, gbxml, sdd, rad, or rad_folder."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Identifier for newly imported or converted Model."),
        ] = None,
        artifact_name: Annotated[
            str | None,
            Field(description="Base filename for exported model artifact."),
        ] = None,
        set_base: Annotated[
            bool,
            Field(description="Set the resulting Model as the active Garden base model."),
        ] = True,
        include_body: Annotated[
            bool,
            Field(description="Include serialized model dictionary in response."),
        ] = False,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Ladybug Location dict for GeoJSON origin projection."),
        ] = None,
        point: Annotated[
            list[float] | None,
            Field(description="Reference 2D [lon, lat] point for GeoJSON projection."),
        ] = None,
        all_polygons_to_buildings: Annotated[
            bool,
            Field(description="Convert all GeoJSON polygons to Buildings instead of context."),
        ] = False,
        existing_to_context: Annotated[
            bool,
            Field(description="Import existing GeoJSON footprints as ContextShades."),
        ] = False,
        units: Annotated[
            Literal["Meters", "Millimeters", "Feet", "Inches", "Centimeters"],
            Field(description="Model length units for file import."),
        ] = "Meters",
        tolerance: Annotated[
            float | None,
            Field(gt=0.0, description="Geometric tolerance override."),
        ] = None,
        angle_tolerance: Annotated[
            float,
            Field(gt=0.0, description="Angular tolerance in degrees."),
        ] = 1.0,
        # to_honeybee parameters
        object_per_model: Annotated[
            Literal["District", "Building", "Story", "Room2D"],
            Field(description="Honeybee conversion granularity: District, Building, Story, or Room2D."),
        ] = "Building",
        shade_distance: Annotated[
            float | None,
            Field(ge=0.0, description="Maximum distance for transferring neighbor context shades."),
        ] = None,
        use_multiplier: Annotated[
            bool,
            Field(description="Use Honeybee Zone multipliers instead of expanding stories."),
        ] = True,
        exclude_plenums: Annotated[
            bool,
            Field(description="Exclude plenum stories during Dragonfly-to-Honeybee conversion."),
        ] = False,
        cap: Annotated[
            bool,
            Field(description="Cap solid ceiling/floor boundary conditions on multiplied stories."),
        ] = False,
        solve_ceiling_adjacencies: Annotated[
            bool,
            Field(description="Solve vertical floor/ceiling adjacencies between stacked stories."),
        ] = False,
        merge_method: Annotated[
            Literal["None", "Zones", "PlenumZones", "Stories", "PlenumStories"] | None,
            Field(description="Room2D coplanar merging strategy: None, Zones, PlenumZones, Stories, or PlenumStories."),
        ] = None,
        enforce_adj: Annotated[
            bool,
            Field(description="Enforce adjacent wall matching when exporting to Honeybee."),
        ] = True,
        enforce_solid: Annotated[
            bool,
            Field(description="Enforce closed Room volumes when exporting to Honeybee."),
        ] = True,
        # from_honeybee parameters
        honeybee_model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Source Honeybee Model target for operation='from_honeybee'."),
        ] = None,
        conversion_method: Annotated[
            Literal["AllRoom2D", "ExtrudedOnly"],
            Field(description="Honeybee-to-Dragonfly strategy: AllRoom2D or ExtrudedOnly."),
        ] = "AllRoom2D",
    ) -> ArtifactResultModel:
        """Import or export DFJSON/GeoJSON/DFPKL/POMF/OSM/IDF/gbXML/SDD/RAD files, or convert between Dragonfly and Honeybee."""
        dumped_model_target = dump_target(model_target)
        dumped_hb_target = dump_target(honeybee_model_target)

        if operation == "import_file":
            if not file_path or not file_type:
                raise ValueError(
                    "file_path and file_type are required for operation='import_file'."
                )
            return validate_output(
                ArtifactResultModel,
                import_dragonfly_model_file(
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
                ),
            )

        if operation == "export_file":
            if not file_type:
                raise ValueError("file_type is required for operation='export_file'.")
            return validate_output(
                ArtifactResultModel,
                export_dragonfly_model_file(
                    garden_root=garden_root,
                    model_target=dumped_model_target,
                    file_type=file_type,
                    artifact_name=artifact_name,
                    include_body=include_body,
                    location=location,
                    point=point,
                    tolerance=tolerance,
                ),
            )

        if operation == "to_honeybee":
            return validate_output(
                ArtifactResultModel,
                dragonfly_model_to_honeybee(
                    garden_root=garden_root,
                    model_target=dumped_model_target,
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
                ),
            )

        return validate_output(
            ArtifactResultModel,
            honeybee_model_to_dragonfly(
                garden_root=garden_root,
                identifier=identifier or "dragonfly_from_honeybee",
                honeybee_model_target=dumped_hb_target,
                conversion_method=conversion_method,
                set_base=set_base,
            ),
        )

    @mcp.tool(
        name="DF_To_Visualization_Set",
        tags={"dragonfly", "visualization", "visualization-set", "display", "target"},
        timeout=45,
    )
    def DF_To_Visualization_Set(
        garden_root: Annotated[
            str,
            Field(description="Garden root directory."),
        ],
        mode: Annotated[
            Literal[
                "model",
                "targets",
                "attribute",
                "envelope_edges",
                "comparison",
                "opening_projection",
            ],
            Field(description="Visualization mode: model, targets, attribute, envelope_edges, comparison, or opening_projection."),
        ] = "model",
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Dragonfly Model target (defaults to active model)."),
        ] = None,
        # targets mode
        target: Annotated[
            BuildingObjectTargetRef | None,
            Field(description="Single Dragonfly object target for mode='targets'."),
        ] = None,
        targets: Annotated[
            list[BuildingObjectTargetRef] | None,
            Field(description="List of Dragonfly object targets for mode='targets'."),
        ] = None,
        selection: Annotated[
            dict[str, Any] | None,
            Field(description="Selection payload dict from DF_Search_Objects for mode='targets'."),
        ] = None,
        # attribute mode
        attribute_result: Annotated[
            dict[str, Any] | None,
            Field(description="Attribute query result dict for mode='attribute'."),
        ] = None,
        attribute: Annotated[
            str | None,
            Field(description="Room2D/Face attribute name to visualize in mode='attribute'."),
        ] = None,
        room_attrs: Annotated[
            list[Any] | None,
            Field(description="Room attribute specs for Dragonfly display."),
        ] = None,
        face_attrs: Annotated[
            list[Any] | None,
            Field(description="Face attribute specs for Dragonfly display."),
        ] = None,
        # comparison / opening_projection mode
        base_model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Baseline Dragonfly Model target for mode='comparison'."),
        ] = None,
        incoming_model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Modified Dragonfly Model target for mode='comparison'."),
        ] = None,
        honeybee_model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Honeybee Model target for mode='opening_projection'."),
        ] = None,
        wall_modifier_data: Annotated[
            Any,
            Field(description="Optional wall modifier data for mode='opening_projection'."),
        ] = None,
        projection_distance: Annotated[
            float,
            Field(description="Maximum aperture projection distance for opening_projection."),
        ] = 0,
        angle_tolerance: Annotated[
            float | None,
            Field(gt=0.0, description="Angular tolerance in degrees for opening_projection."),
        ] = None,
        exclude_existing_openings: Annotated[
            bool,
            Field(description="Skip Room2Ds that already have window parameters in opening_projection."),
        ] = True,
        # model mode options
        view_mode: Annotated[
            Literal["quick", "all", "floors", "wireframe", "custom"] | None,
            Field(description="Display preset for mode='model': quick, all, floors, wireframe, or custom."),
        ] = None,
        use_multiplier: Annotated[
            bool,
            Field(description="Display geometry with Story multipliers or expand."),
        ] = True,
        exclude_plenums: Annotated[
            bool,
            Field(description="Hide plenum stories in visualization."),
        ] = False,
        solve_ceiling_adjacencies: Annotated[
            bool,
            Field(description="Solve ceiling/floor adjacencies in visualization preview."),
        ] = False,
        merge_method: Annotated[
            Literal["None", "Zones", "PlenumZones", "Stories", "PlenumStories"],
            Field(description="Room2D merging method for visualization."),
        ] = "None",
        color_by: Annotated[
            Literal["type", "boundary_condition", "None", "none"] | None,
            Field(description="Face coloring mode: 'type', 'boundary_condition', or 'None'."),
        ] = "type",
        include_wireframe: Annotated[
            bool,
            Field(description="Include wireframe outlines in VisualizationSet."),
        ] = True,
        use_mesh: Annotated[
            bool,
            Field(description="Use triangulated meshes instead of Face3D."),
        ] = True,
        hide_color_by: Annotated[
            bool,
            Field(description="Hide colored face geometry layer initially."),
        ] = False,
        grid_display_mode: Annotated[
            Literal["Default", "Points", "Wireframe", "Surface", "SurfaceWithEdges", "None"],
            Field(description="Sensor grid display mode."),
        ] = "Default",
        hide_grid: Annotated[
            bool,
            Field(description="Hide sensor grids layer initially."),
        ] = False,
        reset_coordinates: Annotated[
            bool,
            Field(description="Translate model near world origin in visualization."),
        ] = False,
        # envelope_edges options
        coplanar_type: Annotated[
            Literal["None", "FloorPlatesOnly", "All"],
            Field(description="Coplanar edge filter for envelope_edges: None, FloorPlatesOnly, or All."),
        ] = "FloorPlatesOnly",
        mullion_thickness: Annotated[
            float | None,
            Field(gt=0.0, description="Optional mullion width for envelope_edges visualization."),
        ] = None,
        # common output options
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet display name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(description="Include full VisualizationSet dictionary in response."),
        ] = True,
    ) -> MutationResultModel:
        """Convert a Dragonfly Model, targets/selection, attributes, edges, opening projection, or diff to VisualizationSet."""
        dumped_model_target = dump_target(model_target)
        dumped_target = dump_target(target)
        dumped_targets = dump_targets(targets)

        if mode == "model":
            return validate_output(
                MutationResultModel,
                dragonfly_model_to_visualization_set(
                    garden_root=garden_root,
                    model_target=dumped_model_target,
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
                ),
            )

        if mode == "targets":
            return validate_output(
                MutationResultModel,
                dragonfly_targets_to_visualization_set(
                    garden_root=garden_root,
                    target=dumped_target,
                    selection=dump_input(selection),
                    targets=dumped_targets,
                    model_target=dumped_model_target,
                    name=name,
                    return_visualization_set=return_visualization_set,
                ),
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
            return validate_output(
                MutationResultModel,
                dragonfly_room2d_attribute_to_visualization_set(
                    garden_root=garden_root,
                    attribute_result=dump_input(attribute_result),
                    attribute=attribute,
                    room_attrs=dump_input(room_attrs),
                    face_attrs=dump_input(face_attrs),
                    model_target=dumped_model_target,
                    name=name,
                    return_visualization_set=return_visualization_set,
                ),
            )

        if mode == "envelope_edges":
            return validate_output(
                MutationResultModel,
                dragonfly_model_envelope_edges_to_visualization_set(
                    garden_root=garden_root,
                    model_target=dumped_model_target,
                    coplanar_type=coplanar_type,
                    mullion_thickness=mullion_thickness,
                    reset_coordinates=reset_coordinates,
                    name=name,
                    return_visualization_set=return_visualization_set,
                ),
            )

        if mode == "opening_projection":
            return validate_output(
                MutationResultModel,
                dragonfly_opening_projection_to_visualization_set(
                    garden_root=garden_root,
                    honeybee_model_target=dump_target(honeybee_model_target),
                    model_target=dumped_model_target,
                    wall_modifier_data=dump_input(wall_modifier_data),
                    projection_distance=projection_distance,
                    angle_tolerance=angle_tolerance,
                    exclude_existing_openings=exclude_existing_openings,
                    reset_coordinates=reset_coordinates,
                    name=name,
                    return_visualization_set=return_visualization_set,
                ),
            )

        dumped_base = dump_target(base_model_target)
        dumped_incoming = dump_target(incoming_model_target)
        if dumped_base is None or dumped_incoming is None:
            raise ValueError(
                "base_model_target and incoming_model_target are required for mode='comparison'."
            )
        return validate_output(
            MutationResultModel,
            dragonfly_models_to_comparison_visualization_set(
                garden_root=garden_root,
                base_model_target=dumped_base,
                incoming_model_target=dumped_incoming,
                use_multiplier=use_multiplier,
                exclude_plenums=exclude_plenums,
                solve_ceiling_adjacencies=solve_ceiling_adjacencies,
                merge_method=merge_method,
                reset_coordinates=reset_coordinates,
                name=name,
                return_visualization_set=return_visualization_set,
            ),
        )

    @mcp.tool(
        name="DF_Validate_Model",
        tags={"dragonfly", "validate", "qa", "target"},
        timeout=30,
    )
    def DF_Validate_Model(
        garden_root: Annotated[
            str,
            Field(description="Garden root directory."),
        ],
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Dragonfly Model target (defaults to active model)."),
        ] = None,
    ) -> ValidationResultModel:
        """Validate a Dragonfly Model for geometry, adjacency, and property issues."""
        return validate_output(
            ValidationResultModel,
            validate_dragonfly_model(
                garden_root=garden_root,
                model_target=dump_target(model_target),
            ),
        )
