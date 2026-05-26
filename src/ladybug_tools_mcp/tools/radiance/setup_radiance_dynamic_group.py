"""Apply Honeybee Radiance dynamic group state MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.dynamic import setup_radiance_dynamic_group as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_setup_dynamic_group tool.'

    @mcp.tool(
        name="setup_dynamic_group",
        description=(
            "Apply the same Honeybee Radiance dynamic_group_identifier and "
            "state update to multiple Shade, Aperture, or Door targets in a "
            "Garden model. This creates model-side grouping by setting object "
            "properties; it does not create a separate SDK DynamicShadeGroup "
            "or DynamicSubFaceGroup object. For replace_all/add, pass at least "
            "one state from radiance_create_shade_state or "
            "radiance_create_subface_state. This edits Radiance properties and "
            "does not run a recipe."
        ),
        tags={
            "dynamic",
            "radiance",
            "model",
            "edit",
        },
        timeout=60,
    )
    def setup_radiance_dynamic_group(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Shade, Aperture, or Door typed targets to update; all targets receive the same dynamic_group_identifier."),
        ] = None,
        dynamic_group_identifier: Annotated[
            str | None,
            Field(description="Dynamic group identifier to set on every target."),
        ] = None,
        states: Annotated[
            list[dict[str, Any]] | None,
            Field(description="State dictionaries from radiance_create_shade_state or radiance_create_subface_state. Required for replace_all and add; omit for clear."),
        ] = None,
        operation: Annotated[
            str,
            Field(description="State operation on the target objects: replace_all, add, or clear."),
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
