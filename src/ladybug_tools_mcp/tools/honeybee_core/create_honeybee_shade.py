"""Create Honeybee Shade MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.creation import create_honeybee_shade as service


def register(mcp: FastMCP) -> None:
    """Register the create_honeybee_shade tool."""

    @mcp.tool(
        name="create_honeybee_shade",
        description="Create an orphaned Honeybee Shade or attach it to a Room, Face, Aperture, or Door typed target from explicit Face3D geometry. This is not the default louver, overhang, sunshade, or window shade tool; for natural parametric shade requests use create_honeybee_shades_by_parameters instead. Requires garden_root, unique identifier, and geometry; hosted shades also need host_target from search_honeybee_model_objects matches[i].target or a prior result target. If the identifier already exists, search and reuse the existing shade target, remove it first, or choose a new identifier. The parameter names are exactly geometry and host_target, not Face3D and not host_face. Never pass arguments null or {}.",
        tags={
            "honeybee-core",
            "garden-mode",
            "shade",
            "geometry",
            "explicit-geometry",
            "face3d",
            "custom-shade-geometry",
            "write",
            "safe",
        },
        timeout=20,
    )
    def create_honeybee_shade(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        identifier: Annotated[
            str,
            Field(
                description="Required unique Honeybee shade identifier. If it already exists, use search_honeybee_model_objects to reuse/remove it or choose a new identifier."
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
                description="Optional Honeybee model target dict. Defaults to the Garden base model."
            ),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee room/face/aperture/door typed target dict from nested target search_honeybee_model_objects matches[i].target or a prior create result target; parameter name is host_target, not host_face. Full responses are rejected; omit for orphaned shade."
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
