"""Create Honeybee Apertures By Parameters MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.creation import (
    create_honeybee_apertures_by_parameters as service,
)
from garden.honeybee_core.search import search_honeybee_model_objects


def register(mcp: FastMCP) -> None:
    """Register the create_honeybee_apertures_by_parameters tool."""

    @mcp.tool(
        name="create_honeybee_apertures_by_parameters",
        description="Create Honeybee Apertures, windows, rectangular windows, glazed openings, glazing ratio, window-to-wall ratio, or WWR openings on a host exterior wall Face typed target by ratio or by width and height parameters. This is the preferred tool for natural requests like add windows by WWR, set window-to-wall ratio to 0.3, add rectangular windows, or apply glazing percentage; use low-level create_honeybee_aperture only when the user provides explicit Face3D geometry. Prefer a search_honeybee_model_objects face match where face_type is Wall and boundary_condition is Outdoors; unique search responses can be auto-unwrapped. Requires a full arguments object with garden_root, host_target, and mode-specific parameters; do not pass arguments null or {}. Use create_honeybee_apertures_by_parameters for parametric window/WWR workflows.",
        tags={
            "honeybee-core",
            "garden-mode",
            "aperture",
            "window",
            "rectangular-window",
            "glazed-opening",
            "glazing-ratio",
            "window-to-wall-ratio",
            "wwr",
            "wall",
            "face",
            "parameters",
            "ratio",
            "width-height",
            "create",
            "write",
            "safe",
        },
        timeout=20,
    )
    def create_honeybee_apertures_by_parameters(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        host_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Required Honeybee face typed target dict from nested target search_honeybee_model_objects matches[i].target, a prior create result target, or a unique full tool response that can be auto-unwrapped; choose a Wall/Outdoors face for exterior windows. Ambiguous responses, room targets, floor/ground faces, and identifier strings are rejected."
            ),
        ] = None,
        host_face_target: Annotated[
            dict[str, Any] | None,
            Field(description="Natural-language alias for host_target accepted for Agent compatibility."),
        ] = None,
        room_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Agent alias. When host_target is omitted, a Wall face is searched under this room target."),
        ] = None,
        wall_identifier: Annotated[
            str | None,
            Field(description="Optional wall identifier/query hint used with room_target to find a host Wall face."),
        ] = None,
        wall_index: Annotated[
            int | None,
            Field(description="Optional natural wall index hint when a room target is provided. Interpreted against Wall face search results."),
        ] = None,
        wall_indices: Annotated[
            int | list[int] | None,
            Field(description="Optional Agent alias for wall_index. If a list is provided, the first index is used."),
        ] = None,
        face_identifier: Annotated[
            str | None,
            Field(description="Optional natural synonym for wall_identifier when the host Face identifier is known."),
        ] = None,
        face_name: Annotated[
            str | None,
            Field(description="Optional natural synonym for face_identifier; accepted to avoid Agent retries."),
        ] = None,
        face_type: Annotated[
            str | None,
            Field(description="Optional Agent face-type hint accepted for compatibility; exterior wall selection should use a Face target or room_target/wall_identifier."),
        ] = None,
        offset: Annotated[
            list[float] | None,
            Field(description="Optional Agent placement hint accepted for compatibility. Ignored by parameter-based SDK methods."),
        ] = None,
        generation_mode: Annotated[
            str | None,
            Field(
                description="Generation mode: by_ratio or by_width_height. The short values ratio, window_ratio, and by_count_and_ratio are normalized to by_ratio. by_ratio requires ratio; by_width_height requires aperture_width and aperture_height."
            ),
        ] = "by_ratio",
        mode: Annotated[
            str | None,
            Field(
                description="Optional natural synonym for generation_mode; use generation_mode in stable hand-written calls."
            ),
        ] = None,
        parameters: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Agent fallback parameter object. Prefer top-level ratio, aperture_width, aperture_height, and sill_height in stable calls."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict. Defaults to the Garden base model."
            ),
        ] = None,
        ratio: Annotated[
            float | None,
            Field(
                description="Required for by_ratio mode: aperture-to-face area ratio between 0 and 1, for example 0.3."
            ),
        ] = None,
        count: Annotated[
            int | None,
            Field(
                description="Optional user-requested window count hint. Current SDK ratio mode may ignore this; included to avoid rejecting natural Agent requests."
            ),
        ] = None,
        x_count: Annotated[
            int | None,
            Field(description="Optional horizontal count hint accepted for Agent compatibility. Current SDK ratio mode may ignore this."),
        ] = None,
        y_count: Annotated[
            int | None,
            Field(description="Optional vertical count hint accepted for Agent compatibility. Current SDK ratio mode may ignore this."),
        ] = None,
        aperture_count: Annotated[
            int | None,
            Field(
                description="Optional natural synonym for count; accepted to avoid Agent retries."
            ),
        ] = None,
        x_ratio: Annotated[
            float | None,
            Field(
                description="Optional natural placement hint accepted to avoid Agent retries. Current SDK ratio mode ignores this value."
            ),
        ] = None,
        y_ratio: Annotated[
            float | None,
            Field(
                description="Optional natural placement hint accepted to avoid Agent retries. Current SDK ratio mode ignores this value."
            ),
        ] = None,
        horizontal_spacing: Annotated[
            float | None,
            Field(
                description="Optional natural layout hint accepted to avoid Agent retries. Current SDK parameter methods ignore this value."
            ),
        ] = None,
        vertical_spacing: Annotated[
            float | None,
            Field(
                description="Optional natural layout hint accepted to avoid Agent retries. Current SDK parameter methods ignore this value."
            ),
        ] = None,
        aperture_width: Annotated[
            float | None,
            Field(
                description="Required for by_width_height mode: single aperture width in model units."
            ),
        ] = None,
        window_width: Annotated[
            float | None,
            Field(
                description="Optional natural synonym for aperture_width; accepted to avoid Agent retries."
            ),
        ] = None,
        aperture_height: Annotated[
            float | None,
            Field(
                description="Required for by_width_height mode: single aperture height in model units."
            ),
        ] = None,
        window_height: Annotated[
            float | None,
            Field(
                description="Optional natural synonym for aperture_height; accepted as a harmless hint in ratio mode."
            ),
        ] = None,
        sill_height: Annotated[
            float,
            Field(description="Sill height for by_width_height mode in model units."),
        ] = 1.0,
        aperture_identifier: Annotated[
            str | None,
            Field(
                description="Optional aperture identifier for by_width_height mode. Defaults to SDK naming."
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(
                description="Optional natural naming alias. In ratio mode it names created windows as a prefix; in width-and-height mode it names the single aperture when no explicit aperture name is provided."
            ),
        ] = None,
        identifier_prefix: Annotated[
            str | None,
            Field(
                description="Optional Agent-friendly prefix for created aperture identifiers, especially when ratio mode creates SDK-named windows."
            ),
        ] = None,
        aperture_name_prefix: Annotated[
            str | None,
            Field(
                description="Optional natural synonym for the aperture naming prefix; accepted to avoid Agent retries."
            ),
        ] = None,
        name_prefix: Annotated[
            str | None,
            Field(
                description="Optional natural synonym for the aperture naming prefix; accepted to avoid Agent retries."
            ),
        ] = None,
        tolerance: Annotated[
            float, Field(description="Geometry tolerance used by by_ratio mode.")
        ] = 0.01,
        rect_split: Annotated[
            bool,
            Field(
                description="Whether by_ratio should split apertures into rectangles when needed."
            ),
        ] = True,
        create_shades: Annotated[
            bool | None,
            Field(description="Ignored Agent compatibility hint. Use create_honeybee_shades_by_parameters after apertures when shades are needed."),
        ] = None,
    ) -> dict[str, Any]:
        """Create Honeybee Apertures on a host Face by ratio or width/height parameters."""
        _ = create_shades
        parameters = dict(parameters or {})
        if host_target is None and host_face_target is not None:
            host_target = host_face_target
        if wall_index is None and wall_indices is not None:
            wall_index = wall_indices[0] if isinstance(wall_indices, list) else wall_indices
        if (
            isinstance(host_target, dict)
            and host_target.get("object_type") == "room"
            and room_target is None
        ):
            room_target = host_target
            host_target = None
        generation_mode = mode or generation_mode or "by_ratio"
        if count is None:
            count = aperture_count
        if count is None and x_count is not None and y_count is not None:
            count = int(x_count) * int(y_count)
        if ratio is None:
            ratio = parameters.get("ratio") or parameters.get("window_ratio")
        if aperture_width is None:
            aperture_width = (
                window_width
                or parameters.get("aperture_width")
                or parameters.get("window_width")
                or parameters.get("width")
            )
        if aperture_height is None:
            aperture_height = (
                window_height
                or parameters.get("aperture_height")
                or parameters.get("window_height")
                or parameters.get("height")
            )
        if "sill_height" in parameters and sill_height == 1.0:
            sill_height = parameters["sill_height"]
        if "tolerance" in parameters and tolerance == 0.01:
            tolerance = parameters["tolerance"]
        if "rect_split" in parameters:
            rect_split = parameters["rect_split"]
        if identifier_prefix is None:
            identifier_prefix = aperture_name_prefix or name_prefix
        if wall_identifier is None:
            wall_identifier = face_identifier or face_name
        if host_target is None and room_target is not None:
            search_limit = 50 if wall_index is not None else 1
            search = search_honeybee_model_objects(
                garden_root=garden_root,
                model_target=model_target,
                object_type="face",
                query=wall_identifier,
                face_type="Wall",
                children_scope=room_target,
                limit=search_limit,
            )
            if not search["matches"] and wall_identifier:
                search = search_honeybee_model_objects(
                    garden_root=garden_root,
                    model_target=model_target,
                    object_type="face",
                    face_type="Wall",
                    children_scope=room_target,
                    limit=search_limit,
                )
            if search["matches"]:
                selected_index = 0
                if wall_index is not None:
                    if 0 <= wall_index < len(search["matches"]):
                        selected_index = wall_index
                    elif 1 <= wall_index <= len(search["matches"]):
                        selected_index = wall_index - 1
                host_target = search["matches"][selected_index]["target"]
        if host_target is None and wall_identifier:
            search = search_honeybee_model_objects(
                garden_root=garden_root,
                model_target=model_target,
                object_type="face",
                identifier=wall_identifier,
                face_type="Wall",
                limit=1,
            )
            if not search["matches"]:
                search = search_honeybee_model_objects(
                    garden_root=garden_root,
                    model_target=model_target,
                    object_type="face",
                    query=wall_identifier,
                    face_type="Wall",
                    limit=1,
                )
            if search["matches"]:
                host_target = search["matches"][0]["target"]
        if host_target is None:
            raise ValueError(
                "host_target is required. Provide a face target, or provide room_target so a Wall face can be selected."
            )
        normalized_mode = {
            "ratio": "by_ratio",
            "window_ratio": "by_ratio",
            "by_window_ratio": "by_ratio",
            "count_and_ratio": "by_ratio",
            "by_count_and_ratio": "by_ratio",
            "width_height": "by_width_height",
            "width_and_height": "by_width_height",
        }.get(generation_mode, generation_mode)
        if identifier is not None:
            if normalized_mode == "by_width_height" and aperture_identifier is None:
                aperture_identifier = identifier
            elif identifier_prefix is None:
                identifier_prefix = identifier
        return service(
            garden_root=garden_root,
            host_target=host_target,
            generation_mode=generation_mode,
            model_target=model_target,
            ratio=ratio,
            aperture_width=aperture_width,
            aperture_height=aperture_height,
            sill_height=sill_height,
            aperture_identifier=aperture_identifier,
            identifier_prefix=identifier_prefix,
            tolerance=tolerance,
            rect_split=rect_split,
        )
