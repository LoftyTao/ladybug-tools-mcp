"""Dragonfly geometry governance services backed by public SDK methods."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from dragonfly.model import Model
from dragonfly.room2d import Room2D
from dragonfly.story import Story

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
) -> dict[str, Any]:
    return make_persistence_receipt(
        status="persisted",
        garden_id=garden_id,
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
