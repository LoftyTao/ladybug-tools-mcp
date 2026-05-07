"""Create a Honeybee Radiance SensorGrid MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.assets import create_radiance_sensor_grid as service


def _room_identifier_from_target(
    room_identifier: str | None,
    room_target: dict[str, Any] | None,
) -> str | None:
    if room_identifier is not None or not isinstance(room_target, dict):
        return room_identifier
    target = room_target.get("target") if isinstance(room_target.get("target"), dict) else room_target
    if str(target.get("object_type", "")).lower() == "room":
        value = target.get("object_identifier") or target.get("identifier")
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
    """Register the create_radiance_sensor_grid tool."""

    @mcp.tool(
        name="create_radiance_sensor_grid",
        description="Create a Honeybee Radiance SensorGrid from explicit positions or from rectangular workplane dimensions x_dim/y_dim/x_count/y_count. With garden_root, writes a Garden .pts artifact and returns a compact radiance_sensor_grid target. Set attach_to_model=true to add the SensorGrid to the Honeybee model Radiance properties for later daylight/radiance recipes.",
        tags={
            "honeybee-radiance",
            "radiance",
            "sensor-grid",
            "sensors",
            "pts",
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
    def create_radiance_sensor_grid(
        identifier: Annotated[
            str | None,
            Field(description="Stable SensorGrid identifier. Defaults to sensor_grid when omitted by an Agent."),
        ] = None,
        positions: Annotated[
            list[list[float]] | None,
            Field(description="Sensor positions as [[x, y, z], ...]. Omit only when using x_dim/y_dim/x_count/y_count."),
        ] = None,
        grid_points: Annotated[
            list[list[float]] | None,
            Field(description="Optional Agent alias for positions."),
        ] = None,
        grid_type: Annotated[
            str | None,
            Field(description="Optional Agent hint such as workplane. Ignored; this tool creates a SensorGrid."),
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
            Field(description="Optional Honeybee Room target alias. Used to infer room_identifier when provided."),
        ] = None,
        room_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional Agent alias for one or more room targets. The first room target is used."),
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
        workplane_height: Annotated[
            float | None,
            Field(description="Optional Agent alias for height."),
        ] = None,
        offset: Annotated[
            float | None,
            Field(description="Optional Agent alias for height/workplane offset."),
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
            Field(description="Optional spacing hint used to derive x_count/y_count from x_dim/y_dim."),
        ] = None,
        spacing: Annotated[
            float | None,
            Field(description="Alias for grid_spacing accepted for Agent compatibility."),
        ] = None,
        x_axis: Annotated[
            list[float] | None,
            Field(description="Optional local x-axis hint accepted for Agent compatibility. Rectangular grids are currently axis-aligned."),
        ] = None,
        y_axis: Annotated[
            list[float] | None,
            Field(description="Optional local y-axis hint accepted for Agent compatibility. Rectangular grids are currently axis-aligned."),
        ] = None,
        origin: Annotated[
            list[float] | None,
            Field(description="Optional rectangular grid origin [x, y, z]. Defaults to [0, 0, 0]."),
        ] = None,
        grid_origin: Annotated[
            list[float] | None,
            Field(description="Alias for origin accepted for Agent compatibility."),
        ] = None,
        group_identifier: Annotated[
            str | None,
            Field(description="Optional Radiance group identifier."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Optional Garden root path. When provided, writes a .pts artifact and target."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target. Used when attach_to_model is true; omitted means Garden base model."),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Agent alias for model_target when attaching the SensorGrid to a Honeybee model."),
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
        if model_target is None and host_target is not None:
            model_target = host_target
            attach_to_model = True
        elif model_target is not None and not attach_to_model:
            attach_to_model = True
        if height is None and workplane_height is not None:
            height = workplane_height
        if height is None and offset is not None:
            height = offset
        if grid_spacing is None and spacing is not None:
            grid_spacing = spacing
        if origin is None and grid_origin is not None:
            origin = grid_origin
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
        if room_target is None and room_targets:
            room_target = room_targets[0]
        if positions is None and x_dim is None and y_dim is None and room_target is not None:
            x_dim = 4
            y_dim = 4
        if positions is None and grid_points is not None:
            positions = grid_points
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
