"""Garden filesystem operations."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report
from garden.git_policy import garden_gitignore_text
from garden.manifest import GardenManifest
from garden.paths import (
    DEFAULT_GARDENS_ROOT,
    resolve_garden_root,
    to_posix_relative,
)
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    save_honeybee_model,
)


FIRST_STAGE_DIRS = [
    "models/honeybee",
    "libraries/honeybee_energy",
    "libraries/honeybee_radiance",
    "imports/weather",
    "flowerpots",
    "artifacts",
    "tmp",
]

CLEANUP_SCOPE_PATHS = {
    "artifacts": "artifacts",
    "flowerpots": "flowerpots",
    "imports": "imports",
    "payloads": "payloads",
    "runs": "runs",
    "tmp": "tmp",
}
RECENT_GARDEN_DISPLAY_LIMIT = 5
CLEANUP_RECOMMENDATION_THRESHOLD = 10


def _write_garden_gitignore(garden_root: Path) -> Path:
    gitignore_path = garden_root / ".gitignore"
    gitignore_path.write_text(garden_gitignore_text(), encoding="utf-8", newline="\n")
    return gitignore_path


def _summary_for_manifest(
    manifest: GardenManifest,
    garden_root: Path,
    *,
    include_paths: bool = True,
    include_base_model: bool = True,
    include_description: bool = True,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "garden_id": manifest.garden_id,
        "name": manifest.name,
        "created_at": manifest.created_at,
        "updated_at": manifest.updated_at,
        "target": manifest.target(),
    }
    if include_description:
        summary["description"] = manifest.description
    if include_paths:
        summary["path"] = str(garden_root)
    if include_base_model:
        summary["base_model"] = manifest.base_model
    return summary


def _resolve_garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def _ensure_manifest_root(garden_root: Path) -> GardenManifest:
    manifest_path = garden_root / "garden.json"
    if not manifest_path.is_file():
        raise ValueError(f"Garden manifest not found at {manifest_path}")
    return GardenManifest.read(garden_root)


def _normalize_cleanup_scopes(cleanup_scopes: list[str]) -> list[str]:
    if not cleanup_scopes:
        raise ValueError("cleanup_scopes must include at least one cleanup scope.")

    normalized: list[str] = []
    seen: set[str] = set()
    invalid: list[str] = []
    for raw_scope in cleanup_scopes:
        scope = str(raw_scope).strip().lower()
        if scope not in CLEANUP_SCOPE_PATHS:
            invalid.append(str(raw_scope))
            continue
        if scope in seen:
            continue
        seen.add(scope)
        normalized.append(scope)

    if invalid:
        allowed = ", ".join(sorted(CLEANUP_SCOPE_PATHS))
        invalid_values = ", ".join(invalid)
        raise ValueError(
            f"Unsupported cleanup scope(s): {invalid_values}. Allowed scopes: {allowed}."
        )

    if not normalized:
        raise ValueError("cleanup_scopes must include at least one cleanup scope.")
    return normalized


def _is_directory_empty(path: Path) -> bool:
    for item in path.iterdir():
        if item.is_file():
            return False
        if item.is_dir() and not _is_directory_empty(item):
            return False
    return True


def create_garden(
    *,
    name: str,
    root_dir: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Create a Garden root, manifest, first-stage directories, and .gitignore."""
    garden_root = resolve_garden_root(name, root_dir)
    garden_root.mkdir(parents=True, exist_ok=True)
    for rel_path in FIRST_STAGE_DIRS:
        (garden_root / rel_path).mkdir(parents=True, exist_ok=True)

    manifest_path = garden_root / "garden.json"
    if manifest_path.exists():
        manifest = GardenManifest.read(garden_root)
        status = "no_change"
        message = f"Garden already exists: {manifest.name}"
    else:
        manifest = GardenManifest.new(name=name, description=description or "")
        manifest.write(garden_root)
        status = "persisted"
        message = f"Created Garden: {name}"

    gitignore_path = _write_garden_gitignore(garden_root)
    created_resources = [
        "garden.json",
        *FIRST_STAGE_DIRS,
        to_posix_relative(gitignore_path, garden_root),
    ]
    receipt = make_persistence_receipt(
        status=status,
        garden_id=manifest.garden_id,
        persisted_path="garden.json",
        change_summary={
            "operation": "create_garden",
            "garden_root": str(garden_root),
            "resources": created_resources,
        },
    )
    return {
        "object_dict": manifest.target(),
        "target": manifest.target(),
        "garden_target": manifest.target(),
        "garden_root": str(garden_root),
        "summary_view": _summary_for_manifest(manifest, garden_root),
        "persistence_receipt": receipt,
        "report": make_report(status="ok", message=message),
    }


