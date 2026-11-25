"""Energy simulation SDK configuration and weather discovery services."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
import unicodedata
from pathlib import Path
from typing import Any
from uuid import uuid4

from honeybee_energy.config import folders as energy_folders
from ladybug_tools_mcp.contracts import make_report
from garden.manifest import GardenManifest, garden_lock
from garden.paths import resolve_contained_path, to_posix_relative

WEATHER_TARGET_TYPE = "weather_file"
_WEATHER_QUERY_STOPWORDS = {"weather", "epw", "file", "climate", "data"}
_DATASET_VERSION_RE = re.compile(
    r"(?:^|[_\-])("
    r"TMYx(?:\.\d{4}-\d{4})?"
    r"|TMY[23]?"
    r"|IWEC2?"
    r"|CSWD"
    r"|CWEC"
    r"|SWERA"
    r"|ISHRAE2?"
    r"|CTZ\d*"
    r"|TRY"
    r"|AMY(?:[._-]?\d{4})?"
    r")(?=$|[_\-.])",
    re.IGNORECASE,
)


def compute_file_sha256(path: Path) -> str:
    """Return the lowercase SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def parse_weather_filename_metadata(filename: str) -> dict[str, str | None]:
    """Extract optional dataset_version and inferred station name from a weather file name."""
    stem = Path(str(filename or "").strip()).stem
    if not stem:
        return {"station": None, "dataset_version": None}
    match = _DATASET_VERSION_RE.search(stem)
    dataset_version = match.group(1) if match else None
    station = stem[: match.start()].rstrip("_-.") if match else stem
    return {
        "station": station or stem,
        "dataset_version": dataset_version,
    }


def parse_epw_location_metadata(epw_path: Path) -> dict[str, str | None]:
    """Read station/source/WMO metadata from the first LOCATION line of an EPW file."""
    try:
        with epw_path.open("r", encoding="utf-8", errors="replace") as handle:
            first_line = handle.readline().strip()
    except OSError:
        return {"station": None, "epw_source": None, "wmo_station": None}
    parts = [part.strip() for part in first_line.split(",")]
    if len(parts) < 6 or parts[0].upper() != "LOCATION":
        return {"station": None, "epw_source": None, "wmo_station": None}
    return {
        "station": parts[1] or None,
        "epw_source": parts[4] or None,
        "wmo_station": parts[5] or None,
    }


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
        "external_source_url": "https://climate.onebuilding.org/",
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
    """Build a Garden-managed weather_file target with relative paths and EPW provenance."""
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

    filename_meta = parse_weather_filename_metadata(
        str(target.get("file_name") or epw_path.name)
    )
    epw_loc = parse_epw_location_metadata(epw_path) if epw_path.is_file() else {}
    if not target.get("station"):
        station = epw_loc.get("station") or filename_meta.get("station") or epw_path.stem
        if station:
            target["station"] = station
    if not target.get("wmo_station") and epw_loc.get("wmo_station"):
        target["wmo_station"] = epw_loc["wmo_station"]
    if not target.get("dataset_version") and filename_meta.get("dataset_version"):
        target["dataset_version"] = filename_meta["dataset_version"]
    if not target.get("source"):
        target["source"] = "local_weather"
    if not target.get("epw_sha256") and epw_path.is_file():
        target["epw_sha256"] = compute_file_sha256(epw_path)
    return target


