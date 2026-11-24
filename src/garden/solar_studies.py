"""Ladybug and Ladybug-Radiance fast solar geometry study services."""

from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path
from statistics import mean
from typing import Any

from ladybug.color import Color, Colorset
from ladybug.datacollection import HourlyDiscontinuousCollection
from ladybug.datatype.fraction import Fraction
from ladybug.datatype.generic import GenericType
from ladybug.epw import EPW
from ladybug.graphic import GraphicContainer
from ladybug.legend import LegendParameters
from ladybug.location import Location
from ladybug.solarenvelope import SolarEnvelope
from ladybug.sunpath import Sunpath
from ladybug.viewsphere import ViewSphere
from ladybug_display.extension.study.directsun import direct_sun_study_to_vis_set
from ladybug_display.extension.study.radiation import radiation_study_to_vis_set
from ladybug_display.extension.viewsphere import view_sphere_to_vis_set
from ladybug_display.geometry3d import (
    DisplayFace3D,
    DisplayLineSegment3D,
    DisplayMesh3D,
    DisplayPoint3D,
    DisplayPolyline3D,
    DisplayText3D,
)
from ladybug_display.visualization import (
    AnalysisGeometry,
    ContextGeometry,
    VisualizationData,
    VisualizationSet,
)
from ladybug_geometry.bounding import bounding_box
from ladybug_geometry.geometry3d import (
    Face3D,
    LineSegment3D,
    Mesh3D,
    Point3D,
    Polyline3D,
    Vector3D,
)
from ladybug_radiance.intersection import sky_intersection_matrix
from ladybug_radiance.skymatrix import SkyMatrix
from ladybug_radiance.study.directsun import DirectSunStudy
from ladybug_radiance.study.radiation import RadiationStudy

from garden.analysis_period import analysis_period_from_input
from garden.data_collection import DATA_COLLECTION_TARGET_TYPE, load_data_collection
from garden.honeybee_core.locate import find_object
from garden.honeybee_core.model_io import load_honeybee_model, resolve_model_target
from garden.manifest import GardenManifest
from garden.paths import slugify_name
from garden.ray_intersect import (
    intersect_mesh_rays,
    intersect_mesh_rays_distance,
    intersect_rays_with_mesh_faces,
    trace_ray_bounces,
    triangulate_geometry,
)
from garden.run_energy.config import resolve_garden_weather_epw
from garden.visualize.artifacts import coerce_legend_parameter, save_visualization_set
from garden.visualize.sky import _sky_matrix_from_target
from ladybug_tools_mcp.contracts import make_report


def _coerce_mesh3d(raw: dict[str, Any]) -> Mesh3D:
    if not isinstance(raw, dict):
        raise ValueError("study_mesh must be a Mesh3D or Face3D dictionary.")
    data = dict(raw)
    if data.get("type") == "Face3D":
        face = Face3D.from_dict(data)
        return Mesh3D.from_face_vertices([face.vertices])
    data.setdefault("type", "Mesh3D")
    return Mesh3D.from_dict(data)


def _coerce_context_item(raw: dict[str, Any]) -> Face3D | Mesh3D:
    if not isinstance(raw, dict):
        raise ValueError("Each context_geometry entry must be a Face3D or Mesh3D dict.")
    data = dict(raw)
    gtype = data.get("type")
    if gtype == "Mesh3D" or "faces" in data:
        data.setdefault("type", "Mesh3D")
        return Mesh3D.from_dict(data)
    data.setdefault("type", "Face3D")
    return Face3D.from_dict(data)


def _join_meshes(meshes: list[Mesh3D]) -> Mesh3D:
    if len(meshes) == 1:
        return meshes[0]
    return Mesh3D.join_meshes(meshes)


def _geometry_from_model(
    *,
    garden_root_path: Path,
    model_target: dict[str, Any] | None,
    study_face_targets: list[dict[str, Any]] | None,
    study_room_targets: list[dict[str, Any]] | None,
    face_type_filter: str | None,
    grid_size: float | None,
) -> tuple[Mesh3D | None, list[Face3D | Mesh3D], dict[str, Any]]:
    _, resolved_target = resolve_model_target(garden_root_path, model_target)
    model = load_honeybee_model(garden_root_path, resolved_target)

    study_faces: list[Face3D] = []
    selected_ids: set[str] = set()
    for tgt in study_face_targets or []:
        obj = find_object(model, tgt)
        if hasattr(obj, "geometry"):
            study_faces.append(obj.geometry)
            selected_ids.add(obj.identifier)
    for tgt in study_room_targets or []:
        room = find_object(model, tgt)
        for face in getattr(room, "faces", []):
            if face_type_filter and type(face.type).__name__.lower() != face_type_filter.lower():
                continue
            study_faces.append(face.geometry)
            selected_ids.add(face.identifier)

    all_context: list[Face3D | Mesh3D] = []
    for room in model.rooms:
        for face in room.faces:
            if not study_faces and face_type_filter and type(face.type).__name__.lower() == face_type_filter.lower():
                study_faces.append(face.geometry)
                selected_ids.add(face.identifier)
            if face.identifier not in selected_ids:
                all_context.append(face.geometry)
            for sh in face.shades:
                all_context.append(sh.geometry)
        for sh in room.shades:
            all_context.append(sh.geometry)
    for face in model.orphaned_faces:
        if not study_faces and face_type_filter and type(face.type).__name__.lower() == face_type_filter.lower():
            study_faces.append(face.geometry)
            selected_ids.add(face.identifier)
        if face.identifier not in selected_ids:
            all_context.append(face.geometry)
        for sh in face.shades:
            all_context.append(sh.geometry)
    for sh in model.shades:
        all_context.append(sh.geometry)

    if not study_faces:
        first_room_faces = [
            face.geometry
            for room in model.rooms
            for face in room.faces
            if type(face.type).__name__.lower() in {"roofceiling", "floor"}
        ]
        if first_room_faces:
            study_faces = first_room_faces
        elif model.rooms:
            study_faces = [model.rooms[0].faces[0].geometry]

    study_mesh: Mesh3D | None = None
    if study_faces:
        if grid_size is not None and grid_size > 0:
            meshes = [face.mesh_grid(grid_size) for face in study_faces]
        else:
            meshes = [Mesh3D.from_face_vertices([face.vertices]) for face in study_faces]
        study_mesh = _join_meshes(meshes)

    return study_mesh, all_context, resolved_target


def _resolve_study_geometry(
    *,
    garden_root_path: Path,
    study_mesh: dict[str, Any] | None,
    study_face: dict[str, Any] | None,
    context_geometry: list[dict[str, Any]] | None,
    model_target: dict[str, Any] | None,
    study_face_targets: list[dict[str, Any]] | None,
    study_room_targets: list[dict[str, Any]] | None,
    face_type_filter: str | None,
    grid_size: float | None,
    require_study_mesh: bool = True,
) -> tuple[Mesh3D | None, list[Face3D | Mesh3D], dict[str, Any] | None]:
    resolved_mesh: Mesh3D | None = None
    resolved_context: list[Face3D | Mesh3D] = []
    resolved_model_target: dict[str, Any] | None = None

    if model_target is not None or study_face_targets or study_room_targets:
        resolved_mesh, resolved_context, resolved_model_target = _geometry_from_model(
            garden_root_path=garden_root_path,
            model_target=model_target,
            study_face_targets=study_face_targets,
            study_room_targets=study_room_targets,
            face_type_filter=face_type_filter,
            grid_size=grid_size,
        )

    if study_mesh is not None:
        resolved_mesh = _coerce_mesh3d(study_mesh)
    elif study_face is not None:
        face = Face3D.from_dict({"type": "Face3D", **study_face})
        resolved_mesh = (
            face.mesh_grid(grid_size)
            if (grid_size is not None and grid_size > 0)
            else Mesh3D.from_face_vertices([face.vertices])
        )

    if context_geometry is not None:
        resolved_context.extend(_coerce_context_item(item) for item in context_geometry)

    if require_study_mesh and resolved_mesh is None:
        raise ValueError(
            "Provide study_mesh, study_face, or model_target with study geometry."
        )
    return resolved_mesh, resolved_context, resolved_model_target


