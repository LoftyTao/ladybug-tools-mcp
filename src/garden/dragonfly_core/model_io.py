"""Dragonfly model I/O inside a Garden."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dragonfly.model import Model

from garden.manifest import GardenManifest
from garden.paths import to_posix_relative
from garden.dragonfly_core.targets import is_dragonfly_model_target

DRAGONFLY_MODELS_DIR = Path("models") / "dragonfly"


def model_filename(model_identifier: str) -> str:
    """Return the Garden file name for a Dragonfly model identifier."""
    return f"{model_identifier}.dfjson"


def dragonfly_model_path(garden_root: Path, model_identifier: str) -> Path:
    """Return the DFJSON path for a model identifier."""
    return garden_root / DRAGONFLY_MODELS_DIR / model_filename(model_identifier)


def model_target_for_manifest(
    garden_id: str,
    model_identifier: str,
    *,
    path: str | None = None,
) -> dict[str, Any]:
    """Build a Dragonfly model target with optional Garden-relative path."""
    target: dict[str, Any] = {
        "target_type": "dragonfly_model",
        "id": model_identifier,
        "garden_id": garden_id,
        "domain": "dragonfly",
        "model_identifier": model_identifier,
    }
    if path:
        target["path"] = path
    return target


def normalize_dragonfly_model_target(value: Any) -> dict[str, Any]:
    """Validate and normalize a Dragonfly model target."""
    if not is_dragonfly_model_target(value):
        raise ValueError(
            "Dragonfly model target must be a dict with target_type "
            "'dragonfly_model' and a non-empty id."
        )
    target = dict(value)
    target["domain"] = "dragonfly"
    target["model_identifier"] = str(target["id"])
    return target


def load_dragonfly_model(garden_root: Path, model_target: dict[str, Any]) -> Model:
    """Load a Dragonfly model from a Garden model target."""
    model_target = normalize_dragonfly_model_target(model_target)
    path_value = model_target.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("Dragonfly model target requires a Garden-relative path.")
    model_path = garden_root / path_value
    return Model.from_dfjson(str(model_path), cleanup_irrational=False)


def resolve_model_target(
    garden_root: Path,
    model_target: dict[str, Any] | None = None,
) -> tuple[GardenManifest, dict[str, Any]]:
    """Resolve an explicit Dragonfly model target or the Garden base Dragonfly model."""
    manifest = GardenManifest.read(garden_root)
    model_target = model_target or manifest.base_dragonfly_model
    if not model_target:
        raise ValueError(
            "Garden has no base Dragonfly model. Create or set a Dragonfly model first."
        )
    return manifest, normalize_dragonfly_model_target(model_target)


def save_dragonfly_model(
    garden_root: Path,
    manifest: GardenManifest,
    model: Model,
    *,
    name: str | None = None,
    indent: int | None = 2,
    included_prop: list[str] | None = None,
    set_base: bool = False,
) -> tuple[dict[str, Any], str]:
    """Save a Dragonfly model into Garden authoring truth and update manifest."""
    model_dir = garden_root / DRAGONFLY_MODELS_DIR
    model_dir.mkdir(parents=True, exist_ok=True)
    output_name = name or model.identifier
    model.to_dfjson(
        name=output_name,
        folder=str(model_dir),
        indent=indent,
        included_prop=included_prop,
    )
    output_path = model_dir / model_filename(output_name)
    persisted_path = to_posix_relative(output_path, garden_root)
    target = model_target_for_manifest(
        manifest.garden_id,
        output_name,
        path=persisted_path,
    )
    manifest.models = [
        item
        for item in manifest.models
        if not (
            item.get("domain") == "dragonfly"
            and item.get("model_identifier") == output_name
        )
    ]
    manifest.models.append(target)
    if set_base or manifest.base_dragonfly_model is None:
        manifest.base_dragonfly_model = target
    manifest.write(garden_root)
    return target, persisted_path
