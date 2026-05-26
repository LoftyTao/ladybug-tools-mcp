"""Search Honeybee Model Objects MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.search import (
    search_honeybee_model_objects as service,
)


def register(mcp: FastMCP) -> None:
    'Register the honeybee_search_model_objects tool.'

    @mcp.tool(
        name="search_model_objects",
        description="Search Honeybee Room, Face, Aperture/window, Door, and Shade objects in the Garden base model or an explicit model_target. Use object_type plus identifier, query, room_identifier, face_identifier, face_type, boundary_condition, or children_scope to narrow results; for exterior wall/window workflows search faces with face_type=Wall and boundary_condition=Outdoors, then search children under the face. Returns matches with nested target dicts, compact child_counts, geometry summaries, limited room/shade energy_properties, summary_view, and a top-level target only when there is one match. Pass matches[i].target to create/edit/remove tools. This is not for Energy library resources or Radiance SensorGrids/Views.",
        tags={
            "aperture",
            "children",
            "door",
            "face",
            "honeybee",
            "model",
            "room",
            "search",
            "shade",
            "target",
            "wall",
            "window",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_honeybee_model_objects(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually honeybee_create_model['target']; defaults to the Garden base Honeybee Model; do not pass model_identifier or a full model body."
            ),
        ] = None,
        object_type: Annotated[
            str,
            Field(
                description="Object type to return: all, room, face, aperture, door, or shade. Use room for rooms, face for walls, aperture for windows, door for doors, and shade for shades."
            ),
        ] = "all",
        identifier: Annotated[
            str | None,
            Field(
                description="Optional exact Honeybee object identifier or display name filter, such as office_west or office_west_Front."
            ),
        ] = None,
        room_identifier: Annotated[
            str | None,
            Field(
                description="Optional parent room identifier filter for faces, apertures, doors, or shades, such as office_west."
            ),
        ] = None,
        face_identifier: Annotated[
            str | None,
            Field(
                description="Optional parent face identifier filter for apertures, doors, or shades, such as office_west_Front. For object_type=face, it filters the face identifier itself."
            ),
        ] = None,
        query: Annotated[
            str | None,
            Field(
                description="Optional identifier/display-name substring query, such as Tiny_House_Office or Front exterior wall."
            ),
        ] = None,
        face_type: Annotated[
            str | None,
            Field(
                description="Optional face type filter for face searches, for example Wall, Floor, RoofCeiling, or AirBoundary."
            ),
        ] = None,
        boundary_condition: Annotated[
            str | dict[str, Any] | None,
            Field(
                description="Optional boundary condition filter for face/aperture/door searches, for example Outdoors or {type: Outdoors}."
            ),
        ] = None,
        children_scope: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional typed Honeybee parent target dict used to return only child objects under a room, face, aperture, or door. Use this before retrying aperture/shade creation so Agents can see existing children on the host. Do not pass true, false, or parent_target."
            ),
        ] = None,
        limit: Annotated[
            int | None,
            Field(description="Optional maximum number of object matches to return."),
        ] = None,
    ) -> dict[str, Any]:
        """Search Honeybee objects and return typed targets."""
        object_type = object_type.strip().lower().replace("-", "_").replace(" ", "_")
        return service(
            garden_root=garden_root,
            model_target=model_target,
            object_type=object_type,
            identifier=identifier,
            room_identifier=room_identifier,
            face_identifier=face_identifier,
            query=query,
            face_type=face_type,
            boundary_condition=boundary_condition,
            children_scope=children_scope,
            limit=limit,
        )
