"""Start the annual daylight EN 17037 Radiance recipe MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    'Register the RAD_start_annual_daylight_en17037 tool.'

    @mcp.tool(
        name="RAD_start_annual_daylight_en17037",
        description=(
            "Start a background Radiance annual daylight EN 17037 recipe for "
            "a Honeybee model with attached, ungrouped SensorGrids. Use grids with meshes "
            "for area-weighted criteria; point-only grids use sensor counts. "
            "RAD_create_sensor_grid_from_object preserves the mesh. Provide a Garden "
            "weather_file target returned by EP_import_local_weather or "
            "EP_search_weather_files; its epw_path must reference an annual "
            "hourly EPW file. Optional grid_metrics and thresholds configure "
            "the accompanying annual metrics. Poll with RAD_poll_simulation, "
            "then pass run_target to RAD_read_daylight_compliance. Returns "
            "run_target, radiance_run_target, and runtime_status through "
            "summary_view.status, poll_next, and report."
        ),
        tags={
            "start",
            "radiance",
            "simulate",
            "compliance",
            "en17037",
            "poll",
        },
        timeout=60,
    )
    def start_annual_daylight_en17037(
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
        weather_file_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Garden weather_file target returned by "
                    "EP_import_local_weather or EP_search_weather_files. "
                    "It must include a Garden-relative epw_path for an annual "
                    "hourly EPW file. Required for EN 17037."
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
        grid_metrics: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional native grid-metrics input for additional grid summaries."
            ),
        ] = None,
        thresholds: Annotated[
            str | None,
            Field(description=(
                "Optional DA/UDI threshold string, such as '-t 300 -lt 100 -ut 3000'. "
                "Changes the accompanying annual metrics, not EN 17037 criteria."
            )),
        ] = None,
    ) -> dict[str, Any]:
        """Start an annual daylight EN 17037 Radiance run."""
        from garden.radiance.compliance import (
            start_radiance_compliance_run as service,
        )

        return service(
            garden_root=garden_root,
            recipe_name="annual-daylight-en17037",
            model_target=model_target,
            weather_file_target=weather_file_target,
            wea_target=None,
            grid_filter=grid_filter,
            north=north,
            min_sensor_count=min_sensor_count,
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            recipe_options={"grid-metrics": grid_metrics, "thresholds": thresholds},
        )
