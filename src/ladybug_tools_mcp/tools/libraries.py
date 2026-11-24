"""libraries MCP tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Callable, Literal

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.contracts import (
    LibraryObjectTargetRef,
    MutationResultModel,
    QueryResultModel,
    dump_target,
    make_report,
    validate_output,
)


@dataclass(frozen=True)
class _ThermFamily:
    key: str
    label: str
    identifiers: tuple[str, ...]
    getter: Callable[[str], Any]


def _therm_families() -> tuple[_ThermFamily, ...]:
    from fairyfly_next_therm.lib.conditions import CONDITIONS, condition_by_name
    from fairyfly_next_therm.lib.gases import GASES, PURE_GASES, gas_by_name, pure_gas_by_name
    from fairyfly_next_therm.lib.materials import (
        CAVITY_MATERIALS,
        SOLID_MATERIALS,
        cavity_material_by_name,
        solid_material_by_name,
    )

    return (
        _ThermFamily("solid_material", "SolidMaterial", tuple(SOLID_MATERIALS), solid_material_by_name),
        _ThermFamily("cavity_material", "CavityMaterial", tuple(CAVITY_MATERIALS), cavity_material_by_name),
        _ThermFamily("condition", "Condition", tuple(CONDITIONS), condition_by_name),
        _ThermFamily("gas", "Gas", tuple(GASES), gas_by_name),
        _ThermFamily("pure_gas", "PureGas", tuple(PURE_GASES), pure_gas_by_name),
    )


def _selected_therm_families(object_family: str | None) -> tuple[_ThermFamily, ...]:
    families = _therm_families()
    if object_family is None or not object_family.strip() or object_family.strip().lower() == "all":
        return families
    norm = object_family.strip().lower().replace("-", "_")
    aliases: dict[str, tuple[str, ...]] = {
        "materials": ("solid_material", "cavity_material"),
        "material": ("solid_material", "cavity_material"),
        "conditions": ("condition",),
        "gases": ("gas", "pure_gas"),
    }
    keys = aliases.get(norm, (norm,))
    by_key = {f.key: f for f in families}
    selected = tuple(by_key[k] for k in keys if k in by_key)
    if not selected:
        allowed = ", ".join(["all", "materials", "conditions", "gases", *by_key])
        raise ValueError(f"THERM object_family must be one of: {allowed}.")
    return selected


def _score_text(candidate: str, query: str) -> int:
    tokens = [tok for tok in query.lower().replace("_", " ").replace("-", " ").split() if tok]
    if not tokens:
        return 1
    lowered = candidate.lower().replace("_", " ").replace("-", " ")
    score = 20 if query.lower() in candidate.lower() else 0
    for token in tokens:
        if token in lowered:
            score += 4
        if lowered.startswith(token):
            score += 2
    return score


def _search_therm_library(
    *,
    query: str,
    object_family: str | None,
    limit: int,
) -> dict[str, Any]:
    if limit < 1:
        raise ValueError("limit must be greater than zero.")
    matches: list[dict[str, Any]] = []
    for family in _selected_therm_families(object_family):
        for name in family.identifiers:
            score = _score_text(name, query)
            if score <= 0:
                continue
            matches.append(
                {
                    "object_family": family.key,
                    "object_type": family.label,
                    "identifier": name,
                    "display_name": name,
                    "score": score,
                }
            )
    matches.sort(key=lambda item: (-item["score"], item["object_family"], item["identifier"]))
    limited = matches[:limit]
    return {
        "matches": limited,
        "identifiers": [m["identifier"] for m in limited],
        "summary_view": {
            "domain": "therm",
            "query": query,
            "object_family": object_family or "all",
            "match_count": len(limited),
            "total_matches": len(matches),
            "identifiers": [m["identifier"] for m in limited],
            "available_families": [f.key for f in _therm_families()],
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(limited)} Fairyfly THERM library record(s).",
        ),
    }


def _get_therm_library_object(*, identifier: str, object_family: str | None) -> dict[str, Any]:
    target = identifier.strip()
    if not target:
        raise ValueError("identifier is required when action='get'.")
    families = _selected_therm_families(object_family)
    for family in families:
        exact = next((name for name in family.identifiers if name == target), None)
        if exact is None:
            lowered = target.lower()
            exact = next((name for name in family.identifiers if name.lower() == lowered), None)
        if exact is None:
            for name in family.identifiers:
                obj = family.getter(name)
                if getattr(obj, "identifier", None) == target:
                    exact = name
                    break
        if exact is not None:
            obj = family.getter(exact)
            obj_dict = obj.to_dict() if hasattr(obj, "to_dict") else {}
            props = {k: v for k, v in obj_dict.items() if k != "type"}
            return {
                "domain": "therm",
                "object_family": family.key,
                "object_type": family.label,
                "identifier": getattr(obj, "display_name", None) or exact,
                "sdk_identifier": getattr(obj, "identifier", None),
                "properties": props,
                "object_dict": obj_dict,
                "summary_view": {
                    "domain": "therm",
                    "object_family": family.key,
                    "object_type": family.label,
                    "identifier": getattr(obj, "display_name", None) or exact,
                    "body_returned": True,
                },
                "report": make_report(
                    status="ok",
                    message=f"Loaded Fairyfly THERM {family.label}: {exact}.",
                ),
            }
    raise ValueError(f"Fairyfly THERM standards object {identifier!r} was not found.")


def _get_radiance_library_object(*, identifier: str, object_family: str | None) -> dict[str, Any]:
    from honeybee_radiance.lib.modifiers import MODIFIERS, modifier_by_identifier
    from honeybee_radiance.lib.modifiersets import MODIFIER_SETS, modifier_set_by_identifier

    target = identifier.strip()
    if not target:
        raise ValueError("identifier is required when action='get'.")

    norm_family = (object_family or "all").strip().lower().replace("-", "_")
    if norm_family not in {"all", "modifier", "modifier_set"}:
        raise ValueError("Radiance object_family must be one of: all, modifier, modifier_set.")

    candidates: list[tuple[str, str, tuple[str, ...], Callable[[str], Any]]] = []
    if norm_family in {"all", "modifier"}:
        candidates.append(("modifier", "Modifier", tuple(MODIFIERS), modifier_by_identifier))
    if norm_family in {"all", "modifier_set"}:
        candidates.append(("modifier_set", "ModifierSet", tuple(MODIFIER_SETS), modifier_set_by_identifier))

    for fam_key, fam_label, pool, getter in candidates:
        matched = next((item for item in pool if item == target), None)
        if matched is None:
            lowered = target.lower()
            matched = next((item for item in pool if item.lower() == lowered), None)
        if matched is not None:
            obj = getter(matched)
            obj_dict = obj.to_dict()
            props = {k: v for k, v in obj_dict.items() if k not in {"type", "identifier"}}
            return {
                "domain": "radiance",
                "object_family": fam_key,
                "object_type": fam_label,
                "identifier": matched,
                "properties": props,
                "object_dict": obj_dict,
                "summary_view": {
                    "domain": "radiance",
                    "object_family": fam_key,
                    "object_type": fam_label,
                    "identifier": matched,
                    "body_returned": True,
                },
                "report": make_report(
                    status="ok",
                    message=f"Loaded Honeybee Radiance {fam_label}: {matched}.",
                ),
            }
    raise ValueError(f"Honeybee Radiance standards object {identifier!r} was not found.")


def _get_opendss_library_object(
    *,
    identifier: str,
    object_family: str | None,
    catalogs: list[str] | None,
) -> dict[str, Any]:
    from dragonfly_energy.opendss.lib.powerlines import POWER_LINES, power_line_by_identifier
    from dragonfly_energy.opendss.lib.transformers import (
        TRANSFORMER_PROPERTIES,
        transformer_prop_by_identifier,
    )
    from dragonfly_energy.opendss.lib.wires import WIRES, wire_by_identifier

    target = identifier.strip()
    if not target:
        raise ValueError("identifier is required when action='get'.")

    catalog_map: dict[str, tuple[str, tuple[str, ...], Callable[[str], Any]]] = {
        "transformer_properties": ("TransformerProperties", tuple(TRANSFORMER_PROPERTIES), transformer_prop_by_identifier),
        "power_lines": ("PowerLine", tuple(POWER_LINES), power_line_by_identifier),
        "wires": ("Wire", tuple(WIRES), wire_by_identifier),
    }
    selected = (
        catalogs
        if catalogs is not None
        else ([object_family] if object_family and object_family != "all" else list(catalog_map))
    )
    unknown = [cat for cat in selected if cat not in catalog_map]
    if unknown:
        allowed = ", ".join(sorted(catalog_map))
        raise ValueError(f"Unknown OpenDSS catalog(s): {unknown}. Allowed: {allowed}.")

    for catalog in selected:
        label, pool, getter = catalog_map[catalog]
        matched = next((item for item in pool if item == target), None)
        if matched is None:
            lowered = target.lower()
            matched = next((item for item in pool if item.lower() == lowered), None)
        if matched is not None:
            obj = getter(matched)
            obj_dict = obj.to_dict()
            props = {k: v for k, v in obj_dict.items() if k not in {"type", "identifier"}}
            return {
                "domain": "opendss",
                "catalog": catalog,
                "object_family": catalog,
                "object_type": label,
                "identifier": matched,
                "properties": props,
                "object_dict": obj_dict,
                "summary_view": {
                    "domain": "opendss",
                    "catalog": catalog,
                    "object_type": label,
                    "identifier": matched,
                    "body_returned": True,
                },
                "report": make_report(
                    status="ok",
                    message=f"Loaded OpenDSS {label}: {matched}.",
                ),
            }
    raise ValueError(f"OpenDSS standards object {identifier!r} was not found.")


def register(mcp: FastMCP) -> None:
    """Register libraries tools."""

    @mcp.tool(
        name="GD_Properties_Library",
        description=(
            "Search, read, or save reusable Honeybee Energy or Honeybee Radiance objects "
            "in the Garden Properties Library (schedules, program types, loads, HVAC systems, "
            "materials, constructions, construction sets, modifiers, modifier sets, luminaires). "
            "Use action='search' to list/filter saved Garden library targets, action='get' to read "
            "one object_dict by target or (domain, object_family, identifier), and action='save' to "
            "persist an existing complete SDK object_dict into the Garden library."
        ),
        tags={
            "energy",
            "library",
            "properties",
            "radiance",
            "search",
            "target",
        },
        timeout=20,
    )
    def garden_properties_library(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        action: Annotated[
            Literal["search", "get", "save"],
            Field(
                description="Library operation: 'search' saved targets, 'get' one object_dict, or 'save' an object_dict."
            ),
        ],
        query: Annotated[
            str,
            Field(
                description=(
                    "For action='search': text matched against saved identifiers and SDK object_type values; "
                    "leave empty to list recent objects in the selected domain/object_family."
                )
            ),
        ] = "",
        domain: Annotated[
            str | None,
            Field(
                description=(
                    "Library domain: 'honeybee_energy', 'honeybee_radiance', or 'all' (search only). "
                    "Required for action='save' and for action='get' when target is omitted."
                )
            ),
        ] = None,
        object_family: Annotated[
            str | None,
            Field(
                description=(
                    "Object family such as schedule, schedule_type_limit, program_type, load, hvac, "
                    "material, construction, construction_set, modifier, modifier_set, or luminaire. "
                    "Required for action='save' and for action='get' when target is omitted."
                )
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(
                description=(
                    "Object identifier. Used with domain and object_family for action='get' when target "
                    "is omitted, or as an optional identifier override for action='save'."
                )
            ),
        ] = None,
        target: Annotated[
            LibraryObjectTargetRef | None,
            Field(
                description=(
                    "For action='get': optional garden_properties_library_object target from "
                    "GD_Properties_Library(action='search')['matches'][i]['target']."
                )
            ),
        ] = None,
        object_dict: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "For action='save': complete Honeybee Energy or Honeybee Radiance SDK object_dict "
                    "to validate and persist into the Garden Properties Library."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(
                description="For action='save': overwrite an existing object with the same domain, object_family, and identifier."
            ),
        ] = True,
        limit: Annotated[
            int,
            Field(
                description="For action='search': maximum number of Garden-saved matches to return.",
                ge=1,
            ),
        ] = 10,
    ) -> MutationResultModel:
        """Search, read, or save objects in the Garden Properties Library."""
        if action == "search":
            from garden.libraries.properties import (
                search_garden_properties_library_objects as service,
            )

            return validate_output(
                MutationResultModel,
                service(
                    garden_root=garden_root,
                    query=query,
                    domain=domain,
                    object_family=object_family,
                    limit=limit,
                ),
            )
        if action == "get":
            from garden.libraries.properties import (
                get_garden_properties_library_object as service,
            )

            return validate_output(
                MutationResultModel,
                service(
                    garden_root=garden_root,
                    target=dump_target(target),
                    domain=domain,
                    object_family=object_family,
                    identifier=identifier,
                ),
            )
        if not domain or not object_family or object_dict is None:
            raise ValueError(
                "action='save' requires domain, object_family, and object_dict."
            )
        from garden.libraries.properties import (
            save_garden_properties_library_object as service,
        )

        return validate_output(
            MutationResultModel,
            service(
                garden_root=garden_root,
                domain=domain,
                object_family=object_family,
                object_dict=object_dict,
                identifier=identifier,
                overwrite=overwrite,
            ),
        )

    @mcp.tool(
        name="LB_Search_Standards_Library",
        description=(
            "Search or inspect built-in Ladybug Tools standards catalogs across Energy (schedules, "
            "program types, materials, constructions, construction sets), Radiance (modifiers, "
            "modifier sets), OpenDSS electrical catalogs (transformer_properties, power_lines, wires), "
            "and Fairyfly THERM catalogs (solid_material, cavity_material, condition, gas, pure_gas). "
            "Use action='search' (with optional structured filters climate_zone, vintage, "
            "construction_type, building_type) for compact matches, or action='get' with identifier "
            "to inspect full properties, U-values, layers, schedules, and object_dict."
        ),
        tags={
            "energy",
            "library",
            "opendss",
            "radiance",
            "search",
            "standards",
            "therm",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_standards_library(
        query: Annotated[
            str,
            Field(
                description="For action='search': search text or keywords matched against standards identifiers (optional when structured filters or action='get' are used)."
            ),
        ] = "",
        action: Annotated[
            Literal["search", "get"],
            Field(
                description="Operation mode: 'search' catalog identifiers or 'get' full object properties and object_dict."
            ),
        ] = "search",
        domain: Annotated[
            Literal["energy", "radiance", "opendss", "therm"],
            Field(
                description="Standards catalog domain: 'energy', 'radiance', 'opendss', or 'therm'."
            ),
        ] = "energy",
        object_family: Annotated[
            str | None,
            Field(
                description=(
                    "Optional family/catalog filter: for energy use schedule, schedule_type_limit, "
                    "program_type, opaque_material, window_material, opaque_construction, "
                    "window_construction, shade_construction, construction_set, or all; for radiance use "
                    "modifier, modifier_set, or all; for opendss pass a catalog name; for therm use "
                    "solid_material, cavity_material, condition, gas, pure_gas, materials, conditions, gases, or all."
                )
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(
                description="For action='get': exact standards identifier (or display name for THERM) to inspect."
            ),
        ] = None,
        catalogs: Annotated[
            list[Literal["transformer_properties", "power_lines", "wires"]] | None,
            Field(
                description=(
                    "Optional OpenDSS catalog filter list when domain='opendss': "
                    "transformer_properties, power_lines, or wires."
                )
            ),
        ] = None,
        climate_zone: Annotated[
            str | None,
            Field(
                description="Optional Energy filter such as '4', '4A', or 'ClimateZone4'."
            ),
        ] = None,
        vintage: Annotated[
            str | None,
            Field(
                description="Optional Energy vintage/standard filter such as '2019', '2016', '1980_2004', 'pre_1980', or 'GB55015-2021'."
            ),
        ] = None,
        construction_type: Annotated[
            str | None,
            Field(
                description="Optional Energy construction type filter such as 'SteelFramed', 'WoodFramed', 'Mass', or 'Metal Building'."
            ),
        ] = None,
        building_type: Annotated[
            str | None,
            Field(
                description="Optional Energy building/program filter such as 'Office', 'MediumOffice', 'Hospital', 'School', or 'Hotel'."
            ),
        ] = None,
        limit: Annotated[
            int,
            Field(description="Maximum number of matching standards identifiers to return.", ge=1),
        ] = 10,
    ) -> QueryResultModel:
        """Search or inspect built-in Energy, Radiance, OpenDSS, or THERM standards catalogs."""
        if action == "get":
            target_identifier = (identifier if identifier is not None else query).strip()
            if domain == "energy":
                from garden.energy.libraries import get_energy_library_object

                return validate_output(
                    QueryResultModel,
                    get_energy_library_object(
                        identifier=target_identifier,
                        object_family=object_family,
                    ),
                )
            if domain == "radiance":
                return validate_output(
                    QueryResultModel,
                    _get_radiance_library_object(
                        identifier=target_identifier,
                        object_family=object_family,
                    ),
                )
            if domain == "opendss":
                return validate_output(
                    QueryResultModel,
                    _get_opendss_library_object(
                        identifier=target_identifier,
                        object_family=object_family,
                        catalogs=catalogs,
                    ),
                )
            return validate_output(
                QueryResultModel,
                _get_therm_library_object(
                    identifier=target_identifier,
                    object_family=object_family,
                ),
            )

        if domain == "energy":
            from garden.energy.libraries import search_energy_library_objects

            return validate_output(
                QueryResultModel,
                search_energy_library_objects(
                    query=query,
                    object_family=object_family,
                    climate_zone=climate_zone,
                    vintage=vintage,
                    construction_type=construction_type,
                    building_type=building_type,
                    limit=limit,
                ),
            )
        if domain == "radiance":
            from garden.radiance.libraries import search_radiance_library_objects

            return validate_output(
                QueryResultModel,
                search_radiance_library_objects(
                    query=query,
                    object_family=object_family,
                    limit=limit,
                ),
            )
        if domain == "therm":
            return validate_output(
                QueryResultModel,
                _search_therm_library(
                    query=query,
                    object_family=object_family,
                    limit=limit,
                ),
            )
        from garden.dragonfly_grid.authoring import search_opendss

        tokens = [token for token in query.replace(",", " ").split() if token] or None
        resolved_catalogs = (
            catalogs
            if catalogs is not None
            else ([object_family] if object_family and object_family != "all" else None)
        )
        return validate_output(
            QueryResultModel,
            search_opendss(
                keywords=tokens,
                catalogs=resolved_catalogs,
                limit=limit,
            ),
        )
