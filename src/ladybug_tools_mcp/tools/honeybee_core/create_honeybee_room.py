"""Create Honeybee Room MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.creation import create_honeybee_room as service


def register(mcp: FastMCP) -> None:
    'Register the honeybee_create_room tool.'

    @mcp.tool(
        name="create_room",
        description='Create a Honeybee Room, meaning a room/space envelope in a Garden Honeybee Model, from either a Honeybee Face list, a Ladybug Geometry Polyface3D envelope, or custom box dimensions. A Honeybee Room can later map partly to EnergyPlus zone concepts, but this tool does not create an Ironbug ThermalZone, assign ProgramType, assign ConstructionSet, set setpoints, or add HVAC. For simple boxes, use x_dim, y_dim, height, and optional origin. There is no host_target argument; the room is a top-level model object and auto-attaches to the selected model. Returns target, object_target, model_target, and room_target. Requires garden_root, identifier, and exactly one geometry mode; do not pass arguments null or {}.',
        tags={
            "author",
            "geometry",
            "honeybee",
            "room",
        },
        timeout=20,
    )
    def create_honeybee_room(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        identifier: Annotated[
            str, Field(description="Required Honeybee room identifier.")
        ],
        faces: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Optional list of complete Honeybee Face dictionaries for the room. Must provide exactly one geometry mode; not typed targets."
            ),
        ] = None,
        room_geometry: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Ladybug Geometry Polyface3D dictionary for the room envelope, for example Polyface3D.from_box(...).to_dict() with vertices and face_indices. Must provide exactly one geometry mode."
            ),
        ] = None,
        x_dim: Annotated[
            float | None,
            Field(
                description="Optional custom box width. Use with y_dim and height as one geometry mode."
            ),
        ] = None,
        y_dim: Annotated[
            float | None,
            Field(
                description="Optional custom box depth. Use with x_dim and height as one geometry mode."
            ),
        ] = None,
        height: Annotated[
            float | None,
            Field(
                description="Optional custom box height. Use with x_dim and y_dim as one geometry mode."
            ),
        ] = None,
        origin: Annotated[
            list[float] | dict[str, Any] | None,
            Field(
                description="Optional box origin as [x, y, z] or {x, y, z}. Defaults to [0, 0, 0]."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually honeybee_create_model['target']; defaults to the Garden base Honeybee Model. This is not host_target; no host_target is supported because honeybee_create_room auto-attaches to the selected model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Room."""
        origin_value = origin
        if isinstance(origin_value, dict):
            origin_value = [
                float(origin_value.get("x", 0)),
                float(origin_value.get("y", 0)),
                float(origin_value.get("z", 0)),
            ]
        return service(
            garden_root=garden_root,
            identifier=identifier,
            faces=faces,
            room_geometry=room_geometry,
            x_dim=x_dim,
            y_dim=y_dim,
            height=height,
            origin=origin_value,
            model_target=model_target,
        )
