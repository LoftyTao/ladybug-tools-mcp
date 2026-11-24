"""Honeybee Radiance sky and WEA foundation services."""

from __future__ import annotations

import json
from calendar import month_abbr
from pathlib import Path
from typing import Any

import honeybee_radiance.lightsource.sky as hbsky
from honeybee_radiance_command.gendaylit import Gendaylit
from honeybee_radiance_command.gensky import Gensky
from honeybee_radiance_command.options.gendaylit import GendaylitOptions
from honeybee_radiance_command.options.gensky import GenskyOptions
from ladybug.dt import DateTime
from ladybug.epw import EPW
from ladybug.location import Location
from ladybug.wea import Wea
from ladybug_radiance.skymatrix import SkyMatrix

from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from garden.run_energy.config import WEATHER_TARGET_TYPE
from ladybug_tools_mcp.contracts import make_artifact_receipt, make_report

WEA_TARGET_TYPE = "wea_file"
WEA_ARTIFACT_TYPE = "wea_file"
SKY_MATRIX_TARGET_TYPE = "sky_matrix"
SKY_MATRIX_ARTIFACT_TYPE = "sky_matrix_json"
RADIANCE_SKY_FILE_TARGET_TYPE = "radiance_sky_file"
RADIANCE_SKY_FILE_ARTIFACT_TYPE = "radiance_sky_file"
WEA_OUTPUT_SUBDIR = "artifacts/radiance/wea"
SKY_MATRIX_OUTPUT_SUBDIR = "artifacts/radiance/sky"
RADIANCE_SKY_OUTPUT_SUBDIR = "artifacts/radiance/sky"
_CIE_SKY_TYPE_INDEX = {
    "sunny": 0,
    "sunny_with_sun": 0,
    "sunny_no_sun": 1,
    "sunny_without_sun": 1,
    "intermediate": 2,
    "intermediate_with_sun": 2,
    "intermediate_no_sun": 3,
    "intermediate_without_sun": 3,
    "cloudy": 4,
    "uniform": 5,
    "uniform_cloudy": 5,
}


