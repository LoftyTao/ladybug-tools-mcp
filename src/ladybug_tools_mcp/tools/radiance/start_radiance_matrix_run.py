"""Start Radiance matrix recipe MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.run import start_radiance_matrix_run as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_start_matrix_simulation tool.'

    @mcp.tool(
        name="start_matrix_simulation",
        description=(
            "Start a background Radiance annual or matrix daylight recipe for "
            "a Honeybee model with attached SensorGrids and a WEA target. Use "
            "for annual-daylight, annual-irradiance, cumulative-radiation, and "
            "rfluxmtx calculations. Poll with radiance_poll_simulation before "
            "reading artifacts. Returns run_target, radiance_run_target, "
            "runtime_status through summary_view.status, poll_next, and "
            "report. Treat failed runtime_status as requiring report review."
        ),
        tags={
            "start",
            "radiance",
            "simulate",
            "poll",
        },
        timeout=60,
    )
    def start_radiance_matrix_run(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target with target_type=honeybee_model. Defaults to the Garden base model and should already have SensorGrids attached."),
        ] = None,
        calculation_type: Annotated[
            str,
            Field(description="Matrix calculation type: annual_daylight, annual_irradiance, or cumulative_radiation."),
        ] = "annual_daylight",
        wea_target: Annotated[
            dict[str, Any] | None,
            Field(description='Garden WEA target returned by radiance_create_wea_from_weather_file or radiance_create_ashrae_clear_sky_wea.'),
        ] = None,
        wea_path: Annotated[
            str | None,
            Field(description="Garden-relative .wea path for controlled workflows. Prefer wea_target."),
        ] = None,
        grid_filter: Annotated[
            str,
            Field(description="Honeybee Radiance grid-filter input. Use '*' for all attached SensorGrids or pass one SensorGrid identifier."),
        ] = "*",
        north: Annotated[float | None, Field(description="Optional north angle in degrees.")] = None,
        timestep: Annotated[int | None, Field(description="Optional recipe timestep.")] = None,
        schedule: Annotated[
            str | None,
            Field(description="Optional annual-daylight schedule file/path or schedule text accepted by the recipe."),
        ] = None,
        thresholds: Annotated[
            str | None,
            Field(description="Optional annual-daylight thresholds string accepted by the recipe."),
        ] = None,
        output_type: Annotated[
            str | None,
            Field(description="Optional annual-irradiance output-type, for example solar or visible."),
        ] = None,
        sky_density: Annotated[
            int | None,
            Field(description="Optional cumulative-radiation sky-density."),
        ] = None,
        min_sensor_count: Annotated[
            int | None,
            Field(description="Minimum sensor count per split grid. Defaults to 1 so small Agent test grids are not filtered out by the Radiance recipe default."),
        ] = 1,
        grid_metrics: Annotated[
            dict[str, Any] | None,
            Field(description="Optional annual-daylight grid-metrics input when needed by the recipe."),
        ] = None,
        radiance_parameters: Annotated[
            str | dict[str, Any] | None,
            Field(description='Optional Radiance parameters string or dictionary returned by radiance_create_parameters.'),
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
        """Start a Radiance matrix run."""
        return service(
            garden_root=garden_root,
            model_target=model_target,
            calculation_type=calculation_type,
            wea_target=wea_target,
            wea_path=wea_path,
            grid_filter=grid_filter,
            north=north,
            timestep=timestep,
            schedule=schedule,
            thresholds=thresholds,
            output_type=output_type,
            sky_density=sky_density,
            min_sensor_count=min_sensor_count,
            grid_metrics=grid_metrics,
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
        )