def resolve_garden_weather_epw(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    weather_target: dict[str, Any],
) -> Path:
    """Resolve a Garden weather_file target to an existing EPW path."""
    if not isinstance(weather_target, dict):
        raise ValueError("weather_target must be a Garden weather_file target.")
    if weather_target.get("target_type") != WEATHER_TARGET_TYPE:
        raise ValueError("weather_target must have target_type 'weather_file'.")
    if weather_target.get("garden_id") != manifest.garden_id:
        raise ValueError("weather_target belongs to a different Garden.")
    path_value = weather_target.get("epw_path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("weather_target requires epw_path.")
    if Path(path_value).is_absolute():
        raise ValueError("weather_target epw_path must be Garden-relative.")
    epw_path = (garden_root / path_value).resolve()
    try:
        epw_path.relative_to(garden_root.resolve())
    except ValueError as exc:
        raise ValueError("weather_target epw_path must stay inside the Garden.") from exc
    if epw_path.suffix.lower() != ".epw":
        raise ValueError("weather_target epw_path must reference a .epw file.")
    if not epw_path.is_file():
        raise ValueError(f"EPW file not found: {path_value}")
    return epw_path


def _searchable_weather_values(target: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in (
        "identifier",
        "station",
        "station_id",
        "wmo_station",
        "dataset_version",
        "file_name",
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
        "admin_region",
    ):
        value = target.get(key)
        if value is not None:
            values.append(str(value))
    for key in ("search_terms",):
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


def _safe_weather_identifier(value: str) -> str:
    normalized = _normalize_search_text(value).replace(" ", "_")
    return normalized or "local_weather"


def _find_weather_siblings(source_path: Path) -> tuple[Path, Path | None, Path | None]:
    if source_path.is_file():
        if source_path.suffix.lower() != ".epw":
            raise ValueError("source_path file must be an .epw file.")
        folder = source_path.parent
        epw_path = source_path
    else:
        folder = source_path
        epw_files = sorted(folder.glob("*.epw"))
        if not epw_files:
            raise ValueError("source_path must contain one .epw file.")
        epw_path = epw_files[0]
    stem = epw_path.stem
    ddy_path = folder / f"{stem}.ddy"
    stat_path = folder / f"{stem}.stat"
    return (
        epw_path,
        ddy_path if ddy_path.is_file() else None,
        stat_path if stat_path.is_file() else None,
    )


def import_local_weather_folder(
    *,
    garden_root: str,
    source_path: str,
    identifier: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Copy a local EPW/DDY/STAT folder into a Garden and register it."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    with garden_lock(garden_root_path):
        manifest = GardenManifest.read(garden_root_path)
        source = Path(source_path).expanduser().resolve()
        if not source.exists():
            raise ValueError(f"Local weather source not found: {source_path}")
        epw_path, ddy_path, stat_path = _find_weather_siblings(source)
        weather_identifier = _safe_weather_identifier(identifier or epw_path.stem)
        weather_relative = f"imports/weather/{weather_identifier}"
        destination = garden_root_path / "imports" / "weather" / weather_identifier
        weather_parent = destination.parent
        safe_destination = resolve_contained_path(
            garden_root_path, weather_relative, label="Weather destination"
        )
        if os.path.normcase(str(destination)) != os.path.normcase(str(safe_destination)):
            raise ValueError("Weather destination must not traverse a symlink.")

        if destination.exists():
            if not destination.is_dir():
                raise ValueError("Weather destination exists but is not a directory.")
            if not overwrite:
                existing = next(
                    (
                        target
                        for target in manifest.weather_files
                        if target.get("identifier") == weather_identifier
                    ),
                    None,
                )
                if existing is not None:
                    return {
                        "target": existing,
                        "weather_target": existing,
                        "weather_file_target": existing,
                        "weather_file": existing,
                        "summary_view": {
                            "garden_target": manifest.target(),
                            "identifier": weather_identifier,
                            "status": "already_registered",
                        },
                        "report": make_report(
                            status="ok",
                            message=f"Local weather already registered: {weather_identifier}",
                        ),
                    }
                raise ValueError(
                    "Weather destination already exists but is not registered: "
                    f"{to_posix_relative(destination, garden_root_path)}"
                )

        weather_parent.mkdir(parents=True, exist_ok=True)
        stage_directory = Path(
            tempfile.mkdtemp(prefix=".weather-stage-", dir=weather_parent)
        )
        backup_directory = (
            weather_parent / f".weather-backup-{uuid4().hex}"
            if destination.exists()
            else None
        )
        published = False

        try:
            # Stage every source file before moving the destination. The source can
            # itself be inside that destination when overwrite=True.
            shutil.copy2(epw_path, stage_directory / epw_path.name)
            if ddy_path is not None:
                shutil.copy2(ddy_path, stage_directory / ddy_path.name)
            if stat_path is not None:
                shutil.copy2(stat_path, stage_directory / stat_path.name)

            if backup_directory is not None:
                os.replace(destination, backup_directory)
            os.replace(stage_directory, destination)
            published = True

            filename_meta = parse_weather_filename_metadata(epw_path.name)
            epw_loc = parse_epw_location_metadata(destination / epw_path.name)
            station = epw_loc.get("station") or filename_meta.get("station") or epw_path.stem
            epw_sha256 = compute_file_sha256(destination / epw_path.name)
            source_metadata: dict[str, Any] = {
                "source": "local_weather",
                "source_path": str(source),
                "station": station,
                "wmo_station": epw_loc.get("wmo_station"),
                "dataset_version": filename_meta.get("dataset_version"),
                "epw_sha256": epw_sha256,
                "file_name": epw_path.name,
                "search_terms": [
                    term for term in (weather_identifier, epw_path.stem, station) if term
                ],
            }
            source_metadata = {
                key: value for key, value in source_metadata.items() if value is not None
            }
            target = make_garden_weather_target(
                garden_root=garden_root_path,
                manifest=manifest,
                identifier=weather_identifier,
                epw_path=destination / epw_path.name,
                ddy_path=(destination / ddy_path.name) if ddy_path is not None else None,
                stat_path=(destination / stat_path.name) if stat_path is not None else None,
                metadata=source_metadata,
            )
            manifest.weather_files = [
                item
                for item in manifest.weather_files
                if item.get("identifier") != weather_identifier
            ]
            manifest.weather_files.append(target)
            manifest.weather_files.sort(key=lambda item: str(item.get("identifier", "")))
            manifest.write(garden_root_path)
        except BaseException as exc:
            rollback_error = None
            if published and destination.exists():
                try:
                    shutil.rmtree(destination)
                except OSError as rollback_exc:
                    rollback_error = f"could not remove the failed weather import: {rollback_exc}"
            if backup_directory is not None and backup_directory.exists():
                if destination.exists():
                    rollback_error = rollback_error or (
                        "the previous weather directory cannot be restored because "
                        f"the destination is occupied: {destination}"
                    )
                else:
                    try:
                        os.replace(backup_directory, destination)
                    except OSError as rollback_exc:
                        rollback_error = (
                            rollback_error
                            or f"could not restore the previous weather directory: {rollback_exc}"
                        )
            if rollback_error:
                retained = []
                if backup_directory is not None and backup_directory.exists():
                    retained.append(str(backup_directory))
                if published and destination.exists():
                    retained.append(str(destination))
                retained_text = (
                    f" Recovery data retained at: {', '.join(retained)}."
                    if retained
                    else ""
                )
                raise RuntimeError(
                    "Local weather import failed and rollback was incomplete: "
                    f"{rollback_error}.{retained_text}"
                ) from exc
            raise
        finally:
            if stage_directory.exists():
                shutil.rmtree(stage_directory, ignore_errors=True)

        if backup_directory is not None:
            shutil.rmtree(backup_directory, ignore_errors=True)
    return {
        "target": target,
        "weather_target": target,
        "weather_file_target": target,
        "weather_file": target,
        "summary_view": {
            "garden_target": manifest.target(),
            "identifier": weather_identifier,
            "station": target.get("station"),
            "dataset_version": target.get("dataset_version"),
            "source": target.get("source"),
            "epw_sha256": target.get("epw_sha256"),
            "epw_path": target.get("epw_path"),
            "ddy_path": target.get("ddy_path"),
            "stat_path": target.get("stat_path"),
            "source_path": source_metadata["source_path"],
        },
        "persistence_receipt": {
            "status": "persisted",
            "garden_id": manifest.garden_id,
            "persisted_path": "garden.json",
            "target": target,
        },
        "report": make_report(
            status="ok",
            message=f"Local weather imported: {weather_identifier}",
        ),
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
        for key in ("station_id", "station", "source", "host", "dataset_version", "epw_sha256"):
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
