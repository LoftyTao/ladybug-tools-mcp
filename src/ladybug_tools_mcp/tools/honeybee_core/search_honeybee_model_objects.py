"""Search Honeybee Model Objects MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.search import (
    search_honeybee_model_objects as service,
)


def register(mcp: FastMCP) -> None:
    """Register the search_honeybee_model_objects tool."""

    @mcp.tool(
        name="search_honeybee_model_objects",
        description="Search and find rooms, walls, windows, doors, shades, and other Honeybee Core geometry objects in the Garden base model or an explicit model target. search_honeybee_model_objects is the only Honeybee object search tool: use it with object_type=room, object_type=face, object_type=aperture, object_type=door, or object_type=shade; not search_honeybee_rooms, not search_honeybee_apertures, and not search_honeybee_doors. Do not use this for Energy program_type, construction_set, schedule, construction, material, or hvac. Radiance SensorGrids and Views are Garden artifacts; prefer search_radiance_sensor_grids. Use garden_root alone for the active Garden base model; do not pass model_identifier. Use identifier for an exact object id such as office_west; use room_identifier and face_identifier as parent filters. Use query for natural substring terms. Returns matches with nested target dicts for create/edit/remove/operate follow-up tools; pass only matches[i].target, or use the top-level target when exactly one match is found. children_scope is an optional typed parent target dict from a prior match; not true, not a boolean, and not parent_target. Room matches include compact energy_properties so Agents can confirm room program/load/setpoint/HVAC assignments and zone_ventilation_fans without inventing get_honeybee_room or full-body reads. Shade matches include compact energy_properties with pv_properties identifier strings so Agents can confirm shade PV assignments. There is no include_body parameter; use these compact summaries instead. Room, face, aperture, and door matches include compact child_counts so Agents can see existing faces/apertures/doors/shades without separate full-model searches. Face, aperture, door, and shade matches include compact Face3D geometry with boundary/vertices, area, and normal so Agents can position explicit sub-face geometry without inventing get_honeybee_face_geometry or visualization tools. Face matches include face_type and boundary_condition so Agents can choose exterior Wall faces for windows/shades instead of floors/roofs. For exterior wall windows, call object_type=face with face_type=Wall and boundary_condition=Outdoors. For natural language room/wall/window tasks, search room first, then search face or aperture; room results are not wall targets.",
        tags={
            "honeybee-core",
            "garden-mode",
            "model",
            "search",
            "find-rooms",
            "walls",
            "windows",
            "doors",
            "shades",
            "read",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_honeybee_model_objects(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict. Defaults to the Garden base model; do not pass model_identifier or a full model body."
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
