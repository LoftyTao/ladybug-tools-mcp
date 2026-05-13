"""Save Base Dragonfly Model MCP tool."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from garden.store import save_base_dragonfly_model as service


def register(mcp: FastMCP) -> None:
    """Register the save_base_dragonfly_model tool."""

    @mcp.tool(
        name="save_base_dragonfly_model",
        description="Save the current Garden base Dragonfly model back to Garden authoring truth.",
        tags={"garden", "garden-mode", "dragonfly", "model", "base-dragonfly-model", "save", "write", "safe"},
        timeout=20,
    )
    def save_base_dragonfly_model(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path string containing garden.json."),
        ],
        message: Annotated[
            str | None,
            Field(description="Optional short save message."),
        ] = None,
        force: Annotated[
            bool,
            Field(description="Force a save even when changes are light."),
        ] = False,
        name: Annotated[
            str | None,
            Field(description="Optional output DFJSON name, without extension."),
        ] = None,
        indent: Annotated[
            int | None,
            Field(description="DFJSON indentation. Defaults to 2."),
        ] = 2,
        included_prop: Annotated[
            list[str] | None,
            Field(description="Extension properties to include. Defaults to all."),
        ] = None,
    ) -> dict[str, object]:
        """Save the current Garden base Dragonfly model."""
        return service(
            garden_root=garden_root,
            message=message,
            force=force,
            name=name,
            indent=indent,
            included_prop=included_prop,
        )
