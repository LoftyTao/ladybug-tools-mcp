"""Garden persistence for official Ironbug IB_HVACSystem JSON and authoring drafts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from garden.ironbug.targets import (
    make_ironbug_model_target,
    normalize_ironbug_model_target,
)
from garden.manifest import GardenManifest
from garden.operations import commit_manifest, read_operation_record
from garden.paths import (
    reject_windows_alias,
    to_posix_relative,
    validate_portable_file_name,
)

IRONBUG_MODELS_DIR = Path("models") / "ironbug"


def empty_draft(*, display_name: str | None = None, imported_only: bool = False) -> dict[str, Any]:
    """Return an empty Ironbug authoring draft."""
    return {
        "schema_version": 1,
        "display_name": display_name,
        "imported_only": bool(imported_only),
        "components": {},
        "thermal_zones": [],
        "air_loops": [],
        "plant_loops": [],
        "vrf_systems": [],
        "energy_management_system": None,
        "electric_load_center": None,
    }


def spec_filename(identifier: str) -> str:
    if not identifier.strip():
        raise ValueError("Ironbug system identifier must not be empty.")
    return validate_portable_file_name(f"{identifier}.json", label="Ironbug system file name")


def draft_filename(identifier: str) -> str:
    if not identifier.strip():
        raise ValueError("Ironbug system identifier must not be empty.")
    return validate_portable_file_name(f"{identifier}.draft.json", label="Ironbug draft file name")


def _ensure_contained(garden_root: Path, path: Path) -> Path:
    root = garden_root.resolve()
    resolved = path.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError("Ironbug system path must be inside the Garden root.")
    return resolved


def resolve_ironbug_system(
    garden_root: Path,
    *,
    ironbug_model_target: dict[str, Any] | None = None,
    identifier: str | None = None,
) -> tuple[GardenManifest, dict[str, Any], Path, Path]:
    """Resolve manifest, normalized target, official spec JSON path, and draft JSON path."""
    manifest = GardenManifest.read(garden_root)
    if ironbug_model_target is not None:
        target = normalize_ironbug_model_target(ironbug_model_target)
        spec_path = _ensure_contained(garden_root, garden_root / target["path"])
        sys_id = str(target["id"])
    elif identifier:
        sys_id = identifier.strip()
        matches = [
            item
            for item in manifest.models
            if item.get("domain") == "ironbug" and item.get("id") == sys_id
        ]
        if matches:
            target = normalize_ironbug_model_target(matches[0])
            spec_path = _ensure_contained(garden_root, garden_root / target["path"])
        else:
            rel = (IRONBUG_MODELS_DIR / spec_filename(sys_id)).as_posix()
            spec_path = _ensure_contained(garden_root, garden_root / rel)
            if not spec_path.is_file():
                raise ValueError(f"Ironbug system not found in Garden: {sys_id}")
            target = make_ironbug_model_target(
                garden_id=manifest.garden_id,
                identifier=sys_id,
                path=rel,
            )
    else:
        candidates = [
            item
            for item in manifest.models
            if item.get("domain") == "ironbug" and item.get("target_type") == "ironbug_model"
        ]
        if len(candidates) == 1:
            target = normalize_ironbug_model_target(candidates[0])
            spec_path = _ensure_contained(garden_root, garden_root / target["path"])
            sys_id = str(target["id"])
        elif not candidates:
            raise ValueError("Garden has no Ironbug HVAC systems. Call IB_create_system first.")
        else:
            ids = ", ".join(str(c.get("id")) for c in candidates)
            raise ValueError(
                f"Garden has multiple Ironbug systems ({ids}); pass ironbug_model_target or identifier."
            )

    draft_path = spec_path.with_name(draft_filename(sys_id))
    _ensure_contained(garden_root, draft_path)
    return manifest, target, spec_path, draft_path


def load_ironbug_system_files(
    garden_root: Path,
    *,
    ironbug_model_target: dict[str, Any] | None = None,
    identifier: str | None = None,
) -> tuple[GardenManifest, dict[str, Any], Path, Path, dict[str, Any], dict[str, Any]]:
    """Load official specification dict and authoring draft dict."""
    manifest, target, spec_path, draft_path = resolve_ironbug_system(
        garden_root,
        ironbug_model_target=ironbug_model_target,
        identifier=identifier,
    )
    if not spec_path.is_file():
        raise ValueError(f"Ironbug specification file missing: {to_posix_relative(spec_path, garden_root)}")
    spec_dict = json.loads(spec_path.read_text(encoding="utf-8"))
    if draft_path.is_file():
        draft_dict = json.loads(draft_path.read_text(encoding="utf-8"))
    else:
        draft_dict = empty_draft(
            display_name=spec_dict.get("DisplayName"),
            imported_only=True,
        )
    return manifest, target, spec_path, draft_path, spec_dict, draft_dict


def save_ironbug_system(
    garden_root: Path,
    manifest: GardenManifest,
    *,
    identifier: str,
    specification_json: str,
    draft: dict[str, Any],
    overwrite: bool = True,
    operation_type: str = "ironbug_system_save",
    operation_id: str | None = None,
) -> tuple[dict[str, Any], str, str]:
    """Commit official IB_HVACSystem JSON + authoring draft atomically into Garden."""
    expected_revision = manifest.revision
    spec_rel = (IRONBUG_MODELS_DIR / spec_filename(identifier)).as_posix()
    draft_rel = (IRONBUG_MODELS_DIR / draft_filename(identifier)).as_posix()

    other_models = [
        item
        for item in manifest.models
        if item.get("domain") == "ironbug" and item.get("id") != identifier
    ]
    reject_windows_alias(identifier, (item.get("id") for item in other_models), label="Ironbug system identifier")
    reject_windows_alias(spec_rel, (item.get("path") for item in other_models), label="Ironbug system path")

    spec_path = garden_root / spec_rel
    if spec_path.exists() and not overwrite:
        replay = read_operation_record(garden_root, operation_id) if operation_id else None
        if replay is None:
            raise ValueError(
                f"Ironbug system '{identifier}' already exists. Pass overwrite=true to replace it."
            )

    # Pretty-format official IB_HVACSystem JSON cleanly while preserving every $type and field
    parsed_spec = json.loads(specification_json)
    spec_bytes = (json.dumps(parsed_spec, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    draft_bytes = (json.dumps(draft, indent=2, ensure_ascii=False) + "\n").encode("utf-8")

    target = make_ironbug_model_target(
        garden_id=manifest.garden_id,
        identifier=identifier,
        path=spec_rel,
    )
    manifest.models = [
        item
        for item in manifest.models
        if not (item.get("domain") == "ironbug" and item.get("id") == identifier)
    ]
    manifest.models.append(target)

    commit_manifest(
        garden_root,
        manifest,
        operation_type=operation_type,
        operation_id=operation_id,
        expected_revision=expected_revision,
        staged_writes={
            spec_rel: spec_bytes,
            draft_rel: draft_bytes,
        },
    )
    return target, spec_rel, draft_rel
