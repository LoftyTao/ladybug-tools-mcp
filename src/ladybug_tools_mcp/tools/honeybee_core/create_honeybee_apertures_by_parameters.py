"""Create Honeybee Apertures By Parameters MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.creation import (
    create_honeybee_apertures_by_parameters as service,
)


def register(mcp: FastMCP) -> None:
    'Register the honeybee_create_apertures_by_parameters tool.'

    @mcp.tool(
        name="create_apertures_by_parameters",
        description='Create Honeybee Apertures, windows, rectangular windows, glazed openings, glazing ratio, window-to-wall ratio, or WWR openings on a host exterior wall Face typed target by ratio or by width and height. This is the preferred tool for requests like add windows by WWR, set window-to-wall ratio to 0.3, add rectangular windows, or apply glazing percentage; use honeybee_create_aperture only for explicit Face3D geometry. Prefer a face match where face_type is Wall and boundary_condition is Outdoors. If the host already has apertures, it returns existing aperture targets with created_count=0 instead of duplicating windows. Requires garden_root, host_target, and mode-specific parameters. Returns target, aperture_target, targets, summary_view, persistence_receipt, and report.',
        tags={
            "aperture",
            "author",
            "face",
            "geometry",
            "honeybee",
            "window",
            "wwr",
        },
        timeout=20,
    )
    def create_honeybee_apertures_by_parameters(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee face typed target dict from nested target honeybee_search_model_objects matches[i].target or a prior create result target; choose a Wall/Outdoors face for exterior windows. Full responses, room targets, floor/ground faces, and identifier strings are rejected.'
            ),
        ],
        generation_mode: Annotated[
            str | None,
            Field(
                description="Generation mode: by_ratio or by_width_height. by_ratio requires ratio; by_width_height requires aperture_width and aperture_height."
            ),
        ] = "by_ratio",
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually honeybee_create_model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
        ratio: Annotated[
            float | None,
            Field(
                description="Required for by_ratio mode: aperture-to-face area ratio between 0 and 1, for example 0.3."
            ),
        ] = None,
        aperture_width: Annotated[
            float | None,
            Field(
                description="Required for by_width_height mode: single aperture width in model units."
            ),
        ] = None,
        aperture_height: Annotated[
            float | None,
            Field(
                description="Required for by_width_height mode: single aperture height in model units."
            ),
        ] = None,
        sill_height: Annotated[
            float,
            Field(description="Sill height for by_width_height mode in model units."),
        ] = 1.0,
        aperture_identifier: Annotated[
            str | None,
            Field(
                description="Optional aperture identifier for by_width_height mode. Defaults to SDK naming."
            ),
        ] = None,
        identifier_prefix: Annotated[
            str | None,
            Field(
                description="Optional Agent-friendly prefix for created aperture identifiers, especially when ratio mode creates SDK-named windows."
            ),
        ] = None,
        tolerance: Annotated[
            float, Field(description="Geometry tolerance used by by_ratio mode.")
        ] = 0.01,
        rect_split: Annotated[
            bool,
            Field(
                description="Whether by_ratio should split apertures into rectangles when needed."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create Honeybee Apertures on a host Face by ratio or width/height parameters."""
        return service(
            garden_root=garden_root,
            host_target=host_target,
            generation_mode=generation_mode,
            model_target=model_target,
            ratio=ratio,
            aperture_width=aperture_width,
            aperture_height=aperture_height,
            sill_height=sill_height,
            aperture_identifier=aperture_identifier,
            identifier_prefix=identifier_prefix,
            tolerance=tolerance,
            rect_split=rect_split,
        )
