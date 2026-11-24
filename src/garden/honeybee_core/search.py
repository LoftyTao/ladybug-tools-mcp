"""Honeybee model search and summary services."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from honeybee.boundarycondition import Outdoors
from honeybee.facetype import Wall

from ladybug_tools_mcp.contracts import make_report
from garden.honeybee_core.locate import iter_honeybee_objects
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target,
)
from garden.honeybee_core.targets import (
    is_honeybee_object_target,
    normalize_honeybee_object_target,
)

COMPASS_SECTORS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
VALID_ORIENTATIONS = (*COMPASS_SECTORS, "horizontal_up", "horizontal_down")
_ORIENTATION_MAP = {value.lower(): value for value in VALID_ORIENTATIONS}
CARDINAL_BUCKETS = ("N", "E", "S", "W", "Other")


def _query_tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    normalized = value.lower().replace("_", " ").replace("-", " ")
    return {token for token in normalized.split() if token}


def _orientation_from_normal(normal: Any) -> str | None:
    """Classify a 3D normal vector into compass sector or horizontal up/down."""
    if normal is None:
        return None
    nx = float(normal.x)
    ny = float(normal.y)
    nz = float(normal.z)
    magnitude = math.sqrt(nx * nx + ny * ny + nz * nz)
    if magnitude == 0.0:
        return None
    nx /= magnitude
    ny /= magnitude
    nz /= magnitude
    if nz >= 0.7:
        return "horizontal_up"
    if nz <= -0.7:
        return "horizontal_down"
    azimuth_deg = math.degrees(math.atan2(nx, ny)) % 360.0
    return COMPASS_SECTORS[int(((azimuth_deg + 22.5) % 360.0) // 45.0)]


def _object_metadata(obj: Any) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if hasattr(obj, "type"):
        metadata["face_type"] = str(getattr(obj, "type"))
    if hasattr(obj, "boundary_condition"):
        metadata["boundary_condition"] = str(getattr(obj, "boundary_condition"))
    geometry = getattr(obj, "geometry", None)
    normal = getattr(geometry, "normal", None)
    if normal is not None:
        metadata["normal"] = {
            "x": round(float(normal.x), 6),
            "y": round(float(normal.y), 6),
            "z": round(float(normal.z), 6),
        }
        metadata["normal_vector"] = [
            metadata["normal"]["x"],
            metadata["normal"]["y"],
            metadata["normal"]["z"],
        ]
        orientation = _orientation_from_normal(normal)
        if orientation is not None:
            metadata["orientation"] = orientation
    geometry_summary = _face3d_geometry_summary(geometry)
    if geometry_summary is not None:
        metadata["geometry_type"] = "Face3D"
        metadata["geometry"] = geometry_summary
        metadata["vertices"] = geometry_summary["boundary"]
        if "area" in geometry_summary:
            metadata["area"] = geometry_summary["area"]
    if obj.__class__.__name__ == "Room":
        if getattr(obj, "story", None) is not None:
            metadata["story"] = obj.story
        if getattr(obj, "zone", None) is not None:
            metadata["zone"] = obj.zone
        metadata["floor_area"] = round(float(obj.floor_area), 6)
        metadata["volume"] = round(float(obj.volume), 6)
        energy_summary = _room_energy_properties_summary(obj)
        if energy_summary:
            metadata["energy_properties"] = energy_summary
    if obj.__class__.__name__ == "Shade":
        energy_summary = _shade_energy_properties_summary(obj)
        if energy_summary:
            metadata["energy_properties"] = energy_summary
    return metadata


def _room_energy_properties_summary(room: Any) -> dict[str, Any]:
    properties = getattr(room, "properties", None)
    energy = getattr(properties, "energy", None)
    if energy is None:
        return {}
    fields = [
        "program_type",
        "construction_set",
        "hvac",
        "ventilation",
        "setpoint",
        "people",
        "lighting",
        "electric_equipment",
        "infiltration",
    ]
    summary: dict[str, Any] = {}
    for field in fields:
        value = getattr(energy, field, None)
        identifier = getattr(value, "identifier", None)
        if identifier:
            summary[field] = identifier
    fans = list(getattr(energy, "fans", []) or [])
    fan_identifiers = [
        str(identifier)
        for fan in fans
        if (identifier := getattr(fan, "identifier", None))
    ]
    if fan_identifiers:
        summary["zone_ventilation_fans"] = fan_identifiers
        summary["zone_ventilation_fan_count"] = len(fan_identifiers)
    summary["has_energy_properties"] = bool(summary)
    return summary


def _shade_energy_properties_summary(shade: Any) -> dict[str, Any]:
    properties = getattr(shade, "properties", None)
    energy = getattr(properties, "energy", None)
    if energy is None:
        return {}
    fields = [
        "construction",
        "transmittance_schedule",
        "pv_properties",
    ]
    summary: dict[str, Any] = {}
    for field in fields:
        value = getattr(energy, field, None)
        identifier = getattr(value, "identifier", None)
        if identifier:
            summary[field] = identifier
            summary[f"{field}_identifier"] = identifier
    summary["has_energy_properties"] = bool(summary)
    return summary


def _face3d_geometry_summary(geometry: Any) -> dict[str, Any] | None:
    if geometry is None or geometry.__class__.__name__ != "Face3D":
        return None
    try:
        face_dict = geometry.to_dict()
    except Exception:  # pragma: no cover - SDK defensive boundary
        return None
    boundary = face_dict.get("boundary")
    if not isinstance(boundary, (list, tuple)):
        return None
    summary: dict[str, Any] = {
        "type": "Face3D",
        "boundary": [_round_triplet(point) for point in boundary],
    }
    area = getattr(geometry, "area", None)
    if area is not None:
        summary["area"] = round(float(area), 6)
    return summary


def _round_triplet(point: Any) -> list[float]:
    return [round(float(point[index]), 6) for index in range(3)]


def _face_child_counts(face: Any) -> dict[str, int]:
    apertures = list(getattr(face, "apertures", []) or [])
    doors = list(getattr(face, "doors", []) or [])
    face_shades = list(getattr(face, "shades", []) or [])
    aperture_shades = [
        shade for aperture in apertures for shade in getattr(aperture, "shades", [])
    ]
    door_shades = [shade for door in doors for shade in getattr(door, "shades", [])]
    return {
        "apertures": len(apertures),
        "doors": len(doors),
        "shades": len(face_shades) + len(aperture_shades) + len(door_shades),
    }


def _object_child_counts(obj: Any, object_type: str) -> dict[str, int] | None:
    if object_type == "room":
        faces = list(getattr(obj, "faces", []) or [])
        face_counts = [_face_child_counts(face) for face in faces]
        room_shades = list(getattr(obj, "shades", []) or [])
        return {
            "faces": len(faces),
            "apertures": sum(count["apertures"] for count in face_counts),
            "doors": sum(count["doors"] for count in face_counts),
            "shades": len(room_shades)
            + sum(count["shades"] for count in face_counts),
        }
    if object_type == "face":
        return _face_child_counts(obj)
    if object_type in {"aperture", "door"}:
        return {"shades": len(getattr(obj, "shades", []) or [])}
    return None


def _semantic_terms(metadata: dict[str, Any]) -> set[str]:
    terms = _query_tokens(" ".join(str(value) for value in metadata.values()))
    if str(metadata.get("boundary_condition", "")).lower() == "outdoors":
        terms.update({"outdoor", "exterior", "external"})
    if str(metadata.get("boundary_condition", "")).lower() == "ground":
        terms.add("ground")
    if str(metadata.get("face_type", "")).lower() == "wall":
        terms.add("wall")
    return terms


def _metadata_value_matches(actual: Any, expected: str | dict[str, Any] | None) -> bool:
    if expected is None:
        return True
    if isinstance(expected, dict):
        expected = str(expected.get("type") or expected.get("name") or "")
    actual_tokens = _query_tokens(str(actual))
    expected_tokens = _query_tokens(str(expected))
    return bool(expected_tokens) and expected_tokens.issubset(actual_tokens)


def _identifier_matches(actual: Any, expected: str | None) -> bool:
    if expected is None:
        return True
    actual_value = str(actual or "")
    return actual_value == expected or actual_value.endswith(f"_{expected}")


def _children_scope_matches(
    target: dict[str, Any],
    children_scope: dict[str, Any] | None,
) -> bool:
    if children_scope is None:
        return True
    scope_target = normalize_honeybee_object_target(children_scope)
    scope_type = scope_target["object_type"]
    scope_identifier = scope_target["object_identifier"]
    parent = target.get("parent") or {}
    parent_key_by_scope = {
        "room": "room_identifier",
        "face": "face_identifier",
        "aperture": "aperture_identifier",
        "door": "door_identifier",
    }
    parent_key = parent_key_by_scope.get(scope_type)
    if parent_key is None:
        return False
    return _identifier_matches(parent.get(parent_key), scope_identifier)


def search_honeybee_model_objects(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    object_type: str = "all",
    identifier: str | None = None,
    room_identifier: str | None = None,
    face_identifier: str | None = None,
    query: str | None = None,
    face_type: str | None = None,
    boundary_condition: str | dict[str, Any] | None = None,
    children_scope: dict[str, Any] | None = None,
    orientation: str | None = None,
    story: str | None = None,
    zone: str | None = None,
    min_area: float | None = None,
    max_area: float | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Search Honeybee objects by type, orientation, story, zone, area, and query."""
    if limit is not None and limit < 1:
        raise ValueError("limit must be greater than zero when provided.")
    original_object_type = object_type
    object_type = str(object_type or "all").strip().lower().replace("-", "_")
    supported_object_types = {"all", "room", "face", "aperture", "door", "shade"}
    if object_type not in supported_object_types:
        raise ValueError(
            "object_type must be one of all, room, face, aperture, door, or shade. "
            "For Honeybee Energy objects such as program_type, construction_set, "
            "schedule, material, construction, or hvac, use search_energy_library_objects, "
            "create_program_type, create_construction_set, or search_hvac_templates."
        )

    orientation_filter: str | None = None
    if orientation is not None:
        orientation_filter = _ORIENTATION_MAP.get(str(orientation).strip().lower())
        if orientation_filter is None:
            raise ValueError(
                f"orientation must be one of {', '.join(VALID_ORIENTATIONS)}."
            )
    if min_area is not None and min_area < 0:
        raise ValueError("min_area must be greater than or equal to 0.")
    if max_area is not None and max_area < 0:
        raise ValueError("max_area must be greater than or equal to 0.")
    if min_area is not None and max_area is not None and min_area > max_area:
        raise ValueError("min_area must be less than or equal to max_area.")

    if is_honeybee_object_target(model_target):
        if children_scope is None:
            children_scope = model_target
        model_target = None
    identifier_filter = identifier
    garden_root = Path(garden_root).expanduser().resolve()
    manifest, model_target = resolve_model_target(garden_root, model_target)
    model = load_honeybee_model(garden_root, model_target)
    rooms_by_id = {room.identifier: room for room in model.rooms}
    query_tokens = _query_tokens(query)
    matches: list[dict[str, Any]] = []
    for obj, target in iter_honeybee_objects(
        model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
    ):
        obj_type = target["object_type"]
        if object_type != "all" and obj_type != object_type:
            continue
        if not _children_scope_matches(target, children_scope):
            continue
        identifier = obj.identifier
        display_name = getattr(obj, "display_name", None)
        if (
            identifier_filter is not None
            and not _identifier_matches(identifier, identifier_filter)
            and display_name != identifier_filter
        ):
            continue
        parent_room = target.get("parent", {}).get("room_identifier")
        if room_identifier is not None and parent_room != room_identifier:
            continue
        if face_identifier is not None:
            if obj_type == "face":
                if not _identifier_matches(identifier, face_identifier):
                    continue
            elif not _identifier_matches(
                target.get("parent", {}).get("face_identifier"),
                face_identifier,
            ):
                continue

        if story is not None:
            obj_story = (
                getattr(obj, "story", None)
                if obj_type == "room"
                else getattr(rooms_by_id.get(parent_room), "story", None)
            )
            if obj_story != story:
                continue
        if zone is not None:
            obj_zone = (
                getattr(obj, "zone", None)
                if obj_type == "room"
                else getattr(rooms_by_id.get(parent_room), "zone", None)
            )
            if obj_zone != zone:
                continue

        if min_area is not None or max_area is not None:
            if obj_type == "room":
                obj_area: float | None = float(obj.floor_area)
            elif hasattr(obj, "area"):
                obj_area = float(obj.area)
            else:
                obj_area = None
            if obj_area is None:
                continue
            if min_area is not None and obj_area < min_area:
                continue
            if max_area is not None and obj_area > max_area:
                continue

        metadata = _object_metadata(obj)
        if orientation_filter is not None:
            allowed_orient_types = (
                {"face", "aperture", "door", "shade"}
                if object_type == "shade"
                else {"face", "aperture", "door"}
            )
            if obj_type not in allowed_orient_types:
                continue
            if metadata.get("orientation") != orientation_filter:
                continue

        child_counts = _object_child_counts(obj, obj_type)
        searchable = " ".join(
            item
            for item in [
                identifier,
                display_name,
                metadata.get("face_type"),
                metadata.get("boundary_condition"),
            ]
            if item
        ).lower()
        searchable_tokens = _query_tokens(searchable) | _semantic_terms(metadata)
        if query_tokens and not query_tokens.issubset(searchable_tokens):
            continue
        if not _metadata_value_matches(metadata.get("face_type"), face_type):
            continue
        if not _metadata_value_matches(
            metadata.get("boundary_condition"), boundary_condition
        ):
            continue
        match = {
            "target": target,
            "object_type": obj_type,
            "identifier": identifier,
            "display_name": display_name,
            "parent": target.get("parent", {}),
            **metadata,
            "matched_fields": [{"field": "identifier", "value": identifier}],
        }
        if isinstance(parent_room, str) and identifier.startswith(f"{parent_room}_"):
            match["local_identifier"] = identifier.removeprefix(f"{parent_room}_")
        if child_counts is not None:
            match["child_counts"] = child_counts
        matches.append(match)
        if limit is not None and len(matches) >= limit:
            break

    result = {
        "matches": matches,
        "summary_view": {
            "garden_target": manifest.target(),
            "model_target": model_target,
            "object_type": object_type,
            "requested_object_type": original_object_type,
            "identifier": identifier_filter,
            "room_identifier": room_identifier,
            "face_identifier": face_identifier,
            "count": len(matches),
            "limit": limit,
            "face_type": face_type,
            "boundary_condition": boundary_condition,
            "children_scope": children_scope,
            "orientation": orientation_filter,
            "story": story,
            "zone": zone,
            "min_area": min_area,
            "max_area": max_area,
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(matches)} Honeybee object(s).",
        ),
    }
    if len(matches) == 1:
        result["target"] = matches[0]["target"]
    return result


