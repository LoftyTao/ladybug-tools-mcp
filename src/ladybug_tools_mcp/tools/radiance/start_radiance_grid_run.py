"""Start Radiance grid recipe MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.run import start_radiance_grid_run as service


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
        sky_file_target: Annotated[
            dict[str, Any] | None,
            Field(description="Radiance sky_file target from create_cie_standard_sky or create_climate_based_sky for point_in_time runs."),
        ] = None,
        sky_file: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Agent alias for sky_file_target."),
        ] = None,
        sky_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Agent alias for sky_file_target."),
        ] = None,
        radiance_sky_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Agent alias for sky_file_target."),
        ] = None,
        radiance_sky_file_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Agent alias for sky_file_target."),
        ] = None,
        radiance_sky_file: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Agent alias for sky_file_target."),
        ] = None,
        sky: Annotated[
            str | None,
            Field(description="Inline Radiance sky text fallback. Prefer sky_file_target for Garden workflows."),
        ] = None,
        grid_filter: Annotated[
            str,
            Field(description="Honeybee Radiance grid-filter input. Use '*' for all attached SensorGrids."),
        ] = "*",
        sensor_grid_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional SensorGrid target. When supplied and grid_filter is '*', its identifier is used as grid-filter."),
        ] = None,
        radiance_sensor_grid_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Agent alias for sensor_grid_target."),
        ] = None,
        sensorgrid_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Agent alias for sensor_grid_target."),
        ] = None,
        radiance_sensor_grid: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Agent alias for sensor_grid_target."),
        ] = None,
        metric: Annotated[
            str,
            Field(description="Point-in-time metric, usually illuminance, irradiance, luminance, or radiance depending on recipe."),
        ] = "illuminance",
        grid_type: Annotated[
            str | None,
            Field(description="Optional Agent alias for metric, for example illuminance."),
        ] = None,
        grid_run_mode: Annotated[
            str | None,
            Field(description="Optional Agent alias for metric, for example illuminance."),
        ] = None,
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
            Field(description="Optional Radiance parameters string or full create_radiance_parameters result."),
        ] = None,
        radiance_parameters_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional radiance_parameters target from create_radiance_parameters. Alias for radiance_parameters."),
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
        if sky_file_target is None and sky_file is not None:
            sky_file_target = sky_file
        if sky_file_target is None and sky_target is not None:
            sky_file_target = sky_target
        if sky_file_target is None and radiance_sky_target is not None:
            sky_file_target = radiance_sky_target
        if sky_file_target is None and radiance_sky_file_target is not None:
            sky_file_target = radiance_sky_file_target
        if sky_file_target is None and radiance_sky_file is not None:
            sky_file_target = radiance_sky_file
        if sky_file_target is not None and sky is not None:
            sky = None
        if sensor_grid_target is None and radiance_sensor_grid_target is not None:
            sensor_grid_target = radiance_sensor_grid_target
        if sensor_grid_target is None and sensorgrid_target is not None:
            sensor_grid_target = sensorgrid_target
        if sensor_grid_target is None and radiance_sensor_grid is not None:
            sensor_grid_target = radiance_sensor_grid
        if grid_filter == "*" and isinstance(sensor_grid_target, dict):
            target = sensor_grid_target.get("target") if isinstance(sensor_grid_target.get("target"), dict) else sensor_grid_target
            identifier = target.get("identifier") or target.get("full_id") or target.get("name")
            if identifier:
                grid_filter = str(identifier)
        if grid_type is not None:
            metric = grid_type
        if grid_run_mode is not None:
            metric = grid_run_mode
        if radiance_parameters is None and radiance_parameters_target is not None:
            radiance_parameters = radiance_parameters_target
        return service(
            garden_root=garden_root,
            model_target=model_target,
            calculation_type=calculation_type,
            sky_file_target=sky_file_target,
            sky=sky,
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
