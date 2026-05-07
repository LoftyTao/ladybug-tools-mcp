"""EPW map search and download services."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ladybug.futil import download_file, unzip_file

from ladybug_tools_mcp.contracts.report import make_report
from garden.manifest import GardenManifest
from garden.paths import slugify_name
from garden.run_energy.config import make_garden_weather_target

EPWMAP_URL = "https://www.ladybug.tools/epwmap/"
EPWMAP_PRE_LINK = {
    "doe": "https://energyplus-weather.s3.amazonaws.com",
    "onebuilding": "https://climate.onebuilding.org",
}
EPWMAP_CANDIDATE_TARGET_TYPE = "epw_map_weather"
_EPWMAP_CACHE: list[dict[str, Any]] | None = None


def _fetch_text(url: str, *, timeout: int = 30) -> str:
    request = Request(url, headers={"User-Agent": "LadybugToolsMCP/0.1"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _epwmap_bundle_url() -> str:
    html = _fetch_text(EPWMAP_URL)
    match = re.search(r'<script[^>]+src="(?P<src>[^"]*static/js/main[^"]+\.js)"', html)
    if not match:
        raise ValueError("Could not find EPW map JavaScript bundle.")
    src = match.group("src")
    if src.startswith("http"):
        return src
    return EPWMAP_URL.rstrip("/") + "/" + src.lstrip("./")


def _load_raw_epwmap_rows() -> list[list[str]]:
    bundle = _fetch_text(_epwmap_bundle_url())
    raw_text = ""
    start = bundle.find("var raw = ")
    end = bundle.find(";\n\nvar pre_link", start)
    if start >= 0 and end >= 0:
        raw_text = bundle[start + len("var raw = "):end]
    else:
        marker = re.search(
            r'\],\w+=\{DOE:"https://energyplus-weather\.s3\.amazonaws\.com"',
            bundle,
        )
        if marker:
            minified_start = bundle.rfind("=[[", 0, marker.start())
            if minified_start >= 0:
                raw_text = bundle[minified_start + 1:marker.start() + 1]
    if not raw_text:
        raise ValueError("Could not find EPW map weather records in bundle.")
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return _parse_js_string_rows(raw_text)


def _decode_js_string(value: str) -> str:
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return value.replace(r"\"", '"').replace(r"\\", "\\")


def _parse_js_string_rows(raw_text: str) -> list[list[str]]:
    string_value = r'"((?:\\.|[^"\\])*)"'
    row_pattern = re.compile(r"\[" + ",".join([string_value] * 7) + r"\]")
    rows = [
        [_decode_js_string(value) for value in match.groups()]
        for match in row_pattern.finditer(raw_text)
    ]
    if not rows:
        raise ValueError("Could not parse EPW map weather records from bundle.")
    return rows


def _record_from_raw(row: list[str]) -> dict[str, Any] | None:
    if len(row) < 7 or not row[1]:
        return None
    host = str(row[6]).lower()
    base_url = EPWMAP_PRE_LINK.get(host)
    if not base_url:
        return None
    relative_url = str(row[5])
    return {
        "station_id": str(row[0]),
        "station": str(row[1]),
        "source": str(row[2]),
        "latitude": float(row[3]),
        "longitude": float(row[4]),
        "host": host,
        "relative_url": relative_url,
        "download_url": base_url + relative_url,
    }


def _epwmap_records() -> list[dict[str, Any]]:
    global _EPWMAP_CACHE
    if _EPWMAP_CACHE is None:
        records = []
        for row in _load_raw_epwmap_rows():
            record = _record_from_raw(row)
            if record is not None:
                records.append(record)
        _EPWMAP_CACHE = records
    return _EPWMAP_CACHE


def _candidate_target(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_type": EPWMAP_CANDIDATE_TARGET_TYPE,
        "domain": "ladybug",
        "station_id": record["station_id"],
        "station": record["station"],
        "source": record["source"],
        "host": record["host"],
        "download_url": record["download_url"],
    }


def _candidate_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "station_id": record["station_id"],
        "station": record["station"],
        "source": record["source"],
        "host": record["host"],
        "latitude": record["latitude"],
        "longitude": record["longitude"],
        "download_url": record["download_url"],
        "target": _candidate_target(record),
    }


def _distance_score(record: dict[str, Any], latitude: float | None, longitude: float | None) -> float:
    if latitude is None or longitude is None:
        return 0
    return (record["latitude"] - latitude) ** 2 + (record["longitude"] - longitude) ** 2


def _normalized_tokens(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return tuple(token for token in normalized.split() if token)


def _matches_query(record: dict[str, Any], query: str | None) -> bool:
    tokens = _normalized_tokens(query)
    if not tokens:
        return True
    haystack = " ".join(
        str(item)
        for item in (
            record.get("station"),
            record.get("station_id"),
            record.get("source"),
            record.get("host"),
            record.get("download_url"),
        )
    )
    haystack_tokens = set(_normalized_tokens(haystack))
    haystack_text = " ".join(sorted(haystack_tokens))
    return all(token in haystack_tokens or token in haystack_text for token in tokens)


def _source_tokens_from_query(query: str | None) -> set[str]:
    tokens = set(_normalized_tokens(query))
    return {token for token in tokens if token in {"tmy", "tmy2", "tmy3", "amy", "tdy"}}


def search_epw_map(
    *,
    query: str | None = None,
    source: str | None = None,
    host: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    max_results: int = 10,
) -> dict[str, Any]:
    """Search EPW map records and return lightweight candidate targets."""
    query_value = (query or "").strip().lower()
    source_value = (source or "").strip().lower()
    host_value = (host or "").strip().lower()
    records = []
    for record in _epwmap_records():
        if query_value and not _matches_query(record, query):
            continue
        if source_value and source_value not in str(record["source"]).lower():
            continue
        if host_value and host_value != str(record["host"]).lower():
            continue
        records.append(record)
    records.sort(
        key=lambda item: (
            _distance_score(item, latitude, longitude),
            str(item["station"]),
            str(item["source"]),
        )
    )
    matches = [_candidate_summary(record) for record in records[:max_results]]
    return {
        "matches": matches,
        "summary_view": {
            "count": len(matches),
            "query": query or "",
            "source": source or "",
            "host": host or "",
            "has_coordinate_sort": latitude is not None and longitude is not None,
            "max_results": max_results,
        },
        "report": make_report(status="ok", message=f"Found {len(matches)} EPW map candidate(s)."),
    }


def _resolve_candidate(
    *,
    epw_map_target: dict[str, Any] | None,
    query: str | None,
    source: str | None,
    host: str | None,
) -> dict[str, Any]:
    if epw_map_target is not None:
        if isinstance(epw_map_target.get("matches"), list):
            matches = epw_map_target["matches"]
            if len(matches) != 1:
                raise ValueError(
                    "epw_map_target search response must contain exactly one match. "
                    f"Found {len(matches)}; pass matches[i].target explicitly."
            )
            epw_map_target = matches[0].get("target")
        if isinstance(epw_map_target, dict) and isinstance(epw_map_target.get("target"), dict):
            epw_map_target = epw_map_target["target"]
        target_type = epw_map_target.get("target_type") or epw_map_target.get("type")
        if target_type != EPWMAP_CANDIDATE_TARGET_TYPE:
            raise ValueError("epw_map_target must be an epw_map_weather target.")
        if "download_url" not in epw_map_target:
            station_id = epw_map_target.get("station_id") or epw_map_target.get("identifier")
            source_value = str(epw_map_target.get("source") or "").lower()
            host_value = str(epw_map_target.get("host") or "").lower()
            candidates = [
                record
                for record in _epwmap_records()
                if (station_id is None or str(record.get("station_id")) == str(station_id))
                and (not source_value or str(record.get("source", "")).lower() == source_value)
                and (not host_value or str(record.get("host", "")).lower() == host_value)
            ]
            if len(candidates) != 1:
                raise ValueError(
                    "Minimal epw_map_target must identify exactly one EPW map record. "
                    f"Found {len(candidates)}; pass search_epw_map matches[i].target."
                )
            epw_map_target = _candidate_target(candidates[0])
        return {
            "station_id": epw_map_target.get("station_id"),
            "station": epw_map_target.get("station"),
            "source": epw_map_target.get("source"),
            "host": epw_map_target.get("host"),
            "download_url": epw_map_target["download_url"],
        }

    search = search_epw_map(query=query, source=source, host=host, max_results=2)
    matches = search["matches"]
    if len(matches) != 1:
        source_tokens = _source_tokens_from_query(query)
        if source:
            source_tokens.add(str(source).strip().lower())
        if source_tokens:
            source_filtered = [
                match
                for match in matches
                if str(match.get("source", "")).lower() in source_tokens
            ]
            if len(source_filtered) == 1:
                return source_filtered[0]
            doe_filtered = [
                match for match in source_filtered if str(match.get("host", "")).lower() == "doe"
            ]
            if len(doe_filtered) == 1:
                return doe_filtered[0]
        raise ValueError(
            "EPW map query must identify exactly one candidate. "
            f"Found {len(matches)}; call search_epw_map first and pass epw_map_target_."
        )
    return matches[0]


def _download_zip(url: str, zip_path: Path) -> None:
    download_file(url, str(zip_path), mkdir=True)


def _weather_identifier(candidate: dict[str, Any]) -> str:
    identifier = slugify_name(
        f"{candidate.get('station')}_{candidate.get('station_id')}_{candidate.get('source')}"
    )
    return identifier.replace("-", "_")


def _weather_output_folder(garden_root: Path, candidate: dict[str, Any]) -> Path:
    return garden_root / "imports" / "weather" / _weather_identifier(candidate)


def _find_extracted_weather_files(folder: Path) -> tuple[Path, Path | None, Path | None]:
    epw_files = sorted(folder.rglob("*.epw"))
    if not epw_files:
        raise ValueError("Downloaded EPW map archive did not contain an EPW file.")
    epw_path = epw_files[0].resolve()
    siblings = list(epw_path.parent.iterdir())
    ddy_path = next((path.resolve() for path in siblings if path.suffix.lower() == ".ddy"), None)
    stat_path = next((path.resolve() for path in siblings if path.suffix.lower() == ".stat"), None)
    return epw_path, ddy_path, stat_path


def download_epw(
    *,
    garden_root: str | None = None,
    epw_map_target: dict[str, Any] | None = None,
    query: str | None = None,
    source: str | None = None,
    host: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Download one EPW map archive, unzip it, and return a weather_file target."""
    if not garden_root:
        raise ValueError("download_epw requires garden_root; weather files are Garden-managed.")
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    candidate = _resolve_candidate(
        epw_map_target=epw_map_target,
        query=query,
        source=source,
        host=host,
    )
    output_folder = _weather_output_folder(garden_root_path, candidate)
    output_folder.mkdir(parents=True, exist_ok=True)
    zip_name = Path(urlparse(str(candidate["download_url"])).path).name
    if not zip_name:
        raise ValueError("EPW map download URL does not include a file name.")
    zip_path = output_folder / zip_name
    if overwrite or not zip_path.is_file():
        _download_zip(str(candidate["download_url"]), zip_path)
    unzip_file(str(zip_path), str(output_folder), mkdir=True)
    epw_path, ddy_path, stat_path = _find_extracted_weather_files(output_folder)
    identifier = _weather_identifier(candidate)
    target = make_garden_weather_target(
        garden_root=garden_root_path,
        manifest=manifest,
        identifier=identifier,
        epw_path=epw_path,
        ddy_path=ddy_path,
        stat_path=stat_path,
        metadata={
            "station_id": candidate.get("station_id"),
            "station": candidate.get("station"),
            "source": candidate.get("source"),
            "host": candidate.get("host"),
            "download_url": candidate.get("download_url"),
        },
    )
    manifest.weather_files = [
        item
        for item in manifest.weather_files
        if item.get("identifier") != target["identifier"]
    ]
    manifest.weather_files.append(target)
    manifest.weather_files.sort(key=lambda item: str(item.get("identifier", "")))
    manifest.write(garden_root_path)
    return {
        "target": target,
        "weather_target": target,
        "weather_file": target,
        "summary_view": {
            "garden_target": manifest.target(),
            "identifier": identifier,
            "station_id": candidate.get("station_id"),
            "station": candidate.get("station"),
            "source": candidate.get("source"),
            "host": candidate.get("host"),
            "download_url": candidate.get("download_url"),
            "epw_path": target["epw_path"],
            "ddy_path": target.get("ddy_path"),
            "stat_path": target.get("stat_path"),
            "folder": target["path"],
        },
        "report": make_report(
            status="ok",
            message=f"Downloaded EPW weather file: {candidate.get('station')}",
        ),
    }
