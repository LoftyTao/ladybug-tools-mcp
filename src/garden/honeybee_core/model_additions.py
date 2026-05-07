"""Helpers for adding complete Honeybee objects to a model."""

from __future__ import annotations

from typing import Any

from honeybee.aperture import Aperture
from honeybee.door import Door
from honeybee.face import Face
from honeybee.model import Model
from honeybee.room import Room
from honeybee.shade import Shade

from garden.honeybee_core.geometry import (
    validate_face_sub_faces,
    validate_honeybee_aperture,
    validate_honeybee_door,
    validate_honeybee_face,
    validate_honeybee_room,
    validate_honeybee_shade,
    validate_model_adjacency,
)
from garden.honeybee_core.targets import normalize_honeybee_object_target


def add_objects_to_model(
    model: Model,
    object_dicts: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Add supported Honeybee objects to a model and return a light summary."""
    if not object_dicts:
        return {
            "added_object_count": 0,
            "added_object_types": [],
        }

    added_types: list[str] = []
    for object_dict in object_dicts:
        object_type, obj = _load_addable_object(object_dict)
        _add_object(model, object_type=object_type, obj=obj)
        added_types.append(object_type)

    _validate_model_after_add(model)
    return {
        "added_object_count": len(added_types),
        "added_object_types": sorted(set(added_types)),
    }


def remove_objects_from_model(
    model: Model,
    remove_targets: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Remove supported top-level Honeybee objects from a model and return a light summary."""
    if not remove_targets:
        return {
            "removed_object_count": 0,
            "removed_object_types": [],
        }

    removed_types: list[str] = []
    for target in remove_targets:
        object_type = _remove_target_object(model, target)
        removed_types.append(object_type)

    return {
        "removed_object_count": len(removed_types),
        "removed_object_types": sorted(set(removed_types)),
    }


def _load_addable_object(object_dict: dict[str, Any]) -> tuple[str, Any]:
    if not isinstance(object_dict, dict):
        raise ValueError("add_objects entries must be Honeybee object dictionaries.")

    object_type = str(object_dict.get("type", ""))
    if object_type == "Room":
        room = Room.from_dict(object_dict)
        validate_honeybee_room(room)
        return "room", room
    if object_type == "Face":
        face = Face.from_dict(object_dict)
        validate_honeybee_face(face)
        validate_face_sub_faces(face)
        return "face", face
    if object_type == "Aperture":
        aperture = Aperture.from_dict(object_dict)
        validate_honeybee_aperture(aperture)
        return "aperture", aperture
    if object_type == "Door":
        door = Door.from_dict(object_dict)
        validate_honeybee_door(door)
        return "door", door
    if object_type == "Shade":
        shade = Shade.from_dict(object_dict)
        validate_honeybee_shade(shade)
        return "shade", shade

    raise ValueError(
        "add_objects only supports complete Honeybee Room, Face, Aperture, Door, and Shade dictionaries."
    )


def _add_object(model: Model, *, object_type: str, obj: Any) -> None:
    if object_type == "room":
        model.add_room(obj)
    elif object_type == "face":
        model.add_face(obj)
    elif object_type == "aperture":
        model.add_aperture(obj)
    elif object_type == "door":
        model.add_door(obj)
    elif object_type == "shade":
        model.add_shade(obj)
    else:  # pragma: no cover - guarded by _load_addable_object
        raise ValueError(f"Unsupported Honeybee add object type: {object_type}")


def _validate_model_after_add(model: Model) -> None:
    try:
        model.check_all_duplicate_identifiers(raise_exception=True, detailed=False)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(
            f"Honeybee model must not contain duplicate identifiers after add_objects. {exc}"
        ) from exc

    validate_model_adjacency(model)


def _remove_target_object(model: Model, target: dict[str, Any]) -> str:
    target = normalize_honeybee_object_target(target)

    object_type = str(target.get("object_type", ""))
    object_identifier = str(target.get("object_identifier", ""))
    parent = target.get("parent") or {}
    if not object_identifier:
        raise ValueError("remove_targets entries must include object_identifier.")

    if object_type == "room":
        model.remove_rooms(room_ids=[object_identifier])
        return "room"
    if object_type == "face":
        if parent.get("room_identifier"):
            raise ValueError(
                "edit_honeybee_model remove_targets only supports top-level orphaned faces."
            )
        model.remove_faces(face_ids=[object_identifier])
        return "face"
    if object_type == "aperture":
        if parent:
            raise ValueError(
                "edit_honeybee_model remove_targets only supports top-level orphaned apertures."
            )
        model.remove_apertures(aperture_ids=[object_identifier])
        return "aperture"
    if object_type == "door":
        if parent:
            raise ValueError(
                "edit_honeybee_model remove_targets only supports top-level orphaned doors."
            )
        model.remove_doors(door_ids=[object_identifier])
        return "door"
    if object_type == "shade":
        if parent:
            raise ValueError(
                "edit_honeybee_model remove_targets only supports top-level orphaned shades."
            )
        model.remove_shades(shade_ids=[object_identifier])
        return "shade"

    raise ValueError(
        "remove_targets only supports Honeybee room, face, aperture, door, and shade targets."
    )
