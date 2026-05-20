"""Dragonfly model object search services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from dragonfly.room2d import Room2D
from dragonfly.story import Story
from dragonfly.model import Model

from garden.dragonfly_core.model_io import load_dragonfly_model, resolve_model_target
from garden.dragonfly_core.targets import (
    is_dragonfly_object_target,
    make_dragonfly_object_target,
    normalize_dragonfly_object_target,
)
from ladybug_tools_mcp.contracts.report import make_report


SUPPORTED_OBJECT_TYPES = {"all", "building", "story", "room2d", "context_shade"}


def _query_tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    normalized = value.lower().replace("_", " ").replace("-", " ")
    return {token for token in normalized.split() if token}


def _identifier_matches(actual: Any, expected: str | None) -> bool:
    if expected is None:
        return True
    return str(actual or "") == expected


def _display_name(obj: Any) -> str | None:
    value = getattr(obj, "display_name", None)
    return str(value) if value is not None else None


def _text_matches(obj: Any, query: str | None) -> bool:
    tokens = _query_tokens(query)
    if not tokens:
        return True
    searchable = " ".join(
        item
        for item in [
            getattr(obj, "identifier", None),
            _display_name(obj),
            getattr(obj, "type", None),
        ]
        if item
    )
    return tokens.issubset(_query_tokens(searchable))


def _geometry_summary(geometry: Any) -> dict[str, Any] | None:
    if geometry is None:
        return None
    try:
        geometry_dict = geometry.to_dict()
    except Exception:  # pragma: no cover - SDK defensive boundary
        return None
    boundary = geometry_dict.get("boundary")
    if not isinstance(boundary, (list, tuple)):
        return None
    summary: dict[str, Any] = {
        "type": geometry.__class__.__name__,
        "boundary": [_round_triplet(point) for point in boundary],
    }
    area = getattr(geometry, "area", None)
    if area is not None:
        summary["area"] = round(float(area), 6)
    return summary


def _round_triplet(point: Any) -> list[float]:
    return [round(float(point[index]), 6) for index in range(3)]


def _child_counts(obj: Any, object_type: str) -> dict[str, int] | None:
    if object_type == "building":
        stories = list(getattr(obj, "unique_stories", []) or [])
        return {
            "stories": len(stories),
            "room2ds": sum(len(getattr(story, "room_2ds", []) or []) for story in stories),
        }
    if object_type == "story":
        return {"room2ds": len(getattr(obj, "room_2ds", []) or [])}
    return None


def _metadata(obj: Any, object_type: str, include_geometry: bool) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for attr in (
        "floor_area",
        "footprint_area",
        "volume",
        "floor_height",
        "floor_to_floor_height",
        "floor_to_ceiling_height",
        "multiplier",
        "type",
    ):
        value = getattr(obj, attr, None)
        if value is not None:
            metadata[attr] = value
    child_counts = _child_counts(obj, object_type)
    if child_counts is not None:
        metadata["child_counts"] = child_counts
    if include_geometry:
        geometry = _geometry_summary(getattr(obj, "floor_geometry", None))
        if geometry is not None:
            metadata["geometry"] = geometry
    return metadata


def _scope_filter(
    children_scope: dict[str, Any] | None,
) -> tuple[str, str] | None:
    if children_scope is None:
        return None
    target = normalize_dragonfly_object_target(children_scope)
    return target["object_type"], target["object_identifier"]


def _scope_matches(parent: dict[str, str], scope: tuple[str, str] | None) -> bool:
    if scope is None:
        return True
    scope_type, identifier = scope
    if scope_type == "building":
        return parent.get("building_identifier") == identifier
    if scope_type == "story":
        return parent.get("story_identifier") == identifier
    return False


def _iter_dragonfly_objects(
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


def _draft_object_type_dir(object_type: str) -> str:
    return object_type.replace("_", "")


def _load_draft_object(object_type: str, object_path: Path) -> Any:
    object_dict = json.loads(object_path.read_text(encoding="utf-8"))
    if object_type == "room2d":
        return Room2D.from_dict(object_dict)
    if object_type == "story":
        return Story.from_dict(object_dict)
    return None


def _iter_draft_objects(
    *,
    garden_root: Path,
    garden_id: str,
    model_identifier: str,
    embedded_keys: set[tuple[str, str]],
) -> Iterable[tuple[Any, dict[str, Any], dict[str, str]]]:
    object_root = garden_root / "models" / "dragonfly" / "objects" / model_identifier
    for object_type in ("room2d", "story"):
        object_dir = object_root / _draft_object_type_dir(object_type)
        if not object_dir.exists():
            continue
        for object_path in sorted(object_dir.glob("*.json")):
            obj = _load_draft_object(object_type, object_path)
            if obj is None:
                continue
            key = (object_type, obj.identifier)
            if key in embedded_keys:
                continue
            target = make_dragonfly_object_target(
                garden_id=garden_id,
                model_identifier=model_identifier,
                object_type=object_type,
                object_identifier=obj.identifier,
                path=object_path.relative_to(garden_root).as_posix(),
            )
            yield obj, target, {}


def search_dragonfly_model_objects(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    object_type: str = "all",
    identifier: str | None = None,
    query: str | None = None,
    building_identifier: str | None = None,
    story_identifier: str | None = None,
    children_scope: dict[str, Any] | None = None,
    include_geometry: bool = False,
) -> dict[str, Any]:
    """Search Dragonfly objects by type and compact identifier/display-name query."""
    object_type = str(object_type or "all").strip().lower()
    if object_type not in SUPPORTED_OBJECT_TYPES:
        raise ValueError(
            "object_type must be one of all, building, story, room2d, or "
            "context_shade."
        )
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    scope = _scope_filter(children_scope)
    matches: list[dict[str, Any]] = []
    model_identifier = str(resolved_model_target["model_identifier"])
    embedded_items = list(
        _iter_dragonfly_objects(
            model,
            garden_id=manifest.garden_id,
            model_identifier=model_identifier,
        )
    )
    embedded_keys = {
        (target["object_type"], target["object_identifier"])
        for _obj, target, _parent in embedded_items
    }
    all_items = [
        *embedded_items,
        *_iter_draft_objects(
            garden_root=garden_root_path,
            garden_id=manifest.garden_id,
            model_identifier=model_identifier,
            embedded_keys=embedded_keys,
        ),
    ]
    for obj, target, parent in all_items:
        if object_type != "all" and target["object_type"] != object_type:
            continue
        if building_identifier is not None and target["object_type"] == "building":
            if not _identifier_matches(obj.identifier, building_identifier):
                continue
        elif building_identifier is not None:
            if parent.get("building_identifier") != building_identifier:
                continue
        if story_identifier is not None and target["object_type"] == "story":
            if not _identifier_matches(obj.identifier, story_identifier):
                continue
        elif story_identifier is not None:
            if parent.get("story_identifier") != story_identifier:
                continue
        if not _scope_matches(parent, scope):
            continue
        display_name = _display_name(obj)
        if (
            identifier is not None
            and not _identifier_matches(obj.identifier, identifier)
            and display_name != identifier
        ):
            continue
        if not _text_matches(obj, query):
            continue
        matches.append(
            {
                "target": target,
                "object_type": target["object_type"],
                "identifier": obj.identifier,
                "display_name": display_name,
                "parent": parent,
                "matched_fields": [{"field": "identifier", "value": obj.identifier}],
                **_metadata(obj, target["object_type"], include_geometry),
            }
        )

    result: dict[str, Any] = {
        "matches": matches,
        "summary_view": {
            "garden_target": manifest.target(),
            "model_target": resolved_model_target,
            "object_type": object_type,
            "identifier": identifier,
            "query": query,
            "building_identifier": building_identifier,
            "story_identifier": story_identifier,
            "children_scope": children_scope,
            "include_geometry": include_geometry,
            "count": len(matches),
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(matches)} Dragonfly object(s).",
        ),
    }
    if len(matches) == 1:
        result["target"] = matches[0]["target"]
    return result
