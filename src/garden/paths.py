"""Garden path helpers."""

from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable


DEFAULT_GARDENS_ROOT = Path(
    os.environ.get("LADYBUG_TOOLS_GARDENS_ROOT")
    or Path.home() / "Gardens"
).expanduser().resolve()
_WINDOWS_INVALID_FILENAME_CHARACTERS = frozenset('<>:"/\\|?*')
_WINDOWS_RESERVED_FILENAME_STEMS = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "CONIN$",
        "CONOUT$",
        "CLOCK$",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
)


def slugify_name(value: str) -> str:
    """Convert a user label into a conservative filesystem slug."""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip()).strip("_").lower()
    return slug or "garden"


def simulation_folder_name(display_name: str) -> str:
    """Apply the LBT Grasshopper model-folder naming rule."""
    return validate_portable_file_name(
        re.sub(r"[^.A-Za-z0-9_-]", "_", display_name),
        label="Simulation folder name",
    )


def validate_portable_file_name(value: str, *, label: str = "File name") -> str:
    """Validate one file name for the supported POSIX and Windows runtimes."""
    if not value or value in {".", ".."}:
        raise ValueError(f"{label} must be a non-empty portable file name.")
    if value.endswith((" ", ".")) or any(
        character in _WINDOWS_INVALID_FILENAME_CHARACTERS or ord(character) < 32
        for character in value
    ):
        raise ValueError(f"{label} contains characters unsupported in file names.")
    stem = value.split(".", 1)[0].rstrip(" ").upper()
    if stem in _WINDOWS_RESERVED_FILENAME_STEMS:
        raise ValueError(f"{label} uses a Windows-reserved file name.")
    if len(value.encode("utf-8")) > 255 or len(value.encode("utf-16-le")) // 2 > 255:
        raise ValueError(f"{label} exceeds the portable 255-unit component limit.")
    return value


def windows_path_key(value: str | Path) -> str:
    """Return a conservative key for Windows-equivalent paths and names."""
    return str(value).replace("\\", "/").casefold()


def reject_windows_alias(
    value: str,
    existing_values: Iterable[Any],
    *,
    label: str,
) -> None:
    """Reject a value that aliases another value on a case-insensitive filesystem."""
    value_key = windows_path_key(value)
    for existing in existing_values:
        if isinstance(existing, str) and windows_path_key(existing) == value_key:
            raise ValueError(f"{label} conflicts with existing value {existing!r} on Windows.")


def require_garden_root(value: str | Path) -> Path:
    """Resolve a user-supplied Garden root directory path."""
    return Path(value).expanduser().resolve()


def resolve_existing_garden_path(
    garden_root: Path,
    value: str | Path,
    *,
    kind: str = "file",
    suffix: str | None = None,
    label: str = "Garden path",
) -> Path:
    """Resolve an absolute or Garden-relative path and enforce Garden containment."""
    root_resolved = require_garden_root(garden_root)
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = root_resolved / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside the Garden.") from exc
    if kind == "file":
        if suffix is not None and resolved.suffix.lower() != suffix.lower():
            raise ValueError(f"{label} must reference a {suffix} file.")
        if not resolved.is_file():
            raise ValueError(f"{label} was not found: {value}")
    elif kind == "directory":
        if not resolved.is_dir():
            raise ValueError(f"{label} directory was not found: {value}")
    else:  # pragma: no cover - internal guard
        raise ValueError(f"Unsupported path kind: {kind}")
    return resolved


def resolve_garden_root(name: str, root_dir: str | None) -> Path:
    """Resolve the Garden root directory."""
    if root_dir:
        return Path(root_dir).expanduser().resolve()
    return (DEFAULT_GARDENS_ROOT / slugify_name(name)).resolve()


def to_posix_relative(path: Path, root: Path) -> str:
    """Return a stable POSIX-style path relative to a root."""
    return path.resolve().relative_to(root.resolve()).as_posix()


def resolve_contained_path(
    root: Path,
    relative_path: str | Path,
    *,
    label: str = "Garden path",
) -> Path:
    """Resolve a relative path and ensure it stays inside ``root``."""
    if relative_path is None or isinstance(relative_path, bool):
        raise ValueError(f"{label} must be a relative path string.")
    text = str(relative_path).strip().replace("\\", "/")
    posix_path = PurePosixPath(text)
    windows_path = PureWindowsPath(text)
    if (
        not text
        or posix_path.is_absolute()
        or windows_path.drive
        or windows_path.root
        or any(part in {"", ".", ".."} for part in posix_path.parts)
    ):
        raise ValueError(f"{label} must be relative and contained: {relative_path!r}.")
    for part in posix_path.parts:
        validate_portable_file_name(part, label=f"{label} component")
    root_resolved = root.expanduser().resolve()
    candidate = (root_resolved / posix_path).resolve()
    if not candidate.is_relative_to(root_resolved):
        raise ValueError(f"{label} must stay inside the Garden: {relative_path!r}.")
    return candidate
