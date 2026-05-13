"""Dragonfly model I/O inside a Garden."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dragonfly.model import Model

from garden.manifest import GardenManifest
from garden.paths import to_posix_relative
from ladybug_tools_mcp.contracts.targets import make_model_target

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
    target: dict[str, Any] = make_model_target(
        garden_id=garden_id,
        model_identifier=model_identifier,
        domain="dragonfly",
    )
    if path:
        target["path"] = path
    return target


def dragonfly_model_target_from_path(
    garden_id: str,
    path_value: str,
) -> dict[str, Any]:
    """Build a Dragonfly model target from a Garden-relative DFJSON path."""
    model_identifier = Path(path_value).stem
    return model_target_for_manifest(
        garden_id,
        model_identifier,
        path=path_value,
    )


def dragonfly_model_target_from_object_target(
    garden_id: str,
    value: dict[str, Any],
) -> dict[str, Any] | None:
    """Infer a Dragonfly model target from a Dragonfly object target."""
    if value.get("target_type") == "model" or value.get("domain") != "dragonfly":
        return None
    model_identifier = value.get("model_identifier")
    if not isinstance(model_identifier, str) or not model_identifier:
        return None
    path_value = value.get("path")
    model_path = None
    if (
        isinstance(path_value, str)
        and path_value.startswith("models/dragonfly/")
        and path_value.endswith(".dfjson")
    ):
        model_path = path_value
    return model_target_for_manifest(garden_id, model_identifier, path=model_path)


def normalize_dragonfly_model_target(value: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a Dragonfly model target."""
    if not isinstance(value, dict):
        raise ValueError("Dragonfly model target must be a dictionary.")
    if value.get("target_type") != "model":
        raise ValueError("Dragonfly model target must have target_type 'model'.")
    if value.get("domain") != "dragonfly":
        raise ValueError("Dragonfly model target must have domain 'dragonfly'.")
    model_identifier = value.get("model_identifier")
    if not isinstance(model_identifier, str) or not model_identifier:
        raise ValueError("Dragonfly model target requires model_identifier.")
    return dict(value)


def load_dragonfly_model(garden_root: Path, model_target: dict[str, Any]) -> Model:
    """Load a Dragonfly model from a Garden model target."""
    model_target = normalize_dragonfly_model_target(model_target)
    path_value = model_target.get("path")
    if path_value:
        model_path = garden_root / str(path_value)
    else:
        model_path = dragonfly_model_path(
            garden_root,
            str(model_target["model_identifier"]),
        )
    return Model.from_dfjson(str(model_path), cleanup_irrational=False)


def resolve_model_target(
    garden_root: Path,
    model_target: dict[str, Any] | str | None = None,
) -> tuple[GardenManifest, dict[str, Any]]:
    """Resolve an explicit Dragonfly model target or the Garden base Dragonfly model."""
    manifest = GardenManifest.read(garden_root)
    if isinstance(model_target, str):
        model_target = dragonfly_model_target_from_path(manifest.garden_id, model_target)
    else:
        model_target = model_target or manifest.base_dragonfly_model
    if isinstance(model_target, dict):
        nested_model_target = model_target.get("model_target")
        if isinstance(nested_model_target, dict):
            model_target = nested_model_target
        elif isinstance(model_target.get("target"), dict):
            model_target = model_target["target"]
        model_target = (
            dragonfly_model_target_from_object_target(manifest.garden_id, model_target)
            or model_target
        )
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
