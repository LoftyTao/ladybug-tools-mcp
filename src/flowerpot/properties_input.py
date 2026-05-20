"""Grasshopper Properties Input service helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flowerpot.registry import get_flowerpot
from garden.libraries.properties import (
    get_garden_properties_library_object,
)
from ladybug_tools_mcp.contracts.report import make_report

PROPERTIES_TYPES = {
    "energy": "honeybee_energy",
    "radiance": "honeybee_radiance",
}

INDEX_FOLDERS = {
    ("honeybee_energy", "schedule"): "schedules",
    ("honeybee_energy", "schedule_type_limit"): "schedule_type_limits",
    ("honeybee_energy", "program_type"): "program_types",
    ("honeybee_energy", "load"): "loads",
    ("honeybee_energy", "material"): "materials",
    ("honeybee_energy", "construction"): "constructions",
    ("honeybee_energy", "construction_set"): "construction_sets",
    ("honeybee_energy", "hvac"): "hvacs",
    ("honeybee_energy", "zone_ventilation_fan"): "zone_ventilation_fans",
    ("honeybee_energy", "pv_properties"): "pv_properties",
    ("honeybee_energy", "electric_load_center"): "electric_load_centers",
    ("honeybee_radiance", "modifier"): "modifiers",
    ("honeybee_radiance", "modifier_set"): "modifier_sets",
    ("honeybee_radiance", "luminaire"): "luminaires",
}


def normalize_properties_type(value: str) -> str:
    """Return a current Flowerpot properties type."""
    normalized = str(value or "").strip()
    if normalized in PROPERTIES_TYPES:
        return normalized

    allowed = ", ".join(sorted(PROPERTIES_TYPES))
    raise ValueError(
        f"Unsupported properties_type: {value}. Supported: {allowed}."
    )


def garden_root_from_flowerpot(flowerpot: dict[str, Any]) -> str:
    """Return the Garden root encoded in an opaque Flowerpot."""
    get_flowerpot(flowerpot=flowerpot)
    payload_context = flowerpot.get("payload_context") or {}
    garden_root = payload_context.get("garden_root")
    if not garden_root:
        raise ValueError("Flowerpot does not include a Garden root context.")
    return str(Path(garden_root).expanduser().resolve())


def properties_index_path(garden_root: str, domain: str) -> str:
    """Return the domain library path used for Grasshopper follow signatures."""
    return str(Path(garden_root).expanduser().resolve() / "libraries" / domain)


def _family_index_path(garden_root: str, domain: str, object_family: str) -> Path:
    folder = INDEX_FOLDERS[(domain, object_family)]
    return (
        Path(garden_root).expanduser().resolve()
        / "libraries"
        / domain
        / folder
        / "index.json"
    )


def _all_index_matches(garden_root: str, domain: str) -> list[dict[str, Any]]:
    """Return every indexed match for one Garden Properties Library domain."""
    matches: list[dict[str, Any]] = []
    for index_domain, object_family in sorted(INDEX_FOLDERS):
        if index_domain != domain:
            continue
        path = _family_index_path(garden_root, domain, object_family)
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8") as handle:
            index = json.load(handle)
        matches.extend(
            {
                "domain": domain,
                "object_family": object_family,
                "identifier": item.get("identifier"),
                "object_type": item.get("object_type"),
                "path": item.get("path"),
                "target": item["target"],
                "score": 1,
            }
            for item in index.get("objects", [])
        )
    return matches


def _search_matches(
    *,
    garden_root: str,
    domain: str,
    query: str,
) -> list[dict[str, Any]]:
    """Search properties, returning all indexed domain objects for empty queries."""
    matches = _all_index_matches(garden_root, domain)
    if not query:
        return matches
    scored = []
    for match in matches:
        score = _match_score(
            identifier=str(match.get("identifier") or ""),
            object_type=str(match.get("object_type") or ""),
            query=query,
        )
        if score <= 0:
            continue
        match = dict(match)
        match["score"] = score
        scored.append(match)
    scored.sort(
        key=lambda match: (
            -int(match["score"]),
            str(match["domain"]),
            str(match["object_family"]),
            str(match["identifier"]),
        )
    )
    return scored


def _match_score(*, identifier: str, object_type: str, query: str) -> int:
    text = f"{identifier} {object_type}".lower().replace("_", " ").replace("-", " ")
    tokens = [
        token
        for token in query.lower().replace("_", " ").replace("-", " ").split()
        if token
    ]
    score = 0
    if query.lower() in text:
        score += 20
    for token in tokens:
        if token in text:
            score += 4
        if text.startswith(token):
            score += 2
    return score


def read_properties_input(
    *,
    flowerpot: dict[str, Any],
    domain: str,
    properties_type: str,
    value: str | None = None,
) -> dict[str, Any]:
    """Read Garden Properties Library object dicts for a Grasshopper component."""
    garden_root = garden_root_from_flowerpot(flowerpot)
    normalized_type = normalize_properties_type(properties_type)
    expected_domain = PROPERTIES_TYPES[normalized_type]
    if domain != expected_domain:
        raise ValueError(
            f"properties_type {normalized_type!r} is not valid for {domain}; "
            f"expected {expected_domain}."
        )
    query = str(value or "").strip()
    matches = _search_matches(
        garden_root=garden_root,
        domain=domain,
        query=query,
    )

    objects: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []
    warnings: list[str] = []
    for match in matches:
        try:
            loaded = get_garden_properties_library_object(
                garden_root=garden_root,
                target=match["target"],
            )
        except Exception as error:
            warnings.append(str(error))
            continue
        objects.append(loaded["object_dict"])
        targets.append(loaded["target"])

    property_value: dict[str, Any] | list[dict[str, Any]] | None
    if not objects:
        property_value = None
    elif len(objects) == 1:
        property_value = objects[0]
    else:
        property_value = objects

    search_match_count = len(matches)
    loaded_count = len(objects)
    matched_families = sorted(
        {
            str(match.get("object_family"))
            for match in matches
            if match.get("object_family")
        }
    )
    object_family = matched_families[0] if len(matched_families) == 1 else "all"
    if search_match_count > 0 and loaded_count == 0 and warnings:
        report_status = "error"
        message = (
            f"Failed to load {search_match_count} matched "
            f"{normalized_type} properties."
        )
    elif warnings:
        report_status = "partial"
        message = (
            f"Loaded {loaded_count} of {search_match_count} matched "
            f"{normalized_type} properties."
        )
    else:
        report_status = "ok"
        message = f"Found {loaded_count} {normalized_type} properties."

    return {
        "property": property_value,
        "properties": objects,
        "targets": targets,
        "follow_path": properties_index_path(garden_root, domain),
        "report": make_report(
            status=report_status,
            message=message,
            warnings=warnings,
            details={
                "garden_root": garden_root,
                "domain": domain,
                "object_family": object_family,
                "query": query,
                "match_count": loaded_count,
                "search_match_count": search_match_count,
                "loaded_count": loaded_count,
                "targets": targets,
            },
        ),
    }
