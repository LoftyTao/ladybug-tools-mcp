"""Garden path helpers."""

from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GARDENS_ROOT = PROJECT_ROOT / "gardens"


def slugify_name(value: str) -> str:
    """Convert a user label into a conservative filesystem slug."""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip()).strip("_").lower()
    return slug or "garden"


def resolve_garden_root(name: str, root_dir: str | None) -> Path:
    """Resolve the Garden root directory."""
    if root_dir:
        return Path(root_dir).expanduser().resolve()
    return (DEFAULT_GARDENS_ROOT / slugify_name(name)).resolve()


def to_posix_relative(path: Path, root: Path) -> str:
    """Return a stable POSIX-style path relative to a root."""
    return path.resolve().relative_to(root.resolve()).as_posix()