def _resolve_sun_vectors(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    vectors: list[list[float] | dict[str, Any]] | None,
    location: dict[str, Any] | None,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
    hoys: list[float] | None,
    analysis_period: dict[str, Any] | str | None,
    north_angle: float,
    solar_time: bool,
) -> list[Vector3D]:
    if vectors:
        vec_objs: list[Vector3D] = []
        for item in vectors:
            if isinstance(item, dict):
                data = dict(item)
                data.setdefault("type", "Vector3D")
                vec_objs.append(Vector3D.from_dict(data))
            elif isinstance(item, (list, tuple)) and len(item) >= 3:
                vec_objs.append(Vector3D(float(item[0]), float(item[1]), float(item[2])))
            else:
                raise ValueError("Each vector must be a 3-element list or Vector3D dict.")
        return vec_objs

    if location is not None:
        loc_data = dict(location)
        loc_data.setdefault("type", "Location")
        loc_obj = Location.from_dict(loc_data)
    elif weather_target is not None:
        epw_file = resolve_garden_weather_epw(
            garden_root=garden_root_path, manifest=manifest, weather_target=weather_target
        )
        loc_obj = EPW(str(epw_file)).location
    elif epw_path is not None:
        raw = Path(epw_path).expanduser()
        cand = raw.resolve() if raw.is_absolute() else (garden_root_path / raw).resolve()
        cand.relative_to(garden_root_path)
        loc_obj = EPW(str(cand)).location
    else:
        raise ValueError("Provide vectors or location/weather_target/epw_path.")

    sp = Sunpath.from_location(loc_obj, north_angle=north_angle)
    resolved_hoys = list(hoys or [])
    if not resolved_hoys and analysis_period is not None:
        ap = analysis_period_from_input(analysis_period)
        if ap is not None:
            resolved_hoys = list(ap.hoys)
    if not resolved_hoys:
        resolved_hoys = [12.0 + 24.0 * d for d in range(0, 365, 30)]

    day_vecs = []
    for hoy in resolved_hoys:
        sun = sp.calculate_sun_from_hoy(float(hoy), is_solar_time=solar_time)
        if sun.is_during_day:
            day_vecs.append(sun.sun_vector)
    if not day_vecs:
        raise ValueError("No daytime sun vectors found for the specified HOYs/analysis_period.")
    return day_vecs


def _resolve_sky_matrix(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    sky_matrix_target: dict[str, Any] | None,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
    location: dict[str, Any] | None,
    hoys: list[float] | None,
    analysis_period: dict[str, Any] | str | None,
    north_angle: float,
    high_density: bool,
    ground_reflectance: float,
    benefit: bool,
    balance_temperature: float,
    balance_offset: float,
) -> SkyMatrix:
    if sky_matrix_target is not None:
        sm, _, _ = _sky_matrix_from_target(
            garden_root=garden_root_path,
            manifest=manifest,
            sky_matrix_target=sky_matrix_target,
        )
        return sm

    resolved_hoys = list(hoys or [])
    if not resolved_hoys and analysis_period is not None:
        ap = analysis_period_from_input(analysis_period)
        if ap is not None:
            resolved_hoys = list(ap.hoys)

    if weather_target is not None or epw_path is not None:
        if weather_target is not None:
            epw_file = resolve_garden_weather_epw(
                garden_root=garden_root_path, manifest=manifest, weather_target=weather_target
            )
        else:
            raw = Path(str(epw_path)).expanduser()
            epw_file = raw.resolve() if raw.is_absolute() else (garden_root_path / raw).resolve()
            epw_file.relative_to(garden_root_path)
        if benefit:
            return SkyMatrix.from_epw_benefit(
                str(epw_file),
                balance_temperature=balance_temperature,
                balance_offset=balance_offset,
                hoys=resolved_hoys or None,
                north=north_angle,
                high_density=high_density,
                ground_reflectance=ground_reflectance,
            )
        return SkyMatrix.from_epw(
            str(epw_file),
            hoys=resolved_hoys or None,
            north=north_angle,
            high_density=high_density,
            ground_reflectance=ground_reflectance,
        )
    if location is not None:
        loc_data = dict(location)
        loc_data.setdefault("type", "Location")
        loc_obj = Location.from_dict(loc_data)
        return SkyMatrix.from_ashrae_clear_sky(
            loc_obj,
            hoys=resolved_hoys or None,
            north=north_angle,
            high_density=high_density,
            ground_reflectance=ground_reflectance,
        )
    raise ValueError("Provide sky_matrix_target, weather_target, epw_path, or location.")


def _persist_study_vis_set(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    vis_set: VisualizationSet,
    name: str,
    source: dict[str, Any],
    return_visualization_set: bool,
    extra_summary: dict[str, Any],
    message: str,
) -> dict[str, Any]:
    safe_name = slugify_name(name)
    vis_set.identifier = safe_name
    vis_set.display_name = name
    vis_dict = vis_set.to_dict()
    saved = save_visualization_set(
        garden_root=str(garden_root_path),
        visualization_set=vis_dict,
        name=safe_name,
        source=source,
    )
    summary_view = {
        "garden_target": manifest.target(),
        "visualization_set_target": saved["visualization_set_target"],
        "geometry_count": len(vis_dict.get("geometry", [])),
        **extra_summary,
    }
    res: dict[str, Any] = {
        "target": saved["target"],
        "visualization_set_target": saved["visualization_set_target"],
        "artifact": saved["artifact"],
        "persistence_receipt": saved["persistence_receipt"],
        "summary_view": summary_view,
        "report": make_report(status="ok", message=message),
    }
    if return_visualization_set:
        res["visualization_set"] = vis_dict
    return res


_VIEW_TYPE_MAP: dict[str, str] = {
    "horizontalradial": "HorizontalRadial",
    "horizontal_radial": "HorizontalRadial",
    "0": "HorizontalRadial",
    "horizontal30degreeoffset": "Horizontal30DegreeOffset",
    "horizontal_30_degree_offset": "Horizontal30DegreeOffset",
    "1": "Horizontal30DegreeOffset",
    "spherical": "Spherical",
    "2": "Spherical",
    "skyexposure": "SkyExposure",
    "sky_exposure": "SkyExposure",
    "3": "SkyExposure",
    "skyview": "SkyView",
    "sky_view": "SkyView",
    "4": "SkyView",
}


def _coerce_point3d(raw: dict[str, Any] | list[float] | tuple[float, ...], field_name: str = "point") -> Point3D:
    if isinstance(raw, dict):
        return Point3D(float(raw.get("x", 0.0)), float(raw.get("y", 0.0)), float(raw.get("z", 0.0)))
    if isinstance(raw, (list, tuple)) and len(raw) >= 3:
        return Point3D(float(raw[0]), float(raw[1]), float(raw[2]))
    raise ValueError(f"{field_name} must be a 3-element list or Point3D dict.")


def _coerce_vector3d(raw: dict[str, Any] | list[float] | tuple[float, ...], field_name: str = "vector") -> Vector3D:
    if isinstance(raw, dict):
        return Vector3D(float(raw.get("x", 0.0)), float(raw.get("y", 0.0)), float(raw.get("z", 0.0)))
    if isinstance(raw, (list, tuple)) and len(raw) >= 3:
        return Vector3D(float(raw[0]), float(raw[1]), float(raw[2]))
    raise ValueError(f"{field_name} must be a 3-element list or Vector3D dict.")


def _mesh_from_geometry_list(items: list[dict[str, Any]], grid_size: float | None) -> Mesh3D:
    meshes: list[Mesh3D] = []
    for raw in items:
        geo = _coerce_context_item(raw)
        if isinstance(geo, Mesh3D):
            meshes.append(geo)
        else:
            meshes.append(
                geo.mesh_grid(grid_size)
                if (grid_size is not None and grid_size > 0)
                else Mesh3D.from_face_vertices([geo.vertices])
            )
    if not meshes:
        raise ValueError("Geometry list must contain at least one Face3D or Mesh3D.")
    return _join_meshes(meshes)


def _normalize_view_type(view_type: str | int) -> str:
    key = str(view_type).strip().lower().replace(" ", "")
    canon = _VIEW_TYPE_MAP.get(key)
    if canon is None:
        raise ValueError(
            f"Unsupported view_type {view_type!r}. Choose from: HorizontalRadial, "
            "Horizontal30DegreeOffset, Spherical, SkyExposure, SkyView."
        )
    return canon


def _resolve_location_obj(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    location: dict[str, Any] | None,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
) -> tuple[Location, EPW | None]:
    if weather_target is not None:
        epw_file = resolve_garden_weather_epw(
            garden_root=garden_root_path, manifest=manifest, weather_target=weather_target
        )
        epw_obj = EPW(str(epw_file))
    elif epw_path is not None:
        raw = Path(epw_path).expanduser()
        cand = raw.resolve() if raw.is_absolute() else (garden_root_path / raw).resolve()
        cand.relative_to(garden_root_path)
        epw_obj = EPW(str(cand))
    else:
        epw_obj = None

    if location is not None:
        loc_data = dict(location)
        loc_data.setdefault("type", "Location")
        return Location.from_dict(loc_data), epw_obj
    if epw_obj is not None:
        return epw_obj.location, epw_obj
    raise ValueError("Provide location, weather_target, or epw_path.")


