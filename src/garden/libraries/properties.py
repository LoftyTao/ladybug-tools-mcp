"""Garden Properties Library file-backed object store."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from honeybee_energy.construction.dictutil import dict_to_construction
from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.generator.loadcenter import ElectricLoadCenter
from honeybee_energy.generator.pv import PVProperties
from honeybee_energy.load.dictutil import dict_to_load
from honeybee_energy.material.dictutil import dict_to_material
from honeybee_energy.hvac import HVAC_TYPES_DICT
from honeybee_energy.hvac._base import _HVACSystem
from honeybee_energy.programtype import ProgramType
from honeybee_energy.schedule.dictutil import dict_to_schedule
from honeybee_energy.schedule.typelimit import ScheduleTypeLimit
from honeybee_energy.ventcool.fan import VentilationFan
from honeybee_radiance.dictutil import dict_to_object as dict_to_radiance_object
from honeybee_radiance.luminaire import Luminaire
from honeybee_radiance.modifier.modifierbase import Modifier
from honeybee_radiance.modifierset import ModifierSet

from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report
from ladybug_tools_mcp.contracts.targets import make_garden_properties_library_target
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative


Validator = Callable[[dict[str, Any]], Any]
IndexEntry = dict[str, Any]


@dataclass(frozen=True)
class _FamilySpec:
    domain: str
    key: str
    folder: str
    label: str
    validator: Validator


def _validate_schedule(data: dict[str, Any]) -> Any:
    return dict_to_schedule(data)


def _validate_schedule_type_limit(data: dict[str, Any]) -> Any:
    return ScheduleTypeLimit.from_dict(data)


def _validate_program_type(data: dict[str, Any]) -> Any:
    return ProgramType.from_dict(data)


def _validate_load(data: dict[str, Any]) -> Any:
    return dict_to_load(data)


def _validate_hvac(data: dict[str, Any]) -> Any:
    hvac_type = data.get("type") if isinstance(data, dict) else None
    if not isinstance(hvac_type, str):
        raise ValueError("object_dict is not a Honeybee Energy HVAC dictionary.")
    hvac_cls = HVAC_TYPES_DICT.get(hvac_type)
    if hvac_cls is None:
        allowed = ", ".join(sorted(HVAC_TYPES_DICT))
        raise ValueError(f"Unsupported Honeybee Energy HVAC type: {hvac_type}. Supported: {allowed}.")
    obj = hvac_cls.from_dict(data)
    if not isinstance(obj, _HVACSystem):
        raise ValueError("object_dict is not a Honeybee Energy HVAC object.")
    return obj


def _validate_material(data: dict[str, Any]) -> Any:
    return dict_to_material(data)


def _validate_construction(data: dict[str, Any]) -> Any:
    return dict_to_construction(data)


def _validate_construction_set(data: dict[str, Any]) -> Any:
    return ConstructionSet.from_dict(data)


def _validate_zone_ventilation_fan(data: dict[str, Any]) -> Any:
    return VentilationFan.from_dict(data)


def _validate_pv_properties(data: dict[str, Any]) -> Any:
    return PVProperties.from_dict(data)


def _validate_electric_load_center(data: dict[str, Any]) -> Any:
    return ElectricLoadCenter.from_dict(data)


def _validate_modifier(data: dict[str, Any]) -> Any:
    obj = dict_to_radiance_object(data)
    if not isinstance(obj, Modifier) or isinstance(obj, ModifierSet):
        raise ValueError("object_dict is not a Honeybee Radiance modifier.")
    return obj


def _validate_modifier_set(data: dict[str, Any]) -> Any:
    obj = dict_to_radiance_object(data)
    if not isinstance(obj, ModifierSet):
        raise ValueError("object_dict is not a Honeybee Radiance modifier set.")
    return obj


def _validate_luminaire(data: dict[str, Any]) -> Any:
    obj = Luminaire.from_dict(data)
    if not isinstance(obj, Luminaire):
        raise ValueError("object_dict is not a Honeybee Radiance Luminaire.")
    return obj


_FAMILY_SPECS = (
    _FamilySpec("honeybee_energy", "schedule", "schedules", "Schedule", _validate_schedule),
    _FamilySpec(
        "honeybee_energy",
        "schedule_type_limit",
        "schedule_type_limits",
        "ScheduleTypeLimit",
        _validate_schedule_type_limit,
    ),
    _FamilySpec(
        "honeybee_energy",
        "program_type",
        "program_types",
        "ProgramType",
        _validate_program_type,
    ),
    _FamilySpec("honeybee_energy", "load", "loads", "Load", _validate_load),
    _FamilySpec("honeybee_energy", "hvac", "hvacs", "HVAC", _validate_hvac),
    _FamilySpec("honeybee_energy", "material", "materials", "Material", _validate_material),
    _FamilySpec(
        "honeybee_energy",
        "construction",
        "constructions",
        "Construction",
        _validate_construction,
    ),
    _FamilySpec(
        "honeybee_energy",
        "construction_set",
        "construction_sets",
        "ConstructionSet",
        _validate_construction_set,
    ),
    _FamilySpec(
        "honeybee_energy",
        "zone_ventilation_fan",
        "zone_ventilation_fans",
        "ZoneVentilationFan",
        _validate_zone_ventilation_fan,
    ),
    _FamilySpec(
        "honeybee_energy",
        "pv_properties",
        "pv_properties",
        "PVProperties",
        _validate_pv_properties,
    ),
    _FamilySpec(
        "honeybee_energy",
        "electric_load_center",
        "electric_load_centers",
        "ElectricLoadCenter",
        _validate_electric_load_center,
    ),
    _FamilySpec("honeybee_radiance", "modifier", "modifiers", "Modifier", _validate_modifier),
    _FamilySpec(
        "honeybee_radiance",
        "modifier_set",
        "modifier_sets",
        "ModifierSet",
        _validate_modifier_set,
    ),
    _FamilySpec(
        "honeybee_radiance",
        "luminaire",
        "luminaires",
        "Luminaire",
        _validate_luminaire,
    ),
)
_SPECS_BY_KEY = {(spec.domain, spec.key): spec for spec in _FAMILY_SPECS}


def _garden_root(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _family_spec(domain: str, object_family: str) -> _FamilySpec:
    try:
        return _SPECS_BY_KEY[(domain, object_family)]
    except KeyError as exc:
        allowed = ", ".join(f"{spec.domain}:{spec.key}" for spec in _FAMILY_SPECS)
        raise ValueError(f"Unsupported Garden Properties Library family. Allowed: {allowed}.") from exc


def _identifier_from_object(obj: Any, object_dict: dict[str, Any], override: str | None) -> str:
    object_identifier = getattr(obj, "identifier", None) or object_dict.get("identifier")
    if override and object_identifier and str(override) != str(object_identifier):
        raise ValueError(
            "identifier_ must match the SDK object's own identifier when one is present."
        )
    identifier = override or object_identifier
    if not identifier:
        raise ValueError("Garden Properties Library objects must have an identifier.")
    return str(identifier)


def _object_type(obj: Any, object_dict: dict[str, Any]) -> str:
    return str(object_dict.get("type") or obj.__class__.__name__)


def _object_to_dict(obj: Any, fallback: dict[str, Any]) -> dict[str, Any]:
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return fallback


def _family_dir(garden_root: Path, spec: _FamilySpec) -> Path:
    return garden_root / "libraries" / spec.domain / spec.folder


def _index_path(garden_root: Path, spec: _FamilySpec) -> Path:
    return _family_dir(garden_root, spec) / "index.json"


def _read_index(garden_root: Path, spec: _FamilySpec) -> dict[str, Any]:
    path = _index_path(garden_root, spec)
    if not path.is_file():
        return {
            "schema_version": "1",
            "domain": spec.domain,
            "object_family": spec.key,
            "objects": [],
        }
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_index(garden_root: Path, spec: _FamilySpec, index: dict[str, Any]) -> None:
    path = _index_path(garden_root, spec)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(path, index)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _record_path(garden_root: Path, target: dict[str, Any]) -> Path:
    path = (garden_root / str(target["path"])).resolve()
    path.relative_to(garden_root.resolve())
    return path


def _read_record(garden_root: Path, target: dict[str, Any]) -> dict[str, Any]:
    with _record_path(garden_root, target).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _is_legacy_record(data: Any) -> bool:
    return (
        isinstance(data, dict)
        and isinstance(data.get("object_dict"), dict)
        and isinstance(data.get("domain"), str)
        and isinstance(data.get("object_family"), str)
    )


def _extract_object_dict(data: Any) -> dict[str, Any]:
    if _is_legacy_record(data):
        return dict(data["object_dict"])
    if not isinstance(data, dict):
        raise ValueError("Garden Properties Library file must contain a JSON object.")
    return dict(data)


def _find_index_entry(
    index: dict[str, Any],
    *,
    target: dict[str, Any] | None = None,
    identifier: str | None = None,
    path: str | None = None,
) -> IndexEntry | None:
    for item in index.get("objects", []):
        item_target = item.get("target")
        if not isinstance(item_target, dict):
            continue
        if target is not None and item_target == target:
            return item
        if path is not None and item.get("path") == path:
            return item
        if identifier is not None and item.get("identifier") == identifier:
            return item
    return None


def _resolved_object_type(
    *,
    obj: Any,
    object_dict: dict[str, Any],
    index_entry: IndexEntry | None,
    legacy_record: dict[str, Any] | None = None,
) -> str:
    return str(
        (index_entry or {}).get("object_type")
        or (legacy_record or {}).get("object_type")
        or _object_type(obj, object_dict)
    )


def _score(identifier: str, object_type: str, query: str) -> int:
    if not query:
        return 1
    text = f"{identifier} {object_type}".lower().replace("_", " ").replace("-", " ")
    tokens = [token for token in query.lower().replace("_", " ").replace("-", " ").split() if token]
    score = 0
    if query.lower() in text:
        score += 20
    for token in tokens:
        if token in text:
            score += 4
        if text.startswith(token):
            score += 2
    return score


def save_garden_properties_library_object(
    *,
    garden_root: str,
    domain: str,
    object_family: str,
    object_dict: dict[str, Any],
    identifier: str | None = None,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Save one SDK object dict as a Garden Properties Library resource."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    spec = _family_spec(domain, object_family)
    obj = spec.validator(object_dict)
    object_dict = _object_to_dict(obj, object_dict)
    identifier = _identifier_from_object(obj, object_dict, identifier)
    object_type = _object_type(obj, object_dict)

    folder = _family_dir(root, spec)
    folder.mkdir(parents=True, exist_ok=True)
    object_path = folder / f"{slugify_name(identifier)}.json"
    if object_path.exists() and not overwrite:
        raise ValueError(f"Garden Properties Library object already exists: {identifier}")

    persisted_path = to_posix_relative(object_path, root)
    target = make_garden_properties_library_target(
        manifest.garden_id,
        domain=domain,
        object_family=object_family,
        identifier=identifier,
        path=persisted_path,
    )
    updated_at = utc_now_iso()
    _write_json(object_path, object_dict)

    index = _read_index(root, spec)
    objects = [
        item
        for item in index.get("objects", [])
        if item.get("identifier") != identifier
    ]
    objects.append(
        {
            "identifier": identifier,
            "object_type": object_type,
            "path": persisted_path,
            "target": target,
            "updated_at": updated_at,
        }
    )
    objects.sort(key=lambda item: item["identifier"])
    index["objects"] = objects
    _write_index(root, spec, index)

    return {
        "object_dict": object_dict,
        "target": target,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "domain": domain,
            "object_family": object_family,
            "identifier": identifier,
            "object_type": object_type,
        },
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            persisted_path=persisted_path,
            change_summary={
                "operation": "save_garden_properties_library_object",
                "target": target,
                "index_path": to_posix_relative(_index_path(root, spec), root),
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Saved Garden Properties Library object: {identifier}",
        ),
    }


def get_garden_properties_library_object(
    *,
    garden_root: str,
    target: dict[str, Any] | None = None,
    domain: str | None = None,
    object_family: str | None = None,
    identifier: str | None = None,
) -> dict[str, Any]:
    """Read one Garden Properties Library resource."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    if target is None:
        if not domain or not object_family or not identifier:
            raise ValueError("Provide target or domain, object_family, and identifier.")
        spec = _family_spec(domain, object_family)
        index = _read_index(root, spec)
        index_entry = _find_index_entry(index, identifier=identifier)
        if index_entry is None:
            raise ValueError(f"Garden Properties Library object not found: {identifier}")
        target = index_entry["target"]
    if target.get("target_type") != "garden_properties_library_object":
        raise ValueError("target must be a Garden Properties Library object target.")
    if target.get("garden_id") != manifest.garden_id:
        raise ValueError("target belongs to a different Garden.")
    spec = _family_spec(str(target["domain"]), str(target["object_family"]))
    index = _read_index(root, spec)
    index_entry = _find_index_entry(
        index,
        target=target,
        identifier=str(target.get("identifier") or ""),
        path=str(target.get("path") or ""),
    )
    record = _read_record(root, target)
    object_dict = _extract_object_dict(record)
    obj = spec.validator(object_dict)
    resolved_identifier = _identifier_from_object(obj, object_dict, None)
    if (
        isinstance(target.get("identifier"), str)
        and str(target["identifier"]) != resolved_identifier
    ):
        raise ValueError(
            "Garden Properties Library file identifier does not match its target."
        )
    object_type = _resolved_object_type(
        obj=obj,
        object_dict=object_dict,
        index_entry=index_entry,
        legacy_record=record if _is_legacy_record(record) else None,
    )
    return {
        "object_dict": object_dict,
        "target": target,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": target,
            "domain": spec.domain,
            "object_family": spec.key,
            "identifier": resolved_identifier,
            "object_type": object_type,
        },
        "report": make_report(
            status="ok",
            message=f"Loaded Garden Properties Library object: {resolved_identifier}",
        ),
    }


