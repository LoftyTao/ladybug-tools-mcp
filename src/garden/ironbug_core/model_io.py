"""Ironbug model IO inside a Garden."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ironbug.hvac import IB_Model
from ironbug.ibjson import model_from_ibjson, model_to_ibjson_string

from garden.manifest import GardenManifest
from garden.operations import commit_manifest, read_operation_record
from garden.paths import (
    reject_windows_alias,
    to_posix_relative,
    validate_portable_file_name,
)
from garden.ironbug_core.targets import (
    make_ironbug_model_target,
    normalize_ironbug_model_target,
)


IRONBUG_MODELS_DIR = Path("models") / "ironbug"


def ironbug_model_filename(identifier: str) -> str:
    """Return the Garden file name for an Ironbug model identifier."""

    if not identifier.strip():
        raise ValueError("Ironbug model identifier must not be empty.")
    return validate_portable_file_name(
        f"{identifier}.ibjson",
        label="Ironbug model file name",
    )


def ironbug_model_path(garden_root: Path, identifier: str) -> Path:
    """Return the Garden-local ibjson path for an Ironbug model identifier."""

    return garden_root / IRONBUG_MODELS_DIR / ironbug_model_filename(identifier)


def _ensure_garden_contained(garden_root: Path, path: Path) -> Path:
    garden_root = garden_root.resolve()
    resolved = path.resolve()
    if resolved != garden_root and garden_root not in resolved.parents:
        raise ValueError("Ironbug model path must be Garden-contained.")
    return resolved


def resolve_ironbug_model_target(
    garden_root: Path,
    *,
    ironbug_model_target: dict[str, Any] | None = None,
    path: str | None = None,
) -> tuple[GardenManifest, dict[str, Any], Path]:
    """Resolve an Ironbug target or Garden-contained path."""

    manifest = GardenManifest.read(garden_root)
    if ironbug_model_target is not None and path is not None:
        raise ValueError("Pass either ironbug_model_target or path, not both.")
    if ironbug_model_target is not None:
        target = normalize_ironbug_model_target(ironbug_model_target)
        model_path = _ensure_garden_contained(garden_root, garden_root / target["path"])
        return manifest, target, model_path
    if not path:
        raise ValueError("Pass an ironbug_model_target or a Garden-relative .ibjson path.")

    raw_path = Path(path).expanduser()
    model_path = raw_path if raw_path.is_absolute() else garden_root / raw_path
    model_path = _ensure_garden_contained(garden_root, model_path)
    relative = to_posix_relative(model_path, garden_root)
    matches = [
        item
        for item in manifest.models
        if item.get("domain") == "ironbug" and item.get("path") == relative
    ]
    if matches:
        target = normalize_ironbug_model_target(matches[0])
    else:
        target = make_ironbug_model_target(
            garden_id=manifest.garden_id,
            identifier=model_path.stem,
            path=relative,
        )
    return manifest, target, model_path


def load_ironbug_model(
    garden_root: Path,
    *,
    ironbug_model_target: dict[str, Any] | None = None,
    path: str | None = None,
) -> tuple[GardenManifest, dict[str, Any], Path, IB_Model]:
    """Load an Ironbug model from a target or Garden path."""

    manifest, target, model_path = resolve_ironbug_model_target(
        garden_root,
        ironbug_model_target=ironbug_model_target,
        path=path,
    )
    return manifest, target, model_path, model_from_ibjson(model_path)


def save_ironbug_model(
    garden_root: Path,
    manifest: GardenManifest,
    model: IB_Model,
    *,
    identifier: str,
    overwrite: bool = False,
    operation_id: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Save an Ironbug model into Garden authoring truth and update manifest."""

    expected_revision = manifest.revision
    persisted_path = (IRONBUG_MODELS_DIR / ironbug_model_filename(identifier)).as_posix()
    other_models = [
        item
        for item in manifest.models
        if item.get("domain") == "ironbug" and item.get("id") != identifier
    ]
    reject_windows_alias(
        identifier,
        (item.get("id") for item in other_models),
        label="Ironbug model identifier",
    )
    reject_windows_alias(
        persisted_path,
        (item.get("path") for item in other_models),
        label="Ironbug model path",
    )
    output_path = garden_root / persisted_path
    if output_path.exists() and not overwrite:
        replay_record = (
            read_operation_record(garden_root, operation_id)
            if operation_id is not None
            else None
        )
        if replay_record is None:
            raise ValueError(
                f"Ironbug model already exists: {identifier}. "
                "Pass overwrite=true to replace it."
            )
    content = model_to_ibjson_string(model, indent=2).encode("utf-8")
    target = make_ironbug_model_target(
        garden_id=manifest.garden_id,
        identifier=identifier,
        path=persisted_path,
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
        operation_type="ironbug_model_save",
        operation_id=operation_id,
        expected_revision=expected_revision,
        staged_writes={persisted_path: content},
    )
    return target, persisted_path
