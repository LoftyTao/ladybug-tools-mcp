"""Create a Honeybee Radiance SensorGrid from a Honeybee object surface."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.assets import create_radiance_sensor_grid_from_object as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_create_sensor_grid_from_object tool.'

    @mcp.tool(
        name="create_sensor_grid_from_object",
        description=(
            "Create a Honeybee Radiance SensorGrid by sampling the surface of "
            "a Honeybee Face, Aperture, Door, Shade, shading panel, PV panel, "
            "or solar collector target. Use this for object-hosted grids, "
            "shade irradiance sensors, and PV solar-potential studies. Pass "
            "object_target from Honeybee object search or shade creation plus "
            "garden_root. Set attach_to_model=true to attach the grid for "
            "Radiance grid or annual-irradiance recipes. This samples existing "
            "geometry and does not create new Honeybee objects."
        ),
        tags={
            "radiance",
            "sensor-grid",
            "author",
            "object-surface",
        },
        timeout=60,
    )
    def create_radiance_sensor_grid_from_object(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        object_target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee face, aperture, door, or shade target to sample into a Radiance SensorGrid. Pass matches[i].target from honeybee_search_model_objects or target from honeybee_create_shade.'
            ),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Stable SensorGrid identifier. Defaults to object_sensor_grid."),
        ] = None,
        grid_spacing: Annotated[
            float | None,
            Field(description="Optional approximate spacing in model units used to derive x_count/y_count."),
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
