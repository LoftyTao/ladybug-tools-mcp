"""Normalize Garden Properties Library storage MCP tool."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from garden.libraries.properties import (
    normalize_garden_properties_library_storage as service,
)


def register(mcp: FastMCP) -> None:
    """Register the normalize_garden_properties_library_storage tool."""

    @mcp.tool(
        name="normalize_garden_properties_library_storage",
        description="Rewrite Garden Properties Library files that store MCP wrapper metadata beside object_dict into native SDK dict JSON files. Keep using the same targets, index entries, and receipts. Use this maintenance tool when reusable resources need native SDK JSON files for non-MCP handoff.",
        tags={
            "garden",
            "properties",
            "library",
            "save",
            "write",
            "energy",
            "radiance",
            "maintenance",
        },
        timeout=20,
    )
    def normalize_garden_properties_library_storage(
        garden_root: Annotated[
            str, Field(description="Garden root directory containing garden.json.")
        ],
        domain: Annotated[
            str | None,
            Field(
                description="Optional domain filter: honeybee_energy or honeybee_radiance. Omit for all supported domains."
            ),
        ] = None,
        object_family: Annotated[
            str | None,
            Field(
                description="Optional object family filter such as schedule, construction_set, modifier, or luminaire. Omit for all supported families."
            ),
        ] = None,
        dry_run: Annotated[
            bool,
            Field(
                description="When true, report which wrapped files would be rewritten without changing any files."
            ),
        ] = False,
    ) -> dict:
        """Normalize wrapped Garden Properties Library storage files."""
        return service(
            garden_root=garden_root,
            domain=domain,
            object_family=object_family,
            dry_run=dry_run,
        )
