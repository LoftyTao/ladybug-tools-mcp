"""Search Honeybee Model Objects MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from pathlib import Path
from ladybug_tools_mcp.contracts.report import make_report
from garden.honeybee_core.search import (
    search_honeybee_model_objects as service,
)
from garden.store import (
    get_base_honeybee_model as get_base_honeybee_model_service,
    list_garden_artifacts,
)


def _radiance_object_type(value: str) -> str | None:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "radiance_sensor_grid": "radiance_sensor_grid",
        "sensor_grid": "radiance_sensor_grid",
        "sensorgrid": "radiance_sensor_grid",
        "sensor_grids": "radiance_sensor_grid",
        "sensorgrids": "radiance_sensor_grid",
        "radiance_view": "radiance_view",
        "view": "radiance_view",
        "views": "radiance_view",
        "sky": "radiance_sky_file",
        "skies": "radiance_sky_file",
        "sky_file": "radiance_sky_file",
        "sky_files": "radiance_sky_file",
        "radiance_sky": "radiance_sky_file",
        "radiance_sky_file": "radiance_sky_file",
        "radiance_hdr": "radiance_hdr_image",
        "hdr": "radiance_hdr_image",
        "hdri": "radiance_hdr_image",
        "radiance_image": "radiance_hdr_image",
        "radiance_gif": "radiance_gif_image",
        "gif": "radiance_gif_image",
    }
    return aliases.get(normalized)


def _radiance_artifact_target(
    artifact: dict[str, Any],
    garden_target: dict[str, Any],
    target_type: str,
) -> dict[str, Any]:
    path = str(artifact.get("path") or "")
    return {
        "target_type": target_type,
        "domain": "honeybee_radiance",
        "garden_id": garden_target.get("garden_id"),
        "identifier": str(artifact.get("name") or Path(path).stem),
        "path": path,
    }


def _search_radiance_artifacts(
    *,
    garden_root: str,
    object_type: str,
    identifier: str | None,
    query: str | None,
    limit: int | None,
) -> dict[str, Any]:
    listed = list_garden_artifacts(garden_root=garden_root, artifact_type=object_type)
    garden_target = listed["summary_view"]["garden_target"]
    query_text = (identifier or query or "").strip().lower()
    matches: list[dict[str, Any]] = []
    for artifact in listed["matches"]:
        searchable = " ".join(
            str(value)
            for value in (
                artifact.get("name"),
                artifact.get("path"),
                artifact.get("artifact_type"),
            )
            if value
        ).lower()
        if query_text and query_text not in searchable:
            continue
        target = _radiance_artifact_target(artifact, garden_target, object_type)
        matches.append(
            {
                "target": target,
                "object_type": object_type,
                "identifier": target["identifier"],
                "artifact": artifact,
                "matched_fields": [{"field": "artifact", "value": artifact.get("path")}],
            }
        )
        if limit is not None and len(matches) >= limit:
            break
    result: dict[str, Any] = {
        "matches": matches,
        "summary_view": {
            "garden_target": garden_target,
            "object_type": object_type,
            "count": len(matches),
            "query": query,
            "identifier": identifier,
            "redirected_from": "search_honeybee_model_objects",
            "recommended_tool": (
                "search_radiance_sensor_grids"
                if object_type == "radiance_sensor_grid"
                else "search_radiance_sky_files"
                if object_type == "radiance_sky_file"
                else "list_garden_files"
            ),
        },
        "report": make_report(
            status="ok",
            message=(
                f"Found {len(matches)} {object_type} artifact(s). "
                "Radiance assets are stored as Garden artifacts, not Honeybee Core objects."
            ),
        ),
    }
    if len(matches) == 1:
        result["target"] = matches[0]["target"]
    return result


def register(mcp: FastMCP) -> None:
    """Register the search_honeybee_model_objects tool."""

    @mcp.tool(
        name="search_honeybee_model_objects",
        description="Search and find rooms, walls, windows, doors, shades, and other Honeybee Core geometry objects in the Garden base model or an explicit model target. search_honeybee_model_objects is the only Honeybee object search tool: use it with object_type=room, object_type=face, object_type=aperture, object_type=door, or object_type=shade; not search_honeybee_rooms, not search_honeybee_apertures, and not search_honeybee_doors. Natural aliases like rooms, walls, windows, doors, and shades are accepted and normalized. Do not use this for Energy program_type, construction_set, schedule, construction, material, or hvac. Radiance SensorGrids and Views are Garden artifacts; prefer search_radiance_sensor_grids for object_type=radiance_sensor_grid, but accidental radiance_sensor_grid or radiance_view searches return compact artifact targets instead of failing. Use garden_root alone for the active Garden base model; do not pass model_identifier. Use identifier for an exact object id such as office_west; use room_identifier and face_identifier as parent filters. Use query for natural substring terms. Returns matches with nested target dicts for create/edit/remove/operate follow-up tools; pass only matches[i].target, or use the top-level target when exactly one match is found. Unique full search responses can be auto-unwrapped by compatible create/edit tools. Room matches include compact energy_properties so Agents can confirm room program/load/setpoint/HVAC assignments without inventing get_honeybee_room. Room, face, aperture, and door matches include compact child_counts so Agents can see existing faces/apertures/doors/shades without separate full-model searches. Face, aperture, door, and shade matches include compact Face3D geometry with boundary/vertices, area, and normal so Agents can position explicit sub-face geometry without inventing get_honeybee_face_geometry or visualization tools. Face matches include face_type and boundary_condition so Agents can choose exterior Wall faces for windows/shades instead of floors/roofs. For exterior wall windows, call object_type=face with face_type=Wall and boundary_condition=Outdoors. For natural language room/wall/window tasks, search room first, then search face or aperture; room results are not wall targets.",
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
        target: Annotated[
            dict[str, Any] | None,
            Field(description="Alias for model_target accepted for Agent compatibility when searching within a model target."),
        ] = None,
        object_type: Annotated[
            str,
            Field(
                description="Object type to return: all, room, face, aperture, door, or shade. Natural aliases rooms, walls, windows, doors, and shades are accepted and normalized. Use room for rooms, use face for walls, use aperture for windows, use door for doors, and use shade for shades. In stable calls pass object_type=room, object_type=face, object_type=aperture, object_type=door, or object_type=shade."
            ),
        ] = "all",
        matches_type: Annotated[
            str | None,
            Field(
                description="Optional Agent alias for object_type or face_type. For example matches_type=Wall searches faces with face_type=Wall."
            ),
        ] = None,
        match_type: Annotated[
            str | None,
            Field(
                description="Optional singular Agent alias for matches_type. For example match_type=Wall searches faces with face_type=Wall; match_type=boundary_condition is accepted as a harmless filter hint."
            ),
        ] = None,
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
        search_pattern: Annotated[
            str | None,
            Field(
                description="Optional Agent alias for query, accepted when a model asks for a search pattern."
            ),
        ] = None,
        detail: Annotated[
            str | None,
            Field(
                description="Optional Agent search-detail hint accepted for compatibility with Code Mode search habits. Ignored; this tool always returns compact matches and targets."
            ),
        ] = None,
        domain: Annotated[
            str | None,
            Field(
                description="Ignored Agent compatibility hint for cross-domain searches, such as radiance. This tool always searches Honeybee model objects."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Optional Agent hint accepted to avoid retries. Ignored; search results stay compact and do not return full object dictionaries."
            ),
        ] = False,
        matches_only: Annotated[
            bool | None,
            Field(description="Optional Agent hint accepted for compatibility. Search results already return compact matches."),
        ] = None,
        include_energy_properties: Annotated[
            bool | None,
            Field(
                description="Ignored Agent compatibility hint. Room matches already include compact energy_properties summaries."
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
            dict[str, Any] | str | bool | None,
            Field(
                description="Optional typed Honeybee parent target used to return only child objects under a room, face, aperture, or door. A bare string is accepted as a natural parent identifier shorthand. Boolean true is accepted as a harmless Agent hint; room/face results already include child_counts. Use this before retrying aperture/shade creation so Agents can see existing children on the host."
            ),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional natural parent-target alias for children_scope, accepted when Agents ask to search faces/windows/shades under a host room, face, aperture, or door."
            ),
        ] = None,
        room_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Agent alias for children_scope when searching faces or child objects under a Room target."
            ),
        ] = None,
        limit: Annotated[
            int | None,
            Field(description="Optional maximum number of object matches to return."),
        ] = None,
        matches_limit: Annotated[
            int | None,
            Field(
                description="Optional Agent alias for limit, accepted when a model asks for a maximum number of matches as matches_limit."
            ),
        ] = None,
        matches_filter: Annotated[
            str | None,
            Field(
                description="Optional Agent natural filter hint. For faces, matches_filter=is_exterior maps to boundary_condition=Outdoors and face_type=Wall when unset."
            ),
        ] = None,
        matches: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Optional previous search matches accidentally echoed by Agents. Ignored; use object_type/query/filters for a new search."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Search Honeybee objects and return typed targets."""
        _ = (domain, matches_only)
        if model_target is None and target is not None:
            model_target = target
        if isinstance(children_scope, bool):
            children_scope = None
        if children_scope is None and host_target is not None:
            children_scope = host_target
        if children_scope is None and room_target is not None:
            children_scope = room_target
        if limit is None and matches_limit is not None:
            limit = matches_limit
        if query is None and search_pattern:
            query = search_pattern
        if matches_type is None and match_type:
            matches_type = match_type
        if matches_filter and matches_filter.strip().lower() in {
            "is_exterior",
            "exterior",
            "outdoors",
            "outdoor",
        }:
            if boundary_condition is None:
                boundary_condition = "Outdoors"
            if face_type is None:
                face_type = "Wall"
        object_type = object_type.strip().lower().replace("-", "_").replace(" ", "_")
        if matches_type:
            normalized_matches_type = matches_type.strip()
            if normalized_matches_type.lower() in {
                "wall",
                "walls",
                "floor",
                "floors",
                "roof",
                "roofs",
                "roofceiling",
                "airboundary",
            }:
                object_type = "face"
                if face_type is None:
                    face_type = {
                        "walls": "Wall",
                        "floors": "Floor",
                        "roofs": "RoofCeiling",
                    }.get(normalized_matches_type.lower(), normalized_matches_type)
            elif normalized_matches_type.lower() in {"boundary_condition", "boundary"}:
                object_type = "face"
            elif object_type == "all":
                object_type = normalized_matches_type
        if object_type in {"model", "models", "honeybee_model", "honeybee_models"}:
            base = get_base_honeybee_model_service(
                garden_root=garden_root,
                include_body=False,
            )
            target = base.get("target")
            matches = []
            if isinstance(target, dict):
                matches.append(
                    {
                        "identifier": target.get("model_identifier") or target.get("identifier"),
                        "object_type": "model",
                        "target": target,
                    }
                )
            return {
                "garden_root": base.get("garden_root"),
                "matches": matches,
                "count": len(matches),
                "target": target if len(matches) == 1 else None,
                "summary_view": {
                    "object_type": "model",
                    "count": len(matches),
                    "has_base_honeybee_model": target is not None,
                },
                "report": base.get("report"),
            }
        radiance_type = _radiance_object_type(object_type)
        if radiance_type is not None:
            return _search_radiance_artifacts(
                garden_root=garden_root,
                object_type=radiance_type,
                identifier=identifier,
                query=query,
                limit=limit,
            )
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
