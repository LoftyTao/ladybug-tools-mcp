"""Energy simulation SDK configuration and weather discovery services."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

from honeybee_energy.config import folders as energy_folders
from ladybug_tools_mcp.contracts.report import make_report
from garden.manifest import GardenManifest
from garden.paths import to_posix_relative

WEATHER_TARGET_TYPE = "weather_file"
_WEATHER_QUERY_STOPWORDS = {"weather", "epw", "file", "climate", "data"}


def _existing_path(value: str | None) -> dict[str, Any]:
    exists = bool(value and Path(value).expanduser().exists())
    return {"path": value, "exists": exists}


def _version_value(getter) -> str | None:
    try:
        return getter()
    except Exception:
        return None


def _engine_record(name: str, path: str | None, exe: str | None, version_getter) -> dict[str, Any]:
    record = {
        "name": name,
        "path": path,
        "path_exists": bool(path and Path(path).expanduser().is_dir()),
        "exe": exe,
        "exe_exists": bool(exe and Path(exe).expanduser().is_file()),
    }
    version = _version_value(version_getter)
    if version:
        record["version"] = version
    return record


def get_energy_simulation_config() -> dict[str, Any]:
    """Return local Ladybug Tools SDK configuration for Energy simulation."""
    engines = {
        "openstudio": _engine_record(
            "openstudio",
            energy_folders.openstudio_path,
            energy_folders.openstudio_exe,
            lambda: energy_folders.openstudio_version_str,
        ),
        "energyplus": _engine_record(
            "energyplus",
            energy_folders.energyplus_path,
            energy_folders.energyplus_exe,
            lambda: energy_folders.energyplus_version_str,
        ),
    }
    measures = {
        "lbt_measures_path": _existing_path(energy_folders.lbt_measures_path),
        "openstudio_results_measure_path": _existing_path(
            energy_folders.openstudio_results_measure_path
        ),
        "honeybee_openstudio_gem_path": _existing_path(
            energy_folders.honeybee_openstudio_gem_path
        ),
    }
    weather = {
        "managed_by": "garden",
        "weather_dir": "imports/weather",
        "target_type": WEATHER_TARGET_TYPE,
    }
    return {
        "summary_view": {
            "weather": weather,
            "engines": engines,
            "measures": measures,
        },
        "report": make_report(
            status="ok",
            message="Energy simulation SDK configuration returned.",
        ),
    }


def make_garden_weather_target(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    identifier: str,
    epw_path: Path,
    ddy_path: Path | None,
    stat_path: Path | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a Garden-managed weather_file target with relative paths."""
    target: dict[str, Any] = {
        "target_type": WEATHER_TARGET_TYPE,
        "domain": "ladybug",
        "garden_id": manifest.garden_id,
        "identifier": identifier,
        "path": to_posix_relative(epw_path.parent, garden_root),
        "epw_path": to_posix_relative(epw_path, garden_root),
    }
    if ddy_path is not None:
        target["ddy_path"] = to_posix_relative(ddy_path, garden_root)
    if stat_path is not None:
        target["stat_path"] = to_posix_relative(stat_path, garden_root)
    if metadata:
        target.update(metadata)
    return target


def _searchable_weather_values(target: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in (
        "identifier",
        "station",
        "station_id",
        "source",
        "host",
        "path",
        "epw_path",
        "ddy_path",
        "stat_path",
        "city",
        "country",
        "state",
        "province",
        "region",
    ):
        value = target.get(key)
        if value is not None:
            values.append(str(value))
    for key in ("aliases", "query_aliases", "search_aliases"):
        value = target.get(key)
        if isinstance(value, (list, tuple, set)):
            values.extend(str(item) for item in value if item is not None)
        elif value is not None:
            values.append(str(value))
    return values


def _normalize_search_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", ascii_text).lower()
    return " ".join(normalized.split())


def _weather_tokens(value: str) -> set[str]:
    return {
        token
        for token in _normalize_search_text(value).split()
        if token and token not in _WEATHER_QUERY_STOPWORDS
    }


def _weather_target_matches_query(target: dict[str, Any], query: str) -> bool:
    query_tokens = _weather_tokens(query)
    if not query_tokens:
        return True
    values = _searchable_weather_values(target)
    normalized_haystack = _normalize_search_text(" ".join(values))
    haystack_tokens = set(normalized_haystack.split())
    if query_tokens.issubset(haystack_tokens):
        return True
    normalized_query = _normalize_search_text(query)
    return bool(normalized_query and normalized_query in normalized_haystack)


def search_weather_files(
    *,
    garden_root: str,
    query: str | None = None,
    max_results: int = 10,
    require_ddy: bool = False,
) -> dict[str, Any]:
    """Search Garden-managed EPW weather targets."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    normalized_query = (query or "").strip()
    matches: list[dict[str, Any]] = []
    for target in manifest.weather_files:
        if normalized_query and not _weather_target_matches_query(target, normalized_query):
            continue
        if require_ddy and not target.get("ddy_path"):
            continue
        match = {
            "identifier": target.get("identifier"),
            "epw_path": target.get("epw_path"),
            "ddy_path": target.get("ddy_path"),
            "has_ddy": bool(target.get("ddy_path")),
            "target": target,
        }
        for key in ("station_id", "station", "source", "host"):
            if key in target:
                match[key] = target[key]
        matches.append(match)
        if len(matches) >= max_results:
            break

    return {
        "matches": matches,
        "summary_view": {
            "garden_target": manifest.target(),
            "query": query or "",
            "count": len(matches),
            "max_results": max_results,
            "require_ddy": require_ddy,
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(matches)} weather file(s).",
        ),
    }
