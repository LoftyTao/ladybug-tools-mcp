"""Dragonfly model I/O inside a Garden."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dragonfly.model import Model

from garden.dragonfly_core.targets import is_dragonfly_model_target
from garden.manifest import GardenManifest
from garden.model_io import (
    _load_model,
    _model_filename,
    _model_target_for_manifest,
    _resolve_model_target,
    _save_model,
)

DRAGONFLY_MODELS_DIR = Path("models") / "dragonfly"


def model_filename(model_identifier: str) -> str:
    """Return the Garden file name for a Dragonfly model identifier."""
    return _model_filename(model_identifier, "dragonfly")


def dragonfly_model_path(garden_root: Path, model_identifier: str) -> Path:
    """Return the DFJSON path for a model identifier."""
    return garden_root / DRAGONFLY_MODELS_DIR / _model_filename(model_identifier, "dragonfly")


def model_target_for_manifest(
    garden_id: str,
    model_identifier: str,
    *,
    path: str | None = None,
) -> dict[str, Any]:
    """Build a Dragonfly model target with optional Garden-relative path."""
    return _model_target_for_manifest(garden_id, model_identifier, "dragonfly", path)


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
    return _load_model(
        garden_root,
        model_target,
        normalize_target=normalize_dragonfly_model_target,
        target_kind="dragonfly",
        loader=lambda path: Model.from_dfjson(str(path), cleanup_irrational=False),
    )


def resolve_model_target(
    garden_root: Path,
    model_target: dict[str, Any] | None = None,
) -> tuple[GardenManifest, dict[str, Any]]:
    """Resolve an explicit Dragonfly model target or the Garden base Dragonfly model."""
    return _resolve_model_target(
        garden_root,
        model_target,
        domain="dragonfly",
        normalize_target=normalize_dragonfly_model_target,
    )


def save_dragonfly_model(
    garden_root: Path,
    manifest: GardenManifest,
    model: Model,
    *,
    name: str | None = None,
    indent: int | None = 2,
    included_prop: list[str] | None = None,
    set_base: bool = False,
    operation_id: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Save a Dragonfly model into Garden authoring truth and update manifest."""
    output_name = name or model.identifier
    content = json.dumps(
        model.to_dict(included_prop=included_prop),
        indent=indent,
    ).encode("utf-8")
    return _save_model(
        garden_root,
        manifest,
        domain="dragonfly",
        output_name=output_name,
        content=content,
        set_base=set_base,
        operation_id=operation_id,
    )
