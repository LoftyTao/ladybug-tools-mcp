"""Create Honeybee Shade MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.creation import create_honeybee_shade as service


def register(mcp: FastMCP) -> None:
    'Register the honeybee_create_shade tool.'

    @mcp.tool(
        name="create_shade",
        description='Create an orphaned Honeybee Shade or attach it to a Room, Face, Aperture, or Door typed target from explicit Face3D geometry. This is the low-level explicit-geometry route for context shades, hosted shades, custom sunshades, or overhangs that already have Face3D geometry. For parametric louvers or aperture extruded borders, use honeybee_create_shades_by_parameters instead. Requires garden_root, unique identifier, and geometry; hosted shades also need host_target from honeybee_search_model_objects matches[i].target or a prior result target. The parameter names are geometry and host_target, not Face3D and not host_face. Returns target, object_target, model_target, shade_target, summary_view, persistence_receipt, and report.',
        tags={
            "author",
            "geometry",
            "honeybee",
            "hosted",
            "shade",
        },
        timeout=20,
    )
    def create_honeybee_shade(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        identifier: Annotated[
            str,
            Field(
                description='Required unique Honeybee shade identifier. If it already exists, use honeybee_search_model_objects to reuse/remove it or choose a new identifier.'
            ),
        ],
        geometry: Annotated[
            dict[str, Any],
            Field(
                description="Required Ladybug Geometry Face3D dict, for example {'type':'Face3D','boundary':[[x,y,z],...]}; boundary points may also be {'x':0,'y':0,'z':0} Point3D dicts. Omit plane unless using exact Ladybug Plane keys n, o, and x. Pass this inline geometry dict directly; no separate Point3D tool and no separate Face3D tool are needed. Parameter name is geometry, not Face3D; not Rhino geometry."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually honeybee_create_model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Optional Honeybee room/face/aperture/door typed target dict from nested target honeybee_search_model_objects matches[i].target or a prior create result target; parameter name is host_target, not host_face. Full responses are rejected; omit for orphaned shade.'
            ),
        ] = None,
        attach_side: Annotated[
            str,
            Field(
                description="Attach side for hosted shades: outdoor or indoor. Natural exterior words like top, exterior, or outside normalize to outdoor."
            ),
        ] = "outdoor",
        is_detached: Annotated[
            bool, Field(description="Whether the shade is detached.")
        ] = False,
    ) -> dict[str, Any]:
        """Create a Honeybee Shade."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            geometry=geometry,
            model_target=model_target,
            host_target=host_target,
            attach_side=attach_side,
            is_detached=is_detached,
        )
