"""Dragonfly Display VisualizationSet services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dragonfly_display.model import (
    model_comparison_to_vis_set,
    model_envelope_edges_to_vis_set,
    model_to_vis_set,
)

from garden.dragonfly_core.model_io import load_dragonfly_model, resolve_model_target
from garden.paths import slugify_name
from garden.visualize.artifacts import save_visualization_set
from ladybug_tools_mcp.contracts.report import make_report


def _summarize_visualization_set(
    visualization_set: dict[str, Any],
) -> dict[str, Any]:
    geometry_layers = visualization_set.get("geometry", [])
    layer_identifiers = [
        layer.get("identifier")
        for layer in geometry_layers
        if isinstance(layer, dict) and layer.get("identifier")
    ]
    return {
        "identifier": visualization_set.get("identifier"),
        "display_name": visualization_set.get("display_name"),
        "units": visualization_set.get("units"),
        "geometry_count": len(geometry_layers),
        "geometry_identifiers": layer_identifiers,
    }


def _set_visualization_set_name(vis_set: Any, name: str | None) -> None:
    if not name:
        return
    vis_set.identifier = slugify_name(name)
    vis_set.display_name = name


def _visualization_set_response(
    *,
    garden_root_path: Path,
    visualization_set: dict[str, Any],
    summary: dict[str, Any],
    source: dict[str, Any],
    name: str | None,
    return_visualization_set: bool,
    message: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "visualization_set": visualization_set,
        "summary_view": summary,
        "report": make_report(status="ok", message=message),
    }
    if return_visualization_set:
        return result
    saved = save_visualization_set(
        garden_root=str(garden_root_path),
        visualization_set=visualization_set,
        name=name or visualization_set.get("identifier") or "dragonfly_display",
        source=source,
    )
    result["target"] = saved["target"]
    result["visualization_set_target"] = saved["visualization_set_target"]
    result["persistence_receipt"] = saved["persistence_receipt"]
    result["summary_view"]["visualization_set_target"] = saved[
        "visualization_set_target"
    ]
    result["summary_view"]["body_returned"] = False
    result.pop("visualization_set", None)
    return result


def _edge_fallback_visualization_set_response(
    *,
    garden_root_path: Path,
    model: Any,
    manifest: Any,
    resolved_target: dict[str, Any],
    original_error: Exception,
    name: str | None,
    return_visualization_set: bool,
) -> dict[str, Any]:
    """Return an honest wireframe fallback when Dragonfly Display edge view fails."""
    fallback_name = name or "dragonfly_envelope_edges_fallback"
    vis_set = model_to_vis_set(
        model,
        use_multiplier=True,
        include_wireframe=True,
        use_mesh=False,
        hide_color_by=True,
        reset_coordinates=True,
    )
    _set_visualization_set_name(vis_set, fallback_name)
    visualization_set = vis_set.to_dict()
    summary = _summarize_visualization_set(visualization_set)
    original_error_message = str(original_error)
    summary.update(
        {
            "garden_target": manifest.target(),
            "model_target": resolved_target,
            "edge_view_status": "degraded",
            "fallback_tool": "dragonfly_model_to_visualization_set",
            "fallback_reason": "dragonfly_display_envelope_edges_failed",
            "original_error": original_error_message,
            "use_multiplier": True,
            "include_wireframe": True,
            "use_mesh": False,
            "hide_color_by": True,
            "reset_coordinates": True,
        }
    )
    result = _visualization_set_response(
        garden_root_path=garden_root_path,
        visualization_set=visualization_set,
        summary=summary,
        source={
            "tool": "dragonfly_model_envelope_edges_to_visualization_set",
            "model_target": resolved_target,
            "fallback_tool": "dragonfly_model_to_visualization_set",
            "original_error": original_error_message,
        },
        name=fallback_name,
        return_visualization_set=return_visualization_set,
        message=(
            "Dragonfly envelope-edge SDK view failed; returned a wireframe "
            "model VisualizationSet fallback."
        ),
    )
    result["report"] = make_report(
        status="degraded",
        message=(
            "Dragonfly envelope-edge SDK view failed; returned a wireframe "
            "model VisualizationSet fallback."
        ),
        warnings=[
            "This is a wireframe model preview fallback, not the strict Dragonfly "
            "Display envelope-edge output."
        ],
        details={
            "fallback_tool": "dragonfly_model_to_visualization_set",
            "fallback_reason": "dragonfly_display_envelope_edges_failed",
            "original_error": original_error_message,
        },
    )
    return result


def dragonfly_model_to_visualization_set(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    use_multiplier: bool = True,
    exclude_plenums: bool = False,
    solve_ceiling_adjacencies: bool = False,
    merge_method: str = "None",
    color_by: str | None = "type",
    include_wireframe: bool = True,
    use_mesh: bool = True,
    hide_color_by: bool = False,
    grid_display_mode: str = "Default",
    hide_grid: bool = False,
    reset_coordinates: bool = False,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Translate a Garden Dragonfly model into a Ladybug Display VisualizationSet."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_target)
    vis_set = model_to_vis_set(
        model,
        use_multiplier=use_multiplier,
        exclude_plenums=exclude_plenums,
        solve_ceiling_adjacencies=solve_ceiling_adjacencies,
        merge_method=merge_method,
        color_by=color_by,
        include_wireframe=include_wireframe,
        use_mesh=use_mesh,
        hide_color_by=hide_color_by,
        grid_display_mode=grid_display_mode,
        hide_grid=hide_grid,
        reset_coordinates=reset_coordinates,
    )
    if name:
        _set_visualization_set_name(vis_set, name)

    visualization_set = vis_set.to_dict()
    summary = _summarize_visualization_set(visualization_set)
    summary.update(
        {
            "garden_target": manifest.target(),
            "model_target": resolved_target,
            "use_multiplier": use_multiplier,
            "exclude_plenums": exclude_plenums,
            "solve_ceiling_adjacencies": solve_ceiling_adjacencies,
            "merge_method": merge_method,
            "color_by": color_by,
            "include_wireframe": include_wireframe,
            "use_mesh": use_mesh,
            "hide_color_by": hide_color_by,
            "grid_display_mode": grid_display_mode,
            "hide_grid": hide_grid,
            "reset_coordinates": reset_coordinates,
        }
    )
    return _visualization_set_response(
        garden_root_path=garden_root_path,
        visualization_set=visualization_set,
        summary=summary,
        source={
            "tool": "dragonfly_model_to_visualization_set",
            "model_target": resolved_target,
        },
        name=name,
        return_visualization_set=return_visualization_set,
        message="Dragonfly model VisualizationSet created.",
    )


def dragonfly_model_envelope_edges_to_visualization_set(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    coplanar_type: str = "FloorPlatesOnly",
    mullion_thickness: float | None = None,
    reset_coordinates: bool = False,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a Dragonfly Display envelope-edge VisualizationSet."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_target)
    try:
        vis_set = model_envelope_edges_to_vis_set(
            model,
            coplanar_type=coplanar_type,
            mullion_thickness=mullion_thickness,
            reset_coordinates=reset_coordinates,
        )
    except Exception as exc:
        return _edge_fallback_visualization_set_response(
            garden_root_path=garden_root_path,
            model=model,
            manifest=manifest,
            resolved_target=resolved_target,
            original_error=exc,
            name=name,
            return_visualization_set=return_visualization_set,
        )
    if name:
        _set_visualization_set_name(vis_set, name)
    visualization_set = vis_set.to_dict()
    summary = _summarize_visualization_set(visualization_set)
    summary.update(
        {
            "garden_target": manifest.target(),
            "model_target": resolved_target,
            "coplanar_type": coplanar_type,
            "mullion_thickness": mullion_thickness,
            "reset_coordinates": reset_coordinates,
        }
    )
    return _visualization_set_response(
        garden_root_path=garden_root_path,
        visualization_set=visualization_set,
        summary=summary,
        source={
            "tool": "dragonfly_model_envelope_edges_to_visualization_set",
            "model_target": resolved_target,
        },
        name=name,
        return_visualization_set=return_visualization_set,
        message="Dragonfly model envelope-edge VisualizationSet created.",
    )


def dragonfly_models_to_comparison_visualization_set(
    *,
    garden_root: str,
    base_model_target: dict[str, Any],
    incoming_model_target: dict[str, Any],
    use_multiplier: bool = True,
    exclude_plenums: bool = False,
    solve_ceiling_adjacencies: bool = False,
    merge_method: str = "None",
    reset_coordinates: bool = False,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a Dragonfly Display comparison VisualizationSet for two models."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_base_target = resolve_model_target(
        garden_root_path,
        base_model_target,
    )
    _manifest, resolved_incoming_target = resolve_model_target(
        garden_root_path,
        incoming_model_target,
    )
    base_model = load_dragonfly_model(garden_root_path, resolved_base_target)
    incoming_model = load_dragonfly_model(garden_root_path, resolved_incoming_target)
    vis_set = model_comparison_to_vis_set(
        base_model,
        incoming_model,
        use_multiplier=use_multiplier,
        exclude_plenums=exclude_plenums,
        solve_ceiling_adjacencies=solve_ceiling_adjacencies,
        merge_method=merge_method,
        reset_coordinates=reset_coordinates,
    )
    if name:
        _set_visualization_set_name(vis_set, name)
    visualization_set = vis_set.to_dict()
    summary = _summarize_visualization_set(visualization_set)
    summary.update(
        {
            "garden_target": manifest.target(),
            "base_model_target": resolved_base_target,
            "incoming_model_target": resolved_incoming_target,
            "use_multiplier": use_multiplier,
            "exclude_plenums": exclude_plenums,
            "solve_ceiling_adjacencies": solve_ceiling_adjacencies,
            "merge_method": merge_method,
            "reset_coordinates": reset_coordinates,
        }
    )
    return _visualization_set_response(
        garden_root_path=garden_root_path,
        visualization_set=visualization_set,
        summary=summary,
        source={
            "tool": "dragonfly_models_to_comparison_visualization_set",
            "base_model_target": resolved_base_target,
            "incoming_model_target": resolved_incoming_target,
        },
        name=name,
        return_visualization_set=return_visualization_set,
        message="Dragonfly comparison VisualizationSet created.",
    )
