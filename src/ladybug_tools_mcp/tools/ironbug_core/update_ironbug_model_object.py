"""Update one Ironbug component field MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the IB_update_model_object tool."""

    @mcp.tool(
        name="IB_update_model_object",
        description=(
            "Update exactly one field on a canonical Ironbug component selected by a "
            "typed component target. field_name must be display_name or one of the "
            "component SOURCE_FIELD_NAMES, SOURCE_PROPERTIES, or SOURCE_DATA_MEMBERS. "
            "Use exactly one mode: scalar/scalar-list value, one typed reference_target, "
            "many typed reference_targets, or clear=true. Dicts, nested dicts, raw object "
            "payloads, and non-component targets are rejected. Returns target, "
            "updated_model_target, summary_view.updated_fields, persistence_receipt, "
            "and report."
        ),
        tags={"ironbug", "detailed-hvac", "component", "edit", "author"},
        timeout=20,
    )
    def update_ironbug_model_object(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any],
            Field(description="Required Ironbug model target from IB_create_model."),
        ],
        target: Annotated[
            dict[str, Any],
            Field(description="Required typed Ironbug component target from a search or create result."),
        ],
        field_name: Annotated[
            str,
            Field(description="One display_name or source metadata field name to update."),
        ],
        value: Annotated[
            str | int | float | bool | list[str | int | float | bool] | None,
            Field(description="Scalar or flat scalar-list value; object payloads are rejected."),
        ] = None,
        reference_target: Annotated[
            dict[str, Any] | None,
            Field(description="One typed Ironbug component target for a single object reference field."),
        ] = None,
        reference_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Typed Ironbug component targets for a list reference field."),
        ] = None,
        clear: Annotated[
            bool,
            Field(description="Clear the selected field; use this as the only update mode."),
        ] = False,
    ) -> dict[str, Any]:
        """Update one canonical Ironbug component field."""

        from garden.ironbug_core.object_updates import (
            update_ironbug_model_object as service,
        )

        return service(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            target=target,
            field_name=field_name,
            value=value,
            reference_target=reference_target,
            reference_targets=reference_targets,
            clear=clear,
        )
