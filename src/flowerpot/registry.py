"""Garden-local Flowerpot registry services."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from ladybug_tools_mcp.contracts.flowerpot import make_flowerpot
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report
from garden.manifest import GardenManifest, utc_now_iso

REGISTRY_RELATIVE_PATH = "flowerpots/registry.json"
ITEMS_RELATIVE_DIR = "flowerpots/items"
SUPPORTED_SOURCES = {"garden", "base_honeybee_model", "base_dragonfly_model", "target"}
SUPPORTED_CLEANUP_SCOPES = {"orphaned", "expired", "all"}


def _resolve_garden_root(garden_root: str) -> Path:
    root = Path(garden_root).expanduser().resolve()
    if not (root / "garden.json").is_file():
        raise ValueError(f"Garden manifest not found at {root / 'garden.json'}")
    return root


def _registry_path(garden_root: Path) -> Path:
    return garden_root / REGISTRY_RELATIVE_PATH


def _items_dir(garden_root: Path) -> Path:
    return garden_root / ITEMS_RELATIVE_DIR


def _read_registry(garden_root: Path) -> dict[str, Any]:
    path = _registry_path(garden_root)
    if not path.is_file():
        return {
            "schema_version": "1",
            "updated_at": utc_now_iso(),
            "flowerpots": [],
        }
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    data.setdefault("schema_version", "1")
    data.setdefault("flowerpots", [])
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def _write_registry(garden_root: Path, registry: dict[str, Any]) -> None:
    registry["updated_at"] = utc_now_iso()
    _write_json(_registry_path(garden_root), registry)


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _normalize_source(source: str | None) -> str:
    normalized = str(source or "garden").strip().lower()
    if normalized not in SUPPORTED_SOURCES:
        allowed = ", ".join(sorted(SUPPORTED_SOURCES))
        raise ValueError(f"source must be one of: {allowed}.")
    return normalized


def _target_for_source(
    *,
    manifest: GardenManifest,
    source: str,
    target: dict[str, Any] | None,
) -> dict[str, Any]:
    if source == "garden":
        if target is not None and target != manifest.target():
            _validate_typed_target(target)
            return target
        return manifest.target()
    if source == "base_honeybee_model":
        if not manifest.base_honeybee_model:
            raise ValueError(
                "Garden has no base Honeybee model for a base_honeybee_model Flowerpot."
            )
        if target is not None and target != manifest.base_honeybee_model:
            _validate_typed_target(target)
            return target
        return manifest.base_honeybee_model
    if source == "base_dragonfly_model":
        if not manifest.base_dragonfly_model:
            raise ValueError(
                "Garden has no base Dragonfly model for a base_dragonfly_model Flowerpot."
            )
        if target is not None and target != manifest.base_dragonfly_model:
            _validate_typed_target(target)
            return target
        return manifest.base_dragonfly_model

    if target is None:
        raise ValueError("target is required when source is 'target'.")
    _validate_typed_target(target)
    return target


def _validate_typed_target(target: dict[str, Any]) -> None:
    if not isinstance(target, dict) or not target.get("target_type"):
        raise ValueError(
            "Flowerpot targets must be registered Garden typed targets with "
            "a target_type field; inline payload bodies are not supported."
        )


def _label_for_source(
    *,
    manifest: GardenManifest,
    source: str,
    target: dict[str, Any],
    label: str | None,
) -> str:
    if label:
        return str(label)
    if source == "garden":
        return manifest.name
    if source in {"base_honeybee_model", "base_dragonfly_model"}:
        return str(target.get("model_identifier") or f"{manifest.name} {source}")
    return str(target.get("identifier") or target.get("target_type") or "Flowerpot")


def _summary_for_flowerpot(
    *,
    flowerpot_id: str | None,
    flowerpot: dict[str, Any],
    source: str | None = None,
    item_path: str | None = None,
    garden_root: str | None = None,
) -> dict[str, Any]:
    target = flowerpot.get("target") if isinstance(flowerpot, dict) else {}
    payload_context = flowerpot.get("payload_context", {})
    summary = {
        "flowerpot_id": flowerpot_id,
        "kind": flowerpot.get("kind"),
        "label": flowerpot.get("label"),
        "source": source or payload_context.get("source"),
        "target": target,
        "platform": flowerpot.get("platform", {}),
        "file_path": item_path,
        "body_returned": False,
    }
    context_garden_root = garden_root or payload_context.get("garden_root")
    if context_garden_root:
        summary["garden_root"] = str(Path(context_garden_root).expanduser().resolve())
    return summary


def _item_path(garden_root: Path, flowerpot_id: str) -> Path:
    return _items_dir(garden_root) / f"{flowerpot_id}.json"


def _read_item(garden_root: Path, flowerpot_id: str) -> dict[str, Any]:
    path = _item_path(garden_root, flowerpot_id)
    if not path.is_file():
        raise ValueError(f"Flowerpot not found: {flowerpot_id}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _match_for_item(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "flowerpot_id": entry["flowerpot_id"],
        "kind": entry.get("kind"),
        "label": entry.get("label"),
        "target": entry.get("target", {}),
        "source": entry.get("source"),
        "platform": entry.get("platform", {}),
        "summary": entry.get("summary", {}),
        "file_path": entry.get("file_path"),
        "created_at": entry.get("created_at"),
        "updated_at": entry.get("updated_at"),
    }


def _platform_key(platform: dict[str, Any]) -> str:
    return json.dumps(platform or {}, sort_keys=True, separators=(",", ":"))


def _find_reusable_entry(
    registry: dict[str, Any],
    *,
    source: str,
    target: dict[str, Any],
    platform: dict[str, Any],
) -> dict[str, Any] | None:
    for entry in reversed(registry.get("flowerpots", [])):
        if entry.get("source") != source:
            continue
        if entry.get("target") != target:
            continue
        if _platform_key(entry.get("platform", {})) != _platform_key(platform):
            continue
        return entry
    return None


def create_flowerpot(
    *,
    garden_root: str,
    source: str = "garden",
    target: dict[str, Any] | None = None,
    label: str | None = None,
    platform: dict[str, Any] | None = None,
    force_new: bool = False,
) -> dict[str, Any]:
    """Create and register a Garden-local Flowerpot from an existing target."""
    garden_root_path = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    source = _normalize_source(source)
    selected_target = _target_for_source(
        manifest=manifest,
        source=source,
        target=target,
    )
    selected_label = _label_for_source(
        manifest=manifest,
        source=source,
        target=selected_target,
        label=label,
    )
    now = utc_now_iso()
    platform_context = platform or {}
    registry = _read_registry(garden_root_path)
    if not force_new:
        existing_entry = _find_reusable_entry(
            registry,
            source=source,
            target=selected_target,
            platform=platform_context,
        )
        if existing_entry is not None:
            flowerpot_id = str(existing_entry["flowerpot_id"])
            item = _read_item(garden_root_path, flowerpot_id)
            flowerpot = item["flowerpot"]
            summary = _summary_for_flowerpot(
                flowerpot_id=flowerpot_id,
                flowerpot=flowerpot,
                source=existing_entry.get("source"),
                item_path=existing_entry.get("file_path"),
                garden_root=str(garden_root_path),
            )
            summary["reused"] = True
            return {
                "flowerpot": flowerpot,
                "flowerpot_id": flowerpot_id,
                "target": flowerpot.get("target", selected_target),
                "summary_view": summary,
                "persistence_receipt": make_persistence_receipt(
                    status="no_change",
                    garden_id=manifest.garden_id,
                    persisted_path=existing_entry.get("file_path"),
                    change_summary={
                        "operation": "create_flowerpot",
                        "source": source,
                        "flowerpot_id": flowerpot_id,
                        "registry_path": REGISTRY_RELATIVE_PATH,
                        "reused": True,
                    },
                ),
                "report": make_report(
                    status="ok",
                    message=f"Reused Flowerpot: {selected_label}",
                    details={"garden_root": str(garden_root_path)},
                ),
            }

    flowerpot_id = f"flowerpot_{uuid4().hex[:12]}"
    flowerpot = make_flowerpot(
        kind=source,
        label=selected_label,
        target=selected_target,
        payload_context={
            "source": source,
            "flowerpot_id": flowerpot_id,
            "garden_id": manifest.garden_id,
            "garden_root": str(garden_root_path),
        },
        platform=platform_context,
    )
    item_path = _item_path(garden_root_path, flowerpot_id)
    item_relative_path = _relative(item_path, garden_root_path)
    summary = _summary_for_flowerpot(
        flowerpot_id=flowerpot_id,
        flowerpot=flowerpot,
        source=source,
        item_path=item_relative_path,
        garden_root=str(garden_root_path),
    )
    summary["reused"] = False
    entry = {
        "flowerpot_id": flowerpot_id,
        "created_at": now,
        "updated_at": now,
        "kind": source,
        "label": selected_label,
        "target": selected_target,
        "source": source,
        "platform": platform_context,
        "summary": summary,
        "file_path": item_relative_path,
    }
    item = {
        "schema_version": "1",
        "flowerpot_id": flowerpot_id,
        "created_at": now,
        "updated_at": now,
        "flowerpot": flowerpot,
        "registry_entry": entry,
    }
    _write_json(item_path, item)

    registry["flowerpots"] = [
        existing
        for existing in registry.get("flowerpots", [])
        if existing.get("flowerpot_id") != flowerpot_id
    ]
    registry["flowerpots"].append(entry)
    _write_registry(garden_root_path, registry)

    return {
        "flowerpot": flowerpot,
        "flowerpot_id": flowerpot_id,
        "target": selected_target,
        "summary_view": summary,
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            persisted_path=item_relative_path,
            change_summary={
                "operation": "create_flowerpot",
                "source": source,
                "flowerpot_id": flowerpot_id,
                "registry_path": REGISTRY_RELATIVE_PATH,
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Created Flowerpot: {selected_label}",
            details={"garden_root": str(garden_root_path)},
        ),
    }


def get_flowerpot(
    *,
    garden_root: str | None = None,
    flowerpot_id: str | None = None,
    flowerpot: dict[str, Any] | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Read a registered Flowerpot, list registered items, or summarize one."""
    if flowerpot is not None:
        warnings = (
            ["Flowerpot body loading is not supported; returning lightweight context."]
            if include_body
            else []
        )
        summary = _summary_for_flowerpot(
            flowerpot_id=flowerpot.get("payload_context", {}).get("flowerpot_id"),
            flowerpot=flowerpot,
        )
        return {
            "flowerpot": flowerpot,
            "target": flowerpot.get("target", {}),
            "matches": [],
            "summary_view": summary,
            "report": make_report(
                status="ok",
                message="Flowerpot context returned.",
                warnings=warnings,
            ),
        }

    if garden_root is None:
        raise ValueError("garden_root or flowerpot is required.")
    garden_root_path = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    registry = _read_registry(garden_root_path)

    if not flowerpot_id:
        matches = [_match_for_item(entry) for entry in registry.get("flowerpots", [])]
        return {
            "flowerpot": {},
            "target": {},
            "matches": matches,
            "summary_view": {
                "garden_target": manifest.target(),
                "count": len(matches),
                "body_returned": False,
            },
            "report": make_report(
                status="ok",
                message=f"Found {len(matches)} Flowerpot(s).",
            ),
        }

    item = _read_item(garden_root_path, flowerpot_id)
    entry = item.get("registry_entry", {})
    registered_flowerpot = item["flowerpot"]
    warnings = (
        ["Flowerpot body loading is not supported; returning lightweight context."]
        if include_body
        else []
    )
    summary = _summary_for_flowerpot(
        flowerpot_id=flowerpot_id,
        flowerpot=registered_flowerpot,
        source=entry.get("source"),
        item_path=entry.get("file_path"),
        garden_root=str(garden_root_path),
    )
    return {
        "flowerpot": registered_flowerpot,
        "target": registered_flowerpot.get("target", {}),
        "matches": [_match_for_item(entry)] if entry else [],
        "summary_view": summary,
        "report": make_report(
            status="ok",
            message=f"Flowerpot returned: {flowerpot_id}",
            warnings=warnings,
        ),
    }


