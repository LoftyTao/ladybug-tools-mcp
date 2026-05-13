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

from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report
from garden.honeybee_core.locate import find_object
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target,
    save_honeybee_model,
    with_honeybee_model_write_lock,
)
from garden.honeybee_core.postprocess import (
    apply_honeybee_postprocess,
    attach_postprocess_result,
)
from garden.honeybee_core.targets import normalize_honeybee_object_target


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


@with_honeybee_model_write_lock
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

    adjacency_cleanup = _clear_surface_references_to_room(model, room.identifier)
    model.remove_rooms(room_ids=[room.identifier])
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


@with_honeybee_model_write_lock
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
    model.remove_faces(face_ids=[face.identifier])
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


@with_honeybee_model_write_lock
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


@with_honeybee_model_write_lock
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
            _remove_hosted_subface(adjacent_door.parent, adjacent_door, list_name="_doors")
            paired_removed_identifier = adjacent_door.identifier
            removed_count = 2
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


@with_honeybee_model_write_lock
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

    if shade.parent is None:
        model.remove_shades(shade_ids=[shade.identifier])
    else:
        _remove_hosted_shade(shade.parent, shade)
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
