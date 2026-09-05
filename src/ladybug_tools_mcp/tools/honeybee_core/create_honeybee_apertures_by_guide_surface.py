"""Create Honeybee Apertures from Ladybug Geometry guide surfaces."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the HB_create_apertures_by_guide_surface tool."""

    @mcp.tool(
        name="HB_create_apertures_by_guide_surface",
        description=(
            "Create Honeybee Apertures on a host Face typed target from one or "
            "more Ladybug Geometry Face3D guide surfaces. Guide surfaces must "
            "be coplanar with and fully inside the host Face within tolerance; "
            "non-coplanar, outside, overlapping, invalid, and unprojectable "
            "guides are skipped with reasons. Existing equivalent Apertures "
            "are reused without duplication. Requires garden_root, "
            "host_target, and guide_surfaces. Returns target, targets, "
            "created_targets, reused_targets, summary_view, "
            "persistence_receipt, and report."
        ),
        tags={
            "aperture",
            "author",
            "face",
            "geometry",
            "guide-surface",
            "honeybee",
            "window",
        },
        timeout=20,
    )
    def create_honeybee_apertures_by_guide_surface(
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
                    "HB_search_model_objects matches[i].target."
                )
            ),
        ],
        guide_surfaces: Annotated[
            list[dict[str, Any]],
            Field(
                description=(
                    "Required list of Ladybug Geometry Face3D dictionaries used "
                    "as aperture guide surfaces."
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
            Field(description="Geometry tolerance for coplanarity and containment."),
        ] = 0.01,
        identifier_prefix: Annotated[
            str | None,
            Field(description="Optional prefix for generated aperture identifiers."),
        ] = None,
    ) -> dict[str, Any]:
        """Create Honeybee Apertures from guide surfaces."""
        from garden.honeybee_core.guide_openings import (
            create_honeybee_apertures_by_guide_surface as service,
        )

        return service(
            garden_root=garden_root,
            host_target=host_target,
            guide_surfaces=guide_surfaces,
            model_target=model_target,
            tolerance=tolerance,
            identifier_prefix=identifier_prefix,
        )
