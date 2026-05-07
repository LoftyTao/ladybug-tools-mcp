"""Honeybee Radiance sky and WEA foundation services."""

from __future__ import annotations

import json
from calendar import month_abbr
from pathlib import Path
from typing import Any

from honeybee_radiance_command.gendaylit import Gendaylit
from honeybee_radiance_command.gensky import Gensky
from honeybee_radiance_command.options.gendaylit import GendaylitOptions
from honeybee_radiance_command.options.gensky import GenskyOptions
from ladybug.location import Location
from ladybug.wea import Wea
from ladybug_radiance.skymatrix import SkyMatrix

from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from garden.run_energy.config import WEATHER_TARGET_TYPE
from ladybug_tools_mcp.contracts.receipts import make_artifact_receipt
from ladybug_tools_mcp.contracts.report import make_report

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
    normalized_subdir = output_subdir.strip().lower().replace("\\", "/")
    if normalized_subdir in {
        "wea",
        "weather/wea",
        "radiance/wea",
        "radiance/weather",
        "artifacts/wea",
    }:
        output_subdir = WEA_OUTPUT_SUBDIR
    elif normalized_subdir in {
        "sky",
        "skies",
        "sky_files",
        "radiance_sky",
        "radiance_skies",
        "radiance/sky",
        "radiance/sky_files",
        "artifacts/sky",
    }:
        output_subdir = RADIANCE_SKY_OUTPUT_SUBDIR
    output_dir = (garden_root / output_subdir).resolve()
    output_dir.relative_to(garden_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _normalize_sky_matrix_output_subdir(output_subdir: str) -> str:
    normalized_subdir = output_subdir.strip().lower().replace("\\", "/")
    if normalized_subdir in {
        "imports/weather",
        "weather",
        "wea",
        "sky_matrix",
        "sky_matrices",
        "radiance/sky_matrix",
        "radiance/sky_matrices",
        "artifacts/radiance/sky_matrix",
        "artifacts/radiance/sky_matrices",
        "artifacts/radiance/wea",
    }:
        return SKY_MATRIX_OUTPUT_SUBDIR
    return output_subdir


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
    manifest.artifacts = [
        item
        for item in manifest.artifacts
        if not (
            item.get("artifact_type") == artifact_type
            and item.get("path") == path
        )
    ]
    manifest.artifacts.append(record)
    return record


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
    wea_target = _unwrap_target(wea_target) or {}
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
) -> dict[str, Any]:
    safe_identifier = slugify_name(identifier)
    output_dir = _resolve_output_dir(garden_root_path, output_subdir)
    sky_path = (output_dir / f"{safe_identifier}.sky").resolve()
    sky_path.relative_to(garden_root_path)
    sky_path.write_text(f"!{command_text}\n", encoding="utf-8", newline="\n")

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
    time_zone: str | None = None,
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
        time_zone=time_zone,
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
    if isinstance(time_zone, int):
        _append_option(recipe_parts, "-tz", time_zone)
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
    time_zone: str | None = None,
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
        time_zone=time_zone,
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
    if isinstance(time_zone, int):
        _append_option(recipe_parts, "-tz", time_zone)
    _append_option(recipe_parts, "-dni", direct_normal_irradiance)
    _append_option(recipe_parts, "-dhi", diffuse_horizontal_irradiance)
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


def create_sky_matrix(
    *,
    garden_root: str,
    identifier: str,
    wea_target: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    location: dict[str, Any] | None = None,
    sky_clearness: float = 1,
    north: float = 0,
    high_density: bool = False,
    ground_reflectance: float = 0.2,
    compute: bool = False,
    output_subdir: str = SKY_MATRIX_OUTPUT_SUBDIR,
) -> dict[str, Any]:
    """Create a Garden target describing a Ladybug Radiance SkyMatrix."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    sources = [wea_target is not None, weather_target is not None or epw_path is not None, location is not None]
    if sum(1 for item in sources if item) != 1:
        raise ValueError("Provide exactly one sky source: wea_target, weather_target/epw_path, or location.")

    if wea_target is not None:
        source_type = "wea_file"
        wea_path = _resolve_wea_path(
            garden_root=garden_root_path,
            manifest=manifest,
            wea_target=wea_target,
        )
        source = {
            "source_type": source_type,
            "wea_target": _unwrap_target(wea_target),
            "wea_path": to_posix_relative(wea_path, garden_root_path),
        }
        wea = Wea.from_file(str(wea_path))
    elif weather_target is not None or epw_path is not None:
        resolved_epw, source = _resolve_epw_path(
            garden_root=garden_root_path,
            manifest=manifest,
            weather_target=weather_target,
            epw_path=epw_path,
        )
        source_type = str(source["source_type"])
        wea = Wea.from_epw_file(str(resolved_epw))
    else:
        location_obj = _location_from_input(location or {})
        source_type = "ashrae_clear_sky"
        source = {
            "source_type": source_type,
            "sky_clearness": sky_clearness,
            "location": location_obj.to_dict(),
        }
        wea = Wea.from_ashrae_clear_sky(location_obj, sky_clearness=sky_clearness)

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
    }
    payload: dict[str, Any] = {
        "type": SKY_MATRIX_TARGET_TYPE,
        "identifier": slugify_name(identifier),
        "source": source,
        "parameters": parameters,
    }
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
        metadata={"computed": compute},
    )
    return {
        "target": target,
        "sky_matrix_target": target,
        "artifact": artifact,
        "summary_view": _sky_matrix_summary(
            identifier=safe_identifier,
            target=target,
            source_type=source_type,
            parameters=parameters,
            sky_matrix=sky_matrix,
            computed=compute,
        ),
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
