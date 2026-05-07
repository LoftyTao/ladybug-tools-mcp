"""Create Honeybee Room MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.creation import create_honeybee_room as service


def register(mcp: FastMCP) -> None:
    """Register the create_honeybee_room tool."""

    @mcp.tool(
        name="create_honeybee_room",
        description="Create a Honeybee Room in an existing Garden Honeybee model from either a Honeybee Face list, a Ladybug Geometry Polyface3D envelope, or custom box dimensions. For simple boxes, use exact arguments x_dim, y_dim, height, and optional origin; do not use boxDimensions, x/y/z, width/depth, or geometry. Call create_honeybee_model first or ensure the Garden has a base model; create_honeybee_room auto-attaches the room to the Garden base model. There is no host_target argument: do not pass host_target, and do not add the returned room target with edit_honeybee_model.add_objects. Returns target, object_target, model_target, and room_target for downstream edit/search calls. Requires garden_root, identifier, and exactly one geometry mode; do not pass arguments null or {}.",
        tags={"honeybee-core", "garden-mode", "model", "room", "write", "safe"},
        timeout=20,
    )
    def create_honeybee_room(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
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
                description="Optional Ladybug Geometry Polyface3D dictionary for the room envelope, for example Polyface3D.from_box(...).to_dict(). Must provide exactly one geometry mode."
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
                description="Optional Honeybee model target dict. Defaults to the Garden base model. This is not host_target; no host_target is supported because create_honeybee_room auto-attaches to the selected model."
            ),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(description="Agent compatibility alias for model_target when a model target is provided. Room creation does not use host objects."),
        ] = None,
        add_shades: Annotated[
            bool | None,
            Field(description="Ignored Agent compatibility hint. Create shades after the room with create_honeybee_shades_by_parameters or create_honeybee_shade."),
        ] = None,
        shade_distance: Annotated[
            float | None,
            Field(description="Ignored Agent compatibility hint paired with add_shades."),
        ] = None,
        return_object_dict: Annotated[
            bool | None,
            Field(description="Compatibility hint accepted for compact Agent workflows. Room creation returns compact targets regardless."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Room."""
        _ = (add_shades, shade_distance, return_object_dict)
        if model_target is None and isinstance(host_target, dict):
            model_target = host_target
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
