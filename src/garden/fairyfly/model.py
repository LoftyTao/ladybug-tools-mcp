"""Fairyfly model I/O, 2D geometry, materials, authoring, validation, and display."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import fairyfly_therm  # noqa: F401
from fairyfly.boundary import Boundary
from fairyfly.model import Model
from fairyfly.shape import Shape
from fairyfly_therm.condition.steadystate import SteadyState
from fairyfly_therm.material.dictutil import dict_to_material
from fairyfly_therm.material.solid import SolidMaterial
from fairyfly_therm.result import THMZResult
from ladybug.color import Color
from ladybug_display.analysis import AnalysisGeometry, VisualizationData
from ladybug_display.context import ContextGeometry
from ladybug_display.geometry3d import DisplayFace3D, DisplayLineSegment3D
from ladybug_display.visualization import VisualizationSet
from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry2d.polygon import Polygon2D
from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.line import LineSegment3D
from ladybug_geometry.geometry3d.pointvector import Point3D

from garden.manifest import GardenManifest
from garden.model_io import (
    _load_model,
    _model_filename,
    _model_target_for_manifest,
    _resolve_model_target,
    _save_model,
)
from garden.paths import require_garden_root
from garden.visualize.artifacts import save_visualization_set
from ladybug_tools_mcp.contracts import make_persistence_receipt, make_report

FAIRYFLY_MODELS_DIR = Path("models") / "fairyfly"
DEFAULT_SHAPE_COLOR = Color(180, 180, 180)
DEFAULT_BOUNDARY_COLOR = Color(50, 110, 200)
_THERM_RESULT_UNITS = {
    "temperature": "C",
    "heat_flux": "W/m2",
}


# ---------------------------------------------------------------------------
# Model I/O
# ---------------------------------------------------------------------------


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
        loader=lambda path: Model.from_dict(json.loads(path.read_text(encoding="utf-8"))),
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
    )


# ---------------------------------------------------------------------------
# 2D Geometry adapters & materials
# ---------------------------------------------------------------------------


def _point2d(value: Iterable[float]) -> Point2D:
    coords = list(value)
    if len(coords) < 2:
        raise ValueError("2D points must include x and y coordinates.")
    return Point2D(float(coords[0]), float(coords[1]))


def _point3d_from_2d(point: Point2D) -> Point3D:
    return Point3D(point.x, point.y, 0)


def polygon2d_from_vertices(
    vertices_2d: list[list[float]],
    *,
    tolerance: float | None = None,
) -> Polygon2D:
    """Create a cleaned Polygon2D from public 2D vertex input."""
    polygon = Polygon2D(tuple(_point2d(vertex) for vertex in vertices_2d))
    if tolerance is not None:
        polygon = polygon.remove_duplicate_vertices(tolerance)
        polygon = polygon.remove_colinear_vertices(tolerance)
    if len(polygon.vertices) < 3:
        raise ValueError("A Fairyfly Shape polygon needs at least three vertices.")
    if polygon.is_self_intersecting:
        raise ValueError(
            "Self-intersecting Fairyfly Shape polygons are not supported by this "
            "tool yet. Split the polygon before adding it to the model."
        )
    return polygon


def face3d_from_vertices_2d(
    vertices_2d: list[list[float]],
    *,
    holes_2d: list[list[list[float]]] | None = None,
    tolerance: float | None = None,
) -> Face3D:
    """Create a z=0 Face3D from 2D polygon input."""
    polygon = polygon2d_from_vertices(vertices_2d, tolerance=tolerance)
    boundary = tuple(_point3d_from_2d(point) for point in polygon.vertices)
    holes = None
    if holes_2d:
        holes = tuple(
            tuple(_point3d_from_2d(point) for point in hole.vertices)
            for hole in (
                polygon2d_from_vertices(hole_vertices, tolerance=tolerance)
                for hole_vertices in holes_2d
            )
        )
    return Face3D(boundary, holes=holes)


def line_segments3d_from_segments_2d(
    line_segments_2d: list[list[list[float]]],
) -> tuple[LineSegment3D, ...]:
    """Create z=0 LineSegment3D objects from public 2D segment input."""
    segments: list[LineSegment3D] = []
    for segment in line_segments_2d:
        if len(segment) != 2:
            raise ValueError("Each Fairyfly boundary segment must have two points.")
        segment_2d = LineSegment2D.from_end_points(_point2d(segment[0]), _point2d(segment[1]))
        segments.append(LineSegment3D.from_line_segment2d(segment_2d))
    if not segments:
        raise ValueError("Fairyfly boundaries need at least one line segment.")
    return tuple(segments)


def _color_from_rgb(rgb_color: list[int] | None) -> Color | None:
    if rgb_color is None:
        return None
    if len(rgb_color) != 3:
        raise ValueError("rgb_color must be [r, g, b].")
    return Color(*(int(value) for value in rgb_color))


def create_fairyfly_solid_material(
    *,
    name: str,
    conductivity: float,
    emissivity: float = 0.9,
    emissivity_back: float | None = None,
    density: float | None = None,
    porosity: float | None = None,
    specific_heat: float | None = None,
    vapor_diffusion_resistance: float | None = None,
    reflectance: float | None = None,
    transmittance: float | None = None,
    rgb_color: list[int] | None = None,
) -> dict[str, Any]:
    """Create a Fairyfly SolidMaterial payload."""
    material = SolidMaterial(
        conductivity=conductivity,
        emissivity=emissivity,
        emissivity_back=emissivity_back,
        density=density,
        porosity=porosity,
        specific_heat=specific_heat,
        vapor_diffusion_resistance=vapor_diffusion_resistance,
        reflectance=reflectance,
        transmittance=transmittance,
    )
    material.display_name = name
    material.color = _color_from_rgb(rgb_color) or Color(180, 180, 180)
    material_dict = material.to_dict()
    return {
        "object_dict": material_dict,
        "target": material_dict,
        "summary_view": {
            "type": material_dict.get("type"),
            "identifier": material_dict.get("identifier"),
            "display_name": material_dict.get("display_name") or material_dict.get("identifier"),
            "conductivity": material_dict.get("conductivity"),
            "emissivity": material_dict.get("emissivity"),
            "color": material_dict.get("color"),
        },
        "report": make_report(status="ok", message=f"Created Fairyfly solid material: {name}"),
    }


# ---------------------------------------------------------------------------
# Model authoring & validation
# ---------------------------------------------------------------------------


def _model_counts(model: Model) -> dict[str, int]:
    return {
        "shapes": len(getattr(model, "shapes", []) or []),
        "boundaries": len(getattr(model, "boundaries", []) or []),
    }


def _save_changed_model(
    garden_root: Path,
    manifest: GardenManifest,
    model_target: dict[str, Any],
    model: Model,
) -> tuple[dict[str, Any], str]:
    return save_fairyfly_model(
        garden_root,
        manifest,
        model,
        name=str(model_target["model_identifier"]),
        set_base=manifest.base_fairyfly_model == model_target,
    )


def _model_update_response(
    *,
    model: Model,
    model_target: dict[str, Any],
    garden_id: str,
    persisted_path: str,
    operation: str,
    message: str,
    change_details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "object_dict": model_target,
        "target": model_target,
        "model_target": model_target,
        "fairyfly_model_target": model_target,
        "summary_view": {
            "model_target": model_target,
            "object_counts": _model_counts(model),
            **change_details,
        },
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=garden_id,
            model_target=model_target,
            persisted_path=persisted_path,
            change_summary={"operation": operation, "target": model_target, **change_details},
        ),
        "report": make_report(status="ok", message=message),
    }


def create_fairyfly_model(
    *,
    garden_root: str,
    identifier: str,
    units: str = "Millimeters",
    tolerance: float | None = None,
    angle_tolerance: float = 1.0,
    display_name: str | None = None,
    save_back: bool = True,
    set_base: bool = True,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create a Fairyfly Model and optionally persist it to a Garden."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    model = Model(units=units, tolerance=tolerance, angle_tolerance=angle_tolerance)
    model.display_name = display_name or identifier
    receipt: dict[str, Any] | None = None
    if save_back:
        model_target, persisted_path = save_fairyfly_model(
            garden_root_path, manifest, model, name=identifier, set_base=set_base
        )
        object_dict = model_target
        receipt = make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            model_target=model_target,
            persisted_path=persisted_path,
            change_summary={
                "operation": "create_fairyfly_model",
                "target": model_target,
                "base_fairyfly_model_changed": bool(set_base),
            },
        )
    else:
        object_dict = (
            model.to_dict()
            if include_body
            else {"domain": "fairyfly", "model_identifier": identifier}
        )

    return {
        "object_dict": object_dict,
        "target": object_dict,
        "model_target": object_dict,
        "fairyfly_model_target": object_dict,
        "summary_view": {
            "model_identifier": identifier,
            "sdk_identifier": model.identifier,
            "display_name": model.display_name,
            "domain": "fairyfly",
            "units": model.units,
            "saved": save_back,
            "base_fairyfly_model_changed": bool(save_back and set_base),
            "object_counts": _model_counts(model),
        },
        "persistence_receipt": receipt,
        "report": make_report(status="ok", message=f"Created Fairyfly model: {identifier}"),
    }


def add_fairyfly_shape_to_model(
    *,
    garden_root: str,
    vertices_2d: list[list[float]],
    material: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    name: str | None = None,
    holes_2d: list[list[list[float]]] | None = None,
    rgb_color: list[int] | None = None,
    tolerance: float | None = None,
) -> dict[str, Any]:
    """Add a 2D Fairyfly Shape to a Garden-backed model."""
    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_fairyfly_model(garden_root_path, resolved_model_target)
    shape = Shape(face3d_from_vertices_2d(vertices_2d, holes_2d=holes_2d, tolerance=tolerance))
    if name:
        shape.display_name = name
    material_obj = dict_to_material(material)
    color = _color_from_rgb(rgb_color)
    if color is not None:
        material_obj.color = color
    shape.properties.therm.material = material_obj
    model.add_shape(shape)
    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path, manifest, resolved_model_target, model
    )
    return _model_update_response(
        model=model,
        model_target=updated_model_target,
        garden_id=manifest.garden_id,
        persisted_path=persisted_path,
        operation="add_fairyfly_shape_to_model",
        message=f"Added Fairyfly shape: {shape.display_name}",
        change_details={
            "added_shape": {
                "display_name": shape.display_name,
                "area": shape.area,
                "material": shape.properties.therm.material.display_name,
            }
        },
    )


def add_fairyfly_boundary_to_model(
    *,
    garden_root: str,
    line_segments_2d: list[list[list[float]]],
    temperature: float,
    film_coefficient: float,
    model_target: dict[str, Any] | None = None,
    name: str | None = None,
    emissivity: float = 1.0,
    radiant_temperature: float | None = None,
    heat_flux: float = 0,
    relative_humidity: float = 0.5,
    u_factor_tag: str | None = None,
    rgb_color: list[int] | None = None,
) -> dict[str, Any]:
    """Add a 2D Fairyfly Boundary to a Garden-backed model."""
    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_fairyfly_model(garden_root_path, resolved_model_target)
    boundary = Boundary(line_segments3d_from_segments_2d(line_segments_2d))
    if name:
        boundary.display_name = name
    condition = SteadyState(
        temperature=temperature,
        film_coefficient=film_coefficient,
        emissivity=emissivity,
        radiant_temperature=radiant_temperature,
        heat_flux=heat_flux,
        relative_humidity=relative_humidity,
    )
    condition.display_name = name or f"{temperature}C boundary"
    condition.color = _color_from_rgb(rgb_color) or Color(50, 110, 200)
    boundary.properties.therm.condition = condition
    boundary.properties.therm.u_factor_tag = u_factor_tag
    model.add_boundary(boundary)
    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path, manifest, resolved_model_target, model
    )
    return _model_update_response(
        model=model,
        model_target=updated_model_target,
        garden_id=manifest.garden_id,
        persisted_path=persisted_path,
        operation="add_fairyfly_boundary_to_model",
        message=f"Added Fairyfly boundary: {boundary.display_name}",
        change_details={
            "added_boundary": {
                "display_name": boundary.display_name,
                "length": boundary.length,
                "condition": condition.display_name,
                "u_factor_tag": u_factor_tag,
            }
        },
    )


def validate_fairyfly_model(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a Garden-backed Fairyfly model with the Fairyfly SDK."""
    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_target = resolve_model_target(garden_root_path, model_target)
    model = load_fairyfly_model(garden_root_path, resolved_target)
    try:
        raw = model.check_all(raise_exception=False, detailed=True)
    except AttributeError:
        raw = []
    if raw is None:
        issues: list[str] = []
    elif isinstance(raw, (list, tuple)):
        issues = [str(item) for item in raw if item]
    else:
        issues = [str(raw)] if raw else []
    valid = len(issues) == 0
    return {
        "valid": valid,
        "is_valid": valid,
        "issues": issues,
        "summary_view": {
            "garden_target": manifest.target(),
            "model_target": resolved_target,
            "object_counts": _model_counts(model),
            "issue_count": len(issues),
        },
        "report": make_report(
            status="ok" if valid else "warning",
            message="Fairyfly model validation completed.",
            warnings=issues,
        ),
    }


