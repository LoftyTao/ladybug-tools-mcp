"""Create a Garden-managed Ironbug IB_HVACSystem file."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.tools.ironbug._schemas import (
    IronbugSystemMutationResult,
    IronbugSystemSpecDict,
)


def register(mcp: FastMCP) -> None:
    """Register IB_create_system."""

    @mcp.tool(
        name="IB_create_system",
        description=(
            "Initialize a new Garden-managed official Ironbug IB_HVACSystem specification under "
            "models/ironbug/<identifier>.json (or import an existing official IB_HVACSystem JSON). "
            "Use the returned ironbug_model_target with IB_upsert_components and IB_configure_loops."
        ),
        tags={"ironbug", "detailed-hvac", "hvac", "author"},
        annotations={"read_only_hint": False, "destructive_hint": False},
        timeout=20,
    )
    def ib_create_system(
        garden_root: Annotated[
            str,
            Field(min_length=1, description="Required Garden root path containing garden.json."),
        ],
        identifier: Annotated[
            str,
            Field(min_length=1, description="Unique identifier for this Ironbug HVAC system inside the Garden."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional human-readable DisplayName stored on IB_HVACSystem."),
        ] = None,
        specification: Annotated[
            IronbugSystemSpecDict | str | None,
            Field(description="Optional existing official IB_HVACSystem JSON dict or string to import."),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing Ironbug system with the same identifier."),
        ] = False,
    ) -> IronbugSystemMutationResult:
        """Create an Ironbug HVAC system in a Garden."""
        from garden.ironbug.service import create_ironbug_system

        raw_specification = (
            specification.model_dump(exclude_unset=True)
            if isinstance(specification, IronbugSystemSpecDict)
            else specification
        )

        return IronbugSystemMutationResult.model_validate(
            create_ironbug_system(
                garden_root=garden_root,
                identifier=identifier,
                display_name=display_name,
                specification=raw_specification,
                overwrite=overwrite,
            )
        )
