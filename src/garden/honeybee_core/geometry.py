"""Honeybee geometry parsing helpers."""

from __future__ import annotations

from typing import Any

from honeybee.aperture import Aperture
from honeybee.door import Door
from honeybee.face import Face
from honeybee.model import Model
from honeybee.room import Room
from honeybee.shade import Shade
from ladybug_geometry.geometry2d.pointvector import Vector2D
from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.plane import Plane
from ladybug_geometry.geometry3d.polyface import Polyface3D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D

GEOMETRY_TOLERANCE = 0.01
ANGLE_TOLERANCE = 1.0
FACE3D_INPUT_HINT = (
    "Use a Ladybug Geometry Face3D dict like "
    "{'type': 'Face3D', 'boundary': [[x, y, z], ...]}; boundary may also "
    "contain {'x': x, 'y': y, 'z': z} Point3D dictionaries. Omit 'plane' "
    "unless it uses Ladybug Plane keys 'n', 'o', and optional 'x'."
)


def face3d_from_dict(data: dict[str, Any]) -> Face3D:
    """Parse a Ladybug Geometry Face3D dict."""
    if not isinstance(data, dict):
        raise ValueError(f"Geometry must be a Face3D dictionary. {FACE3D_INPUT_HINT}")
    if data.get("type") != "Face3D":
        raise ValueError(f"Geometry must be a Ladybug Geometry Face3D dictionary. {FACE3D_INPUT_HINT}")
    if "boundary" not in data and "vertices" not in data:
        raise ValueError(f"Face3D geometry must include a 'boundary' field. {FACE3D_INPUT_HINT}")

    normalized = dict(data)
    normalized["boundary"] = _normalize_point_boundary(
        data.get("boundary", data.get("vertices")),
        field_name="boundary",
    )
    if "holes" in normalized:
        normalized["holes"] = [
            _normalize_point_boundary(hole, field_name=f"holes[{index}]")
            for index, hole in enumerate(normalized["holes"])
        ]
    plane = _normalize_face3d_plane(normalized.get("plane"))
    if plane is None:
        normalized.pop("plane", None)
    else:
        normalized["plane"] = plane

    try:
        return Face3D.from_dict(normalized)
    except Exception as exc:  # pragma: no cover - SDK-raised shape diagnostics
        raise ValueError(f"Could not parse Face3D geometry. {FACE3D_INPUT_HINT} Details: {exc}") from exc


def _normalize_point_boundary(data: Any, *, field_name: str) -> list[list[float]]:
    if not isinstance(data, list) or len(data) < 3:
        raise ValueError(
            f"Face3D {field_name} must be a list of at least three [x, y, z] points. "
            f"{FACE3D_INPUT_HINT}"
        )
    return [
        _normalize_xyz(point, field_name=f"{field_name}[{index}]")
        for index, point in enumerate(data)
    ]


def _normalize_xyz(data: Any, *, field_name: str) -> list[float]:
    if isinstance(data, dict):
        try:
            data = [data["x"], data["y"], data["z"]]
        except KeyError as exc:
            raise ValueError(
                f"Face3D {field_name} must include x, y, and z coordinates. "
                f"{FACE3D_INPUT_HINT}"
            ) from exc
    if not isinstance(data, (list, tuple)) or len(data) != 3:
        raise ValueError(
            f"Face3D {field_name} must be a [x, y, z] coordinate triplet. "
            f"{FACE3D_INPUT_HINT}"
        )
    try:
        return [float(data[0]), float(data[1]), float(data[2])]
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Face3D {field_name} coordinates must be numbers. {FACE3D_INPUT_HINT}"
        ) from exc


def _normalize_face3d_plane(data: Any) -> dict[str, Any] | None:
    """Normalize common Agent-written Plane dictionaries or let Face3D infer it."""
    if not isinstance(data, dict) or data.get("type") not in {None, "Plane"}:
        return None
    if "n" not in data or "o" not in data:
        return None
    try:
        normalized = {
            "type": "Plane",
            "n": _normalize_xyz(data["n"], field_name="plane.n"),
            "o": _normalize_xyz(data["o"], field_name="plane.o"),
        }
        x_axis = data.get("x", data.get("u"))
        if x_axis is not None:
            normalized["x"] = _normalize_xyz(x_axis, field_name="plane.x")
        return normalized
    except ValueError:
        return None


def polyface3d_from_dict(data: dict[str, Any]) -> Polyface3D:
    """Parse a Ladybug Geometry Polyface3D dict."""
    if data.get("type") != "Polyface3D":
        raise ValueError("Room geometry must be a Ladybug Geometry Polyface3D dictionary.")
    if "vertices" not in data or "face_indices" not in data:
        raise ValueError("Polyface3D geometry must include 'vertices' and 'face_indices'.")
    return Polyface3D.from_dict(data)