def _resolve_output_dir(garden_root: Path, output_subdir: str) -> Path:
    output_subdir = output_subdir.strip().replace("\\", "/")
    if not output_subdir:
        raise ValueError("output_subdir must be a non-empty Garden-relative path.")
    output_dir = (garden_root / output_subdir).resolve()
    output_dir.relative_to(garden_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _normalize_sky_matrix_output_subdir(output_subdir: str) -> str:
    normalized_subdir = output_subdir.strip().replace("\\", "/")
    if not normalized_subdir:
        raise ValueError("output_subdir must be a non-empty Garden-relative path.")
    return normalized_subdir


def _register_artifact(
    manifest: GardenManifest,
    *,
    artifact_type: str,
    name: str,
    path: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    record = {
        "artifact_type": artifact_type,
        "name": name,
        "path": path,
        "source": source,
        "created_at": utc_now_iso(),
    }
    return manifest.upsert_artifact(record)


def _target(
    *,
    manifest: GardenManifest,
    target_type: str,
    domain: str,
    identifier: str,
    path: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target = {
        "target_type": target_type,
        "domain": domain,
        "garden_id": manifest.garden_id,
        "identifier": identifier,
        "path": path,
    }
    if metadata:
        target.update(metadata)
    return target


def _validate_target_garden(
    *,
    target: dict[str, Any],
    manifest: GardenManifest,
    field_name: str,
) -> None:
    garden_id = target.get("garden_id")
    if garden_id != manifest.garden_id:
        raise ValueError(f"{field_name} belongs to a different Garden.")


def _garden_relative_path(garden_root: Path, path_value: str, *, field_name: str) -> Path:
    path = (garden_root / path_value).resolve()
    path.relative_to(garden_root)
    if not path.is_file():
        raise ValueError(f"{field_name} does not exist inside the Garden: {path_value}")
    return path


def _resolve_epw_path(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
) -> tuple[Path, dict[str, Any]]:
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
        return _garden_relative_path(garden_root, epw_value, field_name="epw_path"), {
            "source_type": "weather_file",
            "weather_target": weather_target,
            "epw_path": epw_value,
        }
    epw = _garden_relative_path(garden_root, str(epw_path), field_name="epw_path")
    return epw, {"source_type": "epw_path", "epw_path": to_posix_relative(epw, garden_root)}


def _resolve_wea_path(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    wea_target: dict[str, Any],
) -> Path:
    if wea_target.get("target_type") != WEA_TARGET_TYPE:
        raise ValueError("wea_target must be a wea_file target.")
    _validate_target_garden(
        target=wea_target,
        manifest=manifest,
        field_name="wea_target",
    )
    path_value = wea_target.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("wea_target requires a Garden-relative path.")
    return _garden_relative_path(garden_root, path_value, field_name="wea_target.path")


def _location_from_input(location: dict[str, Any]) -> Location:
    if not isinstance(location, dict):
        raise ValueError("location must be a Ladybug Location dictionary.")
    data = dict(location)
    data.setdefault("type", "Location")
    try:
        return Location.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Ladybug Location input. {exc}") from exc


def _wea_summary(
    *,
    identifier: str,
    wea: Wea,
    source_type: str,
    target: dict[str, Any],
) -> dict[str, Any]:
    return {
        "identifier": identifier,
        "target": target,
        "source_type": source_type,
        "location": wea.location.to_dict(),
        "timestep": wea.timestep,
        "timestep_count": len(wea),
        "is_annual": wea.is_annual,
        "is_leap_year": wea.is_leap_year,
    }


def _save_wea(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    identifier: str,
    wea: Wea,
    source: dict[str, Any],
    output_subdir: str,
    write_hours: bool,
    return_object_dict: bool,
) -> dict[str, Any]:
    safe_identifier = slugify_name(identifier)
    output_dir = _resolve_output_dir(garden_root_path, output_subdir)
    wea_path = (output_dir / f"{safe_identifier}.wea").resolve()
    wea_path.relative_to(garden_root_path)
    written_path = Path(wea.write(str(wea_path), write_hours=write_hours)).resolve()
    artifact_path = to_posix_relative(written_path, garden_root_path)
    artifact = _register_artifact(
        manifest,
        artifact_type=WEA_ARTIFACT_TYPE,
        name=safe_identifier,
        path=artifact_path,
        source=source,
    )
    manifest.write(garden_root_path)
    target = _target(
        manifest=manifest,
        target_type=WEA_TARGET_TYPE,
        domain="ladybug",
        identifier=safe_identifier,
        path=artifact_path,
        metadata={"source_type": source["source_type"]},
    )
    result = {
        "target": target,
        "wea_target": target,
        "artifact": artifact,
        "summary_view": _wea_summary(
            identifier=safe_identifier,
            wea=wea,
            source_type=str(source["source_type"]),
            target=target,
        ),
        "persistence_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=WEA_ARTIFACT_TYPE,
            artifact_path=artifact_path,
            absolute_path=str(written_path),
            source=source,
        ),
        "report": make_report(
            status="ok",
            message=f"Created WEA file: {safe_identifier}",
        ),
    }
    if return_object_dict:
        result["object_dict"] = wea.to_dict()
    return result


def create_wea_from_weather_file(
    *,
    garden_root: str,
    identifier: str,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    timestep: int = 1,
    hoys: list[float] | None = None,
    write_hours: bool = False,
    output_subdir: str = WEA_OUTPUT_SUBDIR,
    return_object_dict: bool = False,
) -> dict[str, Any]:
    """Create a Garden WEA artifact from a Garden weather target or EPW path."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    resolved_epw, source = _resolve_epw_path(
        garden_root=garden_root_path,
        manifest=manifest,
        weather_target=weather_target,
        epw_path=epw_path,
    )
    wea = Wea.from_epw_file(str(resolved_epw), timestep=timestep)
    if hoys is not None:
        wea = wea.filter_by_hoys(hoys)
        source["hoys"] = hoys
    return _save_wea(
        garden_root_path=garden_root_path,
        manifest=manifest,
        identifier=identifier,
        wea=wea,
        source=source,
        output_subdir=output_subdir,
        write_hours=write_hours,
        return_object_dict=return_object_dict,
    )


def create_ashrae_clear_sky_wea(
    *,
    garden_root: str,
    identifier: str,
    location: dict[str, Any],
    sky_clearness: float = 1,
    timestep: int = 1,
    is_leap_year: bool = False,
    output_subdir: str = WEA_OUTPUT_SUBDIR,
    write_hours: bool = False,
    return_object_dict: bool = False,
) -> dict[str, Any]:
    """Create a Garden WEA artifact from the ASHRAE clear sky model."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    location_obj = _location_from_input(location)
    wea = Wea.from_ashrae_clear_sky(
        location_obj,
        sky_clearness=sky_clearness,
        timestep=timestep,
        is_leap_year=is_leap_year,
    )
    source = {
        "source_type": "ashrae_clear_sky",
        "sky_clearness": sky_clearness,
        "location": location_obj.to_dict(),
    }
    return _save_wea(
        garden_root_path=garden_root_path,
        manifest=manifest,
        identifier=identifier,
        wea=wea,
        source=source,
        output_subdir=output_subdir,
        write_hours=write_hours,
        return_object_dict=return_object_dict,
    )


def _sky_matrix_summary(
    *,
    identifier: str,
    target: dict[str, Any],
    source_type: str,
    parameters: dict[str, Any],
    sky_matrix: SkyMatrix,
    computed: bool,
) -> dict[str, Any]:
    patch_count = 577 if parameters["high_density"] else 145
    return {
        "identifier": identifier,
        "target": target,
        "source_type": source_type,
        "north": parameters["north"],
        "high_density": parameters["high_density"],
        "ground_reflectance": parameters["ground_reflectance"],
        "patch_count": patch_count,
        "wea_duration": sky_matrix.wea_duration,
        "computed": computed,
    }


def _apply_common_sky_options(
    options: GenskyOptions | GendaylitOptions,
    *,
    latitude: float | None,
    longitude: float | None,
    standard_meridian: float | None,
    ground_reflectance: float | None,
) -> None:
    if latitude is not None:
        options.a = latitude
    if longitude is not None:
        options.o = longitude
    if standard_meridian is not None:
        options.m = standard_meridian
    if ground_reflectance is not None:
        options.g = ground_reflectance


def _format_number(value: float | int | None) -> str | None:
    if value is None:
        return None
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:g}"


def _normalize_time_input(value: str | float | None) -> str | float | None:
    if isinstance(value, float) and value.is_integer():
        return f"{int(value)}:00"
    return value


def _append_option(parts: list[str], flag: str, value: Any | None) -> None:
    formatted = _format_number(value) if isinstance(value, (int, float)) else value
    if formatted is not None:
        parts.extend([flag, str(formatted)])


def _recipe_sky_datetime_parts(
    *,
    month: int | None,
    day: int | None,
    time: str | float | None,
) -> list[str]:
    if month is None or day is None or time is None:
        return []
    month_name = month_abbr[int(month)]
    return [str(int(day)), month_name, str(time)]


def _build_sky_command(
    command_type: type[Gensky] | type[Gendaylit],
    *,
    month: int | None,
    day: int | None,
    time: str | float | None,
    time_zone: str | None,
    solar_time: bool,
    solar_altitude: float | None,
    solar_azimuth: float | None,
    options: GenskyOptions | GendaylitOptions,
) -> Gensky | Gendaylit:
    has_angles = solar_altitude is not None or solar_azimuth is not None
    has_date = month is not None or day is not None or time is not None
    if has_angles and has_date:
        raise ValueError("Provide either solar_altitude/solar_azimuth or month/day/time, not both.")
    if has_angles:
        if solar_altitude is None or solar_azimuth is None:
            raise ValueError("solar_altitude and solar_azimuth must be provided together.")
        return command_type.from_ang((solar_altitude, solar_azimuth), options=options)
    if month is None or day is None or time is None:
        raise ValueError("month, day, and time are required when solar angles are not provided.")
    return command_type(
        month,
        day,
        time,
        time_zone=time_zone,
        solar_time=solar_time,
        options=options,
    )


def _save_sky_file(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    identifier: str,
    sky_family: str,
    command_text: str,
    source: dict[str, Any],
    summary: dict[str, Any],
    output_subdir: str,
    recipe_sky: str | None = None,
    raw_text: str | None = None,
) -> dict[str, Any]:
    safe_identifier = slugify_name(identifier)
    output_dir = _resolve_output_dir(garden_root_path, output_subdir)
    sky_path = (output_dir / f"{safe_identifier}.sky").resolve()
    sky_path.relative_to(garden_root_path)
    content = (
        f"{raw_text.rstrip()}\n"
        if raw_text is not None
        else (
            f"{command_text.rstrip()}\n"
            if command_text.lstrip().startswith("!")
            else f"!{command_text}\n"
        )
    )
    sky_path.write_text(content, encoding="utf-8", newline="\n")

    artifact_path = to_posix_relative(sky_path, garden_root_path)
    artifact_source = dict(source)
    if recipe_sky:
        artifact_source["recipe_sky"] = recipe_sky
    artifact = _register_artifact(
        manifest,
        artifact_type=RADIANCE_SKY_FILE_ARTIFACT_TYPE,
        name=safe_identifier,
        path=artifact_path,
        source=artifact_source,
    )
    manifest.write(garden_root_path)
    metadata = {"sky_family": sky_family}
    if recipe_sky:
        metadata["recipe_sky"] = recipe_sky
    target = _target(
        manifest=manifest,
        target_type=RADIANCE_SKY_FILE_TARGET_TYPE,
        domain="honeybee_radiance",
        identifier=safe_identifier,
        path=artifact_path,
        metadata=metadata,
    )
    summary_view = {
        "identifier": safe_identifier,
        "target": target,
        "sky_family": sky_family,
        "command": command_text,
        **summary,
    }
    if recipe_sky:
        summary_view["recipe_sky"] = recipe_sky
    return {
        "target": target,
        "sky_file_target": target,
        "radiance_sky_file": target,
        "artifact": artifact,
        "summary_view": summary_view,
        "persistence_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=RADIANCE_SKY_FILE_ARTIFACT_TYPE,
            artifact_path=artifact_path,
            absolute_path=str(sky_path),
            source=artifact_source,
        ),
        "report": make_report(
            status="ok",
            message=f"Created Radiance sky file: {safe_identifier}",
        ),
    }