def _is_expired(entry: dict[str, Any], older_than_days: int | None) -> bool:
    if older_than_days is None:
        return False
    raw_updated = str(entry.get("updated_at") or entry.get("created_at") or "")
    if not raw_updated:
        return False
    try:
        updated = datetime.fromisoformat(raw_updated.replace("Z", "+00:00"))
    except ValueError:
        return False
    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    return updated < cutoff


def cleanup_flowerpots(
    *,
    garden_root: str,
    cleanup_scope: str = "orphaned",
    dry_run: bool = False,
    older_than_days: int | None = None,
) -> dict[str, Any]:
    """Clean Garden-local Flowerpot registry entries and item files."""
    cleanup_scope = str(cleanup_scope or "orphaned").strip().lower()
    if cleanup_scope not in SUPPORTED_CLEANUP_SCOPES:
        allowed = ", ".join(sorted(SUPPORTED_CLEANUP_SCOPES))
        raise ValueError(f"cleanup_scope must be one of: {allowed}.")
    garden_root_path = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    registry = _read_registry(garden_root_path)
    entries = list(registry.get("flowerpots", []))
    removed: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for entry in entries:
        flowerpot_id = str(entry.get("flowerpot_id", ""))
        item_path = _item_path(garden_root_path, flowerpot_id)
        is_orphaned = not item_path.is_file()
        remove = cleanup_scope == "all"
        if cleanup_scope == "orphaned":
            remove = is_orphaned
        elif cleanup_scope == "expired":
            remove = _is_expired(entry, older_than_days)

        if not remove:
            kept.append(entry)
            skipped.append(
                {
                    "flowerpot_id": flowerpot_id,
                    "reason": "not_matched",
                    "path": entry.get("file_path"),
                }
            )
            continue

        removed.append(
            {
                "flowerpot_id": flowerpot_id,
                "path": entry.get("file_path"),
                "dry_run": dry_run,
                "reason": cleanup_scope,
            }
        )
        if dry_run:
            kept.append(entry)
        elif item_path.is_file():
            item_path.unlink()

    if not dry_run:
        registry["flowerpots"] = kept
        _write_registry(garden_root_path, registry)

    receipt_status = "no_change" if dry_run or not removed else "persisted"
    return {
        "removed": removed,
        "skipped": skipped,
        "summary_view": {
            "garden_target": manifest.target(),
            "cleanup_scope": cleanup_scope,
            "dry_run": dry_run,
            "matched_count": len(entries),
            "removed_count": len(removed),
            "kept_count": len(kept),
        },
        "persistence_receipt": make_persistence_receipt(
            status=receipt_status,
            garden_id=manifest.garden_id,
            persisted_path=REGISTRY_RELATIVE_PATH,
            change_summary={
                "operation": "cleanup_flowerpots",
                "cleanup_scope": cleanup_scope,
                "dry_run": dry_run,
                "removed": removed,
            },
        ),
        "report": make_report(
            status="ok",
            message=(
                f"Dry run found {len(removed)} Flowerpot(s) to clean."
                if dry_run
                else f"Cleaned {len(removed)} Flowerpot(s)."
            ),
            warnings=[
                "Garden authoring truth in garden.json, models/, and libraries/ was not modified."
            ],
        ),
    }
