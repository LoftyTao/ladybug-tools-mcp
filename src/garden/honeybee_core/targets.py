"""Honeybee typed target helpers."""

from __future__ import annotations

from typing import Any


def is_honeybee_model_target(value: Any) -> bool:
    """Return whether a value is a Honeybee model typed target."""
    return (
        isinstance(value, dict)
        and value.get("target_type") == "model"
        and value.get("domain") == "honeybee"
        and isinstance(value.get("model_identifier"), str)
        and bool(value.get("model_identifier"))
    )


def _coerce_honeybee_model_target(value: Any) -> dict[str, Any] | None:
    if is_honeybee_model_target(value):
        return value
    if not isinstance(value, dict):
        return None
    target_type = str(value.get("target_type") or "").replace("_", "").lower()
    model_identifier = (
        value.get("model_identifier")
        or value.get("model_id")
        or value.get("identifier")
    )
    if target_type not in {"model", "honeybeemodel"} or not isinstance(
        model_identifier, str
    ):
        return None
    return {
        "target_type": "model",
        "domain": "honeybee",
        "model_identifier": model_identifier,
    }


def is_honeybee_object_target(value: Any) -> bool:
    """Return whether a value is a Honeybee object typed target."""
    return (
        isinstance(value, dict)
        and value.get("target_type") == "honeybee_object"
        and value.get("domain") == "honeybee"
        and isinstance(value.get("model_identifier"), str)
        and isinstance(value.get("object_type"), str)
        and isinstance(value.get("object_identifier"), str)
        and bool(value.get("model_identifier"))
        and bool(value.get("object_type"))
        and bool(value.get("object_identifier"))
    )


def normalize_honeybee_model_target(value: Any) -> dict[str, Any]:
    """Extract a Honeybee model target from common MCP result envelopes."""
    candidates = _target_candidates(value, include_search_matches=False)
    model_targets = [candidate for candidate in candidates if is_honeybee_model_target(candidate)]
    if len(model_targets) == 1:
        return model_targets[0]
    if len(model_targets) > 1:
        raise ValueError(
            "Input contains multiple Honeybee model targets. Pass one nested model "
            "target dict, such as object_dict, target, or summary_view.model_target."
        )
    raise ValueError(
        "Expected a Honeybee model target dict. Pass only the nested model target, "
        "not the full model body or unrelated tool response."
    )


def normalize_honeybee_object_target(value: Any) -> dict[str, Any]:
    """Extract a Honeybee object target from common MCP result envelopes."""
    candidates = _target_candidates(value, include_search_matches=True)
    object_targets = [candidate for candidate in candidates if is_honeybee_object_target(candidate)]
    if len(object_targets) == 1:
        return object_targets[0]
    if len(object_targets) > 1:
        raise ValueError(
            "Input contains multiple Honeybee object targets. Pass one nested "
            "target dict, for example matches[0].target."
        )
    raise ValueError(
        "Expected a Honeybee object typed target dict. Pass only the nested target, "
        "such as matches[0].target or a write tool result target; do not pass the "
        "full tool response, summary_view, report, or persistence_receipt."
    )


def normalize_honeybee_target(value: Any) -> dict[str, Any]:
    """Extract either a Honeybee model target or object target."""
    candidates = _target_candidates(value, include_search_matches=True)
    targets = [
        candidate
        for candidate in candidates
        if is_honeybee_model_target(candidate) or is_honeybee_object_target(candidate)
    ]
    if len(targets) == 1:
        return targets[0]
    if len(targets) > 1:
        raise ValueError(
            "Input contains multiple Honeybee targets. Pass one nested target dict, "
            "for example target or matches[0].target."
        )
    raise ValueError(
        "Expected a Honeybee typed target dict. Pass only the nested target, not "
        "the full tool response."
    )


def _target_candidates(value: Any, *, include_search_matches: bool) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []

    candidates: list[dict[str, Any]] = []
    coerced_model_target = _coerce_honeybee_model_target(value)
    if coerced_model_target is not None:
        candidates.append(coerced_model_target)
    elif is_honeybee_object_target(value):
        candidates.append(value)

    for key in ("target", "object_dict", "model_target"):
        nested = value.get(key)
        if isinstance(nested, dict):
            candidates.append(_coerce_honeybee_model_target(nested) or nested)

    summary = value.get("summary_view")
    if isinstance(summary, dict):
        for key in ("target", "model_target"):
            nested = summary.get(key)
            if isinstance(nested, dict):
                candidates.append(_coerce_honeybee_model_target(nested) or nested)

    receipt = value.get("persistence_receipt")
    if isinstance(receipt, dict):
        nested = receipt.get("model_target")
        if isinstance(nested, dict):
            candidates.append(_coerce_honeybee_model_target(nested) or nested)
        change_summary = receipt.get("change_summary")
        if isinstance(change_summary, dict):
            nested = change_summary.get("target")
            if isinstance(nested, dict):
                candidates.append(_coerce_honeybee_model_target(nested) or nested)

    if include_search_matches:
        matches = value.get("matches")
        if isinstance(matches, list):
            for match in matches:
                if not isinstance(match, dict):
                    continue
                nested = match.get("target")
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


def make_honeybee_object_target(
    *,
    garden_id: str,
    model_identifier: str,
    object_type: str,
    object_identifier: str,
    parent: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a Honeybee object typed target."""
    return {
        "target_type": "honeybee_object",
        "garden_id": garden_id,
        "domain": "honeybee",
        "model_identifier": model_identifier,
        "object_type": object_type,
        "object_identifier": object_identifier,
        "identifier": object_identifier,
        "parent": parent or {},
    }


def object_summary(target: dict[str, Any], object_dict: dict[str, Any]) -> dict[str, Any]:
    """Build a compact Honeybee object summary."""
    return {
        "target": target,
        "identifier": object_dict.get("identifier"),
        "display_name": object_dict.get("display_name"),
        "type": object_dict.get("type"),
    }
