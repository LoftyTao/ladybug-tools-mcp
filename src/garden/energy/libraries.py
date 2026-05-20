"""Honeybee Energy standards library search helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from honeybee_energy.lib.constructions import (
    OPAQUE_CONSTRUCTIONS,
    SHADE_CONSTRUCTIONS,
    WINDOW_CONSTRUCTIONS,
)
from honeybee_energy.lib.constructionsets import CONSTRUCTION_SETS
from honeybee_energy.lib.materials import OPAQUE_MATERIALS, WINDOW_MATERIALS
from honeybee_energy.lib.programtypes import PROGRAM_TYPES
from honeybee_energy.lib.schedules import SCHEDULES
from honeybee_energy.lib.scheduletypelimits import SCHEDULE_TYPE_LIMITS

from ladybug_tools_mcp.contracts.report import make_report


@dataclass(frozen=True)
class _LibraryFamily:
    key: str
    label: str
    identifiers: tuple[str, ...]
    use_as: tuple[str, ...]


_FAMILIES = (
    _LibraryFamily(
        "schedule",
        "Schedule",
        SCHEDULES,
        ("schedule", "occupancy_schedule", "activity_schedule", "heating/cooling schedule inputs"),
    ),
    _LibraryFamily(
        "schedule_type_limit",
        "ScheduleTypeLimit",
        SCHEDULE_TYPE_LIMITS,
        ("schedule_type_limit",),
    ),
    _LibraryFamily(
        "program_type",
        "ProgramType",
        PROGRAM_TYPES,
        ("base_program_type",),
    ),
    _LibraryFamily(
        "opaque_material",
        "OpaqueMaterial",
        OPAQUE_MATERIALS,
        ("opaque material inputs",),
    ),
    _LibraryFamily(
        "window_material",
        "WindowMaterial",
        WINDOW_MATERIALS,
        ("window material inputs",),
    ),
    _LibraryFamily(
        "opaque_construction",
        "OpaqueConstruction",
        OPAQUE_CONSTRUCTIONS,
        ("opaque construction inputs",),
    ),
    _LibraryFamily(
        "window_construction",
        "WindowConstruction",
        WINDOW_CONSTRUCTIONS,
        ("window construction inputs",),
    ),
    _LibraryFamily(
        "shade_construction",
        "ShadeConstruction",
        SHADE_CONSTRUCTIONS,
        ("shade_construction",),
    ),
    _LibraryFamily(
        "construction_set",
        "ConstructionSet",
        CONSTRUCTION_SETS,
        ("base_construction_set", "construction_set"),
    ),
)
_FAMILIES_BY_KEY = {family.key: family for family in _FAMILIES}


def _query_tokens(query: str) -> tuple[str, ...]:
    normalized = query.lower().replace("_", " ").replace("-", " ").replace("::", " ")
    return tuple(token for token in normalized.split() if token)


def _score_identifier(identifier: str, tokens: tuple[str, ...], raw_query: str) -> int:
    if not tokens:
        return 1
    normalized = identifier.lower().replace("_", " ").replace("-", " ").replace("::", " ")
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
    normalized = None
    if object_family is not None:
        normalized = object_family.strip().replace("-", "_").lower()
    if normalized is None or normalized == "" or normalized == "all":
        return _FAMILIES
    family = _FAMILIES_BY_KEY.get(normalized)
    if family is None:
        allowed = ", ".join(["all", *_FAMILIES_BY_KEY])
        guidance = ""
        if normalized == "setpoint":
            guidance = (
                " Setpoints are created, not searched in the standards library; "
                "call create_setpoint with heating_setpoint and cooling_setpoint."
            )
        raise ValueError(f"object_family must be one of: {allowed}.{guidance}")
    return (family,)


def search_energy_library_objects(
    *,
    query: str,
    object_family: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search Honeybee Energy standards library identifiers."""
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
        "identifiers": [match["identifier"] for match in limited],
        "summary_view": {
            "query": query,
            "object_family": object_family or "all",
            "match_count": len(limited),
            "identifiers": [match["identifier"] for match in limited],
            "available_families": list(_FAMILIES_BY_KEY),
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(limited)} Honeybee Energy library identifier(s).",
        ),
    }
