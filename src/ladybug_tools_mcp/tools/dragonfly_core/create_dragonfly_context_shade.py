"""Create Dragonfly ContextShade MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.creation import create_dragonfly_context_shade as service


def register(mcp: FastMCP) -> None:
    """Register the create_dragonfly_context_shade tool."""

    @mcp.tool(
        name="create_dragonfly_context_shade",
        description=(
            "Create a Dragonfly ContextShade in a Garden from one or more 3D "
            "shade faces, save it into the Dragonfly model, and return a "
            "context_shade target for search, UWG vegetation properties, and "
            "model summaries. Use this for surrounding buildings, tree canopy, "
            "or other detached urban context geometry."
        ),
        tags={
            "dragonfly-core",
            "garden-mode",
            "context-shade",
            "urban-context",
            "create",
            "write",
            "safe",
        },
        timeout=20,
    )
    def create_dragonfly_context_shade(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path containing garden.json."),
        ],
        identifier: Annotated[
            str,
            Field(description="Required Dragonfly ContextShade identifier."),
        ],
        geometry: Annotated[
            Any,
            Field(
                description=(
                    "Required ContextShade face geometry as a list of 3D face "
                    "boundaries: [[[x, y, z], ...], ...], or Face3D-style "
                    "dicts with vertices/boundary. Each face needs at least "
                    "three points."
                )
            ),
        ] = None,
        vertices: Annotated[
            Any,
            Field(
                description=(
                    "Optional natural footprint/boundary vertices. Pass 3D vertices "
                    "for one shade face, or 2D vertices with height to extrude a "
                    "simple urban-context mass."
                )
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly model target. Defaults to base Dragonfly model."
                )
            ),
        ] = None,
        is_detached: Annotated[
            bool,
            Field(description="Whether this ContextShade is detached from buildings."),
        ] = True,
        x_dim: Annotated[
            float | None,
            Field(description="Optional rectangular context footprint width."),
        ] = None,
        y_dim: Annotated[
            float | None,
            Field(description="Optional rectangular context footprint depth."),
        ] = None,
        height: Annotated[
            float | None,
            Field(description="Optional rectangular context height."),
        ] = None,
        origin: Annotated[
            list[float] | None,
            Field(description="Optional rectangular context origin [x, y] or [x, y, z]."),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing ContextShade display name."),
        ] = None,
        context_shade_type: Annotated[
            str | None,
            Field(description="Optional natural context type, such as tree or building."),
        ] = None,
        is_vegetation: Annotated[
            bool | None,
            Field(description="Optional UWG vegetation flag when UWG properties are available."),
        ] = None,
        cen_pt: Annotated[
            list[float] | None,
            Field(description="Optional natural center point [x, y] or [x, y, z]."),
        ] = None,
        radius: Annotated[
            float | None,
            Field(description="Optional natural radius used with cen_pt for tree/building shades."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly ContextShade."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            geometry=geometry,
            vertices=vertices,
            model_target=model_target,
            is_detached=is_detached,
            x_dim=x_dim,
            y_dim=y_dim,
            height=height,
            origin=origin,
            display_name=display_name,
            context_shade_type=context_shade_type,
            is_vegetation=is_vegetation,
            cen_pt=cen_pt,
            radius=radius,
        )
