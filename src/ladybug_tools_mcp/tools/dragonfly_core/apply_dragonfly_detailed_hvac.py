"""Apply Ironbug DetailedHVAC to Dragonfly Energy properties MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the DF_detailed_hvac tool."""

    @mcp.tool(
        name="DF_detailed_hvac",
        description=(
            "Apply a Garden Ironbug-Core .ibjson model as Dragonfly Energy "
            "DetailedHVAC/HVAC properties on a Dragonfly Room2D, Story, or Building "
            "target. This is the Dragonfly-side route for Ironbug-backed HVAC: pass "
            "ironbug_model_target from IB_create_model plus a Dragonfly "
            "host_target. It does not accept plain strings, Honeybee-only "
            "DetailedHVAC objects, or run EnergyPlus. Returns the Ironbug-backed "
            "detailed_hvac_target, updated Dragonfly model target, summary_view, "
            "persistence_receipt, and report."
        ),
        tags={"dragonfly", "detailed-hvac", "ironbug", "hvac", "energy", "edit"},
        timeout=60,
    )
    def apply_dragonfly_detailed_hvac(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_create['garden_root']."),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required Ironbug model target returned by IB_create_model. "
                    "Do not pass a plain string or Honeybee DetailedHVAC object."
                )
            ),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required Dragonfly Room2D, Story, or Building target from DF_search_objects "
                    "or Dragonfly authoring tools."
                )
            ),
        ],
        dragonfly_model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Dragonfly model target. Defaults to base_dragonfly_model."),
        ] = None,
        detailed_hvac_identifier: Annotated[
            str | None,
            Field(description="Optional DetailedHVAC identifier. Defaults from the Ironbug model."),
        ] = None,
        conditioned_only: Annotated[
            bool,
            Field(
                description=(
                    "For Story and Building hosts, apply only to already conditioned Room2Ds. "
                    "Set false to apply to all child Room2Ds. Room2D hosts ignore this distinction."
                )
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Apply Ironbug DetailedHVAC to Dragonfly Energy properties."""
        from garden.ironbug_core.detailed_hvac import (
            apply_ironbug_detailed_hvac_to_dragonfly_energy_properties as service,
        )

        return service(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            host_target=host_target,
            dragonfly_model_target=dragonfly_model_target,
            detailed_hvac_identifier=detailed_hvac_identifier,
            conditioned_only=conditioned_only,
        )
