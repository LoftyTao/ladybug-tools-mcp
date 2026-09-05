"""Safely remove Ironbug component-library objects."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the IB_remove_component tool."""

    @mcp.tool(
        name="IB_remove_component",
        description=(
            "Safely remove an Ironbug component from the canonical component library. "
            "Pass a typed component target returned by IB_search_model_objects to "
            "remove one component only when it has no references; or pass "
            "cleanup_orphans=true to remove every component unreachable from active "
            "EMS, electric-load-center, air-loop, plant-loop, VRF, and no-loop "
            "room-serving graphs. Identifier strings and non-component targets are "
            "rejected. Returns summary_view, persistence_receipt, and report."
        ),
        tags={"ironbug", "detailed-hvac", "component", "remove", "target"},
        timeout=20,
    )
    def remove_ironbug_component(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_create['garden_root']."
            ),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any],
            Field(
                description="Required Ironbug model target returned by IB_create_model."
            ),
        ],
        target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional typed component target from IB_search_model_objects; "
                    "do not pass an identifier string. Omit it when using cleanup_orphans."
                )
            ),
        ] = None,
        cleanup_orphans: Annotated[
            bool,
            Field(
                description=(
                    "Explicitly remove all component-library entries unreachable from "
                    "the active Ironbug graph."
                )
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Remove one unreferenced component or clean orphan components."""

        from garden.ironbug_core.models import remove_ironbug_component as service

        return service(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            target=target,
            cleanup_orphans=cleanup_orphans,
        )
