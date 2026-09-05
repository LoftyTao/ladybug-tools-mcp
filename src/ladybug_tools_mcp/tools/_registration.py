"""Convention-based registration for tool modules."""

from __future__ import annotations

from collections.abc import Iterable
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def iter_tool_module_names(
    package_name: str,
    *,
    exclude: Iterable[str] = (),
) -> tuple[str, ...]:
    """Return sorted public Python modules in a tool family package."""

    package = import_module(package_name)
    package_file = getattr(package, "__file__", None)
    if package_file is None:
        raise ValueError(f"Tool family package has no file: {package_name}")
    excluded = set(exclude)
    return tuple(
        sorted(
            path.stem
            for path in Path(package_file).parent.glob("*.py")
            if path.stem != "__init__" and path.stem not in excluded
        )
    )


def register_discovered_tools(
    mcp: FastMCP,
    package_name: str,
    *,
    exclude: Iterable[str] = (),
) -> None:
    """Import and register each convention-based tool module in order."""

    for module_name in iter_tool_module_names(package_name, exclude=exclude):
        import_module(f"{package_name}.{module_name}").register(mcp)
