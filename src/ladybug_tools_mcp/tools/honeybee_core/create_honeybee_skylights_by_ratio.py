"""Create Honeybee skylights by ratio MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the HB_create_skylights_by_ratio tool."""

    @mcp.tool(
        name="HB_create_skylights_by_ratio",
        description=(
            "Create or reuse Honeybee skylight Apertures on a RoofCeiling or "
            "Floor Face typed target by an aperture-to-face area ratio. The Face "
            "must have an Outdoors boundary condition. Existing compatible "
            "Apertures are returned without a new write; existing Doors or a "
            "different aperture ratio are rejected because the Honeybee SDK ratio "
            "generator replaces sub-faces. Use HB_create_aperture for explicit "
            "Face3D geometry. Returns target, aperture_target, targets, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={
            "aperture",
            "author",
            "face",
            "floor",
            "honeybee",
            "ratio",
            "roof",
            "skylight",
        },
        timeout=20,
    )
    def create_honeybee_skylights_by_ratio(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_create['garden_root']."
                )
            ),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required Honeybee Face typed target from "
                    "HB_search_model_objects; it must identify a RoofCeiling or "
                    "Floor Face with an Outdoors boundary condition."
                )
            ),
        ],
        ratio: Annotated[
            float,
            Field(
                description=(
                    "Required aperture-to-face area ratio between 0 and 1, for "
                    "example 0.2."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Honeybee model target dict; defaults to the Garden "
                    "base Honeybee Model."
                )
            ),
        ] = None,
        tolerance: Annotated[
            float,
            Field(description="Positive geometry and ratio matching tolerance."),
        ] = 0.01,
        identifier_prefix: Annotated[
            str | None,
            Field(
                description="Optional prefix for generated skylight identifiers."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create or reuse ratio-based skylights on a Honeybee Face."""
        from garden.honeybee_core.creation import (
            create_honeybee_skylights_by_ratio as service,
        )

        return service(
            garden_root=garden_root,
            host_target=host_target,
            ratio=ratio,
            model_target=model_target,
            tolerance=tolerance,
            identifier_prefix=identifier_prefix,
        )
