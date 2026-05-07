"""Locate Honeybee objects and parent paths inside a model."""

from __future__ import annotations

from typing import Any

from honeybee.aperture import Aperture
from honeybee.door import Door
from honeybee.face import Face
from honeybee.model import Model
from honeybee.room import Room

from garden.honeybee_core.targets import (
    make_honeybee_object_target,
    normalize_honeybee_object_target,
)


def iter_honeybee_objects(model: Model, garden_id: str, model_identifier: str):
    """Yield Honeybee objects with typed target context."""
    for room in model.rooms:
        yield room, make_honeybee_object_target(
            garden_id=garden_id,
            model_identifier=model_identifier,
            object_type="room",
            object_identifier=room.identifier,
        )
        for face in room.faces:
            face_parent = {"room_identifier": room.identifier}
            yield face, make_honeybee_object_target(
                garden_id=garden_id,
                model_identifier=model_identifier,
                object_type="face",
                object_identifier=face.identifier,
                parent=face_parent,
            )
            yield from _iter_face_children(
                face,
                garden_id,
                model_identifier,
                room_identifier=room.identifier,
            )
        for shade in room.shades:
            yield shade, make_honeybee_object_target(
                garden_id=garden_id,
                model_identifier=model_identifier,
                object_type="shade",
                object_identifier=shade.identifier,
                parent={"room_identifier": room.identifier},
            )

    for face in model.orphaned_faces:
        yield face, make_honeybee_object_target(
            garden_id=garden_id,
            model_identifier=model_identifier,
            object_type="face",
            object_identifier=face.identifier,
        )
        yield from _iter_face_children(face, garden_id, model_identifier)

    for aperture in model.orphaned_apertures:
        yield aperture, make_honeybee_object_target(
            garden_id=garden_id,
            model_identifier=model_identifier,
            object_type="aperture",
            object_identifier=aperture.identifier,
        )
    for door in model.orphaned_doors:
        yield door, make_honeybee_object_target(
            garden_id=garden_id,
            model_identifier=model_identifier,
            object_type="door",
            object_identifier=door.identifier,
        )
    for shade in model.orphaned_shades:
        yield shade, make_honeybee_object_target(
            garden_id=garden_id,
            model_identifier=model_identifier,
            object_type="shade",
            object_identifier=shade.identifier,
        )


def _iter_face_children(
    face: Face,
    garden_id: str,
    model_identifier: str,
    *,
    room_identifier: str | None = None,
):
    face_parent = {"face_identifier": face.identifier}
    if room_identifier:
        face_parent["room_identifier"] = room_identifier
    for aperture in face.apertures:
        yield aperture, make_honeybee_object_target(
            garden_id=garden_id,
            model_identifier=model_identifier,
            object_type="aperture",
            object_identifier=aperture.identifier,
            parent=face_parent,
        )
        for shade in aperture.shades:
            yield shade, make_honeybee_object_target(
                garden_id=garden_id,
                model_identifier=model_identifier,
                object_type="shade",
                object_identifier=shade.identifier,
                parent={**face_parent, "aperture_identifier": aperture.identifier},
            )
    for door in face.doors:
        yield door, make_honeybee_object_target(
            garden_id=garden_id,
            model_identifier=model_identifier,
            object_type="door",
            object_identifier=door.identifier,
            parent=face_parent,
        )
        for shade in door.shades:
            yield shade, make_honeybee_object_target(
                garden_id=garden_id,
                model_identifier=model_identifier,
                object_type="shade",
                object_identifier=shade.identifier,
                parent={**face_parent, "door_identifier": door.identifier},
            )
    for shade in face.shades:
        yield shade, make_honeybee_object_target(
            garden_id=garden_id,
            model_identifier=model_identifier,
            object_type="shade",
            object_identifier=shade.identifier,
            parent=face_parent,
        )


def find_object(model: Model, target: dict[str, Any]) -> Any:
    """Find a Honeybee object by typed target."""
    target = normalize_honeybee_object_target(target)
    for obj, found_target in iter_honeybee_objects(
        model,
        garden_id=str(target.get("garden_id", "")),
        model_identifier=str(target.get("model_identifier", "")),
    ):
        if (
            found_target["object_type"] == target.get("object_type")
            and found_target["object_identifier"] == target.get("object_identifier")
        ):
            return obj
    raise ValueError(
        f"Honeybee {target.get('object_type')} not found: "
        f"{target.get('object_identifier')}"
    )


def ensure_face_host(host: Any) -> Face:
    """Validate a Face host."""
    if not isinstance(host, Face):
        raise ValueError("Host target must identify a Honeybee Face.")
    return host


def ensure_shade_host(host: Any) -> None:
    """Validate whether a host can accept shades."""
    if not isinstance(host, (Room, Face, Aperture, Door)):
        raise ValueError("Shade host must be a Room, Face, Aperture, or Door target.")
