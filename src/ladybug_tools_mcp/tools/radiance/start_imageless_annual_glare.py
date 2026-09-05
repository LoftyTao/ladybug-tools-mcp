"""Start the imageless annual glare Radiance recipe MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.tools.radiance.start_radiance_view_run import (
    _view_filter_from_target,
)


def register(mcp: FastMCP) -> None:
    """Register the RAD_start_imageless_annual_glare tool."""

    @mcp.tool(
        name="RAD_start_imageless_annual_glare",
        description=(
            "Start the native imageless-annual-glare Radiance recipe in the "
            "background for a Honeybee model with attached SensorGrids and at "
            "least one attached View. Provide a WEA target or Garden-relative "
            "WEA path. The recipe produces annual DGP matrices and glare "
            "autonomy (GA) outputs; dynamic Radiance states on the model are "
            "handled by the native recipe. Poll with RAD_poll_simulation, then "
            "pass the completed run_target to RAD_summarize_glare_metrics."
        ),
        tags={
            "start",
            "radiance",
            "simulate",
            "glare",
            "poll",
        },
        timeout=60,
    )
    def start_imageless_annual_glare(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually "
                    "GD_create['garden_root']; required when saving or reading "
                    "Garden targets."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Honeybee model target with "
                    "target_type=honeybee_model. Defaults to the Garden base "
                    "model."
                )
            ),
        ] = None,
        wea_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Garden WEA target returned by "
                    "RAD_create_wea_from_weather_file or "
                    "RAD_create_ashrae_clear_sky_wea."
                )
            ),
        ] = None,
        wea_path: Annotated[
            str | None,
            Field(description="Garden-relative .wea path. Prefer wea_target."),
        ] = None,
        view_filter: Annotated[
            str,
            Field(
                description=(
                    "Radiance View identifier or pattern. Use '*' for all "
                    "attached Views."
                )
            ),
        ] = "*",
        view_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional radiance_view target used to select one View."),
        ] = None,
        grid_filter: Annotated[
            str,
            Field(
                description=(
                    "SensorGrid identifier or pattern. Use '*' for all "
                    "attached SensorGrids."
                )
            ),
        ] = "*",
        north: Annotated[
            float | None,
            Field(description="Optional north angle in degrees."),
        ] = None,
        schedule: Annotated[
            str | None,
            Field(
                description=(
                    "Optional annual occupancy schedule file/path or schedule "
                    "text accepted by the recipe."
                )
            ),
        ] = None,
        dgp_threshold: Annotated[
            float,
            Field(
                description="DGP threshold used to calculate glare autonomy.",
                ge=0,
                le=1,
            ),
        ] = 0.4,
        luminance_factor: Annotated[
            float,
            Field(
                description=(
                    "Luminance threshold in cd/m2 used to detect glare sources."
                ),
                gt=0,
            ),
        ] = 2000.0,
        min_sensor_count: Annotated[
            int,
            Field(description="Minimum sensors per redistributed grid batch.", ge=1),
        ] = 1,
        radiance_parameters: Annotated[
            str | dict[str, Any] | None,
            Field(
                description=(
                    "Optional Radiance parameters string or RAD_create_parameters "
                    "result."
                )
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier."),
        ] = None,
        workers: Annotated[
            int | None,
            Field(description="Optional recipe worker count.", ge=1),
        ] = None,
        reload_old: Annotated[
            bool,
            Field(
                description=(
                    "Reload existing recipe results in the run folder when "
                    "available."
                )
            ),
        ] = False,
        silent: Annotated[
            bool,
            Field(description="Run the Radiance recipe silently."),
        ] = True,
    ) -> dict[str, Any]:
        """Start an imageless annual glare Radiance run."""
        from garden.radiance.run import (
            start_radiance_imageless_annual_glare as service,
        )

        if view_filter == "*":
            view_filter = _view_filter_from_target(view_target) or view_filter
        return service(
            garden_root=garden_root,
            model_target=model_target,
            wea_target=wea_target,
            wea_path=wea_path,
            view_filter=view_filter,
            grid_filter=grid_filter,
            north=north,
            schedule=schedule,
            dgp_threshold=dgp_threshold,
            luminance_factor=luminance_factor,
            min_sensor_count=min_sensor_count,
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
        )
