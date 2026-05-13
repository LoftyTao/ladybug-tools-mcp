"""Honeybee relationship processing services."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from honeybee.aperture import Aperture
from honeybee.boundarycondition import Surface, boundary_conditions
from honeybee.door import Door
from honeybee.face import Face
from honeybee.model import Model
from honeybee.room import Room
from ladybug_geometry.geometry3d.face import Face3D

from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target,
    save_honeybee_model,
    with_honeybee_model_write_lock,
)
from garden.honeybee_core.targets import make_honeybee_object_target


@with_honeybee_model_write_lock
def relate_honeybee_model(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    relation_mode: str = "solve_adjacency",
    intersect: bool = True,
    merge_coplanar: bool = False,
    overwrite: bool = False,
    remove_mismatched_sub_faces: bool = False,
    subface_mismatch_policy: str = "clone_single",
    air_boundary: bool = False,
    adiabatic: bool = False,
    relationship_cleanup: bool = False,
    tolerance: float | None = None,
    angle_tolerance: float | None = None,
) -> dict[str, Any]:
    """Run SDK-backed relationship processing on a Honeybee model."""
    if relation_mode not in {"solve_adjacency", "explicit_relate_full"}:
        raise ValueError(
            "relation_mode currently supports 'solve_adjacency' or "
            "'explicit_relate_full'."
        )

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, model_target = resolve_model_target(garden_root_path, model_target)
    model = load_honeybee_model(garden_root_path, model_target)
    before_counts = _adjacency_counts(model)
    before_face_count = len(model.faces)
    tol = tolerance if tolerance is not None else model.tolerance
    angle_tol = (
        angle_tolerance
        if angle_tolerance is not None
        else model.angle_tolerance
    )

    if relation_mode == "explicit_relate_full":
        merge_coplanar = True
        overwrite = True
        remove_mismatched_sub_faces = True
        relationship_cleanup = True
        if subface_mismatch_policy == "clone_single":
            subface_mismatch_policy = "clone_missing"

    if subface_mismatch_policy not in {"none", "clone_single", "clone_missing"}:
        raise ValueError(
            "subface_mismatch_policy must be one of 'none', 'clone_single', "
            "or 'clone_missing'."
        )

    cleanup_summary = (
        _clear_surface_relationships(model) if relationship_cleanup else _empty_cleanup_summary()
    )
    if merge_coplanar:
        for room in model.rooms:
            room.merge_coplanar_faces(tol, angle_tol)
    if intersect:
        Room.intersect_adjacency(model.rooms, tol, angle_tol)

    patch_summary = _clone_missing_subfaces(
        model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        tolerance=tol,
        angle_tolerance=angle_tol,
        policy=subface_mismatch_policy,
    ) if subface_mismatch_policy in {"clone_single", "clone_missing"} else _empty_patch_summary()

    model.solve_adjacency(
        merge_coplanar=False,
        intersect=False,
        overwrite=overwrite,
        remove_mismatched_sub_faces=remove_mismatched_sub_faces,
        air_boundary=air_boundary,
        adiabatic=adiabatic,
        tolerance=tolerance,
        angle_tolerance=angle_tolerance,
    )

    after_counts = _adjacency_counts(model)
    after_face_count = len(model.faces)
    updated_model_target, persisted_path = save_honeybee_model(
        garden_root_path,
        manifest,
        model,
        name=str(model_target["model_identifier"]),
        set_base=manifest.base_honeybee_model == model_target,
    )
    warnings = []
    if intersect:
        warnings.append(
            "intersect=True can modify Room Face geometry before adjacency solving; "
            "run validate_honeybee_model to review the resulting model."
        )
    warnings.extend(patch_summary["warnings"])
    return {
        "summary_view": {
            "model_target": updated_model_target,
            "relation_mode": relation_mode,
            "options": {
                "intersect": intersect,
                "merge_coplanar": merge_coplanar,
                "overwrite": overwrite,
                "remove_mismatched_sub_faces": remove_mismatched_sub_faces,
                "subface_mismatch_policy": subface_mismatch_policy,
                "air_boundary": air_boundary,
                "adiabatic": adiabatic,
                "relationship_cleanup": relationship_cleanup,
                "tolerance": tolerance,
                "angle_tolerance": angle_tolerance,
            },
            "face_count_before": before_face_count,
            "face_count_after": after_face_count,
            "adjacency_counts_before": before_counts,
            "adjacency_counts_after": after_counts,
            "subface_patch": patch_summary,
            "relationship_cleanup": cleanup_summary,
        },
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            warnings=warnings,
            change_summary={
                "operation": "relate_honeybee_model",
                "relation_mode": relation_mode,
                "adjacency_counts_before": before_counts,
                "adjacency_counts_after": after_counts,
                "face_count_before": before_face_count,
                "face_count_after": after_face_count,
                "subface_patch": patch_summary,
                "relationship_cleanup": cleanup_summary,
            },
        ),
        "report": make_report(
            status="ok",
            message=(
                "Solved Honeybee model adjacency: "
                f"{updated_model_target['model_identifier']}"
            ),
            warnings=warnings,
            details={
                "relation_mode": relation_mode,
                "adjacency_counts_before": before_counts,
                "adjacency_counts_after": after_counts,
                "subface_patch": patch_summary,
                "relationship_cleanup": cleanup_summary,
            },
        ),
    }


def _adjacency_counts(model) -> dict[str, int]:
    adjacent_faces = 0
    adjacent_apertures = 0
    adjacent_doors = 0
    for room in model.rooms:
        for face in room.faces:
            if isinstance(face.boundary_condition, Surface):
                adjacent_faces += 1
            for aperture in face.apertures:
                if isinstance(aperture.boundary_condition, Surface):
                    adjacent_apertures += 1
            for door in face.doors:
                if isinstance(door.boundary_condition, Surface):
                    adjacent_doors += 1
    return {
        "faces": adjacent_faces,
        "apertures": adjacent_apertures,
        "doors": adjacent_doors,
    }


def _empty_patch_summary() -> dict[str, Any]:
    return {
        "policy": "none",
        "created_count": 0,
        "created_targets": [],
        "skipped": [],
        "warnings": [],
    }


def _empty_cleanup_summary() -> dict[str, Any]:
    return {
        "enabled": False,
        "cleared_faces": 0,
        "cleared_apertures": 0,
        "cleared_doors": 0,
    }


def _clear_surface_relationships(model: Model) -> dict[str, Any]:
    cleared_faces = 0
    cleared_apertures = 0
    cleared_doors = 0
    for room in model.rooms:
        for face in room.faces:
            if isinstance(face.boundary_condition, Surface):
                face.boundary_condition = boundary_conditions.outdoors
                cleared_faces += 1
            for aperture in face.apertures:
                if isinstance(aperture.boundary_condition, Surface):
                    aperture.boundary_condition = boundary_conditions.outdoors
                    cleared_apertures += 1
            for door in face.doors:
                if isinstance(door.boundary_condition, Surface):
                    door.boundary_condition = boundary_conditions.outdoors
                    cleared_doors += 1
    return {
        "enabled": True,
        "cleared_faces": cleared_faces,
        "cleared_apertures": cleared_apertures,
        "cleared_doors": cleared_doors,
    }


def _clone_missing_subfaces(
    model: Model,
    *,
    garden_id: str,
    model_identifier: str,
    tolerance: float,
    angle_tolerance: float,
    policy: str = "clone_single",
) -> dict[str, Any]:
    existing_identifiers = _subface_identifiers(model)
    created_targets: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    warnings: list[str] = []
    for face_1, face_2 in Room.find_adjacency(model.rooms, tolerance):
        if isinstance(face_1.boundary_condition, Surface) or isinstance(
            face_2.boundary_condition,
            Surface,
        ):
            continue
        patch = _missing_subface_patch(face_1, face_2)
        if patch is None:
            skip = _skip_for_unhandled_subface_pair(face_1, face_2)
            if skip is not None:
                skipped.append(skip)
            continue

        source_face, target_face, source_subfaces = patch
        if policy == "clone_single" and len(source_subfaces) != 1:
            skipped.append(
                {
                    "reason": "unsupported_multi_subface_mismatch_for_clone_single",
                    "source_face": source_face.identifier,
                    "source_subface_count": len(source_subfaces),
                    "target_face": target_face.identifier,
                }
            )
            continue

        for source_subface in source_subfaces:
            clone = source_subface.duplicate()
            clone.identifier = _unique_subface_identifier(
                source_subface.identifier,
                existing_identifiers,
            )
            if not _project_subface_to_face(
                clone,
                source_face,
                target_face,
                tolerance=tolerance,
                angle_tolerance=angle_tolerance,
            ):
                skipped.append(
                    {
                        "reason": "projected_subface_outside_target_face",
                        "source_face": source_face.identifier,
                        "target_face": target_face.identifier,
                        "source_subface": source_subface.identifier,
                    }
                )
                continue

            existing_identifiers.add(clone.identifier)
            target = make_honeybee_object_target(
                garden_id=garden_id,
                model_identifier=model_identifier,
                object_type="aperture" if isinstance(clone, Aperture) else "door",
                object_identifier=clone.identifier,
                parent={
                    "room_identifier": target_face.parent.identifier,
                    "face_identifier": target_face.identifier,
                },
            )
            created_targets.append(
                {
                    "target": target,
                    "source_identifier": source_subface.identifier,
                    "source_face_identifier": source_face.identifier,
                    "target_face_identifier": target_face.identifier,
                }
            )
            if _has_dynamic_states(source_subface):
                warnings.append(
                    "Cloned a subface with Radiance dynamic states and projected "
                    f"state geometry to the adjacent face: {source_subface.identifier}."
                )

    return {
        "policy": policy,
        "created_count": len(created_targets),
        "created_targets": created_targets,
        "skipped": skipped,
        "warnings": warnings,
    }


def _clone_single_missing_subfaces(
    model: Model,
    *,
    garden_id: str,
    model_identifier: str,
    tolerance: float,
    angle_tolerance: float,
) -> dict[str, Any]:
    return _clone_missing_subfaces(
        model,
        garden_id=garden_id,
        model_identifier=model_identifier,
        tolerance=tolerance,
        angle_tolerance=angle_tolerance,
        policy="clone_single",
    )


def _missing_subface_patch(
    face_1: Face,
    face_2: Face,
) -> tuple[Face, Face, list[Aperture | Door]] | None:
    patches: list[tuple[Face, Face, list[Aperture | Door]]] = []
    for subface_getter in (lambda face: list(face.apertures), lambda face: list(face.doors)):
        subfaces_1 = subface_getter(face_1)
        subfaces_2 = subface_getter(face_2)
        if subfaces_1 and not subfaces_2:
            patches.append((face_1, face_2, subfaces_1))
        elif subfaces_2 and not subfaces_1:
            patches.append((face_2, face_1, subfaces_2))
    if len(patches) == 1:
        return patches[0]
    return None


def _skip_for_unhandled_subface_pair(face_1: Face, face_2: Face) -> dict[str, Any] | None:
    subfaces_1 = list(face_1.sub_faces)
    subfaces_2 = list(face_2.sub_faces)
    if not subfaces_1 and not subfaces_2:
        return None
    if len(subfaces_1) == len(subfaces_2):
        return None
    return {
        "reason": "unsupported_subface_mismatch",
        "face_1": face_1.identifier,
        "face_1_subface_count": len(subfaces_1),
        "face_2": face_2.identifier,
        "face_2_subface_count": len(subfaces_2),
    }


def _project_subface_to_face(
    subface: Aperture | Door,
    source_face: Face,
    target_face: Face,
    *,
    tolerance: float,
    angle_tolerance: float,
) -> bool:
    source_plane = source_face.geometry.plane
    target_plane = target_face.geometry.plane
    before_count = len(target_face.sub_faces)
    target_face.project_and_add_sub_face(subface, angle_tolerance=angle_tolerance)
    was_added = len(target_face.sub_faces) == before_count + 1 and subface.parent is target_face
    is_valid_subface = was_added and target_face.geometry.is_sub_face(
        subface.geometry,
        tolerance,
        math.radians(angle_tolerance),
    )
    if not is_valid_subface:
        if was_added:
            _remove_subface_by_identifier(target_face, subface)
        return False
    _project_radiance_state_geometry(subface, source_plane, target_plane)
    return True


def _remove_subface_by_identifier(face: Face, subface: Aperture | Door) -> None:
    if isinstance(subface, Aperture):
        face._apertures = Model._remove_by_ids(face._apertures, [subface.identifier])
    else:
        face._doors = Model._remove_by_ids(face._doors, [subface.identifier])
    subface._parent = None
    face._punched_geometry = None


def _project_radiance_state_geometry(
    subface: Aperture | Door,
    source_plane: Any,
    target_plane: Any,
) -> None:
    radiance = getattr(subface.properties, "radiance", None)
    for state in getattr(radiance, "states", ()):
        for shade in getattr(state, "shades", ()):
            shade._geometry = _project_face3d_between_planes(
                shade.geometry,
                source_plane,
                target_plane,
            )
        if getattr(state, "_vmtx_geometry", None) is not None:
            state._vmtx_geometry = _project_face3d_between_planes(
                state._vmtx_geometry,
                source_plane,
                target_plane,
            )
        if getattr(state, "_dmtx_geometry", None) is not None:
            state._dmtx_geometry = _project_face3d_between_planes(
                state._dmtx_geometry,
                source_plane,
                target_plane,
            )


def _project_face3d_between_planes(
    geometry: Face3D,
    source_plane: Any,
    target_plane: Any,
) -> Face3D:
    boundary = [
        _project_point_between_planes(point, source_plane, target_plane)
        for point in geometry.boundary
    ]
    holes = (
        [
            [
                _project_point_between_planes(point, source_plane, target_plane)
                for point in hole
            ]
            for hole in geometry.holes
        ]
        if geometry.has_holes
        else None
    )
    return Face3D(boundary, target_plane, holes)


def _project_point_between_planes(
    point: Any,
    source_plane: Any,
    target_plane: Any,
    *,
    preserve_offset: bool = True,
) -> Any:
    projected = target_plane.project_point(point)
    if not preserve_offset:
        return projected
    offset = source_plane.n.dot(point - source_plane.o)
    return projected.move(target_plane.n * offset)


def _unique_subface_identifier(source_identifier: str, existing: set[str]) -> str:
    base = f"{source_identifier}_Adjacent"
    if len(base) > 92:
        base = base[:92]
    candidate = base
    index = 1
    while candidate in existing:
        suffix = f"_{index}"
        candidate = f"{base[:100 - len(suffix)]}{suffix}"
        index += 1
    return candidate


def _subface_identifiers(model: Model) -> set[str]:
    return {
        subface.identifier
        for face in model.faces
        for subface in face.sub_faces
    }


def _has_dynamic_states(subface: Aperture | Door) -> bool:
    radiance = getattr(subface.properties, "radiance", None)
    return bool(getattr(radiance, "state_count", 0))
