"""Dragonfly geometry governance services backed by public SDK methods."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
import json
import math
from pathlib import Path
from typing import Any

from dragonfly.model import Model
from dragonfly.room2d import Room2D
from dragonfly.story import Story
from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry2d.pointvector import Point2D

from garden.dragonfly_core.model_io import (
    load_dragonfly_model,
    normalize_dragonfly_model_target,
    resolve_model_target,
    save_dragonfly_model,
)
from garden.dragonfly_core.targets import (
    is_dragonfly_model_target,
    make_dragonfly_object_target,
    normalize_dragonfly_object_target,
    object_summary,
)
from garden.operations import (
    GardenRevisionConflictError,
    active_operation_controls,
    commit_manifest,
    read_operation_record,
)
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report


def _load_target_model(
    garden_root: str,
    model_target: dict[str, Any] | None,
) -> tuple[Path, Any, dict[str, Any], Model]:
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    return garden_root_path, manifest, resolved_model_target, model


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
    change_details: dict[str, Any],
    status: str = "persisted",
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return make_persistence_receipt(
        status=status,
        garden_id=garden_id,
        warnings=warnings,
        model_target=model_target,
        persisted_path=persisted_path,
        change_summary={
            "operation": operation,
            "target": target,
            **change_details,
        },
    )


def _one_by_identifier(objects: list[Any], identifier: str, object_type: str) -> Any:
    if len(objects) == 1:
        return objects[0]
    if not objects:
        raise ValueError(f"Dragonfly {object_type} not found: {identifier}.")
    raise ValueError(f"Dragonfly {object_type} identifier is ambiguous: {identifier}.")


def _story_by_identifier(model: Model, identifier: str) -> Story:
    return _one_by_identifier(model.stories_by_identifier([identifier]), identifier, "Story")


def _room_by_identifier(model: Model, identifier: str) -> Room2D:
    return _one_by_identifier(model.room_2ds_by_identifier([identifier]), identifier, "Room2D")


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


def _finite_float(
    value: Any,
    *,
    field_name: str,
    minimum: float,
    inclusive: bool = True,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a number.")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field_name} must be a number.") from exc
    if not math.isfinite(result) or (
        result < minimum if inclusive else result <= minimum
    ):
        comparator = "greater than or equal to" if inclusive else "greater than"
        raise ValueError(f"{field_name} must be {comparator} {minimum}.")
    return result


def _point2d(value: Any, *, field_name: str) -> Point2D:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != 2:
        raise ValueError(f"{field_name} must be a 2D coordinate list.")
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
        raise ValueError(f"{field_name} must contain numeric coordinates.")
    try:
        x, y = float(value[0]), float(value[1])
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field_name} must contain numeric coordinates.") from exc
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError(f"{field_name} must contain finite coordinates.")
    return Point2D(x, y)


def _line_segments(lines: Any) -> tuple[LineSegment2D, ...]:
    if isinstance(lines, (str, bytes)) or not isinstance(lines, Sequence) or not lines:
        raise ValueError("lines must include at least one straight 2D line segment.")
    segments: list[LineSegment2D] = []
    for index, line in enumerate(lines):
        points = line
        if isinstance(points, (str, bytes)) or not isinstance(points, Sequence) or len(points) != 2:
            raise ValueError(f"lines[{index}] must contain exactly two 2D points.")
        start = _point2d(points[0], field_name=f"lines[{index}][0]")
        end = _point2d(points[1], field_name=f"lines[{index}][1]")
        if math.hypot(start.x - end.x, start.y - end.y) == 0:
            raise ValueError(f"lines[{index}] must have two distinct points.")
        segments.append(LineSegment2D.from_end_points(start, end))
    return tuple(segments)


def _resolve_host_stories(
    model: Model,
    *,
    model_target: dict[str, Any],
    host_type: str | None,
    host_target: dict[str, Any] | None,
) -> tuple[str, str, list[Story]]:
    if host_type is not None and not isinstance(host_type, str):
        raise ValueError("host_type must be a string.")
    target_type = (
        str(host_target.get("object_type"))
        if isinstance(host_target, dict) and host_target.get("object_type")
        else None
    )
    resolved_type = (host_type or target_type or "model").strip().lower().replace("-", "_")
    if resolved_type not in {"model", "building", "story"}:
        raise ValueError("host_type must be model, building, or story.")
    if target_type is not None and target_type != resolved_type:
        raise ValueError("host_type must match host_target.object_type.")
    if resolved_type == "model":
        if host_target is not None:
            if not is_dragonfly_model_target(host_target):
                raise ValueError(
                    "host_target must be the selected Dragonfly Model target "
                    "when host_type is model."
                )
            normalized_model_target = normalize_dragonfly_model_target(host_target)
            if any(
                normalized_model_target.get(field) != model_target.get(field)
                for field in ("id", "garden_id", "domain", "model_identifier", "path")
            ):
                raise ValueError("host_target must match the loaded model_target.")
        return resolved_type, model.identifier, list(model.stories)
    if host_target is None:
        raise ValueError(f"host_target is required for host_type {resolved_type}.")
    normalized_target = normalize_dragonfly_object_target(
        host_target,
        expected_type=resolved_type,
    )
    target_model_identifier = str(normalized_target["model_identifier"])
    if target_model_identifier != model.identifier:
        raise ValueError("host_target belongs to a different Dragonfly Model.")
    identifier = str(normalized_target["object_identifier"])
    if resolved_type == "story":
        return resolved_type, identifier, [_story_by_identifier(model, identifier)]
    building = _one_by_identifier(
        model.buildings_by_identifier([identifier]),
        identifier,
        "Building",
    )
    return resolved_type, identifier, list(building.unique_stories)


def _host_target(
    *,
    garden_id: str,
    model_target: dict[str, Any],
    host_type: str,
    host_identifier: str,
) -> dict[str, Any]:
    if host_type == "model":
        return model_target
    return make_dragonfly_object_target(
        garden_id=garden_id,
        model_identifier=str(model_target["model_identifier"]),
        object_type=host_type,
        object_identifier=host_identifier,
    )


def _room_signature(room: Room2D) -> tuple[str, str]:
    return (
        json.dumps(room.to_dict(), sort_keys=True, separators=(",", ":")),
        json.dumps(room.floor_geometry.to_dict(), sort_keys=True, separators=(",", ":")),
    )


def _roof_signature(story: Story) -> str | None:
    roof = getattr(story, "roof", None)
    if roof is None:
        return None
    return json.dumps(roof.to_dict(), sort_keys=True, separators=(",", ":"))


def _room_snapshot(
    stories: Sequence[Story],
) -> dict[tuple[str, str, str], tuple[str, str]]:
    snapshot: dict[tuple[str, str, str], tuple[str, str]] = {}
    for story in stories:
        building = getattr(story, "parent", None)
        building_identifier = str(getattr(building, "identifier", ""))
        story_identifier = str(story.identifier)
        for room in story.room_2ds:
            room_identifier = str(room.identifier)
            snapshot[(building_identifier, story_identifier, room_identifier)] = _room_signature(room)
    return snapshot


def _roof_snapshot(stories: Sequence[Story]) -> dict[tuple[str, str], str | None]:
    snapshot: dict[tuple[str, str], str | None] = {}
    for story in stories:
        building = getattr(story, "parent", None)
        building_identifier = str(getattr(building, "identifier", ""))
        snapshot[(building_identifier, str(story.identifier))] = _roof_signature(story)
    return snapshot


def _scope_counts(
    snapshot: dict[tuple[str, str, str], tuple[str, str]],
) -> dict[str, int]:
    return {
        "buildings": len({building for building, _story, _room in snapshot if building}),
        "stories": len({(building, story) for building, story, _room in snapshot}),
        "room2ds": len(snapshot),
    }


def _batch_change_summary(
    before: dict[tuple[str, str, str], tuple[str, str]],
    after: dict[tuple[str, str, str], tuple[str, str]],
    before_roofs: dict[tuple[str, str], str | None] | None = None,
    after_roofs: dict[tuple[str, str], str | None] | None = None,
) -> dict[str, Any]:
    before_roofs = before_roofs or {}
    after_roofs = after_roofs or {}
    common = set(before) & set(after)
    changed_keys = {key for key in common if before[key][0] != after[key][0]}
    changed_geometry_keys = {key for key in common if before[key][1] != after[key][1]}
    removed_keys = set(before) - set(after)
    added_keys = set(after) - set(before)
    common_roofs = set(before_roofs) & set(after_roofs)
    changed_roof_keys = {
        key for key in common_roofs if before_roofs[key] != after_roofs[key]
    }
    affected_keys = changed_keys | removed_keys | added_keys
    affected_story_keys = {
        (building, story) for building, story, _room in affected_keys
    }
    affected_story_keys.update(changed_roof_keys)
    affected_building_keys = {
        building for building, _story, _room in affected_keys if building
    }
    affected_building_keys.update(
        building
        for building, _story in changed_roof_keys
        if building
    )
    affected_buildings = sorted(affected_building_keys)
    affected_stories = sorted({story for _building, story in affected_story_keys})
    affected_rooms = sorted({room for _building, _story, room in affected_keys})
    return {
        "affected_counts": {
            "buildings": len(affected_buildings),
            "stories": len(affected_story_keys),
            "room2ds": len(affected_keys),
        },
        "affected_identifiers": {
            "buildings": affected_buildings,
            "stories": affected_stories,
            "room2ds": affected_rooms,
        },
        "object_counts_before": _scope_counts(before),
        "object_counts_after": _scope_counts(after),
        "changed_room2d_identifiers": sorted(
            {room for _building, _story, room in changed_keys}
        ),
        "changed_geometry_room2d_identifiers": sorted(
            {room for _building, _story, room in changed_geometry_keys}
        ),
        "changed_roof_story_identifiers": sorted(
            {story for _building, story in changed_roof_keys}
        ),
        "added_room2d_identifiers": sorted({room for _building, _story, room in added_keys}),
        "removed_room2d_identifiers": sorted(
            {room for _building, _story, room in removed_keys}
        ),
    }


def _batch_result(
    *,
    garden_root_path: Path,
    manifest: Any,
    resolved_model_target: dict[str, Any],
    model: Model,
    operation: str,
    message: str,
    host_type: str,
    host_identifier: str,
    before: dict[tuple[str, str, str], tuple[str, str]],
    after: dict[tuple[str, str, str], tuple[str, str]],
    before_roofs: dict[tuple[str, str], str | None] | None = None,
    after_roofs: dict[tuple[str, str], str | None] | None = None,
    parameters: dict[str, Any],
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    changes = _batch_change_summary(
        before,
        after,
        before_roofs=before_roofs,
        after_roofs=after_roofs,
    )
    validation = _validation_summary(model)
    if not validation["is_valid"]:
        raise ValueError(
            f"{operation} produced an invalid Dragonfly Model and was not saved "
            f"({validation['issue_count']} issue(s))."
        )
    has_changes = bool(
        changes["affected_counts"]["room2ds"]
        or changes["changed_roof_story_identifiers"]
    )
    if has_changes:
        updated_model_target, persisted_path = _save_changed_model(
            garden_root_path,
            manifest,
            resolved_model_target,
            model,
        )
        receipt_status = "persisted"
    else:
        updated_model_target = resolved_model_target
        persisted_path = str(resolved_model_target.get("path", ""))
        receipt_status = "no_change"
        controls = active_operation_controls()
        existing_record = (
            read_operation_record(garden_root_path, controls[0])
            if controls is not None
            else None
        )
        if existing_record is not None:
            model_path = garden_root_path / str(resolved_model_target["path"])
            commit_manifest(
                garden_root_path,
                manifest,
                operation_type="dragonfly_model_save",
                operation_id=controls[0],
                expected_revision=controls[1],
                staged_writes={
                    str(resolved_model_target["path"]): model_path.read_bytes()
                },
            )
        elif controls is not None and controls[1] is not None:
            expected_revision = controls[1]
            if expected_revision != manifest.revision:
                raise GardenRevisionConflictError(
                    expected_revision=expected_revision,
                    current_revision=manifest.revision,
                )
    target = _host_target(
        garden_id=manifest.garden_id,
        model_target=updated_model_target,
        host_type=host_type,
        host_identifier=host_identifier,
    )
    summary_view = {
        "target": target,
        "model_target": updated_model_target,
        "host_type": host_type,
        "scope_identifier": host_identifier,
        "parameters": parameters,
        **changes,
        "validation": validation,
    }
    if warnings:
        summary_view["warnings"] = warnings
    response = {
        "target": target,
        "host_target": target,
        "model_target": updated_model_target,
        "summary_view": summary_view,
        "persistence_receipt": _receipt(
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            operation=operation,
            target=target,
            change_details=changes,
            status=receipt_status,
            warnings=warnings,
        ),
        "report": make_report(
            status="ok",
            message=message,
            warnings=warnings,
            details={"affected_counts": changes["affected_counts"]},
        ),
    }
    if not has_changes:
        response["runtime_status"] = "no_change"
    return response


def _validation_summary(model: Model) -> dict[str, Any]:
    issues = model.check_all(raise_exception=False, detailed=True)
    issue_codes = [
        issue["code"]
        for issue in issues
        if isinstance(issue, dict) and isinstance(issue.get("code"), str)
    ]
    issue_types = [
        issue["error_type"]
        for issue in issues
        if isinstance(issue, dict) and isinstance(issue.get("error_type"), str)
    ]
    return {
        "is_valid": len(issues) == 0,
        "issue_count": len(issues),
        "issue_codes": sorted(set(issue_codes)),
        "issue_types": sorted(set(issue_types)),
        "issue_counts_by_code": dict(sorted(Counter(issue_codes).items())),
        "issue_counts_by_type": dict(sorted(Counter(issue_types).items())),
    }


def _adjacency_counts(story: Story) -> dict[str, int]:
    surface_boundaries = sum(
        1
        for room in story.room_2ds
        for boundary_condition in room.boundary_conditions
        if boundary_condition.__class__.__name__ == "Surface"
    )
    return {
        "rooms": len(story.room_2ds),
        "segments": sum(room.segment_count for room in story.room_2ds),
        "surface_boundaries": surface_boundaries,
        "adjacent_pairs": surface_boundaries // 2,
    }


def _changed_counts(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    return {
        key: after.get(key, 0) - before.get(key, 0)
        for key in sorted(set(before) | set(after))
    }


def _resolve_story(
    model: Model,
    *,
    story_target: dict[str, Any] | None,
    story_identifier: str | None,
) -> Story:
    if story_target is not None:
        target = normalize_dragonfly_object_target(story_target, expected_type="story")
        target_identifier = str(target["object_identifier"])
        if story_identifier is not None and story_identifier != target_identifier:
            raise ValueError(
                "story_identifier must match story_target.object_identifier when both are provided."
            )
        story_identifier = target_identifier
    if not story_identifier:
        raise ValueError("Provide story_target or story_identifier.")
    return _story_by_identifier(model, story_identifier)


def solve_dragonfly_story_adjacency(
    *,
    garden_root: str,
    story_target: dict[str, Any] | None = None,
    story_identifier: str | None = None,
    model_target: dict[str, Any] | None = None,
    tolerance: float = 0.01,
    intersect: bool = False,
    resolve_window_conflicts: bool = True,
) -> dict[str, Any]:
    """Solve Room2D adjacencies on a Story with Story.solve_room_2d_adjacency."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    story = _resolve_story(
        model,
        story_target=story_target,
        story_identifier=story_identifier,
    )
    before_counts = _adjacency_counts(story)
    story.solve_room_2d_adjacency(
        tolerance=tolerance,
        intersect=intersect,
        resolve_window_conflicts=resolve_window_conflicts,
    )
    after_counts = _adjacency_counts(story)

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
    changed_counts = _changed_counts(before_counts, after_counts)
    summary_view = {
        **object_summary(target, story.to_dict()),
        "adjacency_counts_before": before_counts,
        "adjacency_counts_after": after_counts,
        "changed_counts": changed_counts,
        "validation": _validation_summary(model),
        "parameters": {
            "tolerance": tolerance,
            "intersect": intersect,
            "resolve_window_conflicts": resolve_window_conflicts,
        },
    }
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
            operation="solve_dragonfly_story_adjacency",
            target=target,
            change_details={
                "adjacency_counts_before": before_counts,
                "adjacency_counts_after": after_counts,
                "changed_counts": changed_counts,
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Solved Dragonfly Story adjacency: {story.identifier}",
        ),
    }


