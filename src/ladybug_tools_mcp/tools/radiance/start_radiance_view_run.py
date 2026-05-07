"""Start Radiance view recipe MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.run import start_radiance_view_run as service
from garden.store import list_garden_artifacts


def _view_filter_from_target(view_target: dict[str, Any] | None) -> str | None:
    if not isinstance(view_target, dict):
        return None
    target = view_target.get("target") if isinstance(view_target.get("target"), dict) else view_target
    identifier = target.get("identifier") or target.get("full_id") or target.get("name")
    return str(identifier) if identifier else None


def _latest_sky_file_target(garden_root: str) -> dict[str, Any] | None:
    listed = list_garden_artifacts(
        garden_root=garden_root,
        artifact_type="radiance_sky_file",
    )
    matches = listed.get("matches", [])
    if not matches:
        return None
    artifact = matches[-1]
    garden_target = listed.get("summary_view", {}).get("garden_target", {})
    path = str(artifact.get("path") or "")
    return {
        "target_type": "radiance_sky_file",
        "domain": "honeybee_radiance",
        "garden_id": garden_target.get("garden_id"),
        "identifier": str(artifact.get("name") or path.rsplit("/", 1)[-1].rsplit(".", 1)[0]),
        "path": path,
    }


def _normalize_model_target(model_target: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(model_target, dict):
        return None
    target = model_target.get("target") if isinstance(model_target.get("target"), dict) else model_target
    if target.get("target_type") != "model":
        return None
    if target.get("domain") is None:
        target = dict(target)
        target["domain"] = "honeybee"
    if not target.get("path") and target.get("model_identifier"):
        target = dict(target)
        target["path"] = f"models/honeybee/{target['model_identifier']}.hbjson"
    return target


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
            Field(description="Optional Honeybee model target. Defaults to the Garden base model and should already have Views attached."),
        ] = None,
        calculation_type: Annotated[
            str,
            Field(description="View calculation type. Currently point_in_time."),
        ] = "point_in_time",
        sky_file_target: Annotated[
            dict[str, Any] | None,
            Field(description="Radiance sky_file target from create_cie_standard_sky or create_climate_based_sky."),
        ] = None,
        radiance_sky_file: Annotated[
            dict[str, Any] | None,
            Field(description="Alias for sky_file_target accepted for Agent compatibility."),
        ] = None,
        radiance_sky_file_target: Annotated[
            dict[str, Any] | None,
            Field(description="Alias for sky_file_target accepted for Agent compatibility."),
        ] = None,
        sky_file: Annotated[
            dict[str, Any] | None,
            Field(description="Alias for sky_file_target accepted for Agent compatibility."),
        ] = None,
        sky_target: Annotated[
            dict[str, Any] | None,
            Field(description="Alias for sky_file_target accepted for Agent compatibility."),
        ] = None,
        radiance_sky_target: Annotated[
            dict[str, Any] | None,
            Field(description="Alias for sky_file_target accepted for Agent compatibility."),
        ] = None,
        sky: Annotated[
            str | None,
            Field(description="Inline Radiance sky text fallback. Prefer sky_file_target for Garden workflows."),
        ] = None,
        view_filter: Annotated[
            str,
            Field(description="Honeybee Radiance view-filter input. Use '*' for all attached Views or one View identifier."),
        ] = "*",
        view_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional radiance_view target. When supplied and view_filter is '*', its identifier is used as the view-filter."),
        ] = None,
        radiance_view_target: Annotated[
            dict[str, Any] | None,
            Field(description="Alias for view_target accepted for Agent compatibility."),
        ] = None,
        radiance_view: Annotated[
            dict[str, Any] | None,
            Field(description="Alias for view_target accepted for Agent compatibility."),
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
        output_format: Annotated[
            str | None,
            Field(description="Optional Agent image-format hint such as hdr accepted for compatibility. Point-in-time view runs produce HDR output."),
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
        identifier: Annotated[
            str | None,
            Field(description="Alias for run_id accepted for Agent compatibility."),
        ] = None,
        workers: Annotated[int | None, Field(description="Optional recipe worker count.")] = None,
        reload_old: Annotated[
            bool,
            Field(description="Ask the recipe to reload existing results in the run folder when available."),
        ] = False,
        silent: Annotated[bool, Field(description="Run the Radiance recipe silently.")] = True,
    ) -> dict[str, Any]:
        """Start a Radiance view run."""
        _ = output_format
        model_target = _normalize_model_target(model_target)
        if view_target is None and radiance_view_target is not None:
            view_target = radiance_view_target
        if view_target is None and radiance_view is not None:
            view_target = radiance_view
        if view_filter == "*":
            view_filter = _view_filter_from_target(view_target) or view_filter
        if sky_file_target is None and radiance_sky_file is not None:
            sky_file_target = radiance_sky_file
        if sky_file_target is None and radiance_sky_file_target is not None:
            sky_file_target = radiance_sky_file_target
        if sky_file_target is None and sky_file is not None:
            sky_file_target = sky_file
        if sky_file_target is None and sky_target is not None:
            sky_file_target = sky_target
        if sky_file_target is None and radiance_sky_target is not None:
            sky_file_target = radiance_sky_target
        if sky_file_target is None and sky is None:
            sky_file_target = _latest_sky_file_target(garden_root)
        if radiance_parameters is None and radiance_parameters_target is not None:
            radiance_parameters = radiance_parameters_target
        if run_id is None and identifier is not None:
            run_id = identifier
        return service(
            garden_root=garden_root,
            model_target=model_target,
            calculation_type=calculation_type,
            sky_file_target=sky_file_target,
            sky=sky,
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
