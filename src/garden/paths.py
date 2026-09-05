"""Garden path helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GARDENS_ROOT = PROJECT_ROOT / "gardens"
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
        *(f"COM{suffix}" for suffix in ("\u00b9", "\u00b2", "\u00b3")),
        *(f"LPT{suffix}" for suffix in ("\u00b9", "\u00b2", "\u00b3")),
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


def resolve_garden_root(name: str, root_dir: str | None) -> Path:
    """Resolve the Garden root directory."""
    if root_dir:
        return Path(root_dir).expanduser().resolve()
    return (DEFAULT_GARDENS_ROOT / slugify_name(name)).resolve()


def to_posix_relative(path: Path, root: Path) -> str:
    """Return a stable POSIX-style path relative to a root."""
    return path.resolve().relative_to(root.resolve()).as_posix()