def create_cie_standard_sky(
    *,
    garden_root: str,
    identifier: str,
    month: int | None = None,
    day: int | None = None,
    time: str | float | None = None,
    time_zone: str | int | float | None = None,
    solar_time: bool = False,
    solar_altitude: float | None = None,
    solar_azimuth: float | None = None,
    sky_type: str = "sunny",
    latitude: float | None = None,
    longitude: float | None = None,
    standard_meridian: float | None = None,
    ground_reflectance: float | None = None,
    sky_turbidity: float | None = None,
    solar_radiance: float | None = None,
    direct_horizontal_irradiance: float | None = None,
    zenith_brightness: float | None = None,
    diffuse_horizontal_irradiance: float | None = None,
    output_subdir: str = RADIANCE_SKY_OUTPUT_SUBDIR,
) -> dict[str, Any]:
    """Create a command-backed Radiance CIE standard sky file with gensky."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    options = GenskyOptions()
    command_time_zone = _normalize_sky_time_zone(time_zone)
    recipe_time_zone = _recipe_time_zone_int(time_zone)
    normalized_sky_type = sky_type.lower().replace("-", "_").replace(" ", "_")
    if normalized_sky_type == "clear":
        normalized_sky_type = "sunny"
    time = _normalize_time_input(time)
    if normalized_sky_type in {"sunny", "sunny_with_sun"}:
        options.s = "+"
    elif normalized_sky_type in {"sunny_no_sun", "sunny_without_sun"}:
        options.s = "-"
    elif normalized_sky_type == "cloudy":
        options.c = True
    elif normalized_sky_type in {"uniform", "uniform_cloudy"}:
        options.u = True
    elif normalized_sky_type in {"intermediate", "intermediate_with_sun"}:
        options.i = "+"
    elif normalized_sky_type in {"intermediate_no_sun", "intermediate_without_sun"}:
        options.i = "-"
    else:
        raise ValueError(
            "sky_type must be one of sunny, sunny_no_sun, cloudy, uniform_cloudy, "
            "intermediate, or intermediate_no_sun."
        )
    _apply_common_sky_options(
        options,
        latitude=latitude,
        longitude=longitude,
        standard_meridian=standard_meridian,
        ground_reflectance=ground_reflectance,
    )
    if sky_turbidity is not None:
        options.t = sky_turbidity
    if solar_radiance is not None:
        options.r = solar_radiance
    if direct_horizontal_irradiance is not None:
        options.R = direct_horizontal_irradiance
    if zenith_brightness is not None:
        options.b = zenith_brightness
    if diffuse_horizontal_irradiance is not None:
        options.B = diffuse_horizontal_irradiance

    command = _build_sky_command(
        Gensky,
        month=month,
        day=day,
        time=time,
        time_zone=command_time_zone,
        solar_time=solar_time,
        solar_altitude=solar_altitude,
        solar_azimuth=solar_azimuth,
        options=options,
    )
    source = {
        "source_type": "cie_standard_sky",
        "sky_type": normalized_sky_type,
        "generator": "gensky",
        "month": month,
        "day": day,
        "time": time,
        "time_zone": time_zone,
        "solar_time": solar_time,
        "solar_altitude": solar_altitude,
        "solar_azimuth": solar_azimuth,
        "latitude": latitude,
        "longitude": longitude,
        "standard_meridian": standard_meridian,
        "ground_reflectance": ground_reflectance,
    }
    sky_type_index = _CIE_SKY_TYPE_INDEX[normalized_sky_type]
    if solar_altitude is not None and solar_azimuth is not None:
        recipe_parts = ["cie"]
        _append_option(recipe_parts, "-alt", solar_altitude)
        _append_option(recipe_parts, "-az", solar_azimuth)
    else:
        recipe_parts = ["cie", *_recipe_sky_datetime_parts(month=month, day=day, time=time)]
    _append_option(recipe_parts, "-lat", latitude)
    _append_option(recipe_parts, "-lon", longitude)
    if recipe_time_zone is not None:
        _append_option(recipe_parts, "-tz", recipe_time_zone)
    _append_option(recipe_parts, "-type", sky_type_index)
    _append_option(recipe_parts, "-g", ground_reflectance)
    recipe_sky = " ".join(recipe_parts)
    summary = {
        "sky_type": normalized_sky_type,
        "generator": "gensky",
        "date_time": {"month": month, "day": day, "time": time},
        "solar_angles": {"altitude": solar_altitude, "azimuth": solar_azimuth},
    }
    return _save_sky_file(
        garden_root_path=garden_root_path,
        manifest=manifest,
        identifier=identifier,
        sky_family="cie_standard",
        command_text=command.to_radiance(),
        source=source,
        summary=summary,
        output_subdir=output_subdir,
        recipe_sky=recipe_sky,
    )


def create_climate_based_sky(
    *,
    garden_root: str,
    identifier: str,
    month: int | None = None,
    day: int | None = None,
    time: str | float | None = None,
    time_zone: str | int | float | None = None,
    solar_time: bool = False,
    solar_altitude: float | None = None,
    solar_azimuth: float | None = None,
    direct_normal_irradiance: float | None = None,
    diffuse_horizontal_irradiance: float | None = None,
    direct_normal_illuminance: float | None = None,
    diffuse_horizontal_illuminance: float | None = None,
    output_mode: int | None = None,
    sky_part: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    standard_meridian: float | None = None,
    ground_reflectance: float | None = None,
    output_subdir: str = RADIANCE_SKY_OUTPUT_SUBDIR,
) -> dict[str, Any]:
    """Create a command-backed Radiance climate-based sky file with gendaylit."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    options = GendaylitOptions()
    command_time_zone = _normalize_sky_time_zone(time_zone)
    recipe_time_zone = _recipe_time_zone_int(time_zone)
    time = _normalize_time_input(time)
    has_irradiance = direct_normal_irradiance is not None or diffuse_horizontal_irradiance is not None
    has_illuminance = direct_normal_illuminance is not None or diffuse_horizontal_illuminance is not None
    if has_irradiance and has_illuminance:
        raise ValueError("Provide irradiance inputs or illuminance inputs, not both.")
    if has_irradiance:
        if direct_normal_irradiance is None or diffuse_horizontal_irradiance is None:
            raise ValueError(
                "direct_normal_irradiance and diffuse_horizontal_irradiance must be provided together."
            )
        options.W = (direct_normal_irradiance, diffuse_horizontal_irradiance)
    elif has_illuminance:
        if direct_normal_illuminance is None or diffuse_horizontal_illuminance is None:
            raise ValueError(
                "direct_normal_illuminance and diffuse_horizontal_illuminance must be provided together."
            )
        options.L = (direct_normal_illuminance, diffuse_horizontal_illuminance)
    else:
        raise ValueError("Provide either irradiance inputs (-W) or illuminance inputs (-L).")
    if output_mode is not None:
        options.O = output_mode
    if sky_part is not None:
        normalized_sky_part = sky_part.lower().replace("-", "_").replace(" ", "_")
        if normalized_sky_part in {"visible", "luminance"}:
            options.s = True
        elif normalized_sky_part in {"solar", "radiance"}:
            options.s = False
        else:
            raise ValueError("sky_part must be visible/luminance or solar/radiance.")
    else:
        normalized_sky_part = None
    _apply_common_sky_options(
        options,
        latitude=latitude,
        longitude=longitude,
        standard_meridian=standard_meridian,
        ground_reflectance=ground_reflectance,
    )

    command = _build_sky_command(
        Gendaylit,
        month=month,
        day=day,
        time=time,
        time_zone=command_time_zone,
        solar_time=solar_time,
        solar_altitude=solar_altitude,
        solar_azimuth=solar_azimuth,
        options=options,
    )
    irradiance = None
    illuminance = None
    if has_irradiance:
        irradiance = {
            "direct_normal": direct_normal_irradiance,
            "diffuse_horizontal": diffuse_horizontal_irradiance,
        }
    if has_illuminance:
        illuminance = {
            "direct_normal": direct_normal_illuminance,
            "diffuse_horizontal": diffuse_horizontal_illuminance,
        }
    source = {
        "source_type": "climate_based_sky",
        "generator": "gendaylit",
        "month": month,
        "day": day,
        "time": time,
        "time_zone": time_zone,
        "solar_time": solar_time,
        "solar_altitude": solar_altitude,
        "solar_azimuth": solar_azimuth,
        "irradiance": irradiance,
        "illuminance": illuminance,
        "output_mode": output_mode,
        "sky_part": normalized_sky_part,
        "latitude": latitude,
        "longitude": longitude,
        "standard_meridian": standard_meridian,
        "ground_reflectance": ground_reflectance,
    }
    if solar_altitude is not None and solar_azimuth is not None:
        recipe_parts = ["climate-based"]
        _append_option(recipe_parts, "-alt", solar_altitude)
        _append_option(recipe_parts, "-az", solar_azimuth)
    else:
        recipe_parts = [
            "climate-based",
            *_recipe_sky_datetime_parts(month=month, day=day, time=time),
        ]
    _append_option(recipe_parts, "-lat", latitude)
    _append_option(recipe_parts, "-lon", longitude)
    if recipe_time_zone is not None:
        _append_option(recipe_parts, "-tz", recipe_time_zone)
    if has_irradiance:
        _append_option(recipe_parts, "-dni", direct_normal_irradiance)
        _append_option(recipe_parts, "-dhi", diffuse_horizontal_irradiance)
    elif has_illuminance:
        dni_lum = _format_number(direct_normal_illuminance)
        dhi_lum = _format_number(diffuse_horizontal_illuminance)
        recipe_parts.extend(["-L", str(dni_lum), str(dhi_lum)])
    _append_option(recipe_parts, "-g", ground_reflectance)
    recipe_sky = " ".join(recipe_parts)
    summary = {
        "generator": "gendaylit",
        "date_time": {"month": month, "day": day, "time": time},
        "solar_angles": {"altitude": solar_altitude, "azimuth": solar_azimuth},
        "irradiance": irradiance,
        "illuminance": illuminance,
        "output_mode": output_mode,
        "sky_part": normalized_sky_part,
    }
    return _save_sky_file(
        garden_root_path=garden_root_path,
        manifest=manifest,
        identifier=identifier,
        sky_family="climate_based",
        command_text=command.to_radiance(),
        source=source,
        summary=summary,
        output_subdir=output_subdir,
        recipe_sky=recipe_sky,
    )


