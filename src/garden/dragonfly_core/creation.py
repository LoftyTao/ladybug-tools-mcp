"""Dragonfly object creation services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dragonfly.building import Building
from dragonfly.context import ContextShade
from dragonfly.model import Model
from dragonfly.room2d import Room2D
from dragonfly.story import Story
from honeybee.typing import clean_string
from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.pointvector import Point3D

from garden.dragonfly_core.model_io import save_dragonfly_model
from garden.manifest import GardenManifest
from garden.paths import to_posix_relative
from garden.dragonfly_core.model_io import load_dragonfly_model, resolve_model_target
from garden.dragonfly_core.targets import (
    make_dragonfly_object_target,
    normalize_dragonfly_object_target,
    object_summary,
)
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report

DRAGONFLY_OBJECTS_DIR = Path("models") / "dragonfly" / "objects"


def _garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def _save_receipt(
    *,
    garden_id: str,
    model_target: dict[str, Any],
    persisted_path: str,
    operation: str,
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
            "target": model_target,
            **(change_details or {}),
        },
    )


def create_dragonfly_model(
    *,
    garden_root: str,
    identifier: str,
    display_name: str | None = None,
    units: str = "Meters",
    tolerance: float | None = None,
    angle_tolerance: float = 1.0,
    save_back: bool = True,
    set_base: bool = True,
    include_body: bool = False,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict[str, Any]:
    """Create a Dragonfly Model and optionally persist it to a Garden."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_identifier = _clean_dragonfly_identifier(identifier)
    model = Model(
        resolved_identifier,
        units=units,
        tolerance=tolerance,
        angle_tolerance=angle_tolerance,
    )
    resolved_display_name = display_name or (
        identifier if resolved_identifier != identifier else None
    )
    if resolved_display_name:
        model.display_name = resolved_display_name
    if latitude is not None or longitude is not None:
        model.user_data = {
            **(model.user_data or {}),
            "location_context": {
                "latitude": latitude,
                "longitude": longitude,
            },
        }
    receipt: dict[str, Any] | None = None
    if save_back:
        model_target, persisted_path = save_dragonfly_model(
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
            operation="create_dragonfly_model",
            change_details={"base_dragonfly_model_changed": bool(set_base)},
        )
    else:
        model_target = None
        object_dict = model.to_dict() if include_body else None

    return {
        "object_dict": object_dict,
        "target": model_target,
        "model_target": model_target,
        "summary_view": {
            "model_identifier": resolved_identifier,
            "display_name": resolved_display_name,
            "units": units,
            "saved": save_back,
            "base_dragonfly_model_changed": bool(save_back and set_base),
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=f"Created Dragonfly model: {resolved_identifier}",
        ),
    }


def _object_type_dir(object_type: str) -> str:
    return object_type.replace("_", "")


