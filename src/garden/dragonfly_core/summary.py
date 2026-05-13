"""Dragonfly compact model summary services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dragonfly.model import Model

from garden.dragonfly_core.model_io import load_dragonfly_model, resolve_model_target
from ladybug_tools_mcp.contracts.report import make_report


def _counts(model: Model) -> dict[str, int]:
    return {
        "buildings": len(model.buildings),
        "stories": len(model.stories),
        "room2ds": len(model.room_2ds),
        "context_shades": len(model.context_shades),
    }


def _metadata(model: Model) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "identifier": model.identifier,
        "display_name": model.display_name,
        "units": model.units,
        "tolerance": model.tolerance,
        "angle_tolerance": model.angle_tolerance,
    }
    for attr in (
        "average_story_count",
        "average_height",
        "footprint_area",
        "floor_area",
        "volume",
    ):
        value = getattr(model, attr, None)
        if value is not None:
            metadata[attr] = value
    return metadata


def get_dragonfly_model_summary(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return compact Dragonfly model counts and metadata without DFJSON body."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    summary_view = {
        "garden_target": manifest.target(),
        "model_target": resolved_model_target,
        "base_dragonfly_model": manifest.base_dragonfly_model,
        "counts": _counts(model),
        "metadata": _metadata(model),
    }
    return {
        "model_target": resolved_model_target,
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message=f"Summarized Dragonfly model: {model.identifier}",
        ),
    }
