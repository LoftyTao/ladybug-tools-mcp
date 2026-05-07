"""Create Honeybee Door MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.creation import create_honeybee_door as service


def register(mcp: FastMCP) -> None:
    """Register the create_honeybee_door tool."""

    @mcp.tool(
        name="create_honeybee_door",
        description="Create a Honeybee Door on a host Honeybee Face typed target. For an ordinary rectangular door, omit geometry and pass door_width, door_height, and sill_height; the service will place it inside the host wall and avoid existing apertures or doors when possible. For a shared interior Surface wall between adjacent rooms, this creates the paired adjacent Door automatically and preserves Honeybee Surface adjacency. Requires garden_root, identifier, and host_target from search_honeybee_model_objects matches[i].target or a prior create_honeybee_face target; pass geometry only for explicit custom Face3D geometry. The parameter names are exactly geometry and host_target, not Face3D and not host_face. Unique full tool/search responses can be auto-unwrapped, but never pass arguments null or {}.",
        tags={
            "honeybee-core",
            "garden-mode",
            "door",
            "interior-door",
            "adjacency",
            "geometry",
            "write",
            "safe",
        },
        timeout=20,
    )
    def create_honeybee_door(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        identifier: Annotated[
            str, Field(description="Required Honeybee door identifier.")
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description="Required Honeybee face typed target dict from nested target search_honeybee_model_objects matches[i].target or a prior create_honeybee_face result target; parameter name is host_target, not host_face. Use a Surface boundary wall face to create an interior door between adjacent rooms; the adjacent paired door is created automatically. A unique full tool response can be auto-unwrapped, but ambiguous responses, room targets, and identifier strings are rejected."
            ),
        ],
        geometry: Annotated[
            dict[str, Any] | None,
            Field(
                description="Required Ladybug Geometry Face3D dict fully inside the host face; for example {'type':'Face3D','boundary':[[x,y,z],...]}. Boundary points may also be {'x':0,'y':0,'z':0} Point3D dicts. Keep door edges inset from the host face boundary by at least model tolerance; for a floor-touching door use a tiny positive sill such as z=0.01 instead of putting the lower edge exactly on the parent wall edge. Omit plane unless using exact Ladybug Plane keys n, o, and x. Pass this inline geometry dict directly; no separate Point3D tool and no separate Face3D tool are needed. A top-level boundary shorthand is accepted only as an Agent recovery alias. Parameter name is geometry, not Face3D; not Rhino geometry."
            ),
        ] = None,
        boundary: Annotated[
            list[list[float]] | None,
            Field(
                description="Optional Agent recovery shorthand for geometry.boundary. Prefer geometry={'type':'Face3D','boundary':[[x,y,z],...]}; do not use both geometry and boundary."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict. Defaults to the Garden base model."
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
        is_operable: Annotated[
            bool | None,
            Field(
                description="Ignored Agent recovery alias sometimes copied from apertures. Doors do not use is_operable; use is_glass for glass doors."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Door."""
        if geometry is not None and boundary is not None:
            raise ValueError("Pass either geometry or boundary, not both.")
        if geometry is None and boundary is not None:
            geometry = {"type": "Face3D", "boundary": boundary}
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