def _save_object_dict(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    model_identifier: str,
    object_type: str,
    object_identifier: str,
    object_dict: dict[str, Any],
    parent: dict[str, str] | None = None,
) -> tuple[dict[str, Any], str]:
    object_dir = (
        garden_root
        / DRAGONFLY_OBJECTS_DIR
        / model_identifier
        / _object_type_dir(object_type)
    )
    object_dir.mkdir(parents=True, exist_ok=True)
    object_path = object_dir / f"{object_identifier}.json"
    object_path.write_text(
        json.dumps(object_dict, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    persisted_path = to_posix_relative(object_path, garden_root)
    target = make_dragonfly_object_target(
        garden_id=manifest.garden_id,
        model_identifier=model_identifier,
        object_type=object_type,
        object_identifier=object_identifier,
        parent=parent,
        path=persisted_path,
    )
    return target, persisted_path


def _load_object_dict(garden_root: Path, target: dict[str, Any]) -> dict[str, Any]:
    path_value = target.get("path")
    if not path_value:
        model_identifier = target.get("model_identifier")
        object_type = target.get("object_type")
        object_identifier = target.get("object_identifier")
        if model_identifier and object_type and object_identifier:
            path_value = (
                DRAGONFLY_OBJECTS_DIR
                / str(model_identifier)
                / _object_type_dir(str(object_type))
                / f"{object_identifier}.json"
            ).as_posix()
    if not path_value:
        raise ValueError("Dragonfly draft object target must include a Garden path.")
    object_path = garden_root / str(path_value)
    return json.loads(object_path.read_text(encoding="utf-8"))


def _target_from_response(value: dict[str, Any], expected_type: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Expected a Dragonfly {expected_type} target dictionary.")
    if value.get("target_type") == "dragonfly_object":
        return value
    for key in (f"{expected_type}_target", "object_target", "target"):
        candidate = value.get(key)
        if isinstance(candidate, dict):
            return candidate
    return value


def _load_target_model(
    garden_root: str,
    model_target: dict[str, Any] | None,
) -> tuple[Path, GardenManifest, dict[str, Any], Model]:
    garden_root_path = _garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    return garden_root_path, manifest, resolved_model_target, model


def _save_changed_model(
    garden_root: Path,
    manifest: GardenManifest,
    model_target: dict[str, Any],
    model: Model,
) -> tuple[dict[str, Any], str]:
    return save_dragonfly_model(
        garden_root,
        manifest,
        model,
        name=str(model_target["model_identifier"]),
        set_base=manifest.base_dragonfly_model == model_target,
    )


def _one_by_identifier(objects: list[Any], identifier: str, object_type: str) -> Any:
    if len(objects) == 1:
        return objects[0]
    if not objects:
        raise ValueError(f"Dragonfly {object_type} not found: {identifier}.")
    raise ValueError(f"Dragonfly {object_type} identifier is ambiguous: {identifier}.")


def _model_object_identifiers(model: Model) -> set[tuple[str, str]]:
    identifiers: set[tuple[str, str]] = set()
    for building in model.buildings:
        identifiers.add(("building", building.identifier))
        for story in building.unique_stories:
            identifiers.add(("story", story.identifier))
            for room in story.room_2ds:
                identifiers.add(("room2d", room.identifier))
    for shade in model.context_shades:
        identifiers.add(("context_shade", shade.identifier))
    return identifiers


def _ensure_unique_model_objects(model: Model, objects: list[tuple[str, str]]) -> None:
    existing = _model_object_identifiers(model)
    duplicates = [
        f"{object_type}:{identifier}"
        for object_type, identifier in objects
        if (object_type, identifier) in existing
    ]
    if duplicates:
        raise ValueError(
            "Dragonfly object identifier already exists in the model: "
            + ", ".join(duplicates)
        )


def separate_building_top_bottom_stories(building: Building) -> None:
    """Use the Dragonfly SDK to separate repeated top/bottom Stories."""
    if not building.has_room_2ds:
        return
    for story in building.unique_stories:
        story.set_ground_contact(False)
        story.set_top_exposed(False)
    building.separate_top_bottom_floors()


def _created_object_response(
    *,
    object_dict: dict[str, Any],
    target: dict[str, Any],
    garden_id: str,
    model_target: dict[str, Any],
    persisted_path: str,
    operation: str,
    message: str,
) -> dict[str, Any]:
    object_type = str(target.get("object_type") or "")
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
            change_details={"target": target},
        ),
        "report": make_report(status="ok", message=message),
    }
    if object_type:
        response[f"{object_type}_target"] = target
    return response


def create_dragonfly_room2d(
    *,
    garden_root: str,
    identifier: str,
    display_name: str | None = None,
    floor_height: float | None = None,
    vertices: Any = None,
    floor_to_ceiling_height: float | None = None,
    model_target: dict[str, Any] | None = None,
    is_ground_contact: bool = False,
    is_top_exposed: bool = False,
    x_dim: float | None = None,
    y_dim: float | None = None,
    origin: list[float] | None = None,
    height: float | None = None,
    story_number: int | None = None,
) -> dict[str, Any]:
    """Create a Dragonfly Room2D draft object inside a Garden."""
    garden_root_path, manifest, resolved_model_target, _model = _load_target_model(
        garden_root,
        model_target,
    )
    if vertices is None:
        if x_dim is None or y_dim is None:
            raise ValueError(
                "create_dragonfly_room2d requires either vertices or rectangular "
                "dimensions x_dim and y_dim."
            )
        origin_x = float(origin[0]) if origin else 0.0
        origin_y = float(origin[1]) if origin and len(origin) > 1 else 0.0
        vertices = [
            [origin_x, origin_y],
            [origin_x + float(x_dim), origin_y],
            [origin_x + float(x_dim), origin_y + float(y_dim)],
            [origin_x, origin_y + float(y_dim)],
        ]
    vertices = _normalize_room2d_vertices(vertices)
    resolved_height = floor_to_ceiling_height if floor_to_ceiling_height is not None else height
    if resolved_height is None:
        resolved_height = 3.0
    if floor_height is None:
        floor_height = max(story_number - 1, 0) * resolved_height if story_number else 0.0
    resolved_identifier = _clean_dragonfly_identifier(identifier)
    room = Room2D.from_vertices(
        resolved_identifier,
        vertices,
        floor_height,
        resolved_height,
        is_ground_contact=is_ground_contact,
        is_top_exposed=is_top_exposed,
    )
    if display_name:
        room.display_name = display_name
    object_dict = room.to_dict()
    target, persisted_path = _save_object_dict(
        garden_root=garden_root_path,
        manifest=manifest,
        model_identifier=str(resolved_model_target["model_identifier"]),
        object_type="room2d",
        object_identifier=resolved_identifier,
        object_dict=object_dict,
    )
    return _created_object_response(
        object_dict=object_dict,
        target=target,
        garden_id=manifest.garden_id,
        model_target=resolved_model_target,
        persisted_path=persisted_path,
        operation="create_dragonfly_room2d",
        message=f"Created Dragonfly Room2D: {resolved_identifier}",
    )


def _face3d_from_points(points: list[list[float]]) -> Face3D:
    z_offset = 0.0
    if isinstance(points, dict):
        plane = points.get("plane")
        if isinstance(plane, dict):
            origin = plane.get("origin") or plane.get("o")
            if isinstance(origin, list) and len(origin) > 2:
                z_offset = float(origin[2])
        points = (
            points.get("vertices")
            or points.get("boundary")
        )
    if (
        isinstance(points, list)
        and points
        and isinstance(points[0], list)
        and points[0]
        and isinstance(points[0][0], list)
    ):
        points = points[0]
    if points is None:
        raise ValueError("ContextShade face dictionaries require vertices or boundary.")
    if len(points) < 3:
        raise ValueError("ContextShade geometry faces need at least three points.")
    vertices = []
    for point in points:
        if len(point) >= 3:
            vertices.append(Point3D(float(point[0]), float(point[1]), float(point[2])))
        else:
            vertices.append(Point3D(float(point[0]), float(point[1]), z_offset))
    return Face3D(vertices)


def _identifier_from_display_name(display_name: str | None) -> str | None:
    if not display_name:
        return None
    return _clean_dragonfly_identifier(display_name)


def _clean_dragonfly_identifier(identifier: str) -> str:
    return clean_string(identifier, "dragonfly object identifier")


def _normalize_room2d_vertices(vertices: Any) -> Any:
    if not isinstance(vertices, list):
        return vertices
    normalized = []
    for point in vertices:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            normalized.append(point)
            continue
        normalized.append([float(point[0]), float(point[1])])
    return normalized


def create_dragonfly_context_shade(
    *,
    garden_root: str,
    identifier: str,
    geometry: Any = None,
    vertices: Any = None,
    model_target: dict[str, Any] | None = None,
    is_detached: bool = True,
    x_dim: float | None = None,
    y_dim: float | None = None,
    height: float | None = None,
    origin: list[float] | None = None,
    display_name: str | None = None,
    context_shade_type: str | None = None,
    is_vegetation: bool | None = None,
    cen_pt: list[float] | None = None,
    radius: float | None = None,
) -> dict[str, Any]:
    """Create a Dragonfly ContextShade and persist it into the model."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    resolved_identifier = _clean_dragonfly_identifier(identifier)
    _ensure_unique_model_objects(model, [("context_shade", resolved_identifier)])
    raw_geometry = geometry
    if raw_geometry is None and x_dim is not None and y_dim is not None and height is not None:
        raw_geometry = _context_shade_box_faces(
            x_dim=float(x_dim),
            y_dim=float(y_dim),
            height=float(height),
            origin=origin,
        )
    if raw_geometry is None and vertices is not None:
        raw_geometry = _context_shade_faces_from_vertices(
            vertices,
            height=height,
            origin=origin,
        )
    if (
        isinstance(raw_geometry, list)
        and raw_geometry
        and isinstance(raw_geometry[0], list)
        and raw_geometry[0]
        and not isinstance(raw_geometry[0][0], list)
    ):
        raw_geometry = _context_shade_faces_from_vertices(
            raw_geometry,
            height=height,
            origin=origin,
        )
    if raw_geometry is None and cen_pt is not None and radius is not None:
        raw_geometry = _context_shade_from_center_radius(
            center=cen_pt,
            radius=float(radius),
            height=float(height or radius),
            context_shade_type=context_shade_type,
        )
    if raw_geometry is None:
        raise ValueError(
            "create_dragonfly_context_shade requires geometry, vertices, "
            "or x_dim/y_dim/height."
        )
    if isinstance(raw_geometry, dict):
        raw_geometry = [raw_geometry]
    faces = [_face3d_from_points(face_points) for face_points in raw_geometry]
    shade = ContextShade(resolved_identifier, faces, is_detached=is_detached)
    if display_name:
        shade.display_name = display_name
    if is_vegetation is not None:
        uwg = getattr(getattr(shade, "properties", None), "uwg", None)
        if uwg is not None and hasattr(uwg, "is_vegetation"):
            uwg.is_vegetation = bool(is_vegetation)
    model.add_context_shade(shade)
    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    target = make_dragonfly_object_target(
        garden_id=manifest.garden_id,
        model_identifier=str(updated_model_target["model_identifier"]),
        object_type="context_shade",
        object_identifier=resolved_identifier,
    )
    response = _created_object_response(
        object_dict=shade.to_dict(),
        target=target,
        garden_id=manifest.garden_id,
        model_target=updated_model_target,
        persisted_path=persisted_path,
        operation="create_dragonfly_context_shade",
        message=f"Created Dragonfly ContextShade: {resolved_identifier}",
    )
    response["summary_view"]["face_count"] = len(faces)
    return response


def _context_shade_box_faces(
    *,
    x_dim: float,
    y_dim: float,
    height: float,
    origin: list[float] | None = None,
) -> list[list[list[float]]]:
    x = float(origin[0]) if origin else 0.0
    y = float(origin[1]) if origin and len(origin) > 1 else 0.0
    z = float(origin[2]) if origin and len(origin) > 2 else 0.0
    x2 = x + x_dim
    y2 = y + y_dim
    z2 = z + height
    return [
        [[x, y, z], [x2, y, z], [x2, y, z2], [x, y, z2]],
        [[x2, y, z], [x2, y2, z], [x2, y2, z2], [x2, y, z2]],
        [[x2, y2, z], [x, y2, z], [x, y2, z2], [x2, y2, z2]],
        [[x, y2, z], [x, y, z], [x, y, z2], [x, y2, z2]],
        [[x, y, z2], [x2, y, z2], [x2, y2, z2], [x, y2, z2]],
    ]


def _context_shade_faces_from_vertices(
    vertices: Any,
    *,
    height: float | None,
    origin: list[float] | None = None,
) -> list[list[list[float]]]:
    if not isinstance(vertices, list) or len(vertices) < 3:
        raise ValueError("ContextShade vertices must define at least three points.")
    first = vertices[0]
    if not isinstance(first, list):
        raise ValueError("ContextShade vertices must be a list of point lists.")
    if len(first) >= 3:
        return [vertices]
    if height is None:
        raise ValueError("ContextShade 2D vertices require height.")
    z = float(origin[2]) if origin and len(origin) > 2 else 0.0
    base = [[float(point[0]), float(point[1]), z] for point in vertices]
    top = [[point[0], point[1], z + float(height)] for point in base]
    faces: list[list[list[float]]] = []
    for index, point in enumerate(base):
        next_index = (index + 1) % len(base)
        faces.append([point, base[next_index], top[next_index], top[index]])
    faces.append(top)
    return faces


def _context_shade_from_center_radius(
    *,
    center: list[float],
    radius: float,
    height: float,
    context_shade_type: str | None = None,
) -> list[list[list[float]]]:
    cx = float(center[0])
    cy = float(center[1]) if len(center) > 1 else 0.0
    cz = float(center[2]) if len(center) > 2 else 0.0
    if str(context_shade_type or "").lower() == "tree":
        z = cz + height
        return [
            [
                [cx - radius, cy - radius, z],
                [cx + radius, cy - radius, z],
                [cx + radius, cy + radius, z],
                [cx - radius, cy + radius, z],
            ]
        ]
    return _context_shade_box_faces(
        x_dim=radius * 2,
        y_dim=radius * 2,
        height=height,
        origin=[cx - radius, cy - radius, cz],
    )


def create_dragonfly_story(
    *,
    garden_root: str,
    room2d_targets: list[dict[str, Any]] | None = None,
    identifier: str | None = None,
    model_target: dict[str, Any] | None = None,
    floor_to_floor_height: float | None = None,
    floor_height: float | None = None,
    multiplier: int = 1,
    story_type: str = "Standard",
    display_name: str | None = None,
) -> dict[str, Any]:
    """Create a Dragonfly Story draft object from Room2D targets."""
    garden_root_path, manifest, resolved_model_target, _model = _load_target_model(
        garden_root,
        model_target,
    )
    resolved_identifier = (
        _clean_dragonfly_identifier(identifier)
        if identifier is not None
        else _identifier_from_display_name(display_name)
    )
    if resolved_identifier is None:
        raise ValueError("create_dragonfly_story requires identifier or display_name.")
    allowed_story_types = {"Standard", "CeilingPlenum", "FloorPlenum"}
    if story_type not in allowed_story_types:
        raise ValueError(
            "create_dragonfly_story story_type must be Standard, CeilingPlenum, or FloorPlenum."
        )
    if not room2d_targets:
        raise ValueError(
            "create_dragonfly_story requires room2d_targets. Use the room2d_target "
            "returned by create_dragonfly_room2d."
        )
    room_targets = [
        normalize_dragonfly_object_target(
            _target_from_response(target, "room2d"),
            expected_type="room2d",
        )
        for target in room2d_targets
    ]
    rooms = [
        Room2D.from_dict(_load_object_dict(garden_root_path, target))
        for target in room_targets
    ]
    if floor_height is not None:
        for room in rooms:
            room.floor_height = floor_height
    story = Story(
        resolved_identifier,
        rooms,
        floor_to_floor_height=floor_to_floor_height,
        floor_height=floor_height,
        multiplier=multiplier,
        type=story_type,
    )
    if display_name:
        story.display_name = display_name
    object_dict = story.to_dict()
    parent = {"room2d_identifiers": ",".join(room.identifier for room in rooms)}
    target, persisted_path = _save_object_dict(
        garden_root=garden_root_path,
        manifest=manifest,
        model_identifier=str(resolved_model_target["model_identifier"]),
        object_type="story",
        object_identifier=resolved_identifier,
        object_dict=object_dict,
        parent=parent,
    )
    return _created_object_response(
        object_dict=object_dict,
        target=target,
        garden_id=manifest.garden_id,
        model_target=resolved_model_target,
        persisted_path=persisted_path,
        operation="create_dragonfly_story",
        message=f"Created Dragonfly Story: {resolved_identifier}",
    )


def create_dragonfly_building(
    *,
    garden_root: str,
    story_targets: list[dict[str, Any]] | None = None,
    identifier: str | None = None,
    model_target: dict[str, Any] | None = None,
    sort_stories: bool = True,
    display_name: str | None = None,
) -> dict[str, Any]:
    """Create a Dragonfly Building in a model from Story targets."""
    if not story_targets:
        raise ValueError(
            "create_dragonfly_building requires story_targets. Pass the "
            "story_target values returned by create_dragonfly_story."
        )
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    normalized_story_targets = [
        normalize_dragonfly_object_target(
            _target_from_response(target, "story"),
            expected_type="story",
        )
        for target in story_targets
    ]
    stories = [
        Story.from_dict(_load_object_dict(garden_root_path, target))
        for target in normalized_story_targets
    ]
    resolved_identifier = identifier or _identifier_from_display_name(display_name)
    if resolved_identifier is not None:
        resolved_identifier = _clean_dragonfly_identifier(resolved_identifier)
    if resolved_identifier is None:
        raise ValueError("create_dragonfly_building requires identifier or display_name.")
    building = Building(
        resolved_identifier,
        unique_stories=stories,
        sort_stories=sort_stories,
    )
    if display_name:
        building.display_name = display_name
    separate_building_top_bottom_stories(building)
    objects_to_add = [("building", building.identifier)]
    for story in building.unique_stories:
        objects_to_add.append(("story", story.identifier))
        for room in story.room_2ds:
            objects_to_add.append(("room2d", room.identifier))
    _ensure_unique_model_objects(model, objects_to_add)
    model.add_building(building)
    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    target = make_dragonfly_object_target(
        garden_id=manifest.garden_id,
        model_identifier=str(updated_model_target["model_identifier"]),
        object_type="building",
        object_identifier=resolved_identifier,
    )
    response = _created_object_response(
        object_dict=building.to_dict(),
        target=target,
        garden_id=manifest.garden_id,
        model_target=updated_model_target,
        persisted_path=persisted_path,
        operation="create_dragonfly_building",
        message=f"Created Dragonfly Building: {resolved_identifier}",
    )
    response["summary_view"]["story_count"] = len(building.unique_stories)
    return response