def reset_dragonfly_story_adjacency(
    *,
    garden_root: str,
    story_target: dict[str, Any] | None = None,
    story_identifier: str | None = None,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Reset Story Surface boundary conditions with Story.reset_adjacency."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    story = _resolve_story(
        model,
        story_target=story_target,
        story_identifier=story_identifier,
    )
    before_counts = _adjacency_counts(story)
    story.reset_adjacency()
    after_counts = _adjacency_counts(story)

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
    changed_counts = _changed_counts(before_counts, after_counts)
    summary_view = {
        **object_summary(target, story.to_dict()),
        "adjacency_counts_before": before_counts,
        "adjacency_counts_after": after_counts,
        "changed_counts": changed_counts,
        "validation": _validation_summary(model),
    }
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
            operation="reset_dragonfly_story_adjacency",
            target=target,
            change_details={
                "adjacency_counts_before": before_counts,
                "adjacency_counts_after": after_counts,
                "changed_counts": changed_counts,
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Reset Dragonfly Story adjacency: {story.identifier}",
        ),
    }


def _replace_room_in_parent(room: Room2D, replacement: Room2D) -> Room2D:
    story = room.parent if getattr(room, "has_parent", False) else None
    if story is None:
        raise ValueError(
            "clean_dragonfly_room2d_geometry requires a model-embedded Room2D with a Story parent."
        )
    story.room_2ds = [
        replacement if existing.identifier == room.identifier else existing
        for existing in story.room_2ds
    ]
    return _one_by_identifier(
        [existing for existing in story.room_2ds if existing.identifier == room.identifier],
        room.identifier,
        "Room2D",
    )


