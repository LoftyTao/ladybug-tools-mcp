"""Honeybee model geometry, adjacency, and comparison/repair services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import honeybee_energy  # noqa: F401 - ensures Adiabatic BC is registered on boundary_conditions
from honeybee.boundarycondition import Surface, boundary_conditions
from honeybee.model import Model
from ladybug_geometry.geometry3d.pointvector import Point3D

from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target,
    save_honeybee_model,
)
from garden.honeybee_core.postprocess import (
    apply_honeybee_postprocess,
    attach_postprocess_result,
)
from garden.honeybee_core.targets import normalize_honeybee_model_target
from garden.paths import require_garden_root
from ladybug_tools_mcp.contracts import make_persistence_receipt, make_report


_REPAIR_ACTIONS = (
    "remove_degenerate_geometry",
    "triangulate_non_planar_quads",
    "clean_irrational_geometry",
    "split_rooms_through_holes",
    "rooms_to_extrusions",
    "reset_coordinate_system",
    "clean_envelope",
    "fix_invalid_sub_faces",
    "missing_adjacencies_to_adiabatic",
    "assign_stories_by_floor_height",
    "add_model",
    "comparison_report",
)


def _model_counts(model: Model) -> dict[str, int]:
    return {
        "rooms": len(model.rooms),
        "faces": len(model.faces),
        "apertures": len(model.apertures),
        "doors": len(model.doors),
        "shades": len(model.shades),
        "shade_meshes": len(model.shade_meshes),
        "orphaned_faces": len(model.orphaned_faces),
        "orphaned_apertures": len(model.orphaned_apertures),
        "orphaned_doors": len(model.orphaned_doors),
        "orphaned_shades": len(model.orphaned_shades),
    }


def _point3d_from_input(value: dict[str, Any] | list[float] | tuple[float, ...]) -> Point3D:
    if isinstance(value, dict):
        return Point3D.from_dict(value)
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return Point3D(float(value[0]), float(value[1]), float(value[2]))
    raise ValueError("new_origin must be a Point3D dict or [x, y, z] coordinates.")


def _resolve_other_model(
    garden_root_path: Path,
    other_model_target: dict[str, Any] | None,
    *,
    action: str,
) -> tuple[dict[str, Any], Model]:
    if not isinstance(other_model_target, dict):
        raise ValueError(f"other_model_target is required for action={action!r}.")
    normalized = normalize_honeybee_model_target(other_model_target)
    _, resolved = resolve_model_target(garden_root_path, normalized)
    return resolved, load_honeybee_model(garden_root_path, resolved)


def _check_merge_collisions(target_model: Model, other_model: Model) -> None:
    checks = (
        ("room", {r.identifier for r in target_model.rooms}, [r.identifier for r in other_model.rooms]),
        (
            "orphaned_face",
            {f.identifier for f in target_model.orphaned_faces},
            [f.identifier for f in other_model.orphaned_faces],
        ),
        (
            "orphaned_aperture",
            {a.identifier for a in target_model.orphaned_apertures},
            [a.identifier for a in other_model.orphaned_apertures],
        ),
        (
            "orphaned_door",
            {d.identifier for d in target_model.orphaned_doors},
            [d.identifier for d in other_model.orphaned_doors],
        ),
        (
            "orphaned_shade",
            {s.identifier for s in target_model.orphaned_shades},
            [s.identifier for s in other_model.orphaned_shades],
        ),
        (
            "shade_mesh",
            {m.identifier for m in target_model.shade_meshes},
            [m.identifier for m in other_model.shade_meshes],
        ),
    )
    for kind, existing, incoming in checks:
        collisions = sorted(existing.intersection(incoming))
        if collisions:
            sample = ", ".join(collisions[:5])
            raise ValueError(
                f"Cannot merge models due to duplicate {kind} identifier(s): {sample}. "
                "Provide other_model_prefix to prefix merged object identifiers."
            )


def _missing_adjacencies_to_adiabatic(model: Model) -> dict[str, Any]:
    room_ids = {room.identifier for room in model.rooms}
    faces_by_id = {face.identifier: face for face in model.faces}
    apertures_by_id = {ap.identifier: ap for ap in model.apertures}
    doors_by_id = {door.identifier: door for door in model.doors}

    converted_faces: list[str] = []
    removed_sub_faces: list[str] = []

    for room in model.rooms:
        for face in room.faces:
            bc = face.boundary_condition
            if not isinstance(bc, Surface):
                continue
            bc_objs = bc.boundary_condition_objects
            adj_face_id = bc_objs[0] if len(bc_objs) >= 1 else None
            adj_room_id = bc_objs[1] if len(bc_objs) >= 2 else None
            adj_face = faces_by_id.get(adj_face_id) if adj_face_id else None
            missing_face = adj_face_id == face.identifier or adj_face is None
            missing_room = adj_room_id is not None and adj_room_id not in room_ids
            asymmetric_face = (
                adj_face is not None
                and (
                    not isinstance(adj_face.boundary_condition, Surface)
                    or adj_face.boundary_condition.boundary_condition_objects[0] != face.identifier
                )
            )
            if missing_face or missing_room or asymmetric_face:
                if face.sub_faces:
                    removed_sub_faces.extend(sf.identifier for sf in face.sub_faces)
                    face.remove_sub_faces()
                face.boundary_condition = boundary_conditions.adiabatic
                converted_faces.append(face.identifier)
                continue

            bad_ap_ids: list[str] = []
            for ap in face.apertures:
                if not isinstance(ap.boundary_condition, Surface):
                    bad_ap_ids.append(ap.identifier)
                    continue
                ap_objs = ap.boundary_condition.boundary_condition_objects
                adj_ap_id = ap_objs[0] if len(ap_objs) >= 1 else None
                ap_room_id = ap_objs[2] if len(ap_objs) >= 3 else None
                adj_ap = apertures_by_id.get(adj_ap_id) if adj_ap_id else None
                if (
                    adj_ap_id == ap.identifier
                    or adj_ap is None
                    or (ap_room_id is not None and ap_room_id not in room_ids)
                    or not isinstance(adj_ap.boundary_condition, Surface)
                    or adj_ap.boundary_condition.boundary_condition_objects[0] != ap.identifier
                ):
                    bad_ap_ids.append(ap.identifier)
            if bad_ap_ids:
                face._apertures = Model._remove_by_ids(face._apertures, bad_ap_ids)
                face._punched_geometry = None
                removed_sub_faces.extend(bad_ap_ids)

            bad_door_ids: list[str] = []
            for door in face.doors:
                if not isinstance(door.boundary_condition, Surface):
                    bad_door_ids.append(door.identifier)
                    continue
                d_objs = door.boundary_condition.boundary_condition_objects
                adj_d_id = d_objs[0] if len(d_objs) >= 1 else None
                d_room_id = d_objs[2] if len(d_objs) >= 3 else None
                adj_door = doors_by_id.get(adj_d_id) if adj_d_id else None
                if (
                    adj_d_id == door.identifier
                    or adj_door is None
                    or (d_room_id is not None and d_room_id not in room_ids)
                    or not isinstance(adj_door.boundary_condition, Surface)
                    or adj_door.boundary_condition.boundary_condition_objects[0] != door.identifier
                ):
                    bad_door_ids.append(door.identifier)
            if bad_door_ids:
                face._doors = Model._remove_by_ids(face._doors, bad_door_ids)
                face._punched_geometry = None
                removed_sub_faces.extend(bad_door_ids)

    return {
        "converted_face_count": len(converted_faces),
        "converted_face_identifiers": converted_faces[:50],
        "removed_sub_face_count": len(removed_sub_faces),
        "removed_sub_face_identifiers": removed_sub_faces[:50],
    }


def _fix_invalid_sub_faces(
    model: Model,
    *,
    trim_with_parent: bool,
    union_overlaps: bool,
    offset_distance: float,
    tolerance: float | None,
    include_surface_faces: bool,
) -> dict[str, Any]:
    tol = model.tolerance if tolerance is None else float(tolerance)
    all_faces = [*model.faces, *model.orphaned_faces]
    processed = 0
    modified_faces: list[str] = []
    skipped_surface_faces: list[str] = []

    for face in all_faces:
        if not face.has_sub_faces:
            continue
        if isinstance(face.boundary_condition, Surface) and not include_surface_faces:
            skipped_surface_faces.append(face.identifier)
            continue
        before_sig = [(sf.identifier, sf.geometry.area) for sf in face.sub_faces]
        face.fix_invalid_sub_faces(
            trim_with_parent=trim_with_parent,
            union_overlaps=union_overlaps,
            offset_distance=offset_distance,
            tolerance=tol,
        )
        processed += 1
        after_sig = [(sf.identifier, sf.geometry.area) for sf in face.sub_faces]
        if before_sig != after_sig:
            modified_faces.append(face.identifier)

    return {
        "processed_face_count": processed,
        "modified_face_count": len(modified_faces),
        "modified_face_identifiers": modified_faces[:50],
        "skipped_surface_face_count": len(skipped_surface_faces),
    }


def _clean_envelope(model: Model, *, tolerance: float | None) -> dict[str, Any]:
    tol = model.tolerance if tolerance is None else float(tolerance)
    adj_dict: dict[str, Any] = {}
    cleaned_rooms = 0
    for room in model.rooms:
        try:
            r_adj = room.clean_envelope(adj_dict, tolerance=tol)
        except AssertionError as exc:
            raise ValueError(
                f"Failed to clean envelope for Room {room.identifier}: {exc}"
            ) from exc
        adj_dict.update(r_adj)
        cleaned_rooms += 1
    return {
        "cleaned_room_count": cleaned_rooms,
        "coordinated_adjacent_face_count": len(adj_dict),
    }


def _clean_irrational_from_disk_or_model(
    garden_root_path: Path,
    model_target: dict[str, Any],
) -> tuple[Model, dict[str, Any]]:
    rel_path = model_target.get("path")
    if isinstance(rel_path, str) and rel_path:
        raw_path = (garden_root_path / rel_path).resolve()
        raw_path.relative_to(garden_root_path.resolve())
        with raw_path.open("r", encoding="utf-8") as handle:
            model_dict = json.load(handle)
    else:
        model_dict = load_honeybee_model(garden_root_path, model_target).to_dict()

    before_rooms = len(model_dict.get("rooms") or [])
    before_orphaned_faces = len(model_dict.get("orphaned_faces") or [])
    before_orphaned_shades = len(model_dict.get("orphaned_shades") or [])
    Model.clean_irrational_geometry(model_dict)
    cleaned = Model.from_dict(model_dict, cleanup_irrational=False)
    return cleaned, {
        "raw_rooms_before": before_rooms,
        "raw_rooms_after": len(cleaned.rooms),
        "raw_orphaned_faces_before": before_orphaned_faces,
        "raw_orphaned_faces_after": len(cleaned.orphaned_faces),
        "raw_orphaned_shades_before": before_orphaned_shades,
        "raw_orphaned_shades_after": len(cleaned.orphaned_shades),
    }


def repair_honeybee_model(
    *,
    garden_root: str,
    action: str,
    model_target: dict[str, Any] | None = None,
    other_model_target: dict[str, Any] | None = None,
    other_model_prefix: str | None = None,
    tolerance: float | None = None,
    angle_tolerance: float | None = None,
    new_origin: dict[str, Any] | list[float] | None = None,
    trim_with_parent: bool = True,
    union_overlaps: bool = True,
    offset_distance: float = 0.05,
    include_surface_faces: bool = False,
    min_difference: float = 2.0,
    overwrite: bool = False,
    ignore_deleted: bool = False,
    ignore_added: bool = False,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Run Honeybee Model repair, cleanup, merge, or comparison diagnostics."""
    normalized_action = str(action or "").strip().lower()
    if normalized_action not in _REPAIR_ACTIONS:
        allowed = ", ".join(_REPAIR_ACTIONS)
        raise ValueError(f"Unsupported repair action {action!r}. Supported: {allowed}.")

    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)

    if normalized_action == "comparison_report":
        base_model = load_honeybee_model(garden_root_path, resolved_model_target)
        resolved_other_target, other_model = _resolve_other_model(
            garden_root_path,
            other_model_target,
            action=normalized_action,
        )
        report_dict = base_model.comparison_report(
            other_model,
            ignore_deleted=ignore_deleted,
            ignore_added=ignore_added,
        )
        return {
            "target": resolved_model_target,
            "model_target": resolved_model_target,
            "other_model_target": resolved_other_target,
            "comparison_report": report_dict,
            "summary_view": {
                "action": normalized_action,
                "model_target": resolved_model_target,
                "other_model_target": resolved_other_target,
                "changed_object_count": len(report_dict.get("changed_objects") or []),
                "added_object_count": len(report_dict.get("added_objects") or []),
                "deleted_object_count": len(report_dict.get("deleted_objects") or []),
            },
            "report": make_report(
                status="ok",
                message="Generated Honeybee model comparison report.",
            ),
        }

    action_details: dict[str, Any] = {}
    if normalized_action == "clean_irrational_geometry":
        before_counts = {}
        try:
            current_model = load_honeybee_model(garden_root_path, resolved_model_target)
            before_counts = _model_counts(current_model)
        except Exception:
            before_counts = {}
        working_model, action_details = _clean_irrational_from_disk_or_model(
            garden_root_path,
            resolved_model_target,
        )
        if not before_counts:
            before_counts = {
                "rooms": action_details["raw_rooms_before"],
                "orphaned_faces": action_details["raw_orphaned_faces_before"],
                "orphaned_shades": action_details["raw_orphaned_shades_before"],
            }
    else:
        working_model = load_honeybee_model(garden_root_path, resolved_model_target).duplicate()
        before_counts = _model_counts(working_model)

        if normalized_action == "remove_degenerate_geometry":
            working_model.remove_degenerate_geometry(tolerance=tolerance)
        elif normalized_action == "triangulate_non_planar_quads":
            working_model.triangulate_non_planar_quads(tolerance=tolerance)
        elif normalized_action == "split_rooms_through_holes":
            new_faces = working_model.split_rooms_through_holes(
                tolerance=tolerance,
                angle_tolerance=angle_tolerance,
            )
            action_details = {
                "split_face_count": len(new_faces),
                "new_face_identifiers": [f.identifier for f in new_faces[:50]],
            }
        elif normalized_action == "rooms_to_extrusions":
            working_model.rooms_to_extrusions(
                tolerance=tolerance,
                angle_tolerance=angle_tolerance,
            )
        elif normalized_action == "reset_coordinate_system":
            origin_pt = _point3d_from_input(new_origin) if new_origin is not None else None
            min_before = [working_model.min.x, working_model.min.y, working_model.min.z]
            working_model.reset_coordinate_system(new_origin=origin_pt)
            min_after = [working_model.min.x, working_model.min.y, working_model.min.z]
            action_details = {
                "model_min_before": min_before,
                "model_min_after": min_after,
            }
        elif normalized_action == "clean_envelope":
            action_details = _clean_envelope(working_model, tolerance=tolerance)
        elif normalized_action == "fix_invalid_sub_faces":
            action_details = _fix_invalid_sub_faces(
                working_model,
                trim_with_parent=trim_with_parent,
                union_overlaps=union_overlaps,
                offset_distance=offset_distance,
                tolerance=tolerance,
                include_surface_faces=include_surface_faces,
            )
        elif normalized_action == "missing_adjacencies_to_adiabatic":
            action_details = _missing_adjacencies_to_adiabatic(working_model)
        elif normalized_action == "assign_stories_by_floor_height":
            stories = working_model.assign_stories_by_floor_height(
                min_difference=min_difference,
                overwrite=overwrite,
            )
            action_details = {
                "stories": list(stories),
                "story_count": len(stories),
                "room_stories": {r.identifier: r.story for r in working_model.rooms},
            }
        elif normalized_action == "add_model":
            resolved_other_target, other_model = _resolve_other_model(
                garden_root_path,
                other_model_target,
                action=normalized_action,
            )
            merged_other = other_model.duplicate()
            if other_model_prefix:
                merged_other.add_prefix(other_model_prefix)
            _check_merge_collisions(working_model, merged_other)
            working_model.add_model(merged_other)
            action_details = {
                "other_model_target": resolved_other_target,
                "other_model_prefix": other_model_prefix,
            }

    after_counts = _model_counts(working_model)
    effective_strategy = postprocess_strategy or "auto_validate"
    working_model, postprocess = apply_honeybee_postprocess(
        model=working_model,
        garden_id=manifest.garden_id,
        model_identifier=str(resolved_model_target["model_identifier"]),
        operation=f"repair_honeybee_model.{normalized_action}",
        target=resolved_model_target,
        object_type="model",
        updated_fields=[normalized_action],
        strategy=effective_strategy,
    )
    after_counts = _model_counts(working_model)

    updated_model_target, persisted_path = save_honeybee_model(
        garden_root_path,
        manifest,
        working_model,
        name=str(resolved_model_target["model_identifier"]),
        set_base=manifest.base_honeybee_model == resolved_model_target,
    )
    summary_view = {
        "action": normalized_action,
        "target": updated_model_target,
        "model_target": updated_model_target,
        "counts_before": before_counts,
        "counts_after": after_counts,
        **action_details,
    }
    response = {
        "target": updated_model_target,
        "model_target": updated_model_target,
        "summary_view": summary_view,
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            base_honeybee_model_changed=manifest.base_honeybee_model == resolved_model_target,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            change_summary={
                "operation": "repair_honeybee_model",
                "action": normalized_action,
                "counts_before": before_counts,
                "counts_after": after_counts,
                **action_details,
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Completed Honeybee model repair action '{normalized_action}'.",
        ),
    }
    return attach_postprocess_result(response, postprocess)
