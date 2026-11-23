"""Apply a validated Ironbug IB_HVACSystem as DetailedHVAC on a Honeybee or Dragonfly model."""

from __future__ import annotations

from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.tools.ironbug._schemas import (
    ApplyToModelResult,
    BuildingModelTargetRef,
    BuildingObjectTargetRef,
    IronbugModelTargetRef,
    dump_models,
    dump_target,
)


def register(mcp: FastMCP) -> None:
    """Register IB_apply_to_model."""

    @mcp.tool(
        name="IB_apply_to_model",
        description=(
            "Attach a validated official Ironbug IB_HVACSystem as DetailedHVAC on selected "
            "Honeybee Rooms (or Dragonfly Room2D/Story/Building hosts) and persist the updated model. "
            "For Honeybee, omitting room selectors automatically binds to rooms matching the "
            "system's thermal_zones."
        ),
        tags={"ironbug", "detailed-hvac", "hvac", "energy", "apply", "edit"},
        annotations={"read_only_hint": False, "destructive_hint": False},
        timeout=60,
    )
    def ib_apply_to_model(
        garden_root: Annotated[
            str,
            Field(min_length=1, description="Required Garden root path containing garden.json."),
        ],
        ironbug_model_target: Annotated[
            IronbugModelTargetRef | None,
            Field(description="Target returned by IB_create_system. Optional when only one Ironbug system exists."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional Ironbug system identifier when ironbug_model_target is omitted."),
        ] = None,
        model_family: Annotated[
            Literal["honeybee", "dragonfly"],
            Field(description="Target building model family: 'honeybee' (default) or 'dragonfly'."),
        ] = "honeybee",
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Optional Honeybee or Dragonfly model target; defaults to the Garden base model."),
        ] = None,
        room_targets: Annotated[
            list[BuildingObjectTargetRef] | None,
            Field(description="Optional Honeybee Room targets from HB_search_model_objects."),
        ] = None,
        room_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional Honeybee Room identifiers to assign this DetailedHVAC to."),
        ] = None,
        apply_to_all_rooms: Annotated[
            bool,
            Field(description="Assign this DetailedHVAC to all Rooms in the target Honeybee model."),
        ] = False,
        host_target: Annotated[
            BuildingObjectTargetRef | None,
            Field(description="Optional Dragonfly Room2D, Story, or Building target when model_family='dragonfly'."),
        ] = None,
        conditioned_only: Annotated[
            bool,
            Field(description="For Dragonfly Story/Building hosts, apply only to conditioned Room2Ds."),
        ] = True,
        detailed_hvac_identifier: Annotated[
            str | None,
            Field(description="Optional DetailedHVAC identifier stored in the model."),
        ] = None,
    ) -> ApplyToModelResult:
        """Apply an Ironbug DetailedHVAC system to a Honeybee or Dragonfly model."""
        from garden.ironbug.service import apply_ironbug_to_model

        return ApplyToModelResult.model_validate(
            apply_ironbug_to_model(
                garden_root=garden_root,
                ironbug_model_target=dump_target(ironbug_model_target),
                identifier=identifier,
                model_family=model_family,
                model_target=dump_target(model_target),
                room_targets=dump_models(room_targets),
                room_identifiers=room_identifiers,
                apply_to_all_rooms=apply_to_all_rooms,
                host_target=dump_target(host_target),
                conditioned_only=conditioned_only,
                detailed_hvac_identifier=detailed_hvac_identifier,
            )
        )
