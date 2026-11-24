"""Honeybee object creation services."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from honeybee.aperture import Aperture
from honeybee.boundarycondition import Outdoors, Surface, boundary_conditions
from honeybee.door import Door
from honeybee.face import Face
from honeybee.facetype import Floor, RoofCeiling
from honeybee.model import Model
from honeybee.room import Room
from honeybee.shade import Shade
from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.pointvector import Point3D

from ladybug_tools_mcp.contracts import make_persistence_receipt, make_report
from garden.manifest import GardenManifest
from garden.honeybee_core.geometry import (
    face3d_from_dict,
    polyface3d_from_dict,
    validate_face_sub_faces,
    validate_honeybee_aperture,
    validate_honeybee_door,
    validate_honeybee_face,
    validate_honeybee_room,
    validate_honeybee_shade,
    validate_model_adjacency,
    vector2d_from_input,
)
from garden.honeybee_core.model_additions import add_objects_to_model
from garden.honeybee_core.locate import (
    ensure_face_host,
    ensure_shade_host,
    find_object,
)
from garden.honeybee_core.model_io import (
    import_honeybee_model_file,
    load_honeybee_model,
    resolve_model_target,
    save_honeybee_model,
)
from garden.honeybee_core.postprocess import (
    apply_honeybee_postprocess,
    attach_postprocess_result,
)
from garden.honeybee_core.relate import (
    _project_subface_to_face,
    _unique_subface_identifier,
)
from garden.honeybee_core.targets import (
    make_honeybee_object_target,
    normalize_honeybee_object_target,
    object_summary,
)


def _garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def _save_receipt(
    *,
    garden_id: str,
    model_target: dict[str, Any],
    persisted_path: str,
    operation: str,
    object_target: dict[str, Any] | None = None,
    change_details: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    status: str = "persisted",
) -> dict[str, Any]:
    return make_persistence_receipt(
        status=status,
        garden_id=garden_id,
        model_target=model_target,
        persisted_path=persisted_path,
        warnings=warnings,
        change_summary={
            "operation": operation,
            "target": object_target or model_target,
            **(change_details or {}),
        },
    )


def _model_object_identifiers(model: Model) -> set[str]:
    identifiers: set[str] = set()
    for collection_name in ("rooms", "faces", "apertures", "doors", "shades"):
        for obj in getattr(model, collection_name, []) or []:
            identifier = getattr(obj, "identifier", None)
            if isinstance(identifier, str):
                identifiers.add(identifier)
    return identifiers


def _ensure_unique_object_identifier(model: Model, identifier: str) -> None:
    if identifier not in _model_object_identifiers(model):
        return
    raise ValueError(
        f"Honeybee object identifier already exists: {identifier}. "
        "Use HB_Search_Model_Objects to reuse the existing target, remove "
        "the existing object first, or choose a new unique identifier."
    )


def _normalize_origin(origin: list[float] | dict[str, Any] | None) -> list[float] | None:
    if origin is None:
        return None
    if isinstance(origin, dict):
        return [
            float(origin.get("x", 0)),
            float(origin.get("y", 0)),
            float(origin.get("z", 0)),
        ]
    return [float(value) for value in origin]


def create_honeybee_model(
    *,
    garden_root: str,
    identifier: str,
    units: str = "Meters",
    tolerance: float | None = None,
    angle_tolerance: float = 1.0,
    save_back: bool = True,
    set_base: bool = True,
    include_body: bool = False,
    add_objects: list[dict[str, Any]] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Create a Honeybee Model and optionally persist it to a Garden."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    model = Model(
        identifier,
        units=units,
        tolerance=tolerance,
        angle_tolerance=angle_tolerance,
    )
    add_summary = add_objects_to_model(model, add_objects)
    postprocess: dict[str, Any] = {}
    receipt: dict[str, Any] | None = None
    if save_back:
        if postprocess_strategy is not None:
            model, postprocess = apply_honeybee_postprocess(
                model=model,
                garden_id=manifest.garden_id,
                model_identifier=str(model.identifier),
                operation="create_honeybee_model",
                object_type="model",
                strategy=postprocess_strategy,
            )
        model_target, persisted_path = save_honeybee_model(
            garden_root_path,
            manifest,
            model,
            set_base=set_base,
        )
        object_dict = model_target
        receipt = _save_receipt(
            garden_id=manifest.garden_id,
            model_target=model_target,
            persisted_path=persisted_path,
            operation="create_honeybee_model",
            change_details=add_summary,
        )
    else:
        model_target = None
        object_dict = model.to_dict() if include_body else None

    response = {
        "object_dict": object_dict,
        "target": model_target,
        "model_target": model_target,
        "summary_view": {
            "model_identifier": identifier,
            "units": units,
            "saved": save_back,
            "base_honeybee_model_changed": bool(save_back and set_base),
            **add_summary,
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=f"Created Honeybee model: {identifier}",
        ),
    }
    return attach_postprocess_result(response, postprocess)


def import_honeybee_model_with_postprocess(
    *,
    garden_root: str,
    file_path: str,
    identifier: str | None = None,
    set_base: bool = True,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Import a Garden-local HBJSON file and optionally run postprocessing."""
    result = import_honeybee_model_file(
        garden_root=garden_root,
        file_path=file_path,
        identifier=identifier,
        set_base=set_base,
    )
    if postprocess_strategy is None:
        return result

    garden_root_path = _garden_root(garden_root)
    manifest, model_target = resolve_model_target(
        garden_root_path,
        result["model_target"],
    )
    if postprocess_strategy == "none":
        model = Model("placeholder")
    else:
        model = load_honeybee_model(garden_root_path, model_target)
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="import_honeybee_model_file",
        target=model_target,
        object_type="model",
        strategy=postprocess_strategy,
    )
    if postprocess_strategy in {
        "auto_relate_existing_geometry",
        "auto_relate_intersect_clone_single",
    }:
        updated_target, persisted_path = save_honeybee_model(
            garden_root_path,
            manifest,
            model,
            name=str(model_target["model_identifier"]),
            set_base=set_base,
            set_default_base=False,
        )
        result["target"] = updated_target
        result["model_target"] = updated_target
        result["persistence_receipt"]["model_target"] = updated_target
        result["persistence_receipt"]["persisted_path"] = persisted_path
    return attach_postprocess_result(result, postprocess)


def _load_target_model(
    garden_root: str,
    model_target: dict[str, Any] | None,
) -> tuple[Path, GardenManifest, dict[str, Any], Model]:
    garden_root_path = _garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_honeybee_model(garden_root_path, resolved_model_target)
    return garden_root_path, manifest, resolved_model_target, model


