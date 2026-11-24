"""Pure-Python Ladybug climate, weather, solar, psychrometric, and sky-model services."""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any

from ladybug.datacollection import HourlyContinuousCollection, HourlyDiscontinuousCollection
from ladybug.datatype.energyflux import Irradiance
from ladybug.datatype.fraction import HumidityRatio, RelativeHumidity
from ladybug.datatype.pressure import Pressure
from ladybug.datatype.specificenergy import Enthalpy
from ladybug.datatype.speed import WindSpeed
from ladybug.datatype.temperature import DewPointTemperature, DryBulbTemperature, Temperature, WetBulbTemperature
from ladybug.ddy import DDY
from ladybug.designday import DesignDay
from ladybug.epw import EPW, EPWFields
from ladybug.header import Header
from ladybug.location import Location
from ladybug.north import WorldMagneticModel
import ladybug.psychrometrics as psy
import ladybug.skymodel as skymodel
from ladybug.stat import STAT
from ladybug.sunpath import Sunpath
from ladybug.wea import Wea
from ladybug.windprofile import WindProfile

from garden.analysis_period import analysis_period_from_input, analysis_period_summary
from garden.data_collection import (
    collection_from_dict,
    data_collection_summary,
    load_data_collection,
    save_data_collection,
)
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from garden.radiance.sky import WEA_ARTIFACT_TYPE, WEA_TARGET_TYPE
from garden.run_energy.config import WEATHER_TARGET_TYPE, make_garden_weather_target, resolve_garden_weather_epw
from ladybug_tools_mcp.contracts import make_artifact_receipt, make_report


WEATHER_ARTIFACT_SUBDIR = "artifacts/weather"
DDY_ARTIFACT_TYPE = "ddy_file"
MOS_ARTIFACT_TYPE = "mos_file"
EPW_ARTIFACT_TYPE = "epw_file"

_EPW_FIELD_NUMBER_BY_NAME: dict[str, int] = {}
for _num in range(6, 35):
    _field = EPWFields.field_by_number(_num)
    _key = re.sub(r"[^a-zA-Z0-9]+", "_", _field.name.name).strip("_").lower()
    _EPW_FIELD_NUMBER_BY_NAME[_key] = _num

_PSY_FUNCTIONS: dict[str, Any] = {
    name: getattr(psy, name)
    for name in dir(psy)
    if not name.startswith("_") and callable(getattr(psy, name)) and getattr(psy, name).__module__ == psy.__name__
}

_PSY_OUTPUT_DATATYPES = {
    "db_temp_from_enth_hr": (DryBulbTemperature, "C"),
    "db_temp_from_rh_hr": (DryBulbTemperature, "C"),
    "dew_point_from_db_enth": (DewPointTemperature, "C"),
    "dew_point_from_db_hr": (DewPointTemperature, "C"),
    "dew_point_from_db_rh": (DewPointTemperature, "C"),
    "dew_point_from_db_rh_fast": (DewPointTemperature, "C"),
    "dew_point_from_db_wb": (DewPointTemperature, "C"),
    "enthalpy_from_db_hr": (Enthalpy, "kJ/kg"),
    "humid_ratio_from_db_rh": (HumidityRatio, "fraction"),
    "humid_ratio_from_db_wb": (HumidityRatio, "fraction"),
    "rel_humid_from_db_dpt": (RelativeHumidity, "%"),
    "rel_humid_from_db_enth": (RelativeHumidity, "%"),
    "rel_humid_from_db_hr": (RelativeHumidity, "%"),
    "rel_humid_from_db_wb": (RelativeHumidity, "%"),
    "saturated_vapor_pressure": (Pressure, "Pa"),
    "wet_bulb_from_db_hr": (WetBulbTemperature, "C"),
    "wet_bulb_from_db_rh": (WetBulbTemperature, "C"),
    "wet_bulb_from_db_rh_fast": (WetBulbTemperature, "C"),
}


def _resolve_garden_path(
    garden_root_path: Path,
    raw_path: str,
    *,
    field_name: str,
    suffix: str | None = None,
    must_exist: bool = True,
) -> Path:
    path = Path(raw_path).expanduser()
    resolved = path.resolve() if path.is_absolute() else (garden_root_path / path).resolve()
    try:
        resolved.relative_to(garden_root_path)
    except ValueError as exc:
        raise ValueError(f"{field_name} must stay inside the Garden root.") from exc
    if suffix is not None and resolved.suffix.lower() != suffix.lower():
        raise ValueError(f"{field_name} must reference a {suffix} file.")
    if must_exist and not resolved.is_file():
        raise ValueError(f"{field_name} file not found: {raw_path}")
    return resolved


def _resolve_weather_files(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
    stat_path: str | None,
    ddy_path: str | None,
    require_epw: bool = False,
) -> tuple[Path | None, Path | None, Path | None, dict[str, Any]]:
    resolved_epw: Path | None = None
    resolved_stat: Path | None = None
    resolved_ddy: Path | None = None
    source: dict[str, Any] = {}

    if weather_target is not None:
        resolved_epw = resolve_garden_weather_epw(
            garden_root=garden_root_path,
            manifest=manifest,
            weather_target=weather_target,
        )
        source["weather_target"] = weather_target
        source["epw_path"] = to_posix_relative(resolved_epw, garden_root_path)
        for key, target_attr in (("stat", "stat_path"), ("ddy", "ddy_path")):
            val = weather_target.get(target_attr)
            if isinstance(val, str) and val:
                cand = _resolve_garden_path(
                    garden_root_path, val, field_name=f"weather_target.{target_attr}", must_exist=False
                )
                if cand.is_file():
                    if key == "stat":
                        resolved_stat = cand
                    else:
                        resolved_ddy = cand
    elif epw_path is not None:
        resolved_epw = _resolve_garden_path(
            garden_root_path, epw_path, field_name="epw_path", suffix=".epw"
        )
        source["epw_path"] = to_posix_relative(resolved_epw, garden_root_path)

    if resolved_epw is not None:
        sib_stat = resolved_epw.with_suffix(".stat")
        sib_ddy = resolved_epw.with_suffix(".ddy")
        if resolved_stat is None and sib_stat.is_file():
            resolved_stat = sib_stat
        if resolved_ddy is None and sib_ddy.is_file():
            resolved_ddy = sib_ddy

    if stat_path is not None:
        resolved_stat = _resolve_garden_path(
            garden_root_path, stat_path, field_name="stat_path", suffix=".stat"
        )
    if ddy_path is not None:
        resolved_ddy = _resolve_garden_path(
            garden_root_path, ddy_path, field_name="ddy_path", suffix=".ddy"
        )

    if require_epw and resolved_epw is None:
        raise ValueError("Provide weather_target or epw_path.")
    if resolved_stat is not None:
        source["stat_path"] = to_posix_relative(resolved_stat, garden_root_path)
    if resolved_ddy is not None:
        source["ddy_path"] = to_posix_relative(resolved_ddy, garden_root_path)
    return resolved_epw, resolved_stat, resolved_ddy, source


