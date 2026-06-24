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
    try:
        value = getattr(obj, attribute)
    except AttributeError:
        return None
    if callable(value):
        return None
    return _compact_value(value)


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
) -> dict[str, Any]:
    """Return Room2D targets and compact values for one SDK attribute."""
    if not attribute or not str(attribute).strip():
        raise ValueError("attribute is required.")
    requested_attribute = str(attribute).strip()
    garden_root_path = _garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
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
        value = _attribute_value(obj, requested_attribute)
        if value is None:
            continue
        matches.append(
            {
                "target": target,
                "identifier": obj.identifier,
                "display_name": _display_name(obj),
                "parent": parent,
                "attribute": requested_attribute,
                "value": value,
            }
        )

    return {
        "matches": matches,
        "summary_view": {
            "garden_target": manifest.target(),
            "model_target": resolved_model_target,
            "attribute": requested_attribute,
            "match_count": len(matches),
        },
        "report": make_report(
            status="ok",
            message=(
                f"Found {len(matches)} Dragonfly Room2D value(s) for "
                f"{requested_attribute}."
            ),
        ),
    }
