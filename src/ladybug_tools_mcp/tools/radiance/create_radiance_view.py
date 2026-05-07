"""Create a Honeybee Radiance View MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.assets import create_radiance_view as service


VectorInput = list[float] | dict[str, float] | None


def _vector(value: VectorInput, field_name: str) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        try:
            return [float(value[axis]) for axis in ("x", "y", "z")]
        except KeyError as exc:
            raise ValueError(f"{field_name} dict must include x, y, and z.") from exc
    return [float(item) for item in value]


def _direction_from_target(
    position: list[float] | None,
    target: list[float] | None,
) -> list[float] | None:
    if target is None:
        return None
    origin = position or [0, 0, 0]
    if len(origin) != 3 or len(target) != 3:
        raise ValueError("position and target must both be [x, y, z] vectors.")
    return [float(target[index]) - float(origin[index]) for index in range(3)]


def _normalize_view_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.startswith("vt") and len(normalized) == 3:
        normalized = normalized[-1]
    aliases = {
        "absolute": "v",
        "perspective": "v",
        "vterrain": "v",
        "terrain": "v",
        "view": "v",
        "camera": "v",
        "vertical": "v",
        "glare": "v",
        "g": "v",
        "hemispherical": "h",
    }
    if normalized in aliases:
        return aliases[normalized]
    allowed = {"v", "h", "l", "c", "a", "s"}
    if normalized not in allowed and normalized[:1] in allowed:
        normalized = normalized[:1]
    return normalized


def _normalize_view_size(view_type: str, h_size: float, v_size: float) -> tuple[float, float]:
    if view_type == "v":
        if h_size >= 180:
            h_size = 60
        if v_size >= 180:
            v_size = 60
    return h_size, v_size


def register(mcp: FastMCP) -> None:
    """Register the create_radiance_view tool."""

    @mcp.tool(
        name="create_radiance_view",
        description="Create Radiance view / Honeybee Radiance View for rpict daylight rendering from position, direction or look-at target point, up vector, view type, and view size. With garden_root, writes a Garden .vf artifact and returns a compact radiance_view target. Set attach_to_model=true to add the View to the Honeybee model Radiance properties for later rpict/glare/daylight workflows.",
        tags={
            "honeybee-radiance",
            "radiance",
            "view",
            "vf",
            "rpict",
            "glare",
            "daylight",
            "garden-mode",
            "model",
            "target",
            "artifact",
            "write",
            "safe",
        },
        timeout=60,
    )
    def create_radiance_view(
        identifier: Annotated[
            str | None,
            Field(description="Stable View identifier. Defaults to view when omitted by an Agent."),
        ] = None,
        position: Annotated[
            list[float] | dict[str, float] | None,
            Field(description="View position [x, y, z]. Default is [0, 0, 0]."),
        ] = None,
        center: Annotated[
            list[float] | dict[str, float] | None,
            Field(description="Optional Agent alias for position."),
        ] = None,
        direction: Annotated[
            list[float] | dict[str, float] | None,
            Field(description="View direction [x, y, z]. Default is [0, 0, 1]."),
        ] = None,
        target: Annotated[
            list[float] | dict[str, float] | None,
            Field(description="Optional look-at point [x, y, z]. Used to derive direction as target - position when direction is omitted."),
        ] = None,
        look_at: Annotated[
            list[float] | dict[str, float] | None,
            Field(description="Alias for target look-at point accepted for Agent compatibility."),
        ] = None,
        look: Annotated[
            list[float] | dict[str, float] | None,
            Field(description="Alias for target/look_at accepted for Agent compatibility."),
        ] = None,
        look_at_target: Annotated[
            list[float] | dict[str, float] | None,
            Field(description="Alias for target/look_at accepted for Agent compatibility."),
        ] = None,
        up_vector: Annotated[
            list[float] | dict[str, float] | None,
            Field(description="View up vector [x, y, z]. Default is [0, 1, 0]."),
        ] = None,
        up: Annotated[
            list[float] | dict[str, float] | None,
            Field(description="Alias for up_vector accepted for Agent compatibility."),
        ] = None,
        view_type: Annotated[
            str,
            Field(description="Radiance view type character: v, h, l, c, a, or s. Radiance CLI tokens like vtv/vth/vtl/vtc/vta/vts are accepted."),
        ] = "v",
        h_size: Annotated[
            float,
            Field(description="Horizontal view size or field of view."),
        ] = 60,
        v_size: Annotated[
            float,
            Field(description="Vertical view size or field of view."),
        ] = 60,
        shift: Annotated[
            float | None,
            Field(description="Optional Radiance view shift (-vs)."),
        ] = None,
        lift: Annotated[
            float | None,
            Field(description="Optional Radiance view lift (-vl)."),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional display name."),
        ] = None,
        room_identifier: Annotated[
            str | None,
            Field(description="Optional Honeybee Room identifier associated with this view."),
        ] = None,
        group_identifier: Annotated[
            str | None,
            Field(description="Optional Radiance group identifier."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Optional Garden root path. When provided, writes a .vf artifact and target."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target. Used when attach_to_model is true; omitted means Garden base model."),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Agent alias for model_target when attaching the View to a Honeybee model."),
        ] = None,
        attach_to_model: Annotated[
            bool,
            Field(description="When true, add the View to model.properties.radiance.views and save the model."),
        ] = False,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for Radiance view .vf artifacts."),
        ] = "artifacts/radiance/views",
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full View object_dict. Keep false for compact Agent handoff."),
        ] = True,
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
        look = _vector(look, "look")
        look_at_target = _vector(look_at_target, "look_at_target")
        up_vector = _vector(up_vector, "up_vector")
        up = _vector(up, "up")
        if position is None and center is not None:
            position = center
        if target is None:
            target = look_at
        if target is None:
            target = look
        if target is None:
            target = look_at_target
        if direction is None:
            direction = _direction_from_target(position, target)
        if up_vector is None and up is not None:
            up_vector = up
        view_type = _normalize_view_type(view_type)
        h_size, v_size = _normalize_view_size(view_type, h_size, v_size)
        return service(
            identifier=identifier,
            position=position,
            direction=direction,
            up_vector=up_vector,
            view_type=view_type,
            h_size=h_size,
            v_size=v_size,
            shift=shift,
            lift=lift,
            display_name=display_name,
            room_identifier=room_identifier,
            group_identifier=group_identifier,
            garden_root=garden_root,
            model_target=model_target,
            attach_to_model=attach_to_model,
            output_subdir=output_subdir,
            return_object_dict=return_object_dict,
        )