def get_honeybee_model_summary(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a compact geometry, WWR, story/zone, Energy, and Radiance summary."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_honeybee_model(garden_root_path, resolved_model_target)

    object_counts = {
        "rooms": len(model.rooms),
        "faces": len(model.faces),
        "apertures": len(model.apertures),
        "doors": len(model.doors),
        "shades": len(model.shades),
        "orphaned_faces": len(model.orphaned_faces),
    }

    total_floor_area = round(float(model.floor_area), 4)
    total_volume = round(float(model.volume), 4)

    buckets: dict[str, dict[str, float | int]] = {
        bucket: {"wall_area": 0.0, "aperture_area": 0.0, "wall_face_count": 0}
        for bucket in CARDINAL_BUCKETS
    }
    ext_wall_area = 0.0
    ext_wall_ap_area = 0.0
    total_ext_ap_area = 0.0

    face_groups: list[tuple[Any, int]] = [
        (room.faces, int(getattr(room, "multiplier", 1) or 1))
        for room in model.rooms
    ]

    for faces, mult in face_groups:
        for face in faces:
            if not isinstance(getattr(face, "boundary_condition", None), Outdoors):
                continue
            ap_area = float(getattr(face, "aperture_area", 0.0) or 0.0) * mult
            total_ext_ap_area += ap_area
            if isinstance(getattr(face, "type", None), Wall):
                w_area = float(getattr(face, "area", 0.0) or 0.0) * mult
                ext_wall_area += w_area
                ext_wall_ap_area += ap_area
                orient = _orientation_from_normal(getattr(face.geometry, "normal", None))
                bucket = orient if orient in {"N", "E", "S", "W"} else "Other"
                buckets[bucket]["wall_area"] += w_area
                buckets[bucket]["aperture_area"] += ap_area
                buckets[bucket]["wall_face_count"] += 1

    overall_wwr = (
        round(ext_wall_ap_area / ext_wall_area, 4) if ext_wall_area > 0 else 0.0
    )
    wwr_by_orientation = {
        bucket: (
            round(float(data["aperture_area"]) / float(data["wall_area"]), 4)
            if float(data["wall_area"]) > 0
            else 0.0
        )
        for bucket, data in buckets.items()
    }
    orientation_breakdown = {
        bucket: {
            "wall_area": round(float(data["wall_area"]), 4),
            "aperture_area": round(float(data["aperture_area"]), 4),
            "wwr": wwr_by_orientation[bucket],
            "wall_face_count": int(data["wall_face_count"]),
        }
        for bucket, data in buckets.items()
    }

    stories = sorted(
        {str(room.story) for room in model.rooms if getattr(room, "story", None)}
    )
    zones = sorted(
        {str(room.zone) for room in model.rooms if getattr(room, "zone", None)}
    )

    model_props = getattr(model, "properties", None)
    model_energy = getattr(model_props, "energy", None)
    program_types = sorted(
        {
            str(obj.identifier)
            for obj in (getattr(model_energy, "program_types", None) or [])
            if getattr(obj, "identifier", None)
        }
    )
    construction_sets = sorted(
        {
            str(obj.identifier)
            for obj in (getattr(model_energy, "construction_sets", None) or [])
            if getattr(obj, "identifier", None)
        }
    )
    hvacs = sorted(
        {
            str(obj.identifier)
            for obj in (getattr(model_energy, "hvacs", None) or [])
            if getattr(obj, "identifier", None)
        }
    )
    setpoints = sorted(
        {
            str(sp.identifier)
            for room in model.rooms
            if (
                sp := getattr(
                    getattr(getattr(room, "properties", None), "energy", None),
                    "setpoint",
                    None,
                )
            )
            is not None
            and getattr(sp, "identifier", None)
        }
    )
    conditioned_room_count = sum(
        1
        for room in model.rooms
        if bool(
            getattr(
                getattr(getattr(room, "properties", None), "energy", None),
                "is_conditioned",
                False,
            )
        )
    )
    energy_summary = {
        "program_types": program_types,
        "construction_sets": construction_sets,
        "hvacs": hvacs,
        "setpoints": setpoints,
        "conditioned_room_count": conditioned_room_count,
        "unconditioned_room_count": len(model.rooms) - conditioned_room_count,
        "has_electric_load_center": getattr(model_energy, "electric_load_center", None)
        is not None,
    }

    model_radiance = getattr(model_props, "radiance", None)
    modifier_sets = sorted(
        {
            str(obj.identifier)
            for obj in (getattr(model_radiance, "modifier_sets", None) or [])
            if getattr(obj, "identifier", None)
        }
    )
    sensor_grids = [
        str(grid.identifier)
        for grid in (getattr(model_radiance, "sensor_grids", None) or [])
        if getattr(grid, "identifier", None)
    ]
    views = [
        str(view.identifier)
        for view in (getattr(model_radiance, "views", None) or [])
        if getattr(view, "identifier", None)
    ]
    radiance_summary = {
        "modifier_sets": modifier_sets,
        "sensor_grids": sensor_grids,
        "views": views,
        "sensor_grid_count": len(sensor_grids),
        "view_count": len(views),
    }

    ext_wall_area_rounded = round(ext_wall_area, 4)
    ext_ap_area_rounded = round(total_ext_ap_area, 4)
    ext_wall_ap_area_rounded = round(ext_wall_ap_area, 4)
    model_identifier = str(resolved_model_target["model_identifier"])

    summary_payload = {
        "garden_target": manifest.target(),
        "model_target": resolved_model_target,
        "model_identifier": model_identifier,
        "display_name": getattr(model, "display_name", None),
        "units": getattr(model, "units", None),
        "tolerance": getattr(model, "tolerance", None),
        "angle_tolerance": getattr(model, "angle_tolerance", None),
        "object_counts": object_counts,
        "total_floor_area": total_floor_area,
        "volume": total_volume,
        "exterior_wall_area": ext_wall_area_rounded,
        "exterior_aperture_area": ext_ap_area_rounded,
        "exterior_wall_aperture_area": ext_wall_ap_area_rounded,
        "overall_wwr": overall_wwr,
        "wwr_by_orientation": wwr_by_orientation,
        "orientation_breakdown": orientation_breakdown,
        "stories": stories,
        "zones": zones,
        "energy": energy_summary,
        "radiance": radiance_summary,
    }

    return {
        "target": resolved_model_target,
        **summary_payload,
        "summary_view": summary_payload,
        "report": make_report(
            status="ok",
            message=(
                f"Summarized Honeybee model {model_identifier}: "
                f"{object_counts['rooms']} room(s), floor area {total_floor_area}, "
                f"overall WWR {overall_wwr}."
            ),
        ),
    }
