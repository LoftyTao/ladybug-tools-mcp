"""Dragonfly Display VisualizationSet services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dragonfly.building import Building
from dragonfly.colorobj import ColorRoom2D
from dragonfly.context import ContextShade
from dragonfly_display.model import (
    model_comparison_to_vis_set,
    model_envelope_edges_to_vis_set,
    model_opening_projection_to_vis_set,
    model_to_vis_set,
)
from dragonfly.model import Model
from dragonfly.room2d import Room2D
from dragonfly.story import Story
from honeybee_display.attr import FaceAttribute, RoomAttribute
from ladybug_display.geometry3d import DisplayFace3D
from ladybug_display.visualization import (
    AnalysisGeometry,
    ContextGeometry,
    VisualizationData,
    VisualizationSet,
)

from garden.dragonfly_core.model_io import load_dragonfly_model, resolve_model_target
from garden.dragonfly_core.targets import normalize_dragonfly_object_target
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target as resolve_honeybee_model_target,
)
from garden.paths import slugify_name
from garden.visualize.artifacts import save_visualization_set
from ladybug_tools_mcp.contracts import make_report


def _summarize_visualization_set(
    visualization_set: dict[str, Any],
) -> dict[str, Any]:
    geometry_layers = visualization_set.get("geometry", [])
    layer_identifiers = [
        layer.get("identifier")
        for layer in geometry_layers
        if isinstance(layer, dict) and layer.get("identifier")
    ]
    return {
        "identifier": visualization_set.get("identifier"),
        "display_name": visualization_set.get("display_name"),
        "units": visualization_set.get("units"),
        "geometry_count": len(geometry_layers),
        "geometry_identifiers": layer_identifiers,
    }


def _set_visualization_set_name(vis_set: Any, name: str | None) -> None:
    if not name:
        return
    vis_set.identifier = slugify_name(name)
    vis_set.display_name = name


def _display_options_for_view_mode(view_mode: str | None) -> dict[str, Any]:
    mode = (view_mode or "custom").strip().lower()
    if mode == "quick":
        return {"view_mode": "quick", "include_wireframe": True, "use_mesh": True}
    if mode == "all":
        return {"view_mode": "all", "include_wireframe": True, "use_mesh": True}
    if mode == "floors":
        return {
            "view_mode": "floors",
            "use_multiplier": False,
            "include_wireframe": False,
            "use_mesh": True,
            "color_by": "type",
        }
    if mode == "wireframe":
        return {"view_mode": "wireframe", "include_wireframe": True, "use_mesh": False}
    if mode == "custom":
        return {"view_mode": "custom"}
    raise ValueError("view_mode must be quick, all, floors, wireframe, or custom.")


def _clone_model_metadata(source: Model, preview_model: Model) -> Model:
    preview_model.display_name = source.display_name
    preview_model.user_data = dict(source.user_data or {})
    return preview_model


def _building_by_identifier(model: Model, identifier: str) -> Building:
    matches = model.buildings_by_identifier([identifier])
    if not matches:
        raise ValueError(f"Dragonfly Building not found: {identifier}.")
    return matches[0]


def _story_by_identifier(model: Model, identifier: str) -> Story:
    matches = model.stories_by_identifier([identifier])
    if not matches:
        raise ValueError(f"Dragonfly Story not found: {identifier}.")
    return matches[0]


def _room_by_identifier(model: Model, identifier: str) -> Room2D:
    matches = model.room_2ds_by_identifier([identifier])
    if not matches:
        raise ValueError(f"Dragonfly Room2D not found: {identifier}.")
    return matches[0]


def _context_shade_by_identifier(model: Model, identifier: str) -> ContextShade:
    matches = model.context_shade_by_identifier([identifier])
    if not matches:
        raise ValueError(f"Dragonfly ContextShade not found: {identifier}.")
    return matches[0]


def _copy_building(building: Building) -> Building:
    return Building.from_dict(building.to_dict())


def _copy_story(story: Story) -> Story:
    return Story.from_dict(story.to_dict())


def _copy_room(room: Room2D) -> Room2D:
    return Room2D.from_dict(room.to_dict())


def _copy_context_shade(shade: ContextShade) -> ContextShade:
    return ContextShade.from_dict(shade.to_dict())


def _preview_building_from_story(story: Story) -> Building:
    return Building(f"{story.identifier}_preview", unique_stories=[_copy_story(story)])


def _preview_building_from_room(room: Room2D) -> Building:
    copied_room = _copy_room(room)
    story = Story(
        f"{room.identifier}_preview_story",
        [copied_room],
        floor_to_floor_height=room.floor_to_ceiling_height,
        floor_height=room.floor_height,
    )
    return Building(f"{room.identifier}_preview_building", unique_stories=[story])


def _subset_model_from_targets(
    model: Model,
    targets: list[dict[str, Any]],
) -> tuple[Model, list[dict[str, str]]]:
    buildings: list[Building] = []
    context_shades: list[ContextShade] = []
    selected: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw_target in targets:
        target = normalize_dragonfly_object_target(raw_target)
        object_type = str(target["object_type"])
        identifier = str(target["object_identifier"])
        key = (object_type, identifier)
        if key in seen:
            continue
        seen.add(key)
        selected.append({"object_type": object_type, "identifier": identifier})
        if object_type == "building":
            buildings.append(_copy_building(_building_by_identifier(model, identifier)))
        elif object_type == "story":
            buildings.append(_preview_building_from_story(_story_by_identifier(model, identifier)))
        elif object_type == "room2d":
            buildings.append(_preview_building_from_room(_room_by_identifier(model, identifier)))
        elif object_type == "context_shade":
            context_shades.append(
                _copy_context_shade(_context_shade_by_identifier(model, identifier))
            )
        else:
            raise ValueError(
                "Dragonfly VisualizationSet previews support building, story, "
                "room2d, and context_shade targets."
            )
    preview_model = Model(
        f"{model.identifier}_selection_preview",
        buildings=buildings,
        context_shades=context_shades,
        units=model.units,
        tolerance=model.tolerance,
        angle_tolerance=model.angle_tolerance,
    )
    return _clone_model_metadata(model, preview_model), selected


def _visualization_set_from_preview_model(
    *,
    garden_root_path: Path,
    manifest: Any,
    resolved_target: dict[str, Any],
    preview_model: Model,
    source: dict[str, Any],
    summary_updates: dict[str, Any],
    name: str | None,
    return_visualization_set: bool,
    message: str,
) -> dict[str, Any]:
    vis_set = model_to_vis_set(
        preview_model,
        use_multiplier=True,
        include_wireframe=True,
        use_mesh=True,
        color_by="type",
    )
    if name:
        _set_visualization_set_name(vis_set, name)
    visualization_set = vis_set.to_dict()
    summary = _summarize_visualization_set(visualization_set)
    summary.update(
        {
            "garden_target": manifest.target(),
            "model_target": resolved_target,
            **summary_updates,
        }
    )
    return _visualization_set_response(
        garden_root_path=garden_root_path,
        visualization_set=visualization_set,
        summary=summary,
        source=source,
        name=name,
        return_visualization_set=return_visualization_set,
        message=message,
    )


def _visualization_set_response(
    *,
    garden_root_path: Path,
    visualization_set: dict[str, Any],
    summary: dict[str, Any],
    source: dict[str, Any],
    name: str | None,
    return_visualization_set: bool,
    message: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "visualization_set": visualization_set,
        "summary_view": summary,
        "report": make_report(status="ok", message=message),
    }
    if return_visualization_set:
        return result
    saved = save_visualization_set(
        garden_root=str(garden_root_path),
        visualization_set=visualization_set,
        name=name or visualization_set.get("identifier") or "dragonfly_display",
        source=source,
    )
    result["target"] = saved["target"]
    result["visualization_set_target"] = saved["visualization_set_target"]
    result["persistence_receipt"] = saved["persistence_receipt"]
    result["summary_view"]["visualization_set_target"] = saved[
        "visualization_set_target"
    ]
    result["summary_view"]["body_returned"] = False
    result.pop("visualization_set", None)
    return result


def _edge_degraded_visualization_set_response(
    *,
    garden_root_path: Path,
    model: Any,
    manifest: Any,
    resolved_target: dict[str, Any],
    original_error: Exception,
    name: str | None,
    return_visualization_set: bool,
) -> dict[str, Any]:
    """Return an honest wireframe preview when Dragonfly Display edge view fails."""
    degraded_name = name or "dragonfly_envelope_edges_degraded"
    vis_set = model_to_vis_set(
        model,
        use_multiplier=True,
        include_wireframe=True,
        use_mesh=False,
        hide_color_by=True,
        reset_coordinates=True,
    )
    _set_visualization_set_name(vis_set, degraded_name)
    visualization_set = vis_set.to_dict()
    summary = _summarize_visualization_set(visualization_set)
    original_error_message = str(original_error)
    summary.update(
        {
            "garden_target": manifest.target(),
            "model_target": resolved_target,
            "edge_view_status": "degraded",
            "degraded_tool": "dragonfly_model_to_visualization_set",
            "degraded_reason": "dragonfly_display_envelope_edges_failed",
            "original_error": original_error_message,
            "use_multiplier": True,
            "include_wireframe": True,
            "use_mesh": False,
            "hide_color_by": True,
            "reset_coordinates": True,
        }
    )
    result = _visualization_set_response(
        garden_root_path=garden_root_path,
        visualization_set=visualization_set,
        summary=summary,
        source={
            "tool": "dragonfly_model_envelope_edges_to_visualization_set",
            "model_target": resolved_target,
            "degraded_tool": "dragonfly_model_to_visualization_set",
            "original_error": original_error_message,
        },
        name=degraded_name,
        return_visualization_set=return_visualization_set,
        message=(
            "Dragonfly envelope-edge SDK view failed; returned a wireframe "
            "model VisualizationSet preview."
        ),
    )
    result["report"] = make_report(
        status="degraded",
        message=(
            "Dragonfly envelope-edge SDK view failed; returned a wireframe "
            "model VisualizationSet preview."
        ),
        warnings=[
            "This is a wireframe model preview, not the strict Dragonfly "
            "Display envelope-edge output."
        ],
        details={
            "degraded_tool": "dragonfly_model_to_visualization_set",
            "degraded_reason": "dragonfly_display_envelope_edges_failed",
            "original_error": original_error_message,
        },
    )
    return result


def dragonfly_model_to_visualization_set(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
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
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Translate a Garden Dragonfly model into a Ladybug Display VisualizationSet."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_target)
    view_options = _display_options_for_view_mode(view_mode)
    resolved_view_mode = str(view_options.pop("view_mode"))
    use_multiplier = view_options.get("use_multiplier", use_multiplier)
    include_wireframe = view_options.get("include_wireframe", include_wireframe)
    use_mesh = view_options.get("use_mesh", use_mesh)
    color_by = view_options.get("color_by", color_by)
    vis_set = model_to_vis_set(
        model,
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
    )
    if name:
        _set_visualization_set_name(vis_set, name)

    visualization_set = vis_set.to_dict()
    summary = _summarize_visualization_set(visualization_set)
    summary.update(
        {
            "garden_target": manifest.target(),
            "model_target": resolved_target,
            "view_mode": resolved_view_mode,
            "use_multiplier": use_multiplier,
            "exclude_plenums": exclude_plenums,
            "solve_ceiling_adjacencies": solve_ceiling_adjacencies,
            "merge_method": merge_method,
            "color_by": color_by,
            "include_wireframe": include_wireframe,
            "use_mesh": use_mesh,
            "hide_color_by": hide_color_by,
            "grid_display_mode": grid_display_mode,
            "hide_grid": hide_grid,
            "reset_coordinates": reset_coordinates,
        }
    )
    return _visualization_set_response(
        garden_root_path=garden_root_path,
        visualization_set=visualization_set,
        summary=summary,
        source={
            "tool": "dragonfly_model_to_visualization_set",
            "model_target": resolved_target,
        },
        name=name,
        return_visualization_set=return_visualization_set,
        message="Dragonfly model VisualizationSet created.",
    )


def dragonfly_object_to_visualization_set(
    *,
    garden_root: str,
    target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a VisualizationSet preview for one Dragonfly object target."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_target)
    object_target = normalize_dragonfly_object_target(target)
    preview_model, selected = _subset_model_from_targets(model, [object_target])
    object_type = str(object_target["object_type"])
    return _visualization_set_from_preview_model(
        garden_root_path=garden_root_path,
        manifest=manifest,
        resolved_target=resolved_target,
        preview_model=preview_model,
        source={
            "tool": f"dragonfly_{object_type}_to_visualization_set",
            "model_target": resolved_target,
            "object_target": object_target,
        },
        summary_updates={
            "source_object_type": object_type,
            "source_object_target": object_target,
            "selected_objects": selected,
            "selection_count": len(selected),
        },
        name=name,
        return_visualization_set=return_visualization_set,
        message=f"Dragonfly {object_type} VisualizationSet preview created.",
    )


def dragonfly_building_to_visualization_set(
    *,
    garden_root: str,
    target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a VisualizationSet preview for one Dragonfly Building target."""
    return dragonfly_object_to_visualization_set(
        garden_root=garden_root,
        target=target,
        model_target=model_target,
        name=name,
        return_visualization_set=return_visualization_set,
    )


