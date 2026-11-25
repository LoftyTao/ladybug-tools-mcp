"""Download and search EPW weather files from the public epwapi/epwfile service."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path, PurePosixPath
import shutil
import ssl
import time
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import zipfile

from garden.manifest import GardenManifest
from garden.paths import slugify_name, to_posix_relative, validate_portable_file_name
from garden.run_energy.config import (
    compute_file_sha256,
    make_garden_weather_target,
    parse_epw_location_metadata,
    parse_weather_filename_metadata,
)
from ladybug_tools_mcp.contracts import make_report


EPW_API_URL = "https://epwapi.greensimhub.com.cn"
EPW_FILE_URL = "https://epwfile.greensimhub.com.cn"
_USER_AGENT = "LadybugToolsMCP/1.1"
_HEALTH_TIMEOUT = 20
_API_TIMEOUT = 60
_DOWNLOAD_TIMEOUT = 300
_OSS_PAGE_SIZE = 1000
_MAX_OSS_PAGES_UNSCOPED = 3
_MAX_OSS_PAGES_SCOPED = 20
_MAX_AMBIGUOUS_CANDIDATES = 20


@lru_cache(maxsize=1)
def _build_ssl_context() -> ssl.SSLContext:
    """Build a standard verified SSL context resilient to isolated Windows envs."""
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        pass

    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass

    context = ssl.create_default_context()
    if hasattr(ssl, "enum_certificates"):
        pem_blocks: list[str] = []
        for store_name in ("CA", "ROOT"):
            try:
                entries = ssl.enum_certificates(store_name)
            except OSError:
                continue
            for cert_bytes, encoding, _trust in entries:
                if encoding != "x509_asn":
                    continue
                try:
                    pem_blocks.append(ssl.DER_cert_to_PEM_cert(cert_bytes))
                except (ssl.SSLError, ValueError):
                    continue
        if pem_blocks:
            for pem in pem_blocks:
                try:
                    context.load_verify_locations(cadata=pem)
                except ssl.SSLError:
                    continue
    return context


def _should_fast_fail_request_error(exc: Exception) -> bool:
    if isinstance(exc, HTTPError):
        return 400 <= exc.code < 500 and exc.code != 429
    if isinstance(exc, URLError) and isinstance(getattr(exc, "reason", None), ssl.SSLError):
        return True
    return False


def _is_network_error(exc: Exception | None) -> bool:
    if exc is None:
        return False
    if isinstance(exc, HTTPError):
        return exc.code == 429 or exc.code >= 500
    return isinstance(exc, (URLError, TimeoutError, ConnectionError, OSError, ssl.SSLError))


def _request_bytes(url: str, *, timeout: int) -> bytes:
    context = _build_ssl_context() if url.lower().startswith("https://") else None
    for attempt in range(3):
        request = Request(
            url,
            headers={
                "Accept": "application/json, application/xml, text/xml, */*",
                "User-Agent": _USER_AGENT,
            },
        )
        try:
            with urlopen(request, timeout=timeout, context=context) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt == 2 or _should_fast_fail_request_error(exc):
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
    max_results: int | None = None,
) -> tuple[list[dict[str, Any]], bool]:
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
    truncated = False
    while True:
        result = _request_json(f"{EPW_API_URL}/v1/files", params=params, timeout=_API_TIMEOUT)
        if not isinstance(result, dict) or not isinstance(result.get("items"), list):
            raise ValueError("epwapi files response must contain an items array.")
        matches.extend(item for item in result["items"] if isinstance(item, dict))
        pages = result.get("pages", 1)
        page = result.get("page", params["page"])
        if max_results is not None and len(matches) >= max_results:
            truncated = len(matches) > max_results or (
                isinstance(pages, int) and isinstance(page, int) and page < pages
            )
            matches = matches[:max_results]
            break
        if not isinstance(pages, int) or not isinstance(page, int) or page >= pages:
            break
        params["page"] = page + 1
    return matches, truncated


def _api_file_detail(file_id: str) -> dict[str, Any]:
    try:
        result = _request_json(
            f"{EPW_API_URL}/v1/files/{quote(file_id, safe='')}",
            timeout=_API_TIMEOUT,
        )
    except HTTPError as exc:
        if exc.code == 404:
            raise LookupError(f"Weather file_id was not found: {file_id}") from exc
        raise
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


def _oss_objects(prefix: str, *, max_pages: int | None = None) -> Iterator[dict[str, Any]]:
    token: str | None = None
    page_num = 0
    while True:
        if max_pages is not None and page_num >= max_pages:
            return
        page_num += 1
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
    if not region:
        return "epwfile/"
    parts = ["epwfile", region]
    if country:
        parts.append(country)
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


def _candidate_item(item: dict[str, Any]) -> dict[str, Any]:
    object_key = item.get("object_key") or item.get("key")
    file_name = item.get("file_name") or item.get("name")
    if not file_name and object_key:
        file_name = str(object_key).rsplit("/", 1)[-1]
    file_name_str = str(file_name).strip() if file_name else None
    parsed = parse_weather_filename_metadata(file_name_str or "")
    station = item.get("station_name") or item.get("station") or parsed.get("station")
    fmt = item.get("format")
    if not fmt and file_name_str and Path(file_name_str).suffix:
        fmt = Path(file_name_str).suffix[1:].lower()
    return {
        "file_id": item.get("file_id") or item.get("id"),
        "file_name": file_name_str,
        "station": station,
        "region": item.get("region"),
        "country": item.get("country"),
        "admin_region": item.get("admin_region"),
        "object_key": object_key,
        "format": str(fmt).lower() if fmt else None,
    }


def _filter_matches_by_fields(
    matches: list[dict[str, Any]],
    *,
    file_name: str | None = None,
    region: str | None = None,
    country: str | None = None,
    admin_region: str | None = None,
) -> list[dict[str, Any]]:
    filtered = matches
    if file_name:
        expected = file_name.strip().casefold()
        filtered = [
            item
            for item in filtered
            if str(item.get("name") or item.get("file_name") or "").strip().casefold() == expected
        ]
    if region:
        expected_region = region.strip().casefold()
        filtered = [
            item
            for item in filtered
            if str(item.get("region") or "").strip().casefold() == expected_region
        ]
    if country:
        expected_country = country.strip().casefold()
        filtered = [
            item
            for item in filtered
            if str(item.get("country") or "").strip().casefold() == expected_country
        ]
    if admin_region:
        expected_admin = admin_region.strip().casefold()
        filtered = [
            item
            for item in filtered
            if str(item.get("admin_region") or "").strip().casefold() == expected_admin
        ]
    return filtered


def _oss_file_search(
    *,
    query: str | None,
    file_name: str | None,
    region: str | None,
    country: str | None,
    admin_region: str | None,
    file_format: str,
    max_results: int = _MAX_AMBIGUOUS_CANDIDATES,
) -> tuple[list[dict[str, Any]], bool]:
    prefix = _directory_prefix(
        region=region,
        country=country,
        admin_region=admin_region,
    )
    unscoped = not (region and country)
    max_pages = _MAX_OSS_PAGES_UNSCOPED if unscoped else _MAX_OSS_PAGES_SCOPED
    max_scanned = max_pages * _OSS_PAGE_SIZE

    matches: list[dict[str, Any]] = []
    query_tokens = [tok for tok in (query or "").casefold().split() if tok]
    expected_name = file_name.strip().casefold() if file_name else None
    country_filter = country.strip().casefold() if country else None
    admin_filter = admin_region.strip().casefold() if admin_region else None
    scanned = 0
    truncated = False

    for row in _oss_objects(prefix, max_pages=max_pages):
        scanned += 1
        key = str(row["key"])
        name = key.rsplit("/", 1)[-1]
        if Path(name).suffix.lower() != f".{file_format}":
            continue
        parts = key.split("/")
        row_region = parts[1] if len(parts) >= 3 else None
        row_country = parts[2] if len(parts) >= 3 else None
        row_admin = parts[3] if len(parts) >= 4 else None
        if country_filter and (row_country or "").casefold() != country_filter:
            continue
        if admin_filter and (row_admin or "").casefold() != admin_filter:
            continue
        if expected_name and name.casefold() != expected_name:
            continue
        if query_tokens and not all(tok in key.casefold() for tok in query_tokens):
            continue
        parsed = parse_weather_filename_metadata(name)
        item: dict[str, Any] = {
            "name": name,
            "file_name": name,
            "station": parsed.get("station"),
            "format": file_format,
            "object_key": key,
            "size": row.get("size"),
        }
        if row_region:
            item["region"] = row_region
        if row_country:
            item["country"] = row_country
        if row_admin:
            item["admin_region"] = row_admin
        matches.append(item)
        if len(matches) >= max_results:
            truncated = True
            break
    if scanned >= max_scanned and not matches:
        truncated = True
    return matches, truncated


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
    matches, _truncated = _oss_file_search(
        query=None,
        file_name=name,
        region=item.get("region"),
        country=item.get("country"),
        admin_region=item.get("admin_region"),
        file_format=_item_format(item, name),
        max_results=2,
    )
    if not matches:
        raise LookupError(f"Object not found in epwfile: {name}")
    if len(matches) > 1:
        raise ValueError(f"Multiple epwfile objects have the name {name!r}.")
    return str(matches[0]["object_key"])


def _download_url(url: str, destination: Path) -> None:
    partial = destination.with_name(destination.name + ".part")
    partial.unlink(missing_ok=True)
    context = _build_ssl_context() if url.lower().startswith("https://") else None
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
                with urlopen(request, timeout=_DOWNLOAD_TIMEOUT, context=context) as response:
                    with partial.open("wb") as output:
                        shutil.copyfileobj(response, output, length=1024 * 1024)
                partial.replace(destination)
                return
            except (HTTPError, URLError, TimeoutError) as exc:
                if attempt == 2 or _should_fast_fail_request_error(exc):
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


def _ambiguous_response(
    *,
    manifest: GardenManifest,
    matches: list[dict[str, Any]],
    query: str | None,
) -> dict[str, Any]:
    candidates = [_candidate_item(item) for item in matches[:_MAX_AMBIGUOUS_CANDIDATES]]
    message = (
        f"Weather query matched {len(matches)} files; pick a specific "
        "file_id, file_name, or object_key from matches."
    )
    next_step = (
        "Re-run LB_Manage_Weather with action='download' passing file_id, "
        "file_name, or object_key from one of the returned matches."
    )
    return {
        "status": "ambiguous",
        "matches": candidates,
        "summary_view": {
            "garden_target": manifest.target(),
            "status": "ambiguous",
            "blocker": "ambiguous_weather_query",
            "query": query,
            "total_matches": len(matches),
            "returned_matches": len(candidates),
            "recommended_next_step": next_step,
        },
        "report": make_report(
            status="blocked",
            message=message,
            details={
                "blocker": "ambiguous_weather_query",
                "total_matches": len(matches),
                "candidates": candidates,
            },
        ),
    }


def _blocked_response(
    *,
    garden_root: Path | None,
    item: dict[str, Any] | None,
    error: Exception,
    api_error: Exception | None,
    operation: str = "download",
) -> dict[str, Any]:
    download_url = str(item.get("download_url") or "") if item else ""
    object_key = str(item.get("object_key") or "") if item else ""
    expected_path: str | None = None
    if item and garden_root is not None:
        try:
            name = _item_name(item)
            expected_path = to_posix_relative(
                garden_root / "imports" / "weather" / _weather_identifier(item, name) / name,
                garden_root,
            )
        except (TypeError, ValueError):
            pass

    if isinstance(error, LookupError):
        blocker = "station_not_found"
        report_message = str(error) or "No matching remote EPW weather file was found."
        manual_recovery = (
            "Broaden or adjust query, use LB_Manage_Weather(action='search_remote') to "
            "browse matching stations, or import a local EPW with action='import'."
        )
    elif _is_network_error(error) or (_is_network_error(api_error) and isinstance(error, ValueError)):
        blocker = "network_error"
        report_message = "Weather request failed due to a network or TLS error at the remote weather source."
        manual_recovery = (
            "Retry when the weather service is reachable, or download the EPW/ZIP object "
            "from object_url and import it with LB_Manage_Weather(action='import')."
        )
    else:
        blocker = "external_weather_download_failed"
        report_message = f"Weather {operation} failed at the remote weather source."
        manual_recovery = (
            "Retry the same request when the weather service is reachable, or download "
            "the EPW/ZIP object from object_url and import it with LB_Manage_Weather(action='import')."
        )

    recovery = {
        "reason": blocker,
        "download_url": download_url,
        "object_key": object_key,
        "garden_relative_path": expected_path,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "api_health_error": str(api_error) if api_error else None,
        "manual_recovery": manual_recovery,
    }
    if object_key:
        recovery["object_url"] = f"{EPW_FILE_URL}/{quote(object_key, safe='/')}"
    result: dict[str, Any] = {
        "summary_view": {
            "status": "blocked",
            "blocker": blocker,
            "download_url": download_url,
            "object_key": object_key,
            "recommended_next_step": manual_recovery,
        },
        "download_recovery": recovery,
        "report": make_report(
            status="blocked",
            message=report_message,
            details=recovery,
        ),
    }
    if operation == "search_remote":
        result["matches"] = []
    return result


def search_remote_weather(
    *,
    garden_root: str | None = None,
    query: str | None = None,
    file_name: str | None = None,
    region: str | None = None,
    country: str | None = None,
    admin_region: str | None = None,
    file_format: str = "zip",
    max_results: int = 20,
) -> dict[str, Any]:
    """Search the public epwapi/epwfile catalog and return compact candidate items."""
    file_format = str(file_format).strip().lower()
    if file_format not in {"epw", "zip"}:
        raise ValueError("file_format must be epw or zip.")
    if isinstance(max_results, bool) or not 1 <= max_results <= 200:
        raise ValueError("max_results must be between 1 and 200.")
    if not any((query, file_name, region, country, admin_region)):
        raise ValueError("Provide query, file_name, region, country, or admin_region.")

    manifest: GardenManifest | None = None
    garden_root_path: Path | None = None
    if garden_root:
        garden_root_path = Path(garden_root).expanduser().resolve()
        if (garden_root_path / "garden.json").is_file():
            manifest = GardenManifest.read(garden_root_path)

    effective_format = file_format
    if file_name and Path(file_name.strip()).suffix.lower() in {".epw", ".zip"}:
        effective_format = Path(file_name.strip()).suffix[1:].lower()
    effective_query = query or (Path(file_name).stem if file_name else None)
    api_error: Exception | None = None
    search_source = "epwapi"
    truncated = False
    warnings: list[str] = []

    try:
        _api_health()
        raw_matches, truncated = _api_file_search(
            query=effective_query,
            region=region,
            country=country,
            admin_region=admin_region,
            file_format=effective_format,
            page_size=min(max(max_results, 20), 200),
            max_results=max_results if not file_name else None,
        )
        raw_matches = _filter_matches_by_fields(
            raw_matches,
            file_name=file_name,
            region=region,
            country=country,
            admin_region=admin_region,
        )
        if len(raw_matches) > max_results:
            truncated = True
            raw_matches = raw_matches[:max_results]
    except Exception as error:
        api_error = error
        search_source = "epwfile"
        try:
            raw_matches, truncated = _oss_file_search(
                query=query,
                file_name=file_name,
                region=region,
                country=country,
                admin_region=admin_region,
                file_format=effective_format,
                max_results=max_results,
            )
            warnings.append("epwapi was unavailable; searched epwfile OSS fallback.")
            if truncated and not raw_matches:
                warnings.append(
                    "Unscoped OSS fallback scan was capped; add region/country for exhaustive results."
                )
        except Exception as oss_error:
            return _blocked_response(
                garden_root=garden_root_path,
                item=None,
                error=oss_error,
                api_error=api_error,
                operation="search_remote",
            )

    candidates = [_candidate_item(item) for item in raw_matches]
    summary_view: dict[str, Any] = {
        "scope": "remote",
        "query": query or "",
        "file_name": file_name,
        "region": region,
        "country": country,
        "admin_region": admin_region,
        "format": file_format,
        "count": len(candidates),
        "max_results": max_results,
        "source": search_source,
        "truncated": truncated,
    }
    if manifest is not None:
        summary_view["garden_target"] = manifest.target()

    return {
        "matches": candidates,
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message=f"Found {len(candidates)} remote weather file(s).",
            warnings=warnings,
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

    effective_format = file_format
    if file_name and Path(file_name.strip()).suffix.lower() in {".epw", ".zip"}:
        effective_format = Path(file_name.strip()).suffix[1:].lower()

    item: dict[str, Any] | None = dict(file_target) if isinstance(file_target, dict) else None
    if file_target is not None and item is None:
        raise ValueError("file_target must be an object returned by the weather API.")
    if object_key:
        item = item or {}
        item["object_key"] = object_key
    if file_id:
        item = item or {}
        item["id"] = file_id
    if file_name and item is not None:
        item["name"] = file_name

    if item is None and (query or file_name):
        matches: list[dict[str, Any]] | None = None
        if api_available:
            try:
                search_query = query or (Path(file_name).stem if file_name else None)
                raw_matches, _truncated = _api_file_search(
                    query=search_query,
                    region=region,
                    country=country,
                    admin_region=admin_region,
                    file_format=effective_format,
                    page_size=max(page_size, _MAX_AMBIGUOUS_CANDIDATES),
                    max_results=max(page_size, _MAX_AMBIGUOUS_CANDIDATES) if not file_name else None,
                )
                matches = _filter_matches_by_fields(
                    raw_matches,
                    file_name=file_name,
                    region=region,
                    country=country,
                    admin_region=admin_region,
                )
            except Exception as error:
                api_error = error
                api_available = False

        if matches is None:
            try:
                matches, oss_truncated = _oss_file_search(
                    query=query,
                    file_name=file_name,
                    region=region,
                    country=country,
                    admin_region=admin_region,
                    file_format=effective_format,
                    max_results=_MAX_AMBIGUOUS_CANDIDATES,
                )
            except Exception as error:
                return _blocked_response(
                    garden_root=garden_root_path,
                    item=None,
                    error=error,
                    api_error=api_error,
                )
            if not matches:
                msg = (
                    "OSS weather fallback scan was capped without region/country filter; "
                    "add region/country, file_id, or object_key."
                    if oss_truncated
                    else "No matching EPW weather file was found."
                )
                return _blocked_response(
                    garden_root=garden_root_path,
                    item=None,
                    error=LookupError(msg),
                    api_error=api_error,
                )

        if not matches:
            return _blocked_response(
                garden_root=garden_root_path,
                item=None,
                error=LookupError("No matching EPW weather file was found."),
                api_error=api_error,
            )
        if len(matches) > 1:
            return _ambiguous_response(
                manifest=manifest,
                matches=matches,
                query=query or file_name,
            )
        item = matches[0]

    if item is None and file_id and api_available:
        try:
            item = _api_file_detail(file_id)
        except Exception as error:
            if isinstance(error, LookupError):
                return _blocked_response(
                    garden_root=garden_root_path,
                    item=None,
                    error=error,
                    api_error=api_error,
                )
            api_error = error
            api_available = False

    if item is None:
        return _blocked_response(
            garden_root=garden_root_path,
            item=None,
            error=api_error or ValueError("Weather file metadata is unavailable."),
            api_error=api_error,
        )

    # A full API file target may be passed with only an id; hydrate its directory fields.
    if file_id and api_available and not item.get("region"):
        try:
            item = {**_api_file_detail(file_id), **item}
        except Exception as error:
            if isinstance(error, LookupError):
                return _blocked_response(
                    garden_root=garden_root_path,
                    item=item,
                    error=error,
                    api_error=api_error,
                )
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
    filename_meta = parse_weather_filename_metadata(epw_path.name)
    if filename_meta.get("dataset_version") is None:
        filename_meta = {
            **filename_meta,
            "dataset_version": parse_weather_filename_metadata(name).get("dataset_version"),
        }
    epw_loc = parse_epw_location_metadata(epw_path)
    epw_sha256 = compute_file_sha256(epw_path)
    station = (
        item.get("station_name")
        or item.get("station")
        or epw_loc.get("station")
        or filename_meta.get("station")
    )
    source_value = item.get("source") or download_source

    metadata = {
        "station_id": item.get("station_id"),
        "station": station,
        "wmo_station": item.get("wmo_station") or epw_loc.get("wmo_station"),
        "dataset_version": filename_meta.get("dataset_version"),
        "source": source_value,
        "epw_sha256": epw_sha256,
        "host": item.get("host"),
        "region": item.get("region"),
        "country": item.get("country"),
        "admin_region": item.get("admin_region"),
        "file_id": item.get("id") or item.get("file_id"),
        "file_name": name,
        "file_format": item_format,
        "download_source": download_source,
        "download_url": item.get("download_url"),
        "source_url": object_url or EPW_API_URL,
        "object_key": selected_object_key,
        "object_url": object_url,
        "search_terms": [
            value
            for value in (name, station, item.get("station_name"), item.get("wmo_station"))
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
            "station": target.get("station"),
            "wmo_station": target.get("wmo_station"),
            "dataset_version": target.get("dataset_version"),
            "source": target.get("source"),
            "epw_sha256": target.get("epw_sha256"),
            "region": target.get("region"),
            "country": target.get("country"),
            "admin_region": target.get("admin_region"),
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