def point3d_from_dict(data: dict[str, Any]) -> Point3D:
    """Parse a Ladybug Geometry Point3D dict."""
    if data.get("type") not in {None, "Point3D"}:
        raise ValueError("Point input must be a Ladybug Geometry Point3D dictionary.")
    return Point3D.from_dict(data)


def vector3d_from_dict(data: dict[str, Any]) -> Vector3D:
    """Parse a Ladybug Geometry Vector3D dict."""
    if data.get("type") not in {None, "Vector3D"}:
        raise ValueError("Vector input must be a Ladybug Geometry Vector3D dictionary.")
    return Vector3D.from_dict(data)


def vector2d_from_input(data: dict[str, Any] | list[float] | tuple[float, float]) -> Vector2D:
    """Parse a Ladybug Geometry Vector2D from a dict or two-number array."""
    if isinstance(data, dict):
        if data.get("type") not in {None, "Vector2D"}:
            raise ValueError("contour_vector must be a Ladybug Geometry Vector2D dictionary.")
        return Vector2D.from_dict(data)
    return Vector2D.from_array(data)


def plane_from_dict(data: dict[str, Any]) -> Plane:
    """Parse a Ladybug Geometry Plane dict."""
    if data.get("type") not in {None, "Plane"}:
        raise ValueError("Plane input must be a Ladybug Geometry Plane dictionary.")
    return Plane.from_dict(data)


def validate_honeybee_face(face: Face) -> None:
    """Validate face geometry before it is persisted."""
    _run_check(face.check_planar, "Honeybee Face must be planar.")
    _run_check(
        face.check_self_intersecting,
        "Honeybee Face must not be self-intersecting.",
    )


def validate_honeybee_aperture(aperture: Aperture) -> None:
    """Validate aperture geometry before it is attached or persisted."""
    _run_check(aperture.check_planar, "Honeybee Aperture must be planar.")
    _run_check(
        aperture.check_self_intersecting,
        "Honeybee Aperture must not be self-intersecting.",
    )


def validate_honeybee_door(door: Door) -> None:
    """Validate door geometry before it is attached or persisted."""
    _run_check(door.check_planar, "Honeybee Door must be planar.")
    _run_check(
        door.check_self_intersecting,
        "Honeybee Door must not be self-intersecting.",
    )


def validate_honeybee_shade(shade: Shade) -> None:
    """Validate shade geometry before it is attached or persisted."""
    _run_check(shade.check_planar, "Honeybee Shade must be planar.")
    _run_check(
        shade.check_self_intersecting,
        "Honeybee Shade must not be self-intersecting.",
    )


def validate_honeybee_room(room: Room) -> None:
    """Validate room geometry before it is persisted."""
    _run_check(room.check_planar, "Honeybee Room geometry must be planar.")
    _run_check(
        room.check_self_intersecting,
        "Honeybee Room geometry must not be self-intersecting.",
    )
    _run_check(room.check_solid, "Honeybee Room must be a closed solid.")
    _run_check(
        room.check_sub_faces_valid,
        "Honeybee Room sub-faces must be co-planar with parent faces and stay within face boundaries.",
    )
    _run_check(
        room.check_sub_faces_overlapping,
        "Honeybee Room sub-faces must not overlap.",
    )


def validate_face_sub_faces(face: Face) -> None:
    """Validate all sub-face relationships on a face after mutation."""
    _run_check(
        face.check_apertures_valid,
        "Honeybee Apertures must be co-planar with the parent Face and stay within its boundary.",
    )
    _run_check(
        face.check_doors_valid,
        "Honeybee Doors must be co-planar with the parent Face and stay within its boundary.",
    )
    _run_check(
        face.check_sub_faces_overlapping,
        "Honeybee sub-faces must not overlap on the same parent Face.",
    )


def validate_model_adjacency(model: Model) -> None:
    """Validate adjacency area consistency for models that include Surface pairs."""
    _run_check(
        model.check_matching_adjacent_areas,
        "Adjacent Honeybee faces and sub-faces with Surface boundary conditions must have matching areas.",
    )


def _run_check(check_fn, message: str) -> None:
    try:
        check_fn(
            tolerance=GEOMETRY_TOLERANCE,
            angle_tolerance=ANGLE_TOLERANCE,
            raise_exception=True,
        )
    except TypeError:
        check_fn(
            tolerance=GEOMETRY_TOLERANCE,
            raise_exception=True,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"{message} {exc}") from exc
