"""Fairyfly model I/O inside a Garden."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import fairyfly_therm  # noqa: F401
from fairyfly.model import Model

from garden.manifest import GardenManifest
from garden.model_io import (
    _load_model,
    _model_filename,
    _model_target_for_manifest,
    _resolve_model_target,
    _save_model,
)

FAIRYFLY_MODELS_DIR = Path("models") / "fairyfly"


def model_filename(model_identifier: str) -> str:
    """Return the Garden file name for a Fairyfly model identifier."""
    return _model_filename(model_identifier, "fairyfly")


def fairyfly_model_path(garden_root: Path, model_identifier: str) -> Path:
    """Return the FFJSON path for a model identifier."""
    return garden_root / FAIRYFLY_MODELS_DIR / _model_filename(model_identifier, "fairyfly")


def model_target_for_manifest(
    garden_id: str,
    model_identifier: str,
    *,
    path: str | None = None,
) -> dict[str, Any]:
    """Build a Fairyfly model target with optional Garden-relative path."""
    return _model_target_for_manifest(garden_id, model_identifier, "fairyfly", path)


def normalize_fairyfly_model_target(value: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a Fairyfly model target."""
    if not isinstance(value, dict):
        raise ValueError("Fairyfly model target must be a dictionary.")
    if value.get("target_type") != "fairyfly_model":
        raise ValueError("Fairyfly model target must have target_type 'fairyfly_model'.")
    if value.get("domain") != "fairyfly":
        raise ValueError("Fairyfly model target must have domain 'fairyfly'.")
    model_identifier = value.get("model_identifier")
    if not isinstance(model_identifier, str) or not model_identifier:
        raise ValueError("Fairyfly model target requires model_identifier.")
    return dict(value)


def load_fairyfly_model(garden_root: Path, model_target: dict[str, Any]) -> Model:
    """Load a Fairyfly model from a Garden model target."""
    return _load_model(
        garden_root,
        model_target,
        normalize_target=normalize_fairyfly_model_target,
        target_kind="fairyfly",
        loader=lambda path: Model.from_dict(
            json.loads(path.read_text(encoding="utf-8"))
        ),
    )


def resolve_model_target(
    garden_root: Path,
    model_target: dict[str, Any] | None = None,
) -> tuple[GardenManifest, dict[str, Any]]:
    """Resolve an explicit Fairyfly model target or the Garden base Fairyfly model."""
    return _resolve_model_target(
        garden_root,
        model_target,
        domain="fairyfly",
        normalize_target=normalize_fairyfly_model_target,
    )


def save_fairyfly_model(
    garden_root: Path,
    manifest: GardenManifest,
    model: Model,
    *,
    name: str | None = None,
    indent: int | None = 2,
    set_base: bool = False,
    operation_id: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Save a Fairyfly model into Garden authoring truth and update manifest."""
    output_name = name or str(model.display_name or model.identifier)
    content = (json.dumps(model.to_dict(), indent=indent) + "\n").encode("utf-8")
    return _save_model(
        garden_root,
        manifest,
        domain="fairyfly",
        output_name=output_name,
        content=content,
        set_base=set_base,
        operation_id=operation_id,
    )
