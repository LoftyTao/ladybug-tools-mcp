"""Dragonfly geometry governance services backed by public SDK methods."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
import json
import math
from pathlib import Path
from typing import Any

from dragonfly.building import Building
from dragonfly.model import Model
from dragonfly.room2d import Room2D
from dragonfly.story import Story
from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D

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
from ladybug_tools_mcp.contracts import make_persistence_receipt, make_report


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
    force_persist: bool = False,
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
        force_persist
        or changes["affected_counts"]["room2ds"]
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


def _building_by_identifier(model: Model, identifier: str) -> Building:
    return _one_by_identifier(
        model.buildings_by_identifier([identifier]),
        identifier,
        "Building",
    )


def _resolve_target_buildings(
    model: Model,
    *,
    model_target: dict[str, Any],
    building_identifier: str | None = None,
    host_type: str | None = None,
    host_target: dict[str, Any] | None = None,
) -> tuple[str, str, list[Building]]:
    if building_identifier is not None:
        return "building", building_identifier, [_building_by_identifier(model, building_identifier)]
    if host_target is not None and (host_type == "building" or host_target.get("object_type") == "building"):
        normalized = normalize_dragonfly_object_target(host_target, expected_type="building")
        identifier = str(normalized["object_identifier"])
        return "building", identifier, [_building_by_identifier(model, identifier)]
    if not model.buildings:
        raise ValueError("The Dragonfly Model contains no Buildings.")
    return "model", model.identifier, list(model.buildings)


def _vector3d(value: Any, *, field_name: str = "vector") -> Vector3D:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) not in {2, 3}:
        raise ValueError(f"{field_name} must be a 2D or 3D numeric vector.")
    coords = [float(item) for item in value]
    return Vector3D(coords[0], coords[1], coords[2] if len(coords) == 3 else 0.0)


def _point3d(value: Any, *, field_name: str = "origin") -> Point3D:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) not in {2, 3}:
        raise ValueError(f"{field_name} must be a 2D or 3D numeric coordinate list.")
    coords = [float(item) for item in value]
    return Point3D(coords[0], coords[1], coords[2] if len(coords) == 3 else 0.0)


def core_perimeter_dragonfly_room2ds(
    *,
    garden_root: str,
    perimeter_offset: float,
    air_boundary: bool = False,
    tolerance: float = 0.01,
    host_type: str | None = None,
    host_target: dict[str, Any] | None = None,
    story_target: dict[str, Any] | None = None,
    story_identifier: str | None = None,
    room2d_target: dict[str, Any] | None = None,
    room_identifier: str | None = None,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Split Room2Ds into core and perimeter zones with Room2D.to_core_perimeter."""
    resolved_offset = _finite_float(
        perimeter_offset,
        field_name="perimeter_offset",
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
    target_room_ids: set[str] | None = None
    if room2d_target is not None or room_identifier is not None:
        if room2d_target is not None:
            normalized_room = normalize_dragonfly_object_target(
                room2d_target,
                expected_type="room2d",
            )
            resolved_room_id = str(normalized_room["object_identifier"])
        else:
            resolved_room_id = str(room_identifier)
        target_room_ids = {resolved_room_id}
        owning_stories = [
            story
            for story in model.stories
            if any(rm.identifier == resolved_room_id for rm in story.room_2ds)
        ]
        if not owning_stories:
            raise ValueError(f"Dragonfly Room2D not found in Model: {resolved_room_id}.")
        resolved_host_type = "story"
        host_identifier = owning_stories[0].identifier
        stories = owning_stories
    elif story_target is not None or story_identifier is not None:
        story = _resolve_story(
            model,
            story_target=story_target,
            story_identifier=story_identifier,
        )
        resolved_host_type = "story"
        host_identifier = story.identifier
        stories = [story]
    else:
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
        new_rooms: list[Room2D] = []
        changed = False
        for room in story.room_2ds:
            if target_room_ids is not None and room.identifier not in target_room_ids:
                new_rooms.append(room)
                continue
            split_rooms = list(
                room.to_core_perimeter(
                    resolved_offset,
                    air_boundary=air_boundary,
                    tolerance=resolved_tolerance,
                )
            )
            new_rooms.extend(split_rooms)
            changed = True
        if changed:
            story.room_2ds = new_rooms
            story.reset_adjacency()
            story.solve_room_2d_adjacency(tolerance=resolved_tolerance)
    after = _room_snapshot(stories)
    return _batch_result(
        garden_root_path=garden_root_path,
        manifest=manifest,
        resolved_model_target=resolved_model_target,
        model=model,
        operation="core_perimeter_dragonfly_room2ds",
        message=f"Generated core/perimeter Room2Ds in {resolved_host_type} scope.",
        host_type=resolved_host_type,
        host_identifier=host_identifier,
        before=before,
        after=after,
        parameters={
            "perimeter_offset": resolved_offset,
            "air_boundary": air_boundary,
            "tolerance": resolved_tolerance,
        },
    )


def pull_dragonfly_stories_to_story(
    *,
    garden_root: str,
    base_story_id: str,
    building_identifier: str | None = None,
    pulled_story_ids: list[str] | None = None,
    distance: float = 0.5,
    coordinate_vertices: bool = True,
    constrain_edges: bool = False,
    tolerance: float = 0.01,
    host_type: str | None = None,
    host_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Pull Stories to align with a base Story using Building.pull_to_story."""
    resolved_distance = _finite_float(distance, field_name="distance", minimum=0)
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
    resolved_host_type, host_identifier, buildings = _resolve_target_buildings(
        model,
        model_target=resolved_model_target,
        building_identifier=building_identifier,
        host_type=host_type,
        host_target=host_target,
    )
    matching = [
        bldg
        for bldg in buildings
        if any(st.identifier == base_story_id for st in bldg.unique_stories)
    ]
    if not matching:
        raise ValueError(f"Base Story not found in selected Building(s): {base_story_id}.")
    before = _room_snapshot(list(model.stories))
    for bldg in matching:
        bldg.pull_to_story(
            resolved_distance,
            base_story_id,
            pulled_story_ids=pulled_story_ids,
            coordinate_vertices=coordinate_vertices,
            constrain_edges=constrain_edges,
            tolerance=resolved_tolerance,
        )
    after = _room_snapshot(list(model.stories))
    return _batch_result(
        garden_root_path=garden_root_path,
        manifest=manifest,
        resolved_model_target=resolved_model_target,
        model=model,
        operation="pull_dragonfly_stories_to_story",
        message=f"Pulled Stories toward base Story {base_story_id}.",
        host_type=resolved_host_type,
        host_identifier=host_identifier,
        before=before,
        after=after,
        parameters={
            "base_story_id": base_story_id,
            "pulled_story_ids": pulled_story_ids,
            "distance": resolved_distance,
            "coordinate_vertices": coordinate_vertices,
            "constrain_edges": constrain_edges,
            "tolerance": resolved_tolerance,
        },
    )


def fill_dragonfly_story_holes(
    *,
    garden_root: str,
    base_name: str = "Room",
    area_threshold: float = 0.0,
    tolerance: float = 0.01,
    host_type: str | None = None,
    host_target: dict[str, Any] | None = None,
    story_target: dict[str, Any] | None = None,
    story_identifier: str | None = None,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fill enclosed holes within Story footprints using Story.fill_holes."""
    resolved_threshold = _finite_float(
        area_threshold,
        field_name="area_threshold",
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
    if story_target is not None or story_identifier is not None:
        story = _resolve_story(
            model,
            story_target=story_target,
            story_identifier=story_identifier,
        )
        resolved_host_type = "story"
        host_identifier = story.identifier
        stories = [story]
    else:
        resolved_host_type, host_identifier, stories = _resolve_host_stories(
            model,
            model_target=resolved_model_target,
            host_type=host_type,
            host_target=host_target,
        )
    if not stories:
        raise ValueError("The selected Dragonfly host contains no Stories.")
    before = _room_snapshot(stories)
    for story in stories:
        story.fill_holes(
            base_name=base_name,
            area_threshold=resolved_threshold,
            tolerance=resolved_tolerance,
        )
        story.reset_adjacency()
        story.solve_room_2d_adjacency(tolerance=resolved_tolerance)
    after = _room_snapshot(stories)
    return _batch_result(
        garden_root_path=garden_root_path,
        manifest=manifest,
        resolved_model_target=resolved_model_target,
        model=model,
        operation="fill_dragonfly_story_holes",
        message=f"Filled Story footprint holes in {resolved_host_type} scope.",
        host_type=resolved_host_type,
        host_identifier=host_identifier,
        before=before,
        after=after,
        parameters={
            "base_name": base_name,
            "area_threshold": resolved_threshold,
            "tolerance": resolved_tolerance,
        },
    )


def join_dragonfly_room2ds(
    *,
    garden_root: str,
    room_identifiers: list[str],
    tolerance: float = 0.01,
    story_target: dict[str, Any] | None = None,
    story_identifier: str | None = None,
    host_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Join specific adjacent Room2Ds on a Story using Story.join_room_2ds."""
    if not room_identifiers or len(room_identifiers) < 2:
        raise ValueError("join_room_2ds requires at least two room_identifiers.")
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
    if story_target is not None or story_identifier is not None:
        story = _resolve_story(
            model,
            story_target=story_target,
            story_identifier=story_identifier,
        )
    elif host_target is not None and host_target.get("object_type") == "story":
        story = _resolve_story(
            model,
            story_target=host_target,
            story_identifier=None,
        )
    else:
        wanted = set(room_identifiers)
        matches = [
            st
            for st in model.stories
            if wanted.issubset({rm.identifier for rm in st.room_2ds})
        ]
        if not matches:
            raise ValueError(
                "Could not find a single Story containing all specified room_identifiers."
            )
        story = matches[0]
    before = _room_snapshot([story])
    story.join_room_2ds(list(room_identifiers), tolerance=resolved_tolerance)
    story.reset_adjacency()
    story.solve_room_2d_adjacency(tolerance=resolved_tolerance)
    after = _room_snapshot([story])
    return _batch_result(
        garden_root_path=garden_root_path,
        manifest=manifest,
        resolved_model_target=resolved_model_target,
        model=model,
        operation="join_dragonfly_room2ds",
        message=f"Joined {len(room_identifiers)} Room2D(s) in Story {story.identifier}.",
        host_type="story",
        host_identifier=story.identifier,
        before=before,
        after=after,
        parameters={
            "room_identifiers": list(room_identifiers),
            "tolerance": resolved_tolerance,
        },
    )


def split_dragonfly_story_with_above(
    *,
    garden_root: str,
    tolerance: float = 0.01,
    building_identifier: str | None = None,
    story_target: dict[str, Any] | None = None,
    story_identifier: str | None = None,
    story_above_identifier: str | None = None,
    host_type: str | None = None,
    host_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Split lower Story Room2Ds along upper Story footprint edges."""
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
    before = _room_snapshot(list(model.stories))
    if story_target is not None or story_identifier is not None:
        story = _resolve_story(
            model,
            story_target=story_target,
            story_identifier=story_identifier,
        )
        if story_above_identifier is not None:
            story_above = _story_by_identifier(model, story_above_identifier)
        else:
            parent_bldg = getattr(story, "parent", None)
            if parent_bldg is None:
                raise ValueError("Provide story_above_identifier when Story has no parent Building.")
            ordered = sorted(parent_bldg.unique_stories, key=lambda s: s.floor_height)
            idx = ordered.index(story)
            if idx + 1 >= len(ordered):
                raise ValueError(f"Story {story.identifier} is the top Story; no Story above.")
            story_above = ordered[idx + 1]
        story.split_with_story_above(story_above, tolerance=resolved_tolerance)
        resolved_host_type = "story"
        host_identifier = story.identifier
    else:
        resolved_host_type, host_identifier, buildings = _resolve_target_buildings(
            model,
            model_target=resolved_model_target,
            building_identifier=building_identifier,
            host_type=host_type,
            host_target=host_target,
        )
        for bldg in buildings:
            ordered = sorted(bldg.unique_stories, key=lambda s: s.floor_height)
            for idx in range(len(ordered) - 1):
                ordered[idx].split_with_story_above(
                    ordered[idx + 1],
                    tolerance=resolved_tolerance,
                )
    after = _room_snapshot(list(model.stories))
    return _batch_result(
        garden_root_path=garden_root_path,
        manifest=manifest,
        resolved_model_target=resolved_model_target,
        model=model,
        operation="split_dragonfly_story_with_above",
        message=f"Split Story footprints against Story above in {resolved_host_type} scope.",
        host_type=resolved_host_type,
        host_identifier=host_identifier,
        before=before,
        after=after,
        parameters={
            "story_above_identifier": story_above_identifier,
            "tolerance": resolved_tolerance,
        },
    )


def convert_dragonfly_multipliers(
    *,
    garden_root: str,
    building_identifier: str | None = None,
    host_type: str | None = None,
    host_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Expand Story multipliers into explicit unique Story instances."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    resolved_host_type, host_identifier, buildings = _resolve_target_buildings(
        model,
        model_target=resolved_model_target,
        building_identifier=building_identifier,
        host_type=host_type,
        host_target=host_target,
    )
    before = _room_snapshot(list(model.stories))
    before_story_count = len(model.stories)
    for bldg in buildings:
        bldg.convert_multipliers_to_stories()
    after = _room_snapshot(list(model.stories))
    return _batch_result(
        garden_root_path=garden_root_path,
        manifest=manifest,
        resolved_model_target=resolved_model_target,
        model=model,
        operation="convert_dragonfly_multipliers",
        message=f"Converted Story multipliers to explicit Stories ({before_story_count} -> {len(model.stories)}).",
        host_type=resolved_host_type,
        host_identifier=host_identifier,
        before=before,
        after=after,
        parameters={"story_count_before": before_story_count, "story_count_after": len(model.stories)},
        force_persist=before_story_count != len(model.stories),
    )


def separate_dragonfly_plenums(
    *,
    garden_root: str,
    building_identifier: str | None = None,
    room_identifiers: list[str] | None = None,
    target_floor_to_ceiling: float | None = None,
    floor_plenum: bool = False,
    tolerance: float = 0.01,
    host_type: str | None = None,
    host_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert Room2D plenum depths to Stories or carve plenums for selected rooms."""
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
    resolved_host_type, host_identifier, buildings = _resolve_target_buildings(
        model,
        model_target=resolved_model_target,
        building_identifier=building_identifier,
        host_type=host_type,
        host_target=host_target,
    )
    before = _room_snapshot(list(model.stories))
    before_story_count = len(model.stories)
    for bldg in buildings:
        if room_identifiers and target_floor_to_ceiling is not None:
            bldg.separate_room_2d_plenums(
                list(room_identifiers),
                float(target_floor_to_ceiling),
                floor_plenum=bool(floor_plenum),
                tolerance=resolved_tolerance,
            )
        else:
            bldg.convert_plenum_depths_to_room_2ds(tolerance=resolved_tolerance)
    after = _room_snapshot(list(model.stories))
    return _batch_result(
        garden_root_path=garden_root_path,
        manifest=manifest,
        resolved_model_target=resolved_model_target,
        model=model,
        operation="separate_dragonfly_plenums",
        message=f"Separated plenums into Story objects in {resolved_host_type} scope.",
        host_type=resolved_host_type,
        host_identifier=host_identifier,
        before=before,
        after=after,
        parameters={
            "room_identifiers": room_identifiers,
            "target_floor_to_ceiling": target_floor_to_ceiling,
            "floor_plenum": floor_plenum,
            "tolerance": resolved_tolerance,
        },
        force_persist=before_story_count != len(model.stories),
    )


def transform_dragonfly_objects(
    *,
    garden_root: str,
    transform_type: str,
    vector: list[float] | None = None,
    angle: float | None = None,
    factor: float | None = None,
    origin: list[float] | None = None,
    host_type: str | None = None,
    host_target: dict[str, Any] | None = None,
    story_target: dict[str, Any] | None = None,
    story_identifier: str | None = None,
    room2d_target: dict[str, Any] | None = None,
    room_identifier: str | None = None,
    building_identifier: str | None = None,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Transform a Dragonfly Model, Building, Story, or Room2D via move/rotate_xy/scale."""
    op_kind = transform_type.strip().lower().replace("-", "_")
    if op_kind not in {"move", "rotate_xy", "scale"}:
        raise ValueError("transform_type must be move, rotate_xy, or scale.")
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    resolved_host_type = "model"
    host_identifier = model.identifier
    targets_to_transform: list[Any] = [model]
    if room2d_target is not None or room_identifier is not None:
        if room2d_target is not None:
            normalized = normalize_dragonfly_object_target(room2d_target, expected_type="room2d")
            rid = str(normalized["object_identifier"])
        else:
            rid = str(room_identifier)
        targets_to_transform = [_room_by_identifier(model, rid)]
        resolved_host_type = "room2d"
        host_identifier = rid
    elif story_target is not None or story_identifier is not None:
        story = _resolve_story(
            model,
            story_target=story_target,
            story_identifier=story_identifier,
        )
        targets_to_transform = [story]
        resolved_host_type = "story"
        host_identifier = story.identifier
    elif building_identifier is not None or (
        host_target is not None and (host_type == "building" or host_target.get("object_type") == "building")
    ):
        resolved_host_type, host_identifier, bldgs = _resolve_target_buildings(
            model,
            model_target=resolved_model_target,
            building_identifier=building_identifier,
            host_type=host_type,
            host_target=host_target,
        )
        targets_to_transform = list(bldgs)
    elif host_type == "story" and host_target is not None:
        story = _resolve_story(model, story_target=host_target, story_identifier=None)
        targets_to_transform = [story]
        resolved_host_type = "story"
        host_identifier = story.identifier

    before = _room_snapshot(list(model.stories))
    if op_kind == "move":
        if vector is None:
            raise ValueError("vector is required for transform_type='move'.")
        vec3 = _vector3d(vector, field_name="vector")
        for obj in targets_to_transform:
            obj.move(vec3)
    elif op_kind == "rotate_xy":
        if angle is None:
            raise ValueError("angle is required for transform_type='rotate_xy'.")
        rot_angle = float(angle)
        ori3 = _point3d(origin if origin is not None else [0.0, 0.0, 0.0], field_name="origin")
        for obj in targets_to_transform:
            obj.rotate_xy(rot_angle, ori3)
    else:
        if factor is None:
            raise ValueError("factor is required for transform_type='scale'.")
        scale_factor = _finite_float(factor, field_name="factor", minimum=0, inclusive=False)
        ori3 = _point3d(origin, field_name="origin") if origin is not None else None
        for obj in targets_to_transform:
            obj.scale(scale_factor, ori3)
    after = _room_snapshot(list(model.stories))
    return _batch_result(
        garden_root_path=garden_root_path,
        manifest=manifest,
        resolved_model_target=resolved_model_target,
        model=model,
        operation=f"transform_dragonfly_{op_kind}",
        message=f"Applied {op_kind} transform to Dragonfly {resolved_host_type} ({host_identifier}).",
        host_type=resolved_host_type,
        host_identifier=host_identifier,
        before=before,
        after=after,
        parameters={
            "transform_type": op_kind,
            "vector": vector,
            "angle": angle,
            "factor": factor,
            "origin": origin,
        },
        force_persist=True,
    )


def merge_dragonfly_model(
    *,
    garden_root: str,
    incoming_model_target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge another Garden Dragonfly Model into the target Model via Model.add_model."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    resolved_incoming_target = normalize_dragonfly_model_target(incoming_model_target)
    other_model = load_dragonfly_model(garden_root_path, resolved_incoming_target)
    before = _room_snapshot(list(model.stories))
    before_context_count = len(model.context_shades)
    model.add_model(other_model.duplicate())
    after = _room_snapshot(list(model.stories))
    return _batch_result(
        garden_root_path=garden_root_path,
        manifest=manifest,
        resolved_model_target=resolved_model_target,
        model=model,
        operation="merge_dragonfly_model",
        message=f"Merged Dragonfly Model {other_model.identifier} into {model.identifier}.",
        host_type="model",
        host_identifier=model.identifier,
        before=before,
        after=after,
        parameters={"incoming_model_identifier": other_model.identifier},
        force_persist=before_context_count != len(model.context_shades),
    )


def process_dragonfly_geometry(
    *,
    garden_root: str,
    operation: str,
    model_target: dict[str, Any] | None = None,
    host_type: str | None = None,
    host_target: dict[str, Any] | None = None,
    story_target: dict[str, Any] | None = None,
    story_identifier: str | None = None,
    room2d_target: dict[str, Any] | None = None,
    room_identifier: str | None = None,
    building_identifier: str | None = None,
    lines: Any = None,
    distance: float = 0.5,
    area_threshold: float = 10.0,
    join_into_large: bool = False,
    tolerance: float = 0.01,
    intersect: bool = False,
    resolve_window_conflicts: bool = True,
    remove_duplicate_vertices: bool = True,
    remove_colinear_vertices: bool = True,
    remove_short_segments_distance: float | None = None,
    preserve_wall_props: bool = True,
    angle_tolerance: float = 1.0,
    perimeter_offset: float | None = None,
    air_boundary: bool = False,
    base_story_id: str | None = None,
    pulled_story_ids: list[str] | None = None,
    coordinate_vertices: bool = True,
    constrain_edges: bool = False,
    base_name: str = "Room",
    room_identifiers: list[str] | None = None,
    story_above_identifier: str | None = None,
    target_floor_to_ceiling: float | None = None,
    floor_plenum: bool = False,
    transform_type: str | None = None,
    vector: list[float] | None = None,
    angle: float | None = None,
    factor: float | None = None,
    origin: list[float] | None = None,
    incoming_model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dispatch Dragonfly geometry processing operations."""
    op = operation.strip().lower().replace("-", "_")
    if op == "align":
        if lines is None:
            raise ValueError("lines is required when operation='align'.")
        return align_dragonfly_room2ds(
            garden_root=garden_root,
            lines=lines,
            distance=distance,
            tolerance=tolerance,
            host_type=host_type,
            host_target=host_target,
            model_target=model_target,
        )
    if op == "clean":
        return clean_dragonfly_room2d_geometry(
            garden_root=garden_root,
            room2d_target=room2d_target,
            room_identifier=room_identifier,
            model_target=model_target,
            remove_duplicate_vertices=remove_duplicate_vertices,
            remove_colinear_vertices=remove_colinear_vertices,
            remove_short_segments_distance=remove_short_segments_distance,
            tolerance=tolerance,
            preserve_wall_props=preserve_wall_props,
            angle_tolerance=angle_tolerance,
        )
    if op == "intersect":
        return intersect_dragonfly_room2ds(
            garden_root=garden_root,
            tolerance=tolerance,
            host_type=host_type,
            host_target=host_target,
            model_target=model_target,
        )
    if op == "join_small":
        return join_small_dragonfly_room2ds(
            garden_root=garden_root,
            area_threshold=area_threshold,
            join_into_large=join_into_large,
            tolerance=tolerance,
            host_type=host_type,
            host_target=host_target,
            model_target=model_target,
        )
    if op == "solve_adjacency":
        return solve_dragonfly_story_adjacency(
            garden_root=garden_root,
            story_target=story_target,
            story_identifier=story_identifier,
            model_target=model_target,
            tolerance=tolerance,
            intersect=intersect,
            resolve_window_conflicts=resolve_window_conflicts,
        )
    if op == "reset_adjacency":
        return reset_dragonfly_story_adjacency(
            garden_root=garden_root,
            story_target=story_target,
            story_identifier=story_identifier,
            model_target=model_target,
        )
    if op == "core_perimeter":
        if perimeter_offset is None:
            raise ValueError("perimeter_offset is required when operation='core_perimeter'.")
        return core_perimeter_dragonfly_room2ds(
            garden_root=garden_root,
            perimeter_offset=perimeter_offset,
            air_boundary=air_boundary,
            tolerance=tolerance,
            host_type=host_type,
            host_target=host_target,
            story_target=story_target,
            story_identifier=story_identifier,
            room2d_target=room2d_target,
            room_identifier=room_identifier,
            model_target=model_target,
        )
    if op == "pull_to_story":
        if not base_story_id:
            raise ValueError("base_story_id is required when operation='pull_to_story'.")
        return pull_dragonfly_stories_to_story(
            garden_root=garden_root,
            base_story_id=base_story_id,
            building_identifier=building_identifier,
            pulled_story_ids=pulled_story_ids,
            distance=distance,
            coordinate_vertices=coordinate_vertices,
            constrain_edges=constrain_edges,
            tolerance=tolerance,
            host_type=host_type,
            host_target=host_target,
            model_target=model_target,
        )
    if op == "fill_holes":
        return fill_dragonfly_story_holes(
            garden_root=garden_root,
            base_name=base_name,
            area_threshold=area_threshold if area_threshold != 10.0 else 0.0,
            tolerance=tolerance,
            host_type=host_type,
            host_target=host_target,
            story_target=story_target,
            story_identifier=story_identifier,
            model_target=model_target,
        )
    if op == "join_room_2ds":
        if not room_identifiers:
            raise ValueError("room_identifiers is required when operation='join_room_2ds'.")
        return join_dragonfly_room2ds(
            garden_root=garden_root,
            room_identifiers=room_identifiers,
            tolerance=tolerance,
            story_target=story_target,
            story_identifier=story_identifier,
            host_target=host_target,
            model_target=model_target,
        )
    if op == "split_with_story_above":
        return split_dragonfly_story_with_above(
            garden_root=garden_root,
            tolerance=tolerance,
            building_identifier=building_identifier,
            story_target=story_target,
            story_identifier=story_identifier,
            story_above_identifier=story_above_identifier,
            host_type=host_type,
            host_target=host_target,
            model_target=model_target,
        )
    if op == "convert_multipliers":
        return convert_dragonfly_multipliers(
            garden_root=garden_root,
            building_identifier=building_identifier,
            host_type=host_type,
            host_target=host_target,
            model_target=model_target,
        )
    if op == "separate_plenums":
        return separate_dragonfly_plenums(
            garden_root=garden_root,
            building_identifier=building_identifier,
            room_identifiers=room_identifiers,
            target_floor_to_ceiling=target_floor_to_ceiling,
            floor_plenum=floor_plenum,
            tolerance=tolerance,
            host_type=host_type,
            host_target=host_target,
            model_target=model_target,
        )
    if op == "transform":
        if not transform_type:
            raise ValueError("transform_type is required when operation='transform'.")
        return transform_dragonfly_objects(
            garden_root=garden_root,
            transform_type=transform_type,
            vector=vector,
            angle=angle,
            factor=factor,
            origin=origin,
            host_type=host_type,
            host_target=host_target,
            story_target=story_target,
            story_identifier=story_identifier,
            room2d_target=room2d_target,
            room_identifier=room_identifier,
            building_identifier=building_identifier,
            model_target=model_target,
        )
    if op == "merge_model":
        if incoming_model_target is None:
            raise ValueError("incoming_model_target is required when operation='merge_model'.")
        return merge_dragonfly_model(
            garden_root=garden_root,
            incoming_model_target=incoming_model_target,
            model_target=model_target,
        )
    raise ValueError(
        "operation must be one of align, clean, intersect, join_small, "
        "solve_adjacency, reset_adjacency, core_perimeter, pull_to_story, "
        "fill_holes, join_room_2ds, split_with_story_above, "
        "convert_multipliers, separate_plenums, transform, or merge_model."
    )
