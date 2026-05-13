"""Edit Honeybee Model MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.edit import edit_honeybee_model as service
from garden.radiance.assets import (
    attach_radiance_sensor_grids_to_model,
    attach_radiance_views_to_model,
)


def register(mcp: FastMCP) -> None:
    """Register the edit_honeybee_model tool."""

    @mcp.tool(
        name="edit_honeybee_model",
        description="Edit a Honeybee Model display name, user data, units, tolerance, angle tolerance, model-level electric load center, and append complete Honeybee Room, Face, Aperture, Door, or Shade object dictionaries while preserving its Garden persistence path. Requires garden_root and a Honeybee model target; create_honeybee_room already writes rooms to the model, so do not use edit_honeybee_model.add_objects to re-add rooms created by create_honeybee_room. Do not pass arguments null or {}.",
        tags={
            "honeybee-core",
            "garden-mode",
            "model",
            "metadata",
            "user-data",
            "units",
            "electric-load-center",
            "pv",
            "photovoltaic",
            "add-objects",
            "remove-objects",
            "display-name",
            "write",
            "safe",
        },
        timeout=20,
    )
    def edit_honeybee_model(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Required Honeybee model target dict from create_honeybee_model, get_base_honeybee_model, or list_garden_models; not full model body."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Alias for target accepted for Agent compatibility."),
        ] = None,
        display_name: Annotated[
            str | None, Field(description="Optional updated display name.")
        ] = None,
        user_data: Annotated[
            dict[str, Any] | None,
            Field(description="Optional replacement user_data dictionary."),
        ] = None,
        units: Annotated[
            str | None, Field(description="Optional updated Honeybee model units.")
        ] = None,
        tolerance: Annotated[
            float | None, Field(description="Optional updated model tolerance.")
        ] = None,
        angle_tolerance: Annotated[
            float | None, Field(description="Optional updated model angle tolerance.")
        ] = None,
        electric_load_center: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy ElectricLoadCenter dict or Garden Properties Library electric_load_center target from create_electric_load_center, used for PV inverter/load-center settings."
            ),
        ] = None,
        add_objects: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Optional complete Honeybee object dictionaries to append to the model. Supports Room, Face, Aperture, Door, and Shade dicts; not typed targets, not create_honeybee_room.target, and not search_honeybee_model_objects matches[i].target. Do not use this to add rooms already created by create_honeybee_room."
            ),
        ] = None,
        add_sensor_grids: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Agent compatibility path for attaching existing radiance_sensor_grid targets to model Radiance properties. Prefer create_radiance_sensor_grid.attach_to_model=true when creating new grids."
            ),
        ] = None,
        radiance_sensor_grid_target: Annotated[
            dict[str, Any] | None,
            Field(description="Single radiance_sensor_grid target alias for add_sensor_grids accepted for Agent compatibility."),
        ] = None,
        add_radiance_views: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Agent compatibility path for attaching existing radiance_view targets to model Radiance properties. Prefer create_radiance_view.attach_to_model=true when creating new views."),
        ] = None,
        radiance_view_target: Annotated[
            dict[str, Any] | None,
            Field(description="Single radiance_view target alias for add_radiance_views accepted for Agent compatibility."),
        ] = None,
        remove_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Optional Honeybee typed targets from search_honeybee_model_objects to remove from the model. Only top-level Room and orphaned Face, Aperture, Door, and Shade targets are supported."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool | None,
            Field(
                description="Optional Agent compatibility hint accepted and ignored; edit_honeybee_model always keeps normal compact/target-first returns."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Edit a Honeybee Model."""
        if target is None and model_target is not None:
            target = model_target
        if target is None:
            raise ValueError("Provide target or model_target.")
        if add_sensor_grids is None and radiance_sensor_grid_target is not None:
            add_sensor_grids = [radiance_sensor_grid_target]
        if add_radiance_views is None and radiance_view_target is not None:
            add_radiance_views = [radiance_view_target]
        has_core_edits = any(
            value is not None
            for value in (
                display_name,
                user_data,
                units,
                tolerance,
                angle_tolerance,
                electric_load_center,
                add_objects,
                remove_targets,
            )
        )
        result: dict[str, Any]
        if has_core_edits:
            result = service(
                garden_root=garden_root,
                target=target,
                display_name=display_name,
                user_data=user_data,
                units=units,
                tolerance=tolerance,
                angle_tolerance=angle_tolerance,
                electric_load_center=electric_load_center,
                add_objects=add_objects,
                remove_targets=remove_targets,
            )
            target = result.get("target") or result.get("model_target") or target
        else:
            result = {
                "target": target,
                "model_target": target,
                "summary_view": {"model_identifier": target.get("identifier")},
            }
        if add_sensor_grids:
            attachment = attach_radiance_sensor_grids_to_model(
                garden_root=garden_root,
                model_target=target,
                sensor_grid_targets=add_sensor_grids,
            )
            result["target"] = attachment["target"]
            result["model_target"] = attachment["model_target"]
            result["radiance_sensor_grid_attachment"] = attachment
            result.setdefault("summary_view", {}).update(
                attachment.get("summary_view", {})
            )
        if add_radiance_views:
            attachment = attach_radiance_views_to_model(
                garden_root=garden_root,
                model_target=target,
                view_targets=add_radiance_views,
            )
            result["target"] = attachment["target"]
            result["model_target"] = attachment["model_target"]
            result["radiance_view_attachment"] = attachment
            result.setdefault("summary_view", {}).update(
                attachment.get("summary_view", {})
            )
        return result
