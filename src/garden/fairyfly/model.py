"""Fairyfly model I/O, 2D geometry, materials, authoring, validation, and display."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable
import uuid
import xml.etree.ElementTree as ET

import fairyfly_hygrotherm  # noqa: F401
import fairyfly_next_therm.lib.conditions as _ff_conditions
import fairyfly_next_therm.lib.gases as _ff_gases
import fairyfly_next_therm.lib.materials as _ff_materials
from fairyfly.boundary import Boundary
from fairyfly.model import Model
from fairyfly.shape import Shape
from fairyfly_next_therm.condition.dictutil import dict_to_condition
from fairyfly_next_therm.condition.steadystate import SteadyState
from fairyfly_next_therm.condition.transient import Transient
from fairyfly_next_therm.material.cavity import CavityMaterial
from fairyfly_next_therm.material.dictutil import dict_to_material
from fairyfly_next_therm.material.gas import Gas, PureGas
from fairyfly_next_therm.material.hygrothermal import HygrothermalMaterial
from fairyfly_next_therm.material.solid import SolidMaterial
from fairyfly_next_therm.material.xmlutil import extract_all_materials_from_xml_file
from fairyfly_next_therm.result import THMZResult
from ladybug.color import Color
from ladybug.legend import Legend, LegendParameters
from ladybug_display.analysis import AnalysisGeometry, VisualizationData
from ladybug_display.context import ContextGeometry
from ladybug_display.geometry3d import DisplayFace3D, DisplayLineSegment3D
from ladybug_display.visualization import VisualizationSet
from ladybug_geometry.geometry2d.line import LineSegment2D
from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry2d.polygon import Polygon2D
from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.line import LineSegment3D
from ladybug_geometry.geometry3d.plane import Plane
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.polyface import Polyface3D

from garden.manifest import GardenManifest
from garden.model_io import (
    _load_model,
    _model_filename,
    _model_target_for_manifest,
    _resolve_model_target,
    _save_model,
)
from garden.paths import (
    require_garden_root,
    resolve_contained_path,
    resolve_existing_garden_path,
    slugify_name,
    to_posix_relative,
)
from garden.visualize.artifacts import save_visualization_set
from ladybug_tools_mcp.contracts import make_artifact_receipt, make_persistence_receipt, make_report

FAIRYFLY_MODELS_DIR = Path("models") / "fairyfly"
DEFAULT_SHAPE_COLOR = Color(180, 180, 180)
DEFAULT_BOUNDARY_COLOR = Color(50, 110, 200)
_THERM_RESULT_UNITS = {
    "temperature": "C",
    "heat_flux": "W/m2",
    "heat_flux_vectors": "W/m2",
    "humidity": "fraction",
    "water_content": "kg/m3",
}
_HYGROTHERMAL_SPEC_KEYS = frozenset({
    "moisture_storage_function",
    "liquid_transport_suction",
    "liquid_transport_redistribution",
    "conductivity_moisture_dependent",
    "conductivity_temperature_dependent",
    "diffusion_moisture_dependent",
    "enthalpy_temperature_dependent",
    "reference_water_content",
    "free_water_saturation",
    "water_absorption_coefficient",
    "drying_factor",
    "roughness",
    "conductivity_moisture_supplement",
    "conductivity_temperature_supplement",
    "conductivity_design_value",
    "typical_built_in_moisture",
    "default_thickness",
    "material_information",
})
_TRANSIENT_CONDITION_KEYS = (
    "bc_type",
    "bc_model",
    "convection_model",
    "radiation_model",
    "timesteps",
    "wind_speed",
    "wind_direction",
    "use_heat_flux",
    "use_temperature",
    "imposed_temperature",
    "use_humidity",
    "imposed_humidity",
    "radiation_temperature",
    "surface_emissivity",
    "view_factor",
    "hr",
    "solar_radiation",
    "absorptance",
    "timestep_file_name",
    "surface_tilt",
    "surface_length",
    "building_width",
    "building_height",
)


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


def _plane_from_spec(plane: Plane | dict[str, Any] | None) -> Plane | None:
    if plane is None:
        return None
    if isinstance(plane, Plane):
        return plane
    if not isinstance(plane, dict):
        raise ValueError("Fairyfly plane must be a dictionary or Plane instance.")
    if "type" in plane:
        return Plane.from_dict(plane)
    normal = plane.get("normal") if plane.get("normal") is not None else plane.get("n")
    origin = plane.get("origin") if plane.get("origin") is not None else plane.get("o")
    x_axis = plane.get("x_axis") if plane.get("x_axis") is not None else plane.get("x")
    n_vec = Vector3D(*(float(v) for v in (normal or (0.0, 0.0, 1.0))))
    o_pt = Point3D(*(float(v) for v in (origin or (0.0, 0.0, 0.0))))
    x_vec = Vector3D(*(float(v) for v in x_axis)) if x_axis is not None else None
    return Plane(n=n_vec, o=o_pt, x=x_vec)


def _point3d_from_2d(point: Point2D, plane: Plane | None = None) -> Point3D:
    if plane is not None:
        return plane.xy_to_xyz(point)
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
    plane: Plane | dict[str, Any] | None = None,
) -> Face3D:
    """Create a Face3D from 2D polygon input in the specified 3D plane (or XY plane)."""
    plane_obj = _plane_from_spec(plane)
    polygon = polygon2d_from_vertices(vertices_2d, tolerance=tolerance)
    boundary = tuple(_point3d_from_2d(point, plane_obj) for point in polygon.vertices)
    holes = None
    if holes_2d:
        holes = tuple(
            tuple(_point3d_from_2d(point, plane_obj) for point in hole.vertices)
            for hole in (
                polygon2d_from_vertices(hole_vertices, tolerance=tolerance)
                for hole_vertices in holes_2d
            )
        )
    return Face3D(boundary, holes=holes)


def line_segments3d_from_segments_2d(
    line_segments_2d: list[list[list[float]]],
    *,
    plane: Plane | dict[str, Any] | None = None,
) -> tuple[LineSegment3D, ...]:
    """Create LineSegment3D objects from 2D segment input in a 3D plane (or XY plane)."""
    plane_obj = _plane_from_spec(plane)
    segments: list[LineSegment3D] = []
    for segment in line_segments_2d:
        if len(segment) != 2:
            raise ValueError("Each Fairyfly boundary segment must have two points.")
        pt1 = _point2d(segment[0])
        pt2 = _point2d(segment[1])
        if plane_obj is not None:
            segments.append(
                LineSegment3D.from_end_points(
                    _point3d_from_2d(pt1, plane_obj),
                    _point3d_from_2d(pt2, plane_obj),
                )
            )
        else:
            segment_2d = LineSegment2D.from_end_points(pt1, pt2)
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


def _coerce_pure_gas(spec: Any) -> PureGas:
    if isinstance(spec, PureGas):
        return spec
    if isinstance(spec, str):
        return _ff_gases.pure_gas_by_name(spec)
    if not isinstance(spec, dict):
        raise ValueError("Each pure gas entry must be a name string or PureGas spec dictionary.")
    if isinstance(spec.get("object_dict"), dict):
        spec = spec["object_dict"]
    if spec.get("type") == "PureGas":
        return PureGas.from_dict(spec)
    if spec.get("pure_gas_name") or (spec.get("name") and "conductivity_coeff_a" not in spec):
        return _ff_gases.pure_gas_by_name(str(spec.get("pure_gas_name") or spec["name"]))
    pure_gas = PureGas(
        conductivity_coeff_a=float(spec["conductivity_coeff_a"]),
        viscosity_coeff_a=float(spec["viscosity_coeff_a"]),
        specific_heat_coeff_a=float(spec["specific_heat_coeff_a"]),
        conductivity_coeff_b=float(spec.get("conductivity_coeff_b", 0.0)),
        viscosity_coeff_b=float(spec.get("viscosity_coeff_b", 0.0)),
        specific_heat_coeff_b=float(spec.get("specific_heat_coeff_b", 0.0)),
        conductivity_coeff_c=float(spec.get("conductivity_coeff_c", 0.0)),
        viscosity_coeff_c=float(spec.get("viscosity_coeff_c", 0.0)),
        specific_heat_coeff_c=float(spec.get("specific_heat_coeff_c", 0.0)),
        specific_heat_ratio=float(spec.get("specific_heat_ratio", 1.0)),
        molecular_weight=float(spec.get("molecular_weight", 20.0)),
        identifier=spec.get("identifier"),
    )
    if spec.get("name") or spec.get("display_name"):
        pure_gas.display_name = str(spec.get("display_name") or spec["name"])
    return pure_gas


def _coerce_gas(spec: Any) -> Gas:
    if spec is None:
        return _ff_gases.air
    if isinstance(spec, Gas):
        return spec
    if isinstance(spec, str):
        return _ff_gases.gas_by_name(spec)
    if not isinstance(spec, dict):
        raise ValueError("Gas specification must be a gas name string or dictionary.")
    if isinstance(spec.get("object_dict"), dict):
        spec = spec["object_dict"]
    if spec.get("type") == "Gas":
        return Gas.from_dict(spec)
    if spec.get("gas_name") or (spec.get("name") and "pure_gases" not in spec):
        return _ff_gases.gas_by_name(str(spec.get("gas_name") or spec["name"]))
    pure_gases = [_coerce_pure_gas(item) for item in (spec.get("pure_gases") or ())]
    fractions = [float(item) for item in (spec.get("gas_fractions") or ())]
    if not pure_gases or len(pure_gases) != len(fractions):
        raise ValueError("Custom Gas requires matching 'pure_gases' and 'gas_fractions' lists.")
    gas = Gas(pure_gases=pure_gases, gas_fractions=fractions, identifier=spec.get("identifier"))
    if spec.get("name") or spec.get("display_name"):
        gas.display_name = str(spec.get("display_name") or spec["name"])
    return gas


def create_fairyfly_pure_gas(
    *,
    name: str,
    conductivity_coeff_a: float,
    viscosity_coeff_a: float,
    specific_heat_coeff_a: float,
    conductivity_coeff_b: float = 0.0,
    viscosity_coeff_b: float = 0.0,
    specific_heat_coeff_b: float = 0.0,
    conductivity_coeff_c: float = 0.0,
    viscosity_coeff_c: float = 0.0,
    specific_heat_coeff_c: float = 0.0,
    specific_heat_ratio: float = 1.0,
    molecular_weight: float = 20.0,
) -> dict[str, Any]:
    """Create a Fairyfly PureGas payload."""
    pure_gas = PureGas(
        conductivity_coeff_a=conductivity_coeff_a,
        viscosity_coeff_a=viscosity_coeff_a,
        specific_heat_coeff_a=specific_heat_coeff_a,
        conductivity_coeff_b=conductivity_coeff_b,
        viscosity_coeff_b=viscosity_coeff_b,
        specific_heat_coeff_b=specific_heat_coeff_b,
        conductivity_coeff_c=conductivity_coeff_c,
        viscosity_coeff_c=viscosity_coeff_c,
        specific_heat_coeff_c=specific_heat_coeff_c,
        specific_heat_ratio=specific_heat_ratio,
        molecular_weight=molecular_weight,
    )
    pure_gas.display_name = name
    gas_dict = pure_gas.to_dict()
    return {
        "object_dict": gas_dict,
        "target": gas_dict,
        "summary_view": {
            "type": gas_dict.get("type"),
            "identifier": gas_dict.get("identifier"),
            "display_name": gas_dict.get("display_name") or gas_dict.get("identifier"),
            "molecular_weight": gas_dict.get("molecular_weight"),
        },
        "report": make_report(status="ok", message=f"Created Fairyfly pure gas: {name}"),
    }


def create_fairyfly_gas(
    *,
    name: str,
    pure_gases: list[Any],
    gas_fractions: list[float],
) -> dict[str, Any]:
    """Create a Fairyfly Gas mixture payload."""
    gas = _coerce_gas(
        {"name": name, "pure_gases": pure_gases, "gas_fractions": gas_fractions}
    )
    gas_dict = gas.to_dict()
    return {
        "object_dict": gas_dict,
        "target": gas_dict,
        "summary_view": {
            "type": gas_dict.get("type"),
            "identifier": gas_dict.get("identifier"),
            "display_name": gas_dict.get("display_name") or gas_dict.get("identifier"),
            "gas_count": gas.gas_count,
            "gas_fractions": list(gas.gas_fractions),
        },
        "report": make_report(status="ok", message=f"Created Fairyfly gas: {name}"),
    }


def create_fairyfly_cavity_material(
    *,
    name: str,
    cavity_model: str = "CEN",
    gas: Any = None,
    gas_name: str | None = None,
    emissivity: float = 0.9,
    emissivity_back: float | None = None,
    rgb_color: list[int] | None = None,
) -> dict[str, Any]:
    """Create a Fairyfly CavityMaterial payload."""
    if cavity_model not in CavityMaterial.CAVITY_MODELS:
        raise ValueError(f"cavity_model must be one of {CavityMaterial.CAVITY_MODELS}.")
    resolved_gas = _coerce_gas(gas if gas is not None else gas_name)
    material = CavityMaterial(
        gas=resolved_gas,
        cavity_model=cavity_model,
        emissivity=emissivity,
        emissivity_back=emissivity_back,
    )
    material.display_name = name
    material.color = _color_from_rgb(rgb_color) or Color(200, 220, 240)
    material_dict = material.to_dict()
    return {
        "object_dict": material_dict,
        "target": material_dict,
        "summary_view": {
            "type": material_dict.get("type"),
            "identifier": material_dict.get("identifier"),
            "display_name": material_dict.get("display_name") or material_dict.get("identifier"),
            "cavity_model": material_dict.get("cavity_model"),
            "emissivity": material_dict.get("emissivity"),
            "color": material_dict.get("color"),
        },
        "report": make_report(status="ok", message=f"Created Fairyfly cavity material: {name}"),
    }


def _material_from_energy_spec(
    spec: dict[str, Any],
    *,
    garden_root: str | Path | None = None,
) -> SolidMaterial:
    from honeybee_energy.lib import materials as hbe_lib_materials
    from honeybee_energy.material.dictutil import dict_to_material as hbe_dict_to_material

    hb_mat: Any = None
    if isinstance(spec.get("energy_material"), dict):
        raw_hb = spec["energy_material"]
        if isinstance(raw_hb.get("object_dict"), dict):
            raw_hb = raw_hb["object_dict"]
        hb_mat = hbe_dict_to_material(raw_hb)
    elif spec.get("hb_material_target") is not None:
        if garden_root is None:
            raise ValueError("garden_root is required to load hb_material_target.")
        from garden.dragonfly_core.properties import load_garden_property_object

        hb_mat = load_garden_property_object(garden_root, spec["hb_material_target"])
    elif spec.get("hb_material_name"):
        mat_name = str(spec["hb_material_name"])
        try:
            hb_mat = hbe_lib_materials.opaque_material_by_identifier(mat_name)
        except Exception:
            hb_mat = hbe_lib_materials.window_material_by_identifier(mat_name)
    else:
        raise ValueError(
            "Energy material conversion requires energy_material, hb_material_name, or hb_material_target."
        )

    type_name = str(hb_mat.to_dict().get("type", ""))
    if "Window" in type_name:
        return SolidMaterial.from_energy_window_material_glazing(hb_mat)
    return SolidMaterial.from_energy_material(hb_mat)


def _coerce_xy_curve(value: Any) -> list[tuple[float, float]] | None:
    if value is None:
        return None
    return [(float(pt[0]), float(pt[1])) for pt in value]


def create_fairyfly_hygrothermal_material(
    *,
    name: str,
    conductivity: float,
    density: float | None = None,
    porosity: float | None = None,
    specific_heat: float | None = None,
    vapor_diffusion_resistance: float | None = None,
    moisture_storage_function: list[Any] | None = None,
    liquid_transport_suction: list[Any] | None = None,
    liquid_transport_redistribution: list[Any] | None = None,
    conductivity_moisture_dependent: list[Any] | None = None,
    conductivity_temperature_dependent: list[Any] | None = None,
    diffusion_moisture_dependent: list[Any] | None = None,
    enthalpy_temperature_dependent: list[Any] | None = None,
    reference_water_content: float | None = None,
    free_water_saturation: float | None = None,
    water_absorption_coefficient: float | None = None,
    drying_factor: float | None = None,
    roughness: str | None = None,
    conductivity_moisture_supplement: float | None = None,
    conductivity_temperature_supplement: float | None = None,
    conductivity_design_value: float | None = None,
    typical_built_in_moisture: float | None = None,
    default_thickness: float | None = None,
    material_information: str | None = None,
    emissivity: float = 0.9,
    emissivity_back: float | None = None,
    reflectance: float | None = None,
    transmittance: float | None = None,
    rgb_color: list[int] | None = None,
    identifier: str | None = None,
) -> dict[str, Any]:
    """Create a Fairyfly HygrothermalMaterial payload."""
    material = HygrothermalMaterial(
        conductivity=float(conductivity),
        density=density,
        porosity=porosity,
        specific_heat=specific_heat,
        vapor_diffusion_resistance=vapor_diffusion_resistance,
        moisture_storage_function=_coerce_xy_curve(moisture_storage_function),
        liquid_transport_suction=_coerce_xy_curve(liquid_transport_suction),
        liquid_transport_redistribution=_coerce_xy_curve(liquid_transport_redistribution),
        conductivity_moisture_dependent=_coerce_xy_curve(conductivity_moisture_dependent),
        conductivity_temperature_dependent=_coerce_xy_curve(conductivity_temperature_dependent),
        diffusion_moisture_dependent=_coerce_xy_curve(diffusion_moisture_dependent),
        enthalpy_temperature_dependent=_coerce_xy_curve(enthalpy_temperature_dependent),
        reference_water_content=reference_water_content,
        free_water_saturation=free_water_saturation,
        water_absorption_coefficient=water_absorption_coefficient,
        drying_factor=drying_factor,
        roughness=roughness,
        conductivity_moisture_supplement=conductivity_moisture_supplement,
        conductivity_temperature_supplement=conductivity_temperature_supplement,
        conductivity_design_value=conductivity_design_value,
        typical_built_in_moisture=typical_built_in_moisture,
        default_thickness=default_thickness,
        material_information=material_information,
        emissivity=float(emissivity),
        emissivity_back=emissivity_back,
        reflectance=reflectance,
        transmittance=transmittance,
        identifier=identifier,
    )
    material.display_name = name
    material.color = _color_from_rgb(rgb_color) or Color(140, 175, 200)
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
        "report": make_report(status="ok", message=f"Created Fairyfly hygrothermal material: {name}"),
    }


def coerce_fairyfly_material(
    material: Any,
    *,
    garden_root: str | Path | None = None,
) -> SolidMaterial | CavityMaterial | HygrothermalMaterial:
    """Coerce a library name, inline spec, HB-Energy material, or Fairyfly dict to a Material."""
    if isinstance(material, (SolidMaterial, CavityMaterial, HygrothermalMaterial)):
        return material
    if isinstance(material, str):
        try:
            return _ff_materials.solid_material_by_name(material)
        except Exception:
            return _ff_materials.cavity_material_by_name(material)
    if not isinstance(material, dict):
        raise ValueError("Fairyfly material must be a material name string or dictionary.")
    if isinstance(material.get("object_dict"), dict):
        material = material["object_dict"]
    if material.get("type") and material.get("identifier"):
        return dict_to_material(material)
    if (
        material.get("energy_material") is not None
        or material.get("hb_material_name") is not None
        or material.get("hb_material_target") is not None
    ):
        mat = _material_from_energy_spec(material, garden_root=garden_root)
    elif material.get("material_name"):
        mat_name = str(material["material_name"])
        try:
            mat = _ff_materials.solid_material_by_name(mat_name)
        except Exception:
            mat = _ff_materials.cavity_material_by_name(mat_name)
    elif "cavity_model" in material or material.get("kind") == "cavity":
        created = create_fairyfly_cavity_material(
            name=str(material.get("name") or material.get("display_name") or "CavityMaterial"),
            cavity_model=str(material.get("cavity_model", "CEN")),
            gas=material.get("gas"),
            gas_name=material.get("gas_name"),
            emissivity=float(material.get("emissivity", 0.9)),
            emissivity_back=(
                float(material["emissivity_back"])
                if material.get("emissivity_back") is not None
                else None
            ),
            rgb_color=material.get("rgb_color"),
        )
        return dict_to_material(created["object_dict"])
    elif "conductivity" in material and (
        material.get("kind") == "hygrothermal"
        or material.get("type") == "HygrothermalMaterial"
        or any(material.get(k) is not None for k in _HYGROTHERMAL_SPEC_KEYS)
    ):
        created = create_fairyfly_hygrothermal_material(
            name=str(material.get("name") or material.get("display_name") or "HygrothermalMaterial"),
            conductivity=float(material["conductivity"]),
            density=float(material["density"]) if material.get("density") is not None else None,
            porosity=float(material["porosity"]) if material.get("porosity") is not None else None,
            specific_heat=(
                float(material["specific_heat"])
                if material.get("specific_heat") is not None
                else None
            ),
            vapor_diffusion_resistance=(
                float(material["vapor_diffusion_resistance"])
                if material.get("vapor_diffusion_resistance") is not None
                else None
            ),
            moisture_storage_function=material.get("moisture_storage_function"),
            liquid_transport_suction=material.get("liquid_transport_suction"),
            liquid_transport_redistribution=material.get("liquid_transport_redistribution"),
            conductivity_moisture_dependent=material.get("conductivity_moisture_dependent"),
            conductivity_temperature_dependent=material.get("conductivity_temperature_dependent"),
            diffusion_moisture_dependent=material.get("diffusion_moisture_dependent"),
            enthalpy_temperature_dependent=material.get("enthalpy_temperature_dependent"),
            reference_water_content=material.get("reference_water_content"),
            free_water_saturation=material.get("free_water_saturation"),
            water_absorption_coefficient=material.get("water_absorption_coefficient"),
            drying_factor=material.get("drying_factor"),
            roughness=material.get("roughness"),
            conductivity_moisture_supplement=material.get("conductivity_moisture_supplement"),
            conductivity_temperature_supplement=material.get("conductivity_temperature_supplement"),
            conductivity_design_value=material.get("conductivity_design_value"),
            typical_built_in_moisture=material.get("typical_built_in_moisture"),
            default_thickness=material.get("default_thickness"),
            material_information=material.get("material_information"),
            emissivity=float(material.get("emissivity", 0.9)),
            emissivity_back=(
                float(material["emissivity_back"])
                if material.get("emissivity_back") is not None
                else None
            ),
            reflectance=(
                float(material["reflectance"]) if material.get("reflectance") is not None else None
            ),
            transmittance=(
                float(material["transmittance"])
                if material.get("transmittance") is not None
                else None
            ),
            rgb_color=material.get("rgb_color"),
            identifier=material.get("identifier"),
        )
        return dict_to_material(created["object_dict"])
    elif "conductivity" in material:
        created = create_fairyfly_solid_material(
            name=str(material.get("name") or material.get("display_name") or "SolidMaterial"),
            conductivity=float(material["conductivity"]),
            emissivity=float(material.get("emissivity", 0.9)),
            emissivity_back=(
                float(material["emissivity_back"])
                if material.get("emissivity_back") is not None
                else None
            ),
            density=float(material["density"]) if material.get("density") is not None else None,
            porosity=float(material["porosity"]) if material.get("porosity") is not None else None,
            specific_heat=(
                float(material["specific_heat"])
                if material.get("specific_heat") is not None
                else None
            ),
            vapor_diffusion_resistance=(
                float(material["vapor_diffusion_resistance"])
                if material.get("vapor_diffusion_resistance") is not None
                else None
            ),
            reflectance=(
                float(material["reflectance"]) if material.get("reflectance") is not None else None
            ),
            transmittance=(
                float(material["transmittance"])
                if material.get("transmittance") is not None
                else None
            ),
            rgb_color=material.get("rgb_color"),
        )
        return dict_to_material(created["object_dict"])
    else:
        raise ValueError(
            "Fairyfly material dictionary requires type+identifier, material_name, "
            "conductivity (SolidMaterial/HygrothermalMaterial), cavity_model (CavityMaterial), "
            "or HB-Energy source."
        )

    if material.get("name") or material.get("display_name"):
        mat = mat.duplicate()
        mat.display_name = str(material.get("display_name") or material["name"])
    color = _color_from_rgb(material.get("rgb_color"))
    if color is not None:
        mat = mat.duplicate()
        mat.color = color
    return mat


_CONDITION_ALIASES = {
    "exterior": _ff_conditions.exterior,
    "generic exterior": _ff_conditions.exterior,
    "interior": _ff_conditions.interior,
    "generic interior": _ff_conditions.interior,
    "adiabatic": _ff_conditions.adiabatic,
    "frame cavity": _ff_conditions.frame_cavity,
    "frame cavity surface": _ff_conditions.frame_cavity,
}


def _normalize_transient_timesteps(raw_timesteps: Any) -> Any:
    if raw_timesteps is None:
        return None
    if isinstance(raw_timesteps, dict):
        return {
            int(step): {str(k): v for k, v in values.items()}
            for step, values in raw_timesteps.items()
        }
    if isinstance(raw_timesteps, (list, tuple)):
        return [{str(k): v for k, v in item.items()} for item in raw_timesteps]
    return raw_timesteps


def _normalize_therm_condition_identifier(raw_id: Any) -> tuple[str | None, str | None]:
    """Normalize a THERM condition identifier to an 8-4-4-4-12 UUID string.

    Non-UUID strings are deterministically converted via uuid5 while returning the
    original human-readable label so callers can preserve it as display_name.
    """
    if raw_id is None:
        return None, None
    raw = str(raw_id).strip()
    if not raw:
        return None, None
    try:
        uuid.UUID(raw)
        return raw, None
    except ValueError:
        converted = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"lbt-mcp:therm-condition:{raw}"))
        return converted, raw


def coerce_fairyfly_condition(spec: dict[str, Any] | SteadyState | Transient) -> SteadyState | Transient:
    """Build or lookup a SteadyState or Transient boundary condition from a spec dict."""
    if isinstance(spec, (SteadyState, Transient)):
        return spec
    if not isinstance(spec, dict):
        raise ValueError(
            "Fairyfly boundary condition must be a dictionary, SteadyState, or Transient object."
        )
    if "condition" in spec and spec["condition"] is not None:
        raw_cond_field = spec["condition"]
        if isinstance(raw_cond_field, (SteadyState, Transient)):
            return raw_cond_field
        if isinstance(raw_cond_field, str):
            forwarded = {k: v for k, v in spec.items() if k != "condition"}
            forwarded["condition_name"] = raw_cond_field
            return coerce_fairyfly_condition(forwarded)
        if not isinstance(raw_cond_field, dict):
            raise ValueError(
                "Boundary 'condition' field must be a condition dictionary, condition_name string, "
                "or SteadyState/Transient object."
            )
        cond_raw = dict(raw_cond_field)
        if isinstance(cond_raw.get("object_dict"), dict):
            cond_raw = dict(cond_raw["object_dict"])
        cond_type = cond_raw.get("type")
        if cond_type == "SteadyState":
            missing_keys = [
                key
                for key in ("temperature", "film_coefficient")
                if key not in cond_raw or cond_raw.get(key) is None
            ]
            if missing_keys:
                raise ValueError(
                    "SteadyState condition dictionary is missing required field(s): "
                    f"{', '.join(missing_keys)}. Accepted fields: temperature, film_coefficient, "
                    "identifier, display_name, emissivity, radiant_temperature, heat_flux, "
                    "relative_humidity."
                )
            if "identifier" not in cond_raw or cond_raw.get("identifier") is None or not str(
                cond_raw.get("identifier")
            ).strip():
                cond_raw["identifier"] = str(uuid.uuid4())
                inferred_display = None
            else:
                norm_id, inferred_display = _normalize_therm_condition_identifier(
                    cond_raw["identifier"]
                )
                cond_raw["identifier"] = norm_id or str(uuid.uuid4())
            if not cond_raw.get("display_name"):
                if cond_raw.get("name"):
                    cond_raw["display_name"] = str(cond_raw["name"])
                elif inferred_display:
                    cond_raw["display_name"] = inferred_display
            return dict_to_condition(cond_raw)
        if cond_type == "Transient":
            if isinstance(cond_raw.get("timesteps"), dict):
                cond_raw["timesteps"] = {
                    str(int(k)): v for k, v in cond_raw["timesteps"].items()
                }
            norm_id, inferred_display = _normalize_therm_condition_identifier(
                cond_raw.get("identifier")
            )
            if norm_id is not None:
                cond_raw["identifier"] = norm_id
            if not cond_raw.get("display_name"):
                if cond_raw.get("name"):
                    cond_raw["display_name"] = str(cond_raw["name"])
                elif inferred_display:
                    cond_raw["display_name"] = inferred_display
            return dict_to_condition(cond_raw)
        if cond_type is not None:
            raise ValueError(
                f"Unsupported THERM condition type {cond_type!r}. "
                "Accepted types: 'SteadyState', 'Transient'."
            )
        return coerce_fairyfly_condition(cond_raw)

    is_transient = (
        str(spec.get("kind") or spec.get("condition_type") or "").strip().lower() == "transient"
        or spec.get("type") == "Transient"
        or any(spec.get(key) is not None for key in _TRANSIENT_CONDITION_KEYS)
    )
    if is_transient:
        bc_type = str(spec.get("bc_type", "Transient"))
        bc_model = str(spec.get("bc_model", "Neumann"))
        use_heat_flux = bool(spec.get("use_heat_flux", False))
        use_temperature = bool(spec.get("use_temperature", False))
        use_humidity = bool(spec.get("use_humidity", False))
        humidity_only = use_humidity and bc_model == "Dirichlet" and not use_temperature
        if "convection_model" in spec:
            convection_model = spec.get("convection_model")
        elif use_heat_flux or use_temperature or humidity_only:
            convection_model = None
        else:
            convection_model = "Fixed Convection Coefficient"

        timesteps = _normalize_transient_timesteps(spec.get("timesteps"))
        if bc_type == "Transient" and timesteps is None:
            # Synthesize a single-step schedule from constant inputs when omitted.
            step: dict[str, Any] = {}
            if spec.get("temperature") is not None:
                step["temperature"] = float(spec["temperature"])
            if spec.get("relative_humidity") is not None:
                step["humidity"] = float(spec["relative_humidity"])
            elif spec.get("humidity") is not None:
                step["humidity"] = float(spec["humidity"])
            if spec.get("film_coefficient") is not None:
                step["film_coefficient"] = float(spec["film_coefficient"])
            if spec.get("heat_flux") is not None and use_heat_flux:
                step["heat_flux"] = float(spec["heat_flux"])
            if spec.get("imposed_temperature") is not None and use_temperature:
                step["surface_temperature"] = float(spec["imposed_temperature"])
            if spec.get("imposed_humidity") is not None and use_humidity:
                step["humidity"] = float(spec["imposed_humidity"])
            if step:
                timesteps = {1: step}

        norm_id, inferred_display = _normalize_therm_condition_identifier(spec.get("identifier"))
        kwargs: dict[str, Any] = {
            "bc_type": bc_type,
            "bc_model": bc_model,
            "convection_model": convection_model,
            "radiation_model": spec.get("radiation_model"),
            "timesteps": timesteps,
            "temperature": spec.get("temperature"),
            "film_coefficient": spec.get("film_coefficient"),
            "wind_speed": spec.get("wind_speed"),
            "wind_direction": spec.get("wind_direction"),
            "use_heat_flux": use_heat_flux,
            "heat_flux": spec.get("heat_flux"),
            "use_temperature": use_temperature,
            "imposed_temperature": spec.get("imposed_temperature"),
            "use_humidity": use_humidity,
            "imposed_humidity": spec.get("imposed_humidity"),
            "radiation_temperature": spec.get("radiation_temperature"),
            "surface_emissivity": spec.get("surface_emissivity"),
            "view_factor": spec.get("view_factor"),
            "hr": spec.get("hr"),
            "solar_radiation": spec.get("solar_radiation"),
            "absorptance": spec.get("absorptance"),
            "timestep_file_name": spec.get("timestep_file_name"),
            "surface_tilt": spec.get("surface_tilt"),
            "surface_length": spec.get("surface_length"),
            "building_width": spec.get("building_width"),
            "building_height": spec.get("building_height"),
            "identifier": norm_id,
        }
        condition = Transient(**kwargs)
        condition.display_name = str(
            spec.get("display_name")
            or inferred_display
            or spec.get("name")
            or f"Transient_{condition.identifier[:8]}"
        )
        condition.color = _color_from_rgb(spec.get("rgb_color")) or Color(50, 110, 200)
        return condition

    if spec.get("condition_name"):
        cond_name = str(spec["condition_name"])
        alias = _CONDITION_ALIASES.get(cond_name.strip().lower().replace("_", " "))
        condition = (
            alias.duplicate()
            if alias is not None
            else _ff_conditions.condition_by_name(cond_name).duplicate()
        )
        if spec.get("name") or spec.get("display_name"):
            condition.display_name = str(spec.get("display_name") or spec["name"])
        color = _color_from_rgb(spec.get("rgb_color"))
        if color is not None:
            condition.color = color
        return condition

    missing_steady = [
        key for key in ("temperature", "film_coefficient") if key not in spec or spec.get(key) is None
    ]
    if missing_steady:
        raise ValueError(
            "Fairyfly boundary condition is missing required field(s): "
            f"{', '.join(missing_steady)}. Accepted boundary condition fields: "
            "(temperature + film_coefficient), condition_name, condition dictionary, "
            "or kind='transient' with transient fields."
        )
    norm_id, inferred_display = _normalize_therm_condition_identifier(spec.get("identifier"))
    condition = SteadyState(
        temperature=float(spec["temperature"]),
        film_coefficient=float(spec["film_coefficient"]),
        emissivity=float(spec.get("emissivity", 1.0)),
        radiant_temperature=spec.get("radiant_temperature"),
        heat_flux=float(spec.get("heat_flux", 0)),
        relative_humidity=float(spec.get("relative_humidity", 0.5)),
        identifier=norm_id,
    )
    condition.display_name = str(
        spec.get("display_name")
        or inferred_display
        or spec.get("name")
        or f"{condition.temperature}C boundary"
    )
    condition.color = _color_from_rgb(spec.get("rgb_color")) or Color(50, 110, 200)
    return condition


def import_fairyfly_therm_xml(
    *,
    garden_root: str,
    xml_path: str,
    include_objects: bool = True,
) -> dict[str, Any]:
    """Import SolidMaterial, CavityMaterial, Gas, and SteadyState objects from THERM XML."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    candidate = Path(xml_path).expanduser()
    resolved_path = (
        candidate.resolve()
        if candidate.is_absolute()
        else resolve_existing_garden_path(garden_root_path, xml_path, kind="file", label="THERM XML")
    )
    if not resolved_path.is_file():
        raise FileNotFoundError(f"THERM XML file not found: {xml_path}")

    gas_map: dict[str, Gas] = {name: _ff_gases.gas_by_name(name) for name in _ff_gases.GASES}
    extracted_gases: list[Gas] = []
    extracted_pure_gases: list[PureGas] = []
    try:
        raw_gases, raw_pure_gases = Gas.extract_all_from_xml_file(str(resolved_path))
        for gas in raw_gases or ():
            extracted_gases.append(gas)
            gas_map[gas.identifier] = gas
            if getattr(gas, "display_name", None):
                gas_map[gas.display_name] = gas
        for pgas in raw_pure_gases or ():
            extracted_pure_gases.append(pgas)
    except Exception:
        pass

    solids_raw: list[Any] = []
    cavities_raw: list[Any] = []
    try:
        solids_raw, cavities_raw = extract_all_materials_from_xml_file(
            str(resolved_path), gases=gas_map
        )
    except Exception:
        tree = ET.parse(resolved_path)
        for mat_obj in tree.getroot():
            if mat_obj.find("Solid") is not None:
                try:
                    solids_raw.append(SolidMaterial.from_therm_xml(mat_obj))
                except Exception:
                    pass
            elif mat_obj.find("Cavity") is not None:
                try:
                    cavities_raw.append(CavityMaterial.from_therm_xml(mat_obj, gas_map))
                except Exception:
                    pass

    def _dedupe(items: list[Any]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for item in items:
            ident = getattr(item, "identifier", None)
            key = str(ident) if ident else json.dumps(item.to_dict(), sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            out.append(item.to_dict())
        return out

    conditions_raw: list[Any] = []
    try:
        conditions_raw = SteadyState.extract_all_from_xml_file(str(resolved_path))
    except Exception:
        pass

    solid_dicts = _dedupe(solids_raw)
    cavity_dicts = _dedupe(cavities_raw)
    gas_dicts = _dedupe(extracted_gases)
    pure_gas_dicts = _dedupe(extracted_pure_gases)
    condition_dicts = _dedupe(conditions_raw)

    result: dict[str, Any] = {
        "summary_view": {
            "garden_target": manifest.target(),
            "xml_path": str(resolved_path),
            "solid_material_count": len(solid_dicts),
            "cavity_material_count": len(cavity_dicts),
            "gas_count": len(gas_dicts),
            "pure_gas_count": len(pure_gas_dicts),
            "condition_count": len(condition_dicts),
        },
        "report": make_report(
            status="ok",
            message=(
                f"Imported {len(solid_dicts)} solid(s), {len(cavity_dicts)} cavity material(s), "
                f"{len(gas_dicts)} gas(es), and {len(condition_dicts)} condition(s) from THERM XML."
            ),
        ),
    }
    if include_objects:
        result["solid_materials"] = solid_dicts
        result["cavity_materials"] = cavity_dicts
        result["gases"] = gas_dicts
        result["pure_gases"] = pure_gas_dicts
        result["conditions"] = condition_dicts
    return result


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


def _unique_material_for_file(model: Model) -> None:
    """Keep Model shapes valid after in-place edits."""
    _ = model


def create_fairyfly_model(
    *,
    garden_root: str,
    identifier: str,
    units: str = "Millimeters",
    tolerance: float | None = None,
    angle_tolerance: float = 1.0,
    display_name: str | None = None,
    plane: Plane | dict[str, Any] | None = None,
    layers: list[dict[str, Any]] | None = None,
    layer_height: float = 200.0,
    source_file: str | None = None,
    file_format: str = "auto",
    save_back: bool = True,
    set_base: bool = True,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create a Fairyfly Model (empty, from layers, or imported from FFJSON/FFpkl)."""
    garden_root_path = require_garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)

    if source_file is not None:
        candidate = Path(source_file).expanduser()
        resolved_source = (
            candidate.resolve()
            if candidate.is_absolute()
            else resolve_existing_garden_path(
                garden_root_path, source_file, kind="file", label="Fairyfly model file"
            )
        )
        if not resolved_source.is_file():
            raise FileNotFoundError(f"Fairyfly source file not found: {source_file}")
        fmt = file_format.strip().lower()
        if fmt == "ffjson":
            model = Model.from_ffjson(str(resolved_source))
        elif fmt == "ffpkl":
            model = Model.from_ffpkl(str(resolved_source))
        elif fmt == "auto":
            model = Model.from_file(str(resolved_source))
        else:
            raise ValueError("file_format must be 'auto', 'ffjson', or 'ffpkl'.")
    elif layers is not None:
        if not isinstance(layers, list) or not layers:
            raise ValueError("layers must be a non-empty list of layer specs with thickness and material.")
        thicknesses: list[float] = []
        for idx, layer in enumerate(layers):
            if not isinstance(layer, dict) or layer.get("thickness") is None:
                raise ValueError(f"Layer entry at index {idx} must include thickness.")
            thicknesses.append(float(layer["thickness"]))
        base_plane = _plane_from_spec(plane)
        model = Model.from_layers(
            thicknesses,
            height=float(layer_height),
            base_plane=base_plane,
            units=units,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
        )
        for shape, layer in zip(model.shapes, layers):
            if layer.get("name") or layer.get("display_name"):
                shape.display_name = str(layer.get("display_name") or layer["name"])
            if layer.get("material") is not None:
                mat = coerce_fairyfly_material(layer["material"], garden_root=garden_root_path)
                color = _color_from_rgb(layer.get("rgb_color"))
                if color is not None:
                    mat = mat.duplicate()
                    mat.color = color
                shape.properties.therm.material = mat
    else:
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


def export_fairyfly_model_file(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    file_format: str = "ffjson",
    output_path: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Export a Garden Fairyfly model to FFJSON, FFpkl, or THERM XML."""
    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_target = resolve_model_target(garden_root_path, model_target)
    model = load_fairyfly_model(garden_root_path, resolved_target)
    fmt = file_format.strip().lower().replace("-", "_")
    ext_map = {"ffjson": ".ffjson", "ffpkl": ".ffpkl", "therm_xml": ".xml", "xml": ".xml"}
    if fmt not in ext_map:
        raise ValueError("file_format must be 'ffjson', 'ffpkl', or 'therm_xml'.")

    stem = slugify_name(name or str(resolved_target.get("model_identifier") or "model"))
    if output_path:
        dest = resolve_contained_path(garden_root_path, output_path, label="export output_path")
    else:
        dest = (garden_root_path / "artifacts" / "fairyfly" / "exports" / f"{stem}{ext_map[fmt]}").resolve()
        dest.relative_to(garden_root_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "ffjson":
        written = Path(model.to_ffjson(name=dest.stem, folder=str(dest.parent)))
        if written.resolve() != dest:
            dest.write_bytes(written.read_bytes())
    elif fmt == "ffpkl":
        written = Path(model.to_ffpkl(name=dest.stem, folder=str(dest.parent)))
        if written.resolve() != dest:
            dest.write_bytes(written.read_bytes())
    else:
        xml_str = model.to_therm_xml()
        dest.write_text(str(xml_str), encoding="utf-8")

    rel_path = to_posix_relative(dest, garden_root_path)
    source = {"model_target": resolved_target, "file_format": fmt}
    artifact = manifest.upsert_artifact(
        {
            "artifact_type": f"fairyfly_{fmt}",
            "name": f"{stem}_{fmt}",
            "path": rel_path,
            "source": source,
        }
    )
    manifest.write(garden_root_path)
    return {
        "target": resolved_target,
        "model_target": resolved_target,
        "artifact": artifact,
        "artifact_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=f"fairyfly_{fmt}",
            artifact_path=rel_path,
            absolute_path=str(dest),
            source=source,
        ),
        "summary_view": {
            "garden_target": manifest.target(),
            "model_target": resolved_target,
            "file_format": fmt,
            "path": rel_path,
            "object_counts": _model_counts(model),
        },
        "report": make_report(status="ok", message=f"Exported Fairyfly model to {rel_path}."),
    }


def _find_model_entity(entities: Iterable[Any], key: str, label: str) -> Any:
    items = list(entities)
    by_id = [item for item in items if getattr(item, "identifier", None) == key]
    if len(by_id) == 1:
        return by_id[0]
    by_name = [item for item in items if getattr(item, "display_name", None) == key]
    if len(by_name) == 1:
        return by_name[0]
    if len(by_name) > 1:
        raise ValueError(f"Multiple {label} entries match display_name {key!r}; pass identifier.")
    raise KeyError(f"Fairyfly {label} not found: {key!r}.")


def add_fairyfly_shape_to_model(
    *,
    garden_root: str,
    vertices_2d: list[list[float]],
    material: Any,
    model_target: dict[str, Any] | None = None,
    name: str | None = None,
    holes_2d: list[list[list[float]]] | None = None,
    rgb_color: list[int] | None = None,
    tolerance: float | None = None,
    plane: Plane | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add a 2D Fairyfly Shape to a Garden-backed model."""
    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_fairyfly_model(garden_root_path, resolved_model_target)
    effective_plane = _plane_from_spec(plane) or (
        getattr(model.properties.therm, "therm_plane", None) if model.shapes else None
    )
    shape = Shape(
        face3d_from_vertices_2d(
            vertices_2d, holes_2d=holes_2d, tolerance=tolerance, plane=effective_plane
        )
    )
    if name:
        shape.display_name = name
    material_obj = coerce_fairyfly_material(material, garden_root=garden_root_path)
    color = _color_from_rgb(rgb_color)
    if color is not None:
        material_obj = material_obj.duplicate()
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
                "identifier": shape.identifier,
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
    temperature: float | None = None,
    film_coefficient: float | None = None,
    model_target: dict[str, Any] | None = None,
    name: str | None = None,
    emissivity: float = 1.0,
    radiant_temperature: float | None = None,
    heat_flux: float = 0,
    relative_humidity: float = 0.5,
    u_factor_tag: str | None = None,
    rgb_color: list[int] | None = None,
    condition_name: str | None = None,
    condition: dict[str, Any] | None = None,
    plane: Plane | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add a 2D Fairyfly Boundary to a Garden-backed model."""
    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_fairyfly_model(garden_root_path, resolved_model_target)
    effective_plane = _plane_from_spec(plane) or (
        getattr(model.properties.therm, "therm_plane", None) if model.shapes else None
    )
    boundary = Boundary(
        line_segments3d_from_segments_2d(line_segments_2d, plane=effective_plane)
    )
    if name:
        boundary.display_name = name
    cond_obj = coerce_fairyfly_condition(
        {
            "temperature": temperature,
            "film_coefficient": film_coefficient,
            "emissivity": emissivity,
            "radiant_temperature": radiant_temperature,
            "heat_flux": heat_flux,
            "relative_humidity": relative_humidity,
            "condition_name": condition_name,
            "condition": condition,
            "name": name,
            "rgb_color": rgb_color,
        }
    )
    boundary.properties.therm.condition = cond_obj
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
                "identifier": boundary.identifier,
                "display_name": boundary.display_name,
                "length": boundary.length,
                "condition": cond_obj.display_name,
                "u_factor_tag": u_factor_tag,
            }
        },
    )


def edit_fairyfly_model_entities(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    shapes: list[dict[str, Any]] | None = None,
    boundaries: list[dict[str, Any]] | None = None,
    edit_shapes: list[dict[str, Any]] | None = None,
    edit_boundaries: list[dict[str, Any]] | None = None,
    remove_shape_identifiers: list[str] | None = None,
    remove_boundary_identifiers: list[str] | None = None,
    intersect_adjacency: bool | dict[str, Any] = False,
    transforms: list[dict[str, Any]] | None = None,
    convert_units: str | None = None,
    plane: Plane | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Perform batch authoring/editing/geometry operations on a Garden Fairyfly model."""
    garden_root_path = require_garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_fairyfly_model(garden_root_path, resolved_model_target)
    default_plane = _plane_from_spec(plane) or (
        getattr(model.properties.therm, "therm_plane", None) if model.shapes else None
    )

    removed_shape_ids: list[str] = []
    if remove_shape_identifiers:
        targets = [_find_model_entity(model.shapes, key, "shape").identifier for key in remove_shape_identifiers]
        model.remove_shapes(targets)
        removed_shape_ids.extend(targets)

    removed_boundary_ids: list[str] = []
    if remove_boundary_identifiers:
        targets = [
            _find_model_entity(model.boundaries, key, "boundary").identifier
            for key in remove_boundary_identifiers
        ]
        model.remove_boundaries(targets)
        removed_boundary_ids.extend(targets)

    added_shapes: list[dict[str, Any]] = []
    for idx, spec in enumerate(shapes or []):
        if not isinstance(spec, dict):
            raise ValueError(f"Shape entry at index {idx} must be a dictionary.")
        if "vertices_2d" not in spec or spec.get("vertices_2d") is None:
            raise ValueError(
                f"Shape entry at index {idx} is missing required 'vertices_2d'. "
                "Accepted shape fields: vertices_2d (required), material (required), "
                "plus optional name/display_name, holes_2d, plane, tolerance, rgb_color."
            )
        if "material" not in spec or spec.get("material") is None:
            raise ValueError(
                f"Shape entry at index {idx} is missing required 'material'. "
                "Accepted material specs: Fairyfly material dict, material_name, conductivity "
                "(SolidMaterial/HygrothermalMaterial), cavity_model (CavityMaterial), or HB-Energy "
                "source. Accepted shape fields: vertices_2d, material, name/display_name, holes_2d, "
                "plane, tolerance, rgb_color."
            )
        shape_plane = _plane_from_spec(spec.get("plane")) or default_plane
        shape = Shape(
            face3d_from_vertices_2d(
                spec["vertices_2d"],
                holes_2d=spec.get("holes_2d"),
                tolerance=spec.get("tolerance"),
                plane=shape_plane,
            )
        )
        if spec.get("name") or spec.get("display_name"):
            shape.display_name = str(spec.get("display_name") or spec["name"])
        mat = coerce_fairyfly_material(spec["material"], garden_root=garden_root_path)
        color = _color_from_rgb(spec.get("rgb_color"))
        if color is not None:
            mat = mat.duplicate()
            mat.color = color
        shape.properties.therm.material = mat
        model.add_shape(shape)
        added_shapes.append(
            {
                "identifier": shape.identifier,
                "display_name": shape.display_name,
                "area": shape.area,
                "material": mat.display_name,
            }
        )

    added_boundaries: list[dict[str, Any]] = []
    for idx, spec in enumerate(boundaries or []):
        if not isinstance(spec, dict):
            raise ValueError(f"Boundary entry at index {idx} must be a dictionary.")
        if "line_segments_2d" not in spec or spec.get("line_segments_2d") is None:
            raise ValueError(
                f"Boundary entry at index {idx} is missing required 'line_segments_2d'. "
                "Accepted boundary fields: line_segments_2d (required), condition "
                "(temperature + film_coefficient, condition_name, condition dict, or "
                "kind='transient'), plus optional name/display_name, u_factor_tag, plane, rgb_color."
            )
        b_plane = _plane_from_spec(spec.get("plane")) or default_plane
        boundary = Boundary(line_segments3d_from_segments_2d(spec["line_segments_2d"], plane=b_plane))
        if spec.get("name") or spec.get("display_name"):
            boundary.display_name = str(spec.get("display_name") or spec["name"])
        cond = coerce_fairyfly_condition(spec)
        boundary.properties.therm.condition = cond
        boundary.properties.therm.u_factor_tag = spec.get("u_factor_tag")
        model.add_boundary(boundary)
        added_boundaries.append(
            {
                "identifier": boundary.identifier,
                "display_name": boundary.display_name,
                "length": boundary.length,
                "condition": cond.display_name,
                "u_factor_tag": spec.get("u_factor_tag"),
            }
        )

    edited_shapes: list[dict[str, Any]] = []
    for idx, spec in enumerate(edit_shapes or []):
        if not isinstance(spec, dict):
            raise ValueError(f"edit_shapes entry at index {idx} must be a dictionary.")
        key = str(spec.get("identifier") or spec.get("name") or "")
        if not key:
            raise ValueError(
                f"edit_shapes entry at index {idx} requires 'identifier' or 'name'. "
                "Accepted fields: identifier/name, new_name/display_name, material, vertices_2d, "
                "holes_2d, plane, tolerance, rgb_color."
            )
        shape = _find_model_entity(model.shapes, key, "shape")
        if spec.get("vertices_2d") is not None:
            new_plane = _plane_from_spec(spec.get("plane")) or default_plane
            new_shape = Shape(
                face3d_from_vertices_2d(
                    spec["vertices_2d"],
                    holes_2d=spec.get("holes_2d"),
                    tolerance=spec.get("tolerance"),
                    plane=new_plane,
                )
            )
            new_shape.display_name = shape.display_name
            new_shape.properties.therm.material = shape.properties.therm.material
            model.remove_shapes([shape.identifier])
            model.add_shape(new_shape)
            shape = new_shape
        if spec.get("new_name") or spec.get("display_name"):
            shape.display_name = str(spec.get("display_name") or spec["new_name"])
        if spec.get("material") is not None:
            mat = coerce_fairyfly_material(spec["material"], garden_root=garden_root_path)
            shape.properties.therm.material = mat
        color = _color_from_rgb(spec.get("rgb_color"))
        if color is not None and shape.properties.therm.material is not None:
            mat = shape.properties.therm.material.duplicate()
            mat.color = color
            shape.properties.therm.material = mat
        edited_shapes.append(
            {
                "identifier": shape.identifier,
                "display_name": shape.display_name,
                "area": shape.area,
                "material": getattr(shape.properties.therm.material, "display_name", None),
            }
        )

    edited_boundaries: list[dict[str, Any]] = []
    for idx, spec in enumerate(edit_boundaries or []):
        if not isinstance(spec, dict):
            raise ValueError(f"edit_boundaries entry at index {idx} must be a dictionary.")
        key = str(spec.get("identifier") or spec.get("name") or "")
        if not key:
            raise ValueError(
                f"edit_boundaries entry at index {idx} requires 'identifier' or 'name'. "
                "Accepted fields: identifier/name, new_name/display_name, line_segments_2d, "
                "condition_name, condition, temperature, film_coefficient, u_factor_tag, plane, rgb_color."
            )
        boundary = _find_model_entity(model.boundaries, key, "boundary")
        if spec.get("line_segments_2d") is not None:
            new_plane = _plane_from_spec(spec.get("plane")) or default_plane
            new_b = Boundary(line_segments3d_from_segments_2d(spec["line_segments_2d"], plane=new_plane))
            new_b.display_name = boundary.display_name
            new_b.properties.therm.condition = boundary.properties.therm.condition
            new_b.properties.therm.u_factor_tag = boundary.properties.therm.u_factor_tag
            model.remove_boundaries([boundary.identifier])
            model.add_boundary(new_b)
            boundary = new_b
        if spec.get("new_name") or spec.get("display_name"):
            boundary.display_name = str(spec.get("display_name") or spec["new_name"])
        if any(
            k in spec
            for k in (
                "condition",
                "condition_name",
                "temperature",
                "film_coefficient",
                "kind",
                "condition_type",
                "bc_type",
                "bc_model",
                "convection_model",
                "radiation_model",
                "timesteps",
                "use_heat_flux",
                "use_temperature",
                "use_humidity",
                "imposed_temperature",
                "imposed_humidity",
            )
        ):
            existing = boundary.properties.therm.condition
            has_transient = (
                any(k in spec for k in _TRANSIENT_CONDITION_KEYS)
                or spec.get("kind") == "transient"
                or isinstance(existing, Transient) and spec.get("condition_name") is None and spec.get("condition") is None
            )
            if has_transient and not isinstance(spec.get("condition"), dict) and not spec.get("condition_name"):
                merged = dict(spec)
                merged.pop("identifier", None)
                if "name" not in merged and "display_name" not in merged:
                    merged["display_name"] = boundary.display_name
                if isinstance(existing, Transient):
                    base_dict = existing.to_dict()
                    base_dict.pop("identifier", None)
                    for k, v in base_dict.items():
                        if k != "type":
                            merged.setdefault(k, v)
                boundary.properties.therm.condition = coerce_fairyfly_condition(merged)
            else:
                merged = {
                    "temperature": spec.get("temperature", getattr(existing, "temperature", None)),
                    "film_coefficient": spec.get(
                        "film_coefficient", getattr(existing, "film_coefficient", None)
                    ),
                    "emissivity": spec.get("emissivity", getattr(existing, "emissivity", 1.0)),
                    "radiant_temperature": spec.get(
                        "radiant_temperature", getattr(existing, "radiant_temperature", None)
                    ),
                    "heat_flux": spec.get("heat_flux", getattr(existing, "heat_flux", 0)),
                    "relative_humidity": spec.get(
                        "relative_humidity", getattr(existing, "relative_humidity", 0.5)
                    ),
                    "condition_name": spec.get("condition_name"),
                    "condition": spec.get("condition"),
                    "name": spec.get("new_name") or spec.get("display_name") or boundary.display_name,
                    "rgb_color": spec.get("rgb_color"),
                }
                boundary.properties.therm.condition = coerce_fairyfly_condition(merged)
        elif spec.get("rgb_color") is not None and boundary.properties.therm.condition is not None:
            cond = boundary.properties.therm.condition.duplicate()
            cond.color = _color_from_rgb(spec["rgb_color"])
            boundary.properties.therm.condition = cond
        if "u_factor_tag" in spec:
            boundary.properties.therm.u_factor_tag = spec["u_factor_tag"]
        edited_boundaries.append(
            {
                "identifier": boundary.identifier,
                "display_name": boundary.display_name,
                "length": boundary.length,
                "u_factor_tag": boundary.properties.therm.u_factor_tag,
            }
        )

    intersected = False
    if intersect_adjacency:
        if isinstance(intersect_adjacency, dict):
            adj_tol = float(intersect_adjacency.get("tolerance", model.tolerance or 0.01))
            adj_plane = _plane_from_spec(intersect_adjacency.get("plane")) or default_plane
        else:
            adj_tol = float(model.tolerance or 0.01)
            adj_plane = default_plane
        if model.shapes:
            Shape.intersect_adjacency(list(model.shapes), tolerance=adj_tol, plane=adj_plane)
            intersected = True

    applied_transforms: list[str] = []
    for idx, tr in enumerate(transforms or []):
        if not isinstance(tr, dict):
            raise ValueError(f"Transform entry at index {idx} must be a dictionary.")
        op = str(tr.get("action") or tr.get("operation") or tr.get("type") or "").strip().lower()
        origin = Point3D(*(float(v) for v in (tr.get("origin") or (0.0, 0.0, 0.0))))
        if op == "move":
            if tr.get("vector") is None:
                raise ValueError(
                    f"Transform entry at index {idx} ('move') requires 'vector' ([dx, dy, dz])."
                )
            vec = Vector3D(*(float(v) for v in tr["vector"]))
            model.move(vec)
        elif op == "rotate":
            if tr.get("axis") is None:
                raise ValueError(
                    f"Transform entry at index {idx} ('rotate') requires 'axis' ([ax, ay, az]) "
                    "and 'angle_degrees'."
                )
            axis = Vector3D(*(float(v) for v in tr["axis"]))
            angle = float(tr.get("angle_degrees", tr.get("angle", 0.0)))
            model.rotate(axis, angle, origin)
        elif op == "rotate_xy":
            angle = float(tr.get("angle_degrees", tr.get("angle", 0.0)))
            model.rotate_xy(angle, origin)
        elif op == "scale":
            if tr.get("factor") is None:
                raise ValueError(
                    f"Transform entry at index {idx} ('scale') requires numeric 'factor'."
                )
            factor = float(tr["factor"])
            model.scale(factor, origin)
        else:
            raise ValueError(f"Unsupported Fairyfly transform operation {op!r}. Use move, rotate, rotate_xy, or scale.")
        applied_transforms.append(op)

    converted_to_units: str | None = None
    if convert_units:
        model.convert_to_units(str(convert_units))
        converted_to_units = str(model.units)

    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path, manifest, resolved_model_target, model
    )
    change_details = {
        "added_shapes": added_shapes,
        "added_boundaries": added_boundaries,
        "edited_shapes": edited_shapes,
        "edited_boundaries": edited_boundaries,
        "removed_shape_identifiers": removed_shape_ids,
        "removed_boundary_identifiers": removed_boundary_ids,
        "added_shape_count": len(added_shapes),
        "added_boundary_count": len(added_boundaries),
        "intersected_adjacency": intersected,
        "applied_transforms": applied_transforms,
        "units": str(model.units),
        "converted_to_units": converted_to_units,
    }
    return _model_update_response(
        model=model,
        model_target=updated_model_target,
        garden_id=manifest.garden_id,
        persisted_path=persisted_path,
        operation="edit_fairyfly_model",
        message=(
            f"Edited Fairyfly model: +{len(added_shapes)}/-{len(removed_shape_ids)} shape(s), "
            f"+{len(added_boundaries)}/-{len(removed_boundary_ids)} boundary(ies)."
        ),
        change_details=change_details,
    )


def _point_to_segment_distance_3d(pt: Point3D, seg: LineSegment3D) -> float:
    ax, ay, az = float(seg.p.x), float(seg.p.y), float(seg.p.z)
    vx, vy, vz = float(seg.v.x), float(seg.v.y), float(seg.v.z)
    px, py, pz = float(pt.x) - ax, float(pt.y) - ay, float(pt.z) - az
    len_sq = vx * vx + vy * vy + vz * vz
    if len_sq <= 1e-18:
        return math.sqrt(px * px + py * py + pz * pz)
    t = max(0.0, min(1.0, (px * vx + py * vy + pz * vz) / len_sq))
    dx, dy, dz = px - t * vx, py - t * vy, pz - t * vz
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _segment_to_segment_distance_3d(seg_a: LineSegment3D, seg_b: LineSegment3D) -> float:
    d1x, d1y, d1z = float(seg_a.v.x), float(seg_a.v.y), float(seg_a.v.z)
    d2x, d2y, d2z = float(seg_b.v.x), float(seg_b.v.y), float(seg_b.v.z)
    rx = float(seg_a.p1.x) - float(seg_b.p1.x)
    ry = float(seg_a.p1.y) - float(seg_b.p1.y)
    rz = float(seg_a.p1.z) - float(seg_b.p1.z)
    a = d1x * d1x + d1y * d1y + d1z * d1z
    e = d2x * d2x + d2y * d2y + d2z * d2z
    if a <= 1e-18 and e <= 1e-18:
        return math.sqrt(rx * rx + ry * ry + rz * rz)
    if a <= 1e-18:
        return _point_to_segment_distance_3d(seg_a.p1, seg_b)
    c = d1x * rx + d1y * ry + d1z * rz
    if e <= 1e-18:
        return _point_to_segment_distance_3d(seg_b.p1, seg_a)
    f = d2x * rx + d2y * ry + d2z * rz
    b = d1x * d2x + d1y * d2y + d1z * d2z
    denom = a * e - b * b
    s = max(0.0, min(1.0, (b * f - c * e) / denom)) if denom > 1e-18 else 0.0
    t = (b * s + f) / e
    if t < 0.0:
        t = 0.0
        s = max(0.0, min(1.0, -c / a))
    elif t > 1.0:
        t = 1.0
        s = max(0.0, min(1.0, (b - c) / a))
    dx = rx + s * d1x - t * d2x
    dy = ry + s * d1y - t * d2y
    dz = rz + s * d1z - t * d2z
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _segment_covered_by_edges(
    seg: LineSegment3D,
    edges: list[LineSegment3D],
    tol: float,
) -> bool:
    length = float(seg.length)
    if length <= 1e-12:
        return False
    if length <= tol:
        return any(
            _point_to_segment_distance_3d(seg.p1, edge) <= tol
            and _point_to_segment_distance_3d(seg.p2, edge) <= tol
            for edge in edges
        )
    p1 = seg.p1
    ux, uy, uz = float(seg.v.x) / length, float(seg.v.y) / length, float(seg.v.z) / length
    intervals: list[tuple[float, float]] = []
    for edge in edges:
        t1 = (
            (float(edge.p1.x) - float(p1.x)) * ux
            + (float(edge.p1.y) - float(p1.y)) * uy
            + (float(edge.p1.z) - float(p1.z)) * uz
        )
        t2 = (
            (float(edge.p2.x) - float(p1.x)) * ux
            + (float(edge.p2.y) - float(p1.y)) * uy
            + (float(edge.p2.z) - float(p1.z)) * uz
        )
        lo = max(0.0, min(t1, t2))
        hi = min(length, max(t1, t2))
        if hi <= lo:
            continue
        q_lo = Point3D(float(p1.x) + lo * ux, float(p1.y) + lo * uy, float(p1.z) + lo * uz)
        q_hi = Point3D(float(p1.x) + hi * ux, float(p1.y) + hi * uy, float(p1.z) + hi * uz)
        if _point_to_segment_distance_3d(q_lo, edge) <= tol and _point_to_segment_distance_3d(
            q_hi, edge
        ) <= tol:
            intervals.append((lo, hi))
    if not intervals:
        return False
    merged_hi = 0.0
    for lo, hi in sorted(intervals):
        if lo > merged_hi + tol:
            return False
        merged_hi = max(merged_hi, hi)
    return merged_hi >= length - tol


def inspect_fairyfly_model_geometry(model: Model) -> dict[str, Any]:
    """Inspect shapes, materials, exterior edges, boundaries, and THERM problem areas."""
    tol = max(float(getattr(model, "tolerance", 0.01) or 0.01), 1e-6)
    plane = getattr(getattr(model.properties, "therm", None), "therm_plane", None)

    shapes_missing_materials: list[dict[str, Any]] = []
    for idx, shape in enumerate(getattr(model, "shapes", ()) or ()):
        therm_props = getattr(getattr(shape, "properties", None), "therm", None)
        if therm_props is None:
            missing = True
        elif hasattr(therm_props, "_material"):
            missing = getattr(therm_props, "_material", None) is None
        else:
            missing = getattr(therm_props, "material", None) is None
        if missing:
            shapes_missing_materials.append(
                {
                    "index": idx,
                    "identifier": getattr(shape, "identifier", None),
                    "display_name": getattr(shape, "display_name", None) or f"shape_{idx}",
                }
            )

    exterior_edges: list[LineSegment3D] = []
    problem_regions: list[dict[str, Any]] = []
    problem_holes: list[dict[str, Any]] = []
    problem_area_error: str | None = None

    shapes = list(getattr(model, "shapes", ()) or ())
    if shapes:
        try:
            shapes_copy = [shape.duplicate() for shape in shapes]
            Shape.intersect_adjacency(shapes_copy, tol, plane)
            polyface = Polyface3D.from_faces([shape.geometry for shape in shapes_copy], tolerance=tol)
            exterior_edges = list(polyface.naked_edges)
        except Exception:
            exterior_edges = [
                seg for shape in shapes for seg in getattr(shape.geometry, "segments", ())
            ]

        try:
            regions_raw, holes_raw = model.duplicate().properties.therm.problem_areas
            for idx, poly in enumerate(regions_raw or ()):
                problem_regions.append(
                    {
                        "index": idx,
                        "vertex_count": len(poly.vertices),
                        "vertices": [
                            [round(v.x, 4), round(v.y, 4), round(v.z, 4)] for v in poly.vertices
                        ],
                    }
                )
            for idx, poly in enumerate(holes_raw or ()):
                problem_holes.append(
                    {
                        "index": idx,
                        "vertex_count": len(poly.vertices),
                        "vertices": [
                            [round(v.x, 4), round(v.y, 4), round(v.z, 4)] for v in poly.vertices
                        ],
                    }
                )
        except Exception as exc:
            problem_area_error = str(exc)

    empty_boundaries: list[dict[str, Any]] = []
    misaligned_boundaries: list[dict[str, Any]] = []
    for b_idx, boundary in enumerate(getattr(model, "boundaries", ()) or ()):
        b_name = str(
            getattr(boundary, "display_name", None)
            or getattr(boundary, "identifier", None)
            or f"boundary_{b_idx}"
        )
        b_id = getattr(boundary, "identifier", None)
        segs = list(getattr(boundary, "geometry", ()) or ())
        if not segs:
            empty_boundaries.append(
                {
                    "index": b_idx,
                    "identifier": b_id,
                    "display_name": b_name,
                }
            )
            continue
        for s_idx, seg in enumerate(segs):
            if exterior_edges and _segment_covered_by_edges(seg, exterior_edges, tol):
                continue
            start_coords = [round(float(seg.p1.x), 4), round(float(seg.p1.y), 4), round(float(seg.p1.z), 4)]
            end_coords = [round(float(seg.p2.x), 4), round(float(seg.p2.y), 4), round(float(seg.p2.z), 4)]
            if exterior_edges:
                min_dist = min(
                    _segment_to_segment_distance_3d(seg, edge) for edge in exterior_edges
                )
                sample_pts = (seg.p1, seg.midpoint, seg.p2)
                max_pt_dist = max(
                    min(_point_to_segment_distance_3d(pt, edge) for edge in exterior_edges)
                    for pt in sample_pts
                )
            else:
                min_dist = None
                max_pt_dist = None
            misaligned_boundaries.append(
                {
                    "boundary_index": b_idx,
                    "boundary_identifier": b_id,
                    "boundary_name": b_name,
                    "segment_index": s_idx,
                    "start": start_coords,
                    "end": end_coords,
                    "min_distance": round(min_dist, 4) if min_dist is not None else None,
                    "max_point_distance": round(max_pt_dist, 4) if max_pt_dist is not None else None,
                }
            )

    return {
        "tolerance": tol,
        "shapes_missing_materials": shapes_missing_materials,
        "empty_boundaries": empty_boundaries,
        "misaligned_boundaries": misaligned_boundaries,
        "problem_regions": problem_regions,
        "problem_holes": problem_holes,
        "problem_area_error": problem_area_error,
    }


def validate_fairyfly_model(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a Garden-backed Fairyfly model with SDK checks and THERM geometry/problem areas."""
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

    geom = inspect_fairyfly_model_geometry(model)
    tol = geom["tolerance"]
    for item in geom["shapes_missing_materials"]:
        issues.append(
            f"Shape '{item['display_name']}' ({item['identifier']}) is missing a THERM material assignment."
        )
    for item in geom["empty_boundaries"]:
        issues.append(
            f"Boundary '{item['display_name']}' ({item['identifier']}) has empty geometry (no line segments)."
        )
    for item in geom["misaligned_boundaries"]:
        if item["min_distance"] is None:
            issues.append(
                f"Boundary '{item['boundary_name']}' segment {item['segment_index']} "
                f"({item['start']} -> {item['end']}) has no shape exterior edges to attach to."
            )
        else:
            dist_detail = f"min_distance={item['min_distance']:.4f}"
            if (
                item["max_point_distance"] is not None
                and item["min_distance"] <= tol
                and item["max_point_distance"] > tol
            ):
                dist_detail += f", max_deviation={item['max_point_distance']:.4f}"
            issues.append(
                f"Boundary '{item['boundary_name']}' segment {item['segment_index']} "
                f"({item['start']} -> {item['end']}) does not lie within model tolerance ({tol}) "
                f"of any shape exterior edge ({dist_detail})."
            )

    if geom["problem_area_error"] is not None:
        issues.append(f"Failed inspecting THERM problem_areas: {geom['problem_area_error']}")
    problem_regions = geom["problem_regions"]
    problem_holes = geom["problem_holes"]
    if problem_regions:
        issues.append(
            f"Detected {len(problem_regions)} disconnected THERM problem region(s) that are not contiguous."
        )
    if problem_holes:
        issues.append(
            f"Detected {len(problem_holes)} THERM problem hole(s) inside shape geometry."
        )

    valid = len(issues) == 0
    problem_areas = {
        "problem_regions": problem_regions,
        "problem_holes": problem_holes,
        "problem_region_count": len(problem_regions),
        "problem_hole_count": len(problem_holes),
    }
    return {
        "valid": valid,
        "is_valid": valid,
        "issues": issues,
        "problem_areas": problem_areas,
        "boundary_issues": geom["empty_boundaries"] + geom["misaligned_boundaries"],
        "missing_material_shapes": geom["shapes_missing_materials"],
        "summary_view": {
            "garden_target": manifest.target(),
            "model_target": resolved_target,
            "object_counts": _model_counts(model),
            "issue_count": len(issues),
            "problem_region_count": len(problem_regions),
            "problem_hole_count": len(problem_holes),
            "empty_boundary_count": len(geom["empty_boundaries"]),
            "missing_material_count": len(geom["shapes_missing_materials"]),
            "misaligned_boundary_count": len(geom["misaligned_boundaries"]),
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
    user_data = visualization_set.get("user_data")
    summary = {
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
    if isinstance(user_data, dict):
        if user_data.get("source_run_id"):
            summary["source_run_id"] = user_data["source_run_id"]
        if user_data.get("data_type"):
            summary["data_type"] = user_data["data_type"]
    return summary


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


def _build_heat_flux_vector_geometries(
    thmz_res: THMZResult,
    vectors: list[list[float]],
    magnitudes: list[float],
    *,
    unit: str,
) -> tuple[list[Any], int]:
    """Build mesh outline and scaled DisplayLineSegment3D arrows for heat_flux_vectors."""
    mesh = thmz_res.mesh
    if mesh is None or not vectors or len(mesh.vertices) != len(vectors):
        return [], 0

    plane = thmz_res.plane
    outline_color = Color(160, 160, 160)
    outline_segments: list[DisplayLineSegment3D] = []
    try:
        shape_faces = list(thmz_res.shape_faces or ())
    except Exception:
        shape_faces = []
    if shape_faces:
        for face in shape_faces:
            for seg in face.boundary_segments:
                outline_segments.append(DisplayLineSegment3D(seg, color=outline_color, line_width=1))
    else:
        for edge in mesh.naked_edges:
            outline_segments.append(DisplayLineSegment3D(edge, color=outline_color, line_width=1))

    diag = max(float(mesh.min.distance_to_point(mesh.max)), 1.0)
    step = 1 if len(vectors) <= 400 else max(1, len(vectors) // 400)
    sampled_indices = list(range(0, len(vectors), step))
    h_approx = diag / max(math.sqrt(max(len(sampled_indices), 1)), 2.0)
    max_arrow_len = min(max(diag * 0.12, 1.0), max(h_approx * 1.25, diag * 0.04))

    max_mag = max((float(magnitudes[i]) for i in sampled_indices), default=0.0)
    active_samples: list[tuple[Point3D, Vector3D, float, float]] = []
    if max_mag > 1e-12:
        for idx in sampled_indices:
            mag = float(magnitudes[idx])
            if mag <= 1e-12:
                continue
            arrow_len = max_arrow_len * (mag / max_mag)
            if arrow_len <= 1e-6:
                continue
            vx, vy = float(vectors[idx][0]), float(vectors[idx][1])
            vec3 = plane.x * vx + plane.y * vy
            if vec3.magnitude <= 1e-12:
                continue
            active_samples.append((mesh.vertices[idx], vec3.normalize(), mag, arrow_len))

    geometries: list[Any] = []
    if outline_segments:
        geometries.append(ContextGeometry("Fairyfly_Mesh_Outline", outline_segments))

    if active_samples:
        active_mags = [item[2] for item in active_samples]
        legend = Legend(active_mags, LegendParameters(title=unit))
        colors = list(legend.value_colors)
        arrow_display_segments: list[DisplayLineSegment3D] = []
        shaft_segments: list[LineSegment3D] = []
        for (origin_pt, unit_vec, _mag, arrow_len), col in zip(active_samples, colors):
            tip = origin_pt.move(unit_vec * arrow_len)
            shaft = LineSegment3D.from_end_points(origin_pt, tip)
            shaft_segments.append(shaft)
            arrow_display_segments.append(DisplayLineSegment3D(shaft, color=col, line_width=2))

            perp_raw = plane.n.cross(unit_vec)
            if perp_raw.magnitude > 1e-12:
                perp = perp_raw.normalize()
                head_len = arrow_len * 0.25
                back_vec = unit_vec * (-head_len * 0.85)
                wing_offset = perp * (head_len * 0.45)
                wing1 = tip.move(back_vec + wing_offset)
                wing2 = tip.move(back_vec - wing_offset)
                if tip.distance_to_point(wing1) > 1e-6:
                    arrow_display_segments.append(
                        DisplayLineSegment3D(
                            LineSegment3D.from_end_points(tip, wing1), color=col, line_width=2
                        )
                    )
                if tip.distance_to_point(wing2) > 1e-6:
                    arrow_display_segments.append(
                        DisplayLineSegment3D(
                            LineSegment3D.from_end_points(tip, wing2), color=col, line_width=2
                        )
                    )

        geometries.append(ContextGeometry("Fairyfly_Heat_Flux_Vectors", arrow_display_segments))
        analysis = AnalysisGeometry(
            "Fairyfly_Heat_Flux_Magnitude",
            shaft_segments,
            [VisualizationData(active_mags, unit=unit)],
            display_mode="Wireframe",
        )
        analysis.display_name = "Fairyfly THERM heat_flux_vectors"
        geometries.append(analysis)

    return geometries, len(active_samples)


def fairyfly_therm_result_to_visualization_set(
    *,
    garden_root: str,
    thmz_target: dict[str, Any] | None = None,
    run_target: dict[str, Any] | None = None,
    run_id: str | None = None,
    data_type: str = "temperature",
    timestep_index: int | None = None,
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
        timestep_index=timestep_index,
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
    thmz_res = THMZResult(str(thmz_path))
    mesh = thmz_res.mesh
    normalized_data_type = str(summary.get("data_type") or data_type)
    unit = _THERM_RESULT_UNITS.get(normalized_data_type, "")
    source_run_id = str(summary.get("run_id") or "")
    identifier = name or f"fairyfly_therm_{source_run_id}_{normalized_data_type}"

    extra_summary: dict[str, Any] = {}
    if normalized_data_type == "heat_flux_vectors":
        vectors = list(read_result.get("vectors", []))
        geometry, arrow_count = _build_heat_flux_vector_geometries(
            thmz_res, vectors, values, unit=unit
        )
        if not geometry:
            summary.update({"status": "no_results", "value_count": 0, "vector_count": 0})
            return {
                "summary_view": summary,
                "report": make_report(
                    status="warning",
                    message="THERM heat-flux vector results are not available for visualization.",
                    warnings=["THERM mesh/vector results are missing from the THMZ."],
                ),
            }
        extra_summary["vector_arrow_count"] = arrow_count
    else:
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
        analysis = AnalysisGeometry(
            "Fairyfly_THERM_Result",
            [mesh],
            [VisualizationData(values, unit=unit)],
            display_mode="SurfaceWithEdges",
        )
        analysis.display_name = f"Fairyfly THERM {normalized_data_type}"
        geometry = [analysis]

    vis_set = VisualizationSet(identifier, geometry, "Millimeters")
    vis_set.display_name = identifier
    vis_set.user_data = {
        "source_run_id": source_run_id,
        "run_id": source_run_id,
        "data_type": normalized_data_type,
        "thmz_path": summary.get("thmz_path"),
    }
    visualization_set = vis_set.to_dict()
    summary.update(
        {
            **_summarize_visualization_set(visualization_set),
            "status": "ok",
            "run_id": source_run_id,
            "source_run_id": source_run_id,
            "units": unit,
            "visualization_units": "Millimeters",
            "body_returned": return_visualization_set,
            **extra_summary,
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
                "run_id": source_run_id,
                "source_run_id": source_run_id,
                "data_type": normalized_data_type,
                "thmz_path": summary.get("thmz_path"),
            },
        )
        result["target"] = saved["target"]
        result["visualization_set_target"] = saved["visualization_set_target"]
        result["persistence_receipt"] = saved["persistence_receipt"]
        result["summary_view"]["visualization_set_target"] = saved["visualization_set_target"]
        result["summary_view"]["body_returned"] = False
        result.pop("visualization_set", None)
    return result