def _location_from_inputs(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    location: dict[str, Any] | None,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
) -> Location:
    if location is not None:
        data = dict(location)
        data.setdefault("type", "Location")
        return Location.from_dict(data)
    if weather_target is not None or epw_path is not None:
        resolved_epw, _, _, _ = _resolve_weather_files(
            garden_root_path=garden_root_path,
            manifest=manifest,
            weather_target=weather_target,
            epw_path=epw_path,
            stat_path=None,
            ddy_path=None,
            require_epw=True,
        )
        return EPW(str(resolved_epw)).location
    raise ValueError("Provide location, weather_target, or epw_path.")


def _serialize_ground_temps(ground_temps: dict[Any, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for depth, col in (ground_temps or {}).items():
        if hasattr(col, "values"):
            out[str(depth)] = {
                "unit": getattr(col.header, "unit", "C"),
                "monthly_values": list(col.values),
            }
        else:
            out[str(depth)] = col
    return out


def _serialize_period(period: Any) -> dict[str, Any] | None:
    if period is None:
        return None
    if hasattr(period, "to_dict"):
        return period.to_dict()
    return str(period)


def _ddy_summary(ddy_obj: DDY) -> dict[str, Any]:
    days = []
    for dd in ddy_obj.design_days:
        dd_dict = dd.to_dict()
        days.append(
            {
                "name": dd.name,
                "day_type": dd.day_type,
                "month": dd_dict.get("dry_bulb_condition", {}).get("month")
                or dd.analysis_period.st_month if hasattr(dd, "analysis_period") else None,
                "day": dd_dict.get("dry_bulb_condition", {}).get("day")
                or dd.analysis_period.st_day if hasattr(dd, "analysis_period") else None,
                "dry_bulb_max": dd.dry_bulb_condition.dry_bulb_max,
                "dry_bulb_range": dd.dry_bulb_condition.dry_bulb_range,
                "humidity_type": dd.humidity_condition.humidity_type,
                "humidity_value": dd.humidity_condition.humidity_value,
                "wind_speed": dd.wind_condition.wind_speed,
                "wind_direction": dd.wind_condition.wind_direction,
                "sky_type": dd_dict.get("sky_condition", {}).get("type"),
            }
        )
    return {
        "location": ddy_obj.location.to_dict(),
        "design_day_count": len(days),
        "design_days": days,
    }


def _stat_summary(stat_obj: STAT) -> dict[str, Any]:
    raw = stat_obj.to_dict()
    return {
        "location": raw.get("location"),
        "ashrae_climate_zone": raw.get("ashrae_climate_zone"),
        "koppen_climate_zone": raw.get("koppen_climate_zone"),
        "extreme_cold_week": raw.get("extreme_cold_week"),
        "extreme_hot_week": raw.get("extreme_hot_week"),
        "typical_weeks": raw.get("typical_weeks"),
        "heating_dict": raw.get("heating_dict"),
        "cooling_dict": raw.get("cooling_dict"),
        "standard_pressure_at_elev": raw.get("standard_pressure_at_elev"),
        "monthly_tau_beam": raw.get("monthly_tau_beam"),
        "monthly_tau_diffuse": raw.get("monthly_tau_diffuse"),
        "monthly_db_50": raw.get("monthly_db_50"),
        "monthly_wb_50": raw.get("monthly_wb_50"),
        "monthly_db_04": raw.get("monthly_db_04"),
        "monthly_wb_04": raw.get("monthly_wb_04"),
        "monthly_wind": raw.get("monthly_wind"),
        "monthly_wind_dirs": raw.get("monthly_wind_dirs"),
    }


def _inspect_weather(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
    stat_path: str | None,
    ddy_path: str | None,
) -> dict[str, Any]:
    resolved_epw, resolved_stat, resolved_ddy, source = _resolve_weather_files(
        garden_root_path=garden_root_path,
        manifest=manifest,
        weather_target=weather_target,
        epw_path=epw_path,
        stat_path=stat_path,
        ddy_path=ddy_path,
        require_epw=False,
    )
    if resolved_epw is None and resolved_stat is None and resolved_ddy is None:
        raise ValueError("Provide weather_target, epw_path, stat_path, or ddy_path.")

    summary_view: dict[str, Any] = {
        "garden_target": manifest.target(),
        "source": source,
    }
    if resolved_epw is not None:
        epw = EPW(str(resolved_epw))
        years = list(getattr(epw.years, "values", []) or [])
        summary_view["epw"] = {
            "location": epw.location.to_dict(),
            "comments_1": epw.comments_1,
            "comments_2": epw.comments_2,
            "is_leap_year": epw.is_leap_year,
            "is_ip": epw.is_ip,
            "years_range": [min(years), max(years)] if years else None,
            "ashrae_climate_zone": epw.ashrae_climate_zone,
            "monthly_ground_temperature": _serialize_ground_temps(epw.monthly_ground_temperature),
            "extreme_cold_weeks": {str(k): _serialize_period(v) for k, v in (epw.extreme_cold_weeks or {}).items()},
            "extreme_hot_weeks": {str(k): _serialize_period(v) for k, v in (epw.extreme_hot_weeks or {}).items()},
            "typical_weeks": {str(k): _serialize_period(v) for k, v in (epw.typical_weeks or {}).items()},
            "heating_design_conditions": dict(epw.heating_design_condition_dictionary or {}),
            "cooling_design_conditions": dict(epw.cooling_design_condition_dictionary or {}),
            "extreme_design_conditions": dict(epw.extreme_design_condition_dictionary or {}),
        }
    if resolved_stat is not None:
        summary_view["stat"] = _stat_summary(STAT(str(resolved_stat)))
    if resolved_ddy is not None:
        summary_view["ddy"] = _ddy_summary(DDY.from_ddy_file(str(resolved_ddy)))

    return {
        "summary_view": summary_view,
        "report": make_report(status="ok", message="Weather files inspected."),
    }


def _resolve_collection_arg(
    garden_root_path: Path,
    val: Any,
    *,
    field_name: str,
) -> Any:
    if isinstance(val, dict):
        if val.get("target_type") == "ladybug_data_collection":
            return load_data_collection(garden_root=garden_root_path, data_collection_target=val)
        return collection_from_dict(val)
    raise ValueError(f"{field_name} must be a ladybug_data_collection target or DataCollection dict.")


def _register_file_artifact(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    artifact_type: str,
    name: str,
    file_path: Path,
    source: dict[str, Any],
    target_type: str | None = None,
    domain: str = "ladybug",
) -> dict[str, Any]:
    resolved = file_path.resolve()
    resolved.relative_to(garden_root_path)
    rel_path = to_posix_relative(resolved, garden_root_path)
    artifact = manifest.upsert_artifact(
        {
            "artifact_type": artifact_type,
            "name": name,
            "path": rel_path,
            "source": source,
            "created_at": utc_now_iso(),
        }
    )
    manifest.write(garden_root_path)
    receipt = make_artifact_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        artifact_type=artifact_type,
        artifact_path=rel_path,
        absolute_path=str(resolved),
        source=source,
    )
    target = (
        {
            "target_type": target_type,
            "domain": domain,
            "garden_id": manifest.garden_id,
            "identifier": name,
            "path": rel_path,
        }
        if target_type
        else {
            "target_type": "artifact",
            "domain": domain,
            "garden_id": manifest.garden_id,
            "artifact_type": artifact_type,
            "identifier": name,
            "path": rel_path,
        }
    )
    return {
        "target": target,
        "artifact": artifact,
        "persistence_receipt": receipt,
        "artifact_path": rel_path,
        "absolute_path": str(resolved),
    }


def _translate_weather(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    translation_type: str,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
    stat_path: str | None,
    location: dict[str, Any] | None,
    percentile: float = 0.4,
    annual_percentile: float = 0.4,
    monthly_percentile: float = 5.0,
    hoys: list[float] | None = None,
    timestep: int = 1,
    is_leap_year: bool = False,
    use_2017: bool = False,
    monthly_tau_beam: list[float] | None = None,
    monthly_tau_diffuse: list[float] | None = None,
    cloud_cover_target: dict[str, Any] | None = None,
    relative_humidity_target: dict[str, Any] | None = None,
    dry_bulb_temperature_target: dict[str, Any] | None = None,
    wind_speed_target: dict[str, Any] | None = None,
    atmospheric_pressure_target: dict[str, Any] | None = None,
    use_disc: bool = False,
    identifier: str | None = None,
    output_subdir: str = WEATHER_ARTIFACT_SUBDIR,
) -> dict[str, Any]:
    kind = str(translation_type).strip().lower()
    kind_aliases = {
        "wea_from_stat": "stat_to_wea",
        "wea_from_clear_sky": "ashrae_revised_clear_sky_wea",
        "wea_from_ashrae_revised_clear_sky": "ashrae_revised_clear_sky_wea",
        "wea_from_zhang_huang": "zhang_huang_solar_wea",
        "wea_from_zhang_huang_solar": "zhang_huang_solar_wea",
    }
    kind = kind_aliases.get(kind, kind)
    resolved_epw, resolved_stat, _, source = _resolve_weather_files(
        garden_root_path=garden_root_path,
        manifest=manifest,
        weather_target=weather_target,
        epw_path=epw_path,
        stat_path=stat_path,
        ddy_path=None,
        require_epw=False,
    )
    out_dir = (garden_root_path / output_subdir).resolve()
    out_dir.relative_to(garden_root_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = slugify_name(identifier or f"weather_{kind}")

    extra_summary: dict[str, Any] = {"translation_type": kind}
    if kind in {"epw_to_ddy", "epw_to_ddy_monthly_cooling", "epw_to_wea", "epw_to_mos"}:
        if resolved_epw is None:
            raise ValueError(f"translation_type={kind!r} requires weather_target or epw_path.")
        epw = EPW(str(resolved_epw))
        if kind == "epw_to_ddy":
            out_path = out_dir / f"{safe_name}.ddy"
            written = Path(epw.to_ddy(str(out_path), percentile=percentile))
            art_type, tgt_type = DDY_ARTIFACT_TYPE, None
            extra_summary["ddy"] = _ddy_summary(DDY.from_ddy_file(str(written)))
        elif kind == "epw_to_ddy_monthly_cooling":
            out_path = out_dir / f"{safe_name}.ddy"
            written = Path(
                epw.to_ddy_monthly_cooling(
                    str(out_path),
                    annual_percentile=annual_percentile,
                    monthly_percentile=monthly_percentile,
                )
            )
            art_type, tgt_type = DDY_ARTIFACT_TYPE, None
            extra_summary["ddy"] = _ddy_summary(DDY.from_ddy_file(str(written)))
        elif kind == "epw_to_wea":
            out_path = out_dir / f"{safe_name}.wea"
            written = Path(epw.to_wea(str(out_path), hoys=hoys))
            art_type, tgt_type = WEA_ARTIFACT_TYPE, WEA_TARGET_TYPE
        else:
            out_path = out_dir / f"{safe_name}.mos"
            written = Path(epw.to_mos(str(out_path)))
            art_type, tgt_type = MOS_ARTIFACT_TYPE, None
    elif kind in {"stat_to_ddy", "stat_to_wea"}:
        if resolved_stat is None:
            raise ValueError(f"translation_type={kind!r} requires stat_path or weather_target with .stat.")
        if kind == "stat_to_ddy":
            out_path = out_dir / f"{safe_name}.ddy"
            written = Path(STAT(str(resolved_stat)).to_ddy(str(out_path), percentile=percentile))
            art_type, tgt_type = DDY_ARTIFACT_TYPE, None
            extra_summary["ddy"] = _ddy_summary(DDY.from_ddy_file(str(written)))
        else:
            wea = Wea.from_stat_file(
                str(resolved_stat),
                timestep=timestep,
                is_leap_year=is_leap_year,
                use_2017=use_2017,
            )
            out_path = out_dir / f"{safe_name}.wea"
            written = Path(wea.write(str(out_path)))
            art_type, tgt_type = WEA_ARTIFACT_TYPE, WEA_TARGET_TYPE
            extra_summary["wea_timestep_count"] = len(wea)
    elif kind == "ashrae_revised_clear_sky_wea":
        loc_obj = _location_from_inputs(
            garden_root_path=garden_root_path,
            manifest=manifest,
            location=location,
            weather_target=weather_target,
            epw_path=epw_path,
        )
        if monthly_tau_beam is None or monthly_tau_diffuse is None:
            if resolved_stat is not None:
                st = STAT(str(resolved_stat))
                monthly_tau_beam = monthly_tau_beam or st.monthly_tau_beam
                monthly_tau_diffuse = monthly_tau_diffuse or st.monthly_tau_diffuse
        if not monthly_tau_beam or not monthly_tau_diffuse:
            raise ValueError(
                "monthly_tau_beam and monthly_tau_diffuse (12 values each) or a .stat file are required."
            )
        wea = Wea.from_ashrae_revised_clear_sky(
            loc_obj,
            monthly_tau_beam=monthly_tau_beam,
            monthly_tau_diffuse=monthly_tau_diffuse,
            timestep=timestep,
            is_leap_year=is_leap_year,
            use_2017=use_2017,
        )
        out_path = out_dir / f"{safe_name}.wea"
        written = Path(wea.write(str(out_path)))
        art_type, tgt_type = WEA_ARTIFACT_TYPE, WEA_TARGET_TYPE
        extra_summary["wea_timestep_count"] = len(wea)
    elif kind == "zhang_huang_solar_wea":
        loc_obj = _location_from_inputs(
            garden_root_path=garden_root_path,
            manifest=manifest,
            location=location,
            weather_target=weather_target,
            epw_path=epw_path,
        )
        epw_fallback = EPW(str(resolved_epw)) if resolved_epw is not None else None
        cc = (
            _resolve_collection_arg(garden_root_path, cloud_cover_target, field_name="cloud_cover_target")
            if cloud_cover_target is not None
            else (epw_fallback.total_sky_cover if epw_fallback else None)
        )
        rh = (
            _resolve_collection_arg(garden_root_path, relative_humidity_target, field_name="relative_humidity_target")
            if relative_humidity_target is not None
            else (epw_fallback.relative_humidity if epw_fallback else None)
        )
        dbt = (
            _resolve_collection_arg(garden_root_path, dry_bulb_temperature_target, field_name="dry_bulb_temperature_target")
            if dry_bulb_temperature_target is not None
            else (epw_fallback.dry_bulb_temperature if epw_fallback else None)
        )
        ws = (
            _resolve_collection_arg(garden_root_path, wind_speed_target, field_name="wind_speed_target")
            if wind_speed_target is not None
            else (epw_fallback.wind_speed if epw_fallback else None)
        )
        if cc is None or rh is None or dbt is None or ws is None:
            raise ValueError(
                "zhang_huang_solar_wea requires weather_target/epw_path or all four "
                "cloud_cover_target, relative_humidity_target, dry_bulb_temperature_target, wind_speed_target."
            )
        atm_p = (
            _resolve_collection_arg(garden_root_path, atmospheric_pressure_target, field_name="atmospheric_pressure_target")
            if atmospheric_pressure_target is not None
            else (epw_fallback.atmospheric_station_pressure if epw_fallback else None)
        )
        wea = Wea.from_zhang_huang_solar(
            loc_obj, cc, rh, dbt, ws, atmospheric_pressure=atm_p, use_disc=use_disc
        )
        out_path = out_dir / f"{safe_name}.wea"
        written = Path(wea.write(str(out_path)))
        art_type, tgt_type = WEA_ARTIFACT_TYPE, WEA_TARGET_TYPE
        extra_summary["wea_timestep_count"] = len(wea)
    else:
        raise ValueError(
            "translation_type must be one of: epw_to_ddy, epw_to_ddy_monthly_cooling, epw_to_wea, "
            "epw_to_mos, stat_to_ddy, stat_to_wea, ashrae_revised_clear_sky_wea, zhang_huang_solar_wea."
        )

    reg = _register_file_artifact(
        garden_root_path=garden_root_path,
        manifest=manifest,
        artifact_type=art_type,
        name=safe_name,
        file_path=written,
        source={"producer": "LB_Climate_Calc", "action": "translate_weather", **source, "translation_type": kind},
        target_type=tgt_type,
    )
    return {
        "target": reg["target"],
        "artifact": reg["artifact"],
        "persistence_receipt": reg["persistence_receipt"],
        "summary_view": {
            "garden_target": manifest.target(),
            "artifact_path": reg["artifact_path"],
            **extra_summary,
        },
        "report": make_report(status="ok", message=f"Weather translated via {kind}."),
    }


def _write_epw(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
    field_updates: dict[str, Any] | None,
    location: dict[str, Any] | None,
    comments_1: str | None,
    comments_2: str | None,
    identifier: str | None,
    register_weather_target: bool = True,
) -> dict[str, Any]:
    resolved_epw, _, _, source = _resolve_weather_files(
        garden_root_path=garden_root_path,
        manifest=manifest,
        weather_target=weather_target,
        epw_path=epw_path,
        stat_path=None,
        ddy_path=None,
        require_epw=True,
    )
    epw = EPW(str(resolved_epw))
    if location is not None:
        loc_dict = dict(location)
        loc_dict.setdefault("type", "Location")
        epw.location = Location.from_dict(loc_dict)
    if comments_1 is not None:
        epw.comments_1 = comments_1
    if comments_2 is not None:
        epw.comments_2 = comments_2

    updated_fields: list[str] = []
    for raw_field, raw_val in (field_updates or {}).items():
        key = re.sub(r"[^a-zA-Z0-9]+", "_", str(raw_field)).strip("_").lower()
        field_num = _EPW_FIELD_NUMBER_BY_NAME.get(key)
        if field_num is None:
            raise ValueError(f"Unsupported EPW field for update: {raw_field!r}.")
        existing_col = getattr(epw, key)
        if isinstance(raw_val, dict):
            col = _resolve_collection_arg(garden_root_path, raw_val, field_name=raw_field)
            values_list = list(col.values)
        elif isinstance(raw_val, (list, tuple)):
            values_list = [float(v) for v in raw_val]
        elif isinstance(raw_val, (int, float)) and not isinstance(raw_val, bool):
            values_list = [float(raw_val)] * len(existing_col)
        else:
            raise ValueError(
                f"field_updates[{raw_field!r}] must be a numeric scalar, list of values, or DataCollection target."
            )
        if len(values_list) != len(existing_col):
            raise ValueError(
                f"field_updates[{raw_field!r}] length ({len(values_list)}) must match EPW length ({len(existing_col)})."
            )
        updated_col = HourlyContinuousCollection(existing_col.header.duplicate(), values_list)
        epw.set_data_by_field(updated_col, field_num)
        updated_fields.append(key)

    safe_name = slugify_name(identifier or f"{resolved_epw.stem}_modified")
    out_dir = (garden_root_path / "imports" / "weather" / safe_name).resolve()
    out_dir.relative_to(garden_root_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_epw = out_dir / f"{safe_name}.epw"
    epw.write(str(out_epw))

    if register_weather_target:
        w_target = make_garden_weather_target(
            garden_root=garden_root_path,
            manifest=manifest,
            identifier=safe_name,
            epw_path=out_epw,
            ddy_path=None,
            stat_path=None,
            metadata={"station": epw.location.city, "source": "LB_Climate_Calc"},
        )
        manifest.weather_files = [
            item for item in manifest.weather_files if item.get("identifier") != safe_name
        ]
        manifest.weather_files.append(w_target)
        manifest.write(garden_root_path)
        target_out = w_target
    else:
        target_out = None

    reg = _register_file_artifact(
        garden_root_path=garden_root_path,
        manifest=manifest,
        artifact_type=EPW_ARTIFACT_TYPE,
        name=safe_name,
        file_path=out_epw,
        source={"producer": "LB_Climate_Calc", "action": "write_epw", **source, "updated_fields": updated_fields},
    )
    return {
        "target": target_out or reg["target"],
        "weather_target": target_out,
        "artifact": reg["artifact"],
        "persistence_receipt": reg["persistence_receipt"],
        "summary_view": {
            "garden_target": manifest.target(),
            "artifact_path": reg["artifact_path"],
            "epw_path": reg["artifact_path"],
            "updated_fields": updated_fields,
            "location": epw.location.to_dict(),
        },
        "report": make_report(status="ok", message=f"EPW written: {safe_name}.epw"),
    }


def _write_ddy(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    weather_target: dict[str, Any] | None,
    ddy_path: str | None,
    location: dict[str, Any] | None,
    design_days: list[dict[str, Any]] | None,
    filter_keyword: str | None,
    identifier: str | None,
    output_subdir: str = WEATHER_ARTIFACT_SUBDIR,
) -> dict[str, Any]:
    _, _, resolved_ddy, source = _resolve_weather_files(
        garden_root_path=garden_root_path,
        manifest=manifest,
        weather_target=weather_target,
        epw_path=None,
        stat_path=None,
        ddy_path=ddy_path,
        require_epw=False,
    )
    if design_days is not None:
        loc_obj = _location_from_inputs(
            garden_root_path=garden_root_path,
            manifest=manifest,
            location=location,
            weather_target=weather_target,
            epw_path=None,
        )
        dd_objs = [DesignDay.from_dict({"type": "DesignDay", **dd}) for dd in design_days]
        ddy_obj = DDY(loc_obj, dd_objs)
    elif resolved_ddy is not None:
        ddy_obj = DDY.from_ddy_file(str(resolved_ddy))
    else:
        raise ValueError("write_ddy requires ddy_path, weather_target with .ddy, or design_days.")

    if filter_keyword:
        ddy_obj = ddy_obj.filter_by_keyword(filter_keyword)

    out_dir = (garden_root_path / output_subdir).resolve()
    out_dir.relative_to(garden_root_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = slugify_name(identifier or "custom_design_days")
    out_ddy = out_dir / f"{safe_name}.ddy"
    ddy_obj.write(str(out_ddy))
    reg = _register_file_artifact(
        garden_root_path=garden_root_path,
        manifest=manifest,
        artifact_type=DDY_ARTIFACT_TYPE,
        name=safe_name,
        file_path=out_ddy,
        source={"producer": "LB_Climate_Calc", "action": "write_ddy", **source, "filter_keyword": filter_keyword},
    )
    return {
        "target": reg["target"],
        "artifact": reg["artifact"],
        "persistence_receipt": reg["persistence_receipt"],
        "summary_view": {
            "garden_target": manifest.target(),
            "artifact_path": reg["artifact_path"],
            "ddy_path": reg["artifact_path"],
            "ddy": _ddy_summary(ddy_obj),
        },
        "report": make_report(status="ok", message=f"DDY written: {safe_name}.ddy"),
    }


def _calc_sunpath(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    location: dict[str, Any] | None,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
    north_angle: float = 0.0,
    hoys: list[float] | None = None,
    analysis_period: dict[str, Any] | str | None = None,
    month: int | None = None,
    day: int | None = None,
    hour: float | None = None,
    solar_time: bool = False,
    depression: float = 0.5334,
) -> dict[str, Any]:
    loc_obj = _location_from_inputs(
        garden_root_path=garden_root_path,
        manifest=manifest,
        location=location,
        weather_target=weather_target,
        epw_path=epw_path,
    )
    sp = Sunpath.from_location(loc_obj, north_angle=north_angle)
    resolved_hoys = list(hoys or [])
    if not resolved_hoys and analysis_period is not None:
        ap = analysis_period_from_input(analysis_period)
        if ap is not None:
            resolved_hoys = list(ap.hoys)
    if not resolved_hoys and month is not None and day is not None and hour is not None:
        sun = sp.calculate_sun(month, day, hour, is_solar_time=solar_time)
        resolved_hoys = [sun.datetime.hoy]

    suns_out: list[dict[str, Any]] = []
    for hoy in resolved_hoys:
        sun = sp.calculate_sun_from_hoy(float(hoy), is_solar_time=solar_time)
        suns_out.append(
            {
                "hoy": float(hoy),
                "datetime": str(sun.datetime),
                "altitude": float(sun.altitude),
                "azimuth": float(sun.azimuth),
                "is_during_day": bool(sun.is_during_day),
                "sun_vector": [float(v) for v in sun.sun_vector.to_array()],
            }
        )

    sunrise_sunset: dict[str, Any] | None = None
    if month is not None and day is not None:
        sr_ss = sp.calculate_sunrise_sunset(
            month, day, depression=depression, is_solar_time=solar_time
        )
        sunrise_sunset = {
            "month": month,
            "day": day,
            "sunrise": str(sr_ss["sunrise"]) if sr_ss.get("sunrise") else None,
            "noon": str(sr_ss["noon"]) if sr_ss.get("noon") else None,
            "sunset": str(sr_ss["sunset"]) if sr_ss.get("sunset") else None,
        }

    return {
        "suns": suns_out,
        "sunrise_sunset": sunrise_sunset,
        "summary_view": {
            "location": loc_obj.to_dict(),
            "north_angle": north_angle,
            "solar_time": solar_time,
            "sun_count": len(suns_out),
            "daytime_sun_count": sum(1 for s in suns_out if s["is_during_day"]),
            "sunrise_sunset": sunrise_sunset,
        },
        "report": make_report(status="ok", message="Sunpath calculations completed."),
    }


def _calc_psychrometrics(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    operation: str,
    inputs: dict[str, Any],
    identifier: str | None,
    return_data_collection: bool,
) -> dict[str, Any]:
    op = str(operation).strip().lower()
    fn = _PSY_FUNCTIONS.get(op)
    if fn is None:
        allowed = ", ".join(sorted(_PSY_FUNCTIONS))
        raise ValueError(f"Unsupported psychrometrics operation {operation!r}. Allowed: {allowed}.")

    sig = inspect.signature(fn)
    alias_map = {
        "db_temp": ("dry_bulb", "dry_bulb_temperature", "db", "ta"),
        "wb_temp": ("wet_bulb", "wet_bulb_temperature", "wb"),
        "wet_bulb": ("wb_temp", "wet_bulb_temperature", "wb"),
        "rel_humid": ("relative_humidity", "rh"),
        "humid_ratio": ("humidity_ratio", "hr"),
        "dew_pt": ("dew_point", "dew_point_temperature", "dpt", "tdp"),
        "enthalpy": ("enth",),
        "b_press": ("pressure", "atmospheric_pressure", "barometric_pressure"),
        "t_kelvin": ("temperature_kelvin", "kelvin", "tk"),
    }

    bound_kwargs: dict[str, Any] = {}
    collection_template: Any = None
    collection_args: dict[str, list[float]] = {}
    scalar_args: dict[str, float] = {}

    for pname, param in sig.parameters.items():
        val = inputs.get(pname)
        if val is None:
            for alt in alias_map.get(pname, ()):
                if alt in inputs and inputs[alt] is not None:
                    val = inputs[alt]
                    break
        if val is None and pname == "t_kelvin" and inputs.get("temperature_c") is not None:
            c_val = inputs["temperature_c"]
            if isinstance(c_val, dict):
                col = _resolve_collection_arg(garden_root_path, c_val, field_name="temperature_c")
                collection_template = collection_template or col
                collection_args[pname] = [float(v) + 273.15 for v in col.values]
                continue
            val = float(c_val) + 273.15
        if val is None:
            if param.default is inspect.Parameter.empty:
                raise ValueError(f"Missing required psychrometrics input {pname!r} for {op}.")
            scalar_args[pname] = float(param.default)
            continue
        if isinstance(val, dict):
            col = _resolve_collection_arg(garden_root_path, val, field_name=pname)
            collection_template = collection_template or col
            collection_args[pname] = [float(v) for v in col.values]
        else:
            scalar_args[pname] = float(val)

    if collection_template is None:
        out_val = fn(**scalar_args)
        if op == "db_temp_and_hr_from_wb_rh":
            result_dict = {"dry_bulb_temperature": float(out_val[0]), "humidity_ratio": float(out_val[1])}
        else:
            result_dict = {"value": float(out_val)}
        return {
            **result_dict,
            "summary_view": {"operation": op, **result_dict},
            "report": make_report(status="ok", message=f"Psychrometrics '{op}' computed."),
        }

    n = len(collection_template)
    for cname, cvals in collection_args.items():
        if len(cvals) != n:
            raise ValueError(f"Psychrometrics input {cname!r} length ({len(cvals)}) must match {n}.")

    out_values_primary: list[float] = []
    out_values_secondary: list[float] = []
    for idx in range(n):
        call_kwargs = dict(scalar_args)
        for cname, cvals in collection_args.items():
            call_kwargs[cname] = cvals[idx]
        res = fn(**call_kwargs)
        if op == "db_temp_and_hr_from_wb_rh":
            out_values_primary.append(float(res[0]))
            out_values_secondary.append(float(res[1]))
        else:
            out_values_primary.append(float(res))

    def _save_psy_col(vals: list[float], dt_cls: type[Any], unit_str: str, suffix_name: str) -> dict[str, Any]:
        meta = dict(collection_template.header.metadata or {})
        meta["psychrometrics_operation"] = op
        hdr = Header(
            dt_cls(),
            unit_str,
            collection_template.header.analysis_period,
            metadata=meta,
        )
        out_col = (
            HourlyContinuousCollection(hdr, vals)
            if isinstance(collection_template, HourlyContinuousCollection)
            else type(collection_template)(hdr, vals, collection_template.datetimes)
        )
        return save_data_collection(
            garden_root=garden_root_path,
            data_collection=out_col,
            identifier=identifier or f"psy_{op}{suffix_name}",
            source={"producer": "LB_Climate_Calc", "action": "psychrometrics", "operation": op},
        )

    if op == "db_temp_and_hr_from_wb_rh":
        s1 = _save_psy_col(out_values_primary, DryBulbTemperature, "C", "_db")
        s2 = _save_psy_col(out_values_secondary, HumidityRatio, "fraction", "_hr")
        return {
            "target": s1["target"],
            "targets": {"dry_bulb_temperature": s1["target"], "humidity_ratio": s2["target"]},
            "data_collection_targets": {"dry_bulb_temperature": s1["target"], "humidity_ratio": s2["target"]},
            "summary_view": {
                "garden_target": manifest.target(),
                "operation": op,
                "dry_bulb_temperature": s1["summary_view"],
                "humidity_ratio": s2["summary_view"],
            },
            "report": make_report(status="ok", message=f"Psychrometrics '{op}' DataCollections persisted."),
        }

    dt_cls, unit_str = _PSY_OUTPUT_DATATYPES.get(op, (Temperature, "unit"))
    saved = _save_psy_col(out_values_primary, dt_cls, unit_str, "")
    out: dict[str, Any] = {
        "target": saved["target"],
        "data_target": saved["target"],
        "data_collection_target": saved["target"],
        "artifact": saved["artifact"],
        "persistence_receipt": saved["persistence_receipt"],
        "summary_view": {
            "garden_target": manifest.target(),
            "operation": op,
            "data_collection": saved["summary_view"],
        },
        "report": make_report(status="ok", message=f"Psychrometrics '{op}' DataCollection persisted."),
    }
    if return_data_collection:
        out["data_collection"] = load_data_collection(
            garden_root=garden_root_path, data_collection_target=saved["target"]
        ).to_dict()
    return out


def _calc_skymodel(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    operation: str,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    op = str(operation).strip().lower()
    if op == "zhang_huang_solar":
        res = skymodel.zhang_huang_solar(
            alt=float(inputs["altitude"]),
            cloud_cover=float(inputs["cloud_cover"]),
            relative_humidity=float(inputs["relative_humidity"]),
            dry_bulb_present=float(inputs["dry_bulb_present"]),
            dry_bulb_t3_hrs=float(inputs["dry_bulb_t3_hrs"]),
            wind_speed=float(inputs["wind_speed"]),
            irr_0=float(inputs.get("irr_0", 1355)),
        )
        out = {"global_horizontal_irradiance": float(res)}
    elif op == "zhang_huang_solar_split":
        ghi, dni, dhi = skymodel.zhang_huang_solar_split(
            altitudes=inputs["altitudes"],
            doys=inputs["doys"],
            cloud_cover=inputs["cloud_cover"],
            relative_humidity=inputs["relative_humidity"],
            dry_bulb_present=inputs["dry_bulb_present"],
            dry_bulb_t3_hrs=inputs["dry_bulb_t3_hrs"],
            wind_speed=inputs["wind_speed"],
            atm_pressure=inputs["atmospheric_pressure"],
            use_disc=bool(inputs.get("use_disc", False)),
        )
        out = {"global_horizontal_irradiance": list(ghi), "direct_normal_irradiance": list(dni), "diffuse_horizontal_irradiance": list(dhi)}
    elif op == "dirint":
        dni = skymodel.dirint(
            ghi=inputs["ghi"],
            altitudes=inputs["altitudes"],
            doys=inputs["doys"],
            pressures=inputs["pressures"],
            use_delta_kt_prime=bool(inputs.get("use_delta_kt_prime", True)),
            temp_dew=inputs.get("temp_dew"),
        )
        out = {"direct_normal_irradiance": list(dni)}
    elif op == "disc":
        dni, kt, am = skymodel.disc(
            ghi=float(inputs["ghi"]),
            altitude=float(inputs["altitude"]),
            doy=int(inputs["doy"]),
            pressure=float(inputs.get("pressure", 101325)),
        )
        out = {
            "direct_normal_irradiance": float(dni),
            "clearness_index": float(kt),
            "air_mass": float(am),
        }
    elif op == "calc_sky_temperature":
        sky_t = skymodel.calc_sky_temperature(
            horiz_ir=float(inputs["horizontal_infrared"]),
            source_emissivity=float(inputs.get("source_emissivity", 1)),
        )
        out = {"sky_temperature": float(sky_t)}
    elif op == "ashrae_clear_sky":
        dni, dhi = skymodel.ashrae_clear_sky(
            altitudes=inputs["altitudes"],
            month=int(inputs["month"]),
            sky_clearness=float(inputs.get("sky_clearness", 1.0)),
        )
        out = {"direct_normal_irradiance": list(dni), "diffuse_horizontal_irradiance": list(dhi)}
    elif op == "ashrae_revised_clear_sky":
        dni, dhi = skymodel.ashrae_revised_clear_sky(
            altitudes=inputs["altitudes"],
            tb=inputs["tau_beam"],
            td=inputs["tau_diffuse"],
            use_2017_model=bool(inputs.get("use_2017_model", False)),
        )
        out = {"direct_normal_irradiance": list(dni), "diffuse_horizontal_irradiance": list(dhi)}
    elif op == "estimate_illuminance_from_irradiance":
        ghi_l, dni_l, dhi_l, zen_l = skymodel.estimate_illuminance_from_irradiance(
            altitude=float(inputs["altitude"]),
            ghi=float(inputs["ghi"]),
            dni=float(inputs["dni"]),
            dhi=float(inputs["dhi"]),
            dew_point=float(inputs["dew_point"]),
            rel_airmass=inputs.get("rel_airmass"),
        )
        out = {
            "global_horizontal_illuminance": float(ghi_l),
            "direct_normal_illuminance": float(dni_l),
            "diffuse_horizontal_illuminance": float(dhi_l),
            "zenith_luminance": float(zen_l),
        }
    elif op == "calc_horizontal_infrared":
        hir = skymodel.calc_horizontal_infrared(
            sky_cover=float(inputs.get("sky_cover", inputs.get("opaque_sky_cover", 0))),
            dry_bulb=float(inputs["dry_bulb"]),
            dew_point=float(inputs["dew_point"]),
        )
        out = {"horizontal_infrared": float(hir)}
    elif op == "clearness_index":
        kt = skymodel.clearness_index(
            ghi=float(inputs["ghi"]),
            altitude=float(inputs["altitude"]),
            extra_radiation=float(inputs.get("extra_radiation", inputs.get("extraterrestrial_rad"))),
        )
        out = {"clearness_index": float(kt)}
    else:
        raise ValueError(
            "Unsupported skymodel operation. Allowed: zhang_huang_solar, zhang_huang_solar_split, "
            "dirint, disc, calc_sky_temperature, ashrae_clear_sky, ashrae_revised_clear_sky, "
            "estimate_illuminance_from_irradiance, calc_horizontal_infrared, clearness_index."
        )

    return {
        **out,
        "summary_view": {"operation": op, **out},
        "report": make_report(status="ok", message=f"SkyModel '{op}' computed."),
    }


def _calc_wind_profile(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    terrain: str = "city",
    meteorological_terrain: str = "country",
    meteorological_height: float = 10.0,
    log_law: bool = False,
    wind_speed: float | None = None,
    wind_speed_target: dict[str, Any] | None = None,
    height: float = 1.0,
    heights: list[float] | None = None,
    identifier: str | None = None,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    wp = WindProfile(
        terrain=terrain,
        meteorological_terrain=meteorological_terrain,
        meteorological_height=meteorological_height,
        log_law=log_law,
    )
    if wind_speed_target is not None:
        ws_col = load_data_collection(garden_root=garden_root_path, data_collection_target=wind_speed_target)
        out_col = wp.calculate_wind_data(ws_col, height=height)
        saved = save_data_collection(
            garden_root=garden_root_path,
            data_collection=out_col,
            identifier=identifier or f"wind_profile_{terrain}_{height:g}m",
            source={
                "producer": "LB_Climate_Calc",
                "action": "wind_profile",
                "terrain": terrain,
                "height": height,
                "log_law": log_law,
            },
        )
        res: dict[str, Any] = {
            "target": saved["target"],
            "data_target": saved["target"],
            "data_collection_target": saved["target"],
            "artifact": saved["artifact"],
            "persistence_receipt": saved["persistence_receipt"],
            "summary_view": {
                "garden_target": manifest.target(),
                "terrain": terrain,
                "meteorological_terrain": meteorological_terrain,
                "meteorological_height": meteorological_height,
                "log_law": log_law,
                "height": height,
                "data_collection": saved["summary_view"],
            },
            "report": make_report(status="ok", message="WindProfile DataCollection persisted."),
        }
        if return_data_collection:
            res["data_collection"] = out_col.to_dict()
        return res

    met_ws = 5.0 if wind_speed is None else float(wind_speed)
    eval_heights = list(heights) if heights is not None else [float(height)]
    profile_values = [{"height": float(h), "wind_speed": float(wp.calculate_wind(met_ws, float(h)))} for h in eval_heights]
    return {
        "wind_speed": profile_values[0]["wind_speed"],
        "profile": profile_values,
        "summary_view": {
            "terrain": terrain,
            "meteorological_terrain": meteorological_terrain,
            "meteorological_height": meteorological_height,
            "meteorological_wind_speed": met_ws,
            "log_law": log_law,
            "profile": profile_values,
        },
        "report": make_report(status="ok", message="WindProfile speeds calculated."),
    }


def _calc_magnetic_north(
    *,
    garden_root_path: Path,
    manifest: GardenManifest,
    location: dict[str, Any] | None,
    weather_target: dict[str, Any] | None,
    epw_path: str | None,
    latitude: float | None = None,
    longitude: float | None = None,
    elevation: float = 0.0,
    magnetic_north: float = 0.0,
    year: float = 2025.0,
) -> dict[str, Any]:
    if location is not None or weather_target is not None or epw_path is not None:
        loc_obj = _location_from_inputs(
            garden_root_path=garden_root_path,
            manifest=manifest,
            location=location,
            weather_target=weather_target,
            epw_path=epw_path,
        )
    elif latitude is not None and longitude is not None:
        loc_obj = Location(latitude=float(latitude), longitude=float(longitude), elevation=float(elevation))
    else:
        raise ValueError("Provide location, weather_target/epw_path, or latitude and longitude.")

    # Use a fresh WorldMagneticModel per call to avoid ladybug's cached-coordinate UnboundLocalError.
    declination = float(
        WorldMagneticModel().magnetic_declination(
            loc_obj.latitude, loc_obj.longitude, loc_obj.elevation, year
        )
    )
    true_north = float(
        WorldMagneticModel().magnetic_to_true_north(
            loc_obj, magnetic_north=magnetic_north, year=year
        )
    )
    return {
        "magnetic_declination": declination,
        "true_north": true_north,
        "summary_view": {
            "location": loc_obj.to_dict(),
            "year": year,
            "magnetic_north": magnetic_north,
            "magnetic_declination": declination,
            "true_north": true_north,
        },
        "report": make_report(status="ok", message="Magnetic declination and true north computed."),
    }


def climate_calc(
    *,
    garden_root: str,
    action: str,
    weather_target: dict[str, Any] | None = None,
    epw_path: str | None = None,
    stat_path: str | None = None,
    ddy_path: str | None = None,
    location: dict[str, Any] | None = None,
    translation_type: str | None = None,
    percentile: float = 0.4,
    annual_percentile: float = 0.4,
    monthly_percentile: float = 5.0,
    hoys: list[float] | None = None,
    timestep: int = 1,
    is_leap_year: bool = False,
    use_2017: bool = False,
    monthly_tau_beam: list[float] | None = None,
    monthly_tau_diffuse: list[float] | None = None,
    cloud_cover_target: dict[str, Any] | None = None,
    relative_humidity_target: dict[str, Any] | None = None,
    dry_bulb_temperature_target: dict[str, Any] | None = None,
    wind_speed_target: dict[str, Any] | None = None,
    atmospheric_pressure_target: dict[str, Any] | None = None,
    use_disc: bool = False,
    field_updates: dict[str, Any] | None = None,
    comments_1: str | None = None,
    comments_2: str | None = None,
    register_weather_target: bool = True,
    design_days: list[dict[str, Any]] | None = None,
    filter_keyword: str | None = None,
    north_angle: float = 0.0,
    analysis_period: dict[str, Any] | str | None = None,
    month: int | None = None,
    day: int | None = None,
    hour: float | None = None,
    solar_time: bool = False,
    depression: float = 0.5334,
    operation: str | None = None,
    inputs: dict[str, Any] | None = None,
    terrain: str = "city",
    meteorological_terrain: str = "country",
    meteorological_height: float = 10.0,
    log_law: bool = False,
    wind_speed: float | None = None,
    height: float = 1.0,
    heights: list[float] | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    elevation: float = 0.0,
    magnetic_north: float = 0.0,
    year: float = 2025.0,
    identifier: str | None = None,
    output_subdir: str = WEATHER_ARTIFACT_SUBDIR,
    return_data_collection: bool = False,
) -> dict[str, Any]:
    """Dispatch pure-Python climate, weather, solar, psychrometric, and sky-model calculations."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    act = str(action).strip().lower()

    if act == "inspect_weather":
        return _inspect_weather(
            garden_root_path=garden_root_path,
            manifest=manifest,
            weather_target=weather_target,
            epw_path=epw_path,
            stat_path=stat_path,
            ddy_path=ddy_path,
        )
    if act == "translate_weather":
        if not translation_type:
            raise ValueError("translation_type is required for action='translate_weather'.")
        return _translate_weather(
            garden_root_path=garden_root_path,
            manifest=manifest,
            translation_type=translation_type,
            weather_target=weather_target,
            epw_path=epw_path,
            stat_path=stat_path,
            location=location,
            percentile=percentile,
            annual_percentile=annual_percentile,
            monthly_percentile=monthly_percentile,
            hoys=hoys,
            timestep=timestep,
            is_leap_year=is_leap_year,
            use_2017=use_2017,
            monthly_tau_beam=monthly_tau_beam,
            monthly_tau_diffuse=monthly_tau_diffuse,
            cloud_cover_target=cloud_cover_target,
            relative_humidity_target=relative_humidity_target,
            dry_bulb_temperature_target=dry_bulb_temperature_target,
            wind_speed_target=wind_speed_target,
            atmospheric_pressure_target=atmospheric_pressure_target,
            use_disc=use_disc,
            identifier=identifier,
            output_subdir=output_subdir,
        )
    if act == "write_epw":
        return _write_epw(
            garden_root_path=garden_root_path,
            manifest=manifest,
            weather_target=weather_target,
            epw_path=epw_path,
            field_updates=field_updates,
            location=location,
            comments_1=comments_1,
            comments_2=comments_2,
            identifier=identifier,
            register_weather_target=register_weather_target,
        )
    if act == "write_ddy":
        return _write_ddy(
            garden_root_path=garden_root_path,
            manifest=manifest,
            weather_target=weather_target,
            ddy_path=ddy_path,
            location=location,
            design_days=design_days,
            filter_keyword=filter_keyword,
            identifier=identifier,
            output_subdir=output_subdir,
        )
    if act == "sunpath":
        return _calc_sunpath(
            garden_root_path=garden_root_path,
            manifest=manifest,
            location=location,
            weather_target=weather_target,
            epw_path=epw_path,
            north_angle=north_angle,
            hoys=hoys,
            analysis_period=analysis_period,
            month=month,
            day=day,
            hour=hour,
            solar_time=solar_time,
            depression=depression,
        )
    if act == "psychrometrics":
        if not operation:
            raise ValueError("operation is required for action='psychrometrics'.")
        return _calc_psychrometrics(
            garden_root_path=garden_root_path,
            manifest=manifest,
            operation=operation,
            inputs=inputs or {},
            identifier=identifier,
            return_data_collection=return_data_collection,
        )
    if act == "skymodel":
        if not operation:
            raise ValueError("operation is required for action='skymodel'.")
        return _calc_skymodel(
            garden_root_path=garden_root_path,
            manifest=manifest,
            operation=operation,
            inputs=inputs or {},
        )
    if act == "wind_profile":
        return _calc_wind_profile(
            garden_root_path=garden_root_path,
            manifest=manifest,
            terrain=terrain,
            meteorological_terrain=meteorological_terrain,
            meteorological_height=meteorological_height,
            log_law=log_law,
            wind_speed=wind_speed,
            wind_speed_target=wind_speed_target,
            height=height,
            heights=heights,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )
    if act == "magnetic_north":
        return _calc_magnetic_north(
            garden_root_path=garden_root_path,
            manifest=manifest,
            location=location,
            weather_target=weather_target,
            epw_path=epw_path,
            latitude=latitude,
            longitude=longitude,
            elevation=elevation,
            magnetic_north=magnetic_north,
            year=year,
        )
    raise ValueError(
        f"Unsupported action {action!r}. Allowed: inspect_weather, translate_weather, "
        "write_epw, write_ddy, sunpath, psychrometrics, skymodel, wind_profile, magnetic_north."
    )


__all__ = ["climate_calc"]
