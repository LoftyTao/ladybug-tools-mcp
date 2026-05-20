"""Honeybee object creation services."""

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
from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.pointvector import Point3D

from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report
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
    load_honeybee_model,
    resolve_model_target,
    save_honeybee_model,
    with_honeybee_model_write_lock,
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
) -> dict[str, Any]:
    return make_persistence_receipt(
        status="persisted",
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
        "Use search_honeybee_model_objects to reuse the existing target, remove "
        "the existing object first, or choose a new unique identifier."
    )


@with_honeybee_model_write_lock
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
) -> dict[str, Any]:
    """Create a Honeybee Model and optionally persist it to a Garden."""
    garden_root = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root)
    model = Model(
        identifier,
        units=units,
        tolerance=tolerance,
        angle_tolerance=angle_tolerance,
    )
    add_summary = add_objects_to_model(model, add_objects)
    receipt: dict[str, Any] | None = None
    if save_back:
        model_target, persisted_path = save_honeybee_model(
            garden_root,
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

    return {
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


def _load_target_model(
    garden_root: str,
    model_target: dict[str, Any] | None,
) -> tuple[Path, GardenManifest, dict[str, Any], Model]:
    garden_root = _garden_root(garden_root)
    manifest, model_target = resolve_model_target(garden_root, model_target)
    model = load_honeybee_model(garden_root, model_target)
    return garden_root, manifest, model_target, model


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


@with_honeybee_model_write_lock
def create_honeybee_room(
    *,
    garden_root: str,
    identifier: str,
    faces: list[dict[str, Any]] | None = None,
    room_geometry: dict[str, Any] | None = None,
    x_dim: float | None = None,
    y_dim: float | None = None,
    height: float | None = None,
    origin: list[float] | None = None,
    model_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Create a Honeybee Room from Face dictionaries or a Polyface3D envelope."""
    has_faces = faces is not None
    has_room_geometry = room_geometry is not None
    has_box = any(value is not None for value in (x_dim, y_dim, height, origin))
    if sum((has_faces, has_room_geometry, has_box)) != 1:
        raise ValueError(
            "create_honeybee_room requires exactly one geometry mode: _faces, "
            "_room_geometry, or x_dim_/y_dim_/height_."
        )
    if has_box and any(value is None for value in (x_dim, y_dim, height)):
        raise ValueError("Box room creation requires x_dim_, y_dim_, and height_.")

    garden_root, manifest, model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    _ensure_unique_object_identifier(model, identifier)
    if faces is not None:
        room = Room(identifier, [Face.from_dict(face) for face in faces])
    elif room_geometry is not None:
        room = Room.from_polyface3d(identifier, polyface3d_from_dict(room_geometry))
    else:
        origin_point = Point3D(*(origin or [0, 0, 0]))
        room = Room.from_box(
            identifier,
            width=float(x_dim),
            depth=float(y_dim),
            height=float(height),
            origin=origin_point,
        )
    validate_honeybee_room(room)
    model.add_room(room)
    validate_model_adjacency(model)
    target = make_honeybee_object_target(
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        object_type="room",
        object_identifier=identifier,
    )
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="create_honeybee_room",
        target=target,
        object_type="room",
        strategy=postprocess_strategy,
    )
    updated_target, persisted_path = _save_changed_model(
        garden_root,
        manifest,
        model_target,
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


@with_honeybee_model_write_lock
def create_honeybee_face(
    *,
    garden_root: str,
    identifier: str,
    geometry: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Create an orphaned Honeybee Face in a model."""
    garden_root, manifest, model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    _ensure_unique_object_identifier(model, identifier)
    face = Face(identifier, face3d_from_dict(geometry))
    validate_honeybee_face(face)
    model.add_face(face)
    target = make_honeybee_object_target(
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        object_type="face",
        object_identifier=identifier,
    )
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="create_honeybee_face",
        target=target,
        object_type="face",
        strategy=postprocess_strategy,
    )
    updated_target, persisted_path = _save_changed_model(
        garden_root,
        manifest,
        model_target,
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


@with_honeybee_model_write_lock
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
    garden_root, manifest, model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    _ensure_unique_object_identifier(model, identifier)
    host_target = _resolve_object_target_for_model(host_target)
    host = ensure_face_host(find_object(model, host_target))
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
        model_identifier=str(model_target["model_identifier"]),
        object_type="aperture",
        object_identifier=identifier,
        parent={**host_target.get("parent", {}), "face_identifier": host.identifier},
    )
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="create_honeybee_aperture",
        target=target,
        object_type="aperture",
        strategy=postprocess_strategy,
    )
    updated_target, persisted_path = _save_changed_model(
        garden_root,
        manifest,
        model_target,
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


@with_honeybee_model_write_lock
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
) -> dict[str, Any]:
    """Create Honeybee Apertures on a host Face with SDK parameter methods."""
    garden_root, manifest, model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    host_target = _resolve_object_target_for_model(host_target)
    host = ensure_face_host(find_object(model, host_target))
    before_ids = {aperture.identifier for aperture in host.apertures}

    if generation_mode == "by_ratio":
        if ratio is None:
            raise ValueError("ratio is required when generation_mode is 'by_ratio'.")
        if not 0 < ratio < 1:
            raise ValueError("ratio must be greater than 0 and less than 1.")
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
        parent = {**host_target.get("parent", {}), "face_identifier": host.identifier}
        targets = [
            make_honeybee_object_target(
                garden_id=manifest.garden_id,
                model_identifier=str(model_target["model_identifier"]),
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
            "No new Honeybee apertures were created because the host face already "
            "has apertures. Returning existing aperture targets."
        )
        return {
            "target": targets[0],
            "aperture_target": targets[0],
            "targets": targets,
            "summary_view": {
                "host_target": host_target,
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
                model_target=model_target,
                persisted_path=str(model_target.get("path", "")),
                operation="create_honeybee_apertures_by_parameters",
                object_target=host_target,
                change_details={
                    "created_targets": [],
                    "existing_targets": targets,
                    "generation_mode": generation_mode,
                },
                warnings=[warning],
            ),
            "report": make_report(
                status="ok",
                message="Existing Honeybee apertures returned.",
                warnings=[warning],
            ),
        }
    if identifier_prefix:
        existing_ids = {
            aperture.identifier for aperture in host.apertures if aperture not in created_apertures
        }
        for index, aperture in enumerate(created_apertures, start=1):
            candidate = (
                identifier_prefix
                if len(created_apertures) == 1
                else f"{identifier_prefix}_{index}"
            )
            while candidate in existing_ids:
                index += 1
                candidate = f"{identifier_prefix}_{index}"
            aperture.identifier = candidate
            existing_ids.add(candidate)

    parent = {**host_target.get("parent", {}), "face_identifier": host.identifier}
    targets = [
        make_honeybee_object_target(
            garden_id=manifest.garden_id,
            model_identifier=str(model_target["model_identifier"]),
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
        model_identifier=str(model_target["model_identifier"]),
        operation="create_honeybee_apertures_by_parameters",
        target=host_target,
        object_type="aperture",
        strategy=postprocess_strategy,
    )
    updated_target, persisted_path = _save_changed_model(
        garden_root,
        manifest,
        model_target,
        model,
    )
    return attach_postprocess_result(
        {
            "target": targets[0],
            "aperture_target": targets[0],
            "targets": targets,
            "summary_view": {
                "host_target": host_target,
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
                operation="create_honeybee_apertures_by_parameters",
                object_target=host_target,
                change_details={
                    "created_targets": targets,
                    "generation_mode": generation_mode,
                },
            ),
            "report": make_report(
                status="ok",
                message=(
                    f"Created {len(created_apertures)} Honeybee aperture(s) on face: "
                    f"{host.identifier}"
                ),
            ),
        },
        postprocess,
    )


@with_honeybee_model_write_lock
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
    garden_root, manifest, model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    host_target = _resolve_object_target_for_model(host_target)
    host = find_object(model, host_target)
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
        existing_ids = {
            shade.identifier
            for shade in getattr(host, "shades", [])
            if shade not in created_shades
        }
        for index, shade in enumerate(created_shades, start=1):
            candidate = base_name if len(created_shades) == 1 else f"{base_name}_{index}"
            while candidate in existing_ids:
                index += 1
                candidate = f"{base_name}_{index}"
            shade.identifier = candidate
            existing_ids.add(candidate)

    parent = dict(host_target.get("parent", {}))
    parent[f"{host_target['object_type']}_identifier"] = host.identifier
    targets = [
        make_honeybee_object_target(
            garden_id=manifest.garden_id,
            model_identifier=str(model_target["model_identifier"]),
            object_type="shade",
            object_identifier=shade.identifier,
            parent=parent,
        )
        for shade in created_shades
    ]
    object_summaries = [
        object_summary(target, shade.to_dict())
        for target, shade in zip(targets, created_shades, strict=True)
    ]
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="create_honeybee_shades_by_parameters",
        target=host_target,
        object_type="shade",
        strategy=postprocess_strategy,
    )
    updated_target, persisted_path = _save_changed_model(
        garden_root,
        manifest,
        model_target,
        model,
    )
    return attach_postprocess_result(
        {
            "target": targets[0],
            "shade_target": targets[0],
            "targets": targets,
            "summary_view": {
                "host_target": host_target,
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
                object_target=host_target,
                change_details={
                    "created_targets": targets,
                    "generation_mode": generation_mode,
                },
            ),
            "report": make_report(
                status="ok",
                message=(
                    f"Created {len(created_shades)} Honeybee shade(s) on "
                    f"{host_target['object_type']}: {host.identifier}"
                ),
            ),
        },
        postprocess,
    )


@with_honeybee_model_write_lock
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
    garden_root, manifest, model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    _ensure_unique_object_identifier(model, identifier)
    host_target = _resolve_object_target_for_model(host_target)
    host = ensure_face_host(find_object(model, host_target))
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
        model_identifier=str(model_target["model_identifier"]),
        object_type="door",
        object_identifier=identifier,
        parent={**host_target.get("parent", {}), "face_identifier": host.identifier},
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
        validate_model_adjacency(model)
        created_doors.append(adjacent_door)
        adjacent_target = make_honeybee_object_target(
            garden_id=manifest.garden_id,
            model_identifier=str(model_target["model_identifier"]),
            object_type="door",
            object_identifier=adjacent_door.identifier,
            parent={
                "room_identifier": adjacent_face.parent.identifier,
                "face_identifier": adjacent_face.identifier,
            },
        )
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="create_honeybee_door",
        target=target,
        object_type="door",
        strategy=postprocess_strategy,
    )
    updated_target, persisted_path = _save_changed_model(
        garden_root,
        manifest,
        model_target,
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
        "host_target": host_target,
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


@with_honeybee_model_write_lock
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
    if host_target is not None:
        host_target = normalize_honeybee_object_target(host_target)
    garden_root, manifest, model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
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
        model_identifier=str(model_target["model_identifier"]),
        object_type="shade",
        object_identifier=identifier,
        parent=parent,
    )
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="create_honeybee_shade",
        target=target,
        object_type="shade",
        strategy=postprocess_strategy,
    )
    updated_target, persisted_path = _save_changed_model(
        garden_root,
        manifest,
        model_target,
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
