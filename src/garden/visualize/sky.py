"""Sunpath, sky dome, and radiation dome VisualizationSet services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ladybug.epw import EPW
from ladybug.location import Location
from ladybug.sunpath import Sunpath
from ladybug.wea import Wea
from ladybug_display.extension.raddome import radiation_dome_to_vis_set
from ladybug_display.extension.skydome import sky_dome_to_vis_set
from ladybug_display.extension.sunpath import sunpath_to_vis_set
from ladybug_geometry.geometry3d.pointvector import Point3D
from ladybug_radiance.skymatrix import SkyMatrix
from ladybug_radiance.visualize.raddome import RadiationDome
from ladybug_radiance.visualize.skydome import SkyDome

from ladybug_tools_mcp.contracts.report import make_report
from garden.manifest import GardenManifest
from garden.paths import slugify_name, to_posix_relative
from garden.radiance.sky import SKY_MATRIX_TARGET_TYPE
from garden.run_energy.config import WEATHER_TARGET_TYPE
from garden.visualize.artifacts import save_visualization_set
from garden.visualize.legend import legend_parameter_from_dict

PROJECTIONS = {"orthographic": "Orthographic", "stereographic": "Stereographic"}


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
    if source_type == "wea_file":
        wea_path = _garden_relative_file(
            garden_root,
            str(source.get("wea_path")),
            field_name="sky_matrix.source.wea_path",
            suffix=".wea",
        )
        wea = Wea.from_file(str(wea_path))
    elif source_type in {"weather_file", "epw_path"}:
        epw_path = _garden_relative_file(
            garden_root,
            str(source.get("epw_path")),
            field_name="sky_matrix.source.epw_path",
            suffix=".epw",
        )
        wea = Wea.from_epw_file(str(epw_path))
    elif source_type == "ashrae_clear_sky":
        location = _location_from_dict(source.get("location") or {})
        wea = Wea.from_ashrae_clear_sky(
            location,
            sky_clearness=float(source.get("sky_clearness", 1)),
        )
    else:
        raise ValueError(f"Unsupported sky_matrix source_type: {source_type}.")
    sky_matrix = SkyMatrix(
        wea,
        north=float(parameters.get("north", 0)),
        high_density=bool(parameters.get("high_density", False)),
        ground_reflectance=float(parameters.get("ground_reflectance", 0.2)),
    )
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
    radius: float = 100,
    center_point: dict[str, Any] | list[float] | None = None,
    solar_time: bool = False,
    daily: bool = False,
    projection: str | None = None,
    sun_spheres: bool = False,
    name: str = "sunpath",
    return_visualization_set: bool = True,
) -> dict[str, Any]:
    """Create a Ladybug Sunpath VisualizationSet."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    location_obj, source = _resolve_location(
        garden_root=garden_root_path,
        manifest=manifest,
        location=location,
        weather_target=weather_target,
        epw_path=epw_path,
    )
    sunpath = Sunpath.from_location(location_obj, north_angle=north_angle)
    vis_set = sunpath_to_vis_set(
        sunpath,
        hoys=hoys,
        radius=radius,
        center_point=_point3d(center_point),
        solar_time=solar_time,
        daily=daily,
        projection=_projection(projection),
        sun_spheres=sun_spheres,
    )
    safe_name = _set_visualization_set_name(vis_set, name)
    visualization_set = vis_set.to_dict()
    source.update(
        {
            "tool": "sunpath_to_visualization_set",
            "north_angle": north_angle,
            "hoys": hoys or [],
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
        extra_summary={"location": location_obj.to_dict()},
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
        legend_parameters=legend_parameter_from_dict(legend_parameter),
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
    source = {
        "tool": "sky_matrix_to_skydome_visualization_set",
        "sky_matrix_target": target,
        "sky_matrix_source": payload.get("source"),
        "plot_irradiance": plot_irradiance,
    }
    return _visualization_response(
        garden_root=garden_root_path,
        manifest=manifest,
        visualization_set=visualization_set,
        name=safe_name,
        source=source,
        message="Sky dome VisualizationSet created.",
        return_visualization_set=return_visualization_set,
    )


def sky_matrix_to_radiation_dome_visualization_set(
    *,
    garden_root: str,
    sky_matrix_target: dict[str, Any],
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
    """Create a cumulative RadiationDome VisualizationSet from a SkyMatrix target."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    sky_matrix, target, payload = _sky_matrix_from_target(
        garden_root=garden_root_path,
        manifest=manifest,
        sky_matrix_target=sky_matrix_target,
    )
    radiation_dome = RadiationDome(
        sky_matrix,
        azimuth_count=azimuth_count,
        altitude_count=altitude_count,
        legend_parameters=legend_parameter_from_dict(legend_parameter),
        plot_irradiance=plot_irradiance,
        center_point=_point3d(center_point),
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
    source = {
        "tool": "sky_matrix_to_radiation_dome_visualization_set",
        "sky_matrix_target": target,
        "sky_matrix_source": payload.get("source"),
        "mode": "cumulative",
        "azimuth_count": azimuth_count,
        "altitude_count": altitude_count,
        "plot_irradiance": plot_irradiance,
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
            "azimuth_count": azimuth_count,
            "altitude_count": altitude_count,
        },
    )
