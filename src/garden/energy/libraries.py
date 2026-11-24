"""Honeybee Energy standards library search and retrieval helpers."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable

from honeybee_energy.lib.constructions import (
    OPAQUE_CONSTRUCTIONS,
    SHADE_CONSTRUCTIONS,
    WINDOW_CONSTRUCTIONS,
    opaque_construction_by_identifier,
    shade_construction_by_identifier,
    window_construction_by_identifier,
)
from honeybee_energy.lib.constructionsets import (
    CONSTRUCTION_SETS,
    construction_set_by_identifier,
)
from honeybee_energy.lib.materials import (
    OPAQUE_MATERIALS,
    WINDOW_MATERIALS,
    opaque_material_by_identifier,
    window_material_by_identifier,
)
from honeybee_energy.lib.programtypes import PROGRAM_TYPES, program_type_by_identifier
from honeybee_energy.lib.schedules import SCHEDULES, schedule_by_identifier
from honeybee_energy.lib.scheduletypelimits import (
    SCHEDULE_TYPE_LIMITS,
    schedule_type_limit_by_identifier,
)

from ladybug_tools_mcp.contracts import make_report


@dataclass(frozen=True)
class _LibraryFamily:
    key: str
    label: str
    identifiers: tuple[str, ...]
    use_as: tuple[str, ...]
    getter: Callable[[str], Any]


_FAMILIES = (
    _LibraryFamily(
        "schedule",
        "Schedule",
        SCHEDULES,
        ("schedule", "occupancy_schedule", "activity_schedule", "heating/cooling schedule inputs"),
        schedule_by_identifier,
    ),
    _LibraryFamily(
        "schedule_type_limit",
        "ScheduleTypeLimit",
        SCHEDULE_TYPE_LIMITS,
        ("schedule_type_limit",),
        schedule_type_limit_by_identifier,
    ),
    _LibraryFamily(
        "program_type",
        "ProgramType",
        PROGRAM_TYPES,
        ("base_program_type",),
        program_type_by_identifier,
    ),
    _LibraryFamily(
        "opaque_material",
        "OpaqueMaterial",
        OPAQUE_MATERIALS,
        ("opaque material inputs",),
        opaque_material_by_identifier,
    ),
    _LibraryFamily(
        "window_material",
        "WindowMaterial",
        WINDOW_MATERIALS,
        ("window material inputs",),
        window_material_by_identifier,
    ),
    _LibraryFamily(
        "opaque_construction",
        "OpaqueConstruction",
        OPAQUE_CONSTRUCTIONS,
        ("opaque construction inputs",),
        opaque_construction_by_identifier,
    ),
    _LibraryFamily(
        "window_construction",
        "WindowConstruction",
        WINDOW_CONSTRUCTIONS,
        ("window construction inputs",),
        window_construction_by_identifier,
    ),
    _LibraryFamily(
        "shade_construction",
        "ShadeConstruction",
        SHADE_CONSTRUCTIONS,
        ("shade_construction",),
        shade_construction_by_identifier,
    ),
    _LibraryFamily(
        "construction_set",
        "ConstructionSet",
        CONSTRUCTION_SETS,
        ("base_construction_set", "construction_set"),
        construction_set_by_identifier,
    ),
)
_FAMILIES_BY_KEY = {family.key: family for family in _FAMILIES}


def _compact(value: str) -> str:
    return re.sub(r"[\s_\-]+", "", value.lower())


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


def _matches_climate_zone(identifier: str, climate_zone: str) -> bool:
    raw = climate_zone.strip()
    if not raw:
        return True
    compact_filter = _compact(raw)
    compact_id = _compact(identifier)
    if compact_filter in compact_id:
        return True
    match = re.search(r"(?:climatezone|cz)?([1-8])([a-c])?$", compact_filter)
    if match:
        zone_num = match.group(1)
        zone_letter = match.group(2) or ""
        patterns = [f"climatezone{zone_num}", f"cz{zone_num}"]
        if zone_letter:
            patterns.extend([f"climatezone{zone_num}{zone_letter}", f"cz{zone_num}{zone_letter}"])
        if any(re.search(rf"{re.escape(pat)}(?:[^0-9]|$)", compact_id) for pat in patterns):
            return True
    return False


def _matches_vintage(identifier: str, vintage: str) -> bool:
    raw = vintage.strip()
    if not raw:
        return True
    segments = [seg.strip() for seg in identifier.split("::") if seg.strip()]
    compact_filter = _compact(raw)
    if segments:
        first_compact = _compact(segments[0])
        if compact_filter == first_compact:
            return True
        if len(segments) > 1 and compact_filter in first_compact:
            return True
    if "ashrae" in compact_filter or "90.1" in raw.lower():
        year_match = re.search(r"(pre_?1980|1980_?2004|2004|2007|2010|2013|2016|2019)", raw.lower())
        if year_match:
            token = _compact(year_match.group(1))
            if segments and _compact(segments[0]) == token:
                return True
            return token in _compact(identifier)
    tokens = _query_tokens(raw)
    norm_id = identifier.lower().replace("_", " ").replace("-", " ").replace("::", " ")
    return all(token in norm_id for token in tokens)


def _matches_construction_type(identifier: str, construction_type: str) -> bool:
    raw = construction_type.strip()
    if not raw:
        return True
    compact_filter = _compact(raw)
    compact_id = _compact(identifier)
    if compact_filter in compact_id:
        return True
    tokens = _query_tokens(raw)
    norm_id = identifier.lower().replace("_", " ").replace("-", " ").replace("::", " ")
    return all(token in norm_id for token in tokens)


def _matches_building_type(identifier: str, building_type: str) -> bool:
    raw = building_type.strip()
    if not raw:
        return True
    compact_filter = _compact(raw)
    segments = [seg.strip() for seg in identifier.split("::") if seg.strip()]
    if len(segments) >= 2 and compact_filter in _compact(segments[1]):
        return True
    if compact_filter in _compact(identifier):
        return True
    tokens = _query_tokens(raw)
    norm_id = identifier.lower().replace("_", " ").replace("-", " ").replace("::", " ")
    return all(token in norm_id for token in tokens)


def _matches_structured_filters(
    identifier: str,
    *,
    climate_zone: str | None = None,
    vintage: str | None = None,
    construction_type: str | None = None,
    building_type: str | None = None,
) -> bool:
    if climate_zone and not _matches_climate_zone(identifier, climate_zone):
        return False
    if vintage and not _matches_vintage(identifier, vintage):
        return False
    if construction_type and not _matches_construction_type(identifier, construction_type):
        return False
    if building_type and not _matches_building_type(identifier, building_type):
        return False
    return True


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


def _extract_material_summary(material: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "identifier": getattr(material, "identifier", None),
        "type": material.__class__.__name__,
    }
    for attr in (
        "thickness",
        "conductivity",
        "density",
        "specific_heat",
        "r_value",
        "u_value",
        "thermal_absorptance",
        "solar_absorptance",
        "visible_absorptance",
        "solar_transmittance",
        "visible_transmittance",
        "shgc",
        "emissivity",
    ):
        if hasattr(material, attr):
            val = getattr(material, attr)
            if isinstance(val, (int, float, str, bool)) or val is None:
                summary[attr] = val
    return summary


def _extract_energy_properties(family_key: str, obj: Any) -> dict[str, Any]:
    if family_key in {"opaque_construction", "window_construction"}:
        props: dict[str, Any] = {
            "u_value": getattr(obj, "u_value", None),
            "u_value_ip": getattr(obj, "u_value_ip", None),
            "r_value": getattr(obj, "r_value", None),
            "r_value_ip": getattr(obj, "r_value_ip", None),
            "layers": [_extract_material_summary(mat) for mat in getattr(obj, "materials", ())],
        }
        for attr in ("shgc", "visible_transmittance", "solar_transmittance", "thickness"):
            if hasattr(obj, attr):
                props[attr] = getattr(obj, attr)
        return props

    if family_key == "construction_set":
        sets: dict[str, Any] = {}
        for attr in ("wall_set", "floor_set", "roof_ceiling_set", "aperture_set", "door_set"):
            sub = getattr(obj, attr, None)
            if sub is None:
                continue
            sub_info: dict[str, Any] = {}
            for slot in (
                "exterior_construction",
                "interior_construction",
                "ground_construction",
                "window_construction",
                "skylight_construction",
                "operable_construction",
                "exterior_glass_construction",
                "overhead_construction",
            ):
                constr = getattr(sub, slot, None)
                if constr is not None:
                    sub_info[slot] = {
                        "identifier": getattr(constr, "identifier", None),
                        "u_value": getattr(constr, "u_value", None),
                        "r_value": getattr(constr, "r_value", None),
                    }
            sets[attr] = sub_info
        for attr in ("shade_construction", "air_boundary_construction"):
            constr = getattr(obj, attr, None)
            if constr is not None:
                sets[attr] = {"identifier": getattr(constr, "identifier", None)}
        return sets

    if family_key == "program_type":
        props = {}
        schedules: dict[str, str] = {}
        for attr in (
            "people",
            "lighting",
            "electric_equipment",
            "gas_equipment",
            "service_hot_water",
            "infiltration",
            "ventilation",
            "setpoint",
        ):
            sub = getattr(obj, attr, None)
            if sub is None:
                props[attr] = None
                continue
            props[attr] = sub.to_dict() if hasattr(sub, "to_dict") else str(sub)
            for sch_attr in (
                "occupancy_schedule",
                "activity_schedule",
                "schedule",
                "heating_schedule",
                "cooling_schedule",
                "humidifying_schedule",
                "dehumidifying_schedule",
            ):
                sch = getattr(sub, sch_attr, None)
                if sch is not None and hasattr(sch, "identifier"):
                    schedules[f"{attr}.{sch_attr}"] = sch.identifier
        props["schedules"] = schedules
        return props

    if family_key in {"opaque_material", "window_material"}:
        return _extract_material_summary(obj)

    if family_key == "schedule":
        type_limit = getattr(obj, "schedule_type_limit", None)
        return {
            "schedule_type_limit": getattr(type_limit, "identifier", None),
            "default_day_schedule": getattr(
                getattr(obj, "default_day_schedule", None), "identifier", None
            ),
            "day_schedule_count": len(getattr(obj, "day_schedules", ()) or ()),
            "rule_count": len(getattr(obj, "schedule_rules", ()) or ()),
            "is_constant": getattr(obj, "is_constant", None),
        }

    return obj.to_dict() if hasattr(obj, "to_dict") else {}


def search_energy_library_objects(
    *,
    query: str = "",
    object_family: str | None = None,
    climate_zone: str | None = None,
    vintage: str | None = None,
    construction_type: str | None = None,
    building_type: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search Honeybee Energy standards library identifiers with optional structured filters."""
    if limit < 1:
        raise ValueError("limit must be greater than zero.")
    tokens = _query_tokens(query)
    matches: list[dict[str, Any]] = []
    for family in _selected_families(object_family):
        for identifier in family.identifiers:
            if not _matches_structured_filters(
                identifier,
                climate_zone=climate_zone,
                vintage=vintage,
                construction_type=construction_type,
                building_type=building_type,
            ):
                continue
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
            "filters": {
                "climate_zone": climate_zone,
                "vintage": vintage,
                "construction_type": construction_type,
                "building_type": building_type,
            },
            "match_count": len(limited),
            "total_matches": len(matches),
            "identifiers": [match["identifier"] for match in limited],
            "available_families": list(_FAMILIES_BY_KEY),
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(limited)} Honeybee Energy library identifier(s).",
        ),
    }