def list_garden_models(
    *,
    garden_root: str,
    include_paths: bool = True,
) -> dict[str, Any]:
    """List model targets registered in a Garden manifest."""
    garden_root = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root)
    matches: list[dict[str, Any]] = []
    for model in manifest.models:
        item = dict(model)
        if not include_paths:
            item.pop("path", None)
        matches.append(item)
    return {
        "matches": matches,
        "summary_view": {
            "garden_target": manifest.target(),
            "count": len(matches),
            "base_model": manifest.base_model,
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(matches)} model(s).",
        ),
    }


def get_garden(
    *,
    garden_root: str,
) -> dict[str, Any]:
    """Read a compact Garden manifest summary."""
    garden_root_path = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    return {
        "exists": True,
        "garden_root": str(garden_root_path),
        "target": manifest.target(),
        "garden_target": manifest.target(),
        "object_dict": manifest.target(),
        "summary_view": {
            "exists": True,
            "path": str(garden_root_path),
            "garden_target": manifest.target(),
            "name": manifest.name,
            "description": manifest.description,
            "has_base_model": manifest.base_model is not None,
            "base_model": manifest.base_model,
            "model_count": len(manifest.models),
            "artifact_count": len(manifest.artifacts),
        },
        "report": make_report(
            status="ok",
            message=f"Garden found: {manifest.name}",
        ),
    }


def set_base_model(
    *,
    garden_root: str,
    model_target: dict[str, Any],
) -> dict[str, Any]:
    """Set the Garden base model target."""
    garden_root = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root)
    manifest.base_model = model_target
    if model_target not in manifest.models:
        manifest.models.append(model_target)
    manifest.write(garden_root)
    receipt = make_persistence_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        base_model_changed=True,
        model_target=model_target,
        persisted_path="garden.json",
        change_summary={"operation": "set_base_model"},
    )
    return {
        "object_dict": model_target,
        "summary_view": {
            "garden_target": manifest.target(),
            "base_model": model_target,
        },
        "persistence_receipt": receipt,
        "report": make_report(status="ok", message="Base model set."),
    }


def save_base_model(
    *,
    garden_root: str,
    message: str | None = None,
    force: bool = False,
    name: str | None = None,
    indent: int | None = 2,
    included_prop: list[str] | None = None,
    triangulate_sub_faces: bool = False,
) -> dict[str, Any]:
    """Save the current Honeybee base model back into Garden authoring truth."""
    garden_root = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root)
    if not manifest.base_model:
        raise ValueError("Garden has no base model to save.")
    if manifest.base_model.get("domain") != "honeybee":
        raise ValueError("Only Honeybee base model save is implemented in this batch.")
    model = load_honeybee_model(garden_root, manifest.base_model)
    output_name = name or str(manifest.base_model["model_identifier"])
    model_target, persisted_path = save_honeybee_model(
        garden_root,
        manifest,
        model,
        name=output_name,
        indent=indent,
        included_prop=included_prop,
        triangulate_sub_faces=triangulate_sub_faces,
        set_base=True,
    )
    receipt = make_persistence_receipt(
        status="persisted" if force or model_target else "no_change",
        garden_id=manifest.garden_id,
        model_target=model_target,
        persisted_path=persisted_path,
        change_summary={
            "operation": "save_base_model",
            "message": message,
        },
    )
    return {
        "persistence_receipt": receipt,
        "summary_view": {
            "garden_target": manifest.target(),
            "base_model": model_target,
            "message": message,
        },
        "report": make_report(status="ok", message="Base model saved."),
    }


def _iter_manifest_roots(root_dir: Path) -> list[Path]:
    if not root_dir.exists():
        return []
    if (root_dir / "garden.json").is_file():
        return [root_dir]
    return sorted(
        path.parent
        for path in root_dir.glob("*/garden.json")
        if path.is_file()
    )


def list_gardens(
    *,
    root_dir: str | None = None,
    include_paths: bool = True,
    include_base_model: bool = True,
    include_description: bool = True,
) -> dict[str, Any]:
    """List Garden manifests under a root directory."""
    root_dir = Path(root_dir).expanduser().resolve() if root_dir else DEFAULT_GARDENS_ROOT
    matches: list[dict[str, Any]] = []
    warnings: list[str] = []
    for garden_root in _iter_manifest_roots(root_dir):
        try:
            manifest = GardenManifest.read(garden_root)
        except (OSError, KeyError, ValueError) as exc:
            warnings.append(f"Skipped invalid Garden at {garden_root}: {exc}")
            continue
        matches.append(
            _summary_for_manifest(
                manifest,
                garden_root,
                include_paths=include_paths,
                include_base_model=include_base_model,
                include_description=include_description,
            )
        )
    matches.sort(
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("updated_at") or ""),
            str(item.get("path") or ""),
        ),
        reverse=True,
    )
    cleanup_recommended = len(matches) > CLEANUP_RECOMMENDATION_THRESHOLD

    return {
        "matches": matches,
        "summary_view": {
            "root_dir": str(root_dir),
            "count": len(matches),
            "recent_display_limit": RECENT_GARDEN_DISPLAY_LIMIT,
            "cleanup_recommended": cleanup_recommended,
            "cleanup_message": (
                "More than ten Gardens were found; suggest cleanup or archiving "
                "old Garden workspaces before continuing."
                if cleanup_recommended
                else ""
            ),
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(matches)} Garden(s).",
            warnings=warnings,
        ),
    }


