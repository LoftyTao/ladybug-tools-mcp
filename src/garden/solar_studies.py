"""Ladybug and Ladybug-Radiance fast solar geometry study services."""

from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path
from statistics import mean
from typing import Any

from ladybug.color import Color, Colorset
from ladybug.datatype.fraction import Fraction
from ladybug.epw import EPW
from ladybug.location import Location
from ladybug.solarenvelope import SolarEnvelope
from ladybug.sunpath import Sunpath
from ladybug.viewsphere import ViewSphere
from ladybug_display.extension.study.directsun import direct_sun_study_to_vis_set
from ladybug_display.extension.study.radiation import radiation_study_to_vis_set
from ladybug_display.extension.viewsphere import view_sphere_to_vis_set
from ladybug_display.geometry3d import DisplayFace3D, DisplayMesh3D
from ladybug_display.visualization import ContextGeometry, VisualizationSet
from ladybug_geometry.geometry3d import Face3D, Mesh3D, Point3D, Vector3D
from ladybug_radiance.intersection import sky_intersection_matrix
from ladybug_radiance.skymatrix import SkyMatrix
from ladybug_radiance.study.directsun import DirectSunStudy
from ladybug_radiance.study.radiation import RadiationStudy

from garden.analysis_period import analysis_period_from_input
from garden.honeybee_core.locate import find_object
from garden.honeybee_core.model_io import load_honeybee_model, resolve_model_target
from garden.manifest import GardenManifest
from garden.paths import slugify_name
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
    # view_sphere / sky_intersection options
    view_type: str = "SkyExposure",
    resolution: int = 1,
    center_point: list[float] | dict[str, Any] | None = None,
    radius: float = 5.0,
    numericalize: bool = False,
    # output options
    legend_parameter: dict[str, Any] | None = None,
    include_title: bool = True,
    include_context: bool = True,
    include_values: bool = False,
    name: str | None = None,
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Run DirectSunStudy, RadiationStudy, SolarEnvelope, SkyIntersection, or ViewSphere study."""
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

    raise ValueError(
        "study_type must be one of: direct_sun, radiation, solar_envelope, sky_intersection, view_sphere."
    )


__all__ = ["run_solar_geometry_study"]