def dragonfly_story_to_visualization_set(
    *,
    garden_root: str,
    target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a VisualizationSet preview for one Dragonfly Story target."""
    return dragonfly_object_to_visualization_set(
        garden_root=garden_root,
        target=target,
        model_target=model_target,
        name=name,
        return_visualization_set=return_visualization_set,
    )


def dragonfly_room2d_to_visualization_set(
    *,
    garden_root: str,
    target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a VisualizationSet preview for one Dragonfly Room2D target."""
    return dragonfly_object_to_visualization_set(
        garden_root=garden_root,
        target=target,
        model_target=model_target,
        name=name,
        return_visualization_set=return_visualization_set,
    )


def dragonfly_context_shade_to_visualization_set(
    *,
    garden_root: str,
    target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a VisualizationSet preview for one Dragonfly ContextShade target."""
    return dragonfly_object_to_visualization_set(
        garden_root=garden_root,
        target=target,
        model_target=model_target,
        name=name,
        return_visualization_set=return_visualization_set,
    )


def dragonfly_selection_to_visualization_set(
    *,
    garden_root: str,
    selection: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a VisualizationSet preview from a Dragonfly selection object."""
    if not isinstance(selection, dict) or selection.get("target_type") != "dragonfly_selection":
        raise ValueError("selection must be a dragonfly_selection dictionary.")
    object_targets = selection.get("object_targets")
    if not isinstance(object_targets, list):
        raise ValueError("selection.object_targets must be a list.")
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_target)
    preview_model, selected = _subset_model_from_targets(model, object_targets)
    return _visualization_set_from_preview_model(
        garden_root_path=garden_root_path,
        manifest=manifest,
        resolved_target=resolved_target,
        preview_model=preview_model,
        source={
            "tool": "dragonfly_selection_to_visualization_set",
            "model_target": resolved_target,
            "selection": selection,
        },
        summary_updates={
            "source_object_type": "selection",
            "selection": selection,
            "selected_objects": selected,
            "selection_count": len(selected),
        },
        name=name,
        return_visualization_set=return_visualization_set,
        message="Dragonfly selection VisualizationSet preview created.",
    )


def _parse_room_attr_inputs(room_attrs: list[Any] | None) -> list[RoomAttribute] | None:
    if not room_attrs:
        return None
    parsed: list[RoomAttribute] = []
    for item in room_attrs:
        if isinstance(item, RoomAttribute):
            parsed.append(item)
        elif isinstance(item, str):
            parsed.append(RoomAttribute(item, [item]))
        elif isinstance(item, dict):
            attrs = item.get("attrs") or ([item["attribute"]] if item.get("attribute") else None)
            if not attrs:
                raise ValueError("room_attrs dict requires attrs list.")
            parsed.append(
                RoomAttribute(
                    str(item.get("name") or attrs[0]),
                    list(attrs),
                    color=bool(item.get("color", True)),
                    text=bool(item.get("text", False)),
                )
            )
        else:
            raise ValueError("room_attrs entries must be strings, dicts, or RoomAttribute objects.")
    return parsed


def _parse_face_attr_inputs(face_attrs: list[Any] | None) -> list[FaceAttribute] | None:
    if not face_attrs:
        return None
    parsed: list[FaceAttribute] = []
    for item in face_attrs:
        if isinstance(item, FaceAttribute):
            parsed.append(item)
        elif isinstance(item, str):
            parsed.append(FaceAttribute(item, [item]))
        elif isinstance(item, dict):
            attrs = item.get("attrs") or ([item["attribute"]] if item.get("attribute") else None)
            if not attrs:
                raise ValueError("face_attrs dict requires attrs list.")
            parsed.append(
                FaceAttribute(
                    str(item.get("name") or attrs[0]),
                    list(attrs),
                    color=bool(item.get("color", True)),
                    text=bool(item.get("text", False)),
                )
            )
        else:
            raise ValueError("face_attrs entries must be strings, dicts, or FaceAttribute objects.")
    return parsed


def _color_room2d_vis_set(model: Model, attr_name: str) -> VisualizationSet:
    color_obj = ColorRoom2D(model.room_2ds, attr_name)
    gc = color_obj.graphic_container
    faces = [DisplayFace3D(face) for face in color_obj.floor_faces]
    vis_data = VisualizationData(
        list(gc.values),
        legend_parameters=gc.legend_parameters,
        data_type=attr_name.replace("_", " ").title(),
    )
    analysis = AnalysisGeometry(attr_name, faces, [vis_data])
    vis_set = VisualizationSet(f"{model.identifier}_{slugify_name(attr_name)}", [analysis])
    vis_set.display_name = f"{model.display_name}: {attr_name}"
    return vis_set


def dragonfly_room2d_attribute_to_visualization_set(
    *,
    garden_root: str,
    attribute_result: dict[str, Any] | None = None,
    attribute: str | None = None,
    room_attrs: list[Any] | None = None,
    face_attrs: list[Any] | None = None,
    color_by: str | None = "None",
    model_target: dict[str, Any] | None = None,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a VisualizationSet coloring Rooms/Faces via RoomAttribute/FaceAttribute or ColorRoom2D."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_target)

    resolved_attr = attribute
    if resolved_attr is None and isinstance(attribute_result, dict):
        summary = attribute_result.get("summary_view")
        if isinstance(summary, dict):
            resolved_attr = summary.get("attribute")

    parsed_room_attrs = _parse_room_attr_inputs(room_attrs)
    parsed_face_attrs = _parse_face_attr_inputs(face_attrs)
    if parsed_room_attrs is None and parsed_face_attrs is None:
        if not resolved_attr:
            raise ValueError(
                "Provide room_attrs, face_attrs, attribute, or attribute_result with summary_view.attribute."
            )
        parsed_room_attrs = [RoomAttribute(str(resolved_attr), [str(resolved_attr)])]

    vis_set: VisualizationSet | None = None
    if model.room_2ds:
        try:
            vis_set = model_to_vis_set(
                model,
                color_by=color_by,
                include_wireframe=True,
                use_mesh=True,
                room_attrs=parsed_room_attrs,
                face_attrs=parsed_face_attrs,
            )
        except Exception:
            vis_set = None
        if vis_set is not None and not any(
            getattr(layer, "__class__", None).__name__ == "AnalysisGeometry"
            for layer in vis_set.geometry
        ):
            if resolved_attr and hasattr(model.room_2ds[0], str(resolved_attr)):
                vis_set = _color_room2d_vis_set(model, str(resolved_attr))
    if vis_set is None and resolved_attr and model.room_2ds:
        vis_set = _color_room2d_vis_set(model, str(resolved_attr))
    if vis_set is None:
        raise ValueError("Unable to construct attribute VisualizationSet for this Model.")

    if name:
        _set_visualization_set_name(vis_set, name)
    visualization_set = vis_set.to_dict()
    groups = (
        attribute_result.get("groups")
        if isinstance(attribute_result, dict) and isinstance(attribute_result.get("groups"), list)
        else []
    )
    summary = _summarize_visualization_set(visualization_set)
    summary.update(
        {
            "garden_target": manifest.target(),
            "model_target": resolved_target,
            "source_object_type": "room2d_attribute",
            "attribute": resolved_attr,
            "room_attr_names": [item.name for item in (parsed_room_attrs or [])],
            "face_attr_names": [item.name for item in (parsed_face_attrs or [])],
            "groups": groups,
            "group_count": len(groups),
        }
    )
    return _visualization_set_response(
        garden_root_path=garden_root_path,
        visualization_set=visualization_set,
        summary=summary,
        source={
            "tool": "dragonfly_room2d_attribute_to_visualization_set",
            "model_target": resolved_target,
            "attribute": resolved_attr,
        },
        name=name,
        return_visualization_set=return_visualization_set,
        message="Dragonfly Room/Face attribute VisualizationSet created.",
    )


def dragonfly_opening_projection_to_visualization_set(
    *,
    garden_root: str,
    honeybee_model_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
    wall_modifier_data: Any = None,
    projection_distance: float = 0,
    angle_tolerance: float | None = None,
    exclude_existing_openings: bool = True,
    reset_coordinates: bool = False,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a VisualizationSet preview of projecting Honeybee Model openings onto Dragonfly walls."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_target = resolve_model_target(garden_root_path, model_target)
    df_model = load_dragonfly_model(garden_root_path, resolved_target)
    _, resolved_hb_target = resolve_honeybee_model_target(
        garden_root_path,
        honeybee_model_target,
    )
    hb_model = load_honeybee_model(garden_root_path, resolved_hb_target)
    vis_set = model_opening_projection_to_vis_set(
        df_model,
        hb_model,
        wall_modifier_data=wall_modifier_data,
        projection_distance=projection_distance,
        angle_tolerance=angle_tolerance,
        exclude_existing_openings=exclude_existing_openings,
        reset_coordinates=reset_coordinates,
    )
    if name:
        _set_visualization_set_name(vis_set, name)
    visualization_set = vis_set.to_dict()
    summary = _summarize_visualization_set(visualization_set)
    summary.update(
        {
            "garden_target": manifest.target(),
            "model_target": resolved_target,
            "honeybee_model_target": resolved_hb_target,
            "projection_distance": projection_distance,
            "exclude_existing_openings": exclude_existing_openings,
            "reset_coordinates": reset_coordinates,
        }
    )
    return _visualization_set_response(
        garden_root_path=garden_root_path,
        visualization_set=visualization_set,
        summary=summary,
        source={
            "tool": "dragonfly_opening_projection_to_visualization_set",
            "model_target": resolved_target,
            "honeybee_model_target": resolved_hb_target,
        },
        name=name,
        return_visualization_set=return_visualization_set,
        message="Dragonfly opening projection VisualizationSet created.",
    )


def dragonfly_model_envelope_edges_to_visualization_set(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    coplanar_type: str = "FloorPlatesOnly",
    mullion_thickness: float | None = None,
    reset_coordinates: bool = False,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a Dragonfly Display envelope-edge VisualizationSet."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_target)
    try:
        vis_set = model_envelope_edges_to_vis_set(
            model,
            coplanar_type=coplanar_type,
            mullion_thickness=mullion_thickness,
            reset_coordinates=reset_coordinates,
        )
    except Exception as exc:
        return _edge_degraded_visualization_set_response(
            garden_root_path=garden_root_path,
            model=model,
            manifest=manifest,
            resolved_target=resolved_target,
            original_error=exc,
            name=name,
            return_visualization_set=return_visualization_set,
        )
    if name:
        _set_visualization_set_name(vis_set, name)
    visualization_set = vis_set.to_dict()
    summary = _summarize_visualization_set(visualization_set)
    summary.update(
        {
            "garden_target": manifest.target(),
            "model_target": resolved_target,
            "coplanar_type": coplanar_type,
            "mullion_thickness": mullion_thickness,
            "reset_coordinates": reset_coordinates,
        }
    )
    return _visualization_set_response(
        garden_root_path=garden_root_path,
        visualization_set=visualization_set,
        summary=summary,
        source={
            "tool": "dragonfly_model_envelope_edges_to_visualization_set",
            "model_target": resolved_target,
        },
        name=name,
        return_visualization_set=return_visualization_set,
        message="Dragonfly model envelope-edge VisualizationSet created.",
    )


def dragonfly_models_to_comparison_visualization_set(
    *,
    garden_root: str,
    base_model_target: dict[str, Any],
    incoming_model_target: dict[str, Any],
    use_multiplier: bool = True,
    exclude_plenums: bool = False,
    solve_ceiling_adjacencies: bool = False,
    merge_method: str = "None",
    reset_coordinates: bool = False,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a Dragonfly Display comparison VisualizationSet for two models."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_base_target = resolve_model_target(
        garden_root_path,
        base_model_target,
    )
    _manifest, resolved_incoming_target = resolve_model_target(
        garden_root_path,
        incoming_model_target,
    )
    base_model = load_dragonfly_model(garden_root_path, resolved_base_target)
    incoming_model = load_dragonfly_model(garden_root_path, resolved_incoming_target)
    vis_set = model_comparison_to_vis_set(
        base_model,
        incoming_model,
        use_multiplier=use_multiplier,
        exclude_plenums=exclude_plenums,
        solve_ceiling_adjacencies=solve_ceiling_adjacencies,
        merge_method=merge_method,
        reset_coordinates=reset_coordinates,
    )
    if name:
        _set_visualization_set_name(vis_set, name)
    visualization_set = vis_set.to_dict()
    summary = _summarize_visualization_set(visualization_set)
    summary.update(
        {
            "garden_target": manifest.target(),
            "base_model_target": resolved_base_target,
            "incoming_model_target": resolved_incoming_target,
            "use_multiplier": use_multiplier,
            "exclude_plenums": exclude_plenums,
            "solve_ceiling_adjacencies": solve_ceiling_adjacencies,
            "merge_method": merge_method,
            "reset_coordinates": reset_coordinates,
        }
    )
    return _visualization_set_response(
        garden_root_path=garden_root_path,
        visualization_set=visualization_set,
        summary=summary,
        source={
            "tool": "dragonfly_models_to_comparison_visualization_set",
            "base_model_target": resolved_base_target,
            "incoming_model_target": resolved_incoming_target,
        },
        name=name,
        return_visualization_set=return_visualization_set,
        message="Dragonfly comparison VisualizationSet created.",
    )


def dragonfly_targets_to_visualization_set(
    *,
    garden_root: str,
    target: dict[str, Any] | None = None,
    selection: dict[str, Any] | None = None,
    targets: list[dict[str, Any]] | None = None,
    model_target: dict[str, Any] | None = None,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a VisualizationSet preview for a target, target list, or selection."""
    if selection is not None:
        return dragonfly_selection_to_visualization_set(
            garden_root=garden_root,
            selection=selection,
            model_target=model_target,
            name=name,
            return_visualization_set=return_visualization_set,
        )
    combined_targets: list[dict[str, Any]] = []
    if targets is not None:
        if target is not None:
            combined_targets.append(target)
        combined_targets.extend(targets)
        if not combined_targets:
            raise ValueError("targets must contain at least one object target.")
        if len(combined_targets) == 1:
            return dragonfly_object_to_visualization_set(
                garden_root=garden_root,
                target=combined_targets[0],
                model_target=model_target,
                name=name,
                return_visualization_set=return_visualization_set,
            )
        normalized = [
            normalize_dragonfly_object_target(item) for item in combined_targets
        ]
        return dragonfly_selection_to_visualization_set(
            garden_root=garden_root,
            selection={
                "target_type": "dragonfly_selection",
                "object_targets": normalized,
            },
            model_target=model_target,
            name=name,
            return_visualization_set=return_visualization_set,
        )
    if target is not None:
        if target.get("target_type") == "dragonfly_selection":
            return dragonfly_selection_to_visualization_set(
                garden_root=garden_root,
                selection=target,
                model_target=model_target,
                name=name,
                return_visualization_set=return_visualization_set,
            )
        return dragonfly_object_to_visualization_set(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            name=name,
            return_visualization_set=return_visualization_set,
        )
    raise ValueError(
        "Provide target, targets, or selection to visualize Dragonfly targets."
    )
