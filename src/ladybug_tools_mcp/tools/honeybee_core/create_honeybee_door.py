"""Create Honeybee Door MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    'Register the HB_create_door tool.'

    @mcp.tool(
        name="HB_create_door",
        description=(
            'Create a Honeybee Door on a host Honeybee Face typed target. For an ordinary '
            'rectangular door, omit geometry and pass door_width, door_height, and sill_height; '
            'the service places it inside the host wall and avoids existing apertures or doors '
            'when possible. For a shared interior Surface boundary wall between adjacent rooms, '
            'this creates the paired adjacent Door automatically and preserves Honeybee Surface '
            'adjacency. Pass geometry only for explicit custom Face3D geometry. Returns target, '
            'object_target, model_target, door_target, and for paired interior doors also '
            'targets, adjacent_target, and summary_view.is_interior_pair.'
        ),
        tags={
            "author",
            "door",
            "geometry",
            "honeybee",
            "hosted",
            "surface",
        },
        timeout=20,
    )
    def create_honeybee_door(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_create['garden_root']."
            ),
        ],
        identifier: Annotated[
            str, Field(description="Required Honeybee door identifier.")
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Required Honeybee face typed target dict from HB_search_model_objects '
                    'matches[i].target or HB_create_face. Use a Surface boundary wall face to '
                    'create a paired interior door between adjacent rooms.'
                )
            ),
        ],
        geometry: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Required Ladybug Geometry Face3D dict fully inside the host face; for '
                    "example {'type':'Face3D','boundary':[[x,y,z],...]}. Boundary points may also "
                    "be {'x':0,'y':0,'z':0} Point3D dicts. Keep door edges inset from the host "
                    'face boundary by at least model tolerance (for a floor-touching door, use a '
                    'small positive sill such as z=0.01). Omit plane unless providing Ladybug '
                    'Plane keys n, o, and x.'
                )
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_create_model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
        door_width: Annotated[
            float | None,
            Field(
                description="Optional width for an ordinary rectangular door when geometry is omitted. Defaults to 0.9 meters and avoids existing apertures/doors when possible."
            ),
        ] = None,
        door_height: Annotated[
            float,
            Field(
                description="Optional height for an ordinary rectangular door when geometry is omitted. Defaults to 2.1 meters."
            ),
        ] = 2.1,
        sill_height: Annotated[
            float,
            Field(
                description="Optional bottom offset above the host wall base for an ordinary rectangular door when geometry is omitted. A user-style 0.0 floor sill is accepted; the service applies the minimum Honeybee-safe inset needed to keep the generated door inside the parent face."
            ),
        ] = 0.05,
        placement: Annotated[
            str,
            Field(
                description="Optional placement preference for generated rectangular doors: auto, left, right, or center. auto chooses the first free span that does not overlap existing apertures or doors."
            ),
        ] = "auto",
        is_glass: Annotated[
            bool, Field(description="Whether the door is glass.")
        ] = False,
    ) -> dict[str, Any]:
        """Create a Honeybee Door."""
        from garden.honeybee_core.creation import create_honeybee_door as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            geometry=geometry,
            host_target=host_target,
            model_target=model_target,
            is_glass=is_glass,
            door_width=door_width,
            door_height=door_height,
            sill_height=sill_height,
            placement=placement,
        )
