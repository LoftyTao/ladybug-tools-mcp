"""Create a Honeybee Radiance SensorGrid from a Honeybee object surface."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.assets import create_radiance_sensor_grid_from_object as service


def register(mcp: FastMCP) -> None:
    """Register the create_radiance_sensor_grid_from_object tool."""

    @mcp.tool(
        name="create_radiance_sensor_grid_from_object",
        description="Create a Honeybee Radiance SensorGrid from object surface geometry by sampling a Honeybee face, aperture, door, shade, shading panel, PV panel, or solar collector object target. Use this for object-hosted surface grids, shade-hosted irradiance sensors, PV shade irradiance / solar-potential studies, and user requests like 'put the sensor grid on the shading panel itself, not on the room workplane'. Pass object_target from search_honeybee_model_objects or a create_honeybee_shade result, plus garden_root. Set attach_to_model=true to attach the grid to the Honeybee model for Radiance grid or annual-irradiance recipes.",
        tags={
            "honeybee-radiance",
            "radiance",
            "sensor-grid",
            "surface-grid",
            "object-hosted",
            "object-grid",
            "from-object",
            "shade",
            "shading-panel",
            "pv-panel",
            "solar-potential",
            "face",
            "irradiance",
            "garden-mode",
            "model",
            "target",
            "artifact",
            "write",
            "safe",
        },
        timeout=60,
    )
    def create_radiance_sensor_grid_from_object(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path string containing garden.json."),
        ],
        object_target: Annotated[
            dict[str, Any],
            Field(
                description="Required Honeybee face, aperture, door, or shade target. Pass matches[i].target from search_honeybee_model_objects or target from create_honeybee_shade."
            ),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Stable SensorGrid identifier. Defaults to object_sensor_grid."),
        ] = None,
        shade_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Agent alias for object_target when the source object is a Shade."),
        ] = None,
        surface_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Agent alias for object_target for face/aperture/door/shade surfaces."),
        ] = None,
        grid_spacing: Annotated[
            float | None,
            Field(description="Optional approximate spacing in model units used to derive x_count/y_count."),
        ] = None,
        spacing: Annotated[
            float | None,
            Field(description="Alias for grid_spacing accepted for Agent compatibility."),
        ] = None,
        x_count: Annotated[
            int | None,
            Field(description="Optional number of samples along the local object x direction."),
        ] = None,
        y_count: Annotated[
            int | None,
            Field(description="Optional number of samples along the local object y direction."),
        ] = None,
        offset: Annotated[
            float,
            Field(description="Offset distance along the object normal. Defaults to 0.01 model units."),
        ] = 0.01,
        flip_direction: Annotated[
            bool,
            Field(description="When true, flip the sensor direction and offset to the reverse normal."),
        ] = False,
        display_name: Annotated[
            str | None,
            Field(description="Optional display name."),
        ] = None,
        group_identifier: Annotated[
            str | None,
            Field(description="Optional Radiance group identifier."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target. Defaults to the Garden base model."),
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
        """Create a Honeybee Radiance SensorGrid from an object surface."""
        if identifier is None:
            identifier = "object_sensor_grid"
        if shade_target is not None:
            object_target = shade_target
        if surface_target is not None:
            object_target = surface_target
        if grid_spacing is None and spacing is not None:
            grid_spacing = spacing
        return service(
            identifier=identifier,
            object_target=object_target,
            garden_root=garden_root,
            grid_spacing=grid_spacing,
            x_count=x_count,
            y_count=y_count,
            offset=offset,
            flip_direction=flip_direction,
            display_name=display_name,
            group_identifier=group_identifier,
            model_target=model_target,
            attach_to_model=attach_to_model,
            output_subdir=output_subdir,
            return_object_dict=return_object_dict,
        )