def _selected_specs(
    domain: str | None,
    object_family: str | None,
) -> tuple[_FamilySpec, ...]:
    specs = _FAMILY_SPECS
    if domain and domain != "all":
        specs = tuple(spec for spec in specs if spec.domain == domain)
    if object_family and object_family != "all":
        specs = tuple(spec for spec in specs if spec.key == object_family)
    if not specs:
        allowed = ", ".join(f"{spec.domain}:{spec.key}" for spec in _FAMILY_SPECS)
        raise ValueError(f"No Garden Properties Library family matched. Allowed: {allowed}.")
    return specs


def search_garden_properties_library_objects(
    *,
    garden_root: str,
    query: str = "",
    domain: str | None = None,
    object_family: str | None = None,
    object_type: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search Garden Properties Library indexes."""
    if limit < 1:
        raise ValueError("limit must be greater than zero.")
    selected_family = object_family if object_family is not None else object_type
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    matches: list[dict[str, Any]] = []
    for spec in _selected_specs(domain, selected_family):
        index = _read_index(root, spec)
        for item in index.get("objects", []):
            score = _score(str(item["identifier"]), str(item.get("object_type", "")), query)
            if score <= 0:
                continue
            matches.append(
                {
                    "domain": spec.domain,
                    "object_family": spec.key,
                    "identifier": item["identifier"],
                    "object_type": item.get("object_type"),
                    "path": item.get("path"),
                    "target": item["target"],
                    "score": score,
                }
            )
    matches.sort(key=lambda item: (-item["score"], item["domain"], item["object_family"], item["identifier"]))
    limited = matches[:limit]
    return {
        "matches": limited,
        "summary_view": {
            "garden_target": manifest.target(),
            "query": query,
            "domain": domain or "all",
            "object_family": selected_family or "all",
            "match_count": len(limited),
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(limited)} Garden Properties Library object(s).",
        ),
    }


def normalize_garden_properties_library_storage(
    *,
    garden_root: str,
    domain: str | None = None,
    object_family: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Rewrite legacy MCP-wrapped Garden library files into native SDK dict files."""
    root = _garden_root(garden_root)
    manifest = GardenManifest.read(root)
    rewritten: list[dict[str, Any]] = []
    already_native: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    selected_family = object_family if object_family is not None else "all"
    for spec in _selected_specs(domain, object_family):
        index = _read_index(root, spec)
        for item in index.get("objects", []):
            target = item.get("target")
            if not isinstance(target, dict):
                skipped.append(
                    {
                        "domain": spec.domain,
                        "object_family": spec.key,
                        "identifier": item.get("identifier"),
                        "reason": "missing_target",
                    }
                )
                continue
            try:
                record = _read_record(root, target)
                object_dict = _extract_object_dict(record)
                spec.validator(object_dict)
            except Exception as exc:
                skipped.append(
                    {
                        "domain": spec.domain,
                        "object_family": spec.key,
                        "identifier": item.get("identifier") or target.get("identifier"),
                        "path": target.get("path"),
                        "reason": str(exc),
                    }
                )
                continue

            summary = {
                "domain": spec.domain,
                "object_family": spec.key,
                "identifier": item.get("identifier") or target.get("identifier"),
                "path": target.get("path"),
            }
            if _is_legacy_record(record):
                rewritten.append(summary)
                if not dry_run:
                    _write_json(_record_path(root, target), object_dict)
            else:
                already_native.append(summary)

    status = "persisted" if rewritten and not dry_run else "no_change"
    action = "Would rewrite" if dry_run else "Rewrote"
    message = (
        f"{action} {len(rewritten)} Garden Properties Library file(s); "
        f"{len(already_native)} already native."
    )
    return {
        "normalized": rewritten,
        "already_native": already_native,
        "skipped": skipped,
        "summary_view": {
            "garden_target": manifest.target(),
            "domain": domain or "all",
            "object_family": selected_family,
            "dry_run": dry_run,
            "normalized_count": len(rewritten),
            "already_native_count": len(already_native),
            "skipped_count": len(skipped),
        },
        "persistence_receipt": make_persistence_receipt(
            status=status,
            garden_id=manifest.garden_id,
            persisted_path="libraries" if rewritten and not dry_run else None,
            change_summary={
                "operation": "normalize_garden_properties_library_storage",
                "domain": domain or "all",
                "object_family": selected_family,
                "dry_run": dry_run,
                "normalized": rewritten,
                "skipped": skipped,
            },
        ),
        "report": make_report(status="ok", message=message),
    }
