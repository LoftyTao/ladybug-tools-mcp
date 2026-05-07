"""Create a Radiance SensorGrid spelling alias MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.assets import create_radiance_sensor_grid as service
from ladybug_tools_mcp.tools.radiance.create_radiance_sensor_grid import (
    _positions_from_rectangular_grid,
    _room_identifier_from_target,
)


def register(mcp: FastMCP) -> None:
    """Register the create_radiance_sensorgrid alias tool."""

    @mcp.tool(
        name="create_radiance_sensorgrid",
        description="Spelling alias for create_radiance_sensor_grid. Create a Honeybee Radiance SensorGrid from positions, grid_points, or rectangular workplane dimensions.",
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
            "alias",
        },
        timeout=60,
    )
    def create_radiance_sensorgrid(
        identifier: Annotated[str | None, Field(description="Stable SensorGrid identifier. Defaults to sensor_grid when omitted.")] = None,
        positions: Annotated[list[list[float]] | None, Field(description="Sensor positions as [[x, y, z], ...].")] = None,
        grid_points: Annotated[list[list[float]] | None, Field(description="Optional alias for positions.")] = None,
        direction: Annotated[list[float] | None, Field(description="Optional shared sensor direction.")] = None,
        directions: Annotated[list[list[float]] | None, Field(description="Optional per-position directions.")] = None,
        display_name: Annotated[str | None, Field(description="Optional display name.")] = None,
        room_identifier: Annotated[str | None, Field(description="Optional Room identifier.")] = None,
        room_target: Annotated[dict[str, Any] | None, Field(description="Optional Room target alias.")] = None,
        room_targets: Annotated[list[dict[str, Any]] | None, Field(description="Optional Agent alias for one or more room targets.")] = None,
        group_identifier: Annotated[str | None, Field(description="Optional Radiance group identifier.")] = None,
        x_dim: Annotated[float | None, Field(description="Optional rectangular workplane width.")] = None,
        y_dim: Annotated[float | None, Field(description="Optional rectangular workplane depth.")] = None,
        height: Annotated[float | None, Field(description="Optional workplane height.")] = None,
        workplane_height: Annotated[float | None, Field(description="Optional Agent alias for height.")] = None,
        offset: Annotated[float | None, Field(description="Optional Agent alias for height/workplane offset.")] = None,
        x_count: Annotated[int | None, Field(description="Optional sensor count along x.")] = None,
        y_count: Annotated[int | None, Field(description="Optional sensor count along y.")] = None,
        grid_spacing: Annotated[float | None, Field(description="Optional spacing hint used to derive x_count/y_count.")] = None,
        origin: Annotated[list[float] | None, Field(description="Optional grid origin [x, y, z].")] = None,
        rotation: Annotated[float | None, Field(description="Optional Agent orientation hint. Ignored; rectangular grids are axis-aligned.")] = None,
        grid_type: Annotated[str | None, Field(description="Optional Agent hint. Ignored.")] = None,
        garden_root: Annotated[str | None, Field(description="Optional Garden root path.")] = None,
        model_target: Annotated[dict[str, Any] | None, Field(description="Optional Honeybee model target.")] = None,
        host_target: Annotated[dict[str, Any] | None, Field(description="Optional Agent alias for model_target when attaching the SensorGrid to a Honeybee model.")] = None,
        attach_to_model: Annotated[bool, Field(description="When true, attach the grid to the model.")] = False,
        output_subdir: Annotated[str, Field(description="Garden-relative output folder.")] = "artifacts/radiance/sensors",
        return_object_dict: Annotated[bool, Field(description="Return the full SensorGrid object_dict.")] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance SensorGrid through a spelling alias."""
        _ = rotation
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