def create_certain_irradiance_sky(
    *,
    garden_root: str,
    identifier: str,
    irradiance: float | None = None,
    illuminance: float | None = None,
    ground_reflectance: float = 0.2,
    uniform: bool = False,
    cloudy: bool | None = None,
    output_subdir: str = RADIANCE_SKY_OUTPUT_SUBDIR,
) -> dict[str, Any]:
    """Create a CertainIrradiance Radiance sky file (supports 0 lux dark sky for electric lighting)."""
    if irradiance is not None and illuminance is not None:
        raise ValueError("Provide either irradiance or illuminance, not both.")
    effective_uniform = (not cloudy) if cloudy is not None else bool(uniform)
    if illuminance is not None:
        sky_obj = hbsky.CertainIrradiance.from_illuminance(
            illuminance=float(illuminance),
            ground_reflectance=float(ground_reflectance),
            uniform=effective_uniform,
        )
    else:
        val = 558.659 if irradiance is None else float(irradiance)
        sky_obj = hbsky.CertainIrradiance(
            irradiance=val,
            ground_reflectance=float(ground_reflectance),
            uniform=effective_uniform,
        )
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    raw_text = sky_obj.to_radiance()
    recipe_parts = ["irradiance", str(_format_number(sky_obj.irradiance))]
    _append_option(recipe_parts, "-g", sky_obj.ground_reflectance)
    if sky_obj.uniform:
        recipe_parts.append("-u")
    recipe_sky = " ".join(recipe_parts)
    source = {
        "source_type": "certain_irradiance",
        "irradiance": float(sky_obj.irradiance),
        "illuminance": float(sky_obj.illuminance),
        "ground_reflectance": float(sky_obj.ground_reflectance),
        "uniform": sky_obj.uniform,
    }
    summary = dict(source)
    return _save_sky_file(
        garden_root_path=garden_root_path,
        manifest=manifest,
        identifier=identifier,
        sky_family="certain_irradiance",
        command_text=raw_text.splitlines()[0].lstrip("!"),
        raw_text=raw_text,
        source=source,
        summary=summary,
        output_subdir=output_subdir,
        recipe_sky=recipe_sky,
    )


def create_epw_hoy_sky(
    *,
    garden_root: str,
    identifier: str,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    month: int | None = None,
    day: int | None = None,
    time: str | float | None = None,
    hoy: float | None = None,
    north: float = 0.0,
    ground_reflectance: float = 0.2,
    is_colored: bool = False,
    output_subdir: str = RADIANCE_SKY_OUTPUT_SUBDIR,
) -> dict[str, Any]:
    """Create a ClimateBased Radiance sky from an EPW file at a month/day/time or HOY."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    resolved_epw, source = _resolve_epw_path(
        garden_root=garden_root_path,
        manifest=manifest,
        weather_target=weather_target,
        epw_path=epw_path,
    )
    epw_obj = EPW(str(resolved_epw))
    if hoy is not None:
        dt = DateTime.from_hoy(float(hoy))
        m, d, h = dt.month, dt.day, dt.float_hour
    else:
        if month is None or day is None or time is None:
            raise ValueError("Provide hoy, or month, day, and time for from_epw_hoy.")
        normalized_time = _normalize_time_input(time)
        if isinstance(normalized_time, str) and ":" in normalized_time:
            hh, mm = normalized_time.split(":", 1)
            h = float(hh) + float(mm) / 60.0
        else:
            h = float(normalized_time)
        m, d = int(month), int(day)
        dt = DateTime(m, d, int(h), int(round((h - int(h)) * 60)))
    sky_obj = hbsky.ClimateBased.from_epw(
        epw_obj,
        m,
        d,
        h,
        north_angle=float(north),
        ground_reflectance=float(ground_reflectance),
        is_colored=bool(is_colored),
    )
    raw_text = sky_obj.to_radiance()
    time_str = f"{int(h):02d}:{int(round((h - int(h)) * 60)):02d}"
    recipe_parts = ["climate-based", str(d), month_abbr[m], time_str]
    _append_option(recipe_parts, "-lat", epw_obj.location.latitude)
    _append_option(recipe_parts, "-lon", epw_obj.location.longitude)
    _append_option(recipe_parts, "-tz", int(round(epw_obj.location.time_zone)))
    _append_option(recipe_parts, "-dni", sky_obj.direct_normal_irradiance)
    _append_option(recipe_parts, "-dhi", sky_obj.diffuse_horizontal_irradiance)
    _append_option(recipe_parts, "-n", float(north))
    _append_option(recipe_parts, "-g", sky_obj.ground_reflectance)
    if is_colored:
        recipe_parts.append("-c")
    recipe_sky = " ".join(recipe_parts)
    source = {
        **source,
        "source_type": "from_epw_hoy",
        "hoy": float(dt.hoy),
        "month": m,
        "day": d,
        "hour": h,
        "north": float(north),
        "ground_reflectance": float(ground_reflectance),
        "is_colored": bool(is_colored),
    }
    summary = {
        "source_type": "from_epw_hoy",
        "hoy": float(dt.hoy),
        "date_time": {"month": m, "day": d, "time": time_str},
        "location": epw_obj.location.to_dict(),
        "altitude": round(float(sky_obj.altitude), 4),
        "azimuth": round(float(sky_obj.azimuth), 4),
        "direct_normal_irradiance": float(sky_obj.direct_normal_irradiance),
        "diffuse_horizontal_irradiance": float(sky_obj.diffuse_horizontal_irradiance),
    }
    return _save_sky_file(
        garden_root_path=garden_root_path,
        manifest=manifest,
        identifier=identifier,
        sky_family="from_epw_hoy",
        command_text=raw_text.splitlines()[0].lstrip("!"),
        raw_text=raw_text,
        source=source,
        summary=summary,
        output_subdir=output_subdir,
        recipe_sky=recipe_sky,
    )


def create_skydome_sky(
    *,
    garden_root: str,
    identifier: str,
    sky_density: int = 1,
    ground_emittance: float = 0.2,
    uniform: bool = False,
    output_subdir: str = RADIANCE_SKY_OUTPUT_SUBDIR,
) -> dict[str, Any]:
    """Create a SkyDome or UniformSky Radiance file."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    if uniform:
        sky_obj = hbsky.UniformSky(ground_emittance=float(ground_emittance))
        raw_text = sky_obj.to_radiance()
        recipe_sky = f"uniform-sky -g {_format_number(ground_emittance)}"
        sky_family = "uniform_sky"
    else:
        sky_obj = hbsky.SkyDome(
            sky_density=int(sky_density),
            ground_emittance=float(ground_emittance),
        )
        raw_text = sky_obj.to_radiance()
        recipe_sky = f"skydome --sky-density {int(sky_density)}"
        sky_family = "skydome"
    source = {
        "source_type": sky_family,
        "sky_density": int(sky_density),
        "ground_emittance": float(ground_emittance),
        "uniform": bool(uniform),
    }
    return _save_sky_file(
        garden_root_path=garden_root_path,
        manifest=manifest,
        identifier=identifier,
        sky_family=sky_family,
        command_text=raw_text.splitlines()[0],
        raw_text=raw_text,
        source=source,
        summary=dict(source),
        output_subdir=output_subdir,
        recipe_sky=recipe_sky,
    )


