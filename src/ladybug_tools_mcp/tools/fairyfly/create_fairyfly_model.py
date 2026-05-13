"""Create Fairyfly Model MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.model import create_fairyfly_model as service


def register(mcp: FastMCP) -> None:
    """Register the create_fairyfly_model tool."""

    @mcp.tool(
        name="create_fairyfly_model",
        description=(
            "Create an empty Fairyfly two-dimensional heat-transfer model in a "
            "Garden and optionally set it as the base Fairyfly model. Fairyfly "
            "SDK model identifiers are UUIDs; this tool's identifier is the stable "
            "Garden model identifier and FFJSON file name. Use this for a create "
            "Fairyfly two dimensional heat transfer model request before adding "
            "Shapes, Boundaries, writing THMZ, or running THERM."
        ),
        tags={
            "fairyfly",
            "therm",
            "garden-mode",
            "model",
            "base-fairyfly-model",
            "create",
            "write",
            "safe",
        },
        timeout=20,
    )
    def create_fairyfly_model(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        identifier: Annotated[
            str,
            Field(
                description="Required stable Garden Fairyfly model identifier used for the FFJSON file name."
            ),
        ],
        units: Annotated[
            str,
            Field(description="Fairyfly model units string, for example Millimeters."),
        ] = "Millimeters",
        tolerance: Annotated[
            float | None,
            Field(description="Optional Fairyfly model tolerance."),
        ] = None,
        angle_tolerance: Annotated[
            float,
            Field(description="Fairyfly model angle tolerance."),
        ] = 1.0,
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing model display name."),
        ] = None,
        save_back: Annotated[
            bool,
            Field(description="Whether to save the model into Garden."),
        ] = True,
        set_base: Annotated[
            bool,
            Field(description="Whether to set as Garden base Fairyfly model."),
        ] = True,
        include_body: Annotated[
            bool,
            Field(description="Whether to return full model body if not saved."),
        ] = False,
    ) -> dict[str, Any]:
        """Create a Fairyfly Model."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            units=units,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
            display_name=display_name,
            save_back=save_back,
            set_base=set_base,
            include_body=include_body,
        )
