"""Bundled EPW weather resources."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote, unquote, urlparse


WEATHER_RESOURCE_ROOT = Path(__file__).resolve().parent / "resources" / "weather"
WEATHER_RESOURCE_PREFIX = "weather://files/"
WEATHER_SOURCE_URL = "https://climate.onebuilding.org/"
_WEATHER_SUFFIXES = {".epw", ".ddy", ".stat"}


def resolve_weather_source(value: str) -> Path:
    """Resolve a local path or bundled weather resource URI."""
    parsed = urlparse(value)
    if parsed.scheme != "weather":
        return Path(value).expanduser().resolve()
    if parsed.netloc != "files" or parsed.query or parsed.fragment:
        raise ValueError("Weather resource URI must use weather://files/<station>[/<file>].")
    relative = Path(unquote(parsed.path.lstrip("/")))
    path = (WEATHER_RESOURCE_ROOT / relative).resolve()
    try:
        path.relative_to(WEATHER_RESOURCE_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("Weather resource URI must stay inside bundled weather resources.") from exc
    if path.is_file() and path.suffix.lower() not in _WEATHER_SUFFIXES:
        raise ValueError("Bundled weather resources only include EPW, DDY, and STAT files.")
    return path


def register_weather_resources(mcp) -> None:
    """Register the bundled weather catalog and files with FastMCP."""
    from fastmcp.resources import FileResource, TextResource

    stations = []
    for folder in sorted(
        path for path in WEATHER_RESOURCE_ROOT.iterdir() if path.is_dir()
    ):
        files = sorted(
            path
            for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() in _WEATHER_SUFFIXES
        )
        stations.append(
            {
                "station": folder.name,
                "import_uri": WEATHER_RESOURCE_PREFIX + quote(folder.name, safe="._-"),
                "files": [
                    WEATHER_RESOURCE_PREFIX
                    + quote(path.relative_to(WEATHER_RESOURCE_ROOT).as_posix(), safe="/._-")
                    for path in files
                ],
            }
        )
    mcp.add_resource(
        TextResource(
            uri="weather://catalog",
            text=json.dumps(
                {
                    "source": "Climate.OneBuilding.Org",
                    "source_url": WEATHER_SOURCE_URL,
                    "stations": stations,
                },
                indent=2,
            ),
            mime_type="application/json",
            name="ladybug-tools-weather-catalog",
            title="Ladybug Tools bundled weather catalog",
            description=(
                "Bundled EPW, DDY, and STAT files sourced from Climate.OneBuilding.Org. "
                "Import a station with EP_import_local_weather using "
                "weather://files/<station>."
            ),
            tags={"weather", "epw", "energy", "radiance", "urbanopt"},
            meta={"source": "Climate.OneBuilding.Org", "source_url": WEATHER_SOURCE_URL},
        )
    )
    for path in sorted(WEATHER_RESOURCE_ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _WEATHER_SUFFIXES:
            continue
        relative = path.relative_to(WEATHER_RESOURCE_ROOT).as_posix()
        mcp.add_resource(
            FileResource(
                uri=WEATHER_RESOURCE_PREFIX + quote(relative, safe="/._-"),
                path=path,
                name=f"weather-{path.parent.name}-{path.suffix[1:]}",
                title=path.name,
                description=(
                    f"Bundled {path.suffix[1:].upper()} weather file from "
                    "Climate.OneBuilding.Org."
                ),
                mime_type="text/plain",
                encoding="cp1252",
                tags={"weather", path.suffix[1:].lower()},
                meta={"source": "Climate.OneBuilding.Org", "source_url": WEATHER_SOURCE_URL},
            )
        )
