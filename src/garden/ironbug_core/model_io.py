"""Ironbug model IO inside a Garden."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ironbug.hvac import IB_Model
from ironbug.ibjson import model_from_ibjson, model_to_ibjson

from garden.manifest import GardenManifest
from garden.paths import to_posix_relative
from garden.ironbug_core.targets import (
    make_ironbug_model_target,
    normalize_ironbug_model_target,
)


IRONBUG_MODELS_DIR = Path("models") / "ironbug"


def ironbug_model_filename(identifier: str) -> str:
    """Return the Garden file name for an Ironbug model identifier."""

    return f"{identifier}.ibjson"


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
) -> tuple[dict[str, Any], str]:
    """Save an Ironbug model into Garden authoring truth and update manifest."""

    model_dir = garden_root / IRONBUG_MODELS_DIR
    model_dir.mkdir(parents=True, exist_ok=True)
    output_path = model_dir / ironbug_model_filename(identifier)
    if output_path.exists() and not overwrite:
        raise ValueError(
            f"Ironbug model already exists: {identifier}. "
            "Pass overwrite=true to replace it."
        )
    model_to_ibjson(model, output_path)
    persisted_path = to_posix_relative(output_path, garden_root)
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
    manifest.write(garden_root)
    return target, persisted_path
