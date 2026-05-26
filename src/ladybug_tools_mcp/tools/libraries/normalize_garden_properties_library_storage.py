"""Normalize Garden Properties Library storage MCP tool."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from garden.libraries.properties import (
    normalize_garden_properties_library_storage as service,
)


def register(mcp: FastMCP) -> None:
    'Register the library_normalize_garden_properties_storage tool.'

    @mcp.tool(
        name="normalize_garden_properties_storage",
        description=(
            "Rewrite legacy Garden Properties Library records that stored MCP "
            "wrapper metadata beside object_dict into native Honeybee Energy or "
            "Honeybee Radiance SDK JSON files. Use this one-time maintenance "
            "migration before reading or handing saved reusable resources to "
            "non-MCP workflows that expect native SDK dictionaries. Returns "
            "normalized, already_native, skipped, summary_view, "
            "persistence_receipt, and report while preserving existing typed "
            "targets and index entries. It is not a generic JSON converter, "
            "standards-library importer, or reindex tool."
        ),
        tags={
            "energy",
            "library",
            "maintenance",
            "properties",
            "radiance",
        },
        timeout=20,
    )
    def normalize_garden_properties_library_storage(
        garden_root: Annotated[
            str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root'].")
        ],
        domain: Annotated[
            str | None,
            Field(
                description=(
                    "Optional domain filter for the Garden Properties Library: "
                    "honeybee_energy or honeybee_radiance. Omit for all supported "
                    "domains."
                )
            ),
        ] = None,
        object_family: Annotated[
            str | None,
            Field(
                description=(
                    "Optional object family filter such as schedule, "
                    "construction_set, modifier, or luminaire. Omit for all "
                    "supported saved families in the selected domain."
                )
            ),
        ] = None,
        dry_run: Annotated[
            bool,
            Field(
                description=(
                    "When true, report which legacy wrapped Garden Properties "
                    "Library files would be rewritten without changing any files."
                )
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