def _resolve_shade_and_study_points(
    *,
    garden_root_path: Path,
    shade_geometry: list[dict[str, Any]] | None,
    study_region: list[dict[str, Any]] | None,
    study_points: list[list[float] | dict[str, Any]] | None,
    study_directions: list[list[float] | dict[str, Any]] | None,
    study_mesh: dict[str, Any] | None,
    study_face: dict[str, Any] | None,
    context_geometry: list[dict[str, Any]] | None,
    model_target: dict[str, Any] | None,
    study_face_targets: list[dict[str, Any]] | None,
    study_room_targets: list[dict[str, Any]] | None,
    face_type_filter: str | None,
    grid_size: float | None,
    center_point: list[float] | dict[str, Any] | None,
    region_grid_divisor: float = 1.0,
) -> tuple[Mesh3D, list[Point3D], list[Vector3D] | None, list[Face3D | Mesh3D], dict[str, Any] | None]:
    res_mesh, ctx, res_model = _resolve_study_geometry(
        garden_root_path=garden_root_path,
        study_mesh=study_mesh,
        study_face=study_face,
        context_geometry=context_geometry,
        model_target=model_target,
        study_face_targets=study_face_targets,
        study_room_targets=study_room_targets,
        face_type_filter=face_type_filter,
        grid_size=grid_size,
        require_study_mesh=False,
    )

    if shade_geometry:
        shade_mesh = _mesh_from_geometry_list(shade_geometry, grid_size)
    elif res_mesh is not None and (study_mesh is not None or study_face is not None):
        shade_mesh = res_mesh
    elif model_target is not None:
        _, resolved_target = resolve_model_target(garden_root_path, model_target)
        model = load_honeybee_model(garden_root_path, resolved_target)
        shade_faces = (
            [sh.geometry for sh in model.shades]
            + [sh.geometry for r in model.rooms for sh in r.shades]
            + [sh.geometry for r in model.rooms for f in r.faces for sh in f.shades]
            + [sh.geometry for f in model.orphaned_faces for sh in f.shades]
        )
        if shade_faces:
            shade_meshes = [
                f.mesh_grid(grid_size)
                if (grid_size is not None and grid_size > 0)
                else Mesh3D.from_face_vertices([f.vertices])
                for f in shade_faces
            ]
            shade_mesh = _join_meshes(shade_meshes)
        elif res_mesh is not None:
            shade_mesh = res_mesh
        else:
            raise ValueError("Provide shade_geometry or a model_target with shade geometry.")
    else:
        raise ValueError("Provide shade_geometry, study_mesh, study_face, or model_target.")

    resolved_pts: list[Point3D] = []
    if study_points:
        resolved_pts = [_coerce_point3d(p, "study_points") for p in study_points]
    elif study_region:
        reg_grid = (grid_size / region_grid_divisor) if (grid_size is not None and grid_size > 0) else None
        reg_mesh = _mesh_from_geometry_list(study_region, reg_grid)
        resolved_pts = list(reg_mesh.face_centroids)
    elif res_mesh is not None and (study_mesh is not None or study_face is not None or study_face_targets or study_room_targets or model_target is not None) and shade_geometry:
        resolved_pts = list(res_mesh.face_centroids)
    elif center_point is not None:
        resolved_pts = [_coerce_point3d(center_point, "center_point")]
    else:
        raise ValueError(
            "Provide study_points, study_region, center_point, or model/study geometry for shade benefit."
        )

    resolved_dirs: list[Vector3D] | None = None
    if study_directions is not None:
        resolved_dirs = [_coerce_vector3d(v, "study_directions") for v in study_directions]
        if len(resolved_dirs) != len(resolved_pts):
            raise ValueError(
                f"study_directions length ({len(resolved_dirs)}) must match study_points ({len(resolved_pts)})."
            )

    return shade_mesh, resolved_pts, resolved_dirs, ctx, res_model


def _compute_view_rose_data(
    *,
    view_type: str,
    resolution: int,
    center_point: Point3D,
    radius: float,
    ctx_geometries: list[Face3D | Mesh3D],
    legend_parameters: LegendParameters | None,
    draw_view_rays: bool,
) -> tuple[VisualizationSet, dict[str, Any], list[float]]:
    vs = ViewSphere()
    rose_vt = "SkyExposure" if view_type == "SkyView" else view_type
    az_count = 72 * int(resolution)
    alt_count = 6 * int(resolution) if rose_vt == "Horizontal30DegreeOffset" else 18 * int(resolution)

    if rose_vt == "HorizontalRadial":
        _, view_vecs = vs.horizontal_circle_view_mesh(
            center_point=center_point, radius=float(radius), azimuth_count=az_count
        )
    elif rose_vt == "Horizontal30DegreeOffset":
        _, view_vecs = vs.horizontal_radial_view_mesh(
            center_point=center_point, radius=float(radius), azimuth_count=az_count, altitude_count=alt_count
        )
    elif rose_vt == "Spherical":
        _, view_vecs = vs.sphere_view_mesh(
            center_point=center_point, radius=float(radius), azimuth_count=az_count, altitude_count=alt_count
        )
    else:
        _, view_vecs = vs.dome_view_mesh(
            center_point=center_point, radius=float(radius), azimuth_count=az_count, altitude_count=alt_count
        )

    if ctx_geometries:
        ctx_tris = triangulate_geometry(ctx_geometries)
        distances = intersect_mesh_rays_distance(
            ctx_tris, center_point, list(view_vecs), max_dist=float(radius)
        )
    else:
        distances = [float(radius)] * len(view_vecs)

    vis_set = view_sphere_to_vis_set(
        vs,
        view_type=rose_vt,
        resolution=int(resolution),
        center_point=center_point,
        context_intersect_dist=distances,
        dist_units="m",
        radius=float(radius),
        legend_parameters=legend_parameters,
        draw_view_rays=draw_view_rays,
    )
    blocked_count = sum(1 for d in distances if d < float(radius) - 1e-6)
    ray_count = len(distances)
    unobstructed_pct = ((ray_count - blocked_count) / ray_count * 100.0) if ray_count else 0.0
    openness_pct = (mean(distances) / float(radius) * 100.0) if (distances and radius > 0) else 0.0
    summary = {
        "view_type": rose_vt,
        "resolution": int(resolution),
        "center_point": [center_point.x, center_point.y, center_point.z],
        "radius": float(radius),
        "ray_count": ray_count,
        "blocked_ray_count": blocked_count,
        "unobstructed_percent": unobstructed_pct,
        "openness_percent": openness_pct,
        "min_distance": min(distances) if distances else None,
        "max_distance": max(distances) if distances else None,
        "mean_distance": mean(distances) if distances else None,
    }
    return vis_set, summary, distances


def _append_context_geometry(vis_set: VisualizationSet, ctx: list[Face3D | Mesh3D]) -> None:
    if not ctx:
        return
    con_color = Color(125, 125, 125, 125)
    vis_set.add_geometry(
        ContextGeometry(
            "Context_Geometry",
            [
                DisplayMesh3D(g, con_color) if isinstance(g, Mesh3D) else DisplayFace3D(g, con_color)
                for g in ctx
            ],
        )
    )