def _wea_from_sky_inputs(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    wea_target: dict[str, Any] | None,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
) -> tuple[Wea, dict[str, Any]]:
    if wea_target is not None:
        wea_file = _resolve_wea_path(
            garden_root=garden_root_path,
            manifest=manifest,
            wea_target=wea_target,
        )
        return Wea.from_file(str(wea_file)), {
            "source_type": "wea_file",
            "wea_target": wea_target,
            "wea_path": to_posix_relative(wea_file, garden_root_path),
        }
    resolved_epw, source = _resolve_epw_path(
        garden_root=garden_root_path,
        manifest=manifest,
        weather_target=weather_target,
        epw_path=epw_path,
    )
    return Wea.from_epw_file(str(resolved_epw)), source


def create_leed_illuminance_skies(
    *,
    garden_root: str,
    identifier: str,
    wea_target: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    north: float = 0.0,
    ground_reflectance: float = 0.2,
    output_subdir: str = RADIANCE_SKY_OUTPUT_SUBDIR,
) -> dict[str, Any]:
    """Generate the two LEED v4.1 Daylight Option 2 clear-sky equinox skies (9AM and 3PM)."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    wea_obj, source = _wea_from_sky_inputs(
        garden_root_path=garden_root_path,
        manifest=manifest,
        wea_target=wea_target,
        weather_target=weather_target,
        epw_path=epw_path,
    )
    if not wea_obj.is_annual or wea_obj.timestep != 1 or wea_obj.is_leap_year:
        raise ValueError("LEED illuminance skies require an annual timestep=1 non-leap-year WEA/EPW.")
    mar_9, sep_9 = DateTime(3, 21, 9).hoy, DateTime(9, 21, 9).hoy
    mar_3, sep_3 = DateTime(3, 21, 15).hoy, DateTime(9, 21, 15).hoy
    hoys_mar9 = list(range(int(mar_9 - (15 * 24)), int(mar_9 + (15 * 24)), 24))
    hoys_sep9 = list(range(int(sep_9 - (15 * 24)), int(sep_9 + (15 * 24)), 24))
    hoys_mar3 = list(range(int(mar_3 - (15 * 24)), int(mar_3 + (15 * 24)), 24))
    hoys_sep3 = list(range(int(sep_3 - (15 * 24)), int(sep_3 + (15 * 24)), 24))

    dni = wea_obj.direct_normal_irradiance
    dhi = wea_obj.diffuse_horizontal_irradiance
    irr_mar9 = [x for _, x in sorted(zip([dni[h] for h in hoys_mar9], hoys_mar9))]
    irr_sep9 = [x for _, x in sorted(zip([dni[h] for h in hoys_sep9], hoys_sep9))]
    irr_mar3 = [x for _, x in sorted(zip([dni[h] for h in hoys_mar3], hoys_mar3))]
    irr_sep3 = [x for _, x in sorted(zip([dni[h] for h in hoys_sep3], hoys_sep3))]

    dni_9 = (dni[irr_mar9[-1]] + dni[irr_sep9[-1]]) / 2.0
    dhi_9 = (dhi[irr_mar9[-1]] + dhi[irr_sep9[-1]]) / 2.0
    dni_3 = (dni[irr_mar3[-1]] + dni[irr_sep3[-1]]) / 2.0
    dhi_3 = (dhi[irr_mar3[-1]] + dhi[irr_sep3[-1]]) / 2.0

    sky_9 = hbsky.ClimateBased.from_location(
        wea_obj.location, 3, 21, 9, dni_9, dhi_9, float(north), float(ground_reflectance)
    )
    sky_3 = hbsky.ClimateBased.from_location(
        wea_obj.location, 3, 21, 15, dni_3, dhi_3, float(north), float(ground_reflectance)
    )

    loc = wea_obj.location
    tz_int = int(round(loc.time_zone))
    saved_entries: dict[str, dict[str, Any]] = {}
    for suffix, hour_val, time_lbl, sky_obj, dni_val, dhi_val in (
        ("9AM", 9, "09:00", sky_9, dni_9, dhi_9),
        ("3PM", 15, "15:00", sky_3, dni_3, dhi_3),
    ):
        recipe_sky = (
            f"climate-based 21 Mar {time_lbl} -lat {_format_number(loc.latitude)} "
            f"-lon {_format_number(loc.longitude)} -tz {tz_int} "
            f"-dni {_format_number(dni_val)} -dhi {_format_number(dhi_val)} "
            f"-n {_format_number(north)} -g {_format_number(ground_reflectance)}"
        )
        raw_text = sky_obj.to_radiance()
        saved = _save_sky_file(
            garden_root_path=garden_root_path,
            manifest=manifest,
            identifier=f"{identifier}_{suffix}",
            sky_family="leed_illuminance",
            command_text=raw_text.splitlines()[0].lstrip("!"),
            raw_text=raw_text,
            source={**source, "source_type": "leed_illuminance", "hour": hour_val, "north": float(north)},
            summary={"hour": hour_val, "dni": dni_val, "dhi": dhi_val},
            output_subdir=output_subdir,
            recipe_sky=recipe_sky,
        )
        saved_entries[suffix] = saved

    primary = saved_entries["9AM"]
    targets = {key: val["target"] for key, val in saved_entries.items()}
    return {
        "target": primary["target"],
        "sky_file_target": primary["target"],
        "sky_file_targets": targets,
        "skies": saved_entries,
        "summary_view": {
            "sky_family": "leed_illuminance",
            "location": loc.to_dict(),
            "north": float(north),
            "targets": targets,
            "recipe_skies": {k: v["summary_view"].get("recipe_sky") for k, v in saved_entries.items()},
        },
        "report": make_report(
            status="ok",
            message=f"Created LEED v4.1 clear equinox skies (9AM and 3PM) for {identifier}.",
        ),
    }


def create_abnt_nbr_15575_skies(
    *,
    garden_root: str,
    identifier: str,
    wea_target: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    north: float = 0.0,
    ground_reflectance: float = 0.2,
    output_subdir: str = RADIANCE_SKY_OUTPUT_SUBDIR,
) -> dict[str, Any]:
    """Generate the four ABNT NBR 15575 CIE intermediate-no-sun skies (Apr 23 & Oct 23, 9:30 & 15:30)."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    wea_obj, source = _wea_from_sky_inputs(
        garden_root_path=garden_root_path,
        manifest=manifest,
        wea_target=wea_target,
        weather_target=weather_target,
        epw_path=epw_path,
    )
    loc = wea_obj.location
    tz_int = int(round(loc.time_zone))
    specs = (
        ("4_930AM", 4, 23, 9.5, "09:30"),
        ("4_330PM", 4, 23, 15.5, "15:30"),
        ("10_930AM", 10, 23, 9.5, "09:30"),
        ("10_330PM", 10, 23, 15.5, "15:30"),
    )
    saved_entries: dict[str, dict[str, Any]] = {}
    for suffix, month_val, day_val, hour_val, time_lbl in specs:
        sky_obj = hbsky.CIE.from_location(
            loc, month_val, day_val, hour_val, sky_type=3, north_angle=float(north), ground_reflectance=float(ground_reflectance)
        )
        recipe_sky = (
            f"cie {day_val} {month_abbr[month_val]} {time_lbl} -lat {_format_number(loc.latitude)} "
            f"-lon {_format_number(loc.longitude)} -tz {tz_int} -type 3 "
            f"-n {_format_number(north)} -g {_format_number(ground_reflectance)}"
        )
        raw_text = sky_obj.to_radiance()
        saved = _save_sky_file(
            garden_root_path=garden_root_path,
            manifest=manifest,
            identifier=f"{identifier}_{suffix}",
            sky_family="abnt_nbr_15575",
            command_text=raw_text.splitlines()[0].lstrip("!"),
            raw_text=raw_text,
            source={**source, "source_type": "abnt_nbr_15575", "month": month_val, "day": day_val, "hour": hour_val},
            summary={"month": month_val, "day": day_val, "time": time_lbl, "sky_type": 3},
            output_subdir=output_subdir,
            recipe_sky=recipe_sky,
        )
        saved_entries[suffix] = saved

    primary = saved_entries["4_930AM"]
    targets = {key: val["target"] for key, val in saved_entries.items()}
    return {
        "target": primary["target"],
        "sky_file_target": primary["target"],
        "sky_file_targets": targets,
        "skies": saved_entries,
        "summary_view": {
            "sky_family": "abnt_nbr_15575",
            "location": loc.to_dict(),
            "north": float(north),
            "targets": targets,
            "recipe_skies": {k: v["summary_view"].get("recipe_sky") for k, v in saved_entries.items()},
        },
        "report": make_report(
            status="ok",
            message=f"Created four ABNT NBR 15575 CIE skies for {identifier}.",
        ),
    }


