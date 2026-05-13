"""Dragonfly typed target helpers."""

from __future__ import annotations

from typing import Any

DRAGONFLY_OBJECT_TARGET_TYPE = "dragonfly_object"


def is_dragonfly_model_target(value: Any) -> bool:
    """Return whether a value is a Dragonfly model typed target."""
    return (
        isinstance(value, dict)
        and value.get("target_type") == "model"
        and value.get("domain") == "dragonfly"
        and isinstance(value.get("model_identifier"), str)
        and bool(value.get("model_identifier"))
    )


def is_dragonfly_object_target(value: Any) -> bool:
    """Return whether a value is a Dragonfly object typed target."""
    return (
        isinstance(value, dict)
        and value.get("target_type") == DRAGONFLY_OBJECT_TARGET_TYPE
        and value.get("domain") == "dragonfly"
        and isinstance(value.get("model_identifier"), str)
        and isinstance(value.get("object_type"), str)
        and isinstance(value.get("object_identifier"), str)
        and bool(value.get("model_identifier"))
        and bool(value.get("object_type"))
        and bool(value.get("object_identifier"))
    )


def normalize_dragonfly_object_target(
    value: Any,
    *,
    expected_type: str | None = None,
) -> dict[str, Any]:
    """Extract a Dragonfly object target from common MCP result envelopes."""
    candidates = _target_candidates(value)
    object_targets = [
        candidate for candidate in candidates if is_dragonfly_object_target(candidate)
    ]
    if expected_type is not None:
        object_targets = [
            target for target in object_targets if target.get("object_type") == expected_type
        ]
    if len(object_targets) == 1:
        return object_targets[0]
    if len(object_targets) > 1:
        raise ValueError(
            "Input contains multiple Dragonfly object targets. Pass one nested "
            "target dict."
        )
    if expected_type:
        raise ValueError(
            f"Expected a Dragonfly {expected_type} target dict. Pass only the "
            "nested target returned by the creation tool."
        )
    raise ValueError(
        "Expected a Dragonfly object target dict. Pass only the nested target, "
        "not the full tool response."
    )


def make_dragonfly_object_target(
    *,
    garden_id: str,
    model_identifier: str,
    object_type: str,
    object_identifier: str,
    parent: dict[str, str] | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    """Build a Dragonfly object typed target."""
    target: dict[str, Any] = {
        "target_type": DRAGONFLY_OBJECT_TARGET_TYPE,
        "garden_id": garden_id,
        "domain": "dragonfly",
        "model_identifier": model_identifier,
        "object_type": object_type,
        "object_identifier": object_identifier,
        "identifier": object_identifier,
        "parent": parent or {},
    }
    if path:
        target["path"] = path
    return target


def object_summary(target: dict[str, Any], object_dict: dict[str, Any]) -> dict[str, Any]:
    """Build a compact Dragonfly object summary."""
    return {
        "target": target,
        "identifier": object_dict.get("identifier"),
        "display_name": object_dict.get("display_name"),
        "type": object_dict.get("type"),
    }


def _target_candidates(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []
    candidates: list[dict[str, Any]] = []
    if is_dragonfly_object_target(value):
        candidates.append(value)
    for key in ("target", "object_dict", "object_target", "room2d_target", "story_target", "building_target"):
        nested = value.get(key)
        if isinstance(nested, dict):
            candidates.append(nested)
    summary = value.get("summary_view")
    if isinstance(summary, dict):
        nested = summary.get("target")
        if isinstance(nested, dict):
            candidates.append(nested)
    receipt = value.get("persistence_receipt")
    if isinstance(receipt, dict):
        change_summary = receipt.get("change_summary")
        if isinstance(change_summary, dict):
            nested = change_summary.get("target")
            if isinstance(nested, dict):
                candidates.append(nested)
    return _dedupe_targets(candidates)


def _dedupe_targets(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for target in targets:
        key = (
            target.get("target_type"),
            target.get("domain"),
            target.get("model_identifier"),
            target.get("object_type"),
            target.get("object_identifier"),
            repr(sorted((target.get("parent") or {}).items())),
            target.get("path"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(target)
    return deduped
