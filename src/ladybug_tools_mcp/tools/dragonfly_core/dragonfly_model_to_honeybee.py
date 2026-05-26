"""Convert Dragonfly Model to Honeybee Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.conversion import dragonfly_model_to_honeybee as service


def register(mcp: FastMCP) -> None:
    """Register the dragonfly_model_to_honeybee tool."""

    @mcp.tool(
        name="model_to_honeybee",
        description=(
            "Convert a Garden Dragonfly model into one or more Honeybee HBJSON models "
            "using Dragonfly SDK Model.to_honeybee. Saves Honeybee models into the "
            "Garden without changing the base Dragonfly model. Returns model_target "
            "entries and report for downstream Honeybee Energy or Radiance tools; "
            "EnergyPlus simulation is a later Energy workflow."
        ),
        tags={"dragonfly", "honeybee", "model", "convert", "export"},
        timeout=60,
    )
    def dragonfly_model_to_honeybee(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Dragonfly Model target dict, usually dragonfly_create_model['target']; "
                    "defaults to the Garden base Dragonfly Model."
                )
            ),
        ] = None,
        object_per_model: Annotated[
            str,
            Field(description="Dragonfly to_honeybee object_per_model option: Building, Story, or District."),
        ] = "Building",
        shade_distance: Annotated[
            float | None,
            Field(description="Optional Dragonfly shade_distance."),
        ] = None,
        use_multiplier: Annotated[
            bool,
            Field(description="Whether to pass Dragonfly story multipliers to Honeybee."),
        ] = True,
        exclude_plenums: Annotated[
            bool,
            Field(description="Whether to exclude Dragonfly plenum Room2Ds."),
        ] = False,
        cap: Annotated[
            bool,
            Field(description="Whether to cap building shade representations."),
        ] = False,
        solve_ceiling_adjacencies: Annotated[
            bool,
            Field(description="Whether to solve interior story ceiling adjacencies."),
        ] = False,
        merge_method: Annotated[
            str | None,
            Field(description="Optional Dragonfly merge_method such as Zones or Stories."),
        ] = None,
        tolerance: Annotated[
            float | None,
            Field(description="Optional conversion tolerance. Defaults to the Dragonfly model tolerance."),
        ] = None,
        enforce_adj: Annotated[
            bool,
            Field(description="Whether invalid Room2D adjacencies should raise during conversion."),
        ] = True,
        enforce_solid: Annotated[
            bool,
            Field(description="Whether translated Honeybee Rooms must be solid."),
        ] = True,
        set_base: Annotated[
            bool,
            Field(description="Whether the first converted Honeybee model becomes the base Honeybee model."),
        ] = False,
    ) -> dict[str, Any]:
        """Convert a Dragonfly Model to Honeybee Models."""
        return service(
            garden_root=garden_root,
            model_target=model_target,
            object_per_model=object_per_model,
            shade_distance=shade_distance,
            use_multiplier=use_multiplier,
            exclude_plenums=exclude_plenums,
            cap=cap,
            solve_ceiling_adjacencies=solve_ceiling_adjacencies,
            merge_method=merge_method,
            tolerance=tolerance,
            enforce_adj=enforce_adj,
            enforce_solid=enforce_solid,
            set_base=set_base,
        )
