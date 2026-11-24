"""Sunpath, sky dome, radiation dome/rose, wind profile, view sphere, and compass VisualizationSet services."""

from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

from ladybug.compass import Compass
from ladybug.epw import EPW
from ladybug.location import Location
from ladybug.sunpath import Sunpath
from ladybug.viewsphere import ViewSphere
from ladybug.wea import Wea
from ladybug.windprofile import WindProfile
from ladybug_display.extension.compass import compass_to_vis_set
from ladybug_display.extension.raddome import radiation_dome_to_vis_set
from ladybug_display.extension.radrose import radiation_rose_to_vis_set
from ladybug_display.extension.skydome import sky_dome_to_vis_set
from ladybug_display.extension.sunpath import sunpath_to_vis_set
from ladybug_display.extension.viewsphere import view_sphere_to_vis_set
from ladybug_display.extension.windprofile import wind_profile_to_vis_set
from ladybug_geometry.geometry2d.pointvector import Point2D
from ladybug_geometry.geometry3d.pointvector import Point3D
from ladybug_radiance.intersection import sky_intersection_matrix
from ladybug_radiance.skymatrix import SkyMatrix
from ladybug_radiance.visualize.raddome import RadiationDome
from ladybug_radiance.visualize.radrose import RadiationRose
from ladybug_radiance.visualize.skydome import SkyDome

from garden.data_collection import collection_from_dict, load_data_collection
from garden.honeybee_core.model_io import load_honeybee_model, resolve_model_target
from garden.manifest import GardenManifest
from garden.paths import slugify_name, to_posix_relative
from garden.radiance.sky import SKY_MATRIX_TARGET_TYPE
from garden.run_energy.config import WEATHER_TARGET_TYPE
from garden.visualize.artifacts import coerce_legend_parameter, save_visualization_set
from ladybug_tools_mcp.contracts import make_report

PROJECTIONS = {
    "orthographic": "Orthographic",
    "stereographic": "Stereographic",
    "equidistant": "Equidistant",
    "equisolid": "Equisolid",
}


