"""Dragonfly model I/O, compact summary, and validation inside a Garden."""

from __future__ import annotations

from collections import Counter
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
from garden.paths import require_garden_root
from ladybug_tools_mcp.contracts import make_report

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
) -> tuple[dict[str, Any], str]:
    """Save a Dragonfly model into Garden authoring truth and update manifest."""
    output_name = name or model.identifier
    content = json.dumps(model.to_dict(included_prop=included_prop), indent=indent).encode("utf-8")
    return _save_model(
        garden_root,
        manifest,
        domain="dragonfly",
        output_name=output_name,
        content=content,
        set_base=set_base,
    )


def get_dragonfly_model_summary(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return compact Dragonfly model counts and metadata without DFJSON body."""
    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    metadata: dict[str, Any] = {
        "identifier": model.identifier,
        "display_name": model.display_name,
        "units": model.units,
        "tolerance": model.tolerance,
        "angle_tolerance": model.angle_tolerance,
    }
    for attr in ("average_story_count", "average_height", "footprint_area", "floor_area", "volume"):
        value = getattr(model, attr, None)
        if value is not None:
            metadata[attr] = value
    return {
        "model_target": resolved_model_target,
        "summary_view": {
            "garden_target": manifest.target(),
            "model_target": resolved_model_target,
            "base_dragonfly_model": manifest.base_dragonfly_model,
            "counts": {
                "buildings": len(model.buildings),
                "stories": len(model.stories),
                "room2ds": len(model.room_2ds),
                "context_shades": len(model.context_shades),
            },
            "metadata": metadata,
        },
        "report": make_report(status="ok", message=f"Summarized Dragonfly model: {model.identifier}"),
    }


def validate_dragonfly_model(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a Dragonfly model and return structured validation issues."""
    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)

    try:
        issues = model.check_all(raise_exception=False, detailed=True)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Failed to validate Dragonfly model. {exc}") from exc

    issue_codes = [issue["code"] for issue in issues if isinstance(issue, dict) and isinstance(issue.get("code"), str)]
    issue_types = [issue["error_type"] for issue in issues if isinstance(issue, dict) and isinstance(issue.get("error_type"), str)]
    element_types = [issue["element_type"] for issue in issues if isinstance(issue, dict) and isinstance(issue.get("element_type"), str)]
    is_valid = len(issues) == 0

    return {
        "is_valid": is_valid,
        "valid": is_valid,
        "issues": issues,
        "summary_view": {
            "garden_target": manifest.target(),
            "model_target": resolved_model_target,
            "model_identifier": str(resolved_model_target["model_identifier"]),
            "is_valid": is_valid,
            "issue_count": len(issues),
            "issue_codes": sorted(set(issue_codes)),
            "issue_types": sorted(set(issue_types)),
            "issue_counts_by_code": dict(sorted(Counter(issue_codes).items())),
            "issue_counts_by_type": dict(sorted(Counter(issue_types).items())),
            "issue_element_types": sorted(set(element_types)),
            "object_counts": {
                "buildings": len(model.buildings),
                "stories": len(model.stories),
                "room2ds": len(model.room_2ds),
                "room3ds": len(model.room_3ds),
                "context_shades": len(model.context_shades),
            },
        },
        "report": make_report(
            status="ok" if is_valid else "invalid",
            message=(
                f"Dragonfly model is valid: {model.identifier}"
                if is_valid
                else f"Dragonfly model has {len(issues)} validation issue(s): {model.identifier}"
            ),
            details={
                "is_valid": is_valid,
                "issue_count": len(issues),
                "issue_codes": sorted(set(issue_codes)),
                "issue_types": sorted(set(issue_types)),
            },
        ),
    }
