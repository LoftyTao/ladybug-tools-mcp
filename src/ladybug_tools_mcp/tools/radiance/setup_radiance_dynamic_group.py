"""Apply Honeybee Radiance dynamic group state MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.dynamic import setup_radiance_dynamic_group as service


def register(mcp: FastMCP) -> None:
    """Register the setup_radiance_dynamic_group tool."""

    @mcp.tool(
        name="setup_radiance_dynamic_group",
        description="Apply the same Honeybee Radiance dynamic_group_identifier and state update to multiple Shade, Aperture, or Door typed targets in a Garden model. This creates the model-side grouping by setting object properties; it does not create a separate SDK DynamicShadeGroup or DynamicSubFaceGroup object. For replace_all/add you must pass at least one state in states=[...]. States should be object_dict/state_dict values from create_radiance_shade_state for shades or create_radiance_subface_state for apertures/doors; create the state and call this tool in the same execute block.",
        tags={
            "honeybee-radiance",
            "radiance",
            "dynamic",
            "dynamic-group",
            "garden-mode",
            "write",
            "safe",
        },
        timeout=60,
    )
    def setup_radiance_dynamic_group(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path string containing garden.json."),
        ],
        targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Shade, Aperture, or Door typed targets to update."),
        ] = None,
        dynamic_group_identifier: Annotated[
            str | None,
            Field(description="Dynamic group identifier to set on every target."),
        ] = None,
        states: Annotated[
            list[dict[str, Any]] | None,
            Field(description="State dictionaries to replace/add. Required for replace_all/add; omit only when operation is clear."),
        ] = None,
        operation: Annotated[
            str,
            Field(description="State operation: replace_all, add, or clear."),
        ] = "replace_all",
    ) -> dict[str, Any]:
        """Apply Radiance dynamic state settings to multiple Honeybee objects."""
        if targets is None:
            raise ValueError("Provide targets.")
        if dynamic_group_identifier is None:
            raise ValueError("Provide dynamic_group_identifier.")
        return service(
            garden_root=garden_root,
            targets=targets,
            dynamic_group_identifier=dynamic_group_identifier,
            states=states,
            operation=operation,
        )
