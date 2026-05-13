"""Fairyfly model I/O inside a Garden."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import fairyfly_therm  # noqa: F401
from fairyfly.model import Model

from garden.manifest import GardenManifest
from garden.paths import to_posix_relative
from ladybug_tools_mcp.contracts.targets import make_model_target

FAIRYFLY_MODELS_DIR = Path("models") / "fairyfly"


def model_filename(model_identifier: str) -> str:
    """Return the Garden file name for a Fairyfly model identifier."""
    return f"{model_identifier}.ffjson"


def fairyfly_model_path(garden_root: Path, model_identifier: str) -> Path:
    """Return the FFJSON path for a model identifier."""
    return garden_root / FAIRYFLY_MODELS_DIR / model_filename(model_identifier)


def model_target_for_manifest(
    garden_id: str,
    model_identifier: str,
    *,
    path: str | None = None,
) -> dict[str, Any]:
    """Build a Fairyfly model target with optional Garden-relative path."""
    target: dict[str, Any] = make_model_target(
        garden_id=garden_id,
        model_identifier=model_identifier,
        domain="fairyfly",
    )
    if path:
        target["path"] = path
    return target


def normalize_fairyfly_model_target(value: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a Fairyfly model target."""
    if not isinstance(value, dict):
        raise ValueError("Fairyfly model target must be a dictionary.")
    if value.get("target_type") != "model":
        raise ValueError("Fairyfly model target must have target_type 'model'.")
    if value.get("domain") != "fairyfly":
        raise ValueError("Fairyfly model target must have domain 'fairyfly'.")
    model_identifier = value.get("model_identifier")
    if not isinstance(model_identifier, str) or not model_identifier:
        raise ValueError("Fairyfly model target requires model_identifier.")
    return dict(value)


def load_fairyfly_model(garden_root: Path, model_target: dict[str, Any]) -> Model:
    """Load a Fairyfly model from a Garden model target."""
    model_target = normalize_fairyfly_model_target(model_target)
    path_value = model_target.get("path")
    if path_value:
        model_path = garden_root / str(path_value)
    else:
        model_path = fairyfly_model_path(
            garden_root,
            str(model_target["model_identifier"]),
        )
    data = json.loads(model_path.read_text(encoding="utf-8"))
    return Model.from_dict(data)


def resolve_model_target(
    garden_root: Path,
    model_target: dict[str, Any] | None = None,
) -> tuple[GardenManifest, dict[str, Any]]:
    """Resolve an explicit Fairyfly model target or the Garden base Fairyfly model."""
    manifest = GardenManifest.read(garden_root)
    model_target = model_target or manifest.base_fairyfly_model
    if not model_target:
        raise ValueError(
            "Garden has no base Fairyfly model. Create or set a Fairyfly model first."
        )
    return manifest, normalize_fairyfly_model_target(model_target)


def save_fairyfly_model(
    garden_root: Path,
    manifest: GardenManifest,
    model: Model,
    *,
    name: str | None = None,
    indent: int | None = 2,
    set_base: bool = False,
) -> tuple[dict[str, Any], str]:
    """Save a Fairyfly model into Garden authoring truth and update manifest."""
    model_dir = garden_root / FAIRYFLY_MODELS_DIR
    model_dir.mkdir(parents=True, exist_ok=True)
    output_name = name or str(model.display_name or model.identifier)
    output_path = model_dir / model_filename(output_name)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(model.to_dict(), handle, indent=indent)
        handle.write("\n")
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
            item.get("domain") == "fairyfly"
            and item.get("model_identifier") == output_name
        )
    ]
    manifest.models.append(target)
    if set_base or manifest.base_fairyfly_model is None:
        manifest.base_fairyfly_model = target
    manifest.write(garden_root)
    return target, persisted_path
