"""Honeybee object removal services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from honeybee.aperture import Aperture
from honeybee.boundarycondition import Surface, boundary_conditions
from honeybee.door import Door
from honeybee.face import Face
from honeybee.model import Model
from honeybee.room import Room
from honeybee.shade import Shade

from ladybug_tools_mcp.contracts import make_persistence_receipt, make_report
from garden.honeybee_core.locate import find_object
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target,
    save_honeybee_model,
)
from garden.honeybee_core.postprocess import (
    apply_honeybee_postprocess,
    attach_postprocess_result,
)
from garden.honeybee_core.targets import normalize_honeybee_object_target

_REMOVAL_PRIORITY = {
    "shade": 0,
    "aperture": 1,
    "door": 2,
    "face": 3,
    "room": 4,
}


def _removal_response(
    *,
    manifest: Any,
    updated_model_target: dict[str, Any],
    persisted_path: str,
    operation: str,
    target: dict[str, Any],
    removed_identifier: str,
    object_label: str,
    removed_count: int = 1,
    paired_removed_identifier: str | None = None,
    postprocess: dict[str, Any] | None = None,
    adjacency_cleanup: dict[str, int] | None = None,
) -> dict[str, Any]:
    adjacency_cleanup = adjacency_cleanup or {}
    receipt = make_persistence_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        model_target=updated_model_target,
        persisted_path=persisted_path,
        change_summary={
            "operation": operation,
            "target": target,
            "removed_identifier": removed_identifier,
            "removed_count": removed_count,
            "paired_removed_identifier": paired_removed_identifier,
            "adjacency_cleanup": adjacency_cleanup,
        },
    )
    summary_view = {
        "removed_count": removed_count,
        "removed_identifier": removed_identifier,
        "model_target": updated_model_target,
    }
    if paired_removed_identifier:
        summary_view["paired_removed_identifier"] = paired_removed_identifier
    if adjacency_cleanup:
        summary_view["adjacency_cleanup"] = adjacency_cleanup
    return attach_postprocess_result({
        "summary_view": summary_view,
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=f"Removed Honeybee {object_label}: {removed_identifier}",
        ),
    }, postprocess or {})


def _save_removed_model(
    *,
    garden_root: Path,
    manifest: Any,
    model_target: dict[str, Any],
    model: Model,
) -> tuple[dict[str, Any], str]:
    return save_honeybee_model(
        garden_root,
        manifest,
        model,
        name=str(model_target["model_identifier"]),
        set_base=manifest.base_honeybee_model == model_target,
    )


def _find_room_by_identifier(model: Model, room_identifier: str) -> Room:
    for room in model.rooms:
        if room.identifier == room_identifier:
            return room
    raise ValueError(f"Honeybee Room not found: {room_identifier}")


def _surface_references_room(boundary_condition: Any, room_identifier: str) -> bool:
    if not isinstance(boundary_condition, Surface):
        return False
    return room_identifier in boundary_condition.boundary_condition_objects


def _clear_surface_references_to_room(model: Model, room_identifier: str) -> dict[str, int]:
    cleared = {"faces": 0, "apertures": 0, "doors": 0}
    for room in model.rooms:
        if room.identifier == room_identifier:
            continue
        for face in room.faces:
            if _surface_references_room(face.boundary_condition, room_identifier):
                face.boundary_condition = boundary_conditions.outdoors
                cleared["faces"] += 1
            for aperture in list(face.apertures):
                if _surface_references_room(
                    aperture.boundary_condition,
                    room_identifier,
                ):
                    _remove_hosted_subface(face, aperture, list_name="_apertures")
                    cleared["apertures"] += 1
            for door in list(face.doors):
                if _surface_references_room(door.boundary_condition, room_identifier):
                    _remove_hosted_subface(face, door, list_name="_doors")
                    cleared["doors"] += 1
    return cleared


def _find_face_by_identifier(
    model: Model,
    *,
    face_identifier: str,
    room_identifier: str | None = None,
) -> Face:
    if room_identifier is not None:
        room = _find_room_by_identifier(model, room_identifier)
        for face in room.faces:
            if face.identifier == face_identifier:
                return face
        raise ValueError(
            f"Honeybee Face not found in Room {room_identifier}: {face_identifier}"
        )

    for face in model.orphaned_faces:
        if face.identifier == face_identifier:
            return face
    raise ValueError(f"Honeybee Face not found: {face_identifier}")


def _remove_hosted_subface(face: Face, subface: Any, *, list_name: str) -> None:
    current = getattr(face, list_name)
    setattr(face, list_name, Model._remove_by_ids(current, [subface.identifier]))
    subface._parent = None


def _find_adjacent_subface(model: Model, subface: Any) -> Any | None:
    boundary_condition = getattr(subface, "boundary_condition", None)
    if not isinstance(boundary_condition, Surface):
        return None

    boundary_objects = boundary_condition.boundary_condition_objects
    if len(boundary_objects) != 3:
        raise ValueError(
            "Surface-adjacent Honeybee sub-faces must include adjacent object, "
            "face, and room identifiers."
        )

    adjacent_identifier, adjacent_face_identifier, adjacent_room_identifier = (
        boundary_objects
    )
    adjacent_face = _find_face_by_identifier(
        model,
        face_identifier=adjacent_face_identifier,
        room_identifier=adjacent_room_identifier,
    )
    candidates = (
        adjacent_face.apertures if isinstance(subface, Aperture) else adjacent_face.doors
    )
    for candidate in candidates:
        if candidate.identifier == adjacent_identifier:
            return candidate
    raise ValueError(
        f"Adjacent Honeybee {subface.__class__.__name__} not found: {adjacent_identifier}"
    )


def _remove_hosted_shade(host: Any, shade: Shade) -> None:
    if not isinstance(host, (Room, Face, Aperture, Door)):
        raise ValueError("Hosted shade parent must be a Room, Face, Aperture, or Door.")

    shade_ids = [shade.identifier]
    if shade.is_indoor:
        host._indoor_shades = Model._remove_by_ids(host._indoor_shades, shade_ids)
        shade._is_indoor = False
    else:
        host._outdoor_shades = Model._remove_by_ids(host._outdoor_shades, shade_ids)
    shade._parent = None


def _remove_room_in_model(model: Model, room: Room) -> dict[str, int]:
    adjacency_cleanup = _clear_surface_references_to_room(model, room.identifier)
    model.remove_rooms(room_ids=[room.identifier])
    return adjacency_cleanup


def _remove_face_in_model(model: Model, face: Face) -> None:
    model.remove_faces(face_ids=[face.identifier])


def _remove_aperture_in_model(model: Model, aperture: Aperture) -> tuple[int, str | None]:
    paired_removed_identifier: str | None = None
    removed_count = 1
    if aperture.parent is None:
        model.remove_apertures(aperture_ids=[aperture.identifier])
    else:
        if not isinstance(aperture.parent, Face):
            raise ValueError("Hosted aperture parent must be a Honeybee Face.")
        adjacent_aperture = _find_adjacent_subface(model, aperture)
        _remove_hosted_subface(aperture.parent, aperture, list_name="_apertures")
        if adjacent_aperture is not None:
            if not isinstance(adjacent_aperture.parent, Face):
                raise ValueError("Adjacent aperture parent must be a Honeybee Face.")
            _remove_hosted_subface(
                adjacent_aperture.parent,
                adjacent_aperture,
                list_name="_apertures",
            )
            paired_removed_identifier = adjacent_aperture.identifier
            removed_count = 2
    return removed_count, paired_removed_identifier


def _remove_door_in_model(model: Model, door: Door) -> tuple[int, str | None]:
    paired_removed_identifier: str | None = None
    removed_count = 1
    if door.parent is None:
        model.remove_doors(door_ids=[door.identifier])
    else:
        if not isinstance(door.parent, Face):
            raise ValueError("Hosted door parent must be a Honeybee Face.")
        adjacent_door = _find_adjacent_subface(model, door)
        _remove_hosted_subface(door.parent, door, list_name="_doors")
        if adjacent_door is not None:
            if not isinstance(adjacent_door.parent, Face):
                raise ValueError("Adjacent door parent must be a Honeybee Face.")
            _remove_hosted_subface(
                adjacent_door.parent,
                adjacent_door,
                list_name="_doors",
            )
            paired_removed_identifier = adjacent_door.identifier
            removed_count = 2
    return removed_count, paired_removed_identifier


def _remove_shade_in_model(model: Model, shade: Shade) -> None:
    if shade.parent is None:
        model.remove_shades(shade_ids=[shade.identifier])
    else:
        _remove_hosted_shade(shade.parent, shade)


def remove_honeybee_room(
    *,
    garden_root: str,
    target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Remove one Honeybee Room from a model by typed target."""
    target = normalize_honeybee_object_target(target)
    if target.get("object_type") != "room":
        raise ValueError("remove_honeybee_room requires a room target.")

    garden_root = Path(garden_root).expanduser().resolve()
    manifest, model_target = resolve_model_target(garden_root, model_target)
    model = load_honeybee_model(garden_root, model_target)

    room = find_object(model, target)
    if not isinstance(room, Room):
        raise ValueError("Target does not resolve to a Honeybee Room.")

    adjacency_cleanup = _remove_room_in_model(model, room)
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="remove_honeybee_room",
        target=target,
        object_type="room",
        strategy=postprocess_strategy,
    )
    updated_model_target, persisted_path = _save_removed_model(
        garden_root=garden_root,
        manifest=manifest,
        model_target=model_target,
        model=model,
    )
    return _removal_response(
        manifest=manifest,
        updated_model_target=updated_model_target,
        persisted_path=persisted_path,
        operation="remove_honeybee_room",
        target=target,
        removed_identifier=room.identifier,
        object_label="room",
        postprocess=postprocess,
        adjacency_cleanup=adjacency_cleanup,
    )


