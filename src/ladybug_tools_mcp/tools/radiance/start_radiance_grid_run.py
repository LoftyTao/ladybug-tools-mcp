"""Start Radiance grid recipe MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.run import start_radiance_grid_run as service


def _requires_radiance_sky_file(calculation_type: str) -> bool:
    return calculation_type.strip().lower().replace("-", "_").replace(" ", "_") == "point_in_time"


def register(mcp: FastMCP) -> None:
    """Register the start_radiance_grid_run tool."""

    @mcp.tool(
        name="start_radiance_grid_run",
        description="Start a background Radiance daylight grid recipe for a Honeybee model with attached SensorGrids and return immediately with target, radiance_run_target, run_target, and summary_view.poll_next.arguments. Use for point-in-time-grid, daylight-factor, rtrace daylight calculations; poll get_radiance_run instead of waiting for the recipe.",
        tags={
            "honeybee-radiance",
            "radiance",
            "run-radiance",
            "daylight",
            "grid",
            "sensor-grid",
            "point-in-time-grid",
            "daylight-factor",
            "rtrace",
            "recipe",
            "background",
            "agent",
            "write",
            "safe",
        },
        timeout=60,
    )
    def start_radiance_grid_run(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target. Defaults to the Garden base model and should already have SensorGrids attached."),
        ] = None,
        calculation_type: Annotated[
            str,
            Field(description="Grid calculation type: point_in_time or daylight_factor."),
        ] = "point_in_time",
        radiance_sky_file: Annotated[
            dict[str, Any] | None,
            Field(description="Radiance sky file target from create_cie_standard_sky, create_climate_based_sky, create_radiance_sky, or create_radiance_sky_file. Required for point_in_time runs."),
        ] = None,
        grid_filter: Annotated[
            str,
            Field(description="Honeybee Radiance grid-filter input. Use '*' for all attached SensorGrids."),
        ] = "*",
        sensor_grid_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional SensorGrid target. When supplied and grid_filter is '*', its identifier is used as grid-filter."),
        ] = None,
        metric: Annotated[
            str,
            Field(description="Point-in-time metric, usually illuminance, irradiance, luminance, or radiance depending on recipe."),
        ] = "illuminance",
        min_sensor_count: Annotated[
            int | None,
            Field(description="Minimum sensor count per split grid. Defaults to 1 so small Agent test grids are not filtered out by the Radiance recipe default."),
        ] = 1,
        grid_metrics: Annotated[
            dict[str, Any] | None,
            Field(description="Optional daylight-factor grid-metrics input when needed by the recipe."),
        ] = None,
        radiance_parameters: Annotated[
            str | dict[str, Any] | None,
            Field(description="Optional Radiance parameters string or a dictionary with radiance_parameters."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier. Omit to generate one."),
        ] = None,
        workers: Annotated[int | None, Field(description="Optional recipe worker count.")] = None,
        reload_old: Annotated[
            bool,
            Field(description="Ask the recipe to reload existing results in the run folder when available."),
        ] = False,
        silent: Annotated[bool, Field(description="Run the Radiance recipe silently.")] = True,
    ) -> dict[str, Any]:
        """Start a Radiance grid run."""
        if _requires_radiance_sky_file(calculation_type) and radiance_sky_file is None:
            raise ValueError("Provide radiance_sky_file for point_in_time Radiance grid runs.")
        if grid_filter == "*" and isinstance(sensor_grid_target, dict):
            if sensor_grid_target.get("target_type") != "radiance_sensor_grid":
                raise ValueError("sensor_grid_target must be a radiance_sensor_grid target.")
            identifier = sensor_grid_target.get("identifier")
            if identifier:
                grid_filter = str(identifier)
        return service(
            garden_root=garden_root,
            model_target=model_target,
            calculation_type=calculation_type,
            sky_file_target=radiance_sky_file,
            sky=None,
            grid_filter=grid_filter,
            metric=metric,
            min_sensor_count=min_sensor_count,
            grid_metrics=grid_metrics,
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
        )
