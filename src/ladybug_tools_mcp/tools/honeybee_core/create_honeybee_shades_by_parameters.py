"""Create Honeybee Shades By Parameters MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.creation import (
    create_honeybee_shades_by_parameters as service,
)


def register(mcp: FastMCP) -> None:
    """Register the create_honeybee_shades_by_parameters tool."""

    @mcp.tool(
        name="create_honeybee_shades_by_parameters",
        description="Create Honeybee Shade louvers, horizontal louver arrays, overhangs, sunshade fins, exterior window shade devices, or extruded borders on a Face or Aperture typed target. This is the preferred tool for natural requests like add 3 horizontal louvers above a window, add an overhang with depth, or add exterior sunshades; use low-level create_honeybee_shade only when the user provides explicit Face3D geometry. Prefer search_honeybee_model_objects matches[i].target or a prior result target as host_target; unique responses can be auto-unwrapped. Supports louver_by_count, louver_by_distance_between, aperture-only extruded_border, and natural overhang/sunshade aliases normalized to one louver_by_count shade when only depth is provided. Requires garden_root, host_target, generation_mode, and parameters; do not pass arguments null or {}. Use create_honeybee_shades_by_parameters for parametric louver/overhang workflows.",
        tags={
            "honeybee-core",
            "garden-mode",
            "shade",
            "face",
            "aperture",
            "louver",
            "horizontal-louver",
            "overhang",
            "sunshade",
            "window-shade",
            "exterior-shade",
            "parametric-shade",
            "extruded-border",
            "parameters",
            "create",
            "write",
            "safe",
        },
        timeout=20,
    )
    def create_honeybee_shades_by_parameters(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description="Required Honeybee face or aperture typed target dict from nested target search_honeybee_model_objects matches[i].target or a prior create result target; a unique full tool response can be auto-unwrapped, but ambiguous responses and identifier strings are rejected."
            ),
        ],
        generation_mode: Annotated[
            str | None,
            Field(
                description="Required generation mode: louver_by_count, louver_by_distance_between, or extruded_border. Natural aliases overhang, horizontal_overhang, and sunshade are accepted and create one louver_by_count shade when no count is given. extruded_border only accepts an aperture target."
            ),
        ] = None,
        mode: Annotated[
            str | None,
            Field(
                description="Optional natural synonym for generation_mode; use generation_mode in stable hand-written calls."
            ),
        ] = None,
        parameters: Annotated[
            dict[str, Any] | None,
            Field(
                description="Required small mode parameter object: louver_by_count uses {'depth':0.35,'louver_count':2}; {'depth':0.35,'count':1} is accepted as a natural alias. louver_by_distance_between uses {'depth':0.35,'distance':0.5}; extruded_border uses {'depth':0.2}; overhang uses {'depth':0.35}."
            ),
        ] = None,
        depth: Annotated[
            float | None,
            Field(
                description="Optional top-level shortcut copied into parameters.depth."
            ),
        ] = None,
        louver_depth: Annotated[
            float | None,
            Field(
                description="Optional natural synonym for depth; accepted to avoid Agent retries."
            ),
        ] = None,
        width: Annotated[
            float | None,
            Field(
                description="Optional natural louver-width hint accepted to avoid Agent retries. Current SDK shade parameter methods do not use it; use depth and count/distance for geometry control."
            ),
        ] = None,
        count: Annotated[
            int | None,
            Field(
                description="Optional top-level shortcut copied into parameters.louver_count for louver_by_count."
            ),
        ] = None,
        louver_count: Annotated[
            int | None,
            Field(
                description="Optional top-level shortcut copied into parameters.louver_count."
            ),
        ] = None,
        distance: Annotated[
            float | None,
            Field(
                description="Optional top-level shortcut copied into parameters.distance for louver_by_distance_between."
            ),
        ] = None,
        offset: Annotated[
            float | None,
            Field(
                description="Optional top-level shortcut copied into parameters.offset."
            ),
        ] = None,
        vertical_offset: Annotated[
            float | None,
            Field(
                description="Optional natural synonym for offset; accepted to avoid Agent retries for overhang requests."
            ),
        ] = None,
        offset_from_host: Annotated[
            float | None,
            Field(
                description="Optional natural synonym for offset; accepted to avoid Agent retries."
            ),
        ] = None,
        angle: Annotated[
            float | None,
            Field(
                description="Optional top-level shortcut copied into parameters.angle."
            ),
        ] = None,
        louver_orientation: Annotated[
            str | None,
            Field(
                description="Optional natural orientation hint such as horizontal. Accepted as a harmless Agent hint; use angle/contour_vector for precise control."
            ),
        ] = None,
        indoor: Annotated[
            bool | None,
            Field(
                description="Optional top-level shortcut copied into parameters.indoor."
            ),
        ] = None,
        identifier_prefix: Annotated[
            str | None,
            Field(
                description="Optional natural shade naming prefix copied into parameters.base_name."
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(
                description="Optional natural shade naming prefix copied into parameters.base_name."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict. Defaults to the Garden base model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create Honeybee Shades on a Face or Aperture with SDK parameter methods."""
        parameters = dict(parameters or {})
        generation_mode = mode or generation_mode
        normalized_mode = (
            str(generation_mode or "").strip().lower().replace("-", "_")
        )
        if normalized_mode in {
            "overhang",
            "single_overhang",
            "horizontal_overhang",
            "sunshade",
            "window_overhang",
        }:
            generation_mode = "louver_by_count"
            parameters.setdefault("louver_count", 1)
        if depth is None:
            depth = louver_depth
        if depth is None:
            depth = parameters.get("louver_depth")
        if "angle" not in parameters and "louver_angle" in parameters:
            parameters["angle"] = parameters["louver_angle"]
        if offset is None:
            offset = offset_from_host if offset_from_host is not None else vertical_offset
        for key, value in {
            "depth": depth,
            "distance": distance,
            "offset": offset,
            "angle": angle,
            "indoor": indoor,
        }.items():
            if value is not None:
                parameters.setdefault(key, value)
        if width is not None:
            parameters.setdefault("width", width)
        if louver_count is not None:
            parameters.setdefault("louver_count", louver_count)
        elif count is not None:
            parameters.setdefault("louver_count", count)
        elif "louver_count" not in parameters and parameters.get("count") is not None:
            parameters["louver_count"] = parameters["count"]
        name_prefix = identifier_prefix or identifier
        if name_prefix is not None:
            parameters.setdefault("base_name", name_prefix)
        return service(
            garden_root=garden_root,
            host_target=host_target,
            generation_mode=generation_mode,
            parameters=parameters,
            model_target=model_target,
        )
