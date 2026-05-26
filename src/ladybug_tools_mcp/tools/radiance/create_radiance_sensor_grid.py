"""Create a Honeybee Radiance SensorGrid MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.assets import create_radiance_sensor_grid as service

VectorInput = list[float] | dict[str, float] | None


def _vector(value: VectorInput, name: str) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        try:
            return [float(value["x"]), float(value["y"]), float(value["z"])]
        except KeyError as exc:
            raise ValueError(f"{name} dict must include x, y, and z.") from exc
    if len(value) != 3:
        raise ValueError(f"{name} must include exactly three numbers.")
    return [float(value[0]), float(value[1]), float(value[2])]


def _room_identifier_from_target(
    room_identifier: str | None,
    room_target: dict[str, Any] | None,
) -> str | None:
    if room_identifier is not None or not isinstance(room_target, dict):
        return room_identifier
    if str(room_target.get("object_type", "")).lower() == "room":
        value = room_target.get("object_identifier") or room_target.get("identifier")
        if isinstance(value, str) and value:
            return value
    return room_identifier


def _positions_from_rectangular_grid(
    *,
    positions: list[list[float]] | None,
    x_dim: float | None,
    y_dim: float | None,
    height: float | None,
    x_count: int | None,
    y_count: int | None,
    grid_spacing: float | None = None,
    origin: list[float] | None = None,
) -> list[list[float]]:
    if positions is not None:
        return positions
    if x_dim is not None and y_dim is not None:
        if grid_spacing is not None and grid_spacing > 0:
            x_count = max(1, int(float(x_dim) / float(grid_spacing)))
            y_count = max(1, int(float(y_dim) / float(grid_spacing)))
        x_count = 4 if x_count is None else x_count
        y_count = 4 if y_count is None else y_count
    if x_dim is None or y_dim is None or x_count is None or y_count is None:
        if x_count is not None and y_count is not None:
            x_dim = float(x_count) if x_dim is None else x_dim
            y_dim = float(y_count) if y_dim is None else y_dim
    if x_dim is None or y_dim is None or x_count is None or y_count is None:
        raise ValueError(
            "Provide positions, or provide x_dim, y_dim, x_count, and y_count to create a rectangular workplane grid."
        )
    if x_dim <= 0 or y_dim <= 0:
        raise ValueError("x_dim and y_dim must be greater than zero.")
    if x_count < 1 or y_count < 1:
        raise ValueError("x_count and y_count must be at least 1.")
    origin_values = origin or [0, 0, 0]
    if len(origin_values) != 3:
        raise ValueError("origin must include exactly three numbers when provided.")
    z = float(origin_values[2]) + float(0.8 if height is None else height)
    x_step = float(x_dim) / int(x_count)
    y_step = float(y_dim) / int(y_count)
    return [
        [
            float(origin_values[0]) + (x_index + 0.5) * x_step,
            float(origin_values[1]) + (y_index + 0.5) * y_step,
            z,
        ]
        for y_index in range(int(y_count))
        for x_index in range(int(x_count))
    ]


def register(mcp: FastMCP) -> None:
    'Register the radiance_create_sensor_grid tool.'

    @mcp.tool(
        name="create_sensor_grid",
        description=(
            "Create a Honeybee Radiance SensorGrid from explicit sensor "
            "positions or rectangular workplane dimensions. With garden_root, "
            "the tool writes a Garden .pts artifact and returns a compact "
            "radiance_sensor_grid target. Set attach_to_model=true to add the "
            "SensorGrid to the Honeybee model Radiance properties for later "
            "daylight recipes. This creates sensor points, not room geometry "
            "or EnergyPlus result data."
        ),
        tags={
            "radiance",
            "sensor-grid",
            "author",
            "pts",
        },
        timeout=60,
    )
    def create_radiance_sensor_grid(
        identifier: Annotated[
            str | None,
            Field(description="Stable Radiance SensorGrid identifier. Defaults to sensor_grid when omitted."),
        ] = None,
        positions: Annotated[
            list[list[float]] | None,
            Field(description="Sensor positions as [[x, y, z], ...]. Omit only when using x_dim/y_dim/x_count/y_count."),
        ] = None,
        direction: Annotated[
            list[float] | None,
            Field(description="Optional shared sensor direction [x, y, z]. Default is [0, 0, 1]. Use instead of directions."),
        ] = None,
        directions: Annotated[
            list[list[float]] | None,
            Field(description="Optional per-position directions as [[x, y, z], ...]. Must match positions length. Use instead of direction."),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional display name."),
        ] = None,
        room_identifier: Annotated[
            str | None,
            Field(description="Optional Honeybee Room identifier associated with this grid."),
        ] = None,
        room_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee Room target used to infer room_identifier when provided."),
        ] = None,
        x_dim: Annotated[
            float | None,
            Field(description="Optional rectangular workplane width in model units. Used only when positions is omitted."),
        ] = None,
        y_dim: Annotated[
            float | None,
            Field(description="Optional rectangular workplane depth in model units. Used only when positions is omitted."),
        ] = None,
        height: Annotated[
            float | None,
            Field(description="Optional workplane height above origin. Defaults to 0.8 when generating positions."),
        ] = None,
        x_count: Annotated[
            int | None,
            Field(description="Optional number of sensors along x when generating a rectangular grid."),
        ] = None,
        y_count: Annotated[
            int | None,
            Field(description="Optional number of sensors along y when generating a rectangular grid."),
        ] = None,
        grid_spacing: Annotated[
            float | None,
            Field(description="Optional spacing used to derive x_count/y_count from x_dim/y_dim."),
        ] = None,
        origin: Annotated[
            VectorInput,
            Field(description="Optional rectangular grid origin [x, y, z], or {'x': x, 'y': y, 'z': z}. Defaults to [0, 0, 0]."),
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
            Field(description="Optional Honeybee model target. Used when attach_to_model is true; omitted means Garden base model."),
        ] = None,
        attach_to_model: Annotated[
            bool,
            Field(description="When true, add the SensorGrid to model.properties.radiance.sensor_grids and save the model."),
        ] = False,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for Radiance sensor .pts artifacts."),
        ] = "artifacts/radiance/sensors",
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full SensorGrid object_dict. Keep false for compact Agent handoff."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance SensorGrid."""
        if identifier is None:
            identifier = "sensor_grid"
        if model_target is not None and not attach_to_model:
            attach_to_model = True
        origin = _vector(origin, "origin")
        if (
            positions is None
            and x_dim is None
            and y_dim is None
            and grid_spacing is not None
            and x_count is not None
            and y_count is not None
        ):
            x_dim = float(grid_spacing) * int(x_count)
            y_dim = float(grid_spacing) * int(y_count)
        positions = _positions_from_rectangular_grid(
            positions=positions,
            x_dim=x_dim,
            y_dim=y_dim,
            height=height,
            x_count=x_count,
            y_count=y_count,
            grid_spacing=grid_spacing,
            origin=origin,
        )
        room_identifier = _room_identifier_from_target(room_identifier, room_target)
        return service(
            identifier=identifier,
            positions=positions,
            direction=direction,
            directions=directions,
            display_name=display_name,
            room_identifier=room_identifier,
            group_identifier=group_identifier,
            garden_root=garden_root,
            model_target=model_target,
            attach_to_model=attach_to_model,
            output_subdir=output_subdir,
            return_object_dict=return_object_dict,
        )