def _garden_root(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _unwrap_target(target: dict[str, Any] | None) -> dict[str, Any] | None:
    if isinstance(target, dict) and isinstance(target.get("target"), dict):
        return target["target"]
    return target


def _validate_target_garden(
    *,
    target: dict[str, Any],
    manifest: GardenManifest,
    field_name: str,
) -> None:
    garden_id = target.get("garden_id")
    if garden_id and garden_id != manifest.garden_id:
        raise ValueError(f"{field_name} belongs to a different Garden.")


def _garden_relative_file(
    garden_root: Path,
    value: str,
    *,
    field_name: str,
    suffix: str | None = None,
) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = garden_root / path
    path = path.resolve()
    try:
        path.relative_to(garden_root)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be inside the Garden root.") from exc
    if not path.is_file():
        raise ValueError(f"{field_name} must reference an existing file.")
    if suffix is not None and path.suffix.lower() != suffix:
        raise ValueError(f"{field_name} must reference a {suffix} file.")
    return path


def _location_from_dict(location: dict[str, Any]) -> Location:
    if not isinstance(location, dict):
        raise ValueError("location must be a Ladybug Location dictionary.")
    data = dict(location)
    data.setdefault("type", "Location")
    try:
        return Location.from_dict(data)
    except Exception as exc:
        raise ValueError(f"Invalid Ladybug Location input. {exc}") from exc


def _resolve_epw_path(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
) -> tuple[Path, dict[str, Any]]:
    weather_target = _unwrap_target(weather_target)
    if (weather_target is None) == (epw_path is None):
        raise ValueError("Provide exactly one of weather_target or epw_path.")
    if weather_target is not None:
        if weather_target.get("target_type") != WEATHER_TARGET_TYPE:
            raise ValueError("weather_target must be a Garden weather_file target.")
        _validate_target_garden(
            target=weather_target,
            manifest=manifest,
            field_name="weather_target",
        )
        epw_value = weather_target.get("epw_path")
        if not isinstance(epw_value, str) or not epw_value:
            raise ValueError("weather_target requires an epw_path.")
        epw = _garden_relative_file(
            garden_root,
            epw_value,
            field_name="weather_target.epw_path",
            suffix=".epw",
        )
        return epw, {"source_type": "weather_file", "weather_target": weather_target}
    epw = _garden_relative_file(
        garden_root,
        str(epw_path),
        field_name="epw_path",
        suffix=".epw",
    )
    return epw, {"source_type": "epw_path", "epw_path": to_posix_relative(epw, garden_root)}


def _resolve_location(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    location: dict[str, Any] | None,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
) -> tuple[Location, dict[str, Any]]:
    sources = [location is not None, weather_target is not None or epw_path is not None]
    if sum(1 for item in sources if item) != 1:
        raise ValueError("Provide exactly one sunpath source: location, weather_target, or epw_path.")
    if location is not None:
        location_obj = _location_from_dict(location)
        return location_obj, {
            "source_type": "location",
            "location": location_obj.to_dict(),
        }
    epw, source = _resolve_epw_path(
        garden_root=garden_root,
        manifest=manifest,
        weather_target=weather_target,
        epw_path=epw_path,
    )
    location_obj = EPW(str(epw)).location
    source["location"] = location_obj.to_dict()
    return location_obj, source


def _sky_matrix_from_target(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    sky_matrix_target: dict[str, Any],
) -> tuple[SkyMatrix, dict[str, Any], dict[str, Any]]:
    target = _unwrap_target(sky_matrix_target) or {}
    if target.get("target_type") != SKY_MATRIX_TARGET_TYPE:
        raise ValueError("sky_matrix_target must be a sky_matrix target.")
    _validate_target_garden(
        target=target,
        manifest=manifest,
        field_name="sky_matrix_target",
    )
    path_value = target.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("sky_matrix_target requires a Garden-relative path.")
    sky_path = _garden_relative_file(
        garden_root,
        path_value,
        field_name="sky_matrix_target.path",
        suffix=".json",
    )
    payload = json.loads(sky_path.read_text(encoding="utf-8"))
    source = dict(payload.get("source") or {})
    parameters = dict(payload.get("parameters") or {})
    source_type = str(source.get("source_type") or "")
    cached_direct = payload.get("direct_values")
    cached_diffuse = payload.get("diffuse_values")
    has_cached = cached_direct is not None and cached_diffuse is not None
    hoys = payload.get("hoys") if "hoys" in payload else source.get("hoys")
    benefit_matrix = (
        payload.get("benefit_matrix")
        if "benefit_matrix" in payload
        else source.get("benefit_matrix")
    )

    wea: Wea | None = None
    if source_type == "wea_file":
        wea_path = _garden_relative_file(
            garden_root,
            str(source.get("wea_path")),
            field_name="sky_matrix.source.wea_path",
            suffix=".wea",
        )
        wea = Wea.from_file(str(wea_path))
    elif source_type in {"weather_file", "epw_path"}:
        epw_rel = source.get("epw_path") or (source.get("weather_target") or {}).get("epw_path")
        if epw_rel:
            epw_path = _garden_relative_file(
                garden_root,
                str(epw_rel),
                field_name="sky_matrix.source.epw_path",
                suffix=".epw",
            )
            wea = Wea.from_epw_file(str(epw_path))
    elif source_type == "stat_file":
        stat_path = _garden_relative_file(
            garden_root,
            str(source.get("stat_path")),
            field_name="sky_matrix.source.stat_path",
            suffix=".stat",
        )
        wea = Wea.from_stat_file(str(stat_path))
    elif source_type == "ashrae_clear_sky":
        location = _location_from_dict(source.get("location") or {})
        wea = Wea.from_ashrae_clear_sky(
            location,
            sky_clearness=float(source.get("sky_clearness", 1)),
        )
    elif has_cached and isinstance(source.get("location"), dict):
        wea = Wea.from_ashrae_clear_sky(_location_from_dict(source["location"]))
    elif has_cached:
        wea = Wea.from_ashrae_clear_sky(Location())
    else:
        raise ValueError(f"Unsupported sky_matrix source_type: {source_type}.")

    if wea is None:
        if has_cached:
            wea = Wea.from_ashrae_clear_sky(
                _location_from_dict(source["location"])
                if isinstance(source.get("location"), dict)
                else Location()
            )
        else:
            raise ValueError(f"Could not resolve Wea source for sky_matrix source_type={source_type!r}.")

    if hoys:
        wea = wea.filter_by_hoys(hoys)

    north = float(parameters.get("north", 0))
    high_density = bool(parameters.get("high_density", False))
    ground_reflectance = float(parameters.get("ground_reflectance", 0.2))
    sky_matrix = SkyMatrix(
        wea,
        north=north,
        high_density=high_density,
        ground_reflectance=ground_reflectance,
    )
    if isinstance(benefit_matrix, (list, tuple)):
        if len(benefit_matrix) == len(wea):
            sky_matrix.benefit_matrix = list(benefit_matrix)
        else:
            sky_matrix._benefit_matrix = list(benefit_matrix)

    if has_cached:
        sky_matrix._direct_values = tuple(float(v) for v in cached_direct)
        sky_matrix._diffuse_values = tuple(float(v) for v in cached_diffuse)
        dts = wea.direct_normal_irradiance.datetimes
        meta_list: list[Any] = [north, ground_reflectance, dts[0], dts[-1]]
        cached_meta = payload.get("metadata")
        if isinstance(cached_meta, list) and len(cached_meta) > 4:
            meta_list.extend(str(item) for item in cached_meta[4:])
        else:
            for key, val in wea.direct_normal_irradiance.header.metadata.items():
                meta_list.append(f"{key} : {val}")
        sky_matrix._metadata = tuple(meta_list)

    return sky_matrix, target, payload


def _projection(value: str | None) -> str | None:
    if value is None:
        return None
    key = value.strip().lower()
    if key not in PROJECTIONS:
        allowed = ", ".join(sorted(PROJECTIONS.values()))
        raise ValueError(f"Unsupported projection: {value}. Allowed values: {allowed}.")
    return PROJECTIONS[key]


def _point3d(value: dict[str, Any] | list[float] | tuple[float, ...] | None) -> Point3D:
    if value is None:
        return Point3D(0, 0, 0)
    if isinstance(value, dict):
        return Point3D(
            float(value.get("x", value.get("x_coordinate", 0))),
            float(value.get("y", value.get("y_coordinate", 0))),
            float(value.get("z", value.get("z_coordinate", 0))),
        )
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return Point3D(float(value[0]), float(value[1]), float(value[2]))
    raise ValueError("center_point must be a dict with x/y/z or a 3-item list.")


def _model_context_faces(garden_root_path: Path, model_target: dict[str, Any]) -> tuple[list[Any], dict[str, Any]]:
    _, resolved_target = resolve_model_target(garden_root_path, model_target)
    model = load_honeybee_model(garden_root_path, resolved_target)
    context_geos: list[Any] = []
    for room in model.rooms:
        for face in room.faces:
            context_geos.append(face.geometry)
            for sh in face.shades:
                context_geos.append(sh.geometry)
        for sh in room.shades:
            context_geos.append(sh.geometry)
    for face in model.orphaned_faces:
        context_geos.append(face.geometry)
        for sh in face.shades:
            context_geos.append(sh.geometry)
    for sh in model.shades:
        context_geos.append(sh.geometry)
    if not context_geos:
        raise ValueError("model_target contains no Face3D or Shade geometry for shading intersection.")
    return context_geos, resolved_target


def _compute_sky_intersection(
    *,
    sky_matrix: SkyMatrix,
    center: Point3D,
    vectors: tuple[Any, ...] | list[Any],
    context_geometry: list[Any],
) -> Any:
    if sky_matrix.north != 0:
        na = math.radians(sky_matrix.north)
        normals = [v.rotate_xy(na) for v in vectors]
    else:
        normals = list(vectors)
    points = [center] * len(normals)
    saved_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as sim_dir:
            return sky_intersection_matrix(
                sky_matrix,
                points,
                normals,
                context_geometry,
                numericalize=False,
                sim_folder=sim_dir,
            )
    finally:
        os.chdir(saved_cwd)


def _set_visualization_set_name(vis_set: Any, name: str) -> str:
    safe_name = slugify_name(name)
    vis_set.identifier = safe_name
    vis_set.display_name = name
    return safe_name


def _visualization_summary(visualization_set: dict[str, Any]) -> dict[str, Any]:
    geometry = visualization_set.get("geometry", []) or []
    identifiers = [
        item.get("identifier")
        for item in geometry
        if isinstance(item, dict) and item.get("identifier")
    ]
    return {
        "identifier": visualization_set.get("identifier"),
        "display_name": visualization_set.get("display_name"),
        "units": visualization_set.get("units"),
        "geometry_count": len(geometry),
        "geometry_identifiers": identifiers,
    }


def _visualization_response(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    visualization_set: dict[str, Any],
    name: str,
    source: dict[str, Any],
    message: str,
    return_visualization_set: bool,
    extra_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = _visualization_summary(visualization_set)
    summary.update(
        {
            "garden_target": manifest.target(),
            "source": source,
            "body_returned": return_visualization_set,
        }
    )
    if extra_summary:
        summary.update(extra_summary)
    result = {
        "visualization_set": visualization_set,
        "summary_view": summary,
        "report": make_report(status="ok", message=message),
    }
    if not return_visualization_set:
        saved = save_visualization_set(
            garden_root=str(garden_root),
            visualization_set=visualization_set,
            name=name,
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


def sunpath_to_visualization_set(
    *,
    garden_root: str,
    location: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    north_angle: float = 0,
    hoys: list[float] | None = None,
    data_collection_targets: list[dict[str, Any]] | None = None,
    data_collections: list[dict[str, Any]] | None = None,
    legend_parameter: dict[str, Any] | None = None,
    legend_parameters: list[dict[str, Any]] | None = None,
    radius: float = 100,
    center_point: dict[str, Any] | list[float] | None = None,
    solar_time: bool = False,
    daily: bool = False,
    projection: str | None = None,
    sun_spheres: bool = False,
    name: str = "sunpath",
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a Ladybug Sunpath VisualizationSet with optional colored sun data."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    location_obj, source = _resolve_location(
        garden_root=garden_root_path,
        manifest=manifest,
        location=location,
        weather_target=weather_target,
        epw_path=epw_path,
    )
    resolved_data: list[Any] = []
    for tgt in data_collection_targets or []:
        resolved_data.append(
            load_data_collection(garden_root=garden_root_path, data_collection_target=tgt)
        )
    for item in data_collections or []:
        resolved_data.append(collection_from_dict(item))

    resolved_legend_pars: Any = None
    if legend_parameters:
        resolved_legend_pars = [coerce_legend_parameter(lp) for lp in legend_parameters]
    elif legend_parameter is not None:
        resolved_legend_pars = coerce_legend_parameter(legend_parameter)

    effective_hoys = hoys
    if not effective_hoys and resolved_data:
        effective_hoys = [dt.hoy for dt in resolved_data[0].datetimes]

    sunpath = Sunpath.from_location(location_obj, north_angle=north_angle)
    vis_set = sunpath_to_vis_set(
        sunpath,
        hoys=effective_hoys,
        data=resolved_data or None,
        legend_parameters=resolved_legend_pars,
        radius=radius,
        center_point=_point3d(center_point),
        solar_time=solar_time,
        daily=daily,
        projection=_projection(projection),
        sun_spheres=sun_spheres,
    )
    safe_name = _set_visualization_set_name(vis_set, name)
    visualization_set = vis_set.to_dict()
    proj_value = _projection(projection)
    source.update(
        {
            "tool": "sunpath_to_visualization_set",
            "north_angle": north_angle,
            "hoys": effective_hoys or [],
            "projection": proj_value,
            "data_collection_count": len(resolved_data),
        }
    )
    return _visualization_response(
        garden_root=garden_root_path,
        manifest=manifest,
        visualization_set=visualization_set,
        name=safe_name,
        source=source,
        message="Sunpath VisualizationSet created.",
        return_visualization_set=return_visualization_set,
        extra_summary={
            "location": location_obj.to_dict(),
            "projection": proj_value,
            "data_collection_count": len(resolved_data),
        },
    )


def sky_matrix_to_skydome_visualization_set(
    *,
    garden_root: str,
    sky_matrix_target: dict[str, Any],
    legend_parameter: dict[str, Any] | None = None,
    plot_irradiance: bool = False,
    radius: float = 100,
    center_point: dict[str, Any] | list[float] | None = None,
    projection: str | None = None,
    show_components: bool = False,
    include_title: bool = True,
    name: str = "sky_dome",
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a SkyDome VisualizationSet from a Garden SkyMatrix target."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    sky_matrix, target, payload = _sky_matrix_from_target(
        garden_root=garden_root_path,
        manifest=manifest,
        sky_matrix_target=sky_matrix_target,
    )
    sky_dome = SkyDome(
        sky_matrix,
        legend_parameters=coerce_legend_parameter(legend_parameter),
        plot_irradiance=plot_irradiance,
        center_point=_point3d(center_point),
        radius=radius,
        projection=_projection(projection),
    )
    vis_set = sky_dome_to_vis_set(
        sky_dome,
        show_components=show_components,
        include_title=include_title,
    )
    safe_name = _set_visualization_set_name(vis_set, name)
    visualization_set = vis_set.to_dict()
    proj_value = _projection(projection)
    used_cached = payload.get("direct_values") is not None and payload.get("diffuse_values") is not None
    source = {
        "tool": "sky_matrix_to_skydome_visualization_set",
        "sky_matrix_target": target,
        "sky_matrix_source": payload.get("source"),
        "plot_irradiance": plot_irradiance,
        "projection": proj_value,
        "used_cached_sky_matrix": used_cached,
    }
    return _visualization_response(
        garden_root=garden_root_path,
        manifest=manifest,
        visualization_set=visualization_set,
        name=safe_name,
        source=source,
        message="Sky dome VisualizationSet created.",
        return_visualization_set=return_visualization_set,
        extra_summary={
            "projection": proj_value,
            "used_cached_sky_matrix": used_cached,
        },
    )


def sky_matrix_to_radiation_dome_visualization_set(
    *,
    garden_root: str,
    sky_matrix_target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    azimuth_count: int = 72,
    altitude_count: int = 18,
    legend_parameter: dict[str, Any] | None = None,
    plot_irradiance: bool = False,
    radius: float = 100,
    center_point: dict[str, Any] | list[float] | None = None,
    projection: str | None = None,
    show_components: bool = False,
    include_title: bool = True,
    name: str = "radiation_dome",
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a cumulative or shaded RadiationDome VisualizationSet from a SkyMatrix target."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    sky_matrix, target, payload = _sky_matrix_from_target(
        garden_root=garden_root_path,
        manifest=manifest,
        sky_matrix_target=sky_matrix_target,
    )
    center = _point3d(center_point)
    int_mtx = None
    resolved_model_target = None
    if model_target is not None:
        context_geos, resolved_model_target = _model_context_faces(garden_root_path, model_target)
        dome_vecs = RadiationDome.dome_vectors(azimuth_count, altitude_count)
        int_mtx = _compute_sky_intersection(
            sky_matrix=sky_matrix,
            center=center,
            vectors=dome_vecs,
            context_geometry=context_geos,
        )

    radiation_dome = RadiationDome(
        sky_matrix,
        intersection_matrix=int_mtx,
        azimuth_count=azimuth_count,
        altitude_count=altitude_count,
        legend_parameters=coerce_legend_parameter(legend_parameter),
        plot_irradiance=plot_irradiance,
        center_point=center,
        radius=radius,
        projection=_projection(projection),
    )
    vis_set = radiation_dome_to_vis_set(
        radiation_dome,
        show_components=show_components,
        include_title=include_title,
    )
    safe_name = _set_visualization_set_name(vis_set, name)
    visualization_set = vis_set.to_dict()
    max_dir = [float(v) for v in radiation_dome.max_direction.to_array()]
    max_info = str(radiation_dome.max_info)
    proj_value = _projection(projection)
    used_cached = payload.get("direct_values") is not None and payload.get("diffuse_values") is not None
    total_rad = float(sum(radiation_dome.total_values)) if radiation_dome.total_values else 0.0
    source = {
        "tool": "sky_matrix_to_radiation_dome_visualization_set",
        "sky_matrix_target": target,
        "sky_matrix_source": payload.get("source"),
        "model_target": resolved_model_target,
        "shaded": model_target is not None,
        "mode": "cumulative",
        "azimuth_count": azimuth_count,
        "altitude_count": altitude_count,
        "plot_irradiance": plot_irradiance,
        "projection": proj_value,
        "used_cached_sky_matrix": used_cached,
    }
    return _visualization_response(
        garden_root=garden_root_path,
        manifest=manifest,
        visualization_set=visualization_set,
        name=safe_name,
        source=source,
        message="Cumulative radiation dome VisualizationSet created.",
        return_visualization_set=return_visualization_set,
        extra_summary={
            "mode": "cumulative",
            "shaded": model_target is not None,
            "azimuth_count": azimuth_count,
            "altitude_count": altitude_count,
            "projection": proj_value,
            "used_cached_sky_matrix": used_cached,
            "total_radiation": total_rad,
            "max_direction": max_dir,
            "max_info": max_info,
        },
    )


def sky_matrix_to_radiation_rose_visualization_set(
    *,
    garden_root: str,
    sky_matrix_target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    direction_count: int = 36,
    tilt_angle: float = 0.0,
    arrow_scale: float = 1.0,
    max_rad: float | None = None,
    legend_parameter: dict[str, Any] | None = None,
    plot_irradiance: bool = False,
    radius: float = 100,
    center_point: dict[str, Any] | list[float] | None = None,
    show_components: bool = False,
    include_title: bool = True,
    name: str = "radiation_rose",
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a RadiationRose VisualizationSet from a SkyMatrix target (with optional shading context)."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    sky_matrix, target, payload = _sky_matrix_from_target(
        garden_root=garden_root_path,
        manifest=manifest,
        sky_matrix_target=sky_matrix_target,
    )
    center = _point3d(center_point)
    int_mtx = None
    resolved_model_target = None
    if model_target is not None:
        context_geos, resolved_model_target = _model_context_faces(garden_root_path, model_target)
        rose_vecs = RadiationRose.radial_vectors(direction_count, tilt_angle=tilt_angle)
        int_mtx = _compute_sky_intersection(
            sky_matrix=sky_matrix,
            center=center,
            vectors=rose_vecs,
            context_geometry=context_geos,
        )

    rose = RadiationRose(
        sky_matrix,
        intersection_matrix=int_mtx,
        direction_count=direction_count,
        tilt_angle=tilt_angle,
        legend_parameters=coerce_legend_parameter(legend_parameter),
        plot_irradiance=plot_irradiance,
        center_point=center,
        radius=radius,
        arrow_scale=arrow_scale,
    )
    vis_set = radiation_rose_to_vis_set(
        rose,
        max_rad=max_rad,
        show_components=show_components,
        include_title=include_title,
    )
    safe_name = _set_visualization_set_name(vis_set, name)
    visualization_set = vis_set.to_dict()
    used_cached = payload.get("direct_values") is not None and payload.get("diffuse_values") is not None
    source = {
        "tool": "sky_matrix_to_radiation_rose_visualization_set",
        "sky_matrix_target": target,
        "sky_matrix_source": payload.get("source"),
        "model_target": resolved_model_target,
        "shaded": model_target is not None,
        "direction_count": direction_count,
        "tilt_angle": tilt_angle,
        "plot_irradiance": plot_irradiance,
        "used_cached_sky_matrix": used_cached,
    }
    return _visualization_response(
        garden_root=garden_root_path,
        manifest=manifest,
        visualization_set=visualization_set,
        name=safe_name,
        source=source,
        message="Radiation rose VisualizationSet created.",
        return_visualization_set=return_visualization_set,
        extra_summary={
            "direction_count": direction_count,
            "tilt_angle": tilt_angle,
            "shaded": model_target is not None,
            "used_cached_sky_matrix": used_cached,
            "max_total_value": max(rose.total_values) if rose.total_values else None,
            "min_total_value": min(rose.total_values) if rose.total_values else None,
        },
    )


def wind_profile_to_visualization_set(
    *,
    garden_root: str,
    terrain: str = "city",
    meteorological_terrain: str = "country",
    meteorological_height: float = 10.0,
    log_law: bool = False,
    meteorological_wind_speed: float = 5.0,
    direction: float | None = None,
    legend_parameter: dict[str, Any] | None = None,
    center_point: dict[str, Any] | list[float] | None = None,
    max_height: float = 30.0,
    vector_spacing: float = 2.0,
    vector_length_dimension: float = 5.0,
    vector_height_dimension: float = 1.0,
    max_speed: float | None = None,
    scale_factor: float = 1.0,
    feet_labels: bool = False,
    name: str = "wind_profile",
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a Ladybug WindProfile VisualizationSet."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    profile = WindProfile(
        terrain=terrain,
        meteorological_terrain=meteorological_terrain,
        meteorological_height=meteorological_height,
        log_law=log_law,
    )
    vis_set = wind_profile_to_vis_set(
        profile,
        meteorological_wind_speed=meteorological_wind_speed,
        direction=direction,
        legend_parameters=coerce_legend_parameter(legend_parameter),
        base_point=_point3d(center_point),
        max_height=max_height,
        vector_spacing=vector_spacing,
        vector_length_dimension=vector_length_dimension,
        vector_height_dimension=vector_height_dimension,
        max_speed=max_speed,
        scale_factor=scale_factor,
        feet_labels=feet_labels,
    )
    safe_name = _set_visualization_set_name(vis_set, name)
    visualization_set = vis_set.to_dict()
    source = {
        "tool": "wind_profile_to_visualization_set",
        "terrain": terrain,
        "meteorological_terrain": meteorological_terrain,
        "meteorological_height": meteorological_height,
        "log_law": log_law,
        "meteorological_wind_speed": meteorological_wind_speed,
    }
    return _visualization_response(
        garden_root=garden_root_path,
        manifest=manifest,
        visualization_set=visualization_set,
        name=safe_name,
        source=source,
        message="Wind profile VisualizationSet created.",
        return_visualization_set=return_visualization_set,
        extra_summary={"terrain": terrain, "max_height": max_height},
    )


def view_sphere_to_visualization_set(
    *,
    garden_root: str,
    view_type: str = "HorizontalRadial",
    resolution: int = 1,
    center_point: dict[str, Any] | list[float] | None = None,
    context_intersect_dist: list[float] | None = None,
    dist_units: str = "m",
    radius: float = 1.0,
    legend_parameter: dict[str, Any] | None = None,
    draw_view_rays: bool = True,
    name: str = "view_sphere",
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a Ladybug ViewSphere VisualizationSet."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    vs = ViewSphere()
    vis_set = view_sphere_to_vis_set(
        vs,
        view_type=view_type,
        resolution=resolution,
        center_point=_point3d(center_point),
        context_intersect_dist=context_intersect_dist,
        dist_units=dist_units,
        radius=radius,
        legend_parameters=coerce_legend_parameter(legend_parameter),
        draw_view_rays=draw_view_rays,
    )
    safe_name = _set_visualization_set_name(vis_set, name)
    visualization_set = vis_set.to_dict()
    source = {
        "tool": "view_sphere_to_visualization_set",
        "view_type": view_type,
        "resolution": resolution,
        "radius": radius,
    }
    return _visualization_response(
        garden_root=garden_root_path,
        manifest=manifest,
        visualization_set=visualization_set,
        name=safe_name,
        source=source,
        message="ViewSphere VisualizationSet created.",
        return_visualization_set=return_visualization_set,
        extra_summary={"view_type": view_type, "resolution": resolution},
    )


def compass_to_visualization_set(
    *,
    garden_root: str,
    radius: float = 100.0,
    center_point: dict[str, Any] | list[float] | None = None,
    north_angle: float = 0.0,
    spacing_factor: float = 0.15,
    custom_angles: list[float] | None = None,
    projection: str | None = None,
    font: str = "Arial",
    maj_txt_size: float | None = None,
    min_txt_size: float | None = None,
    name: str = "compass",
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a Ladybug Compass VisualizationSet."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    pt3 = _point3d(center_point)
    compass = Compass(
        radius=radius,
        center=Point2D(pt3.x, pt3.y),
        north_angle=north_angle,
        spacing_factor=spacing_factor,
    )
    vis_set = compass_to_vis_set(
        compass,
        z=pt3.z,
        custom_angles=custom_angles,
        projection=_projection(projection),
        font=font,
        maj_txt_size=maj_txt_size,
        min_txt_size=min_txt_size,
    )
    safe_name = _set_visualization_set_name(vis_set, name)
    visualization_set = vis_set.to_dict()
    source = {
        "tool": "compass_to_visualization_set",
        "radius": radius,
        "north_angle": north_angle,
        "projection": projection,
    }
    return _visualization_response(
        garden_root=garden_root_path,
        manifest=manifest,
        visualization_set=visualization_set,
        name=safe_name,
        source=source,
        message="Compass VisualizationSet created.",
        return_visualization_set=return_visualization_set,
    )
