"""Download EPW weather files from the public epwapi/epwfile service."""

from __future__ import annotations

import json
import shutil
import time
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterator
from urllib.parse import quote, urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from garden.manifest import GardenManifest
from garden.paths import slugify_name, to_posix_relative, validate_portable_file_name
from ladybug_tools_mcp.contracts.report import make_report
from garden.run_energy.config import make_garden_weather_target


EPW_API_URL = "http://epwapi.greensimhub.com.cn"
EPW_FILE_URL = "https://epwfile.greensimhub.com.cn"
_USER_AGENT = "LadybugToolsMCP/1.1"
_HEALTH_TIMEOUT = 20
_API_TIMEOUT = 60
_DOWNLOAD_TIMEOUT = 300
_OSS_PAGE_SIZE = 1000


def _request_bytes(url: str, *, timeout: int) -> bytes:
    for attempt in range(3):
        request = Request(
            url,
            headers={
                "Accept": "application/json, application/xml, text/xml, */*",
                "User-Agent": _USER_AGENT,
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except HTTPError:
            if attempt == 2:
                raise
            time.sleep(0.5 * (2**attempt))
    raise RuntimeError("Unreachable weather request retry state.")


def _request_json(url: str, *, params: dict[str, Any] | None = None, timeout: int) -> Any:
    if params:
        url = f"{url}?{urlencode(params)}"
    return json.loads(_request_bytes(url, timeout=timeout).decode("utf-8"))


def _api_health() -> dict[str, Any]:
    health = _request_json(f"{EPW_API_URL}/v1/health", timeout=_HEALTH_TIMEOUT)
    if not isinstance(health, dict):
        raise ValueError("epwapi health response must be an object.")
    expected = {
        "status": "ok",
        "api_version": "v1",
        "data_source": "aliyun-oss",
        "prefix": "epwfile",
    }
    if any(health.get(key) != value for key, value in expected.items()):
        raise ValueError("epwapi health response is not a supported v1 OSS service.")
    return health


def _api_file_search(
    *,
    query: str | None,
    region: str | None,
    country: str | None,
    admin_region: str | None,
    file_format: str,
    page_size: int,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"page": 1, "page_size": page_size, "format": file_format}
    for key, value in (
        ("query", query),
        ("region", region),
        ("country", country),
        ("admin_region", admin_region),
    ):
        if value:
            params[key] = value

    matches: list[dict[str, Any]] = []
    while True:
        result = _request_json(f"{EPW_API_URL}/v1/files", params=params, timeout=_API_TIMEOUT)
        if not isinstance(result, dict) or not isinstance(result.get("items"), list):
            raise ValueError("epwapi files response must contain an items array.")
        matches.extend(item for item in result["items"] if isinstance(item, dict))
        pages = result.get("pages", 1)
        page = result.get("page", params["page"])
        if not isinstance(pages, int) or not isinstance(page, int) or page >= pages:
            break
        params["page"] = page + 1
    return matches


def _api_file_detail(file_id: str) -> dict[str, Any]:
    result = _request_json(
        f"{EPW_API_URL}/v1/files/{quote(file_id, safe='')}",
        timeout=_API_TIMEOUT,
    )
    if isinstance(result, dict) and isinstance(result.get("file"), dict):
        result = result["file"]
    if not isinstance(result, dict):
        raise ValueError("epwapi file detail response must be an object.")
    result.setdefault("id", file_id)
    return result


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xml_text(element: ET.Element, name: str) -> str | None:
    for child in element:
        if _xml_local_name(child.tag) == name:
            return child.text or ""
    return None


def _oss_objects(prefix: str) -> Iterator[dict[str, Any]]:
    token: str | None = None
    while True:
        params: dict[str, Any] = {
            "list-type": "2",
            "prefix": prefix,
            "max-keys": str(_OSS_PAGE_SIZE),
        }
        if token:
            params["continuation-token"] = token
        url = f"{EPW_FILE_URL}/?{urlencode(params)}"
        root = ET.fromstring(_request_bytes(url, timeout=_API_TIMEOUT))
        for element in root.iter():
            if _xml_local_name(element.tag) != "Contents":
                continue
            key = _xml_text(element, "Key")
            if key:
                size = _xml_text(element, "Size")
                yield {"key": key, "size": int(size) if size and size.isdigit() else None}
        truncated = (_xml_text(root, "IsTruncated") or "").strip().lower() == "true"
        if not truncated:
            return
        token = _xml_text(root, "NextContinuationToken")
        if not token:
            raise ValueError("epwfile list response is truncated without a continuation token.")


def _directory_prefix(
    *,
    region: str | None,
    country: str | None,
    admin_region: str | None,
) -> str:
    values = [region, country, admin_region]
    for value in values:
        if value and ("/" in value or "\\" in value or value in {".", ".."}):
            raise ValueError("Weather directory fields must be single path components.")
    if not region or not country:
        return "epwfile/"
    parts = ["epwfile", region, country]
    if admin_region:
        parts.append(admin_region)
    return "/".join(parts) + "/"


def _item_name(item: dict[str, Any]) -> str:
    name = item.get("name") or item.get("file_name")
    if not name and item.get("object_key"):
        name = str(item["object_key"]).rsplit("/", 1)[-1]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Weather file metadata requires a file name.")
    name = name.strip()
    validate_portable_file_name(name, label="Weather file name")
    if Path(name).suffix.lower() not in {".epw", ".zip"}:
        raise ValueError("Weather file name must end with .epw or .zip.")
    return name


def _item_format(item: dict[str, Any], name: str) -> str:
    value = str(item.get("format") or Path(name).suffix[1:]).strip().lower()
    if value not in {"epw", "zip"}:
        raise ValueError("Weather format must be epw or zip.")
    if Path(name).suffix.lower() != f".{value}":
        raise ValueError("Weather file format does not match its file name.")
    return value


def _fallback_search(
    *,
    query: str | None,
    file_name: str | None,
    region: str | None,
    country: str | None,
    admin_region: str | None,
    file_format: str,
) -> dict[str, Any]:
    prefix = _directory_prefix(
        region=region,
        country=country,
        admin_region=admin_region,
    )
    matches: list[dict[str, Any]] = []
    query_value = (query or "").casefold()
    expected_name = file_name.casefold() if file_name else None
    for row in _oss_objects(prefix):
        key = str(row["key"])
        name = key.rsplit("/", 1)[-1]
        if Path(name).suffix.lower() != f".{file_format}":
            continue
        if expected_name and name.casefold() != expected_name:
            continue
        if query_value and query_value not in key.casefold():
            continue
        parts = key.split("/")
        item: dict[str, Any] = {
            "name": name,
            "format": file_format,
            "object_key": key,
            "size": row.get("size"),
        }
        if len(parts) >= 3:
            item["region"], item["country"] = parts[1], parts[2]
        if len(parts) >= 4:
            item["admin_region"] = parts[3]
        matches.append(item)
        if len(matches) > 1:
            break
    if not matches:
        raise LookupError("No matching EPW weather file was found.")
    if len(matches) != 1:
        raise ValueError(
            "Weather query matched multiple files; add region, country, admin_region, "
            "file_name, or a more specific query."
        )
    return matches[0]


def _object_key_from_item(item: dict[str, Any]) -> str:
    raw = item.get("object_key") or item.get("key")
    if raw:
        key = str(raw).strip()
        parts = key.split("/")
        if (
            not key.startswith("epwfile/")
            or key.endswith("/")
            or any(part in {"", ".", ".."} for part in parts)
        ):
            raise ValueError("object_key must be an epwfile object key.")
        return key
    name = _item_name(item)
    prefix = _directory_prefix(
        region=item.get("region"),
        country=item.get("country"),
        admin_region=item.get("admin_region"),
    )
    candidates = [
        row["key"]
        for row in _oss_objects(prefix)
        if str(row["key"]).rsplit("/", 1)[-1] == name
    ]
    if not candidates:
        raise LookupError(f"Object not found in epwfile: {name}")
    if len(candidates) > 1:
        raise ValueError(f"Multiple epwfile objects have the name {name!r}.")
    return str(candidates[0])


def _download_url(url: str, destination: Path) -> None:
    partial = destination.with_name(destination.name + ".part")
    partial.unlink(missing_ok=True)
    try:
        for attempt in range(3):
            request = Request(
                url,
                headers={
                    "Accept": "application/octet-stream",
                    "User-Agent": _USER_AGENT,
                },
            )
            try:
                with urlopen(request, timeout=_DOWNLOAD_TIMEOUT) as response:
                    with partial.open("wb") as output:
                        shutil.copyfileobj(response, output, length=1024 * 1024)
                partial.replace(destination)
                return
            except HTTPError:
                if attempt == 2:
                    raise
                time.sleep(0.5 * (2**attempt))
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def _extract_zip(archive_path: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            relative = PurePosixPath(member.filename)
            if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
                raise ValueError("Downloaded weather ZIP contains an invalid path.")
            target = (destination / Path(*relative.parts)).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise ValueError("Downloaded weather ZIP escaped its Garden folder.") from exc
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)


def _weather_files(destination: Path, preferred_stem: str) -> tuple[Path, Path | None, Path | None]:
    epw_files = sorted(
        path for path in destination.rglob("*") if path.is_file() and path.suffix.lower() == ".epw"
    )
    if not epw_files:
        raise ValueError("Downloaded weather ZIP did not contain an EPW file.")
    epw_path = next(
        (path for path in epw_files if path.stem.casefold() == preferred_stem.casefold()),
        epw_files[0],
    )
    siblings = {path.suffix.lower(): path for path in epw_path.parent.iterdir() if path.is_file()}
    ddy_path = siblings.get(".ddy")
    stat_path = siblings.get(".stat")
    if ddy_path is None:
        ddy_path = next(
            (
                path
                for path in sorted(destination.rglob("*"))
                if path.is_file() and path.suffix.lower() == ".ddy"
            ),
            None,
        )
    if stat_path is None:
        stat_path = next(
            (
                path
                for path in sorted(destination.rglob("*"))
                if path.is_file() and path.suffix.lower() == ".stat"
            ),
            None,
        )
    return epw_path, ddy_path, stat_path


def _weather_identifier(item: dict[str, Any], name: str) -> str:
    station = item.get("station_name") or item.get("station") or item.get("wmo_station") or item.get("station_id")
    suffix = item.get("wmo_station") or item.get("station_id")
    label = "_".join(str(value) for value in (station or Path(name).stem, suffix) if value)
    return slugify_name(label).replace("-", "_")


def _aliases(
    *,
    target: dict[str, Any],
    summary_view: dict[str, Any],
    report: dict[str, Any],
    persistence_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "target": target,
        "weather_target": target,
        "weather_file_target": target,
        "weather_file": target,
        "summary_view": summary_view,
        "report": report,
    }
    if persistence_receipt is not None:
        result["persistence_receipt"] = persistence_receipt
    return result


def _blocked_response(
    *,
    garden_root: Path,
    item: dict[str, Any] | None,
    error: Exception,
    api_error: Exception | None,
) -> dict[str, Any]:
    download_url = str(item.get("download_url") or "") if item else ""
    object_key = str(item.get("object_key") or "") if item else ""
    expected_path: str | None = None
    if item:
        try:
            name = _item_name(item)
            expected_path = to_posix_relative(
                garden_root / "imports" / "weather" / _weather_identifier(item, name) / name,
                garden_root,
            )
        except (TypeError, ValueError):
            pass
    recovery = {
        "reason": "external_weather_download_failed",
        "download_url": download_url,
        "object_key": object_key,
        "garden_relative_path": expected_path,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "api_health_error": str(api_error) if api_error else None,
        "manual_recovery": (
            "Retry the same request when the weather service is reachable, or download "
            "the EPW/ZIP object from object_url and import it with EP_import_local_weather."
        ),
    }
    if object_key:
        recovery["object_url"] = f"{EPW_FILE_URL}/{quote(object_key, safe='/')}"
    return {
        "summary_view": {
            "status": "blocked",
            "blocker": "external_weather_download_failed",
            "download_url": download_url,
            "object_key": object_key,
            "recommended_next_step": recovery["manual_recovery"],
        },
        "download_recovery": recovery,
        "report": make_report(
            status="blocked",
            message="Weather download failed at the remote weather source.",
            details=recovery,
        ),
    }


def download_weather(
    *,
    garden_root: str,
    query: str | None = None,
    file_id: str | None = None,
    file_name: str | None = None,
    object_key: str | None = None,
    file_target: dict[str, Any] | None = None,
    region: str | None = None,
    country: str | None = None,
    admin_region: str | None = None,
    file_format: str = "zip",
    page_size: int = 20,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Search and download one EPW file, preferring epwapi then epwfile."""
    file_format = str(file_format).strip().lower()
    if file_format not in {"epw", "zip"}:
        raise ValueError("file_format must be epw or zip.")
    if isinstance(page_size, bool) or not 1 <= page_size <= 200:
        raise ValueError("page_size must be between 1 and 200.")
    if not any((query, file_id, file_name, object_key, file_target)):
        raise ValueError("Provide query, file_id, file_name, object_key, or file_target.")

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    api_error: Exception | None = None
    api_available = True
    try:
        _api_health()
    except Exception as error:
        api_available = False
        api_error = error

    item: dict[str, Any] | None = dict(file_target) if isinstance(file_target, dict) else None
    if file_target is not None and item is None:
        raise ValueError("file_target must be an object returned by the weather API.")
    if object_key:
        item = item or {}
        item["object_key"] = object_key
    if file_name:
        item = item or {}
        item["name"] = file_name
    if file_id:
        item = item or {}
        item["id"] = file_id

    if item is None and query and api_available:
        try:
            matches = _api_file_search(
                query=query,
                region=region,
                country=country,
                admin_region=admin_region,
                file_format=file_format,
                page_size=page_size,
            )
        except Exception as error:
            api_error = error
            api_available = False
        else:
            if not matches:
                raise LookupError("No matching EPW weather file was found.")
            if len(matches) != 1:
                raise ValueError(
                    "Weather query matched multiple files; add region, country, "
                    "admin_region, or a more specific query."
                )
            item = matches[0]

    if item is None and query:
        try:
            item = _fallback_search(
                query=query,
                file_name=file_name,
                region=region,
                country=country,
                admin_region=admin_region,
                file_format=file_format,
            )
        except Exception as error:
            return _blocked_response(
                garden_root=garden_root_path,
                item=None,
                error=error,
                api_error=api_error,
            )

    if item is None and file_id and api_available:
        try:
            item = _api_file_detail(file_id)
        except Exception as error:
            api_error = error
            api_available = False

    if item is None:
        return _blocked_response(
            garden_root=garden_root_path,
            item=None,
            error=ValueError("Weather file metadata is unavailable."),
            api_error=api_error,
        )

    # A full API file target may be passed with only an id; hydrate its directory fields.
    if file_id and api_available and not item.get("region"):
        try:
            item = {**_api_file_detail(file_id), **item}
        except Exception as error:
            api_error = error
            api_available = False

    name = _item_name(item)
    item_format = _item_format(item, name)
    identifier = _weather_identifier(item, name)
    destination = garden_root_path / "imports" / "weather" / identifier
    existing = next(
        (target for target in manifest.weather_files if target.get("identifier") == identifier),
        None,
    )
    if not overwrite and existing and existing.get("epw_path"):
        existing_epw = (garden_root_path / str(existing["epw_path"])).resolve()
        if existing_epw.is_file():
            return _aliases(
                target=existing,
                summary_view={
                    "garden_target": manifest.target(),
                    "identifier": identifier,
                    "status": "already_registered",
                },
                report=make_report(status="ok", message=f"Weather already registered: {identifier}"),
            )
    if overwrite and destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)

    download_source = "epwfile"
    selected_object_key: str | None = None
    object_error: Exception | None = None
    if item.get("object_key"):
        selected_object_key = _object_key_from_item(item)
    else:
        try:
            selected_object_key = _object_key_from_item(item)
        except Exception as error:
            object_error = error

    download_path = destination / name
    try:
        if not download_path.is_file():
            if selected_object_key:
                object_url = f"{EPW_FILE_URL}/{quote(selected_object_key, safe='/')}"
                _download_url(object_url, download_path)
            elif api_available and item.get("id"):
                download_source = "epwapi"
                api_download_url = f"{EPW_API_URL}/v1/files/{quote(str(item['id']), safe='')}/download"
                _download_url(api_download_url, download_path)
            else:
                raise object_error or LookupError("No downloadable weather object was found.")
    except Exception as oss_error:
        if selected_object_key and api_available and item.get("id"):
            try:
                download_source = "epwapi"
                api_download_url = f"{EPW_API_URL}/v1/files/{quote(str(item['id']), safe='')}/download"
                _download_url(api_download_url, download_path)
            except Exception as api_download_error:
                return _blocked_response(
                    garden_root=garden_root_path,
                    item={**item, "object_key": selected_object_key},
                    error=api_download_error,
                    api_error=api_error or oss_error,
                )
        else:
            return _blocked_response(
                garden_root=garden_root_path,
                item={**item, "object_key": selected_object_key},
                error=oss_error,
                api_error=api_error,
            )

    try:
        if item_format == "zip":
            _extract_zip(download_path, destination)
        epw_path, ddy_path, stat_path = _weather_files(destination, Path(name).stem)
    except Exception:
        if overwrite:
            shutil.rmtree(destination, ignore_errors=True)
        raise

    object_url = (
        f"{EPW_FILE_URL}/{quote(selected_object_key, safe='/')}"
        if selected_object_key
        else None
    )
    metadata = {
        "station_id": item.get("station_id"),
        "station": item.get("station_name") or item.get("station"),
        "wmo_station": item.get("wmo_station"),
        "source": item.get("source"),
        "host": item.get("host"),
        "region": item.get("region"),
        "country": item.get("country"),
        "admin_region": item.get("admin_region"),
        "file_id": item.get("id"),
        "file_name": name,
        "file_format": item_format,
        "download_source": download_source,
        "download_url": item.get("download_url"),
        "source_url": object_url or EPW_API_URL,
        "object_key": selected_object_key,
        "object_url": object_url,
        "search_terms": [
            value
            for value in (name, item.get("station_name"), item.get("station"), item.get("wmo_station"))
            if value
        ],
    }
    metadata = {key: value for key, value in metadata.items() if value is not None}
    target = make_garden_weather_target(
        garden_root=garden_root_path,
        manifest=manifest,
        identifier=identifier,
        epw_path=epw_path,
        ddy_path=ddy_path,
        stat_path=stat_path,
        metadata=metadata,
    )
    manifest.weather_files = [
        old for old in manifest.weather_files if old.get("identifier") != identifier
    ]
    manifest.weather_files.append(target)
    manifest.weather_files.sort(key=lambda old: str(old.get("identifier", "")))
    manifest.write(garden_root_path)
    warning = (
        ["epwapi was unavailable; downloaded from the epwfile OSS fallback."]
        if api_error and download_source == "epwfile"
        else []
    )
    report = make_report(
        status="ok",
        message=f"Downloaded weather file: {name}",
        warnings=warning,
    )
    return _aliases(
        target=target,
        summary_view={
            "garden_target": manifest.target(),
            "identifier": identifier,
            "file_name": name,
            "file_format": item_format,
            "station": metadata.get("station"),
            "wmo_station": metadata.get("wmo_station"),
            "region": metadata.get("region"),
            "country": metadata.get("country"),
            "admin_region": metadata.get("admin_region"),
            "download_source": download_source,
            "object_url": object_url,
            "epw_path": target["epw_path"],
            "ddy_path": target.get("ddy_path"),
            "stat_path": target.get("stat_path"),
            "folder": target["path"],
        },
        report=report,
        persistence_receipt={
            "status": "persisted",
            "garden_id": manifest.garden_id,
            "persisted_path": "garden.json",
            "target": target,
        },
    )
