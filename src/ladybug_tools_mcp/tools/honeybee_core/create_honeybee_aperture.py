"""Create Honeybee Aperture MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.creation import create_honeybee_aperture as service


def register(mcp: FastMCP) -> None:
    'Register the honeybee_create_aperture tool.'

    @mcp.tool(
        name="create_aperture",
        description='Create a Honeybee Aperture, commonly a window/opening sub-face, on a host Honeybee Face typed target from explicit Face3D geometry. This is the low-level explicit-geometry path, not the window-to-wall ratio, WWR, glazing ratio, or rectangular window generator; use honeybee_create_apertures_by_parameters for natural parametric window requests. Requires garden_root, identifier, geometry, and host_target from honeybee_search_model_objects matches[i].target or a prior honeybee_create_face target. The parameter names are exactly geometry and host_target, not Face3D and not host_face. Returns target, object_target, model_target, aperture_target, summary_view, persistence_receipt, and report.',
        tags={
            "aperture",
            "author",
            "geometry",
            "honeybee",
            "window",
        },
        timeout=20,
    )
    def create_honeybee_aperture(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
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
                description='Required Honeybee face typed target dict from nested target honeybee_search_model_objects matches[i].target or a prior honeybee_create_face result target; parameter name is host_target, not host_face. Full responses, room targets, and identifier strings are rejected.'
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually honeybee_create_model['target']; defaults to the Garden base Honeybee Model."
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
