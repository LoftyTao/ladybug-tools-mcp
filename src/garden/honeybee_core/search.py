"""Honeybee model search services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ladybug_tools_mcp.contracts.report import make_report
from garden.honeybee_core.locate import iter_honeybee_objects
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target,
)
from garden.honeybee_core.targets import (
    is_honeybee_model_target,
    is_honeybee_object_target,
    normalize_honeybee_object_target,
)


def _query_tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    normalized = value.lower().replace("_", " ").replace("-", " ")
    return {token for token in normalized.split() if token}


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
    geometry_summary = _face3d_geometry_summary(geometry)
    if geometry_summary is not None:
        metadata["geometry_type"] = "Face3D"
        metadata["geometry"] = geometry_summary
        metadata["vertices"] = geometry_summary["boundary"]
    if obj.__class__.__name__ == "Room":
        energy_summary = _room_energy_properties_summary(obj)
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


def _scope_from_shorthand(children_scope: dict[str, Any]) -> tuple[str, str] | None:
    for scope_type in ("room", "face", "aperture", "door"):
        value = children_scope.get(scope_type)
        if isinstance(value, str) and value:
            return scope_type, value
    scope_type = children_scope.get("object_type") or children_scope.get("type")
    identifier = children_scope.get("object_identifier") or children_scope.get(
        "identifier"
    )
    if isinstance(scope_type, str) and isinstance(identifier, str):
        return scope_type.lower(), identifier
    if isinstance(identifier, str):
        return "any", identifier
    return None


def _children_scope_matches(
    target: dict[str, Any],
    children_scope: dict[str, Any] | str | bool | None,
) -> bool:
    if children_scope is None or isinstance(children_scope, bool):
        return True
    if isinstance(children_scope, str):
        children_scope = {"identifier": children_scope}
    if is_honeybee_model_target(children_scope):
        return target.get("model_identifier") == children_scope.get("model_identifier")

    shorthand_scope = _scope_from_shorthand(children_scope)
    if shorthand_scope is None:
        scope_target = normalize_honeybee_object_target(children_scope)
        scope_type = scope_target["object_type"]
        scope_identifier = scope_target["object_identifier"]
    else:
        scope_type, scope_identifier = shorthand_scope
    parent = target.get("parent") or {}
    parent_key_by_scope = {
        "room": "room_identifier",
        "face": "face_identifier",
        "aperture": "aperture_identifier",
        "door": "door_identifier",
    }
    parent_key = parent_key_by_scope.get(scope_type)
    if scope_type == "any":
        return any(
            _identifier_matches(value, scope_identifier) for value in parent.values()
        )
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
    children_scope: dict[str, Any] | str | bool | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Search Honeybee objects by type and simple identifier/display-name query."""
    if limit is not None and limit < 1:
        raise ValueError("limit must be greater than zero when provided.")
    original_object_type = object_type
    object_type = _canonical_object_type(object_type)
    supported_object_types = {"all", "room", "face", "aperture", "door", "shade"}
    if object_type not in supported_object_types:
        raise ValueError(
            "object_type must be one of all, room, face, aperture, door, or shade. "
            "For Honeybee Energy objects such as program_type, construction_set, "
            "schedule, material, construction, or hvac, use search_energy_library_objects, "
            "create_program_type, create_construction_set, or search_hvac_templates."
        )
    if is_honeybee_object_target(model_target):
        if children_scope is None or isinstance(children_scope, bool):
            children_scope = model_target
        model_target = None
    identifier_filter = identifier
    garden_root = Path(garden_root).expanduser().resolve()
    manifest, model_target = resolve_model_target(garden_root, model_target)
    model = load_honeybee_model(garden_root, model_target)
    query_tokens = _query_tokens(query)
    matches: list[dict[str, Any]] = []
    for obj, target in iter_honeybee_objects(
        model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
    ):
        if object_type != "all" and target["object_type"] != object_type:
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
        if (
            room_identifier is not None
            and target.get("parent", {}).get("room_identifier") != room_identifier
        ):
            continue
        if face_identifier is not None:
            if target["object_type"] == "face":
                if not _identifier_matches(identifier, face_identifier):
                    continue
            elif not _identifier_matches(
                target.get("parent", {}).get("face_identifier"),
                face_identifier,
            ):
                continue
        metadata = _object_metadata(obj)
        child_counts = _object_child_counts(obj, target["object_type"])
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
            "object_type": target["object_type"],
            "identifier": identifier,
            "display_name": display_name,
            "parent": target.get("parent", {}),
            **metadata,
            "matched_fields": [{"field": "identifier", "value": identifier}],
        }
        parent_room = target.get("parent", {}).get("room_identifier")
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
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(matches)} Honeybee object(s).",
        ),
    }
    if len(matches) == 1:
        result["target"] = matches[0]["target"]
    return result


def _canonical_object_type(value: str) -> str:
    normalized = str(value or "all").strip().lower().replace("-", "_")
    aliases = {
        "rooms": "room",
        "faces": "face",
        "wall": "face",
        "walls": "face",
        "window": "aperture",
        "windows": "aperture",
        "opening": "aperture",
        "openings": "aperture",
        "apertures": "aperture",
        "doors": "door",
        "shades": "shade",
    }
    return aliases.get(normalized, normalized)
