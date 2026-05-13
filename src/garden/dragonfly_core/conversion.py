"""Dragonfly to Honeybee conversion services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dragonfly.model import Model as DragonflyModel

from garden.dragonfly_core.model_io import (
    load_dragonfly_model,
    resolve_model_target,
    save_dragonfly_model,
)
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target as resolve_honeybee_model_target,
    save_honeybee_model,
)
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report


def dragonfly_model_to_honeybee(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    object_per_model: str = "Building",
    shade_distance: float | None = None,
    use_multiplier: bool = True,
    exclude_plenums: bool = False,
    cap: bool = False,
    solve_ceiling_adjacencies: bool = False,
    merge_method: str | None = None,
    tolerance: float | None = None,
    enforce_adj: bool = True,
    enforce_solid: bool = True,
    set_base: bool = False,
) -> dict[str, Any]:
    """Convert a Garden Dragonfly model to Honeybee model HBJSON files."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(
        garden_root_path,
        model_target,
    )
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    honeybee_models = model.to_honeybee(
        object_per_model=object_per_model,
        shade_distance=shade_distance,
        use_multiplier=use_multiplier,
        exclude_plenums=exclude_plenums,
        cap=cap,
        solve_ceiling_adjacencies=solve_ceiling_adjacencies,
        merge_method=merge_method,
        tolerance=tolerance,
        enforce_adj=enforce_adj,
        enforce_solid=enforce_solid,
    )
    honeybee_model_targets: list[dict[str, Any]] = []
    persisted_paths: list[str] = []
    for index, honeybee_model in enumerate(honeybee_models):
        target, persisted_path = save_honeybee_model(
            garden_root_path,
            manifest,
            honeybee_model,
            set_base=set_base and index == 0,
        )
        honeybee_model_targets.append(target)
        persisted_paths.append(persisted_path)

    receipt = make_persistence_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        model_target=honeybee_model_targets[0] if honeybee_model_targets else {},
        persisted_path=persisted_paths[0] if persisted_paths else None,
        change_summary={
            "operation": "dragonfly_model_to_honeybee",
            "source_model_target": resolved_model_target,
            "honeybee_model_targets": honeybee_model_targets,
            "persisted_paths": persisted_paths,
            "set_base": set_base,
        },
    )
    return {
        "honeybee_model_targets": honeybee_model_targets,
        "model_targets": honeybee_model_targets,
        "source_model_target": resolved_model_target,
        "summary_view": {
            "garden_target": manifest.target(),
            "source_model_target": resolved_model_target,
            "honeybee_model_count": len(honeybee_model_targets),
            "honeybee_model_targets": honeybee_model_targets,
            "base_honeybee_model_changed": bool(set_base and honeybee_model_targets),
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=(
                f"Converted Dragonfly model to {len(honeybee_model_targets)} "
                "Honeybee model(s)."
            ),
        ),
    }


def honeybee_model_to_dragonfly(
    *,
    garden_root: str,
    identifier: str,
    honeybee_model_target: dict[str, Any] | None = None,
    conversion_method: str = "AllRoom2D",
    set_base: bool = True,
) -> dict[str, Any]:
    """Convert a Garden Honeybee model to a Dragonfly model DFJSON file."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_honeybee_target = resolve_honeybee_model_target(
        garden_root_path,
        honeybee_model_target,
    )
    honeybee_model = load_honeybee_model(garden_root_path, resolved_honeybee_target)
    dragonfly_model = DragonflyModel.from_honeybee(
        honeybee_model,
        conversion_method=conversion_method,
    )
    dragonfly_model.identifier = identifier
    dragonfly_model_target, persisted_path = save_dragonfly_model(
        garden_root_path,
        manifest,
        dragonfly_model,
        name=identifier,
        set_base=set_base,
    )
    receipt = make_persistence_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        model_target=dragonfly_model_target,
        persisted_path=persisted_path,
        change_summary={
            "operation": "honeybee_model_to_dragonfly",
            "source_model_target": resolved_honeybee_target,
            "dragonfly_model_target": dragonfly_model_target,
            "base_dragonfly_model_changed": bool(set_base),
        },
    )
    return {
        "dragonfly_model_target": dragonfly_model_target,
        "model_target": dragonfly_model_target,
        "source_model_target": resolved_honeybee_target,
        "summary_view": {
            "garden_target": manifest.target(),
            "source_model_target": resolved_honeybee_target,
            "dragonfly_model_target": dragonfly_model_target,
            "base_dragonfly_model_changed": bool(set_base),
            "building_count": len(dragonfly_model.buildings),
            "story_count": len(dragonfly_model.stories),
            "room2d_count": len(dragonfly_model.room_2ds),
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=f"Converted Honeybee model to Dragonfly model: {identifier}",
        ),
    }
