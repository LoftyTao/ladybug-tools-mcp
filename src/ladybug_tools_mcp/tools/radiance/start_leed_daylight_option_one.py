"""Start the LEED daylight Option 1 Radiance recipe MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    'Register the RAD_start_leed_daylight_option_one tool.'

    @mcp.tool(
        name="RAD_start_leed_daylight_option_one",
        description=(
            "Start a background Radiance LEED daylight Option 1 recipe for a "
            "Honeybee model with attached SensorGrids. Provide a WEA target "
            "from RAD_create_wea_from_weather_file or "
            "RAD_create_ashrae_clear_sky_wea. The recipe applies aperture "
            "group blinds, evaluates annual sDA and ASE, and calculates LEED "
            "daylight credits using the 2% rule. diffuse_transmission is the "
            "unitless diffuse light transmission fraction of the blinds; "
            "specular_transmission is the unitless specular light transmission "
            "fraction. Both accept values from 0.0001 to 1. Poll with "
            "RAD_poll_simulation while summary_view.poll_next is present, "
            "then pass run_target to RAD_read_daylight_compliance. Returns "
            "run_target, radiance_run_target, and runtime_status through "
            "summary_view.status, poll_next, and report."
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
    def start_leed_daylight_option_one(
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
                    "RAD_create_ashrae_clear_sky_wea. It must reference an "
                    "annual hourly weather file and is required for LEED "
                    "Option 1."
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
        diffuse_transmission: Annotated[
            float,
            Field(
                description=(
                    "Diffuse light transmission fraction of the aperture group "
                    "blinds. The native recipe accepts 0.0001 to 1 and defaults "
                    "to 0.05 (5%)."
                ),
                ge=0.0001,
                le=1,
            ),
        ] = 0.05,
        specular_transmission: Annotated[
            float,
            Field(
                description=(
                    "Specular light transmission fraction of the aperture group "
                    "blinds. The native recipe accepts 0.0001 to 1 and defaults "
                    "to 0.0001 (0.01%)."
                ),
                ge=0.0001,
                le=1,
            ),
        ] = 0.0001,
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
        """Start a LEED daylight Option 1 Radiance run."""
        from garden.radiance.compliance import (
            start_radiance_compliance_run as service,
        )

        return service(
            garden_root=garden_root,
            recipe_name="leed-daylight-option-one",
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
            recipe_options={
                "diffuse-transmission": diffuse_transmission,
                "specular-transmission": specular_transmission,
            },
        )
