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
    allowed = {"v", "h", "l", "c", "a", "s"}
    if normalized not in allowed:
        raise ValueError("view_type must be one of v, h, l, c, a, s, or a Radiance vt* token.")
    return normalized


def register(mcp: FastMCP) -> None:
    'Register the radiance_create_view tool.'

    @mcp.tool(
        name="create_view",
        description=(
            "Create a Radiance View / Honeybee Radiance View for rpict "
            "daylight rendering from position, direction or look-at point, up "
            "vector, view type, and view size. With garden_root, the tool "
            "writes a Garden .vf artifact and returns a compact radiance_view "
            "target. Set attach_to_model=true to add the View to the Honeybee "
            "model Radiance properties for later view or glare recipes. This "
            "creates view input data and does not render HDR images."
        ),
        tags={
            "radiance",
            "view",
            "author",
            "camera",
        },
        timeout=60,
    )
    def create_radiance_view(
        identifier: Annotated[
            str | None,
            Field(description="Stable View identifier. Defaults to view when omitted."),
        ] = None,
        position: Annotated[
            list[float] | dict[str, float] | None,
            Field(description="View position [x, y, z]. Default is [0, 0, 0]."),
        ] = None,
        direction: Annotated[
            list[float] | dict[str, float] | None,
            Field(description="View direction [x, y, z]. Default is [0, 0, 1]."),
        ] = None,
        target: Annotated[
            list[float] | dict[str, float] | None,
            Field(description="Optional look-at point [x, y, z]. Used to derive direction as target - position when direction is omitted."),
        ] = None,
        up_vector: Annotated[
            list[float] | dict[str, float] | None,
            Field(description="View up vector [x, y, z]. Default is [0, 1, 0]."),
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
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target with target_type=honeybee_model. Used when attach_to_model is true; omitted means Garden base model."),
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
        if model_target is not None and not attach_to_model:
            attach_to_model = True
        position = _vector(position, "position")
        direction = _vector(direction, "direction")
        target = _vector(target, "target")
        up_vector = _vector(up_vector, "up_vector")
        if direction is None:
            direction = _direction_from_target(position, target)
        view_type = _normalize_view_type(view_type)
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