def remove_honeybee_face(
    *,
    garden_root: str,
    target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Remove one orphaned Honeybee Face from a model by typed target."""
    target = normalize_honeybee_object_target(target)
    if target.get("object_type") != "face":
        raise ValueError("remove_honeybee_face requires a face target.")
    if target.get("parent", {}).get("room_identifier"):
        raise ValueError(
            "remove_honeybee_face does not support room-hosted faces because it "
            "would break the Room closed solid."
        )

    garden_root = Path(garden_root).expanduser().resolve()
    manifest, model_target = resolve_model_target(garden_root, model_target)
    model = load_honeybee_model(garden_root, model_target)

    face = find_object(model, target)
    if not isinstance(face, Face):
        raise ValueError("Target does not resolve to a Honeybee Face.")
    _remove_face_in_model(model, face)
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="remove_honeybee_face",
        target=target,
        object_type="face",
        strategy=postprocess_strategy,
    )

    updated_model_target, persisted_path = _save_removed_model(
        garden_root=garden_root,
        manifest=manifest,
        model_target=model_target,
        model=model,
    )
    return _removal_response(
        manifest=manifest,
        updated_model_target=updated_model_target,
        persisted_path=persisted_path,
        operation="remove_honeybee_face",
        target=target,
        removed_identifier=face.identifier,
        object_label="face",
        postprocess=postprocess,
    )


def remove_honeybee_aperture(
    *,
    garden_root: str,
    target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Remove one Honeybee Aperture from a model by typed target."""
    target = normalize_honeybee_object_target(target)
    if target.get("object_type") != "aperture":
        raise ValueError("remove_honeybee_aperture requires an aperture target.")

    garden_root = Path(garden_root).expanduser().resolve()
    manifest, model_target = resolve_model_target(garden_root, model_target)
    model = load_honeybee_model(garden_root, model_target)

    aperture = find_object(model, target)
    if not isinstance(aperture, Aperture):
        raise ValueError("Target does not resolve to a Honeybee Aperture.")

    removed_count, paired_removed_identifier = _remove_aperture_in_model(model, aperture)
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="remove_honeybee_aperture",
        target=target,
        object_type="aperture",
        strategy=postprocess_strategy,
    )

    updated_model_target, persisted_path = _save_removed_model(
        garden_root=garden_root,
        manifest=manifest,
        model_target=model_target,
        model=model,
    )
    return _removal_response(
        manifest=manifest,
        updated_model_target=updated_model_target,
        persisted_path=persisted_path,
        operation="remove_honeybee_aperture",
        target=target,
        removed_identifier=aperture.identifier,
        object_label="aperture",
        removed_count=removed_count,
        paired_removed_identifier=paired_removed_identifier,
        postprocess=postprocess,
    )


