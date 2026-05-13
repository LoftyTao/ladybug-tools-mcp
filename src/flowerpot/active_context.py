"""Garden-local active Flowerpot context service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name
from ladybug_tools_mcp.contracts.report import make_report

ACTIVE_CONTEXT_DIR = "flowerpots/active_context"
FLOWERPOT_KEYS = {
    "type",
    "schema_version",
    "kind",
    "label",
    "target",
    "payload_context",
    "platform",
}
BODY_KEYS = {
    "payload_body",
    "object_dict",
    "model",
    "hbjson",
    "rooms",
    "faces",
    "apertures",
    "doors",
    "shades",
    "geometry",
    "body",
    "payload",
    "object",
    "objects",
    "data",
}


def _normalize_platform(platform: str) -> str:
    return slugify_name(str(platform or "grasshopper"))


def _resolve_garden_root(garden_root: str) -> tuple[Path, GardenManifest]:
    root = Path(garden_root).expanduser().resolve()
    if not (root / "garden.json").is_file():
        raise ValueError(f"Garden manifest not found at {root / 'garden.json'}")
    manifest = GardenManifest.read(root)
    return root, manifest


def _context_path(garden_root: str, platform: str) -> Path:
    root = Path(garden_root).expanduser().resolve()
    active_context_dir = (root / ACTIVE_CONTEXT_DIR).resolve()
    path = (active_context_dir / f"{_normalize_platform(platform)}.json").resolve()
    try:
        path.relative_to(active_context_dir)
    except ValueError as exc:
        raise ValueError("Active context path must stay inside the Garden.") from exc
    return path


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {}
        for key, nested in value.items():
            if str(key).lower() in BODY_KEYS:
                continue
            cleaned[key] = _sanitize_value(nested)
        return cleaned
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value


def _sanitize_flowerpot(flowerpot: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(flowerpot, dict):
        return {}
    return {
        key: _sanitize_value(flowerpot[key])
        for key in FLOWERPOT_KEYS
        if key in flowerpot
    }


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def _registry_fallback_context(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    platform: str,
) -> dict[str, Any] | None:
    from flowerpot.registry import _read_item, _read_registry

    registry = _read_registry(garden_root)
    entries = list(registry.get("flowerpots", []))
    if not entries:
        return None
    normalized_platform = _normalize_platform(platform)

    def _platform_matches(entry: dict[str, Any]) -> bool:
        entry_platform = entry.get("platform")
        if not isinstance(entry_platform, dict) or not entry_platform:
            return True
        platform_name = entry_platform.get("name") or entry_platform.get("platform")
        if platform_name is None:
            return True
        return _normalize_platform(str(platform_name)) == normalized_platform

    candidates = [entry for entry in entries if _platform_matches(entry)]
    if not candidates:
        candidates = entries
    candidates.sort(
        key=lambda entry: str(entry.get("updated_at") or entry.get("created_at") or ""),
        reverse=True,
    )
    entry = candidates[0]
    flowerpot_id = str(entry.get("flowerpot_id") or "")
    if not flowerpot_id:
        return None
    item = _read_item(garden_root, flowerpot_id)
    flowerpot = _sanitize_flowerpot(item.get("flowerpot", {}))
    context = {
        "schema_version": "1",
        "updated_at": entry.get("updated_at") or item.get("updated_at"),
        "platform": normalized_platform,
        "component": {},
        "garden_root": str(garden_root),
        "garden_target": manifest.target(),
        "flowerpot": flowerpot,
        "flowerpot_id": flowerpot_id,
        "flowerpot_kind": flowerpot.get("kind") or entry.get("kind"),
        "base_honeybee_model_target": manifest.base_honeybee_model,
        "base_dragonfly_model_target": manifest.base_dragonfly_model,
        "model_identifier": (
            manifest.base_honeybee_model.get("model_identifier")
            if isinstance(manifest.base_honeybee_model, dict)
            else None
        ),
        "model_display_name": None,
        "mode": "registry_fallback",
        "follow": False,
        "changed": False,
        "report_status": "ok",
        "source": "registry_fallback",
    }
    return {
        "active_context": context,
        "garden_root": str(garden_root),
        "flowerpot": flowerpot,
        "model_target": manifest.base_honeybee_model,
        "summary_view": {
            "found": True,
            "source": "registry_fallback",
            "platform": normalized_platform,
            "flowerpot_id": flowerpot_id,
            "flowerpot_kind": context.get("flowerpot_kind"),
            "model_identifier": context.get("model_identifier"),
            "model_display_name": None,
            "mode": "registry_fallback",
            "follow": False,
            "changed": False,
            "report_status": "ok",
            "garden_target": manifest.target(),
        },
        "report": make_report(
            status="ok",
            message=(
                f"No explicit active Flowerpot context found for {normalized_platform}; "
                "returned latest registered Flowerpot fallback."
            ),
            warnings=[
                "Returned registry fallback context because no platform active-context file exists."
            ],
        ),
    }


def write_active_context(
    *,
    garden_root: str,
    platform: str,
    flowerpot: dict[str, Any],
    mode: str,
    follow: bool,
    changed: bool,
    component: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
    model_identifier: str | None = None,
    model_display_name: str | None = None,
    report_status: str = "ok",
) -> dict[str, Any]:
    """Write the Garden-local active Flowerpot context for a platform."""
    garden_root_path, manifest = _resolve_garden_root(garden_root)
    normalized_platform = _normalize_platform(platform)
    safe_flowerpot = _sanitize_flowerpot(flowerpot)
    payload_context = safe_flowerpot.get("payload_context", {})
    context = {
        "schema_version": "1",
        "updated_at": utc_now_iso(),
        "platform": normalized_platform,
        "component": _sanitize_value(component or {}),
        "garden_root": str(garden_root_path),
        "garden_target": manifest.target(),
        "flowerpot": safe_flowerpot,
        "flowerpot_id": payload_context.get("flowerpot_id"),
        "flowerpot_kind": safe_flowerpot.get("kind"),
        "base_honeybee_model_target": _sanitize_value(model_target),
        "model_identifier": model_identifier,
        "model_display_name": model_display_name,
        "mode": mode,
        "follow": bool(follow),
        "changed": bool(changed),
        "report_status": report_status,
    }
    path = _context_path(str(garden_root_path), normalized_platform)
    _write_json(path, context)

    return {
        "active_context": context,
        "path": str(path),
        "report": make_report(
            status="ok",
            message=f"Active Flowerpot context written for {normalized_platform}.",
            details={
                "garden_root": str(garden_root_path),
                "platform": normalized_platform,
                "report_status": report_status,
            },
        ),
    }


def read_active_context(
    *,
    garden_root: str,
    platform: str = "grasshopper",
) -> dict[str, Any]:
    """Read the Garden-local active Flowerpot context for a platform."""
    garden_root_path, manifest = _resolve_garden_root(garden_root)
    normalized_platform = _normalize_platform(platform)
    path = _context_path(str(garden_root_path), normalized_platform)

    if not path.is_file():
        fallback = _registry_fallback_context(
            garden_root=garden_root_path,
            manifest=manifest,
            platform=normalized_platform,
        )
        if fallback is not None:
            return fallback
        return {
            "active_context": {},
            "garden_root": str(garden_root_path),
            "flowerpot": {},
            "model_target": None,
            "summary_view": {
                "found": False,
                "platform": normalized_platform,
                "garden_target": manifest.target(),
            },
            "report": make_report(
                status="ok",
                message=f"No active Flowerpot context found for {normalized_platform}.",
            ),
        }

    with path.open("r", encoding="utf-8") as handle:
        context = _sanitize_value(json.load(handle))
    context["garden_root"] = str(garden_root_path)
    context["garden_target"] = manifest.target()
    context["platform"] = normalized_platform
    if isinstance(context.get("flowerpot"), dict):
        context["flowerpot"] = _sanitize_flowerpot(context["flowerpot"])

    flowerpot = context.get("flowerpot") or {}
    model_target = context.get("base_honeybee_model_target")
    return {
        "active_context": context,
        "garden_root": str(garden_root_path),
        "flowerpot": flowerpot,
        "model_target": model_target,
        "summary_view": {
            "found": True,
            "platform": context.get("platform", normalized_platform),
            "flowerpot_id": context.get("flowerpot_id"),
            "flowerpot_kind": context.get("flowerpot_kind"),
            "model_identifier": context.get("model_identifier"),
            "model_display_name": context.get("model_display_name"),
            "mode": context.get("mode"),
            "follow": context.get("follow"),
            "changed": context.get("changed"),
            "report_status": context.get("report_status"),
            "garden_target": context.get("garden_target") or manifest.target(),
        },
        "report": make_report(
            status="ok",
            message=f"Active Flowerpot context returned for {normalized_platform}.",
        ),
    }


def read_latest_active_context(
    *,
    root_folder: str,
    platform: str = "grasshopper",
) -> dict[str, Any]:
    """Read the most recently updated active context under a folder of Gardens."""
    root = Path(root_folder).expanduser().resolve()
    normalized_platform = _normalize_platform(platform)
    matches: list[tuple[str, Path]] = []
    for context_path in root.glob(f"**/{ACTIVE_CONTEXT_DIR}/{normalized_platform}.json"):
        try:
            resolved_context_path = context_path.resolve()
            resolved_context_path.relative_to(root)
            if len(resolved_context_path.parents) < 3:
                continue
            garden_root_path = resolved_context_path.parents[2]
            garden_root_path, _manifest = _resolve_garden_root(str(garden_root_path))
            garden_root_path.relative_to(root)
            with context_path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
            updated_at = str(raw.get("updated_at") or "")
            expected_path = _context_path(str(garden_root_path), normalized_platform)
            if expected_path.resolve() != resolved_context_path:
                continue
        except Exception:
            continue
        matches.append((updated_at, garden_root_path.expanduser().resolve()))

    if not matches:
        return {
            "active_context": {},
            "garden_root": None,
            "flowerpot": {},
            "model_target": None,
            "summary_view": {
                "found": False,
                "platform": normalized_platform,
                "root_folder": str(root),
            },
            "report": make_report(
                status="ok",
                message=f"No active Flowerpot context found for {normalized_platform}.",
            ),
        }

    matches.sort(key=lambda item: item[0], reverse=True)
    return read_active_context(garden_root=str(matches[0][1]), platform=normalized_platform)