# ---------------------------------------------------------------------------
# VisualizationSet display adapters
# ---------------------------------------------------------------------------


def _summarize_visualization_set(visualization_set: dict[str, Any]) -> dict[str, Any]:
    geometry_layers = visualization_set.get("geometry", [])
    return {
        "identifier": visualization_set.get("identifier"),
        "display_name": visualization_set.get("display_name"),
        "units": visualization_set.get("units"),
        "geometry_count": len(geometry_layers),
        "geometry_identifiers": [
            layer.get("identifier")
            for layer in geometry_layers
            if isinstance(layer, dict) and layer.get("identifier")
        ],
    }


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
    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_target = resolve_model_target(garden_root_path, model_target)
    model = load_fairyfly_model(garden_root_path, resolved_target)
    identifier = name or str(resolved_target.get("model_identifier") or "fairyfly_model")

    geometry = []
    shape_faces = [
        DisplayFace3D(
            shape.geometry,
            color=(
                (getattr(getattr(shape.properties.therm, "material", None), "color", DEFAULT_SHAPE_COLOR) or DEFAULT_SHAPE_COLOR)
                if normalized_color_by == "material"
                else DEFAULT_SHAPE_COLOR
            ),
        )
        for shape in model.shapes
    ]
    if shape_faces:
        geometry.append(ContextGeometry("Fairyfly_Shapes", shape_faces))
    if include_boundaries:
        boundary_lines = [
            DisplayLineSegment3D(
                segment,
                color=getattr(getattr(boundary.properties.therm, "condition", None), "color", DEFAULT_BOUNDARY_COLOR) or DEFAULT_BOUNDARY_COLOR,
            )
            for boundary in model.boundaries
            for segment in boundary.geometry
        ]
        if boundary_lines:
            geometry.append(ContextGeometry("Fairyfly_Boundaries", boundary_lines))
    vis_set = VisualizationSet(identifier, geometry, model.units)
    vis_set.display_name = identifier
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
        "report": make_report(status="ok", message="Fairyfly model VisualizationSet created."),
    }
    if not return_visualization_set:
        saved = save_visualization_set(
            garden_root=str(garden_root_path),
            visualization_set=visualization_set,
            name=identifier,
            source={"tool": "fairyfly_model_to_visualization_set", "model_target": resolved_target},
        )
        result["target"] = saved["target"]
        result["visualization_set_target"] = saved["visualization_set_target"]
        result["persistence_receipt"] = saved["persistence_receipt"]
        result["summary_view"]["visualization_set_target"] = saved["visualization_set_target"]
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
    from .therm import read_fairyfly_therm_result

    garden_root_path = require_garden_root(garden_root)
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
    mesh = THMZResult(str(thmz_path)).mesh
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
    analysis = AnalysisGeometry(
        "Fairyfly_THERM_Result",
        [mesh],
        [VisualizationData(values, unit=unit)],
        display_mode="SurfaceWithEdges",
    )
    analysis.display_name = f"Fairyfly THERM {normalized_data_type}"
    vis_set = VisualizationSet(identifier, [analysis], "Millimeters")
    vis_set.display_name = identifier
    visualization_set = vis_set.to_dict()
    summary.update(
        {
            **_summarize_visualization_set(visualization_set),
            "status": "ok",
            "units": unit,
            "visualization_units": "Millimeters",
            "body_returned": return_visualization_set,
        }
    )
    result: dict[str, Any] = {
        "visualization_set": visualization_set,
        "summary_view": summary,
        "report": make_report(status="ok", message="Fairyfly THERM result VisualizationSet created."),
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
        result["summary_view"]["visualization_set_target"] = saved["visualization_set_target"]
        result["summary_view"]["body_returned"] = False
        result.pop("visualization_set", None)
    return result
