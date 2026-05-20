"""Honeybee Radiance standards library search helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from honeybee_radiance.lib.modifiers import MODIFIERS
from honeybee_radiance.lib.modifiersets import MODIFIER_SETS

from ladybug_tools_mcp.contracts.report import make_report


@dataclass(frozen=True)
class _LibraryFamily:
    key: str
    label: str
    identifiers: tuple[str, ...]
    use_as: tuple[str, ...]


_FAMILIES = (
    _LibraryFamily(
        "modifier",
        "Modifier",
        MODIFIERS,
        ("modifier", "modifier_blk", "radiance modifier inputs"),
    ),
    _LibraryFamily(
        "modifier_set",
        "ModifierSet",
        MODIFIER_SETS,
        ("modifier_set",),
    ),
)
_FAMILIES_BY_KEY = {family.key: family for family in _FAMILIES}


def _query_tokens(query: str) -> tuple[str, ...]:
    normalized = query.lower().replace("_", " ").replace("-", " ")
    return tuple(token for token in normalized.split() if token)


def _score_identifier(identifier: str, tokens: tuple[str, ...], raw_query: str) -> int:
    if not tokens:
        return 1
    normalized = identifier.lower().replace("_", " ").replace("-", " ")
    score = 0
    if raw_query and raw_query.lower() in identifier.lower():
        score += 20
    for token in tokens:
        if token in normalized:
            score += 4
        if normalized.startswith(token):
            score += 2
    return score


def _selected_families(object_family: str | None) -> tuple[_LibraryFamily, ...]:
    if object_family is None or object_family == "" or object_family == "all":
        return _FAMILIES
    family = _FAMILIES_BY_KEY.get(object_family)
    if family is None:
        allowed = ", ".join(["all", *_FAMILIES_BY_KEY])
        raise ValueError(f"object_family must be one of: {allowed}.")
    return (family,)


def search_radiance_library_objects(
    *,
    query: str,
    object_family: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search Honeybee Radiance standards library identifiers."""
    if limit < 1:
        raise ValueError("limit must be greater than zero.")
    tokens = _query_tokens(query)
    matches: list[dict[str, Any]] = []
    for family in _selected_families(object_family):
        for identifier in family.identifiers:
            score = _score_identifier(identifier, tokens, query)
            if score <= 0:
                continue
            matches.append(
                {
                    "object_family": family.key,
                    "object_type": family.label,
                    "identifier": identifier,
                    "score": score,
                    "use_as": list(family.use_as),
                }
            )
    matches.sort(key=lambda item: (-item["score"], item["object_family"], item["identifier"]))
    limited = matches[:limit]
    return {
        "matches": limited,
        "summary_view": {
            "query": query,
            "object_family": object_family or "all",
            "match_count": len(limited),
            "available_families": list(_FAMILIES_BY_KEY),
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(limited)} Honeybee Radiance library identifier(s).",
        ),
    }
