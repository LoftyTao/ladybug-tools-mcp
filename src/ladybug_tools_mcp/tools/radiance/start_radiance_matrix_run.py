"""Start Radiance matrix recipe MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.run import start_radiance_matrix_run as service


def _grid_filter_from_targets(sensor_grids: list[dict[str, Any]] | None) -> str | None:
    if not sensor_grids:
        return None
    target = sensor_grids[0]
    if isinstance(target, dict) and isinstance(target.get("target"), dict):
        target = target["target"]
    if not isinstance(target, dict):
        return None
    identifier = target.get("identifier") or target.get("full_id") or target.get("name")
    return str(identifier) if identifier else None


def register(mcp: FastMCP) -> None:
    """Register the start_radiance_matrix_run tool."""

    @mcp.tool(
        name="start_radiance_matrix_run",
        description="Start a background Radiance annual/matrix daylight recipe for a Honeybee model with attached SensorGrids and a WEA target. Use for annual-daylight, annual-irradiance, cumulative-radiation, rfluxmtx calculations; returns immediately and should be polled with get_radiance_run.",
        tags={
            "honeybee-radiance",
            "radiance",
            "run-radiance",
            "daylight",
            "matrix",
            "annual",
            "annual-daylight",
            "annual-irradiance",
            "cumulative-radiation",
            "rfluxmtx",
            "wea",
            "recipe",
            "background",
            "agent",
            "write",
            "safe",
        },
        timeout=60,
    )
    def start_radiance_matrix_run(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target. Defaults to the Garden base model and should already have SensorGrids attached."),
        ] = None,
        calculation_type: Annotated[
            str,
            Field(description="Matrix calculation type: annual_daylight, annual_irradiance, or cumulative_radiation."),
        ] = "annual_daylight",
        recipe: Annotated[
            str | None,
            Field(description="Alias for calculation_type accepted for Agent compatibility."),
        ] = None,
        recipe_type: Annotated[
            str | None,
            Field(description="Alias for calculation_type accepted for Agent compatibility."),
        ] = None,
        wea_target: Annotated[
            dict[str, Any] | None,
            Field(description="Garden WEA target returned by create_wea_from_weather_file or create_ashrae_clear_sky_wea."),
        ] = None,
        wea_path: Annotated[
            str | None,
            Field(description="Garden-relative .wea path fallback for controlled tests. Prefer wea_target."),
        ] = None,
        grid_filter: Annotated[
            str,
            Field(description="Honeybee Radiance grid-filter input. Use '*' for all attached SensorGrids."),
        ] = "*",
        sensor_grids: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional SensorGrid targets. When supplied and grid_filter is '*', the first target identifier is used as grid-filter."),
        ] = None,
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
        output_subdir: Annotated[
            str | None,
            Field(description="Accepted for Agent compatibility; Radiance recipe run folders are managed by the Garden."),
        ] = None,
    ) -> dict[str, Any]:
        """Start a Radiance matrix run."""
        if recipe is None and recipe_type is not None:
            recipe = recipe_type
        if recipe is not None:
            calculation_type = recipe
        if grid_filter == "*":
            grid_filter = _grid_filter_from_targets(sensor_grids) or grid_filter
        if radiance_parameters is None and radiance_parameters_target is not None:
            radiance_parameters = radiance_parameters_target
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
