"""Start Radiance view recipe MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.run import start_radiance_view_run as service


def _view_filter_from_target(view_target: dict[str, Any] | None) -> str | None:
    if not isinstance(view_target, dict):
        return None
    if view_target.get("target_type") != "radiance_view":
        raise ValueError("view_target must be a radiance_view target.")
    identifier = view_target.get("identifier")
    return str(identifier) if identifier else None


def register(mcp: FastMCP) -> None:
    """Register the start_radiance_view_run tool."""

    @mcp.tool(
        name="start_radiance_view_run",
        description="Start a background Radiance daylight view recipe for a Honeybee model with attached Views and return immediately with target, radiance_run_target, run_target, and summary_view.poll_next.arguments. Use for point-in-time-view, rpict image calculations; poll get_radiance_run instead of waiting for the recipe. You may pass view_filter or a radiance_view target from create_radiance_view as view_target. You may pass radiance_parameters or the radiance_parameters target/result from create_radiance_parameters.",
        tags={
            "honeybee-radiance",
            "radiance",
            "run-radiance",
            "daylight",
            "view",
            "image",
            "point-in-time-view",
            "rpict",
            "recipe",
            "background",
            "agent",
            "write",
            "safe",
        },
        timeout=60,
    )
    def start_radiance_view_run(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target with target_type=honeybee_model. Defaults to the Garden base model and should already have Views attached."),
        ] = None,
        calculation_type: Annotated[
            str,
            Field(description="View calculation type. Currently point_in_time."),
        ] = "point_in_time",
        radiance_sky_file: Annotated[
            dict[str, Any] | None,
            Field(description="Radiance sky file target from create_cie_standard_sky, create_climate_based_sky, create_radiance_sky, or create_radiance_sky_file."),
        ] = None,
        view_filter: Annotated[
            str,
            Field(description="Honeybee Radiance view-filter input. Use '*' for all attached Views or one View identifier."),
        ] = "*",
        view_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional radiance_view target. When supplied and view_filter is '*', its identifier is used as the view-filter."),
        ] = None,
        metric: Annotated[
            str,
            Field(description="Point-in-time image metric, usually luminance or radiance."),
        ] = "luminance",
        resolution: Annotated[
            int | None,
            Field(description="Optional image resolution passed to the recipe."),
        ] = None,
        skip_overture: Annotated[
            bool | None,
            Field(description="Optional skip-overture recipe flag."),
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
        """Start a Radiance view run."""
        if radiance_sky_file is None:
            raise ValueError("Provide radiance_sky_file for Radiance view runs.")
        if view_filter == "*":
            view_filter = _view_filter_from_target(view_target) or view_filter
        return service(
            garden_root=garden_root,
            model_target=model_target,
            calculation_type=calculation_type,
            sky_file_target=radiance_sky_file,
            sky=None,
            view_filter=view_filter,
            metric=metric,
            resolution=resolution,
            skip_overture=skip_overture,
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
        )