def _save_changed_model(
    garden_root: Path,
    manifest: GardenManifest,
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


def _resolve_object_target_for_model(
    value: Any,
) -> dict[str, Any]:
    return normalize_honeybee_object_target(value)


def _add_room_in_model(
    model: Model,
    manifest: GardenManifest,
    model_identifier: str,
    *,
    identifier: str,
    faces: list[dict[str, Any]] | None = None,
    room_geometry: dict[str, Any] | None = None,
    x_dim: float | None = None,
    y_dim: float | None = None,
    height: float | None = None,
    origin: list[float] | dict[str, Any] | None = None,
) -> tuple[Room, dict[str, Any]]:
    normalized_origin = _normalize_origin(origin)
    has_faces = faces is not None
    has_room_geometry = room_geometry is not None
    has_box = any(
        value is not None for value in (x_dim, y_dim, height, normalized_origin)
    )
    if sum((has_faces, has_room_geometry, has_box)) != 1:
        raise ValueError(
            "HB_Create_Objects (object_type='room') requires exactly one geometry mode: "
            "faces, room_geometry, or x_dim/y_dim/height."
        )
    if has_box and any(value is None for value in (x_dim, y_dim, height)):
        raise ValueError("Box room creation requires x_dim, y_dim, and height.")

    _ensure_unique_object_identifier(model, identifier)
    if faces is not None:
        room = Room(identifier, [Face.from_dict(face) for face in faces])
    elif room_geometry is not None:
        room = Room.from_polyface3d(identifier, polyface3d_from_dict(room_geometry))
    else:
        origin_point = Point3D(*(normalized_origin or [0, 0, 0]))
        room = Room.from_box(
            identifier,
            width=float(x_dim),
            depth=float(y_dim),
            height=float(height),
            origin=origin_point,
        )
    validate_honeybee_room(room)
    model.add_room(room)
    target = make_honeybee_object_target(
        garden_id=manifest.garden_id,
        model_identifier=model_identifier,
        object_type="room",
        object_identifier=identifier,
    )
    return room, target


def _add_face_in_model(
    model: Model,
    manifest: GardenManifest,
    model_identifier: str,
    *,
    identifier: str,
    geometry: dict[str, Any],
) -> tuple[Face, dict[str, Any]]:
    _ensure_unique_object_identifier(model, identifier)
    face = Face(identifier, face3d_from_dict(geometry))
    validate_honeybee_face(face)
    model.add_face(face)
    target = make_honeybee_object_target(
        garden_id=manifest.garden_id,
        model_identifier=model_identifier,
        object_type="face",
        object_identifier=identifier,
    )
    return face, target


def _add_door_in_model(
    model: Model,
    manifest: GardenManifest,
    model_identifier: str,
    *,
    identifier: str,
    host_target: dict[str, Any],
    geometry: dict[str, Any] | None = None,
    is_glass: bool = False,
    door_width: float | None = None,
    door_height: float = 2.1,
    sill_height: float = 0.05,
    placement: str = "auto",
) -> tuple[Door, dict[str, Any], dict[str, Any] | None, list[Door], dict[str, Any]]:
    _ensure_unique_object_identifier(model, identifier)
    resolved_host_target = _resolve_object_target_for_model(host_target)
    host = ensure_face_host(find_object(model, resolved_host_target))
    if geometry is None:
        geometry = _rectangular_door_geometry_from_host(
            host,
            width=door_width or 0.9,
            height=door_height,
            sill_height=sill_height,
            placement=placement,
            tolerance=model.tolerance,
        )
    door = Door(identifier, face3d_from_dict(geometry), is_glass=is_glass)
    validate_honeybee_door(door)
    target = make_honeybee_object_target(
        garden_id=manifest.garden_id,
        model_identifier=model_identifier,
        object_type="door",
        object_identifier=identifier,
        parent={**resolved_host_target.get("parent", {}), "face_identifier": host.identifier},
    )
    created_doors = [door]
    adjacent_target: dict[str, Any] | None = None
    adjacent_face = _adjacent_surface_face(model, host)
    if adjacent_face is None:
        host.add_door(door)
        validate_face_sub_faces(host)
    else:
        adjacent_door = door.duplicate()
        adjacent_door.identifier = _unique_subface_identifier(
            identifier,
            {existing.identifier for face in model.faces for existing in face.doors},
        )
        host.boundary_condition = boundary_conditions.outdoors
        adjacent_face.boundary_condition = boundary_conditions.outdoors
        host.add_door(door)
        if not _project_subface_to_face(
            adjacent_door,
            host,
            adjacent_face,
            tolerance=model.tolerance,
            angle_tolerance=model.angle_tolerance,
        ):
            raise ValueError(
                "Could not project the interior door geometry onto the adjacent "
                f"face: {adjacent_face.identifier}."
            )
        validate_face_sub_faces(host)
        validate_face_sub_faces(adjacent_face)
        host.set_adjacency(adjacent_face, tolerance=model.tolerance)
        created_doors.append(adjacent_door)
        adjacent_target = make_honeybee_object_target(
            garden_id=manifest.garden_id,
            model_identifier=model_identifier,
            object_type="door",
            object_identifier=adjacent_door.identifier,
            parent={
                "room_identifier": adjacent_face.parent.identifier,
                "face_identifier": adjacent_face.identifier,
            },
        )
    return door, target, adjacent_target, created_doors, resolved_host_target


def _add_aperture_geometry_in_model(
    model: Model,
    manifest: GardenManifest,
    model_identifier: str,
    *,
    identifier: str,
    geometry: dict[str, Any],
    host_target: dict[str, Any],
    is_operable: bool = False,
) -> tuple[Aperture, dict[str, Any], dict[str, Any]]:
    _ensure_unique_object_identifier(model, identifier)
    resolved_host_target = _resolve_object_target_for_model(host_target)
    host = ensure_face_host(find_object(model, resolved_host_target))
    aperture = Aperture(
        identifier,
        face3d_from_dict(geometry),
        is_operable=is_operable,
    )
    validate_honeybee_aperture(aperture)
    host.add_aperture(aperture)
    validate_face_sub_faces(host)
    target = make_honeybee_object_target(
        garden_id=manifest.garden_id,
        model_identifier=model_identifier,
        object_type="aperture",
        object_identifier=identifier,
        parent={**resolved_host_target.get("parent", {}), "face_identifier": host.identifier},
    )
    return aperture, target, resolved_host_target


def _add_shade_geometry_in_model(
    model: Model,
    manifest: GardenManifest,
    model_identifier: str,
    *,
    identifier: str,
    geometry: dict[str, Any],
    host_target: dict[str, Any] | None = None,
    attach_side: str = "outdoor",
    is_detached: bool = False,
) -> tuple[Shade, dict[str, Any]]:
    if host_target is not None:
        host_target = normalize_honeybee_object_target(host_target)
    _ensure_unique_object_identifier(model, identifier)
    shade = Shade(identifier, face3d_from_dict(geometry), is_detached=is_detached)
    validate_honeybee_shade(shade)
    parent: dict[str, str] = {}
    if host_target is None:
        model.add_shade(shade)
    else:
        host = find_object(model, host_target)
        ensure_shade_host(host)
        parent = dict(host_target.get("parent", {}))
        parent[f"{host_target['object_type']}_identifier"] = host.identifier
        normalized_attach_side = attach_side.strip().lower()
        if normalized_attach_side in {
            "top",
            "front",
            "back",
            "exterior",
            "external",
            "outside",
        }:
            normalized_attach_side = "outdoor"
        elif normalized_attach_side in {"interior", "inside"}:
            normalized_attach_side = "indoor"
        if normalized_attach_side == "indoor":
            host.add_indoor_shade(shade)
        elif normalized_attach_side == "outdoor":
            host.add_outdoor_shade(shade)
        else:
            raise ValueError("attach_side must be 'indoor' or 'outdoor'.")

    target = make_honeybee_object_target(
        garden_id=manifest.garden_id,
        model_identifier=model_identifier,
        object_type="shade",
        object_identifier=identifier,
        parent=parent,
    )
    return shade, target


def _add_shades_by_parameters_in_model(
    model: Model,
    manifest: GardenManifest,
    model_identifier: str,
    *,
    host_target: dict[str, Any],
    generation_mode: str,
    parameters: dict[str, Any],
    used_identifiers: set[str] | None = None,
) -> tuple[list[Shade], list[dict[str, Any]], dict[str, Any], Any]:
    resolved_host_target = _resolve_object_target_for_model(host_target)
    host = find_object(model, resolved_host_target)
    if not isinstance(host, (Face, Aperture)):
        raise ValueError("host_target must identify a Honeybee Face or Aperture.")
    if generation_mode == "extruded_border" and not isinstance(host, Aperture):
        raise ValueError("extruded_border requires an aperture host target.")
    if generation_mode not in {
        "louver_by_count",
        "louver_by_distance_between",
        "extruded_border",
    }:
        raise ValueError(
            "generation_mode must be one of 'louver_by_count', "
            "'louver_by_distance_between', or 'extruded_border'."
        )
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be a dictionary.")
    parameters = dict(parameters)
    depth = parameters.get("depth")
    if depth is None or depth <= 0:
        raise ValueError("parameters.depth must be a positive number.")
    indoor = bool(parameters.get("indoor", False))
    base_name = parameters.get("base_name")

    if generation_mode == "extruded_border":
        created_shades = host.extruded_border(
            depth,
            indoor=indoor,
            base_name=base_name,
        )
    else:
        offset = parameters.get("offset", 0)
        angle = parameters.get("angle", 0)
        contour_vector = (
            vector2d_from_input(parameters["contour_vector"])
            if parameters.get("contour_vector") is not None
            else None
        )
        contour_kwargs = (
            {"contour_vector": contour_vector} if contour_vector is not None else {}
        )
        common_kwargs = {
            "offset": offset,
            "angle": angle,
            **contour_kwargs,
            "flip_start_side": bool(parameters.get("flip_start_side", False)),
            "indoor": indoor,
            "tolerance": parameters.get("tolerance", 0.01),
            "base_name": base_name,
        }
        if generation_mode == "louver_by_count":
            louver_count = parameters.get("louver_count")
            if louver_count is None or louver_count <= 0:
                raise ValueError(
                    "parameters.louver_count must be a positive integer for "
                    "louver_by_count."
                )
            created_shades = host.louvers_by_count(
                int(louver_count),
                depth,
                **common_kwargs,
            )
        else:
            distance = parameters.get("distance")
            if distance is None or distance <= 0:
                raise ValueError(
                    "parameters.distance must be a positive number for "
                    "louver_by_distance_between."
                )
            created_shades = host.louvers_by_distance_between(
                distance,
                depth,
                max_count=parameters.get("max_count"),
                **common_kwargs,
            )

    if not created_shades:
        raise ValueError(
            "No Honeybee shades were created from the provided parameters."
        )
    for shade in created_shades:
        validate_honeybee_shade(shade)
    if base_name:
        existing_ids = set(used_identifiers) if used_identifiers is not None else {
            shade.identifier
            for shade in getattr(host, "shades", [])
            if shade not in created_shades
        }
        for index, shade in enumerate(created_shades, start=1):
            candidate = (
                base_name
                if len(created_shades) == 1 and base_name not in existing_ids
                else f"{base_name}_{index}"
            )
            while candidate in existing_ids:
                index += 1
                candidate = f"{base_name}_{index}"
            shade.identifier = candidate
            existing_ids.add(candidate)
        if used_identifiers is not None:
            used_identifiers.update(existing_ids)
    elif used_identifiers is not None:
        used_identifiers.update(shade.identifier for shade in created_shades)

    parent = dict(resolved_host_target.get("parent", {}))
    parent[f"{resolved_host_target['object_type']}_identifier"] = host.identifier
    targets = [
        make_honeybee_object_target(
            garden_id=manifest.garden_id,
            model_identifier=model_identifier,
            object_type="shade",
            object_identifier=shade.identifier,
            parent=parent,
        )
        for shade in created_shades
    ]
    return created_shades, targets, resolved_host_target, host


def create_honeybee_room(
    *,
    garden_root: str,
    identifier: str,
    faces: list[dict[str, Any]] | None = None,
    room_geometry: dict[str, Any] | None = None,
    x_dim: float | None = None,
    y_dim: float | None = None,
    height: float | None = None,
    origin: list[float] | dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Create a Honeybee Room from Face dictionaries or a Polyface3D envelope."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    model_identifier = str(resolved_model_target["model_identifier"])
    room, target = _add_room_in_model(
        model,
        manifest,
        model_identifier,
        identifier=identifier,
        faces=faces,
        room_geometry=room_geometry,
        x_dim=x_dim,
        y_dim=y_dim,
        height=height,
        origin=origin,
    )
    validate_model_adjacency(model)
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=model_identifier,
        operation="create_honeybee_room",
        target=target,
        object_type="room",
        strategy=postprocess_strategy,
    )
    updated_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    return _created_object_response(
        object_dict=room.to_dict(),
        target=target,
        garden_id=manifest.garden_id,
        model_target=updated_target,
        persisted_path=persisted_path,
        operation="create_honeybee_room",
        message=f"Created Honeybee room: {identifier}",
        postprocess=postprocess,
    )


def create_honeybee_face(
    *,
    garden_root: str,
    identifier: str,
    geometry: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Create an orphaned Honeybee Face in a model."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    model_identifier = str(resolved_model_target["model_identifier"])
    face, target = _add_face_in_model(
        model,
        manifest,
        model_identifier,
        identifier=identifier,
        geometry=geometry,
    )
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=model_identifier,
        operation="create_honeybee_face",
        target=target,
        object_type="face",
        strategy=postprocess_strategy,
    )
    updated_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    return _created_object_response(
        object_dict=face.to_dict(),
        target=target,
        garden_id=manifest.garden_id,
        model_target=updated_target,
        persisted_path=persisted_path,
        operation="create_honeybee_face",
        message=f"Created Honeybee face: {identifier}",
        postprocess=postprocess,
    )


def create_honeybee_objects_batch(
    *,
    garden_root: str,
    object_type: str,
    items: list[dict[str, Any]],
    model_target: dict[str, Any] | None = None,
    default_host_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Create multiple Honeybee Rooms, Faces, or Doors in one model save."""
    normalized_type = str(object_type or "").strip().lower()
    if normalized_type not in {"room", "face", "door"}:
        raise ValueError("object_type must be one of room, face, or door.")
    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty list of object specification dicts.")

    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    working_model = model.duplicate()
    model_identifier = str(resolved_model_target["model_identifier"])

    created_targets: list[dict[str, Any]] = []
    created_identifiers: list[str] = []
    object_summaries: list[dict[str, Any]] = []

    for index, raw_item in enumerate(items):
        if not isinstance(raw_item, dict):
            raise ValueError(f"items[{index}] must be a dictionary.")
        item_identifier = raw_item.get("identifier")
        if not isinstance(item_identifier, str) or not item_identifier.strip():
            raise ValueError(f"items[{index}].identifier is required.")
        try:
            if normalized_type == "room":
                room, target = _add_room_in_model(
                    working_model,
                    manifest,
                    model_identifier,
                    identifier=item_identifier,
                    faces=raw_item.get("faces"),
                    room_geometry=raw_item.get("room_geometry"),
                    x_dim=raw_item.get("x_dim"),
                    y_dim=raw_item.get("y_dim"),
                    height=raw_item.get("height"),
                    origin=raw_item.get("origin"),
                )
                created_targets.append(target)
                created_identifiers.append(room.identifier)
                object_summaries.append(object_summary(target, room.to_dict()))
            elif normalized_type == "face":
                geometry = raw_item.get("geometry")
                if geometry is None:
                    raise ValueError("geometry is required for face creation.")
                face, target = _add_face_in_model(
                    working_model,
                    manifest,
                    model_identifier,
                    identifier=item_identifier,
                    geometry=geometry,
                )
                created_targets.append(target)
                created_identifiers.append(face.identifier)
                object_summaries.append(object_summary(target, face.to_dict()))
            else:
                item_host = raw_item.get("host_target", default_host_target)
                if item_host is None:
                    raise ValueError("host_target is required for door creation.")
                door, target, adjacent_target, created_doors, _ = _add_door_in_model(
                    working_model,
                    manifest,
                    model_identifier,
                    identifier=item_identifier,
                    host_target=item_host,
                    geometry=raw_item.get("geometry"),
                    is_glass=bool(raw_item.get("is_glass", False)),
                    door_width=raw_item.get("door_width"),
                    door_height=float(raw_item.get("door_height", 2.1)),
                    sill_height=float(raw_item.get("sill_height", 0.05)),
                    placement=str(raw_item.get("placement", "auto")),
                )
                created_targets.append(target)
                created_identifiers.append(door.identifier)
                object_summaries.append(object_summary(target, door.to_dict()))
                if adjacent_target is not None and len(created_doors) > 1:
                    created_targets.append(adjacent_target)
                    created_identifiers.append(created_doors[1].identifier)
                    object_summaries.append(
                        object_summary(adjacent_target, created_doors[1].to_dict())
                    )
        except Exception as exc:
            raise ValueError(f"items[{index}] ({item_identifier}): {exc}") from exc

    if normalized_type in {"room", "door"}:
        validate_model_adjacency(working_model)

    working_model, postprocess = apply_honeybee_postprocess(
        model=working_model,
        garden_id=manifest.garden_id,
        model_identifier=model_identifier,
        operation="create_honeybee_objects",
        target=created_targets[0],
        object_type=normalized_type,
        object_types=[normalized_type],
        strategy=postprocess_strategy,
    )
    updated_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        working_model,
    )
    response: dict[str, Any] = {
        "target": created_targets[0],
        "object_target": created_targets[0],
        f"{normalized_type}_target": created_targets[0],
        "targets": created_targets,
        "model_target": updated_target,
        "summary_view": {
            "object_type": normalized_type,
            "created_count": len(created_targets),
            "created_identifiers": created_identifiers,
            "objects": object_summaries,
        },
        "persistence_receipt": _save_receipt(
            garden_id=manifest.garden_id,
            model_target=updated_target,
            persisted_path=persisted_path,
            operation="create_honeybee_objects",
            object_target=created_targets[0],
            change_details={
                "object_type": normalized_type,
                "created_targets": created_targets,
                "created_count": len(created_targets),
            },
        ),
        "report": make_report(
            status="ok",
            message=(
                f"Created {len(created_targets)} Honeybee {normalized_type}(s)."
            ),
        ),
    }
    return attach_postprocess_result(response, postprocess)


def create_honeybee_aperture(
    *,
    garden_root: str,
    identifier: str,
    geometry: dict[str, Any],
    host_target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    is_operable: bool = False,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Create a Honeybee Aperture on a host Face target."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    model_identifier = str(resolved_model_target["model_identifier"])
    aperture, target, _ = _add_aperture_geometry_in_model(
        model,
        manifest,
        model_identifier,
        identifier=identifier,
        geometry=geometry,
        host_target=host_target,
        is_operable=is_operable,
    )
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=model_identifier,
        operation="create_honeybee_aperture",
        target=target,
        object_type="aperture",
        strategy=postprocess_strategy,
    )
    updated_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    return _created_object_response(
        object_dict=aperture.to_dict(),
        target=target,
        garden_id=manifest.garden_id,
        model_target=updated_target,
        persisted_path=persisted_path,
        operation="create_honeybee_aperture",
        message=f"Created Honeybee aperture: {identifier}",
        postprocess=postprocess,
    )


def _generate_parametric_apertures_on_host(
    host: Face,
    *,
    generation_mode: str,
    ratio: float | None,
    aperture_width: float | None,
    aperture_height: float | None,
    sill_height: float,
    aperture_identifier: str | None,
    identifier_prefix: str | None,
    tolerance: float,
    rect_split: bool,
    skylight_mode: bool,
    used_model_ids: set[str],
) -> tuple[list[Aperture], list[Aperture], bool]:
    """Generate or reuse parametric apertures on one Face; returns (created, existing, reused)."""
    before_ids = {aperture.identifier for aperture in host.apertures}
    reuse_existing = False

    if generation_mode == "by_ratio":
        if ratio is None:
            raise ValueError("ratio is required when generation_mode is 'by_ratio'.")
        if not 0 < ratio < 1:
            raise ValueError("ratio must be greater than 0 and less than 1.")
        if skylight_mode:
            if tolerance <= 0:
                raise ValueError("tolerance must be greater than 0.")
            if not isinstance(host.type, (RoofCeiling, Floor)):
                raise ValueError(
                    "host_target must identify a Honeybee Face of type RoofCeiling or Floor. "
                    f"Got {host.type}."
                )
            if not isinstance(host.boundary_condition, Outdoors):
                raise ValueError(
                    "Skylights require a RoofCeiling or Floor Face with an Outdoors "
                    "boundary condition; the selected Face is not eligible."
                )
            existing_apertures = list(host.apertures)
            existing_doors = list(host.doors)
            if existing_doors:
                raise ValueError(
                    "Cannot create skylights on a Face with existing Door sub-faces; "
                    "remove or resolve the doors first."
                )
            if existing_apertures:
                validate_face_sub_faces(host)
                if abs(float(host.aperture_ratio) - ratio) > tolerance:
                    raise ValueError(
                        "Existing Apertures conflict with ratio; resolve them explicitly "
                        "before requesting a different aperture ratio."
                    )
                reuse_existing = True
        if not reuse_existing:
            host.apertures_by_ratio(
                ratio,
                tolerance=tolerance,
                rect_split=rect_split,
            )
    elif generation_mode == "by_width_height":
        if aperture_width is None:
            raise ValueError(
                "aperture_width is required when generation_mode is 'by_width_height'."
            )
        if aperture_height is None:
            raise ValueError(
                "aperture_height is required when generation_mode is 'by_width_height'."
            )
        if aperture_width <= 0 or aperture_height <= 0:
            raise ValueError("aperture_width and aperture_height must be positive.")
        if sill_height < 0:
            raise ValueError("sill_height must be greater than or equal to 0.")
        host.aperture_by_width_height(
            aperture_width,
            aperture_height,
            sill_height=sill_height,
            aperture_identifier=aperture_identifier,
        )
    else:
        raise ValueError(
            "generation_mode must be one of 'by_ratio' or 'by_width_height'."
        )

    validate_face_sub_faces(host)
    created_apertures = [
        aperture for aperture in host.apertures if aperture.identifier not in before_ids
    ]
    if not created_apertures:
        existing_apertures = list(host.apertures)
        if not existing_apertures:
            raise ValueError(
                "No Honeybee apertures were created from the provided parameters."
            )
        return [], existing_apertures, reuse_existing

    if identifier_prefix:
        for index, aperture in enumerate(created_apertures, start=1):
            candidate = (
                identifier_prefix
                if len(created_apertures) == 1 and identifier_prefix not in used_model_ids
                else f"{identifier_prefix}_{index}"
            )
            while candidate in used_model_ids:
                index += 1
                candidate = f"{identifier_prefix}_{index}"
            aperture.identifier = candidate
            used_model_ids.add(candidate)
    else:
        for aperture in created_apertures:
            used_model_ids.add(aperture.identifier)

    return created_apertures, [], reuse_existing


def create_honeybee_apertures_by_parameters(
    *,
    garden_root: str,
    host_target: dict[str, Any],
    generation_mode: str,
    model_target: dict[str, Any] | None = None,
    ratio: float | None = None,
    aperture_width: float | None = None,
    aperture_height: float | None = None,
    sill_height: float = 1.0,
    aperture_identifier: str | None = None,
    identifier_prefix: str | None = None,
    tolerance: float = 0.01,
    rect_split: bool = True,
    postprocess_strategy: str | None = None,
    _skylight_mode: bool = False,
) -> dict[str, Any]:
    """Create Honeybee Apertures on a host Face with SDK parameter methods."""
    operation = (
        "create_honeybee_skylights_by_ratio"
        if _skylight_mode
        else "create_honeybee_apertures_by_parameters"
    )
    object_label = "skylight" if _skylight_mode else "aperture"
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    model_identifier = str(resolved_model_target["model_identifier"])
    resolved_host_target = _resolve_object_target_for_model(host_target)
    host = ensure_face_host(find_object(model, resolved_host_target))
    used_model_ids = _model_object_identifiers(model)

    created_apertures, existing_apertures, reuse_existing = (
        _generate_parametric_apertures_on_host(
            host,
            generation_mode=generation_mode,
            ratio=ratio,
            aperture_width=aperture_width,
            aperture_height=aperture_height,
            sill_height=sill_height,
            aperture_identifier=aperture_identifier,
            identifier_prefix=identifier_prefix,
            tolerance=tolerance,
            rect_split=rect_split,
            skylight_mode=_skylight_mode,
            used_model_ids=used_model_ids,
        )
    )

    parent = {**resolved_host_target.get("parent", {}), "face_identifier": host.identifier}
    if not created_apertures:
        targets = [
            make_honeybee_object_target(
                garden_id=manifest.garden_id,
                model_identifier=model_identifier,
                object_type="aperture",
                object_identifier=aperture.identifier,
                parent=parent,
            )
            for aperture in existing_apertures
        ]
        object_summaries = [
            object_summary(target, aperture.to_dict())
            for target, aperture in zip(targets, existing_apertures, strict=True)
        ]
        warning = (
            f"No new Honeybee {object_label}s were created because the host Face "
            "already has apertures. Returning existing aperture targets."
        )
        response = {
            "target": targets[0],
            "aperture_target": targets[0],
            "targets": targets,
            "summary_view": {
                "host_target": resolved_host_target,
                "generation_mode": generation_mode,
                "created_count": 0,
                "existing_count": len(existing_apertures),
                "created_identifiers": [],
                "existing_identifiers": [
                    aperture.identifier for aperture in existing_apertures
                ],
                "objects": object_summaries,
            },
            "persistence_receipt": _save_receipt(
                garden_id=manifest.garden_id,
                model_target=resolved_model_target,
                persisted_path=str(resolved_model_target.get("path", "")),
                operation=operation,
                object_target=resolved_host_target,
                change_details={
                    "created_targets": [],
                    "existing_targets": targets,
                    "generation_mode": generation_mode,
                },
                warnings=[warning],
                status="no_change" if reuse_existing else "persisted",
            ),
            "report": make_report(
                status="ok",
                message=f"Existing Honeybee {object_label}s returned.",
                warnings=[warning],
            ),
        }
        if reuse_existing:
            response["model_target"] = resolved_model_target
            response["runtime_status"] = "no_change"
        return response

    targets = [
        make_honeybee_object_target(
            garden_id=manifest.garden_id,
            model_identifier=model_identifier,
            object_type="aperture",
            object_identifier=aperture.identifier,
            parent=parent,
        )
        for aperture in created_apertures
    ]
    object_summaries = [
        object_summary(target, aperture.to_dict())
        for target, aperture in zip(targets, created_apertures, strict=True)
    ]
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=model_identifier,
        operation=operation,
        target=resolved_host_target,
        object_type="aperture",
        strategy=postprocess_strategy,
    )
    updated_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    return attach_postprocess_result(
        {
            "target": targets[0],
            "aperture_target": targets[0],
            "targets": targets,
            "summary_view": {
                "host_target": resolved_host_target,
                "generation_mode": generation_mode,
                "created_count": len(created_apertures),
                "created_identifiers": [
                    aperture.identifier for aperture in created_apertures
                ],
                "aperture_ratio": host.aperture_ratio,
                "objects": object_summaries,
            },
            "persistence_receipt": _save_receipt(
                garden_id=manifest.garden_id,
                model_target=updated_target,
                persisted_path=persisted_path,
                operation=operation,
                object_target=resolved_host_target,
                change_details={
                    "created_targets": targets,
                    "generation_mode": generation_mode,
                },
            ),
            "report": make_report(
                status="ok",
                message=(
                    f"Created {len(created_apertures)} Honeybee {object_label}(s) on face: "
                    f"{host.identifier}"
                ),
            ),
        },
        postprocess,
    )


def create_honeybee_skylights_by_ratio(
    *,
    garden_root: str,
    host_target: dict[str, Any],
    ratio: float,
    model_target: dict[str, Any] | None = None,
    tolerance: float = 0.01,
    identifier_prefix: str | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Create or reuse ratio-based skylights on a RoofCeiling or Floor Face."""
    return create_honeybee_apertures_by_parameters(
        garden_root=garden_root,
        host_target=host_target,
        generation_mode="by_ratio",
        ratio=ratio,
        model_target=model_target,
        identifier_prefix=identifier_prefix,
        tolerance=tolerance,
        postprocess_strategy=postprocess_strategy,
        _skylight_mode=True,
    )


def _guide_surfaces_on_host(
    host: Face,
    *,
    guide_surfaces: list[dict[str, Any]],
    angle_tolerance: float,
    tolerance: float,
    identifier_prefix: str | None,
    manifest: GardenManifest,
    model_identifier: str,
    parent: dict[str, Any],
    used_model_ids: set[str],
    allow_disambiguate: bool,
) -> tuple[list[Aperture], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    angle_tolerance_radians = math.radians(angle_tolerance)
    known_subfaces = [*host.apertures, *host.doors]
    prefix = (identifier_prefix or f"{host.identifier}_GuideAperture").strip()
    if not prefix:
        raise ValueError("identifier_prefix must not be empty.")

    created: list[Aperture] = []
    created_targets: list[dict[str, Any]] = []
    reused_targets: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for index, guide_surface in enumerate(guide_surfaces):
        try:
            guide_geometry = face3d_from_dict(guide_surface)
            guide_aperture = Aperture(f"{prefix}_{index + 1}", guide_geometry)
            validate_honeybee_aperture(guide_aperture)
        except Exception as exc:
            skipped.append(
                {
                    "guide_surface_index": index,
                    "host_identifier": host.identifier,
                    "reason": "invalid_geometry",
                    "message": f"Could not read guide surface: {exc}",
                }
            )
            continue

        if not host.geometry.plane.is_coplanar_tolerance(
            guide_geometry.plane,
            tolerance,
            angle_tolerance_radians,
        ):
            normal_angle = guide_geometry.normal.angle(host.geometry.normal)
            parallel_angle = min(normal_angle, math.pi - normal_angle)
            reason = (
                "non_coplanar"
                if parallel_angle > angle_tolerance_radians
                else "outside_tolerance"
            )
            skipped.append(
                {
                    "guide_surface_index": index,
                    "host_identifier": host.identifier,
                    "reason": reason,
                    "message": (
                        "Guide surface is not coplanar with the host Face within the "
                        f"{tolerance} geometry tolerance."
                    ),
                }
            )
            continue

        try:
            test_host = host.duplicate()
            test_aperture = Aperture("_guide_surface_test", guide_geometry)
            before_count = len(test_host.apertures)
            test_host.project_and_add_sub_face(
                test_aperture,
                angle_tolerance=angle_tolerance,
            )
        except Exception as exc:
            skipped.append(
                {
                    "guide_surface_index": index,
                    "host_identifier": host.identifier,
                    "reason": "projection_failed",
                    "message": f"Honeybee SDK could not project the guide surface: {exc}.",
                }
            )
            continue

        if len(test_host.apertures) != before_count + 1:
            skipped.append(
                {
                    "guide_surface_index": index,
                    "host_identifier": host.identifier,
                    "reason": "projection_failed",
                    "message": "Honeybee SDK could not project the guide surface onto the host Face.",
                }
            )
            continue

        projected_geometry = test_aperture.geometry
        if not test_host.geometry.is_sub_face(
            projected_geometry,
            tolerance,
            angle_tolerance_radians,
        ):
            skipped.append(
                {
                    "guide_surface_index": index,
                    "host_identifier": host.identifier,
                    "reason": "outside_host_face",
                    "message": "Projected guide surface is not fully inside the host Face.",
                }
            )
            continue

        equivalent = next(
            (
                subface
                for subface in known_subfaces
                if isinstance(subface, Aperture)
                and projected_geometry.is_geometrically_equivalent(
                    subface.geometry,
                    tolerance,
                )
            ),
            None,
        )
        if equivalent is not None:
            reused_targets.append(
                make_honeybee_object_target(
                    garden_id=manifest.garden_id,
                    model_identifier=model_identifier,
                    object_type="aperture",
                    object_identifier=equivalent.identifier,
                    parent=parent,
                )
            )
            continue

        if any(
            projected_geometry.is_overlapping(subface.geometry, tolerance)
            for subface in known_subfaces
        ):
            skipped.append(
                {
                    "guide_surface_index": index,
                    "host_identifier": host.identifier,
                    "reason": "overlaps_existing_subface",
                    "message": (
                        "Projected guide surface overlaps an existing Aperture, Door, "
                        "or another guide surface."
                    ),
                }
            )
            continue

        base = prefix if len(guide_surfaces) == 1 else f"{prefix}_{index + 1}"
        identifier = base[:100]
        if identifier in used_model_ids and allow_disambiguate:
            counter = 1
            while f"{prefix}_{counter}"[:100] in used_model_ids:
                counter += 1
            identifier = f"{prefix}_{counter}"[:100]
        if identifier in used_model_ids:
            skipped.append(
                {
                    "guide_surface_index": index,
                    "host_identifier": host.identifier,
                    "reason": "duplicate_identifier",
                    "message": f"Honeybee object identifier already exists: {identifier}.",
                }
            )
            continue

        try:
            validate_face_sub_faces(test_host)
        except Exception as exc:
            skipped.append(
                {
                    "guide_surface_index": index,
                    "host_identifier": host.identifier,
                    "reason": "invalid_subface",
                    "message": f"Projected guide surface failed Honeybee validation: {exc}",
                }
            )
            continue

        aperture = Aperture(identifier, guide_geometry)
        host.project_and_add_sub_face(
            aperture,
            angle_tolerance=angle_tolerance,
        )
        validate_honeybee_aperture(aperture)
        validate_face_sub_faces(host)
        created.append(aperture)
        known_subfaces.append(aperture)
        used_model_ids.add(identifier)
        created_targets.append(
            make_honeybee_object_target(
                garden_id=manifest.garden_id,
                model_identifier=model_identifier,
                object_type="aperture",
                object_identifier=identifier,
                parent=parent,
            )
        )

    return created, created_targets, reused_targets, skipped


def create_honeybee_apertures_batch(
    *,
    garden_root: str,
    mode: str,
    host_target: dict[str, Any] | None = None,
    host_targets: list[dict[str, Any]] | None = None,
    items: list[dict[str, Any]] | None = None,
    model_target: dict[str, Any] | None = None,
    generation_mode: str = "by_ratio",
    ratio: float | None = None,
    aperture_width: float | None = None,
    aperture_height: float | None = None,
    sill_height: float = 1.0,
    aperture_identifier: str | None = None,
    identifier_prefix: str | None = None,
    tolerance: float = 0.01,
    rect_split: bool = True,
    guide_surfaces: list[dict[str, Any]] | None = None,
    is_operable: bool = False,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Create Honeybee Apertures across multiple host faces or item specs in one save."""
    if mode not in {"geometry", "parameters", "guide_surface", "skylight_ratio"}:
        raise ValueError(
            "mode must be one of 'geometry', 'parameters', 'guide_surface', or 'skylight_ratio'."
        )
    if host_targets is not None and items is not None:
        raise ValueError("Provide either host_targets or items, not both.")
    if host_targets is None and items is None:
        raise ValueError("Batch aperture creation requires host_targets or items.")

    specs: list[dict[str, Any]] = []
    if host_targets is not None:
        if not isinstance(host_targets, list) or not host_targets:
            raise ValueError("host_targets must be a non-empty list.")
        for ht in host_targets:
            specs.append({"host_target": ht})
    else:
        if not isinstance(items, list) or not items:
            raise ValueError("items must be a non-empty list.")
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError(f"items[{index}] must be a dictionary.")
            spec = dict(item)
            if "host_target" not in spec and host_target is not None:
                spec["host_target"] = host_target
            specs.append(spec)

    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    working_model = model.duplicate()
    model_identifier = str(resolved_model_target["model_identifier"])
    used_model_ids = _model_object_identifiers(working_model)

    created_apertures: list[Aperture] = []
    created_targets: list[dict[str, Any]] = []
    reused_targets: list[dict[str, Any]] = []
    skipped_all: list[dict[str, Any]] = []
    resolved_hosts: list[dict[str, Any]] = []
    object_summaries: list[dict[str, Any]] = []

    for index, spec in enumerate(specs):
        raw_host = spec.get("host_target")
        if raw_host is None:
            raise ValueError(f"Batch entry [{index}] is missing host_target.")
        try:
            resolved_host_target = _resolve_object_target_for_model(raw_host)
            host = ensure_face_host(find_object(working_model, resolved_host_target))
        except Exception as exc:
            raise ValueError(f"Batch entry [{index}] invalid host_target: {exc}") from exc
        resolved_hosts.append(resolved_host_target)
        parent = {
            **resolved_host_target.get("parent", {}),
            "face_identifier": host.identifier,
        }

        if mode == "geometry":
            item_id = spec.get("identifier")
            item_geom = spec.get("geometry")
            if not isinstance(item_id, str) or not item_id.strip():
                raise ValueError(f"items[{index}].identifier is required in geometry mode.")
            if item_geom is None:
                raise ValueError(f"items[{index}].geometry is required in geometry mode.")
            if item_id in used_model_ids:
                raise ValueError(
                    f"items[{index}] identifier already exists: {item_id}."
                )
            aperture = Aperture(
                item_id,
                face3d_from_dict(item_geom),
                is_operable=bool(spec.get("is_operable", is_operable)),
            )
            validate_honeybee_aperture(aperture)
            host.add_aperture(aperture)
            validate_face_sub_faces(host)
            used_model_ids.add(item_id)
            target = make_honeybee_object_target(
                garden_id=manifest.garden_id,
                model_identifier=model_identifier,
                object_type="aperture",
                object_identifier=item_id,
                parent=parent,
            )
            created_apertures.append(aperture)
            created_targets.append(target)
            object_summaries.append(object_summary(target, aperture.to_dict()))

        elif mode in {"parameters", "skylight_ratio"}:
            is_skylight = mode == "skylight_ratio"
            item_gen_mode = (
                "by_ratio"
                if is_skylight
                else str(spec.get("generation_mode", generation_mode) or "by_ratio")
            )
            try:
                created_on_host, existing_on_host, _ = (
                    _generate_parametric_apertures_on_host(
                        host,
                        generation_mode=item_gen_mode,
                        ratio=spec.get("ratio", ratio),
                        aperture_width=spec.get("aperture_width", aperture_width),
                        aperture_height=spec.get("aperture_height", aperture_height),
                        sill_height=float(spec.get("sill_height", sill_height)),
                        aperture_identifier=spec.get(
                            "aperture_identifier", aperture_identifier
                        ),
                        identifier_prefix=spec.get(
                            "identifier_prefix", identifier_prefix
                        ),
                        tolerance=float(spec.get("tolerance", tolerance)),
                        rect_split=bool(spec.get("rect_split", rect_split)),
                        skylight_mode=is_skylight,
                        used_model_ids=used_model_ids,
                    )
                )
            except Exception as exc:
                raise ValueError(f"Batch entry [{index}] ({host.identifier}): {exc}") from exc

            for aperture in created_on_host:
                target = make_honeybee_object_target(
                    garden_id=manifest.garden_id,
                    model_identifier=model_identifier,
                    object_type="aperture",
                    object_identifier=aperture.identifier,
                    parent=parent,
                )
                created_apertures.append(aperture)
                created_targets.append(target)
                object_summaries.append(object_summary(target, aperture.to_dict()))
            for aperture in existing_on_host:
                target = make_honeybee_object_target(
                    garden_id=manifest.garden_id,
                    model_identifier=model_identifier,
                    object_type="aperture",
                    object_identifier=aperture.identifier,
                    parent=parent,
                )
                reused_targets.append(target)
                object_summaries.append(object_summary(target, aperture.to_dict()))

        else:  # guide_surface
            item_guides = spec.get("guide_surfaces", guide_surfaces)
            if not isinstance(item_guides, list) or not item_guides:
                raise ValueError(
                    f"Batch entry [{index}] requires non-empty guide_surfaces."
                )
            item_tol = float(spec.get("tolerance", tolerance))
            if item_tol <= 0:
                raise ValueError("tolerance must be greater than 0.")
            if not isinstance(host.boundary_condition, Outdoors):
                raise ValueError(
                    f"Batch entry [{index}] host {host.identifier} must have an Outdoors boundary condition."
                )
            validate_face_sub_faces(host)
            created_on_host, c_targets, r_targets, skipped = _guide_surfaces_on_host(
                host,
                guide_surfaces=item_guides,
                angle_tolerance=working_model.angle_tolerance,
                tolerance=item_tol,
                identifier_prefix=spec.get("identifier_prefix", identifier_prefix),
                manifest=manifest,
                model_identifier=model_identifier,
                parent=parent,
                used_model_ids=used_model_ids,
                allow_disambiguate=len(specs) > 1,
            )
            created_apertures.extend(created_on_host)
            created_targets.extend(c_targets)
            reused_targets.extend(r_targets)
            skipped_all.extend(skipped)
            for t, ap in zip(c_targets, created_on_host, strict=True):
                object_summaries.append(object_summary(t, ap.to_dict()))

    all_targets = [*created_targets, *reused_targets]
    warnings: list[str] = [item["message"] for item in skipped_all]
    if created_targets:
        working_model, postprocess = apply_honeybee_postprocess(
            model=working_model,
            garden_id=manifest.garden_id,
            model_identifier=model_identifier,
            operation="create_honeybee_apertures",
            target=resolved_hosts[0],
            object_type="aperture",
            object_types=["aperture"],
            strategy=postprocess_strategy,
        )
        updated_target, persisted_path = _save_changed_model(
            garden_root_path,
            manifest,
            resolved_model_target,
            working_model,
        )
        receipt = _save_receipt(
            garden_id=manifest.garden_id,
            model_target=updated_target,
            persisted_path=persisted_path,
            operation="create_honeybee_apertures",
            object_target=resolved_hosts[0],
            change_details={
                "mode": mode,
                "host_count": len(resolved_hosts),
                "created_targets": created_targets,
                "reused_targets": reused_targets,
                "skipped": skipped_all,
            },
            warnings=warnings,
        )
        runtime_status = None
    else:
        postprocess = {}
        updated_target = resolved_model_target
        receipt = _save_receipt(
            garden_id=manifest.garden_id,
            model_target=resolved_model_target,
            persisted_path=str(resolved_model_target.get("path", "")),
            operation="create_honeybee_apertures",
            object_target=resolved_hosts[0],
            change_details={
                "mode": mode,
                "host_count": len(resolved_hosts),
                "created_targets": [],
                "reused_targets": reused_targets,
                "skipped": skipped_all,
            },
            warnings=warnings,
            status="no_change",
        )
        runtime_status = "no_change"

    response: dict[str, Any] = {
        "target": all_targets[0] if all_targets else None,
        "aperture_target": all_targets[0] if all_targets else None,
        "targets": all_targets,
        "created_targets": created_targets,
        "reused_targets": reused_targets,
        "model_target": updated_target,
        "summary_view": {
            "mode": mode,
            "host_count": len(resolved_hosts),
            "host_targets": resolved_hosts,
            "created_count": len(created_targets),
            "reused_count": len(reused_targets),
            "skipped_count": len(skipped_all),
            "created_identifiers": [ap.identifier for ap in created_apertures],
            "objects": object_summaries,
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=(
                f"Created {len(created_targets)} Honeybee aperture(s) across "
                f"{len(resolved_hosts)} host face(s)."
            ),
            warnings=warnings,
        ),
    }
    if skipped_all:
        response["skipped"] = skipped_all
        response["summary_view"]["skipped"] = skipped_all
    if runtime_status:
        response["runtime_status"] = runtime_status
    return attach_postprocess_result(response, postprocess)


def create_honeybee_shades_by_parameters(
    *,
    garden_root: str,
    host_target: dict[str, Any],
    generation_mode: str,
    parameters: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Create Honeybee Shades on a Face or Aperture with SDK parameter methods."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    model_identifier = str(resolved_model_target["model_identifier"])
    created_shades, targets, resolved_host_target, host = _add_shades_by_parameters_in_model(
        model,
        manifest,
        model_identifier,
        host_target=host_target,
        generation_mode=generation_mode,
        parameters=parameters,
    )
    object_summaries = [
        object_summary(target, shade.to_dict())
        for target, shade in zip(targets, created_shades, strict=True)
    ]
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=model_identifier,
        operation="create_honeybee_shades_by_parameters",
        target=resolved_host_target,
        object_type="shade",
        strategy=postprocess_strategy,
    )
    updated_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    return attach_postprocess_result(
        {
            "target": targets[0],
            "shade_target": targets[0],
            "targets": targets,
            "summary_view": {
                "host_target": resolved_host_target,
                "generation_mode": generation_mode,
                "created_count": len(created_shades),
                "created_identifiers": [shade.identifier for shade in created_shades],
                "objects": object_summaries,
            },
            "persistence_receipt": _save_receipt(
                garden_id=manifest.garden_id,
                model_target=updated_target,
                persisted_path=persisted_path,
                operation="create_honeybee_shades_by_parameters",
                object_target=resolved_host_target,
                change_details={
                    "created_targets": targets,
                    "generation_mode": generation_mode,
                },
            ),
            "report": make_report(
                status="ok",
                message=(
                    f"Created {len(created_shades)} Honeybee shade(s) on "
                    f"{resolved_host_target['object_type']}: {host.identifier}"
                ),
            ),
        },
        postprocess,
    )


def create_honeybee_shades_batch(
    *,
    garden_root: str,
    mode: str,
    host_target: dict[str, Any] | None = None,
    host_targets: list[dict[str, Any]] | None = None,
    items: list[dict[str, Any]] | None = None,
    model_target: dict[str, Any] | None = None,
    attach_side: str = "outdoor",
    is_detached: bool = False,
    generation_mode: str | None = None,
    parameters: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Create multiple Honeybee Shades by geometry or parameters in one save."""
    if mode not in {"geometry", "parameters"}:
        raise ValueError("mode must be 'geometry' or 'parameters'.")
    if host_targets is not None and items is not None:
        raise ValueError("Provide either host_targets or items, not both.")
    if host_targets is None and items is None:
        raise ValueError("Batch shade creation requires host_targets or items.")

    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    working_model = model.duplicate()
    model_identifier = str(resolved_model_target["model_identifier"])
    used_identifiers = _model_object_identifiers(working_model)

    created_shades: list[Shade] = []
    created_targets: list[dict[str, Any]] = []
    object_summaries: list[dict[str, Any]] = []

    if mode == "geometry":
        if items is None or not isinstance(items, list) or not items:
            raise ValueError(
                "mode='geometry' batch creation requires a non-empty items list with identifier and geometry."
            )
        for index, raw_item in enumerate(items):
            if not isinstance(raw_item, dict):
                raise ValueError(f"items[{index}] must be a dictionary.")
            item_id = raw_item.get("identifier")
            item_geom = raw_item.get("geometry")
            if not isinstance(item_id, str) or not item_id.strip():
                raise ValueError(f"items[{index}].identifier is required.")
            if item_geom is None:
                raise ValueError(f"items[{index}].geometry is required.")
            try:
                shade, target = _add_shade_geometry_in_model(
                    working_model,
                    manifest,
                    model_identifier,
                    identifier=item_id,
                    geometry=item_geom,
                    host_target=raw_item.get("host_target", host_target),
                    attach_side=str(raw_item.get("attach_side", attach_side)),
                    is_detached=bool(raw_item.get("is_detached", is_detached)),
                )
            except Exception as exc:
                raise ValueError(f"items[{index}] ({item_id}): {exc}") from exc
            created_shades.append(shade)
            created_targets.append(target)
            object_summaries.append(object_summary(target, shade.to_dict()))
    else:
        specs: list[dict[str, Any]] = []
        if host_targets is not None:
            if not isinstance(host_targets, list) or not host_targets:
                raise ValueError("host_targets must be a non-empty list.")
            specs = [{"host_target": ht} for ht in host_targets]
        else:
            if not isinstance(items, list) or not items:
                raise ValueError("items must be a non-empty list.")
            for index, raw_item in enumerate(items):
                if not isinstance(raw_item, dict):
                    raise ValueError(f"items[{index}] must be a dictionary.")
                spec = dict(raw_item)
                if "host_target" not in spec and host_target is not None:
                    spec["host_target"] = host_target
                specs.append(spec)

        for index, spec in enumerate(specs):
            raw_host = spec.get("host_target")
            if raw_host is None:
                raise ValueError(f"Batch entry [{index}] is missing host_target.")
            item_gen_mode = spec.get("generation_mode", generation_mode)
            item_params = spec.get("parameters", parameters)
            if not item_gen_mode:
                raise ValueError(
                    f"Batch entry [{index}] requires generation_mode for parameters mode."
                )
            if item_params is None:
                raise ValueError(
                    f"Batch entry [{index}] requires parameters for parameters mode."
                )
            try:
                shades, targets, _, _ = _add_shades_by_parameters_in_model(
                    working_model,
                    manifest,
                    model_identifier,
                    host_target=raw_host,
                    generation_mode=str(item_gen_mode),
                    parameters=item_params,
                    used_identifiers=used_identifiers,
                )
            except Exception as exc:
                raise ValueError(f"Batch entry [{index}]: {exc}") from exc
            created_shades.extend(shades)
            created_targets.extend(targets)
            for t, s in zip(targets, shades, strict=True):
                object_summaries.append(object_summary(t, s.to_dict()))

    working_model, postprocess = apply_honeybee_postprocess(
        model=working_model,
        garden_id=manifest.garden_id,
        model_identifier=model_identifier,
        operation="create_honeybee_shades",
        target=created_targets[0],
        object_type="shade",
        object_types=["shade"],
        strategy=postprocess_strategy,
    )
    updated_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        working_model,
    )
    return attach_postprocess_result(
        {
            "target": created_targets[0],
            "shade_target": created_targets[0],
            "targets": created_targets,
            "model_target": updated_target,
            "summary_view": {
                "mode": mode,
                "created_count": len(created_shades),
                "created_identifiers": [s.identifier for s in created_shades],
                "objects": object_summaries,
            },
            "persistence_receipt": _save_receipt(
                garden_id=manifest.garden_id,
                model_target=updated_target,
                persisted_path=persisted_path,
                operation="create_honeybee_shades",
                object_target=created_targets[0],
                change_details={
                    "mode": mode,
                    "created_targets": created_targets,
                    "created_count": len(created_shades),
                },
            ),
            "report": make_report(
                status="ok",
                message=f"Created {len(created_shades)} Honeybee shade(s).",
            ),
        },
        postprocess,
    )


def create_honeybee_door(
    *,
    garden_root: str,
    identifier: str,
    host_target: dict[str, Any],
    geometry: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
    is_glass: bool = False,
    door_width: float | None = None,
    door_height: float = 2.1,
    sill_height: float = 0.05,
    placement: str = "auto",
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Create a Honeybee Door on a host Face target."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    model_identifier = str(resolved_model_target["model_identifier"])
    door, target, adjacent_target, created_doors, resolved_host_target = _add_door_in_model(
        model,
        manifest,
        model_identifier,
        identifier=identifier,
        host_target=host_target,
        geometry=geometry,
        is_glass=is_glass,
        door_width=door_width,
        door_height=door_height,
        sill_height=sill_height,
        placement=placement,
    )
    if adjacent_target is not None:
        validate_model_adjacency(model)
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=model_identifier,
        operation="create_honeybee_door",
        target=target,
        object_type="door",
        strategy=postprocess_strategy,
    )
    updated_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    response = _created_object_response(
        object_dict=door.to_dict(),
        target=target,
        garden_id=manifest.garden_id,
        model_target=updated_target,
        persisted_path=persisted_path,
        operation="create_honeybee_door",
        message=(
            f"Created Honeybee door: {identifier}"
            if adjacent_target is None
            else f"Created interior Honeybee door pair: {identifier}"
        ),
        postprocess=postprocess,
    )
    response["targets"] = [target] + ([adjacent_target] if adjacent_target else [])
    response["summary_view"] = {
        **response["summary_view"],
        "created_count": len(created_doors),
        "created_identifiers": [created.identifier for created in created_doors],
        "host_target": resolved_host_target,
        "is_interior_pair": adjacent_target is not None,
        **({"adjacent_target": adjacent_target} if adjacent_target else {}),
    }
    response["persistence_receipt"]["change_summary"]["created_targets"] = response[
        "targets"
    ]
    if adjacent_target is not None:
        response["adjacent_target"] = adjacent_target
    return response


def _rectangular_door_geometry_from_host(
    host: Face,
    *,
    width: float,
    height: float,
    sill_height: float,
    placement: str,
    tolerance: float,
) -> dict[str, Any]:
    """Generate a simple rectangular Door Face3D inside an axis-aligned wall."""
    if width <= 0:
        raise ValueError("door_width must be a positive number.")
    if height <= 0:
        raise ValueError("door_height must be a positive number.")
    if sill_height < 0:
        raise ValueError("sill_height must be zero or a positive number.")

    geometry = host.geometry
    normal = geometry.normal
    if abs(float(normal.z)) > max(abs(float(normal.x)), abs(float(normal.y))):
        raise ValueError(
            "Parameterized door geometry requires a vertical wall host Face. "
            "Use explicit geometry for floors, roofs, or sloped faces."
        )
    constant_axis = 0 if abs(float(normal.x)) >= abs(float(normal.y)) else 1
    horizontal_axis = 1 if constant_axis == 0 else 0
    vertices = list(geometry.vertices)
    constant = sum(_point_axis(vertex, constant_axis) for vertex in vertices) / len(
        vertices
    )
    horizontal_values = [_point_axis(vertex, horizontal_axis) for vertex in vertices]
    z_values = [float(vertex.z) for vertex in vertices]
    host_min = min(horizontal_values)
    host_max = max(horizontal_values)
    z_min = min(z_values)
    z_max = max(z_values)
    margin = max(float(tolerance) * 5, 0.05)
    bottom = z_min + max(sill_height, margin)
    top = bottom + height
    if top > z_max - tolerance:
        raise ValueError(
            "door_height plus sill_height exceeds the host Face height. "
            "Use a shorter door_height or explicit geometry."
        )

    available = [(host_min + margin, host_max - margin)]
    blocked: list[tuple[float, float]] = []
    for child in list(getattr(host, "apertures", []) or []) + list(
        getattr(host, "doors", []) or []
    ):
        child_vertices = list(child.geometry.vertices)
        child_z = [float(vertex.z) for vertex in child_vertices]
        if max(child_z) <= bottom + margin or min(child_z) >= top - margin:
            continue
        child_h = [_point_axis(vertex, horizontal_axis) for vertex in child_vertices]
        blocked.append((min(child_h) - margin, max(child_h) + margin))

    for start, end in sorted(blocked):
        split: list[tuple[float, float]] = []
        for available_start, available_end in available:
            if end <= available_start or start >= available_end:
                split.append((available_start, available_end))
                continue
            if start - available_start >= width:
                split.append((available_start, start))
            if available_end - end >= width:
                split.append((end, available_end))
        available = split

    placement_value = str(placement or "auto").strip().lower()
    if placement_value in {"right", "end", "max"}:
        candidate_intervals = list(reversed(available))
    elif placement_value in {"center", "middle"}:
        candidate_intervals = sorted(
            available,
            key=lambda interval: abs(
                ((interval[0] + interval[1]) / 2) - ((host_min + host_max) / 2)
            ),
        )
    else:
        candidate_intervals = available

    interval = next(
        (
            candidate
            for candidate in candidate_intervals
            if candidate[1] - candidate[0] >= width
        ),
        None,
    )
    if interval is None:
        raise ValueError(
            "Could not fit a rectangular door on the host Face without overlapping "
            "existing apertures or doors. Search the host face's child apertures/doors, "
            "choose a smaller door_width, or provide explicit geometry in a free area."
        )
    h_min = (
        interval[0]
        if placement_value not in {"right", "end", "max"}
        else interval[1] - width
    )
    if placement_value in {"center", "middle"}:
        h_min = ((interval[0] + interval[1]) / 2) - (width / 2)
    h_max = h_min + width

    points = [
        _wall_point(constant_axis, horizontal_axis, constant, h_min, bottom),
        _wall_point(constant_axis, horizontal_axis, constant, h_max, bottom),
        _wall_point(constant_axis, horizontal_axis, constant, h_max, top),
        _wall_point(constant_axis, horizontal_axis, constant, h_min, top),
    ]
    door_face = Face3D(points)
    if _dot_vectors(door_face.normal, normal) < 0:
        door_face = Face3D(list(reversed(points)))
    return door_face.to_dict()


def _point_axis(point: Point3D, axis: int) -> float:
    return [float(point.x), float(point.y), float(point.z)][axis]


def _wall_point(
    constant_axis: int,
    horizontal_axis: int,
    constant: float,
    horizontal: float,
    z_value: float,
) -> Point3D:
    coordinates = [0.0, 0.0, float(z_value)]
    coordinates[constant_axis] = float(constant)
    coordinates[horizontal_axis] = float(horizontal)
    return Point3D(*coordinates)


def _dot_vectors(first: Any, second: Any) -> float:
    return (
        float(first.x) * float(second.x)
        + float(first.y) * float(second.y)
        + float(first.z) * float(second.z)
    )


def _adjacent_surface_face(model: Model, host: Face) -> Face | None:
    """Return the Honeybee Face adjacent to a Surface-boundary host Face."""
    boundary_condition = host.boundary_condition
    if not isinstance(boundary_condition, Surface):
        return None
    adjacent_face_identifier = boundary_condition.boundary_condition_objects[0]
    adjacent_room_identifier = boundary_condition.boundary_condition_objects[1]
    for room in model.rooms:
        if room.identifier != adjacent_room_identifier:
            continue
        for face in room.faces:
            if face.identifier == adjacent_face_identifier:
                return face
    raise ValueError(
        "The host face has a Surface boundary condition but its adjacent face "
        f"could not be found: {adjacent_face_identifier} in "
        f"{adjacent_room_identifier}."
    )


def create_honeybee_shade(
    *,
    garden_root: str,
    identifier: str,
    geometry: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    host_target: dict[str, Any] | None = None,
    attach_side: str = "outdoor",
    is_detached: bool = False,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Create a Honeybee Shade as orphaned or attached to a host object."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    model_identifier = str(resolved_model_target["model_identifier"])
    shade, target = _add_shade_geometry_in_model(
        model,
        manifest,
        model_identifier,
        identifier=identifier,
        geometry=geometry,
        host_target=host_target,
        attach_side=attach_side,
        is_detached=is_detached,
    )
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=model_identifier,
        operation="create_honeybee_shade",
        target=target,
        object_type="shade",
        strategy=postprocess_strategy,
    )
    updated_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    return _created_object_response(
        object_dict=shade.to_dict(),
        target=target,
        garden_id=manifest.garden_id,
        model_target=updated_target,
        persisted_path=persisted_path,
        operation="create_honeybee_shade",
        message=f"Created Honeybee shade: {identifier}",
        postprocess=postprocess,
    )


def _created_object_response(
    *,
    object_dict: dict[str, Any],
    target: dict[str, Any],
    garden_id: str,
    model_target: dict[str, Any],
    persisted_path: str,
    operation: str,
    message: str,
    postprocess: dict[str, Any] | None = None,
) -> dict[str, Any]:
    object_type = str(target.get("object_type") or "").lower()
    response = {
        "object_dict": object_dict,
        "target": target,
        "object_target": target,
        "model_target": model_target,
        "summary_view": object_summary(target, object_dict),
        "persistence_receipt": _save_receipt(
            garden_id=garden_id,
            model_target=model_target,
            persisted_path=persisted_path,
            operation=operation,
            object_target=target,
        ),
        "report": make_report(status="ok", message=message),
    }
    if object_type:
        response[f"{object_type}_target"] = target
    return attach_postprocess_result(
        {
            **response,
        },
        postprocess or {},
    )