def remove_honeybee_door(
    *,
    garden_root: str,
    target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Remove one Honeybee Door from a model by typed target."""
    target = normalize_honeybee_object_target(target)
    if target.get("object_type") != "door":
        raise ValueError("remove_honeybee_door requires a door target.")

    garden_root = Path(garden_root).expanduser().resolve()
    manifest, model_target = resolve_model_target(garden_root, model_target)
    model = load_honeybee_model(garden_root, model_target)

    door = find_object(model, target)
    if not isinstance(door, Door):
        raise ValueError("Target does not resolve to a Honeybee Door.")

    removed_count, paired_removed_identifier = _remove_door_in_model(model, door)
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="remove_honeybee_door",
        target=target,
        object_type="door",
        strategy=postprocess_strategy,
    )

    updated_model_target, persisted_path = _save_removed_model(
        garden_root=garden_root,
        manifest=manifest,
        model_target=model_target,
        model=model,
    )
    return _removal_response(
        manifest=manifest,
        updated_model_target=updated_model_target,
        persisted_path=persisted_path,
        operation="remove_honeybee_door",
        target=target,
        removed_identifier=door.identifier,
        object_label="door",
        removed_count=removed_count,
        paired_removed_identifier=paired_removed_identifier,
        postprocess=postprocess,
    )


def remove_honeybee_shade(
    *,
    garden_root: str,
    target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Remove one Honeybee Shade from a model by typed target."""
    target = normalize_honeybee_object_target(target)
    if target.get("object_type") != "shade":
        raise ValueError("remove_honeybee_shade requires a shade target.")

    garden_root = Path(garden_root).expanduser().resolve()
    manifest, model_target = resolve_model_target(garden_root, model_target)
    model = load_honeybee_model(garden_root, model_target)

    shade = find_object(model, target)
    if not isinstance(shade, Shade):
        raise ValueError("Target does not resolve to a Honeybee Shade.")

    _remove_shade_in_model(model, shade)
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="remove_honeybee_shade",
        target=target,
        object_type="shade",
        strategy=postprocess_strategy,
    )

    updated_model_target, persisted_path = _save_removed_model(
        garden_root=garden_root,
        manifest=manifest,
        model_target=model_target,
        model=model,
    )
    return _removal_response(
        manifest=manifest,
        updated_model_target=updated_model_target,
        persisted_path=persisted_path,
        operation="remove_honeybee_shade",
        target=target,
        removed_identifier=shade.identifier,
        object_label="shade",
        postprocess=postprocess,
    )


