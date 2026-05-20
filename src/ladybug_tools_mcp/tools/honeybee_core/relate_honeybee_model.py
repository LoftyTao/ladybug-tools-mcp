"""Relate Honeybee Model MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.relate import relate_honeybee_model as service


def register(mcp: FastMCP) -> None:
    """Register the relate_honeybee_model tool."""

    @mcp.tool(
        name="relate_honeybee_model",
        description="Run SDK-backed Honeybee model relationship processing. Supports the standard solve_adjacency path and explicit_relate_full for high-risk overwrite, cleanup, mismatched sub-face deletion, and clone_missing Aperture/Door repair. Requires garden_root; use explicit_relate_full only when the user asks for repair/overwrite/delete mismatch cleanup.",
        tags={
            "honeybee-core",
            "garden-mode",
            "model",
            "relate",
            "adjacency",
            "intersect",
            "solve",
            "repair",
            "cleanup",
            "destructive",
            "write",
        },
        timeout=30,
    )
    def relate_honeybee_model(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict. Defaults to the Garden base model."
            ),
        ] = None,
        relation_mode: Annotated[
            str,
            Field(
                description="Relation mode: solve_adjacency or explicit_relate_full. explicit_relate_full enables high-risk overwrite, cleanup, remove_mismatched_subfaces, and clone_missing repair defaults."
            ),
        ] = "solve_adjacency",
        solve_adjacency: Annotated[
            bool | None,
            Field(
                description="Optional solve-adjacency flag. Passing true is equivalent to relation_mode='solve_adjacency'."
            ),
        ] = None,
        intersect: Annotated[
            bool,
            Field(
                description="Whether to intersect Room Faces before solving adjacency. Defaults to true for the standard relate flow."
            ),
        ] = True,
        merge_coplanar: Annotated[
            bool,
            Field(
                description="Whether to merge coplanar Room Faces before solving adjacency."
            ),
        ] = False,
        overwrite: Annotated[
            bool,
            Field(
                description="Whether existing Surface boundary conditions should be overwritten."
            ),
        ] = False,
        remove_mismatched_sub_faces: Annotated[
            bool,
            Field(
                description="Whether mismatched adjacent sub-faces should be removed. Defaults to false; prefer subface_mismatch_policy."
            ),
        ] = False,
        subface_mismatch_policy: Annotated[
            str,
            Field(
                description="How to handle one-sided sub-face mismatches before solving adjacency: clone_single, clone_missing, or none."
            ),
        ] = "clone_single",
        air_boundary: Annotated[
            bool,
            Field(
                description="Whether solved wall adjacencies should become AirBoundary faces."
            ),
        ] = False,
        adiabatic: Annotated[
            bool,
            Field(
                description="Whether solved adjacencies should become adiabatic when supported."
            ),
        ] = False,
        relationship_cleanup: Annotated[
            bool,
            Field(
                description="Whether to clear existing Surface boundary conditions before solving. explicit_relate_full enables this automatically."
            ),
        ] = False,
        tolerance: Annotated[
            float | None,
            Field(
                description="Optional distance tolerance. Defaults to model tolerance."
            ),
        ] = None,
        angle_tolerance: Annotated[
            float | None,
            Field(
                description="Optional angle tolerance in degrees. Defaults to model angle tolerance."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Solve Honeybee model relationships with the SDK."""
        if solve_adjacency is True:
            relation_mode = "solve_adjacency"
        return service(
            garden_root=garden_root,
            model_target=model_target,
            relation_mode=relation_mode,
            intersect=intersect,
            merge_coplanar=merge_coplanar,
            overwrite=overwrite,
            remove_mismatched_sub_faces=remove_mismatched_sub_faces,
            subface_mismatch_policy=subface_mismatch_policy,
            air_boundary=air_boundary,
            adiabatic=adiabatic,
            relationship_cleanup=relationship_cleanup,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
        )