def clean_dragonfly_room2d_geometry(
    *,
    garden_root: str,
    room2d_target: dict[str, Any] | None = None,
    room_identifier: str | None = None,
    model_target: dict[str, Any] | None = None,
    remove_duplicate_vertices: bool = True,
    remove_colinear_vertices: bool = True,
    remove_short_segments_distance: float | None = None,
    tolerance: float = 0.01,
    preserve_wall_props: bool = True,
    angle_tolerance: float = 1.0,
) -> dict[str, Any]:
    """Clean a Room2D floor boundary using explicit Dragonfly SDK methods."""
    if room2d_target is not None:
        normalized_target = normalize_dragonfly_object_target(
            room2d_target,
            expected_type="room2d",
        )
        target_identifier = str(normalized_target["object_identifier"])
        if room_identifier is not None and room_identifier != target_identifier:
            raise ValueError(
                "room_identifier must match room2d_target.object_identifier when both are provided."
            )
        room_identifier = target_identifier
    if not room_identifier:
        raise ValueError("Provide room2d_target or room_identifier.")
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    room = _room_by_identifier(model, room_identifier)
    segment_count_before = room.segment_count
    duplicate_vertices_removed = 0

    if remove_duplicate_vertices:
        removed_indices = room.remove_duplicate_vertices(tolerance)
        duplicate_vertices_removed = len(removed_indices)
    if remove_colinear_vertices:
        room = _replace_room_in_parent(
            room,
            room.remove_colinear_vertices(
                tolerance,
                preserve_wall_props=preserve_wall_props,
            ),
        )
    if remove_short_segments_distance is not None:
        room = _replace_room_in_parent(
            room,
            room.remove_short_segments(
                remove_short_segments_distance,
                angle_tolerance=angle_tolerance,
            ),
        )

    segment_count_after = room.segment_count
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
    changed_counts = {"segments": segment_count_after - segment_count_before}
    summary_view = {
        **object_summary(target, room.to_dict()),
        "segment_count_before": segment_count_before,
        "segment_count_after": segment_count_after,
        "changed_counts": changed_counts,
        "validation": _validation_summary(model),
        "cleaning": {
            "remove_duplicate_vertices": remove_duplicate_vertices,
            "duplicate_vertices_removed": duplicate_vertices_removed,
            "remove_colinear_vertices": remove_colinear_vertices,
            "remove_short_segments_distance": remove_short_segments_distance,
            "tolerance": tolerance,
            "preserve_wall_props": preserve_wall_props,
            "angle_tolerance": angle_tolerance,
        },
    }
    return {
        "object_dict": room.to_dict(),
        "target": target,
        "object_target": target,
        "room2d_target": target,
        "model_target": updated_model_target,
        "summary_view": summary_view,
        "persistence_receipt": _receipt(
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            operation="clean_dragonfly_room2d_geometry",
            target=target,
            change_details={
                "segment_count_before": segment_count_before,
                "segment_count_after": segment_count_after,
                "changed_counts": changed_counts,
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Cleaned Dragonfly Room2D geometry: {room.identifier}",
        ),
    }


def align_dragonfly_room2ds(
    *,
    garden_root: str,
    lines: Any,
    distance: float = 0.5,
    tolerance: float = 0.01,
    host_type: str | None = None,
    host_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Align Room2D vertices to straight lines with Dragonfly Story.align."""
    line_segments = _line_segments(lines)
    resolved_distance = _finite_float(
        distance,
        field_name="distance",
        minimum=0,
    )
    resolved_tolerance = _finite_float(
        tolerance,
        field_name="tolerance",
        minimum=0,
        inclusive=False,
    )
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    resolved_host_type, host_identifier, stories = _resolve_host_stories(
        model,
        model_target=resolved_model_target,
        host_type=host_type,
        host_target=host_target,
    )
    if not stories or not any(story.room_2ds for story in stories):
        raise ValueError("The selected Dragonfly host contains no Room2Ds.")
    before = _room_snapshot(stories)
    before_roofs = _roof_snapshot(stories)
    for story in stories:
        for line in line_segments:
            story.align(line, resolved_distance, resolved_tolerance)
        story.remove_room_2d_duplicate_vertices(
            resolved_tolerance,
            delete_degenerate=True,
        )
        story.delete_degenerate_room_2ds(resolved_tolerance)
        story.rebuild_detailed_windows(resolved_tolerance)
        story.reset_adjacency()
        story.solve_room_2d_adjacency(tolerance=resolved_tolerance)
    after = _room_snapshot(stories)
    after_roofs = _roof_snapshot(stories)
    removed = sorted(
        {room for _building, _story, room in set(before) - set(after)}
    )
    warnings = (
        [
            "Room2Ds removed because alignment made their geometry degenerate: "
            + ", ".join(removed)
        ]
        if removed
        else None
    )
    return _batch_result(
        garden_root_path=garden_root_path,
        manifest=manifest,
        resolved_model_target=resolved_model_target,
        model=model,
        operation="align_dragonfly_room2ds",
        message=f"Aligned Dragonfly Room2Ds in {resolved_host_type} scope.",
        host_type=resolved_host_type,
        host_identifier=host_identifier,
        before=before,
        after=after,
        before_roofs=before_roofs,
        after_roofs=after_roofs,
        parameters={
            "line_count": len(line_segments),
            "distance": resolved_distance,
            "tolerance": resolved_tolerance,
        },
        warnings=warnings,
    )


def intersect_dragonfly_room2ds(
    *,
    garden_root: str,
    tolerance: float = 0.01,
    host_type: str | None = None,
    host_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Intersect adjacent Room2D segments and clear wall-level properties."""
    resolved_tolerance = _finite_float(
        tolerance,
        field_name="tolerance",
        minimum=0,
        inclusive=False,
    )
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    resolved_host_type, host_identifier, stories = _resolve_host_stories(
        model,
        model_target=resolved_model_target,
        host_type=host_type,
        host_target=host_target,
    )
    if not stories or not any(story.room_2ds for story in stories):
        raise ValueError("The selected Dragonfly host contains no Room2Ds.")
    before = _room_snapshot(stories)
    for story in stories:
        story_rooms = list(story.room_2ds)
        cleaned_rooms = [
            room.duplicate().remove_colinear_vertices(
                resolved_tolerance,
                preserve_wall_props=False,
            )
            for room in story_rooms
        ]
        intersected_rooms = Room2D.intersect_adjacency(
            cleaned_rooms,
            tolerance=resolved_tolerance,
            preserve_wall_props=False,
        )
        if len(intersected_rooms) != len(story_rooms):
            raise ValueError(
                "Dragonfly Room2D intersection returned an unexpected Room2D count."
            )
        replacements = {
            old.identifier: new
            for old, new in zip(story_rooms, intersected_rooms)
        }
        story.room_2ds = [
            replacements.get(room.identifier, room)
            for room in story.room_2ds
        ]
        story.remove_room_2d_duplicate_vertices(
            resolved_tolerance,
            delete_degenerate=True,
        )
        story.delete_degenerate_room_2ds(resolved_tolerance)
        story.reset_adjacency()
        story.solve_room_2d_adjacency(tolerance=resolved_tolerance)
    after = _room_snapshot(stories)
    warning = (
        "Room2D.intersect_adjacency subdivides wall segments and clears the original "
        "boundary conditions, window/glazing parameters, and shading parameters. "
        "Run this operation before assigning those properties; it does not restore "
        "or automatically preserve them."
    )
    return _batch_result(
        garden_root_path=garden_root_path,
        manifest=manifest,
        resolved_model_target=resolved_model_target,
        model=model,
        operation="intersect_dragonfly_room2ds",
        message=(
            f"Intersected Dragonfly Room2D segments in {resolved_host_type} scope; "
            "wall-level properties were cleared."
        ),
        host_type=resolved_host_type,
        host_identifier=host_identifier,
        before=before,
        after=after,
        parameters={
            "tolerance": resolved_tolerance,
            "preserve_wall_props": False,
        },
        warnings=[warning],
    )


def join_small_dragonfly_room2ds(
    *,
    garden_root: str,
    area_threshold: float = 10.0,
    join_into_large: bool = False,
    tolerance: float = 0.01,
    host_type: str | None = None,
    host_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Join small Room2Ds within selected Dragonfly Stories."""
    if not isinstance(join_into_large, bool):
        raise ValueError("join_into_large must be a boolean.")
    resolved_threshold = _finite_float(
        area_threshold,
        field_name="area_threshold",
        minimum=0,
        inclusive=False,
    )
    resolved_tolerance = _finite_float(
        tolerance,
        field_name="tolerance",
        minimum=0,
        inclusive=False,
    )
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    resolved_host_type, host_identifier, stories = _resolve_host_stories(
        model,
        model_target=resolved_model_target,
        host_type=host_type,
        host_target=host_target,
    )
    if not stories or not any(story.room_2ds for story in stories):
        raise ValueError("The selected Dragonfly host contains no Room2Ds.")
    before = _room_snapshot(stories)
    for story in stories:
        story.join_small_room_2ds(
            resolved_threshold,
            join_into_large=join_into_large,
            tolerance=resolved_tolerance,
        )
        story.remove_room_2d_duplicate_vertices(
            resolved_tolerance,
            delete_degenerate=True,
        )
        story.delete_degenerate_room_2ds(resolved_tolerance)
        story.reset_adjacency()
        story.solve_room_2d_adjacency(tolerance=resolved_tolerance)
    after = _room_snapshot(stories)
    return _batch_result(
        garden_root_path=garden_root_path,
        manifest=manifest,
        resolved_model_target=resolved_model_target,
        model=model,
        operation="join_small_dragonfly_room2ds",
        message=f"Joined small Dragonfly Room2Ds in {resolved_host_type} scope.",
        host_type=resolved_host_type,
        host_identifier=host_identifier,
        before=before,
        after=after,
        parameters={
            "area_threshold": resolved_threshold,
            "join_into_large": join_into_large,
            "tolerance": resolved_tolerance,
        },
    )
