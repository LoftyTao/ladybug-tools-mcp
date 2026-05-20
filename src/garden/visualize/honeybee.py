"""Honeybee VisualizationSet services."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from honeybee.aperture import Aperture
from honeybee.boundarycondition import Ground, Outdoors, Surface
from honeybee.face import Face
from honeybee.facetype import AirBoundary, Floor, RoofCeiling, Wall
from honeybee.shade import Shade
from honeybee_display.attr import FaceAttribute, RoomAttribute
from honeybee_display.model import model_to_vis_set
from honeybee_display.face import face_to_vis_set, face_to_vis_set_wireframe
from honeybee_display.room import room_to_vis_set, room_to_vis_set_wireframe
from honeybee.room import Room
from ladybug_display.visualization import VisualizationSet

from ladybug_tools_mcp.contracts.report import make_report
from garden.manifest import GardenManifest
from garden.honeybee_core.locate import find_object
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target,
)
from garden.visualize.artifacts import load_visualization_set, save_visualization_set
from garden.visualize.legend import legend_parameter_from_dict

MODEL_COLOR_BY = {"type", "boundary_condition", "none"}
OBJECT_COLOR_BY = {"type", "boundary_condition", "none"}
COMPOSE_CONFLICT_STRATEGIES = {"error", "rename"}
FACE_TYPE_MAP = {
    "wall": Wall,
    "roofceiling": RoofCeiling,
    "roof": RoofCeiling,
    "floor": Floor,
    "airboundary": AirBoundary,
    "air_boundary": AirBoundary,
    "aperture": Aperture,
    "shade": Shade,
}
BOUNDARY_CONDITION_MAP = {
    "outdoors": Outdoors,
    "surface": Surface,
    "ground": Ground,
}


def _normalize_model_color_by(color_by: str | None) -> str | None:
    value = "type" if color_by is None else str(color_by).strip().lower()
    if value not in MODEL_COLOR_BY:
        allowed = ", ".join(sorted(MODEL_COLOR_BY))
        raise ValueError(f"Unsupported model color_by: {color_by}. Allowed values: {allowed}.")
    return None if value == "none" else value


def _normalize_object_color_by(color_by: str | None) -> str | None:
    value = "type" if color_by is None else str(color_by).strip().lower()
    if value not in OBJECT_COLOR_BY:
        allowed = ", ".join(sorted(OBJECT_COLOR_BY))
        raise ValueError(f"Unsupported object color_by: {color_by}. Allowed values: {allowed}.")
    return None if value == "none" else value


def _model_target_for_object(
    manifest: GardenManifest,
    target: dict[str, Any],
) -> dict[str, Any]:
    model_identifier = target.get("model_identifier")
    if not model_identifier:
        raise ValueError("Honeybee object target requires model_identifier.")
    for candidate in manifest.models:
        if (
            isinstance(candidate, dict)
            and candidate.get("target_type") == "honeybee_model"
            and candidate.get("domain") == "honeybee"
            and candidate.get("model_identifier") == model_identifier
        ):
            return candidate
    raise ValueError(
        "Honeybee object target references a model that is not registered in "
        "the Garden manifest."
    )


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


def _set_visualization_set_name(vis_set: VisualizationSet, name: str | None) -> None:
    if name:
        vis_set.identifier = name
        vis_set.display_name = name


def _build_room_attributes(
    attribute_specs: list[dict[str, Any]] | None,
) -> list[RoomAttribute] | None:
    if not attribute_specs:
        return None
    return [
        RoomAttribute(
            name=str(spec.get("name") or _default_attribute_name(spec)),
            attrs=_attribute_paths(spec),
            color=bool(spec.get("color", True)),
            text=bool(spec.get("text", False)),
            legend_par=legend_parameter_from_dict(spec.get("legend_parameter")),
        )
        for spec in attribute_specs
    ]


def _build_face_attributes(
    attribute_specs: list[dict[str, Any]] | None,
) -> list[FaceAttribute] | None:
    if not attribute_specs:
        return None
    return [
        FaceAttribute(
            name=str(spec.get("name") or _default_attribute_name(spec)),
            attrs=_attribute_paths(spec),
            color=bool(spec.get("color", True)),
            text=bool(spec.get("text", False)),
            legend_par=legend_parameter_from_dict(spec.get("legend_parameter")),
            face_types=_map_face_types(spec.get("face_types")),
            boundary_conditions=_map_boundary_conditions(spec.get("boundary_conditions")),
        )
        for spec in attribute_specs
    ]


def _attribute_paths(spec: dict[str, Any]) -> list[str]:
    attrs = spec.get("attrs") or spec.get("attribute_paths") or spec.get("attributes")
    if isinstance(attrs, str):
        attrs = [attrs]
    if not attrs:
        raise ValueError("Attribute visualization specs require at least one attribute path.")
    return [str(item) for item in attrs]


def _default_attribute_name(spec: dict[str, Any]) -> str:
    return _attribute_paths(spec)[0].replace(".", "_")


def _map_face_types(values: list[str] | None) -> list[Any]:
    if not values:
        return []
    mapped = []
    for value in values:
        key = str(value).replace(" ", "").replace("-", "_").lower()
        if key not in FACE_TYPE_MAP:
            allowed = ", ".join(sorted(FACE_TYPE_MAP))
            raise ValueError(f"Unsupported face type filter: {value}. Allowed values: {allowed}.")
        mapped.append(FACE_TYPE_MAP[key])
    return mapped


def _map_boundary_conditions(values: list[str] | None) -> list[Any]:
    if not values:
        return []
    mapped = []
    for value in values:
        key = str(value).replace(" ", "").replace("-", "_").lower()
        if key not in BOUNDARY_CONDITION_MAP:
            allowed = ", ".join(sorted(BOUNDARY_CONDITION_MAP))
            raise ValueError(
                f"Unsupported boundary condition filter: {value}. Allowed values: {allowed}."
            )
        mapped.append(BOUNDARY_CONDITION_MAP[key])
    return mapped


def _attribute_spec_summary(
    attribute_specs: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    summaries = []
    for spec in attribute_specs or []:
        summaries.append(
            {
                "name": str(spec.get("name") or _default_attribute_name(spec)),
                "attrs": _attribute_paths(spec),
                "color": bool(spec.get("color", True)),
                "text": bool(spec.get("text", False)),
                "has_legend_parameter": bool(spec.get("legend_parameter")),
                "face_types": spec.get("face_types") or [],
                "boundary_conditions": spec.get("boundary_conditions") or [],
            }
        )
    return summaries


def _object_visualization_response(
    *,
    manifest_target: dict[str, Any],
    model_target: dict[str, Any],
    object_target: dict[str, Any],
    visualization_set: dict[str, Any],
    object_kind: str,
    color_by: str,
    include_wireframe: bool,
    wireframe_only: bool,
) -> dict[str, Any]:
    summary = _summarize_visualization_set(visualization_set)
    summary.update(
        {
            "garden_target": manifest_target,
            "model_target": model_target,
            "object_target": object_target,
            "object_type": object_kind,
            "color_by": color_by,
            "include_wireframe": include_wireframe or wireframe_only,
            "wireframe_only": wireframe_only,
        }
    )
    return {
        "visualization_set": visualization_set,
        "summary_view": summary,
        "report": make_report(
            status="ok",
            message=f"Honeybee {object_kind} VisualizationSet created.",
        ),
    }


def honeybee_model_to_visualization_set(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    color_by: str | None = "type",
    include_wireframe: bool = True,
    wireframe_only: bool = False,
    use_mesh: bool = False,
    hide_color_by: bool = False,
    room_attributes: list[dict[str, Any]] | None = None,
    face_attributes: list[dict[str, Any]] | None = None,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Translate a Garden Honeybee model into a Ladybug Display VisualizationSet."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_target = resolve_model_target(garden_root_path, model_target)
    model = load_honeybee_model(garden_root_path, resolved_target)

    normalized_color_by = None if wireframe_only else _normalize_model_color_by(color_by)
    vis_set = model_to_vis_set(
        model,
        color_by=normalized_color_by,
        include_wireframe=include_wireframe or wireframe_only,
        use_mesh=use_mesh,
        hide_color_by=hide_color_by,
        room_attrs=_build_room_attributes(room_attributes),
        face_attrs=_build_face_attributes(face_attributes),
    )
    if name:
        vis_set.identifier = name
        vis_set.display_name = name

    visualization_set = vis_set.to_dict()
    summary = _summarize_visualization_set(visualization_set)
    summary.update(
        {
            "garden_target": manifest.target(),
            "model_target": resolved_target,
            "color_by": "none" if normalized_color_by is None else normalized_color_by,
            "include_wireframe": include_wireframe or wireframe_only,
            "wireframe_only": wireframe_only,
            "use_mesh": use_mesh,
            "hide_color_by": hide_color_by,
            "room_attributes": _attribute_spec_summary(room_attributes),
            "face_attributes": _attribute_spec_summary(face_attributes),
        }
    )

    result = {
        "visualization_set": visualization_set,
        "summary_view": summary,
        "report": make_report(
            status="ok",
            message="Honeybee model VisualizationSet created.",
        ),
    }
    if not return_visualization_set:
        saved = save_visualization_set(
            garden_root=str(garden_root_path),
            visualization_set=visualization_set,
            name=name or visualization_set.get("identifier") or "honeybee_model",
            source={
                "tool": "honeybee_model_to_visualization_set",
                "model_target": resolved_target,
            },
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


def honeybee_room_to_visualization_set(
    *,
    garden_root: str,
    target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    color_by: str | None = "type",
    include_wireframe: bool = True,
    wireframe_only: bool = False,
    include_sub_faces: bool = True,
    include_shades: bool = True,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Translate a Garden Honeybee Room typed target into a VisualizationSet."""
    if target.get("object_type") != "room":
        raise ValueError("honeybee_room_to_visualization_set requires a room typed target.")
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    manifest, resolved_target = resolve_model_target(
        garden_root_path,
        model_target or _model_target_for_object(manifest, target),
    )
    model = load_honeybee_model(garden_root_path, resolved_target)
    room = find_object(model, target)
    if not isinstance(room, Room):
        raise ValueError("Target did not resolve to a Honeybee Room.")

    normalized_color_by = None if wireframe_only else _normalize_object_color_by(color_by)
    effective_wireframe_only = wireframe_only or normalized_color_by is None
    if effective_wireframe_only:
        vis_set = room_to_vis_set_wireframe(
            room,
            include_sub_faces=include_sub_faces,
            include_shades=include_shades,
        )
    else:
        vis_set = room_to_vis_set(room, color_by=normalized_color_by)
        if include_wireframe:
            vis_set.add_vis_set(
                room_to_vis_set_wireframe(
                    room,
                    include_sub_faces=include_sub_faces,
                    include_shades=include_shades,
                )
            )
    _set_visualization_set_name(vis_set, name)
    visualization_set = vis_set.to_dict()
    result = _object_visualization_response(
        manifest_target=manifest.target(),
        model_target=resolved_target,
        object_target=target,
        visualization_set=visualization_set,
        object_kind="room",
        color_by="none" if normalized_color_by is None else normalized_color_by,
        include_wireframe=include_wireframe,
        wireframe_only=effective_wireframe_only,
    )
    if not return_visualization_set:
        saved = save_visualization_set(
            garden_root=str(garden_root_path),
            visualization_set=visualization_set,
            name=name or visualization_set.get("identifier") or "honeybee_room",
            source={
                "tool": "honeybee_room_to_visualization_set",
                "model_target": resolved_target,
                "object_target": target,
            },
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


def honeybee_face_to_visualization_set(
    *,
    garden_root: str,
    target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    color_by: str | None = "type",
    include_wireframe: bool = True,
    wireframe_only: bool = False,
    include_sub_faces: bool = True,
    include_shades: bool = True,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Translate a Garden Honeybee Face typed target into a VisualizationSet."""
    if target.get("object_type") != "face":
        raise ValueError("honeybee_face_to_visualization_set requires a face typed target.")
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    manifest, resolved_target = resolve_model_target(
        garden_root_path,
        model_target or _model_target_for_object(manifest, target),
    )
    model = load_honeybee_model(garden_root_path, resolved_target)
    face = find_object(model, target)
    if not isinstance(face, Face):
        raise ValueError("Target did not resolve to a Honeybee Face.")

    normalized_color_by = None if wireframe_only else _normalize_object_color_by(color_by)
    effective_wireframe_only = wireframe_only or normalized_color_by is None
    if effective_wireframe_only:
        vis_set = face_to_vis_set_wireframe(
            face,
            include_sub_faces=include_sub_faces,
            include_shades=include_shades,
        )
    else:
        vis_set = face_to_vis_set(face, color_by=normalized_color_by)
        if include_wireframe:
            vis_set.add_vis_set(
                face_to_vis_set_wireframe(
                    face,
                    include_sub_faces=include_sub_faces,
                    include_shades=include_shades,
                )
            )
    _set_visualization_set_name(vis_set, name)
    visualization_set = vis_set.to_dict()
    result = _object_visualization_response(
        manifest_target=manifest.target(),
        model_target=resolved_target,
        object_target=target,
        visualization_set=visualization_set,
        object_kind="face",
        color_by="none" if normalized_color_by is None else normalized_color_by,
        include_wireframe=include_wireframe,
        wireframe_only=effective_wireframe_only,
    )
    if not return_visualization_set:
        saved = save_visualization_set(
            garden_root=str(garden_root_path),
            visualization_set=visualization_set,
            name=name or visualization_set.get("identifier") or "honeybee_face",
            source={
                "tool": "honeybee_face_to_visualization_set",
                "model_target": resolved_target,
                "object_target": target,
            },
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


def compose_visualization_sets(
    *,
    visualization_sets: list[dict[str, Any]] | None = None,
    garden_root: str | None = None,
    visualization_set_targets: list[dict[str, Any]] | None = None,
    name: str | None = None,
    units: str | None = None,
    check_duplicate_geometry_ids: bool = True,
    conflict_strategy: str = "error",
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Compose multiple VisualizationSets from dicts or Garden-backed targets."""
    input_sets = list(visualization_sets or [])
    input_targets = list(visualization_set_targets or [])
    if input_targets:
        if not garden_root:
            raise ValueError(
                "garden_root is required when composing visualization_set_targets."
            )
        input_sets.extend(
            load_visualization_set(
                garden_root=garden_root,
                visualization_set_target=target,
            )
            for target in input_targets
        )
    if not input_sets:
        raise ValueError("compose_visualization_sets requires at least one VisualizationSet.")
    strategy = str(conflict_strategy).strip().lower()
    if strategy not in COMPOSE_CONFLICT_STRATEGIES:
        allowed = ", ".join(sorted(COMPOSE_CONFLICT_STRATEGIES))
        raise ValueError(f"Unsupported conflict_strategy: {conflict_strategy}. Allowed values: {allowed}.")

    vis_sets = [VisualizationSet.from_dict(item) for item in input_sets]
    resolved_units = units if units is not None else next(
        (vis_set.units for vis_set in vis_sets if vis_set.units),
        vis_sets[0].units,
    )
    if units is None:
        mismatches = [
            vis_set.units
            for vis_set in vis_sets
            if vis_set.units and vis_set.units != resolved_units
        ]
        if mismatches:
            raise ValueError("VisualizationSet units must match when units is not provided.")

    combined = VisualizationSet(name or "composed_visualization_set", [], resolved_units)
    renamed_geometry_ids: list[dict[str, str]] = []
    seen: set[str] = set()
    for set_index, vis_set in enumerate(vis_sets, start=1):
        if units is not None and vis_set.units and vis_set.units != units:
            vis_set.convert_to_units(units)
        if check_duplicate_geometry_ids:
            _handle_geometry_identifier_conflicts(
                vis_set,
                set_index=set_index,
                seen=seen,
                strategy=strategy,
                renamed_geometry_ids=renamed_geometry_ids,
            )
        combined.add_vis_set(vis_set)

    if check_duplicate_geometry_ids:
        combined.check_duplicate_identifiers(raise_exception=True)
    visualization_set = combined.to_dict()
    summary = _summarize_visualization_set(visualization_set)
    summary.update(
        {
            "input_count": len(input_sets),
            "dict_input_count": len(visualization_sets or []),
            "target_input_count": len(input_targets),
            "check_duplicate_geometry_ids": check_duplicate_geometry_ids,
            "conflict_strategy": strategy,
            "renamed_geometry_ids": renamed_geometry_ids,
        }
    )
    result: dict[str, Any] = {
        "visualization_set": visualization_set,
        "summary_view": summary,
        "report": make_report(
            status="ok",
            message="VisualizationSets composed.",
        ),
    }
    if garden_root and not return_visualization_set:
        saved = save_visualization_set(
            garden_root=garden_root,
            visualization_set=visualization_set,
            name=name or "composed_visualization_set",
            source={
                "producer": "compose_visualization_sets",
                "visualization_set_targets": input_targets,
            },
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


def compose_model_analysis_visualization_set(
    *,
    garden_root: str,
    model_context_target: dict[str, Any],
    analysis_visualization_set_target: dict[str, Any],
    name: str = "model_analysis_overlay",
    units: str | None = None,
    exclude_context_geometry_identifiers: list[str] | None = None,
    conflict_strategy: str = "rename",
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Compose a Garden model-context VisualizationSet with an analysis layer."""
    excluded = set(exclude_context_geometry_identifiers or ["Sensor_Grids"])
    context = deepcopy(
        load_visualization_set(
            garden_root=garden_root,
            visualization_set_target=model_context_target,
        )
    )
    analysis = load_visualization_set(
        garden_root=garden_root,
        visualization_set_target=analysis_visualization_set_target,
    )
    context_identifier = context.get("identifier")
    analysis_identifier = analysis.get("identifier")
    context["geometry"] = [
        item
        for item in context.get("geometry", [])
        if item.get("identifier") not in excluded
    ]
    composed = compose_visualization_sets(
        visualization_sets=[context, analysis],
        name=name,
        units=units,
        check_duplicate_geometry_ids=True,
        conflict_strategy=conflict_strategy,
    )
    visualization_set = composed["visualization_set"]
    saved = save_visualization_set(
        garden_root=garden_root,
        visualization_set=visualization_set,
        name=name,
        source={
            "producer": "compose_model_analysis_visualization_set",
            "model_context_target": model_context_target,
            "analysis_visualization_set_target": analysis_visualization_set_target,
            "excluded_context_geometry_identifiers": sorted(excluded),
        },
    )
    summary = composed["summary_view"]
    summary.update(
        {
            "model_context_identifier": context_identifier,
            "analysis_identifier": analysis_identifier,
            "excluded_context_geometry_identifiers": sorted(excluded),
            "visualization_set_target": saved["visualization_set_target"],
        }
    )
    result: dict[str, Any] = {
        "visualization_set": visualization_set,
        "target": saved["target"],
        "visualization_set_target": saved["visualization_set_target"],
        "persistence_receipt": saved["persistence_receipt"],
        "summary_view": summary,
        "report": make_report(
            status="ok",
            message="Model context and analysis VisualizationSets composed.",
        ),
    }
    if not return_visualization_set:
        result.pop("visualization_set", None)
    return result


def _handle_geometry_identifier_conflicts(
    vis_set: VisualizationSet,
    *,
    set_index: int,
    seen: set[str],
    strategy: str,
    renamed_geometry_ids: list[dict[str, str]],
) -> None:
    for geo_index, geometry in enumerate(vis_set.geometry, start=1):
        identifier = getattr(geometry, "identifier", None)
        if not identifier:
            continue
        if identifier not in seen:
            seen.add(identifier)
            continue
        if strategy == "error":
            raise ValueError(f"Duplicate VisualizationSet geometry identifier: {identifier}")
        new_identifier = _unique_geometry_identifier(
            identifier,
            set_index=set_index,
            geo_index=geo_index,
            seen=seen,
        )
        geometry.identifier = new_identifier
        renamed_geometry_ids.append(
            {"original_identifier": identifier, "new_identifier": new_identifier}
        )
        seen.add(new_identifier)


def _unique_geometry_identifier(
    identifier: str,
    *,
    set_index: int,
    geo_index: int,
    seen: set[str],
) -> str:
    stem = f"set_{set_index}_{identifier}"[:90].rstrip("_")
    candidate = stem
    suffix = geo_index
    while candidate in seen:
        candidate = f"{stem}_{suffix}"[:99]
        suffix += 1
    return candidate
