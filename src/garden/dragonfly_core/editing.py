"""Dragonfly model editing services backed by public SDK methods."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dragonfly.building import Building
from dragonfly.model import Model
from dragonfly.room2d import Room2D
from dragonfly.story import Story

from garden.dragonfly_core.creation import (
    DRAGONFLY_OBJECTS_DIR,
    _object_type_dir,
    _load_object_dict,
    separate_building_top_bottom_stories,
)
from garden.dragonfly_core.model_io import (
    load_dragonfly_model,
    resolve_model_target,
    save_dragonfly_model,
)
from garden.dragonfly_core.targets import (
    make_dragonfly_object_target,
    normalize_dragonfly_object_target,
    object_summary,
)
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report


def _save_changed_model(
    garden_root: Path,
    manifest: Any,
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


def _receipt(
    *,
    garden_id: str,
    model_target: dict[str, Any],
    persisted_path: str,
    operation: str,
    target: dict[str, Any],
    change_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return make_persistence_receipt(
        status="persisted",
        garden_id=garden_id,
        model_target=model_target,
        persisted_path=persisted_path,
        change_summary={
            "operation": operation,
            "target": target,
            **(change_details or {}),
        },
    )


def _load_target_model(
    garden_root: str,
    model_target: dict[str, Any] | None,
) -> tuple[Path, Any, dict[str, Any], Model]:
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    return garden_root_path, manifest, resolved_model_target, model


def _one_by_identifier(objects: list[Any], identifier: str, object_type: str) -> Any:
    if len(objects) == 1:
        return objects[0]
    if not objects:
        raise ValueError(f"Dragonfly {object_type} not found: {identifier}.")
    raise ValueError(f"Dragonfly {object_type} identifier is ambiguous: {identifier}.")


def _require_edit(updated_fields: list[str], object_type: str) -> None:
    if not updated_fields:
        raise ValueError(
            f"edit_dragonfly_{object_type} requires at least one supported edit input."
        )


def _building_by_identifier(model: Model, identifier: str) -> Building:
    return _one_by_identifier(
        model.buildings_by_identifier([identifier]),
        identifier,
        "Building",
    )


def _room_by_identifier(model: Model, identifier: str) -> Room2D:
    return _one_by_identifier(
        model.room_2ds_by_identifier([identifier]),
        identifier,
        "Room2D",
    )


def _story_by_identifier(model: Model, identifier: str) -> Story:
    return _one_by_identifier(
        model.stories_by_identifier([identifier]),
        identifier,
        "Story",
    )


def _model_response(
    *,
    manifest: Any,
    updated_model_target: dict[str, Any],
    persisted_path: str,
    model: Model,
    updated_fields: list[str],
) -> dict[str, Any]:
    summary_view = {
        "target": updated_model_target,
        "identifier": model.identifier,
        "display_name": model.display_name,
        "type": model.to_dict().get("type"),
        "units": model.units,
        "tolerance": model.tolerance,
        "angle_tolerance": model.angle_tolerance,
        "updated_fields": updated_fields,
    }
    return {
        "object_dict": updated_model_target,
        "target": updated_model_target,
        "model_target": updated_model_target,
        "summary_view": summary_view,
        "persistence_receipt": _receipt(
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            operation="edit_dragonfly_model",
            target=updated_model_target,
            change_details={"updated_fields": updated_fields},
        ),
        "report": make_report(
            status="ok",
            message=f"Edited Dragonfly model: {updated_model_target['model_identifier']}",
        ),
    }


def _room_target(
    *,
    garden_id: str,
    model_identifier: str,
    room_identifier: str,
) -> dict[str, Any]:
    return make_dragonfly_object_target(
        garden_id=garden_id,
        model_identifier=model_identifier,
        object_type="room2d",
        object_identifier=room_identifier,
    )


def _story_target(
    *,
    garden_id: str,
    model_identifier: str,
    story_identifier: str,
) -> dict[str, Any]:
    return make_dragonfly_object_target(
        garden_id=garden_id,
        model_identifier=model_identifier,
        object_type="story",
        object_identifier=story_identifier,
    )


def _building_target(
    *,
    garden_id: str,
    model_identifier: str,
    building_identifier: str,
) -> dict[str, Any]:
    return make_dragonfly_object_target(
        garden_id=garden_id,
        model_identifier=model_identifier,
        object_type="building",
        object_identifier=building_identifier,
    )


def _compact_identifier(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _delete_draft_object(
    garden_root: Path,
    *,
    model_identifier: str,
    object_type: str,
    object_identifier: str,
) -> bool:
    object_path = (
        garden_root
        / DRAGONFLY_OBJECTS_DIR
        / model_identifier
        / _object_type_dir(object_type)
        / f"{object_identifier}.json"
    )
    if object_path.exists():
        object_path.unlink()
        return True
    return False


def edit_dragonfly_model(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    display_name: str | None = None,
    units: str | None = None,
    tolerance: float | None = None,
    angle_tolerance: float | None = None,
) -> dict[str, Any]:
    """Edit Dragonfly Model metadata using public SDK properties."""
    updated_fields: list[str] = []
    if display_name is not None:
        updated_fields.append("display_name")
    if units is not None:
        updated_fields.append("units")
    if tolerance is not None:
        updated_fields.append("tolerance")
    if angle_tolerance is not None:
        updated_fields.append("angle_tolerance")
    _require_edit(updated_fields, "model")

    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    if display_name is not None:
        model.display_name = display_name
    if units is not None:
        model.units = units
    if tolerance is not None:
        model.tolerance = tolerance
    if angle_tolerance is not None:
        model.angle_tolerance = angle_tolerance

    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    return _model_response(
        manifest=manifest,
        updated_model_target=updated_model_target,
        persisted_path=persisted_path,
        model=model,
        updated_fields=updated_fields,
    )


def edit_dragonfly_story(
    *,
    garden_root: str,
    story_target: dict[str, Any] | None = None,
    story_identifier: str | None = None,
    model_target: dict[str, Any] | None = None,
    display_name: str | None = None,
    floor_height: float | None = None,
    floor_to_floor_height: float | None = None,
    multiplier: int | None = None,
) -> dict[str, Any]:
    """Edit an embedded Dragonfly Story using public SDK properties."""
    updated_fields: list[str] = []
    if display_name is not None:
        updated_fields.append("display_name")
    if floor_height is not None:
        updated_fields.append("floor_height")
    if floor_to_floor_height is not None:
        updated_fields.append("floor_to_floor_height")
    if multiplier is not None:
        updated_fields.append("multiplier")
    _require_edit(updated_fields, "story")

    if story_target is not None:
        normalized_target = normalize_dragonfly_object_target(
            story_target,
            expected_type="story",
        )
        target_identifier = str(normalized_target["object_identifier"])
        if story_identifier is not None and story_identifier != target_identifier:
            raise ValueError(
                "story_identifier must match story_target.object_identifier when both are provided."
            )
        story_identifier = target_identifier
    if not story_identifier:
        raise ValueError("Provide story_target or story_identifier.")

    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    story = _story_by_identifier(model, story_identifier)
    if display_name is not None:
        story.display_name = display_name
    if floor_height is not None:
        story.floor_height = floor_height
    if floor_to_floor_height is not None:
        story.floor_to_floor_height = floor_to_floor_height
    if multiplier is not None:
        story.multiplier = multiplier

    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    target = _story_target(
        garden_id=manifest.garden_id,
        model_identifier=str(updated_model_target["model_identifier"]),
        story_identifier=story.identifier,
    )
    summary_view = object_summary(target, story.to_dict())
    summary_view["updated_fields"] = updated_fields
    return {
        "object_dict": story.to_dict(),
        "target": target,
        "story_target": target,
        "model_target": updated_model_target,
        "summary_view": summary_view,
        "persistence_receipt": _receipt(
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            operation="edit_dragonfly_story",
            target=target,
            change_details={"updated_fields": updated_fields},
        ),
        "report": make_report(
            status="ok",
            message=f"Edited Dragonfly Story: {story.identifier}",
        ),
    }


def edit_dragonfly_building(
    *,
    garden_root: str,
    building_identifier: str,
    model_target: dict[str, Any] | None = None,
    display_name: str | None = None,
    sort_stories: bool = False,
) -> dict[str, Any]:
    """Edit an embedded Dragonfly Building using public SDK properties/methods."""
    updated_fields: list[str] = []
    if display_name is not None:
        updated_fields.append("display_name")
    if sort_stories:
        updated_fields.append("sort_stories")
    _require_edit(updated_fields, "building")

    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    building = _building_by_identifier(model, building_identifier)
    if display_name is not None:
        building.display_name = display_name
    if sort_stories:
        building.sort_stories()
        separate_building_top_bottom_stories(building)

    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    target = _building_target(
        garden_id=manifest.garden_id,
        model_identifier=str(updated_model_target["model_identifier"]),
        building_identifier=building.identifier,
    )
    summary_view = {
        **object_summary(target, building.to_dict()),
        "story_count": len(building.unique_stories),
        "updated_fields": updated_fields,
    }
    return {
        "object_dict": building.to_dict(),
        "target": target,
        "building_target": target,
        "model_target": updated_model_target,
        "summary_view": summary_view,
        "persistence_receipt": _receipt(
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            operation="edit_dragonfly_building",
            target=target,
            change_details={"updated_fields": updated_fields},
        ),
        "report": make_report(
            status="ok",
            message=f"Edited Dragonfly Building: {building.identifier}",
        ),
    }


def edit_dragonfly_room2d(
    *,
    garden_root: str,
    room2d_target: dict[str, Any] | None = None,
    room_identifier: str | None = None,
    model_target: dict[str, Any] | None = None,
    vertices: list[list[float]] | None = None,
    floor_height: float | None = None,
    floor_to_ceiling_height: float | None = None,
    display_name: str | None = None,
    zone: str | None = None,
    is_ground_contact: bool | None = None,
    is_top_exposed: bool | None = None,
    projection_distance: float = 0,
) -> dict[str, Any]:
    """Edit a model-embedded Dragonfly Room2D using public Room2D APIs."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    if room2d_target is not None:
        normalized_target = normalize_dragonfly_object_target(
            room2d_target,
            expected_type="room2d",
        )
        room_identifier = str(normalized_target["object_identifier"])
    if not room_identifier:
        raise ValueError("edit_dragonfly_room2d requires room2d_target or room_identifier.")
    room = _room_by_identifier(
        model,
        room_identifier,
    )
    if vertices is not None:
        replacement = Room2D.from_vertices(
            room.identifier,
            vertices,
            room.floor_height if floor_height is None else floor_height,
            (
                room.floor_to_ceiling_height
                if floor_to_ceiling_height is None
                else floor_to_ceiling_height
            ),
            is_ground_contact=room.is_ground_contact,
            is_top_exposed=room.is_top_exposed,
        )
        room.replace_floor_geometry(
            replacement.floor_geometry,
            projection_distance=projection_distance,
            tolerance=model.tolerance,
            angle_tolerance=model.angle_tolerance,
        )
    elif floor_height is not None:
        room.floor_height = floor_height
    if floor_to_ceiling_height is not None:
        room.floor_to_ceiling_height = floor_to_ceiling_height
    if display_name is not None:
        room.display_name = display_name
    if zone is not None:
        room.zone = zone
    if is_ground_contact is not None:
        room.is_ground_contact = is_ground_contact
    if is_top_exposed is not None:
        room.is_top_exposed = is_top_exposed

    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    target = _room_target(
        garden_id=manifest.garden_id,
        model_identifier=str(updated_model_target["model_identifier"]),
        room_identifier=room.identifier,
    )
    return {
        "object_dict": room.to_dict(),
        "target": target,
        "object_target": target,
        "room2d_target": target,
        "model_target": updated_model_target,
        "summary_view": object_summary(target, room.to_dict()),
        "persistence_receipt": _receipt(
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            operation="edit_dragonfly_room2d",
            target=target,
        ),
        "report": make_report(
            status="ok",
            message=f"Edited Dragonfly Room2D: {room.identifier}",
        ),
    }


