"""Fairyfly Display VisualizationSet services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fairyfly_therm.result import THMZResult
from ladybug.color import Color
from ladybug_display.analysis import AnalysisGeometry, VisualizationData
from ladybug_display.context import ContextGeometry
from ladybug_display.geometry3d import DisplayFace3D, DisplayLineSegment3D
from ladybug_display.visualization import VisualizationSet

from garden.fairyfly.model import _model_counts
from garden.fairyfly.model_io import load_fairyfly_model, resolve_model_target
from garden.fairyfly.results import read_fairyfly_therm_result
from garden.visualize.artifacts import save_visualization_set
from ladybug_tools_mcp.contracts.report import make_report

DEFAULT_SHAPE_COLOR = Color(180, 180, 180)
DEFAULT_BOUNDARY_COLOR = Color(50, 110, 200)
_THERM_RESULT_UNITS = {
    "temperature": "C",
    "heat_flux": "W/m2",
}


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


def _shape_color(shape: Any, color_by: str) -> Color:
    if color_by == "material":
        material = getattr(shape.properties.therm, "material", None)
        return getattr(material, "color", DEFAULT_SHAPE_COLOR) or DEFAULT_SHAPE_COLOR
    return DEFAULT_SHAPE_COLOR


def _boundary_color(boundary: Any) -> Color:
    condition = getattr(boundary.properties.therm, "condition", None)
    return getattr(condition, "color", DEFAULT_BOUNDARY_COLOR) or DEFAULT_BOUNDARY_COLOR


def _model_visualization_set(
    *,
    model: Any,
    identifier: str,
    color_by: str,
    include_boundaries: bool,
) -> VisualizationSet:
    geometry = []
    shape_faces = [
        DisplayFace3D(shape.geometry, color=_shape_color(shape, color_by))
        for shape in model.shapes
    ]
    if shape_faces:
        geometry.append(ContextGeometry("Fairyfly_Shapes", shape_faces))
    if include_boundaries:
        boundary_lines = [
            DisplayLineSegment3D(segment, color=_boundary_color(boundary))
            for boundary in model.boundaries
            for segment in boundary.geometry
        ]
        if boundary_lines:
            geometry.append(ContextGeometry("Fairyfly_Boundaries", boundary_lines))
    vis_set = VisualizationSet(identifier, geometry, model.units)
    vis_set.display_name = identifier
    return vis_set


def fairyfly_model_to_visualization_set(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    color_by: str = "material",
    include_boundaries: bool = True,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Translate a Garden Fairyfly model into a Ladybug Display VisualizationSet."""
    normalized_color_by = str(color_by or "material").strip().lower()
    if normalized_color_by not in {"material", "none"}:
        raise ValueError("Unsupported Fairyfly model color_by. Use 'material' or 'none'.")
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_target = resolve_model_target(garden_root_path, model_target)
    model = load_fairyfly_model(garden_root_path, resolved_target)
    identifier = name or str(resolved_target.get("model_identifier") or "fairyfly_model")
    vis_set = _model_visualization_set(
        model=model,
        identifier=identifier,
        color_by=normalized_color_by,
        include_boundaries=include_boundaries,
    )
    visualization_set = vis_set.to_dict()
    summary = _summarize_visualization_set(visualization_set)
    summary.update(
        {
            "garden_target": manifest.target(),
            "model_target": resolved_target,
            "object_counts": _model_counts(model),
            "color_by": normalized_color_by,
            "include_boundaries": include_boundaries,
        }
    )
    result: dict[str, Any] = {
        "visualization_set": visualization_set,
        "summary_view": summary,
        "report": make_report(
            status="ok",
            message="Fairyfly model VisualizationSet created.",
        ),
    }
    if not return_visualization_set:
        saved = save_visualization_set(
            garden_root=str(garden_root_path),
            visualization_set=visualization_set,
            name=identifier,
            source={
                "tool": "fairyfly_model_to_visualization_set",
                "model_target": resolved_target,
            },
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


def fairyfly_therm_result_to_visualization_set(
    *,
    garden_root: str,
    thmz_target: dict[str, Any] | None = None,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    data_type: str = "temperature",
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Translate a completed THERM result mesh into a VisualizationSet."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    read_result = read_fairyfly_therm_result(
        garden_root=str(garden_root_path),
        thmz_target=thmz_target,
        run_target=run_target,
        run_id=run_id,
        data_type=data_type,
        include_values=True,
    )
    summary = dict(read_result.get("summary_view", {}))
    if summary.get("status") == "no_results":
        return {
            "summary_view": summary,
            "report": make_report(
                status="warning",
                message="THERM result mesh values are not available for visualization.",
                warnings=list(read_result.get("report", {}).get("warnings", [])),
            ),
        }

    values = list(read_result.get("values", []))
    thmz_path = (garden_root_path / str(summary["thmz_path"])).resolve()
    thmz_path.relative_to(garden_root_path)
    thmz_result = THMZResult(str(thmz_path))
    mesh = thmz_result.mesh
    if mesh is None or not values:
        summary.update({"status": "no_results", "value_count": 0})
        return {
            "summary_view": summary,
            "report": make_report(
                status="warning",
                message="THERM result mesh values are not available for visualization.",
                warnings=["THERM mesh/results are missing from the THMZ."],
            ),
        }

    normalized_data_type = str(summary.get("data_type") or data_type)
    unit = _THERM_RESULT_UNITS.get(normalized_data_type, "")
    identifier = name or f"fairyfly_therm_{summary['run_id']}_{normalized_data_type}"
    visualization_data = VisualizationData(values, unit=unit)
    analysis = AnalysisGeometry(
        "Fairyfly_THERM_Result",
        [mesh],
        [visualization_data],
        display_mode="SurfaceWithEdges",
    )
    analysis.display_name = f"Fairyfly THERM {normalized_data_type}"
    vis_set = VisualizationSet(identifier, [analysis], "Millimeters")
    vis_set.display_name = identifier
    visualization_set = vis_set.to_dict()
    vis_summary = _summarize_visualization_set(visualization_set)
    summary.update(
        {
            **vis_summary,
            "status": "ok",
            "units": unit,
            "visualization_units": "Millimeters",
            "body_returned": return_visualization_set,
        }
    )
    result: dict[str, Any] = {
        "visualization_set": visualization_set,
        "summary_view": summary,
        "report": make_report(
            status="ok",
            message="Fairyfly THERM result VisualizationSet created.",
        ),
    }
    if not return_visualization_set:
        saved = save_visualization_set(
            garden_root=str(garden_root_path),
            visualization_set=visualization_set,
            name=identifier,
            source={
                "tool": "fairyfly_therm_result_to_visualization_set",
                "therm_result_target": read_result.get("therm_result_target"),
                "run_id": summary.get("run_id"),
                "data_type": normalized_data_type,
            },
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