def create_sky_matrix(
    *,
    garden_root: str,
    identifier: str,
    wea_target: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    stat_path: str | None = None,
    location: dict[str, Any] | None = None,
    sky_clearness: float = 1,
    hoys: list[float] | None = None,
    benefit_matrix: bool = False,
    balance_temperature: float = 15.0,
    balance_offset: float = 2.0,
    north: float = 0,
    high_density: bool = False,
    ground_reflectance: float = 0.2,
    compute: bool = False,
    output_subdir: str = SKY_MATRIX_OUTPUT_SUBDIR,
) -> dict[str, Any]:
    """Create a Garden target describing a Ladybug Radiance SkyMatrix."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    sources = [
        wea_target is not None,
        weather_target is not None or epw_path is not None,
        stat_path is not None,
        location is not None,
    ]
    if sum(1 for item in sources if item) != 1:
        raise ValueError(
            "Provide exactly one sky source: wea_target, weather_target/epw_path, stat_path, or location."
        )

    sky_matrix: SkyMatrix
    if stat_path is not None:
        if benefit_matrix:
            raise ValueError("benefit_matrix requires an EPW via weather_target or epw_path.")
        resolved_stat = _garden_relative_path(garden_root_path, str(stat_path), field_name="stat_path")
        source_type = "stat_file"
        source: dict[str, Any] = {
            "source_type": source_type,
            "stat_path": to_posix_relative(resolved_stat, garden_root_path),
        }
        wea = Wea.from_stat_file(str(resolved_stat))
        if hoys is not None:
            wea = wea.filter_by_hoys(hoys)
            source["hoys"] = list(hoys)
        sky_matrix = SkyMatrix(
            wea,
            north=north,
            high_density=high_density,
            ground_reflectance=ground_reflectance,
        )
    elif wea_target is not None:
        if benefit_matrix:
            raise ValueError("benefit_matrix requires an EPW via weather_target or epw_path.")
        source_type = "wea_file"
        wea_path = _resolve_wea_path(
            garden_root=garden_root_path,
            manifest=manifest,
            wea_target=wea_target,
        )
        source = {
            "source_type": source_type,
            "wea_target": wea_target,
            "wea_path": to_posix_relative(wea_path, garden_root_path),
        }
        wea = Wea.from_file(str(wea_path))
        if hoys is not None:
            wea = wea.filter_by_hoys(hoys)
            source["hoys"] = list(hoys)
        sky_matrix = SkyMatrix(
            wea,
            north=north,
            high_density=high_density,
            ground_reflectance=ground_reflectance,
        )
    elif weather_target is not None or epw_path is not None:
        resolved_epw, source = _resolve_epw_path(
            garden_root=garden_root_path,
            manifest=manifest,
            weather_target=weather_target,
            epw_path=epw_path,
        )
        source_type = str(source["source_type"])
        if benefit_matrix:
            sky_matrix = SkyMatrix.from_epw_benefit(
                str(resolved_epw),
                balance_temperature=float(balance_temperature),
                balance_offset=float(balance_offset),
                hoys=hoys,
                north=north,
                high_density=high_density,
                ground_reflectance=ground_reflectance,
            )
            source["benefit_matrix"] = True
            source["balance_temperature"] = float(balance_temperature)
            source["balance_offset"] = float(balance_offset)
        else:
            wea = Wea.from_epw_file(str(resolved_epw))
            if hoys is not None:
                wea = wea.filter_by_hoys(hoys)
            sky_matrix = SkyMatrix(
                wea,
                north=north,
                high_density=high_density,
                ground_reflectance=ground_reflectance,
            )
        if hoys is not None:
            source["hoys"] = list(hoys)
    else:
        if benefit_matrix:
            raise ValueError("benefit_matrix requires an EPW via weather_target or epw_path.")
        location_obj = _location_from_input(location or {})
        source_type = "ashrae_clear_sky"
        source = {
            "source_type": source_type,
            "sky_clearness": sky_clearness,
            "location": location_obj.to_dict(),
        }
        wea = Wea.from_ashrae_clear_sky(location_obj, sky_clearness=sky_clearness)
        if hoys is not None:
            wea = wea.filter_by_hoys(hoys)
            source["hoys"] = list(hoys)
        sky_matrix = SkyMatrix(
            wea,
            north=north,
            high_density=high_density,
            ground_reflectance=ground_reflectance,
        )

    parameters = {
        "north": north,
        "high_density": high_density,
        "ground_reflectance": ground_reflectance,
        "hoys": list(hoys) if hoys is not None else None,
        "benefit_matrix": benefit_matrix,
        "balance_temperature": float(balance_temperature) if benefit_matrix else None,
        "balance_offset": float(balance_offset) if benefit_matrix else None,
    }
    payload: dict[str, Any] = {
        "type": SKY_MATRIX_TARGET_TYPE,
        "identifier": slugify_name(identifier),
        "source": source,
        "parameters": parameters,
    }
    if benefit_matrix and sky_matrix.benefit_matrix is not None:
        payload["benefit_matrix"] = list(sky_matrix.benefit_matrix)
    if compute:
        payload["metadata"] = [str(item) for item in sky_matrix.metadata]
        payload["direct_values"] = list(sky_matrix.direct_values)
        payload["diffuse_values"] = list(sky_matrix.diffuse_values)

    safe_identifier = slugify_name(identifier)
    output_dir = _resolve_output_dir(
        garden_root_path,
        _normalize_sky_matrix_output_subdir(output_subdir),
    )
    sky_path = (output_dir / f"{safe_identifier}.json").resolve()
    sky_path.relative_to(garden_root_path)
    with sky_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle)
        handle.write("\n")

    artifact_path = to_posix_relative(sky_path, garden_root_path)
    artifact_source = {**source, "parameters": parameters, "computed": compute}
    artifact = _register_artifact(
        manifest,
        artifact_type=SKY_MATRIX_ARTIFACT_TYPE,
        name=safe_identifier,
        path=artifact_path,
        source=artifact_source,
    )
    manifest.write(garden_root_path)
    target = _target(
        manifest=manifest,
        target_type=SKY_MATRIX_TARGET_TYPE,
        domain="ladybug_radiance",
        identifier=safe_identifier,
        path=artifact_path,
        metadata={"computed": compute, "benefit_matrix": benefit_matrix},
    )
    summary = _sky_matrix_summary(
        identifier=safe_identifier,
        target=target,
        source_type=source_type,
        parameters=parameters,
        sky_matrix=sky_matrix,
        computed=compute,
    )
    summary["has_benefit_matrix"] = sky_matrix.benefit_matrix is not None
    if sky_matrix.benefit_matrix is not None:
        summary["benefit_hour_count"] = len(sky_matrix.benefit_matrix)
    if hoys is not None:
        summary["hoys_count"] = len(hoys)
    return {
        "target": target,
        "sky_matrix_target": target,
        "artifact": artifact,
        "summary_view": summary,
        "persistence_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=SKY_MATRIX_ARTIFACT_TYPE,
            artifact_path=artifact_path,
            absolute_path=str(sky_path),
            source=artifact_source,
        ),
        "report": make_report(
            status="ok",
            message=f"Created SkyMatrix target: {safe_identifier}",
        ),
    }


_TIME_ZONE_OFFSET_NAMES = {
    -9: "YST",
    -8: "PST",
    -7: "MST",
    -6: "CST",
    -5: "EST",
    -4: "AST",
    0: "GMT",
    1: "CET",
    2: "EET",
    3: "AST",
    4: "GST",
    5.5: "IST",
    9: "JST",
    12: "NZST",
}
_TIME_ZONE_NAME_TO_OFFSET = {
    "YST": -9,
    "PST": -8,
    "MST": -7,
    "CST": -6,
    "EST": -5,
    "AST": -4,
    "GMT": 0,
    "UTC": 0,
    "CET": 1,
    "EET": 2,
    "GST": 4,
    "IST": 5,
    "JST": 9,
    "NZST": 12,
}


def _recipe_time_zone_int(time_zone: str | int | float | None) -> int | None:
    if time_zone is None or isinstance(time_zone, bool):
        return None
    if isinstance(time_zone, (int, float)):
        return int(round(float(time_zone)))
    stripped = str(time_zone).strip()
    if not stripped:
        return None
    upper = stripped.upper()
    if upper in _TIME_ZONE_NAME_TO_OFFSET:
        return int(_TIME_ZONE_NAME_TO_OFFSET[upper])
    for prefix in ("UTC", "GMT"):
        if upper.startswith(prefix) and len(upper) > len(prefix):
            remainder = stripped[len(prefix) :].strip()
            try:
                return int(round(float(remainder)))
            except ValueError:
                pass
    try:
        return int(round(float(stripped)))
    except ValueError:
        return None


def _normalize_sky_time_zone(time_zone: str | int | float | None) -> str | None:
    if time_zone is None:
        return None
    if isinstance(time_zone, str):
        stripped = time_zone.strip()
        try:
            numeric = float(stripped)
        except ValueError:
            return stripped
    else:
        numeric = float(time_zone)
    key: int | float = int(numeric) if numeric.is_integer() else numeric
    return _TIME_ZONE_OFFSET_NAMES.get(key, str(time_zone))


def _build_location_dict(
    *,
    location: dict[str, Any] | None,
    city: str | None,
    region: str | None,
    latitude: float | None,
    longitude: float | None,
    time_zone: str | int | float | None,
    elevation: float | None,
    default_city: str,
) -> dict[str, Any]:
    if location is not None:
        return location
    if latitude is None or longitude is None or time_zone is None:
        raise ValueError(
            "Provide location, or provide latitude, longitude, and time_zone."
        )
    try:
        tz_value = float(time_zone)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "time_zone must be numeric when constructing a Location without location dict."
        ) from exc
    return {
        "type": "Location",
        "city": city or default_city,
        "state": region,
        "latitude": float(latitude),
        "longitude": float(longitude),
        "time_zone": tz_value,
        "elevation": 0 if elevation is None else float(elevation),
    }


def create_radiance_sky_asset(
    *,
    garden_root: str,
    asset_type: str,
    identifier: str | None = None,
    month: int | None = None,
    day: int | None = None,
    time: str | float | None = None,
    time_zone: str | int | float | None = None,
    solar_time: bool = False,
    solar_altitude: float | None = None,
    solar_azimuth: float | None = None,
    sky_type: str = "sunny",
    latitude: float | None = None,
    longitude: float | None = None,
    standard_meridian: float | None = None,
    ground_reflectance: float | None = None,
    sky_turbidity: float | None = None,
    solar_radiance: float | None = None,
    direct_horizontal_irradiance: float | None = None,
    zenith_brightness: float | None = None,
    diffuse_horizontal_irradiance: float | None = None,
    direct_normal_irradiance: float | None = None,
    direct_normal_illuminance: float | None = None,
    diffuse_horizontal_illuminance: float | None = None,
    output_mode: int | None = None,
    sky_part: str | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    stat_path: str | None = None,
    wea_target: dict[str, Any] | None = None,
    location: dict[str, Any] | None = None,
    city: str | None = None,
    region: str | None = None,
    elevation: float | None = None,
    sky_clearness: float = 1,
    timestep: int = 1,
    hoys: list[float] | None = None,
    hoy: float | None = None,
    is_leap_year: bool = False,
    write_hours: bool = False,
    north: float = 0,
    high_density: bool = False,
    compute: bool = False,
    irradiance: float | None = None,
    illuminance: float | None = None,
    uniform: bool = False,
    cloudy: bool | None = None,
    sky_density: int = 1,
    ground_emittance: float = 0.2,
    is_colored: bool = False,
    benefit_matrix: bool = False,
    balance_temperature: float = 15.0,
    balance_offset: float = 2.0,
    output_subdir: str | None = None,
    return_object_dict: bool = False,
) -> dict[str, Any]:
    """Create a Radiance sky file, WEA file, or SkyMatrix Garden target."""
    normalized = asset_type.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized == "cie_sky":
        return create_cie_standard_sky(
            garden_root=garden_root,
            identifier=identifier or "cie_standard_sky",
            month=month,
            day=day,
            time=time,
            time_zone=time_zone,
            solar_time=solar_time,
            solar_altitude=solar_altitude,
            solar_azimuth=solar_azimuth,
            sky_type=sky_type,
            latitude=latitude,
            longitude=longitude,
            standard_meridian=standard_meridian,
            ground_reflectance=ground_reflectance,
            sky_turbidity=sky_turbidity,
            solar_radiance=solar_radiance,
            direct_horizontal_irradiance=direct_horizontal_irradiance,
            zenith_brightness=zenith_brightness,
            diffuse_horizontal_irradiance=diffuse_horizontal_irradiance,
            output_subdir=output_subdir or RADIANCE_SKY_OUTPUT_SUBDIR,
        )
    if normalized == "climate_based_sky":
        return create_climate_based_sky(
            garden_root=garden_root,
            identifier=identifier or "climate_based_sky",
            month=month,
            day=day,
            time=time,
            time_zone=time_zone,
            solar_time=solar_time,
            solar_altitude=solar_altitude,
            solar_azimuth=solar_azimuth,
            direct_normal_irradiance=direct_normal_irradiance,
            diffuse_horizontal_irradiance=diffuse_horizontal_irradiance,
            direct_normal_illuminance=direct_normal_illuminance,
            diffuse_horizontal_illuminance=diffuse_horizontal_illuminance,
            output_mode=output_mode,
            sky_part=sky_part,
            latitude=latitude,
            longitude=longitude,
            standard_meridian=standard_meridian,
            ground_reflectance=ground_reflectance,
            output_subdir=output_subdir or RADIANCE_SKY_OUTPUT_SUBDIR,
        )
    if normalized == "certain_irradiance":
        return create_certain_irradiance_sky(
            garden_root=garden_root,
            identifier=identifier or "certain_irradiance",
            irradiance=irradiance,
            illuminance=illuminance,
            ground_reflectance=0.2 if ground_reflectance is None else ground_reflectance,
            uniform=uniform,
            cloudy=cloudy,
            output_subdir=output_subdir or RADIANCE_SKY_OUTPUT_SUBDIR,
        )
    if normalized == "from_epw_hoy":
        return create_epw_hoy_sky(
            garden_root=garden_root,
            identifier=identifier or "epw_hoy_sky",
            weather_target=weather_target,
            epw_path=epw_path,
            month=month,
            day=day,
            time=time,
            hoy=hoy,
            north=north,
            ground_reflectance=0.2 if ground_reflectance is None else ground_reflectance,
            is_colored=is_colored,
            output_subdir=output_subdir or RADIANCE_SKY_OUTPUT_SUBDIR,
        )
    if normalized == "skydome":
        return create_skydome_sky(
            garden_root=garden_root,
            identifier=identifier or "skydome",
            sky_density=sky_density,
            ground_emittance=ground_emittance,
            uniform=uniform,
            output_subdir=output_subdir or RADIANCE_SKY_OUTPUT_SUBDIR,
        )
    if normalized == "leed_illuminance":
        return create_leed_illuminance_skies(
            garden_root=garden_root,
            identifier=identifier or "leed",
            wea_target=wea_target,
            weather_target=weather_target,
            epw_path=epw_path,
            north=north,
            ground_reflectance=0.2 if ground_reflectance is None else ground_reflectance,
            output_subdir=output_subdir or RADIANCE_SKY_OUTPUT_SUBDIR,
        )
    if normalized == "abnt_nbr_15575":
        return create_abnt_nbr_15575_skies(
            garden_root=garden_root,
            identifier=identifier or "abnt_15575",
            wea_target=wea_target,
            weather_target=weather_target,
            epw_path=epw_path,
            north=north,
            ground_reflectance=0.2 if ground_reflectance is None else ground_reflectance,
            output_subdir=output_subdir or RADIANCE_SKY_OUTPUT_SUBDIR,
        )
    if normalized == "wea_from_epw":
        resolved_id = identifier
        if resolved_id is None:
            if isinstance(weather_target, dict) and weather_target.get("identifier"):
                resolved_id = str(weather_target["identifier"])
            elif epw_path:
                resolved_id = Path(epw_path).stem
            else:
                resolved_id = "weather_wea"
        return create_wea_from_weather_file(
            garden_root=garden_root,
            identifier=resolved_id,
            weather_target=weather_target,
            epw_path=epw_path,
            timestep=timestep,
            hoys=hoys,
            write_hours=write_hours,
            output_subdir=output_subdir or WEA_OUTPUT_SUBDIR,
            return_object_dict=return_object_dict,
        )
    if normalized == "wea_clear_sky":
        resolved_id = identifier or city or "ashrae_clear_sky_wea"
        resolved_location = _build_location_dict(
            location=location,
            city=city,
            region=region,
            latitude=latitude,
            longitude=longitude,
            time_zone=time_zone,
            elevation=elevation,
            default_city=resolved_id,
        )
        return create_ashrae_clear_sky_wea(
            garden_root=garden_root,
            identifier=resolved_id,
            location=resolved_location,
            sky_clearness=sky_clearness,
            timestep=timestep,
            is_leap_year=is_leap_year,
            output_subdir=output_subdir or WEA_OUTPUT_SUBDIR,
            write_hours=write_hours,
            return_object_dict=return_object_dict,
        )
    if normalized == "sky_matrix":
        resolved_id = identifier or "sky_matrix"
        resolved_location = location
        if (
            wea_target is None
            and weather_target is None
            and epw_path is None
            and stat_path is None
            and resolved_location is None
            and latitude is not None
        ):
            resolved_location = _build_location_dict(
                location=None,
                city=city,
                region=region,
                latitude=latitude,
                longitude=longitude,
                time_zone=time_zone,
                elevation=elevation,
                default_city=resolved_id,
            )
        return create_sky_matrix(
            garden_root=garden_root,
            identifier=resolved_id,
            wea_target=wea_target,
            weather_target=weather_target,
            epw_path=epw_path,
            stat_path=stat_path,
            location=resolved_location,
            sky_clearness=sky_clearness,
            hoys=hoys,
            benefit_matrix=benefit_matrix,
            balance_temperature=balance_temperature,
            balance_offset=balance_offset,
            north=north,
            high_density=high_density,
            ground_reflectance=0.2 if ground_reflectance is None else ground_reflectance,
            compute=compute,
            output_subdir=output_subdir or SKY_MATRIX_OUTPUT_SUBDIR,
        )
    raise ValueError(
        "asset_type must be one of: cie_sky, climate_based_sky, certain_irradiance, "
        "from_epw_hoy, skydome, leed_illuminance, abnt_nbr_15575, wea_from_epw, "
        "wea_clear_sky, sky_matrix."
    )