def add_dragonfly_stories_to_building(
    *,
    garden_root: str,
    building_identifier: str,
    story_targets: list[dict[str, Any]] | None = None,
    model_target: dict[str, Any] | None = None,
    story_identifiers: list[str] | None = None,
) -> dict[str, Any]:
    """Add Story draft objects to an existing Building with Building.add_stories."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    if story_targets is None and story_identifiers is not None:
        story_targets = [
            make_dragonfly_object_target(
                garden_id=manifest.garden_id,
                model_identifier=str(resolved_model_target["model_identifier"]),
                object_type="story",
                object_identifier=identifier,
            )
            for identifier in story_identifiers
        ]
    if not story_targets:
        raise ValueError(
            "add_dragonfly_stories_to_building requires story_targets. If you only "
            "have Story identifiers for draft Stories, pass story_identifiers."
        )
    building = _building_by_identifier(model, building_identifier)
    normalized_targets = [
        normalize_dragonfly_object_target(target, expected_type="story")
        for target in story_targets
    ]
    stories = [
        Story.from_dict(_load_object_dict(garden_root_path, target))
        for target in normalized_targets
    ]
    building.add_stories(stories, add_duplicate_ids=False)
    building.sort_stories()
    separate_building_top_bottom_stories(building)
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
        object_identifier=building.identifier,
    )
    return {
        "object_dict": building.to_dict(),
        "target": target,
        "building_target": target,
        "model_target": updated_model_target,
        "summary_view": {
            **object_summary(target, building.to_dict()),
            "story_count": len(building.unique_stories),
            "added_story_identifiers": [story.identifier for story in stories],
        },
        "persistence_receipt": _receipt(
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            operation="add_dragonfly_stories_to_building",
            target=target,
            change_details={
                "added_story_identifiers": [story.identifier for story in stories]
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Added {len(stories)} Dragonfly Story object(s) to {building.identifier}.",
        ),
    }


def remove_dragonfly_stories_from_building(
    *,
    garden_root: str,
    building_identifier: str,
    story_identifiers: list[str],
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Remove Stories from a Building with Building.remove_stories_by_identifier."""
    if not story_identifiers:
        raise ValueError("story_identifiers must include at least one Story identifier.")
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    building = _building_by_identifier(model, building_identifier)
    existing_ids = {story.identifier for story in building.unique_stories}
    compact_existing_ids = {_compact_identifier(story_id): story_id for story_id in existing_ids}
    resolved_story_identifiers: list[str] = []
    missing: list[str] = []
    for identifier in story_identifiers:
        if identifier in existing_ids:
            resolved_story_identifiers.append(identifier)
            continue
        compact_match = compact_existing_ids.get(_compact_identifier(identifier))
        if compact_match is not None:
            resolved_story_identifiers.append(compact_match)
            continue
        candidates = sorted(
            story_id
            for story_id in existing_ids
            if story_id.endswith(f"_{identifier}") or story_id.startswith(f"{identifier}_")
        )
        if len(candidates) == 1:
            resolved_story_identifiers.append(candidates[0])
            continue
        missing.append(identifier)
    if missing:
        raise ValueError(
            "Dragonfly Story identifier(s) not found on building "
            f"{building_identifier}: {', '.join(missing)}."
        )
    building.remove_stories_by_identifier(resolved_story_identifiers)
    if not building.unique_stories and not building.room_3ds:
        raise ValueError(
            "Removing these Stories would leave the Dragonfly Building empty. "
            "Keep at least one Story or 3D Room."
        )
    building.sort_stories()
    separate_building_top_bottom_stories(building)
    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    deleted_draft_count = 0
    for identifier in set([*story_identifiers, *resolved_story_identifiers]):
        if _delete_draft_object(
            garden_root_path,
            model_identifier=str(updated_model_target["model_identifier"]),
            object_type="story",
            object_identifier=identifier,
        ):
            deleted_draft_count += 1
    target = make_dragonfly_object_target(
        garden_id=manifest.garden_id,
        model_identifier=str(updated_model_target["model_identifier"]),
        object_type="building",
        object_identifier=building.identifier,
    )
    return {
        "object_dict": building.to_dict(),
        "target": target,
        "building_target": target,
        "model_target": updated_model_target,
        "summary_view": {
            **object_summary(target, building.to_dict()),
            "story_count": len(building.unique_stories),
            "removed_counts": {"stories": len(resolved_story_identifiers)},
            "removed_story_identifiers": resolved_story_identifiers,
            "deleted_draft_story_count": deleted_draft_count,
        },
        "persistence_receipt": _receipt(
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            operation="remove_dragonfly_stories_from_building",
            target=target,
            change_details={
                "removed_story_identifiers": resolved_story_identifiers,
                "removed_counts": {"stories": len(resolved_story_identifiers)},
                "deleted_draft_story_count": deleted_draft_count,
            },
        ),
        "report": make_report(
            status="ok",
            message=(
                f"Removed {len(resolved_story_identifiers)} Dragonfly Story object(s) "
                f"from {building.identifier}."
            ),
        ),
    }