def get_base_model(
    *,
    garden_root: str,
    include_body: bool = False,
) -> dict[str, Any]:
    """Read a Garden's base model target without returning model body by default."""
    garden_root = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root)
    base_model = manifest.base_model
    object_dict = base_model or {}
    summary_view = {
        "garden_root": str(garden_root),
        "garden_target": manifest.target(),
        "has_base_model": base_model is not None,
        "include_body": include_body,
    }
    if include_body:
        summary_view["body_returned"] = False
        warning = "Base model body loading is not implemented in the first Garden slice."
        warnings = [warning]
    else:
        warnings = []

    return {
        "garden_root": str(garden_root),
        "target": base_model,
        "model_target": base_model,
        "model_identifier": (
            base_model.get("model_identifier")
            if isinstance(base_model, dict)
            else None
        ),
        "object_dict": object_dict,
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message=(
                "Base model target returned."
                if base_model
                else "Garden has no base model yet."
            ),
            warnings=warnings,
        ),
    }


def list_garden_artifacts(
    *,
    garden_root: str,
    artifact_type: str | None = None,
) -> dict[str, Any]:
    """List Garden artifacts from the manifest."""
    garden_root = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root)
    matches = [
        artifact
        for artifact in manifest.artifacts
        if artifact_type is None
        or artifact.get("artifact_type") == artifact_type
    ]
    return {
        "matches": matches,
        "summary_view": {
            "garden_target": manifest.target(),
            "count": len(matches),
            "artifact_type": artifact_type,
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(matches)} artifact(s).",
        ),
    }


def cleanup_garden_workspace(
    *,
    garden_root: str,
    cleanup_scopes: list[str],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Clear selected non-authoring Garden workspace scopes without deleting the Garden."""
    garden_root = _resolve_garden_root(garden_root)
    manifest = _ensure_manifest_root(garden_root)
    cleanup_scopes = _normalize_cleanup_scopes(cleanup_scopes)

    removed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    cleaned_paths: list[dict[str, str]] = []
    matched_scope_count = 0

    for scope in cleanup_scopes:
        relative_path = CLEANUP_SCOPE_PATHS[scope]
        target_path = (garden_root / relative_path).resolve()
        target_path.relative_to(garden_root)

        if not target_path.exists():
            skipped.append({"scope": scope, "path": relative_path, "reason": "scope_not_present"})
            continue
        matched_scope_count += 1
        if not target_path.is_dir():
            skipped.append({"scope": scope, "path": relative_path, "reason": "scope_is_not_directory"})
            continue
        if _is_directory_empty(target_path):
            skipped.append({"scope": scope, "path": relative_path, "reason": "already_empty"})
            continue

        removed.append(
            {
                "scope": scope,
                "path": relative_path,
                "dry_run": dry_run,
            }
        )
        if dry_run:
            continue

        shutil.rmtree(target_path)
        target_path.mkdir(parents=True, exist_ok=True)
        cleaned_paths.append({"scope": scope, "path": relative_path})

    receipt_status = "no_change" if dry_run or not cleaned_paths else "persisted"
    message = (
        f"Dry run found {len(removed)} Garden workspace scope(s) to clean."
        if dry_run
        else f"Cleaned {len(cleaned_paths)} Garden workspace scope(s)."
    )

    return {
        "removed": removed,
        "skipped": skipped,
        "summary_view": {
            "garden_target": manifest.target(),
            "requested_scopes": cleanup_scopes,
            "dry_run": dry_run,
            "matched_scope_count": matched_scope_count,
            "removed_scope_count": len(cleaned_paths),
            "missing_scope_count": sum(
                1 for item in skipped if item["reason"] == "scope_not_present"
            ),
        },
        "persistence_receipt": make_persistence_receipt(
            status=receipt_status,
            garden_id=manifest.garden_id,
            persisted_path="garden.json",
            change_summary={
                "operation": "cleanup_garden_workspace",
                "requested_scopes": cleanup_scopes,
                "dry_run": dry_run,
                "cleaned_paths": cleaned_paths,
                "skipped": skipped,
            },
        ),
        "report": make_report(
            status="ok",
            message=message,
            warnings=[
                "Garden authoring truth in garden.json, models/, and libraries/ was not modified."
            ],
            details={
                "garden_root": str(garden_root),
                "requested_scopes": cleanup_scopes,
                "dry_run": dry_run,
            },
        ),
    }