def run_solar_geometry_study(
    *,
    garden_root: str,
    study_type: str,
    study_mesh: dict[str, Any] | None = None,
    study_face: dict[str, Any] | None = None,
    context_geometry: list[dict[str, Any]] | None = None,
    model_target: dict[str, Any] | None = None,
    study_face_targets: list[dict[str, Any]] | None = None,
    study_room_targets: list[dict[str, Any]] | None = None,
    face_type_filter: str | None = None,
    grid_size: float | None = None,
    # solar / sky inputs
    vectors: list[list[float] | dict[str, Any]] | None = None,
    sky_matrix_target: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    location: dict[str, Any] | None = None,
    hoys: list[float] | None = None,
    analysis_period: dict[str, Any] | str | None = None,
    north_angle: float = 0.0,
    solar_time: bool = False,
    timestep: int = 1,
    high_density: bool = False,
    ground_reflectance: float = 0.2,
    benefit: bool = False,
    balance_temperature: float = 15.0,
    balance_offset: float = 2.0,
    plot_irradiance: bool = False,
    # study options
    offset_distance: float = 0.0,
    by_vertex: bool = False,
    use_radiance_mesh: bool = False,
    # solar envelope options
    height_limit: float = 100.0,
    solar_rights: bool = False,
    # view_sphere / sky_intersection / view_percent / view_rose options
    view_type: str = "SkyExposure",
    resolution: int = 1,
    center_point: list[float] | dict[str, Any] | None = None,
    radius: float = 5.0,
    numericalize: bool = False,
    geo_block: bool | None = None,
    include_view_rose: bool = False,
    draw_view_rays: bool = True,
    # shade_benefit / thermal_shade_benefit options
    shade_geometry: list[dict[str, Any]] | None = None,
    study_region: list[dict[str, Any]] | None = None,
    study_points: list[list[float] | dict[str, Any]] | None = None,
    study_directions: list[list[float] | dict[str, Any]] | None = None,
    temperature_target: dict[str, Any] | None = None,
    up_threshold: float = 26.0,
    low_threshold: float = 9.0,
    # surface_ray_tracing options
    source_geometry: list[dict[str, Any]] | None = None,
    receiver_geometry: list[dict[str, Any]] | None = None,
    bounce_count: int = 1,
    first_length: float | None = None,
    last_length: float | None = None,
    context_block: bool = False,
    # output options
    legend_parameter: dict[str, Any] | None = None,
    include_title: bool = True,
    include_context: bool = True,
    include_values: bool = False,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Run DirectSunStudy, RadiationStudy, SolarEnvelope, SkyIntersection, ViewSphere, ShadeBenefit, ThermalShadeBenefit, SurfaceRayTracing, ViewPercent, or ViewRose."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    kind = str(study_type).strip().lower()
    l_par = coerce_legend_parameter(legend_parameter)

    if kind == "direct_sun":
        mesh, ctx, res_model = _resolve_study_geometry(
            garden_root_path=garden_root_path,
            study_mesh=study_mesh,
            study_face=study_face,
            context_geometry=context_geometry,
            model_target=model_target,
            study_face_targets=study_face_targets,
            study_room_targets=study_room_targets,
            face_type_filter=face_type_filter,
            grid_size=grid_size,
        )
        sun_vecs = _resolve_sun_vectors(
            garden_root_path=garden_root_path,
            manifest=manifest,
            vectors=vectors,
            location=location,
            weather_target=weather_target,
            epw_path=epw_path,
            hoys=hoys,
            analysis_period=analysis_period,
            north_angle=north_angle,
            solar_time=solar_time,
        )
        saved_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as sim_dir:
                study = DirectSunStudy(
                    sun_vecs,
                    mesh,
                    ctx,
                    timestep=timestep,
                    offset_distance=offset_distance,
                    by_vertex=by_vertex,
                    sim_folder=sim_dir,
                    use_radiance_mesh=use_radiance_mesh,
                )
                vals = [float(v) for v in study.direct_sun_hours]
                vis_set = direct_sun_study_to_vis_set(
                    study,
                    legend_parameters=l_par,
                    include_title=include_title,
                    include_context=include_context,
                )
        finally:
            os.chdir(saved_cwd)
        extra: dict[str, Any] = {
            "study_type": "direct_sun",
            "value_count": len(vals),
            "sun_vector_count": len(sun_vecs),
            "min": min(vals) if vals else None,
            "max": max(vals) if vals else None,
            "mean": mean(vals) if vals else None,
        }
        if include_values:
            extra["values"] = vals
        return _persist_study_vis_set(
            garden_root_path=garden_root_path,
            manifest=manifest,
            vis_set=vis_set,
            name=name or "direct_sun_study",
            source={"producer": "LB_Run_Solar_Geometry_Study", "study_type": "direct_sun", "model_target": res_model},
            return_visualization_set=return_visualization_set,
            extra_summary=extra,
            message="DirectSunStudy completed and VisualizationSet persisted.",
        )

    if kind == "radiation":
        mesh, ctx, res_model = _resolve_study_geometry(
            garden_root_path=garden_root_path,
            study_mesh=study_mesh,
            study_face=study_face,
            context_geometry=context_geometry,
            model_target=model_target,
            study_face_targets=study_face_targets,
            study_room_targets=study_room_targets,
            face_type_filter=face_type_filter,
            grid_size=grid_size,
        )
        sky_mtx = _resolve_sky_matrix(
            garden_root_path=garden_root_path,
            manifest=manifest,
            sky_matrix_target=sky_matrix_target,
            weather_target=weather_target,
            epw_path=epw_path,
            location=location,
            hoys=hoys,
            analysis_period=analysis_period,
            north_angle=north_angle,
            high_density=high_density,
            ground_reflectance=ground_reflectance,
            benefit=benefit,
            balance_temperature=balance_temperature,
            balance_offset=balance_offset,
        )
        saved_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as sim_dir:
                if sky_mtx._metadata is None:
                    sky_mtx.folder = sim_dir
                study = RadiationStudy(
                    sky_mtx,
                    mesh,
                    ctx,
                    offset_distance=offset_distance,
                    by_vertex=by_vertex,
                    sim_folder=sim_dir,
                    use_radiance_mesh=use_radiance_mesh,
                )
                rad_vals = [float(v) for v in study.radiation_values]
                irr_vals = [float(v) for v in study.irradiance_values]
                tot_rad = float(study.total_radiation())
                is_ben = bool(study.is_benefit)
                vis_set = radiation_study_to_vis_set(
                    study,
                    legend_parameters=l_par,
                    plot_irradiance=plot_irradiance,
                    include_title=include_title,
                    include_context=include_context,
                )
        finally:
            os.chdir(saved_cwd)
        active_vals = irr_vals if plot_irradiance else rad_vals
        extra = {
            "study_type": "radiation",
            "benefit": is_ben,
            "is_benefit": is_ben,
            "plot_irradiance": plot_irradiance,
            "unit": "W/m2" if plot_irradiance else "kWh/m2",
            "value_count": len(active_vals),
            "total_radiation_kwh": tot_rad,
            "min": min(active_vals) if active_vals else None,
            "max": max(active_vals) if active_vals else None,
            "mean": mean(active_vals) if active_vals else None,
        }
        if include_values:
            extra["radiation_values"] = rad_vals
            extra["irradiance_values"] = irr_vals
        return _persist_study_vis_set(
            garden_root_path=garden_root_path,
            manifest=manifest,
            vis_set=vis_set,
            name=name or "radiation_study",
            source={"producer": "LB_Run_Solar_Geometry_Study", "study_type": "radiation", "is_benefit": is_ben, "model_target": res_model},
            return_visualization_set=return_visualization_set,
            extra_summary=extra,
            message="RadiationStudy completed and VisualizationSet persisted.",
        )

    if kind == "solar_envelope":
        mesh, ctx, res_model = _resolve_study_geometry(
            garden_root_path=garden_root_path,
            study_mesh=study_mesh,
            study_face=study_face,
            context_geometry=context_geometry,
            model_target=model_target,
            study_face_targets=study_face_targets,
            study_room_targets=study_room_targets,
            face_type_filter=face_type_filter,
            grid_size=grid_size,
        )
        obstacle_faces: list[Face3D] = []
        for item in ctx:
            if isinstance(item, Face3D):
                obstacle_faces.append(item)
            elif isinstance(item, Mesh3D):
                for fv in item.face_vertices:
                    obstacle_faces.append(Face3D(fv))
        sun_vecs = _resolve_sun_vectors(
            garden_root_path=garden_root_path,
            manifest=manifest,
            vectors=vectors,
            location=location,
            weather_target=weather_target,
            epw_path=epw_path,
            hoys=hoys,
            analysis_period=analysis_period,
            north_angle=north_angle,
            solar_time=solar_time,
        )
        envelope = SolarEnvelope(
            mesh,
            obstacle_faces,
            sun_vecs,
            height_limit=float(height_limit),
            solar_rights=bool(solar_rights),
        )
        env_mesh = envelope.envelope_mesh()
        face_heights = [float(c.z) for c in env_mesh.face_centroids]
        vis_set = VisualizationSet.from_single_analysis_geo(
            slugify_name(name or "solar_envelope"),
            [env_mesh],
            face_heights or [0.0] * len(env_mesh.faces),
            legend_parameters=l_par,
        )
        if include_context and obstacle_faces:
            con_color = Color(125, 125, 125, 125)
            vis_set.add_geometry(
                ContextGeometry("Obstacle_Faces", [DisplayFace3D(f, con_color) for f in obstacle_faces])
            )
        extra = {
            "study_type": "solar_envelope",
            "solar_rights": bool(solar_rights),
            "height_limit": float(height_limit),
            "sun_vector_count": len(sun_vecs),
            "vertex_count": len(env_mesh.vertices),
            "face_count": len(env_mesh.faces),
            "min_height": min(face_heights) if face_heights else None,
            "max_height": max(face_heights) if face_heights else None,
            "mean_height": mean(face_heights) if face_heights else None,
        }
        if include_values:
            extra["envelope_mesh"] = env_mesh.to_dict()
        return _persist_study_vis_set(
            garden_root_path=garden_root_path,
            manifest=manifest,
            vis_set=vis_set,
            name=name or "solar_envelope",
            source={"producer": "LB_Run_Solar_Geometry_Study", "study_type": "solar_envelope", "model_target": res_model},
            return_visualization_set=return_visualization_set,
            extra_summary=extra,
            message="SolarEnvelope computed and VisualizationSet persisted.",
        )

    if kind == "sky_intersection":
        mesh, ctx, res_model = _resolve_study_geometry(
            garden_root_path=garden_root_path,
            study_mesh=study_mesh,
            study_face=study_face,
            context_geometry=context_geometry,
            model_target=model_target,
            study_face_targets=study_face_targets,
            study_room_targets=study_room_targets,
            face_type_filter=face_type_filter,
            grid_size=grid_size,
        )
        sky_mtx = _resolve_sky_matrix(
            garden_root_path=garden_root_path,
            manifest=manifest,
            sky_matrix_target=sky_matrix_target,
            weather_target=weather_target,
            epw_path=epw_path,
            location=location,
            hoys=hoys,
            analysis_period=analysis_period,
            north_angle=north_angle,
            high_density=high_density,
            ground_reflectance=ground_reflectance,
            benefit=False,
            balance_temperature=balance_temperature,
            balance_offset=balance_offset,
        )
        pts = mesh.vertices if by_vertex else mesh.face_centroids
        norms = mesh.vertex_normals if by_vertex else mesh.face_normals
        saved_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as sim_dir:
                int_mtx = sky_intersection_matrix(
                    sky_mtx,
                    pts,
                    norms,
                    ctx,
                    offset_distance=offset_distance,
                    numericalize=numericalize,
                    sim_folder=sim_dir,
                    use_radiance_mesh=use_radiance_mesh,
                )
        finally:
            os.chdir(saved_cwd)
        n_sky = 577 if sky_mtx.high_density else 145
        sky_view_factors = [
            float(sum(1 if (float(v) > 0 if numericalize else bool(v)) else 0 for v in row[:n_sky]) / n_sky)
            for row in int_mtx
        ]
        vis_set = VisualizationSet.from_single_analysis_geo(
            slugify_name(name or "sky_intersection"),
            [mesh],
            sky_view_factors,
            legend_parameters=l_par,
            data_type=Fraction("Sky View Factor"),
            unit="fraction",
        )
        if include_context and ctx:
            con_color = Color(125, 125, 125, 125)
            vis_set.add_geometry(
                ContextGeometry(
                    "Context_Geometry",
                    [
                        DisplayMesh3D(g, con_color) if isinstance(g, Mesh3D) else DisplayFace3D(g, con_color)
                        for g in ctx
                    ],
                )
            )
        extra = {
            "study_type": "sky_intersection",
            "point_count": len(pts),
            "patch_count": n_sky,
            "min_svf": min(sky_view_factors) if sky_view_factors else None,
            "max_svf": max(sky_view_factors) if sky_view_factors else None,
            "mean_svf": mean(sky_view_factors) if sky_view_factors else None,
        }
        if include_values:
            extra["sky_view_factors"] = sky_view_factors
        return _persist_study_vis_set(
            garden_root_path=garden_root_path,
            manifest=manifest,
            vis_set=vis_set,
            name=name or "sky_intersection",
            source={"producer": "LB_Run_Solar_Geometry_Study", "study_type": "sky_intersection", "model_target": res_model},
            return_visualization_set=return_visualization_set,
            extra_summary=extra,
            message="Sky intersection study completed and VisualizationSet persisted.",
        )

    if kind == "view_sphere":
        vs = ViewSphere()
        _, ctx, res_model = _resolve_study_geometry(
            garden_root_path=garden_root_path,
            study_mesh=study_mesh,
            study_face=study_face,
            context_geometry=context_geometry,
            model_target=model_target,
            study_face_targets=study_face_targets,
            study_room_targets=study_room_targets,
            face_type_filter=face_type_filter,
            grid_size=grid_size,
            require_study_mesh=False,
        )
        if isinstance(center_point, dict):
            cpt = Point3D(
                float(center_point.get("x", 0)),
                float(center_point.get("y", 0)),
                float(center_point.get("z", 0)),
            )
        elif isinstance(center_point, (list, tuple)) and len(center_point) >= 3:
            cpt = Point3D(float(center_point[0]), float(center_point[1]), float(center_point[2]))
        else:
            cpt = Point3D(0, 0, 0)
        vis_set = view_sphere_to_vis_set(
            vs,
            view_type=view_type,
            resolution=resolution,
            center_point=cpt,
            radius=radius,
            legend_parameters=l_par,
            draw_view_rays=True,
        )
        if include_context and ctx:
            con_color = Color(125, 125, 125, 125)
            vis_set.add_geometry(
                ContextGeometry(
                    "Context_Geometry",
                    [
                        DisplayMesh3D(g, con_color) if isinstance(g, Mesh3D) else DisplayFace3D(g, con_color)
                        for g in ctx
                    ],
                )
            )
        vs_vals = [
            float(v)
            for geo in vis_set.geometry
            for ds in getattr(geo, "data_sets", [])
            for v in ds.values
        ]
        extra: dict[str, Any] = {
            "study_type": "view_sphere",
            "view_type": view_type,
            "resolution": resolution,
            "value_count": len(vs_vals),
            "view_average": mean(vs_vals) if vs_vals else None,
            "min": min(vs_vals) if vs_vals else None,
            "max": max(vs_vals) if vs_vals else None,
        }
        if include_values:
            extra["values"] = vs_vals
        return _persist_study_vis_set(
            garden_root_path=garden_root_path,
            manifest=manifest,
            vis_set=vis_set,
            name=name or "view_sphere_study",
            source={
                "producer": "LB_Run_Solar_Geometry_Study",
                "study_type": "view_sphere",
                "view_type": view_type,
                "model_target": res_model,
            },
            return_visualization_set=return_visualization_set,
            extra_summary=extra,
            message="ViewSphere VisualizationSet persisted.",
        )

    if kind == "shade_benefit":
        shade_mesh, study_pts, study_dirs, ctx, res_model = _resolve_shade_and_study_points(
            garden_root_path=garden_root_path,
            shade_geometry=shade_geometry,
            study_region=study_region,
            study_points=study_points,
            study_directions=study_directions,
            study_mesh=study_mesh,
            study_face=study_face,
            context_geometry=context_geometry,
            model_target=model_target,
            study_face_targets=study_face_targets,
            study_room_targets=study_room_targets,
            face_type_filter=face_type_filter,
            grid_size=grid_size,
            center_point=center_point,
            region_grid_divisor=1.0,
        )
        sun_vecs = _resolve_sun_vectors(
            garden_root_path=garden_root_path,
            manifest=manifest,
            vectors=vectors,
            location=location,
            weather_target=weather_target,
            epw_path=epw_path,
            hoys=hoys,
            analysis_period=analysis_period,
            north_angle=north_angle,
            solar_time=solar_time,
        )
        rev_vecs = [v.reverse() for v in sun_vecs]
        shade_tris = triangulate_geometry([shade_mesh])
        ctx_tris = triangulate_geometry(ctx) if ctx else None
        face_int = intersect_rays_with_mesh_faces(
            shade_tris,
            study_pts,
            rev_vecs,
            context_tris=ctx_tris,
            normals=study_dirs,
        )
        eff_timestep = max(1, int(timestep))
        pt_count = len(study_pts)
        shade_help: list[float] = []
        for face_res, face_area in zip(face_int, shade_mesh.face_areas):
            if face_area > 0:
                shade_help.append(((len(face_res) / face_area) / eff_timestep) / pt_count)
            else:
                shade_help.append(0.0)

        l_par_shd = l_par.duplicate() if l_par is not None else LegendParameters()
        if l_par_shd.are_colors_default:
            l_par_shd.colors = Colorset.shade_benefit()
        if l_par_shd.min is None:
            l_par_shd.min = 0.0
        if l_par_shd.max is None and (not shade_help or max(shade_help) <= 0.0):
            l_par_shd.max = 1.0
        if l_par_shd.is_title_default:
            l_par_shd.title = "hrs/m2"

        vis_data = VisualizationData(
            shade_help,
            l_par_shd,
            GenericType("Shade Helpfulness", "hrs/m2"),
            "hrs/m2",
        )
        mesh_geo = AnalysisGeometry("Shade_Benefit", [shade_mesh], [vis_data])
        mesh_geo.display_name = "Shade Benefit"
        mesh_geo.display_mode = "Surface"
        vis_set = VisualizationSet("ShadeBenefit", [mesh_geo])
        vis_set.display_name = "Shade Benefit"

        if include_title:
            min_pt, max_pt = bounding_box((shade_mesh,) + tuple(ctx))
            graphic = GraphicContainer(
                shade_help,
                min_pt,
                max_pt,
                l_par_shd,
                GenericType("Shade Helpfulness", "hrs/m2"),
                "hrs/m2",
            )
            title_obj = DisplayText3D(
                "Shade Benefit",
                graphic.lower_title_location,
                graphic.legend_parameters.text_height,
                None,
                graphic.legend_parameters.font,
                "Left",
                "Top",
            )
            vis_set.add_geometry(ContextGeometry("Title", [title_obj]))

        vis_set.add_geometry(
            ContextGeometry(
                "Study_Points",
                [DisplayPoint3D(pt, color=Color(30, 120, 220), radius=3) for pt in study_pts],
            )
        )
        if include_context:
            _append_context_geometry(vis_set, ctx)

        total_helpful_hours = sum(
            val * area for val, area in zip(shade_help, shade_mesh.face_areas)
        )
        extra = {
            "study_type": "shade_benefit",
            "unit": "hrs/m2",
            "shade_face_count": len(shade_help),
            "study_point_count": pt_count,
            "sun_vector_count": len(sun_vecs),
            "min": min(shade_help) if shade_help else None,
            "max": max(shade_help) if shade_help else None,
            "mean": mean(shade_help) if shade_help else None,
            "total_helpful_hours": total_helpful_hours,
        }
        if include_values:
            extra["values"] = shade_help
        return _persist_study_vis_set(
            garden_root_path=garden_root_path,
            manifest=manifest,
            vis_set=vis_set,
            name=name or "shade_benefit",
            source={
                "producer": "LB_Run_Solar_Geometry_Study",
                "study_type": "shade_benefit",
                "model_target": res_model,
            },
            return_visualization_set=return_visualization_set,
            extra_summary=extra,
            message="Shade benefit study completed and VisualizationSet persisted.",
        )

    if kind == "thermal_shade_benefit":
        up_thresh = float(up_threshold)
        low_thresh = float(low_threshold)
        if up_thresh <= low_thresh:
            raise ValueError(
                f"up_threshold ({up_thresh}) must be greater than low_threshold ({low_thresh})."
            )
        loc_obj, epw_obj = _resolve_location_obj(
            garden_root_path=garden_root_path,
            manifest=manifest,
            location=location,
            weather_target=weather_target,
            epw_path=epw_path,
        )
        if temperature_target is not None:
            if temperature_target.get("target_type") == DATA_COLLECTION_TARGET_TYPE:
                temp_col = load_data_collection(
                    garden_root=garden_root_path, data_collection_target=temperature_target
                )
            else:
                raise ValueError(
                    f"temperature_target.target_type must be {DATA_COLLECTION_TARGET_TYPE!r}."
                )
        elif epw_obj is not None:
            temp_col = epw_obj.dry_bulb_temperature
        else:
            raise ValueError(
                "thermal_shade_benefit requires temperature_target or weather_target/epw_path."
            )

        if not isinstance(temp_col, HourlyDiscontinuousCollection):
            raise ValueError("temperature_target must be an hourly DataCollection.")
        if getattr(temp_col.header, "unit", "C") == "F":
            temp_col = temp_col.to_si()
        elif getattr(temp_col.header, "unit", "C") != "C":
            raise ValueError(f"temperature_target unit must be C; got {temp_col.header.unit!r}.")

        if analysis_period is not None:
            ap = analysis_period_from_input(analysis_period)
            if ap is not None:
                temp_col = temp_col.filter_by_analysis_period(ap)
        if hoys:
            temp_col = temp_col.filter_by_hoys([float(h) for h in hoys])

        eff_timestep = max(1, int(timestep))
        col_tstep = temp_col.header.analysis_period.timestep
        if eff_timestep != col_tstep:
            if eff_timestep < col_tstep:
                temp_col = temp_col.cull_to_timestep(eff_timestep)
            else:
                temp_col = temp_col.interpolate_to_timestep(eff_timestep)

        t_step_per_day = float(temp_col.header.analysis_period.timestep * 24)
        sp = Sunpath.from_location(loc_obj, north_angle=north_angle)
        relevant_vecs: list[Vector3D] = []
        relevant_temps: list[float] = []
        for dt, temp in zip(temp_col.datetimes, temp_col.values):
            t_val = float(temp)
            if t_val > up_thresh or t_val < low_thresh:
                sun = sp.calculate_sun_from_date_time(dt)
                if sun.is_during_day:
                    relevant_vecs.append(sun.sun_vector_reversed)
                    relevant_temps.append(t_val)

        shade_mesh, study_pts, study_dirs, ctx, res_model = _resolve_shade_and_study_points(
            garden_root_path=garden_root_path,
            shade_geometry=shade_geometry,
            study_region=study_region,
            study_points=study_points,
            study_directions=study_directions,
            study_mesh=study_mesh,
            study_face=study_face,
            context_geometry=context_geometry,
            model_target=model_target,
            study_face_targets=study_face_targets,
            study_room_targets=study_room_targets,
            face_type_filter=face_type_filter,
            grid_size=grid_size,
            center_point=center_point,
            region_grid_divisor=2.0,
        )
        if relevant_vecs:
            shade_tris = triangulate_geometry([shade_mesh])
            ctx_tris = triangulate_geometry(ctx) if ctx else None
            face_int = intersect_rays_with_mesh_faces(
                shade_tris,
                study_pts,
                relevant_vecs,
                context_tris=ctx_tris,
                normals=study_dirs,
            )
        else:
            face_int = [[] for _ in shade_mesh.face_areas]

        pt_div = 1.0 / float(len(study_pts))
        shade_help: list[float] = []
        shade_harm: list[float] = []
        shade_net: list[float] = []
        for face_res, face_area in zip(face_int, shade_mesh.face_areas):
            f_help = 0.0
            f_harm = 0.0
            for t_idx in face_res:
                t_val = relevant_temps[t_idx]
                if t_val > up_thresh:
                    f_help += t_val - up_thresh
                elif t_val < low_thresh:
                    f_harm += t_val - low_thresh
            if face_area > 0:
                shd_help = ((f_help / face_area) / t_step_per_day) * pt_div
                shd_harm = ((f_harm / face_area) / t_step_per_day) * pt_div
            else:
                shd_help = 0.0
                shd_harm = 0.0
            shade_help.append(shd_help)
            shade_harm.append(shd_harm)
            shade_net.append(shd_help + shd_harm)

        l_par_net = l_par.duplicate() if l_par is not None else LegendParameters()
        if l_par_net.are_colors_default:
            l_par_net.colors = list(reversed(Colorset.shade_benefit_harm()))
        bnd_val = max(max(shade_net, default=0.0), abs(min(shade_net, default=0.0)))
        if bnd_val <= 0.0:
            bnd_val = 1.0
        if l_par_net.min is None:
            l_par_net.min = -bnd_val
        if l_par_net.max is None:
            l_par_net.max = bnd_val
        if l_par_net.is_title_default:
            l_par_net.title = "degC-days/m2"

        l_par_help = LegendParameters(
            min=0.0,
            max=max(shade_help) if (shade_help and max(shade_help) > 0.0) else 1.0,
            colors=Colorset.shade_benefit(),
            title="degC-days/m2",
        )
        l_par_harm = LegendParameters(
            min=min(shade_harm) if (shade_harm and min(shade_harm) < 0.0) else -1.0,
            max=0.0,
            colors=Colorset.shade_harm(),
            title="degC-days/m2",
        )
        vis_net = VisualizationData(
            shade_net, l_par_net, GenericType("Thermal Shade Net Benefit", "degC-days/m2"), "degC-days/m2"
        )
        vis_help = VisualizationData(
            shade_help, l_par_help, GenericType("Thermal Shade Helpfulness", "degC-days/m2"), "degC-days/m2"
        )
        vis_harm = VisualizationData(
            shade_harm, l_par_harm, GenericType("Thermal Shade Harmfulness", "degC-days/m2"), "degC-days/m2"
        )
        mesh_geo = AnalysisGeometry(
            "Thermal_Shade_Benefit",
            [shade_mesh],
            [vis_net, vis_help, vis_harm],
            active_data=0,
        )
        mesh_geo.display_name = "Thermal Shade Benefit"
        mesh_geo.display_mode = "Surface"
        vis_set = VisualizationSet("ThermalShadeBenefit", [mesh_geo])
        vis_set.display_name = "Thermal Shade Benefit"

        if include_title:
            min_pt, max_pt = bounding_box((shade_mesh,) + tuple(ctx))
            graphic = GraphicContainer(
                shade_net,
                min_pt,
                max_pt,
                l_par_net,
                GenericType("Thermal Shade Net Benefit", "degC-days/m2"),
                "degC-days/m2",
            )
            title_obj = DisplayText3D(
                "Thermal Shade Benefit",
                graphic.lower_title_location,
                graphic.legend_parameters.text_height,
                None,
                graphic.legend_parameters.font,
                "Left",
                "Top",
            )
            vis_set.add_geometry(ContextGeometry("Title", [title_obj]))

        vis_set.add_geometry(
            ContextGeometry(
                "Study_Points",
                [DisplayPoint3D(pt, color=Color(30, 120, 220), radius=3) for pt in study_pts],
            )
        )
        if include_context:
            _append_context_geometry(vis_set, ctx)

        total_net_dd = sum(v * a for v, a in zip(shade_net, shade_mesh.face_areas))
        total_help_dd = sum(v * a for v, a in zip(shade_help, shade_mesh.face_areas))
        total_harm_dd = sum(v * a for v, a in zip(shade_harm, shade_mesh.face_areas))
        extra = {
            "study_type": "thermal_shade_benefit",
            "unit": "degC-days/m2",
            "up_threshold": up_thresh,
            "low_threshold": low_thresh,
            "shade_face_count": len(shade_net),
            "study_point_count": len(study_pts),
            "relevant_sun_vector_count": len(relevant_vecs),
            "net_min": min(shade_net) if shade_net else None,
            "net_max": max(shade_net) if shade_net else None,
            "net_mean": mean(shade_net) if shade_net else None,
            "help_max": max(shade_help) if shade_help else None,
            "help_mean": mean(shade_help) if shade_help else None,
            "harm_min": min(shade_harm) if shade_harm else None,
            "harm_mean": mean(shade_harm) if shade_harm else None,
            "total_net_degree_days": total_net_dd,
            "total_help_degree_days": total_help_dd,
            "total_harm_degree_days": total_harm_dd,
        }
        if include_values:
            extra["shade_net"] = shade_net
            extra["shade_help"] = shade_help
            extra["shade_harm"] = shade_harm
        return _persist_study_vis_set(
            garden_root_path=garden_root_path,
            manifest=manifest,
            vis_set=vis_set,
            name=name or "thermal_shade_benefit",
            source={
                "producer": "LB_Run_Solar_Geometry_Study",
                "study_type": "thermal_shade_benefit",
                "model_target": res_model,
            },
            return_visualization_set=return_visualization_set,
            extra_summary=extra,
            message="Thermal shade benefit study completed and VisualizationSet persisted.",
        )

    if kind == "surface_ray_tracing":
        eff_bounces = int(bounce_count)
        if eff_bounces < 1:
            raise ValueError(f"bounce_count must be >= 1; got {eff_bounces}.")
        res_mesh, ctx, res_model = _resolve_study_geometry(
            garden_root_path=garden_root_path,
            study_mesh=study_mesh,
            study_face=study_face,
            context_geometry=context_geometry,
            model_target=model_target,
            study_face_targets=study_face_targets,
            study_room_targets=study_room_targets,
            face_type_filter=face_type_filter,
            grid_size=grid_size,
            require_study_mesh=False,
        )
        if source_geometry:
            source_mesh = _mesh_from_geometry_list(source_geometry, grid_size)
        elif res_mesh is not None:
            source_mesh = res_mesh
        else:
            raise ValueError(
                "surface_ray_tracing requires source_geometry, study_mesh, study_face, or model_target."
            )
        sun_vecs = _resolve_sun_vectors(
            garden_root_path=garden_root_path,
            manifest=manifest,
            vectors=vectors,
            location=location,
            weather_target=weather_target,
            epw_path=epw_path,
            hoys=hoys,
            analysis_period=analysis_period,
            north_angle=north_angle,
            solar_time=solar_time,
        )
        all_geos: list[Face3D | Mesh3D] = [source_mesh] + list(ctx)
        min_pt, max_pt = bounding_box(all_geos)
        diag_dist = float(max_pt.distance_to_point(min_pt))
        if diag_dist <= 0.0:
            diag_dist = 10.0
        eff_first = float(first_length) if first_length is not None else diag_dist
        eff_last = float(last_length) if last_length is not None else diag_dist

        all_tris = triangulate_geometry(all_geos)
        ctx_tris = triangulate_geometry(ctx) if ctx else None
        receiver_geos = [_coerce_context_item(r) for r in (receiver_geometry or [])]
        rec_tris = triangulate_geometry(receiver_geos) if receiver_geos else None

        src_centroids = list(source_mesh.face_centroids)
        src_normals = list(source_mesh.face_normals)
        cutoff_ang = math.pi / 2.0

        ray_paths: list[list[Point3D]] = []
        hit_point_groups: list[list[Point3D]] = []

        for sun_vec in sun_vecs:
            lb_vec = sun_vec.normalize()
            neg_lb_vec = -lb_vec
            for centroid, norm in zip(src_centroids, src_normals):
                if norm.angle(neg_lb_vec) >= cutoff_ang:
                    continue
                if context_block and ctx_tris is not None and ctx_tris.triangle_count > 0:
                    check_pt = centroid.move(norm * 1e-4)
                    blk_mtx, _ = intersect_mesh_rays(ctx_tris, [check_pt], [neg_lb_vec])
                    if blk_mtx[0][0] == 0:
                        continue
                origin = centroid + (neg_lb_vec * eff_first)
                all_pts, hit_pts = trace_ray_bounces(
                    all_tris,
                    origin,
                    lb_vec,
                    max_hits=eff_bounces + 1,
                    last_length=eff_last,
                )
                if len(all_pts) < 2:
                    continue
                if rec_tris is not None and rec_tris.triangle_count > 0:
                    seg_vec = all_pts[-1] - all_pts[-2]
                    seg_len = float(seg_vec.magnitude)
                    if seg_len <= 0.0:
                        continue
                    rec_dists = intersect_mesh_rays_distance(
                        rec_tris, all_pts[-2], [seg_vec.normalize()]
                    )
                    if not (0.0 < rec_dists[0] <= seg_len + 1e-3):
                        continue
                ray_paths.append(all_pts)
                hit_point_groups.append(hit_pts)

        ray_display_objs: list[Any] = []
        ray_color = Color(255, 195, 0)
        for pts in ray_paths:
            if len(pts) == 2:
                ray_display_objs.append(
                    DisplayLineSegment3D(
                        LineSegment3D.from_end_points(pts[0], pts[1]),
                        color=ray_color,
                        line_width=2,
                    )
                )
            elif len(pts) >= 3:
                ray_display_objs.append(
                    DisplayPolyline3D(Polyline3D(pts), color=ray_color, line_width=2)
                )

        flat_hits = [pt for grp in hit_point_groups for pt in grp]
        pt_display_objs = [
            DisplayPoint3D(pt, color=Color(220, 50, 40), radius=3) for pt in flat_hits
        ]

        vis_set = VisualizationSet("SurfaceRayTracing", ())
        vis_set.display_name = "Surface Ray Tracing"
        vis_set.add_geometry(ContextGeometry("Sun_Rays", ray_display_objs))
        vis_set.add_geometry(ContextGeometry("Intersection_Points", pt_display_objs))
        vis_set.add_geometry(
            ContextGeometry(
                "Source_Geometry",
                [DisplayMesh3D(source_mesh, Color(180, 210, 240, 180))],
            )
        )
        if include_context:
            _append_context_geometry(vis_set, ctx)
        if receiver_geos:
            rec_color = Color(80, 190, 120, 140)
            vis_set.add_geometry(
                ContextGeometry(
                    "Receiver_Geometry",
                    [
                        DisplayMesh3D(g, rec_color) if isinstance(g, Mesh3D) else DisplayFace3D(g, rec_color)
                        for g in receiver_geos
                    ],
                )
            )

        ray_count = len(ray_paths)
        total_intersections = len(flat_hits)
        avg_segs = (
            sum(len(p) - 1 for p in ray_paths) / ray_count if ray_count > 0 else 0.0
        )
        extra = {
            "study_type": "surface_ray_tracing",
            "bounce_count": eff_bounces,
            "context_block": bool(context_block),
            "first_length": eff_first,
            "last_length": eff_last,
            "sun_vector_count": len(sun_vecs),
            "source_point_count": len(src_centroids),
            "ray_count": ray_count,
            "total_intersections": total_intersections,
            "avg_segments_per_ray": avg_segs,
            "receiver_filtered": bool(receiver_geos),
        }
        if include_values:
            extra["rays"] = [[[p.x, p.y, p.z] for p in path] for path in ray_paths]
            extra["intersection_points"] = [
                [[p.x, p.y, p.z] for p in grp] for grp in hit_point_groups
            ]
        return _persist_study_vis_set(
            garden_root_path=garden_root_path,
            manifest=manifest,
            vis_set=vis_set,
            name=name or "surface_ray_tracing",
            source={
                "producer": "LB_Run_Solar_Geometry_Study",
                "study_type": "surface_ray_tracing",
                "model_target": res_model,
            },
            return_visualization_set=return_visualization_set,
            extra_summary=extra,
            message="Surface ray tracing study completed and VisualizationSet persisted.",
        )

    if kind == "view_percent":
        canon_vt = _normalize_view_type(view_type)
        eff_res = max(1, int(resolution))
        mesh, ctx, res_model = _resolve_study_geometry(
            garden_root_path=garden_root_path,
            study_mesh=study_mesh,
            study_face=study_face,
            context_geometry=context_geometry,
            model_target=model_target,
            study_face_targets=study_face_targets,
            study_room_targets=study_room_targets,
            face_type_filter=face_type_filter,
            grid_size=grid_size,
        )
        eff_offset = float(offset_distance) if offset_distance != 0 else 0.1
        norms = list(mesh.face_normals)
        pts = [pt.move(vec * eff_offset) for pt, vec in zip(mesh.face_centroids, norms)]

        vs = ViewSphere()
        patch_weights: list[float] | None = None
        if canon_vt == "HorizontalRadial":
            view_vecs = list(vs.horizontal_radial_vectors(30 * eff_res))
        elif canon_vt == "Horizontal30DegreeOffset":
            _, raw_vecs = vs.horizontal_radial_patches(30, eff_res)
            view_vecs = list(raw_vecs)
            patch_weights = list(vs.horizontal_radial_patch_weights(30, eff_res))
        elif canon_vt == "Spherical":
            _, raw_vecs = vs.sphere_patches(eff_res)
            view_vecs = list(raw_vecs)
            patch_weights = list(vs.sphere_patch_weights(eff_res))
        else:  # SkyExposure / SkyView
            _, raw_vecs = vs.dome_patches(eff_res)
            view_vecs = list(raw_vecs)
            patch_weights = list(vs.dome_patch_weights(eff_res))

        eff_geo_block = (canon_vt in {"SkyExposure", "SkyView"}) if geo_block is None else bool(geo_block)
        block_geos: list[Face3D | Mesh3D] = ([mesh] + list(ctx)) if eff_geo_block else list(ctx)
        block_tris = triangulate_geometry(block_geos)

        int_mtx, angles_mtx = intersect_mesh_rays(
            block_tris,
            pts,
            view_vecs,
            normals=norms if canon_vt == "SkyView" else None,
        )
        vec_count = len(view_vecs)
        results: list[float] = []
        if canon_vt == "SkyView" and angles_mtx is not None and patch_weights is not None:
            for int_vals, angs in zip(int_mtx, angles_mtx):
                w_res = (
                    (iv * 2.0 * max(0.0, math.cos(ang))) * w
                    for iv, ang, w in zip(int_vals, angs, patch_weights)
                )
                results.append(max(0.0, min(100.0, sum(w_res) * 100.0 / vec_count)))
        elif patch_weights is not None:
            for int_vals in int_mtx:
                val = sum(iv * w for iv, w in zip(int_vals, patch_weights)) * 100.0 / vec_count
                results.append(max(0.0, min(100.0, val)))
        else:
            for int_vals in int_mtx:
                results.append(max(0.0, min(100.0, sum(int_vals) * 100.0 / vec_count)))

        l_par_vp = l_par.duplicate() if l_par is not None else LegendParameters()
        if l_par_vp.are_colors_default:
            l_par_vp.colors = Colorset.view_study()
        if l_par_vp.min is None:
            l_par_vp.min = 0.0
        if l_par_vp.max is None:
            l_par_vp.max = 100.0
        if l_par_vp.is_title_default:
            l_par_vp.title = "%"

        title_map = {
            "HorizontalRadial": "Horizontal Radial View",
            "Horizontal30DegreeOffset": "Horizontal 30-Degree Offset View",
            "Spherical": "Spherical View",
            "SkyExposure": "Sky Exposure",
            "SkyView": "Sky View",
        }
        title_txt = title_map[canon_vt]
        vis_data = VisualizationData(results, l_par_vp, Fraction(title_txt), "%")
        mesh_geo = AnalysisGeometry("View_Percent", [mesh], [vis_data])
        mesh_geo.display_name = title_txt
        mesh_geo.display_mode = "Surface"
        vis_set = VisualizationSet("ViewPercent", [mesh_geo])
        vis_set.display_name = title_txt

        if include_title:
            min_pt, max_pt = bounding_box((mesh,) + tuple(ctx))
            graphic = GraphicContainer(
                results, min_pt, max_pt, l_par_vp, Fraction(title_txt), "%"
            )
            title_obj = DisplayText3D(
                title_txt,
                graphic.lower_title_location,
                graphic.legend_parameters.text_height,
                None,
                graphic.legend_parameters.font,
                "Left",
                "Top",
            )
            vis_set.add_geometry(ContextGeometry("Title", [title_obj]))

        if include_context:
            _append_context_geometry(vis_set, ctx)

        rose_summary: dict[str, Any] | None = None
        if include_view_rose:
            if center_point is not None:
                rose_cpt = _coerce_point3d(center_point, "center_point")
            elif pts:
                rose_cpt = Point3D(
                    mean(p.x for p in pts),
                    mean(p.y for p in pts),
                    mean(p.z for p in pts),
                )
            else:
                rose_cpt = Point3D(0.0, 0.0, 0.0)
            rose_vis_set, rose_summary, _ = _compute_view_rose_data(
                view_type=canon_vt,
                resolution=eff_res,
                center_point=rose_cpt,
                radius=float(radius),
                ctx_geometries=block_geos,
                legend_parameters=l_par,
                draw_view_rays=draw_view_rays,
            )
            for geo in rose_vis_set.geometry:
                if isinstance(geo, AnalysisGeometry):
                    geo.identifier = "View_Rose"
                    geo.display_name = "View Rose"
                elif geo.identifier == "View_Rays":
                    geo.identifier = "View_Rose_Rays"
                    geo.display_name = "View Rose Rays"
                vis_set.add_geometry(geo)

        extra = {
            "study_type": "view_percent",
            "view_type": canon_vt,
            "resolution": eff_res,
            "geo_block": eff_geo_block,
            "offset_distance": eff_offset,
            "point_count": len(pts),
            "vector_count": vec_count,
            "unit": "%",
            "min": min(results) if results else None,
            "max": max(results) if results else None,
            "mean": mean(results) if results else None,
        }
        if rose_summary is not None:
            extra["view_rose"] = rose_summary
        if include_values:
            extra["values"] = results
        return _persist_study_vis_set(
            garden_root_path=garden_root_path,
            manifest=manifest,
            vis_set=vis_set,
            name=name or "view_percent",
            source={
                "producer": "LB_Run_Solar_Geometry_Study",
                "study_type": "view_percent",
                "view_type": canon_vt,
                "model_target": res_model,
            },
            return_visualization_set=return_visualization_set,
            extra_summary=extra,
            message="View percent study completed and VisualizationSet persisted.",
        )

    if kind == "view_rose":
        canon_vt = _normalize_view_type(view_type)
        eff_res = max(1, int(resolution))
        _, ctx, res_model = _resolve_study_geometry(
            garden_root_path=garden_root_path,
            study_mesh=study_mesh,
            study_face=study_face,
            context_geometry=context_geometry,
            model_target=model_target,
            study_face_targets=study_face_targets,
            study_room_targets=study_room_targets,
            face_type_filter=face_type_filter,
            grid_size=grid_size,
            require_study_mesh=False,
        )
        cpt = _coerce_point3d(center_point, "center_point") if center_point is not None else Point3D(0.0, 0.0, 0.0)
        vis_set, rose_summary, distances = _compute_view_rose_data(
            view_type=canon_vt,
            resolution=eff_res,
            center_point=cpt,
            radius=float(radius),
            ctx_geometries=ctx,
            legend_parameters=l_par,
            draw_view_rays=draw_view_rays,
        )
        if include_context:
            _append_context_geometry(vis_set, ctx)
        extra = {
            "study_type": "view_rose",
            **rose_summary,
        }
        if include_values:
            extra["values"] = distances
        return _persist_study_vis_set(
            garden_root_path=garden_root_path,
            manifest=manifest,
            vis_set=vis_set,
            name=name or "view_rose",
            source={
                "producer": "LB_Run_Solar_Geometry_Study",
                "study_type": "view_rose",
                "view_type": rose_summary["view_type"],
                "model_target": res_model,
            },
            return_visualization_set=return_visualization_set,
            extra_summary=extra,
            message="View rose study completed and VisualizationSet persisted.",
        )

    raise ValueError(
        "study_type must be one of: direct_sun, radiation, solar_envelope, sky_intersection, "
        "view_sphere, shade_benefit, thermal_shade_benefit, surface_ray_tracing, view_percent, view_rose."
    )


__all__ = ["run_solar_geometry_study"]