def get_energy_library_object(
    *,
    identifier: str,
    object_family: str | None = None,
) -> dict[str, Any]:
    """Retrieve full properties and object_dict for one Honeybee Energy standards object."""
    target = identifier.strip()
    if not target:
        raise ValueError("identifier is required when action='get'.")

    families = _selected_families(object_family)
    resolved_family: _LibraryFamily | None = None
    resolved_identifier: str | None = None

    for family in families:
        if target in family.identifiers:
            resolved_family = family
            resolved_identifier = target
            break

    if resolved_family is None:
        lowered = target.lower()
        for family in families:
            for item in family.identifiers:
                if item.lower() == lowered:
                    resolved_family = family
                    resolved_identifier = item
                    break
            if resolved_family is not None:
                break

    if resolved_family is None or resolved_identifier is None:
        scope = object_family or "all"
        raise ValueError(
            f"Honeybee Energy standards object {identifier!r} was not found in family {scope!r}."
        )

    obj = resolved_family.getter(resolved_identifier)
    object_dict = obj.to_dict()
    properties = _extract_energy_properties(resolved_family.key, obj)
    return {
        "domain": "energy",
        "object_family": resolved_family.key,
        "object_type": resolved_family.label,
        "identifier": resolved_identifier,
        "use_as": list(resolved_family.use_as),
        "properties": properties,
        "object_dict": object_dict,
        "summary_view": {
            "domain": "energy",
            "object_family": resolved_family.key,
            "object_type": resolved_family.label,
            "identifier": resolved_identifier,
            "use_as": list(resolved_family.use_as),
            "body_returned": True,
        },
        "report": make_report(
            status="ok",
            message=f"Loaded Honeybee Energy standards {resolved_family.label}: {resolved_identifier}.",
        ),
    }
