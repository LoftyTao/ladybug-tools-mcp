"""Apply Ironbug DetailedHVAC to Dragonfly Energy HVAC properties."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core import (
    apply_ironbug_detailed_hvac_to_dragonfly_energy_properties as service,
)


def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_apply_to_dragonfly_energy_properties tool.'

    @mcp.tool(
        name="apply_to_dragonfly_energy_properties",
        description=(
            "Apply a Garden Ironbug-Core .ibjson model as Dragonfly Energy HVAC "
            "properties on a Dragonfly Room2D, Story, or Building target. Use "
            'ironbug_model_target from detailed_hvac_create_model and host_target from '
            'dragonfly_search_model_objects or Dragonfly create tools. Room2D uses '
            "direct SDK HVAC assignment; Story and Building use Dragonfly SDK "
            "set_all_room_2d_hvac bulk assignment. This tool only sets HVAC. "
            "Setpoints remain managed by ProgramType/program workflows. It does "
            "not convert to Honeybee, generate OSM/IDF, run OpenStudio or "
            "EnergyPlus, or provide run_ironbug_energy. Returns model_target, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={"ironbug", "detailed-hvac", "dragonfly", "apply", "energy"},
        timeout=60,
    )
    def apply_ironbug_detailed_hvac_to_dragonfly_energy_properties(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required Ironbug model target named ironbug_model_target; pass "
                    "detailed_hvac_create_model['target'], not ironbug_model."
                )
            ),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required Dragonfly Room2D, Story, or Building object target. "
                    "Use object_type room2d, story, or building."
                )
            ),
        ],
        dragonfly_model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target. Defaults to base Dragonfly model."),
        ] = None,
        detailed_hvac_identifier: Annotated[
            str | None,
            Field(description="Optional DetailedHVAC identifier. Defaults from the Ironbug model."),
        ] = None,
        conditioned_only: Annotated[
            bool,
            Field(
                description=(
                    "For Story and Building hosts, keep the Dragonfly SDK default of "
                    "only applying HVAC to already conditioned Room2Ds. Set false to "
                    "apply to all child Room2Ds. Room2D hosts ignore this distinction."
                )
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Apply Ironbug DetailedHVAC to Dragonfly Energy HVAC properties."""

        return service(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            host_target=host_target,
            dragonfly_model_target=dragonfly_model_target,
            detailed_hvac_identifier=detailed_hvac_identifier,
            conditioned_only=conditioned_only,
        )
