"""Start the LEED daylight Option 2 Radiance recipe MCP tool."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    'Register the RAD_start_leed_daylight_option_two tool.'

    @mcp.tool(
        name="RAD_start_leed_daylight_option_two",
        description=(
            "Start a background Radiance LEED daylight Option 2 recipe for a "
            "Honeybee model with attached, ungrouped SensorGrids (empty "
            "group_identifier). Provide a WEA target "
            "from RAD_create_wea_from_weather_file or "
            "RAD_create_ashrae_clear_sky_wea. The recipe runs the 9AM and "
            "3PM point-in-time illuminance checks and evaluates LEED credits. "
            "Use glare_control_devices='glare-control' when the model has "
            "view-preserving automatic glare-control devices; use "
            "'no-glare-control' otherwise. Poll with RAD_poll_simulation "
            "then pass run_target to RAD_read_daylight_compliance. Returns run_target, "
            "radiance_run_target, and runtime_status through summary_view.status, "
            "poll_next, and report."
        ),
        tags={
            "start",
            "radiance",
            "simulate",
            "compliance",
            "leed",
            "poll",
        },
        timeout=60,
    )
    def start_leed_daylight_option_two(
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
                    "model and should already have SensorGrids attached."
                )
            ),
        ] = None,
        wea_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Garden WEA target returned by "
                    "RAD_create_wea_from_weather_file or "
                    "RAD_create_ashrae_clear_sky_wea. Required for LEED Option "
                    "2."
                )
            ),
        ] = None,
        grid_filter: Annotated[
            str,
            Field(
                description=(
                    "Honeybee Radiance grid-filter input. Use '*' for all "
                    "attached SensorGrids or pass a SensorGrid identifier or "
                    "pattern."
                )
            ),
        ] = "*",
        north: Annotated[
            float | None,
            Field(description="Optional north angle in degrees."),
        ] = None,
        min_sensor_count: Annotated[
            int,
            Field(
                description=(
                    "Minimum sensor count per redistributed batch; controls "
                    "how grids are split between workers."
                ),
                ge=1,
            ),
        ] = 1,
        glare_control_devices: Annotated[
            Literal["glare-control", "no-glare-control"],
            Field(
                description=(
                    "LEED recipe glare-control-devices enum. Use "
                    "'glare-control' when the model has view-preserving "
                    "automatic glare-control devices with manual override; "
                    "use 'no-glare-control' otherwise."
                )
            ),
        ] = "glare-control",
        radiance_parameters: Annotated[
            str | dict[str, Any] | None,
            Field(
                description=(
                    "Optional Radiance parameters string or dictionary returned "
                    "by RAD_create_parameters."
                )
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier. Omit to generate one."),
        ] = None,
        workers: Annotated[
            int | None,
            Field(description="Optional recipe worker count.", ge=1),
        ] = None,
        reload_old: Annotated[
            bool,
            Field(
                description=(
                    "Ask the recipe to reload existing results in the run "
                    "folder when available."
                )
            ),
        ] = False,
        silent: Annotated[
            bool,
            Field(description="Run the Radiance recipe silently."),
        ] = True,
    ) -> dict[str, Any]:
        """Start a LEED daylight Option 2 Radiance run."""
        from garden.radiance.compliance import (
            start_radiance_compliance_run as service,
        )

        return service(
            garden_root=garden_root,
            recipe_name="leed-daylight-option-two",
            model_target=model_target,
            wea_target=wea_target,
            weather_file_target=None,
            grid_filter=grid_filter,
            north=north,
            min_sensor_count=min_sensor_count,
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            recipe_options={"glare-control-devices": glare_control_devices},
        )
