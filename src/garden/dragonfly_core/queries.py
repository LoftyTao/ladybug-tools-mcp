"""Compact Dragonfly geometry query services."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from dragonfly.model import Model

from garden.dragonfly_core.model_io import load_dragonfly_model, resolve_model_target
from garden.dragonfly_core.targets import (
    make_dragonfly_object_target,
    normalize_dragonfly_object_target,
)
from garden.manifest import GardenManifest
from ladybug_tools_mcp.contracts.report import make_report


DEFAULT_GEOMETRY_ATTRIBUTES = [
    "floor_area",
    "footprint_area",
    "volume",
    "height",
    "floor_height",
    "floor_to_floor_height",
    "floor_to_ceiling_height",
    "exterior_wall_area",
    "exterior_aperture_area",
    "multiplier",
]

ROOM2D_ATTRIBUTE_CATALOG = [
    {
        "name": "identifier",
        "type_hint": "string",
        "operators": ["equals", "contains"],
        "description": "Stable Dragonfly Room2D identifier.",
    },
    {
        "name": "display_name",
        "type_hint": "string",
        "operators": ["equals", "contains"],
        "description": "Optional user-facing Dragonfly Room2D display name.",
    },
    {
        "name": "floor_area",
        "type_hint": "number",
        "operators": ["equals", "gt", "lt", "gte", "lte"],
        "description": "Room2D floor area.",
    },
    {
        "name": "footprint_area",
        "type_hint": "number",
        "operators": ["equals", "gt", "lt", "gte", "lte"],
        "description": "Room2D footprint area.",
    },
    {
        "name": "volume",
        "type_hint": "number",
        "operators": ["equals", "gt", "lt", "gte", "lte"],
        "description": "Room2D volume.",
    },
    {
        "name": "floor_height",
        "type_hint": "number",
        "operators": ["equals", "gt", "lt", "gte", "lte"],
        "description": "Room2D floor elevation.",
    },
    {
        "name": "floor_to_ceiling_height",
        "type_hint": "number",
        "operators": ["equals", "gt", "lt", "gte", "lte"],
        "description": "Room2D floor-to-ceiling height.",
    },
    {
        "name": "is_ground_contact",
        "type_hint": "boolean",
        "operators": ["equals"],
        "description": "Whether the Room2D floor is ground-contact.",
    },
    {
        "name": "is_top_exposed",
        "type_hint": "boolean",
        "operators": ["equals"],
        "description": "Whether the Room2D ceiling is top-exposed.",
    },
]

SUPPORTED_ROOM2D_ATTRIBUTES = {
    record["name"]: record for record in ROOM2D_ATTRIBUTE_CATALOG
}
ATTRIBUTE_OPERATORS = {"equals", "contains", "gt", "lt", "gte", "lte"}


def _garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def _display_name(obj: Any) -> str | None:
    value = getattr(obj, "display_name", None)
    return str(value) if value is not None else None


def _compact_value(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, (list, tuple)):
        compact_items = [_compact_value(item) for item in value]
        if all(item is not None for item in compact_items):
            return compact_items
    return None


def _attribute_value(obj: Any, attribute: str) -> Any:
    if attribute == "identifier":
        return str(getattr(obj, "identifier", ""))
    if attribute == "display_name":
        return _display_name(obj)
    try:
        value = getattr(obj, attribute)
    except AttributeError:
        return None
    if callable(value):
        return None
    return _compact_value(value)


def _selection(
    *,
    garden_id: str,
    model_identifier: str,
    object_targets: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "target_type": "dragonfly_selection",
        "garden_id": garden_id,
        "domain": "dragonfly",
        "model_identifier": model_identifier,
        "object_targets": object_targets,
    }


def _unsupported_attribute_response(
    *,
    manifest: GardenManifest,
    model_target: dict[str, Any],
    attribute: str,
) -> dict[str, Any]:
    available = sorted(SUPPORTED_ROOM2D_ATTRIBUTES)
    return {
        "values": [],
        "groups": [],
        "matches": [],
        "selection": _selection(
            garden_id=manifest.garden_id,
            model_identifier=str(model_target["model_identifier"]),
            object_targets=[],
        ),
        "summary_view": {
            "garden_target": manifest.target(),
            "model_target": model_target,
            "attribute": attribute,
            "match_count": 0,
            "available_attributes": available,
        },
        "report": make_report(
            status="blocked",
            message=(
                f"Dragonfly Room2D attribute is not exposed for compact "
                f"attribute grouping: {attribute}."
            ),
            details={"available_attributes": available},
        ),
    }


def _coerce_compare_value(raw_value: Any, sample_value: Any) -> Any:
    if isinstance(sample_value, bool):
        if isinstance(raw_value, str):
            return raw_value.strip().lower() in {"true", "1", "yes"}
        return bool(raw_value)
    if isinstance(sample_value, (int, float)):
        return float(raw_value)
    if raw_value is None:
        return None
    return str(raw_value)


def _matches_operator(value: Any, operator: str | None, expected: Any) -> bool:
    if operator is None:
        return True
    op = operator.strip().lower()
    if op not in ATTRIBUTE_OPERATORS:
        raise ValueError("operator must be equals, contains, gt, lt, gte, or lte.")
    if op == "contains":
        return str(expected or "").lower() in str(value or "").lower()
    compare_value = _coerce_compare_value(expected, value)
    if op == "equals":
        if isinstance(value, str):
            return value.lower() == str(compare_value or "").lower()
        return value == compare_value
    if value is None or compare_value is None:
        return False
    if op == "gt":
        return value > compare_value
    if op == "lt":
        return value < compare_value
    if op == "gte":
        return value >= compare_value
    if op == "lte":
        return value <= compare_value
    return False


def _sort_key(value: Any) -> tuple[str, str]:
    return (value.__class__.__name__, str(value))


def _group_matches(matches: list[dict[str, Any]]) -> tuple[list[Any], list[dict[str, Any]]]:
    grouped: dict[str, dict[str, Any]] = {}
    for match in matches:
        value = match["value"]
        key = str(value)
        if key not in grouped:
            grouped[key] = {
                "value": value,
                "count": 0,
                "matches": [],
                "object_targets": [],
            }
        grouped[key]["count"] += 1
        grouped[key]["matches"].append(match)
        grouped[key]["object_targets"].append(match["target"])
    groups = sorted(grouped.values(), key=lambda item: _sort_key(item["value"]))
    values = [group["value"] for group in groups]
    return values, groups


def _properties(obj: Any, attributes: list[str]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for attribute in attributes:
        value = _attribute_value(obj, attribute)
        if value is not None:
            values[attribute] = value
    return values


def _iter_model_objects(
    model: Model,
    *,
    garden_id: str,
    model_identifier: str,
) -> Iterable[tuple[Any, dict[str, Any], dict[str, str]]]:
    for building in model.buildings:
        building_parent: dict[str, str] = {}
        yield (
            building,
            make_dragonfly_object_target(
                garden_id=garden_id,
                model_identifier=model_identifier,
                object_type="building",
                object_identifier=building.identifier,
                parent=building_parent,
            ),
            building_parent,
        )
        for story in building.unique_stories:
            story_parent = {"building_identifier": building.identifier}
            yield (
                story,
                make_dragonfly_object_target(
                    garden_id=garden_id,
                    model_identifier=model_identifier,
                    object_type="story",
                    object_identifier=story.identifier,
                    parent=story_parent,
                ),
                story_parent,
            )
            for room in story.room_2ds:
                room_parent = {
                    "building_identifier": building.identifier,
                    "story_identifier": story.identifier,
                }
                yield (
                    room,
                    make_dragonfly_object_target(
                        garden_id=garden_id,
                        model_identifier=model_identifier,
                        object_type="room2d",
                        object_identifier=room.identifier,
                        parent=room_parent,
                    ),
                    room_parent,
                )
    for shade in model.context_shades:
        shade_parent: dict[str, str] = {}
        yield (
            shade,
            make_dragonfly_object_target(
                garden_id=garden_id,
                model_identifier=model_identifier,
                object_type="context_shade",
                object_identifier=shade.identifier,
                parent=shade_parent,
            ),
            shade_parent,
        )


def _model_target_from_object_target(
    manifest: GardenManifest,
    target: dict[str, Any],
) -> dict[str, Any] | None:
    model_identifier = target.get("model_identifier")
    for candidate in manifest.models:
        if (
            candidate.get("domain") == "dragonfly"
            and candidate.get("model_identifier") == model_identifier
        ):
            return candidate
    return None


def _resolve_query_model(
    garden_root_path: Path,
    *,
    target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
) -> tuple[GardenManifest, dict[str, Any], Model, dict[str, Any] | None]:
    if target is None:
        manifest, resolved_model_target = resolve_model_target(
            garden_root_path,
            model_target,
        )
        model = load_dragonfly_model(garden_root_path, resolved_model_target)
        return manifest, resolved_model_target, model, None

    object_target = normalize_dragonfly_object_target(target)
    manifest = GardenManifest.read(garden_root_path)
    resolved_model_target = model_target or _model_target_from_object_target(
        manifest,
        object_target,
    )
    if resolved_model_target is None:
        raise ValueError(
            "Dragonfly object target model is not saved in this Garden manifest."
        )
    _manifest, resolved_model_target = resolve_model_target(
        garden_root_path,
        resolved_model_target,
    )
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    return manifest, resolved_model_target, model, object_target


def _target_matches(candidate: dict[str, Any], target: dict[str, Any] | None) -> bool:
    if target is None:
        return True
    return (
        candidate.get("object_type") == target.get("object_type")
        and candidate.get("object_identifier") == target.get("object_identifier")
        and candidate.get("model_identifier") == target.get("model_identifier")
    )


def get_dragonfly_geometry_properties(
    *,
    garden_root: str,
    target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
    attributes: list[str] | None = None,
) -> dict[str, Any]:
    """Return compact geometry property records for Dragonfly model objects."""
    garden_root_path = _garden_root(garden_root)
    manifest, resolved_model_target, model, object_target = _resolve_query_model(
        garden_root_path,
        target=target,
        model_target=model_target,
    )
    requested_attributes = attributes or DEFAULT_GEOMETRY_ATTRIBUTES
    model_identifier = str(resolved_model_target["model_identifier"])
    matches: list[dict[str, Any]] = []
    for obj, candidate_target, parent in _iter_model_objects(
        model,
        garden_id=manifest.garden_id,
        model_identifier=model_identifier,
    ):
        if not _target_matches(candidate_target, object_target):
            continue
        properties = _properties(obj, requested_attributes)
        if not properties:
            continue
        matches.append(
            {
                "target": candidate_target,
                "object_type": candidate_target["object_type"],
                "identifier": obj.identifier,
                "display_name": _display_name(obj),
                "parent": parent,
                "properties": properties,
            }
        )

    return {
        "matches": matches,
        "summary_view": {
            "garden_target": manifest.target(),
            "model_target": resolved_model_target,
            "target": object_target,
            "attributes": requested_attributes,
            "record_count": len(matches),
        },
        "report": make_report(
            status="ok",
            message=f"Returned {len(matches)} Dragonfly geometry property record(s).",
        ),
    }


def query_dragonfly_room2ds_by_attribute(
    *,
    garden_root: str,
    attribute: str,
    model_target: dict[str, Any] | None = None,
    operator: str | None = None,
    value: Any = None,
) -> dict[str, Any]:
    """Return Room2D targets, grouped values, and optional screened matches."""
    if not attribute or not str(attribute).strip():
        raise ValueError("attribute is required.")
    requested_attribute = str(attribute).strip()
    garden_root_path = _garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    if requested_attribute not in SUPPORTED_ROOM2D_ATTRIBUTES:
        return _unsupported_attribute_response(
            manifest=manifest,
            model_target=resolved_model_target,
            attribute=requested_attribute,
        )
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    model_identifier = str(resolved_model_target["model_identifier"])
    matches: list[dict[str, Any]] = []
    for obj, target, parent in _iter_model_objects(
        model,
        garden_id=manifest.garden_id,
        model_identifier=model_identifier,
    ):
        if target["object_type"] != "room2d":
            continue
        room_value = _attribute_value(obj, requested_attribute)
        if room_value is None:
            continue
        if not _matches_operator(room_value, operator, value):
            continue
        matches.append(
            {
                "target": target,
                "identifier": obj.identifier,
                "display_name": _display_name(obj),
                "parent": parent,
                "attribute": requested_attribute,
                "value": room_value,
            }
        )
    values, groups = _group_matches(matches)

    return {
        "values": values,
        "groups": groups,
        "matches": matches,
        "selection": _selection(
            garden_id=manifest.garden_id,
            model_identifier=model_identifier,
            object_targets=[match["target"] for match in matches],
        ),
        "summary_view": {
            "garden_target": manifest.target(),
            "model_target": resolved_model_target,
            "attribute": requested_attribute,
            "operator": operator,
            "value": value,
            "match_count": len(matches),
            "value_count": len(values),
        },
        "report": make_report(
            status="ok",
            message=(
                f"Found {len(matches)} Dragonfly Room2D value(s) for "
                f"{requested_attribute}."
            ),
        ),
    }


def list_dragonfly_room2d_attributes(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """List compact Room2D attributes supported by DF_room2ds_by_attribute."""
    garden_root_path = _garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    attributes = [dict(record) for record in ROOM2D_ATTRIBUTE_CATALOG]
    return {
        "attributes": attributes,
        "summary_view": {
            "garden_target": manifest.target(),
            "model_target": resolved_model_target,
            "attribute_count": len(attributes),
        },
        "report": make_report(
            status="ok",
            message=f"Returned {len(attributes)} Dragonfly Room2D attribute(s).",
        ),
    }
