"""Natural-language alias for creating a Honeybee Radiance View."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.assets import create_radiance_view as service
from ladybug_tools_mcp.tools.radiance.create_radiance_view import (
    _direction_from_target,
    _normalize_view_size,
    _normalize_view_type,
    _vector,
)


VectorInput = list[float] | dict[str, float] | None


def register(mcp: FastMCP) -> None:
    """Register create_honeybee_view as an alias of create_radiance_view."""

    @mcp.tool(
        name="create_honeybee_view",
        description="Alias for create_radiance_view. Create and optionally attach a Honeybee Radiance View target for point-in-time Radiance view rendering.",
        tags={
            "honeybee-radiance",
            "honeybee",
            "radiance",
            "view",
            "rpict",
            "garden-mode",
            "model",
            "target",
            "artifact",
            "write",
            "safe",
            "alias",
        },
        timeout=60,
    )
    def create_honeybee_view(
        identifier: Annotated[
            str | None,
            Field(description="Stable View identifier. Defaults to view."),
        ] = None,
        position: Annotated[
            VectorInput,
            Field(description="View position [x, y, z]. Default is [0, 0, 0]."),
        ] = None,
        center: Annotated[
            VectorInput,
            Field(description="Optional alias for position."),
        ] = None,
        direction: Annotated[
            VectorInput,
            Field(description="View direction [x, y, z]. Default is [0, 0, 1]."),
        ] = None,
        target: Annotated[
            VectorInput,
            Field(description="Optional look-at point [x, y, z]. Used when direction is omitted."),
        ] = None,
        look_at: Annotated[
            VectorInput,
            Field(description="Alias for target look-at point."),
        ] = None,
        up_vector: Annotated[
            VectorInput,
            Field(description="View up vector [x, y, z]. Default is [0, 1, 0]."),
        ] = None,
        up: Annotated[
            VectorInput,
            Field(description="Alias for up_vector."),
        ] = None,
        view_type: Annotated[
            str | None,
            Field(description="Radiance view type character or natural token such as Perspective."),
        ] = None,
        type_: Annotated[
            str | None,
            Field(alias="type", description="Alias for view_type accepted for Agent compatibility."),
        ] = None,
        h_size: Annotated[float, Field(description="Horizontal view size or field of view.")] = 60,
        v_size: Annotated[float, Field(description="Vertical view size or field of view.")] = 60,
        garden_root: Annotated[
            str | None,
            Field(description="Optional Garden root path. When provided, writes a .vf artifact and target."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target. Used when attach_to_model is true."),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(description="Alias for model_target."),
        ] = None,
        attach_to_model: Annotated[
            bool,
            Field(description="When true, add the View to the Honeybee model Radiance properties."),
        ] = False,
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full View object_dict. Keep false for compact Agent handoff."),
        ] = False,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance View."""
        if identifier is None:
            identifier = "view"
        if model_target is None and host_target is not None:
            model_target = host_target
            attach_to_model = True
        elif model_target is not None and not attach_to_model:
            attach_to_model = True
        position = _vector(position, "position")
        center = _vector(center, "center")
        direction = _vector(direction, "direction")
        target = _vector(target, "target")
        look_at = _vector(look_at, "look_at")
        up_vector = _vector(up_vector, "up_vector")
        up = _vector(up, "up")
        if position is None and center is not None:
            position = center
        if target is None:
            target = look_at
        if direction is None:
            direction = _direction_from_target(position, target)
        if up_vector is None and up is not None:
            up_vector = up
        normalized_view_type = _normalize_view_type(view_type or type_ or "v")
        h_size, v_size = _normalize_view_size(normalized_view_type, h_size, v_size)
        return service(
            identifier=identifier,
            position=position,
            direction=direction,
            up_vector=up_vector,
            view_type=normalized_view_type,
            h_size=h_size,
            v_size=v_size,
            garden_root=garden_root,
            model_target=model_target,
            attach_to_model=attach_to_model,
            return_object_dict=return_object_dict,
        )
