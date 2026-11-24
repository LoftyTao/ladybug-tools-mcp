"""Garden filesystem operations."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from ladybug_tools_mcp.contracts import make_persistence_receipt, make_report
from garden.manifest import GardenManifest
from garden.paths import (
    DEFAULT_GARDENS_ROOT,
    resolve_garden_root,
    to_posix_relative,
)
from garden.versions import ensure_garden_git_repository, is_git_available
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    save_honeybee_model,
)
from garden.honeybee_core.targets import normalize_honeybee_model_target
from garden.dragonfly_core.model_io import (
    load_dragonfly_model,
    normalize_dragonfly_model_target,
    save_dragonfly_model,
)


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
GARDEN_GITIGNORE = """# Garden authoring truth is intentionally narrow.
*
!garden.json
!models/
!models/**
!libraries/
!libraries/**

# Generated or exchange-only content stays out of Garden Git.
artifacts/
runs/
flowerpots/
payloads/
imports/
tmp/
.cache/
"""
ARTIFACT_TYPE_ALIASES = {
    "sky": "radiance_sky_file",
    "sky_file": "radiance_sky_file",
    "radiance_sky": "radiance_sky_file",
    "radiance_sky_file": "radiance_sky_file",
    "view": "radiance_view",
    "radiance_view": "radiance_view",
    "sensor_grid": "radiance_sensor_grid",
    "grid": "radiance_sensor_grid",
    "radiance_sensor_grid": "radiance_sensor_grid",
    "hdr": "radiance_hdr_image",
    "hdr_image": "radiance_hdr_image",
    "radiance_hdr_image": "radiance_hdr_image",
    "gif": "radiance_gif_image",
    "gif_image": "radiance_gif_image",
    "radiance_gif_image": "radiance_gif_image",
    "wea": "wea_file",
    "wea_file": "wea_file",
    "vtkjs": "visualization_vtkjs",
    "visualization_vtkjs": "visualization_vtkjs",
    "html": "visualization_html",
    "visualization_html": "visualization_html",
    "svg": "visualization_svg",
    "visualization_svg": "visualization_svg",
}
_ARTIFACT_DOMAIN_ALIASES = {
    "radiance": "honeybee_radiance",
    "honeybee_radiance": "honeybee_radiance",
    "rad": "honeybee_radiance",
    "energy": "honeybee_energy",
    "honeybee_energy": "honeybee_energy",
    "ep": "honeybee_energy",
    "visualize": "visualize",
    "visualization": "visualize",
    "fairyfly": "fairyfly",
    "therm": "fairyfly",
    "uwg": "dragonfly_uwg",
    "dragonfly_uwg": "dragonfly_uwg",
    "des": "dragonfly_des",
    "dragonfly_des": "dragonfly_des",
    "grid": "dragonfly_grid",
    "dragonfly_grid": "dragonfly_grid",
    "urbanopt": "urbanopt",
    "dragonfly": "dragonfly",
    "ladybug": "ladybug",
}


def _write_garden_gitignore(garden_root: Path) -> Path:
    gitignore_path = garden_root / ".gitignore"
    gitignore_path.write_text(GARDEN_GITIGNORE, encoding="utf-8", newline="\n")
    return gitignore_path


def _summary_for_manifest(
    manifest: GardenManifest,
    garden_root: Path,
    *,
    include_paths: bool = True,
    include_base_models: bool = True,
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
    if include_base_models:
        summary["base_honeybee_model"] = manifest.base_honeybee_model
        summary["base_dragonfly_model"] = manifest.base_dragonfly_model
        summary["base_fairyfly_model"] = manifest.base_fairyfly_model
    return summary


def _resolve_garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def _ensure_manifest_root(garden_root: Path) -> GardenManifest:
    manifest_path = garden_root / "garden.json"
    if not manifest_path.is_file():
        raise ValueError(
            f"Garden manifest not found at {manifest_path}. "
            "Call create_garden first for blank-project workflows."
        )
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


def create_garden(
    *,
    name: str,
    root_dir: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Create a Garden manifest and initialize Git when available."""
    garden_root = resolve_garden_root(name, root_dir)
    garden_root.mkdir(parents=True, exist_ok=True)
    git_available = is_git_available()
    repository_created = (
        ensure_garden_git_repository(garden_root) if git_available else False
    )

    manifest_path = garden_root / "garden.json"
    manifest_created = not manifest_path.exists()
    if not manifest_created:
        manifest = GardenManifest.read(garden_root)
    else:
        manifest = GardenManifest.new(name=name, description=description or "")
        manifest.write(garden_root)

    gitignore_path = _write_garden_gitignore(garden_root)
    status = "persisted" if manifest_created or repository_created else "no_change"
    message = (
        f"Created Garden: {name}"
        if manifest_created
        else f"Garden already exists: {manifest.name}"
    )
    repository_initialized = (garden_root / ".git").exists()
    created_resources = [
        "garden.json",
        to_posix_relative(gitignore_path, garden_root),
    ]
    if repository_initialized:
        created_resources.append(".git/")
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
        "summary_view": {
            **_summary_for_manifest(manifest, garden_root),
            "version_control": {
                "git_available": git_available,
                "repository_initialized": repository_initialized,
            },
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=message,
            warnings=(
                []
                if git_available
                else [
                    "Git is not available on PATH. This Garden was created without "
                    "version management; install Git, then call a Garden version tool "
                    "to initialize its repository."
                ]
            ),
        ),
    }


def list_garden_models(
    *,
    garden_root: str,
    include_paths: bool = True,
) -> dict[str, Any]:
    """List model targets registered in a Garden manifest."""
    garden_root_path = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
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
            "base_honeybee_model": manifest.base_honeybee_model,
            "base_dragonfly_model": manifest.base_dragonfly_model,
            "base_fairyfly_model": manifest.base_fairyfly_model,
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
    manifest = _ensure_manifest_root(garden_root_path)
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
            "has_base_honeybee_model": manifest.base_honeybee_model is not None,
            "has_base_dragonfly_model": manifest.base_dragonfly_model is not None,
            "has_base_fairyfly_model": manifest.base_fairyfly_model is not None,
            "base_honeybee_model": manifest.base_honeybee_model,
            "base_dragonfly_model": manifest.base_dragonfly_model,
            "base_fairyfly_model": manifest.base_fairyfly_model,
            "model_count": len(manifest.models),
            "artifact_count": len(manifest.artifacts),
        },
        "report": make_report(
            status="ok",
            message=f"Garden found: {manifest.name}",
        ),
    }


def _base_slot_name(domain: str) -> str:
    normalized = str(domain or "").strip().lower()
    if normalized not in {"honeybee", "dragonfly", "fairyfly"}:
        raise ValueError(
            "Base model domain must be 'honeybee', 'dragonfly', or 'fairyfly'."
        )
    return f"base_{normalized}_model"


def _domain_base_model(
    manifest: GardenManifest,
    domain: str,
) -> dict[str, Any] | None:
    return getattr(manifest, _base_slot_name(domain))


def _set_domain_base_model(
    manifest: GardenManifest,
    domain: str,
    model_target: dict[str, Any],
) -> None:
    setattr(manifest, _base_slot_name(domain), model_target)


def set_domain_base_model(
    *,
    garden_root: str,
    model_target: dict[str, Any],
    domain: str | None = None,
) -> dict[str, Any]:
    """Set the Garden base model target for one model domain."""
    garden_root_path = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    resolved_domain = str(domain or model_target.get("domain") or "").strip().lower()
    _base_slot_name(resolved_domain)
    if resolved_domain == "honeybee":
        model_target = normalize_honeybee_model_target(model_target)
    elif resolved_domain == "dragonfly":
        model_target = normalize_dragonfly_model_target(model_target)
    elif resolved_domain == "fairyfly":
        from garden.fairyfly.model import normalize_fairyfly_model_target

        model_target = normalize_fairyfly_model_target(model_target)
    if model_target.get("domain") != resolved_domain:
        raise ValueError("model_target domain must match the requested base domain.")
    _set_domain_base_model(manifest, resolved_domain, model_target)
    if model_target not in manifest.models:
        manifest.models.append(model_target)
    manifest.write(garden_root_path)
    receipt = make_persistence_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        base_honeybee_model_changed=resolved_domain == "honeybee",
        base_dragonfly_model_changed=resolved_domain == "dragonfly",
        base_fairyfly_model_changed=resolved_domain == "fairyfly",
        model_target=model_target,
        persisted_path="garden.json",
        change_summary={
            "operation": f"set_base_{resolved_domain}_model",
            "domain": resolved_domain,
        },
    )
    return {
        "object_dict": model_target,
        "target": model_target,
        "model_target": model_target,
        "summary_view": {
            "garden_target": manifest.target(),
            f"base_{resolved_domain}_model": model_target,
            "domain": resolved_domain,
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=f"Base {resolved_domain.title()} model set.",
        ),
    }


def save_base_honeybee_model(
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
    garden_root_path = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    if not manifest.base_honeybee_model:
        raise ValueError("Garden has no base Honeybee model to save.")
    model = load_honeybee_model(garden_root_path, manifest.base_honeybee_model)
    output_name = name or str(manifest.base_honeybee_model["model_identifier"])
    model_target, persisted_path = save_honeybee_model(
        garden_root_path,
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
        base_honeybee_model_changed=True,
        model_target=model_target,
        persisted_path=persisted_path,
        change_summary={
            "operation": "save_base_honeybee_model",
            "message": message,
        },
    )
    return {
        "target": model_target,
        "model_target": model_target,
        "persistence_receipt": receipt,
        "summary_view": {
            "garden_target": manifest.target(),
            "base_honeybee_model": model_target,
            "message": message,
        },
        "report": make_report(status="ok", message="Base Honeybee model saved."),
    }


def save_base_dragonfly_model(
    *,
    garden_root: str,
    message: str | None = None,
    force: bool = False,
    name: str | None = None,
    indent: int | None = 2,
    included_prop: list[str] | None = None,
) -> dict[str, Any]:
    """Save the current Dragonfly base model back into Garden authoring truth."""
    garden_root_path = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    if not manifest.base_dragonfly_model:
        raise ValueError("Garden has no base Dragonfly model to save.")
    model = load_dragonfly_model(garden_root_path, manifest.base_dragonfly_model)
    output_name = name or str(manifest.base_dragonfly_model["model_identifier"])
    model_target, persisted_path = save_dragonfly_model(
        garden_root_path,
        manifest,
        model,
        name=output_name,
        indent=indent,
        included_prop=included_prop,
        set_base=True,
    )
    receipt = make_persistence_receipt(
        status="persisted" if force or model_target else "no_change",
        garden_id=manifest.garden_id,
        base_dragonfly_model_changed=True,
        model_target=model_target,
        persisted_path=persisted_path,
        change_summary={
            "operation": "save_base_dragonfly_model",
            "message": message,
        },
    )
    return {
        "target": model_target,
        "model_target": model_target,
        "persistence_receipt": receipt,
        "summary_view": {
            "garden_target": manifest.target(),
            "base_dragonfly_model": model_target,
            "message": message,
        },
        "report": make_report(status="ok", message="Base Dragonfly model saved."),
    }


def save_base_fairyfly_model(
    *,
    garden_root: str,
    message: str | None = None,
    force: bool = False,
    name: str | None = None,
    indent: int | None = 2,
) -> dict[str, Any]:
    """Save the current Fairyfly base model back into Garden authoring truth."""
    from garden.fairyfly.model import load_fairyfly_model, save_fairyfly_model

    garden_root_path = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    if not manifest.base_fairyfly_model:
        raise ValueError("Garden has no base Fairyfly model to save.")
    model = load_fairyfly_model(garden_root_path, manifest.base_fairyfly_model)
    output_name = name or str(manifest.base_fairyfly_model["model_identifier"])
    model_target, persisted_path = save_fairyfly_model(
        garden_root_path,
        manifest,
        model,
        name=output_name,
        indent=indent,
        set_base=True,
    )
    receipt = make_persistence_receipt(
        status="persisted" if force or model_target else "no_change",
        garden_id=manifest.garden_id,
        base_fairyfly_model_changed=True,
        model_target=model_target,
        persisted_path=persisted_path,
        change_summary={
            "operation": "save_base_fairyfly_model",
            "message": message,
        },
    )
    return {
        "target": model_target,
        "model_target": model_target,
        "persistence_receipt": receipt,
        "summary_view": {
            "garden_target": manifest.target(),
            "base_fairyfly_model": model_target,
            "message": message,
        },
        "report": make_report(status="ok", message="Base Fairyfly model saved."),
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
    include_base_models: bool = True,
    include_description: bool = True,
) -> dict[str, Any]:
    """List Garden manifests under a root directory."""
    root_dir_path = (
        Path(root_dir).expanduser().resolve() if root_dir else DEFAULT_GARDENS_ROOT
    )
    matches: list[dict[str, Any]] = []
    warnings: list[str] = []
    for garden_root in _iter_manifest_roots(root_dir_path):
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
                include_base_models=include_base_models,
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
            "root_dir": str(root_dir_path),
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


def _get_domain_base_model(
    *,
    garden_root: str,
    domain: str,
) -> dict[str, Any]:
    """Read a Garden's base model target for one domain."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    base_model = _domain_base_model(manifest, domain)
    object_dict = base_model
    slot_name = _base_slot_name(domain)
    summary_view = {
        "garden_root": str(garden_root_path),
        "garden_target": manifest.target(),
        f"has_{slot_name}": base_model is not None,
        slot_name: base_model,
        "domain": domain,
    }

    return {
        "target": base_model,
        "object_dict": object_dict,
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message=(
                f"Base {domain.title()} model target returned."
                if base_model
                else f"Garden has no base {domain.title()} model yet."
            ),
        ),
    }


def get_base_model(
    *,
    garden_root: str,
    domain: str | None = None,
) -> dict[str, Any]:
    """Read one or all Garden base model slots."""
    if domain is not None:
        return _get_domain_base_model(garden_root=garden_root, domain=domain)
    garden_root_path = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    base_models = {
        "honeybee": manifest.base_honeybee_model,
        "dragonfly": manifest.base_dragonfly_model,
        "fairyfly": manifest.base_fairyfly_model,
    }
    populated = [(key, value) for key, value in base_models.items() if value is not None]
    primary_target = populated[0][1] if len(populated) == 1 else None
    return {
        "target": primary_target,
        "object_dict": primary_target,
        "base_models": base_models,
        "summary_view": {
            "garden_root": str(garden_root_path),
            "garden_target": manifest.target(),
            "has_base_honeybee_model": manifest.base_honeybee_model is not None,
            "has_base_dragonfly_model": manifest.base_dragonfly_model is not None,
            "has_base_fairyfly_model": manifest.base_fairyfly_model is not None,
            "base_honeybee_model": manifest.base_honeybee_model,
            "base_dragonfly_model": manifest.base_dragonfly_model,
            "base_fairyfly_model": manifest.base_fairyfly_model,
        },
        "report": make_report(
            status="ok",
            message="Base model slots returned.",
        ),
    }


def manage_base_model(
    *,
    garden_root: str,
    action: str,
    domain: str | None = None,
    model_target: dict[str, Any] | None = None,
    message: str | None = None,
    force: bool = False,
    name: str | None = None,
    indent: int | None = 2,
    included_prop: list[str] | None = None,
    triangulate_sub_faces: bool = False,
) -> dict[str, Any]:
    """Get, set, or save a Garden base model slot across Honeybee, Dragonfly, or Fairyfly."""
    normalized_action = str(action or "").strip().lower()
    if normalized_action not in {"get", "set", "save"}:
        raise ValueError("action must be 'get', 'set', or 'save'.")
    normalized_domain = (
        str(domain).strip().lower() if isinstance(domain, str) and domain.strip() else None
    )
    if normalized_domain is not None:
        _base_slot_name(normalized_domain)

    if normalized_action == "get":
        return get_base_model(garden_root=garden_root, domain=normalized_domain)

    if normalized_action == "set":
        if model_target is None:
            raise ValueError("model_target is required when action is 'set'.")
        return set_domain_base_model(
            garden_root=garden_root,
            model_target=model_target,
            domain=normalized_domain,
        )

    resolved_domain = normalized_domain
    if resolved_domain is None and isinstance(model_target, dict):
        raw_target_domain = model_target.get("domain")
        if isinstance(raw_target_domain, str) and raw_target_domain.strip():
            resolved_domain = raw_target_domain.strip().lower()
    if resolved_domain is None:
        garden_root_path = _resolve_garden_root(garden_root)
        manifest = GardenManifest.read(garden_root_path)
        populated = [
            key
            for key in ("honeybee", "dragonfly", "fairyfly")
            if _domain_base_model(manifest, key) is not None
        ]
        if len(populated) == 1:
            resolved_domain = populated[0]
        elif not populated:
            raise ValueError("Garden has no base model to save.")
        else:
            raise ValueError(
                "Garden has multiple base models; pass domain='honeybee', 'dragonfly', or 'fairyfly'."
            )

    if resolved_domain == "honeybee":
        return save_base_honeybee_model(
            garden_root=garden_root,
            message=message,
            force=force,
            name=name,
            indent=indent,
            included_prop=included_prop,
            triangulate_sub_faces=triangulate_sub_faces,
        )
    if resolved_domain == "dragonfly":
        return save_base_dragonfly_model(
            garden_root=garden_root,
            message=message,
            force=force,
            name=name,
            indent=indent,
            included_prop=included_prop,
        )
    if resolved_domain == "fairyfly":
        return save_base_fairyfly_model(
            garden_root=garden_root,
            message=message,
            force=force,
            name=name,
            indent=indent,
        )
    raise ValueError("Base model domain must be 'honeybee', 'dragonfly', or 'fairyfly'.")


def get_base_honeybee_model(
    *,
    garden_root: str,
) -> dict[str, Any]:
    """Read a Garden's base Honeybee model target."""
    return _get_domain_base_model(
        garden_root=garden_root,
        domain="honeybee",
    )


def get_base_dragonfly_model(
    *,
    garden_root: str,
) -> dict[str, Any]:
    """Read a Garden's base Dragonfly model target."""
    return _get_domain_base_model(
        garden_root=garden_root,
        domain="dragonfly",
    )


def get_base_fairyfly_model(
    *,
    garden_root: str,
) -> dict[str, Any]:
    """Read a Garden's base Fairyfly model target."""
    return _get_domain_base_model(
        garden_root=garden_root,
        domain="fairyfly",
    )


def _normalize_artifact_type_filter(artifact_type: str | None) -> str | None:
    if artifact_type is None:
        return None
    stripped = str(artifact_type).strip()
    if not stripped:
        return None
    key = stripped.lower().replace("-", "_").replace(" ", "_")
    return ARTIFACT_TYPE_ALIASES.get(key, key)


def _normalize_artifact_domain_filter(domain: str | None) -> str | None:
    if domain is None:
        return None
    key = str(domain).strip().lower().replace("-", "_").replace(" ", "_")
    if not key or key == "all":
        return None
    return _ARTIFACT_DOMAIN_ALIASES.get(key, key)


def _infer_artifact_domain(artifact: dict[str, Any]) -> str | None:
    explicit = artifact.get("domain")
    if isinstance(explicit, str) and explicit.strip():
        return _normalize_artifact_domain_filter(explicit)
    artifact_type = str(artifact.get("artifact_type") or "").strip().lower()
    if artifact_type.startswith("radiance_") or artifact_type == "sky_matrix_json":
        return "honeybee_radiance"
    if artifact_type == "wea_file":
        return "ladybug"
    if artifact_type.startswith("visualization_"):
        return "visualize"
    if artifact_type.startswith("fairyfly_"):
        return "fairyfly"
    if artifact_type.startswith("uwg_"):
        return "dragonfly_uwg"
    if artifact_type.startswith("dragonfly_des_"):
        return "dragonfly_des"
    if artifact_type.startswith("dragonfly_grid_"):
        return "dragonfly_grid"
    if artifact_type.startswith("urbanopt_"):
        return "urbanopt"
    if artifact_type.startswith("energy_") or artifact_type == "simulation_parameter":
        return "honeybee_energy"
    if artifact_type.startswith("dragonfly_"):
        return "dragonfly"
    path = str(artifact.get("path") or "").strip().lower()
    if "/radiance/" in f"/{path}":
        return "honeybee_radiance"
    if "/visualization" in f"/{path}" or "/visualize" in f"/{path}":
        return "visualize"
    if "/fairyfly/" in f"/{path}":
        return "fairyfly"
    if "/uwg/" in f"/{path}":
        return "dragonfly_uwg"
    if "/energy/" in f"/{path}":
        return "honeybee_energy"
    return None


def list_garden_artifacts(
    *,
    garden_root: str,
    artifact_type: str | None = None,
    domain: str | None = None,
    query: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """List Garden artifacts from the manifest with optional alias, domain, query, and limit filters."""
    if limit is not None and limit < 1:
        raise ValueError("limit must be at least 1 when provided.")
    garden_root_path = _resolve_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    normalized_type = _normalize_artifact_type_filter(artifact_type)
    normalized_domain = _normalize_artifact_domain_filter(domain)
    query_text = (query or "").strip().lower()

    matches: list[dict[str, Any]] = []
    for artifact in manifest.artifacts:
        record_type = str(artifact.get("artifact_type") or "").strip().lower()
        if normalized_type is not None and record_type != normalized_type.lower():
            continue
        if normalized_domain is not None:
            record_domain = _infer_artifact_domain(artifact)
            if record_domain != normalized_domain:
                continue
        if query_text:
            searchable = " ".join(
                str(value)
                for value in (
                    artifact.get("name"),
                    artifact.get("identifier"),
                    artifact.get("path"),
                    artifact.get("artifact_type"),
                    artifact.get("domain"),
                )
                if value
            ).lower()
            if query_text not in searchable:
                continue
        matches.append(artifact)

    if limit is not None:
        matches = matches[:limit]

    artifact_paths = [
        str(item["path"])
        for item in matches
        if isinstance(item.get("path"), str) and item.get("path")
    ]
    return {
        "matches": matches,
        "artifact_paths": artifact_paths,
        "summary_view": {
            "garden_target": manifest.target(),
            "count": len(matches),
            "artifact_type": normalized_type,
            "requested_artifact_type": artifact_type,
            "domain": normalized_domain or "all",
            "query": query,
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
    garden_root_path = _resolve_garden_root(garden_root)
    manifest = _ensure_manifest_root(garden_root_path)
    cleanup_scopes = _normalize_cleanup_scopes(cleanup_scopes)

    removed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    cleaned_paths: list[dict[str, str]] = []
    matched_scope_count = 0

    for scope in cleanup_scopes:
        relative_path = CLEANUP_SCOPE_PATHS[scope]
        target_path = (garden_root_path / relative_path).resolve()
        target_path.relative_to(garden_root_path)

        if not target_path.exists():
            skipped.append({"scope": scope, "path": relative_path, "reason": "scope_not_present"})
            continue
        matched_scope_count += 1
        if not target_path.is_dir():
            skipped.append({"scope": scope, "path": relative_path, "reason": "scope_is_not_directory"})
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
                "garden_root": str(garden_root_path),
                "requested_scopes": cleanup_scopes,
                "dry_run": dry_run,
            },
        ),
    }
