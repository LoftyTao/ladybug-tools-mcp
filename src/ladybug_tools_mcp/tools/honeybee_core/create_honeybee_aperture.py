"""Create Honeybee Aperture MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.creation import create_honeybee_aperture as service


def register(mcp: FastMCP) -> None:
    """Register the create_honeybee_aperture tool."""

    @mcp.tool(
        name="create_honeybee_aperture",
        description="Create a Honeybee Aperture in a Garden Honeybee model on a host Honeybee Face typed target from explicit Face3D geometry. This is not the default window, window-to-wall ratio, WWR, glazing ratio, or rectangular window tool; for natural parametric window requests use create_honeybee_apertures_by_parameters instead. Requires garden_root, identifier, geometry, and host_target from search_honeybee_model_objects matches[i].target or a prior create_honeybee_face target; the parameter names are exactly geometry and host_target, not Face3D and not host_face. Never pass arguments null or {}.",
        tags={
            "honeybee-core",
            "garden-mode",
            "model",
            "aperture",
            "create-aperture",
            "geometry",
            "explicit-geometry",
            "face3d",
            "custom-window-geometry",
            "write",
            "safe",
        },
        timeout=20,
    )
    def create_honeybee_aperture(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        identifier: Annotated[
            str, Field(description="Required Honeybee aperture identifier.")
        ],
        geometry: Annotated[
            dict[str, Any],
            Field(
                description="Required Ladybug Geometry Face3D dict fully inside the host face; for example {'type':'Face3D','boundary':[[x,y,z],...]}. Boundary points may also be {'x':0,'y':0,'z':0} Point3D dicts. Keep sub-face edges inset from the host face boundary by at least model tolerance; do not place aperture edges exactly on the parent wall edge. Omit plane unless using exact Ladybug Plane keys n, o, and x. Pass this inline geometry dict directly; no separate Point3D tool and no separate Face3D tool are needed. Parameter name is geometry, not Face3D; not Rhino geometry."
            ),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description="Required Honeybee face typed target dict from nested target search_honeybee_model_objects matches[i].target or a prior create_honeybee_face result target; parameter name is host_target, not host_face. Full responses, room targets, and identifier strings are rejected."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict. Defaults to the Garden base model."
            ),
        ] = None,
        is_operable: Annotated[
            bool, Field(description="Whether the aperture is operable.")
        ] = False,
    ) -> dict[str, Any]:
        """Create a Honeybee Aperture."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            geometry=geometry,
            host_target=host_target,
            model_target=model_target,
            is_operable=is_operable,
        )
