"""Complete a resumable Honeybee opening and shade stage."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the HB_complete_opening_shade_stage tool."""

    @mcp.tool(
        name="HB_complete_opening_shade_stage",
        description=(
            "Create or resume one bounded Honeybee Room -> exterior Wall Face -> "
            "ratio Aperture -> horizontal louver Shade stage. The first call takes "
            "checkpoint_id, exact room_target and face_target, aperture_ratio, "
            "shade_depth, and shade_count. A later Agent session can pass the returned "
            "checkpoint_target to reread current Garden truth and continue. Matching "
            "objects are reused, conflicts are returned without overwrite, and a "
            "completed retry performs no duplicate write. Returns created_targets, "
            "reused_targets, missing_requirements, validation_state, next_action, "
            "checkpoint_target, persistence_receipt, and report."
        ),
        tags={"aperture", "author", "checkpoint", "honeybee", "shade", "workflow"},
        timeout=30,
    )
    def complete_opening_shade_stage(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        checkpoint_id: Annotated[
            str | None,
            Field(
                description=(
                    "Stable new-stage identifier; omit when resuming by "
                    "checkpoint_target."
                )
            ),
        ] = None,
        checkpoint_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Previously returned Honeybee workflow checkpoint target."
            ),
        ] = None,
        room_target: Annotated[
            dict[str, Any] | None,
            Field(description="Exact Honeybee Room target for a new stage."),
        ] = None,
        face_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Exact exterior Wall Face target on room_target for a new stage."
                )
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Exact Honeybee model target; defaults to the Garden base model."
                )
            ),
        ] = None,
        aperture_ratio: Annotated[
            float | None,
            Field(description="Requested aperture-to-face area ratio between 0 and 1."),
        ] = None,
        shade_depth: Annotated[
            float | None,
            Field(description="Positive horizontal louver depth in model units."),
        ] = None,
        shade_count: Annotated[
            int | None,
            Field(description="Positive horizontal louver count per Aperture."),
        ] = None,
        tolerance: Annotated[
            float,
            Field(description="Positive geometry and parameter matching tolerance."),
        ] = 0.01,
    ) -> dict[str, Any]:
        from garden.honeybee_core.opening_shade_stage import (
            complete_honeybee_opening_shade_stage as service,
        )

        return service(
            garden_root=garden_root,
            checkpoint_id=checkpoint_id,
            checkpoint_target=checkpoint_target,
            room_target=room_target,
            face_target=face_target,
            model_target=model_target,
            aperture_ratio=aperture_ratio,
            shade_depth=shade_depth,
            shade_count=shade_count,
            tolerance=tolerance,
        )
