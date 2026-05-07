"""Grasshopper Properties Input service helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flowerpot.registry import get_flowerpot
from garden.libraries.properties import (
    get_garden_properties_library_object,
    search_garden_properties_library_objects,
)
from ladybug_tools_mcp.contracts.report import make_report

ENERGY_ALIASES = {
    "schedule": "schedule",
    "schedules": "schedule",
    "schedule_type_limit": "schedule_type_limit",
    "schedule type limit": "schedule_type_limit",
    "program_type": "program_type",
    "program": "program_type",
    "programs": "program_type",
    "load": "load",
    "loads": "load",
    "material": "material",
    "materials": "material",
    "construction": "construction",
    "constructions": "construction",
    "construction_set": "construction_set",
    "construction set": "construction_set",
    "construction sets": "construction_set",
    "hvac": "hvac",
    "zone_ventilation_fan": "zone_ventilation_fan",
    "zone ventilation fan": "zone_ventilation_fan",
    "pv_properties": "pv_properties",
    "pv properties": "pv_properties",
    "electric_load_center": "electric_load_center",
    "electric load center": "electric_load_center",
}

RADIANCE_ALIASES = {
    "modifier": "modifier",
    "modifiers": "modifier",
    "modifier_set": "modifier_set",
    "modifier set": "modifier_set",
    "modifier sets": "modifier_set",
}

ALIASES_BY_DOMAIN = {
    "honeybee_energy": ENERGY_ALIASES,
    "honeybee_radiance": RADIANCE_ALIASES,
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
}


def normalize_properties_type(domain: str, value: str) -> str:
    """Normalize a user-facing properties type into a Garden family key."""
    aliases = ALIASES_BY_DOMAIN.get(domain)
    if aliases is None:
        raise ValueError(f"Unsupported properties domain: {domain}")

    normalized = " ".join(str(value or "").strip().lower().replace("-", " ").split())
    family = aliases.get(normalized) or aliases.get(normalized.replace(" ", "_"))
    if family:
        return family

    allowed = ", ".join(sorted(set(aliases.values())))
    raise ValueError(
        f"Unsupported {domain} properties type: {value}. Supported: {allowed}."
    )


def garden_root_from_flowerpot(flowerpot: dict[str, Any]) -> str:
    """Return the Garden root encoded in an opaque Flowerpot."""
    get_flowerpot(flowerpot=flowerpot)
    payload_context = flowerpot.get("payload_context") or {}
    garden_root = payload_context.get("garden_root")
    if not garden_root:
        raise ValueError("Flowerpot does not include a Garden root context.")
    return str(Path(garden_root).expanduser().resolve())


def properties_index_path(garden_root: str, domain: str, object_family: str) -> str:
    """Return the family index path used for Grasshopper follow signatures."""
    folder = INDEX_FOLDERS[(domain, object_family)]
    return str(
        Path(garden_root).expanduser().resolve()
        / "libraries"
        / domain
        / folder
        / "index.json"
    )


def _all_index_matches(garden_root: str, domain: str, object_family: str) -> list[dict[str, Any]]:
    """Return every indexed match for one Garden Properties Library family."""
    path = Path(properties_index_path(garden_root, domain, object_family))
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8") as handle:
        index = json.load(handle)
    return [
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
    ]


def _search_matches(
    *,
    garden_root: str,
    domain: str,
    object_family: str,
    query: str,
) -> list[dict[str, Any]]:
    """Search properties, returning all indexed family objects for empty queries."""
    if not query:
        return _all_index_matches(garden_root, domain, object_family)
    search_result = search_garden_properties_library_objects(
        garden_root=garden_root,
        query=query,
        domain=domain,
        object_family=object_family,
        limit=100,
    )
    return list(search_result.get("matches", []))


def read_properties_input(
    *,
    flowerpot: dict[str, Any],
    domain: str,
    properties_type: str,
    value: str | None = None,
) -> dict[str, Any]:
    """Read Garden Properties Library object dicts for a Grasshopper component."""
    garden_root = garden_root_from_flowerpot(flowerpot)
    object_family = normalize_properties_type(domain, properties_type)
    query = str(value or "").strip()
    matches = _search_matches(
        garden_root=garden_root,
        domain=domain,
        object_family=object_family,
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
    if search_match_count > 0 and loaded_count == 0 and warnings:
        report_status = "error"
        message = f"Failed to load {search_match_count} matched {object_family} properties."
    elif warnings:
        report_status = "partial"
        message = (
            f"Loaded {loaded_count} of {search_match_count} matched "
            f"{object_family} properties."
        )
    else:
        report_status = "ok"
        message = f"Found {loaded_count} {object_family} properties."

    return {
        "property": property_value,
        "properties": objects,
        "targets": targets,
        "follow_path": properties_index_path(garden_root, domain, object_family),
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