def remove_honeybee_objects(
    *,
    garden_root: str,
    target: dict[str, Any] | None = None,
    targets: list[dict[str, Any]] | None = None,
    model_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Remove one or more Honeybee Room, Face, Aperture, Door, or Shade targets."""
    if (target is None) == (targets is None):
        raise ValueError("Provide exactly one of target or targets.")

    if target is not None:
        normalized = normalize_honeybee_object_target(target)
        obj_type = normalized.get("object_type")
        dispatch = {
            "room": remove_honeybee_room,
            "face": remove_honeybee_face,
            "aperture": remove_honeybee_aperture,
            "door": remove_honeybee_door,
            "shade": remove_honeybee_shade,
        }
        fn = dispatch.get(str(obj_type))
        if fn is None:
            raise ValueError(
                f"Unsupported Honeybee object_type for removal: {obj_type!r}. "
                "Supported types: room, face, aperture, door, shade."
            )
        return fn(
            garden_root=garden_root,
            target=normalized,
            model_target=model_target,
            postprocess_strategy=postprocess_strategy,
        )

    if not isinstance(targets, list) or not targets:
        raise ValueError("targets must be a non-empty list of Honeybee object targets.")

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(
        garden_root_path,
        model_target,
    )
    expected_model_id = str(resolved_model_target["model_identifier"])

    normalized_targets: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    for index, raw_target in enumerate(targets):
        try:
            norm = normalize_honeybee_object_target(raw_target)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"targets[{index}] must be a Honeybee object typed target."
            ) from exc
        obj_type = str(norm.get("object_type"))
        if obj_type not in _REMOVAL_PRIORITY:
            raise ValueError(
                f"targets[{index}] has unsupported object_type {obj_type!r}. "
                "Supported types: room, face, aperture, door, shade."
            )
        if norm.get("garden_id") != manifest.garden_id:
            raise ValueError(f"targets[{index}] belongs to a different Garden.")
        if norm.get("model_identifier") != expected_model_id:
            raise ValueError(
                f"targets[{index}] belongs to Honeybee model "
                f"{norm.get('model_identifier')!r}, expected {expected_model_id!r}."
            )
        if obj_type == "face" and norm.get("parent", {}).get("room_identifier"):
            raise ValueError(
                f"targets[{index}] is a room-hosted Face; room-hosted faces cannot "
                "be removed because doing so would break the Room closed solid."
            )
        key = (obj_type, str(norm["object_identifier"]))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        normalized_targets.append(norm)

    model = load_honeybee_model(garden_root_path, resolved_model_target)
    expected_classes = {
        "room": Room,
        "face": Face,
        "aperture": Aperture,
        "door": Door,
        "shade": Shade,
    }
    for index, norm in enumerate(normalized_targets):
        found = find_object(model, norm)
        expected_cls = expected_classes[norm["object_type"]]
        if not isinstance(found, expected_cls):
            raise ValueError(
                f"targets[{index}] does not resolve to a Honeybee {expected_cls.__name__}."
            )

    working_model = model.duplicate()
    ordered_targets = sorted(
        normalized_targets,
        key=lambda item: _REMOVAL_PRIORITY[str(item["object_type"])],
    )
    already_removed: set[tuple[str, str]] = set()
    removed_identifiers: list[str] = []
    paired_removed_identifiers: list[str] = []
    removed_types: list[str] = []
    total_removed_count = 0
    adjacency_cleanup = {"faces": 0, "apertures": 0, "doors": 0}

    for norm in ordered_targets:
        obj_type = str(norm["object_type"])
        obj_id = str(norm["object_identifier"])
        if (obj_type, obj_id) in already_removed:
            continue
        obj = find_object(working_model, norm)
        if obj_type == "shade":
            _remove_shade_in_model(working_model, obj)
            total_removed_count += 1
        elif obj_type == "aperture":
            count, paired_id = _remove_aperture_in_model(working_model, obj)
            total_removed_count += count
            if paired_id is not None:
                paired_removed_identifiers.append(paired_id)
                already_removed.add(("aperture", paired_id))
        elif obj_type == "door":
            count, paired_id = _remove_door_in_model(working_model, obj)
            total_removed_count += count
            if paired_id is not None:
                paired_removed_identifiers.append(paired_id)
                already_removed.add(("door", paired_id))
        elif obj_type == "face":
            _remove_face_in_model(working_model, obj)
            total_removed_count += 1
        elif obj_type == "room":
            room_cleanup = _remove_room_in_model(working_model, obj)
            for k in adjacency_cleanup:
                adjacency_cleanup[k] += room_cleanup.get(k, 0)
            total_removed_count += 1
        already_removed.add((obj_type, obj_id))
        removed_identifiers.append(obj_id)
        if obj_type not in removed_types:
            removed_types.append(obj_type)

    working_model, postprocess = apply_honeybee_postprocess(
        model=working_model,
        garden_id=manifest.garden_id,
        model_identifier=expected_model_id,
        operation="remove_honeybee_objects",
        target=normalized_targets[0],
        object_type=removed_types[0] if len(removed_types) == 1 else None,
        object_types=removed_types,
        strategy=postprocess_strategy,
    )
    updated_model_target, persisted_path = _save_removed_model(
        garden_root=garden_root_path,
        manifest=manifest,
        model_target=resolved_model_target,
        model=working_model,
    )

    cleanup_summary = (
        adjacency_cleanup if any(adjacency_cleanup.values()) else {}
    )
    summary_view: dict[str, Any] = {
        "removed_count": total_removed_count,
        "requested_count": len(normalized_targets),
        "removed_identifiers": removed_identifiers,
        "removed_object_types": removed_types,
        "model_target": updated_model_target,
    }
    if len(removed_identifiers) == 1:
        summary_view["removed_identifier"] = removed_identifiers[0]
    if paired_removed_identifiers:
        summary_view["paired_removed_identifiers"] = paired_removed_identifiers
    if cleanup_summary:
        summary_view["adjacency_cleanup"] = cleanup_summary

    receipt = make_persistence_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        model_target=updated_model_target,
        persisted_path=persisted_path,
        change_summary={
            "operation": "remove_honeybee_objects",
            "targets": normalized_targets,
            "removed_identifiers": removed_identifiers,
            "removed_count": total_removed_count,
            "paired_removed_identifiers": paired_removed_identifiers,
            "adjacency_cleanup": cleanup_summary,
        },
    )
    return attach_postprocess_result(
        {
            "model_target": updated_model_target,
            "summary_view": summary_view,
            "persistence_receipt": receipt,
            "report": make_report(
                status="ok",
                message=(
                    f"Removed {total_removed_count} Honeybee object(s) "
                    f"({', '.join(removed_types)})."
                ),
            ),
        },
        postprocess,
    )
