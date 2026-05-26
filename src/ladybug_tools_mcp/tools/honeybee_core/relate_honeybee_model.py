"""Relate Honeybee Model MCP tool."""

from __future__ import annotations
from typing import Annotated, Any, Literal
from fastmcp import FastMCP
from pydantic import Field
from garden.honeybee_core.relate import relate_honeybee_model as service


def register(mcp: FastMCP) -> None:
    'Register the honeybee_relate_model tool.'

    @mcp.tool(
        name="relate_model",
        description="Run SDK-backed Honeybee model relationship processing for solve_adjacency, Surface boundary relationships, optional room-face intersection, coplanar merge, AirBoundary/adiabatic settings, and explicit high-risk cleanup or missing sub-face repair. explicit_relate_full enables overwrite, relationship_cleanup, mismatched sub-face deletion, and clone_missing Aperture/Door repair, so use it only when the user asks for repair/overwrite/delete mismatch cleanup. Returns summary_view.model_target, persistence_receipt, and report for validation or export calls; there is no top-level target.",
        tags={
            "adjacency",
            "boundary",
            "cleanup",
            "edit",
            "geometry",
            "honeybee",
            "model",
            "repair",
            "validate",
        },
        timeout=30,
    )
    def relate_honeybee_model(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually honeybee_create_model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
        relation_mode: Annotated[
            str,
            Field(
                description="Relation mode: solve_adjacency or explicit_relate_full. explicit_relate_full enables high-risk overwrite, cleanup, remove_mismatched_subfaces, and clone_missing Aperture/Door repair defaults."
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
            Literal["none", "clone_single", "clone_missing"],
            Field(
                description="How to handle one-sided Aperture/Door sub-face mismatches before solving adjacency: clone_single, clone_missing, or none."
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
