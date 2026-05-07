"""Create Flowerpot MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from flowerpot.registry import create_flowerpot as service


def register(mcp: FastMCP) -> None:
    """Register the create_flowerpot tool."""

    @mcp.tool(
        name="create_flowerpot",
        description="Create and register a Garden-local Flowerpot handoff container from existing Garden entity content such as a Garden target or base model. Flowerpot is for migrating Garden ecology, not arbitrary payload wrapping; do not pass full model bodies, SDK object_dict payloads, or arguments null. Preferred call shape: {\"name\":\"create_flowerpot\",\"arguments\":{\"garden_root\":\"tests/.artifacts/.../garden\",\"source\":\"garden\"}}.",
        tags={
            "flowerpot",
            "garden-mode",
            "platform-handoff",
            "registered-container",
            "grasshopper",
            "write",
            "safe",
        },
        timeout=20,
    )
    def create_flowerpot(
        garden_root: Annotated[
            str,
            Field(
                description="Required exact Garden root path string containing garden.json."
            ),
        ],
        source: Annotated[
            str,
            Field(
                description="Flowerpot source entity. First batch supports garden, base_model, or target. Use garden for a Garden Flowerpot and base_model for the current Garden base model."
            ),
        ] = "garden",
        target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional registered typed target dict with target_type. Do not pass inline payload bodies, full model dictionaries, or SDK object_dict values."
            ),
        ] = None,
        label: Annotated[
            str | None,
            Field(description="Optional user-facing Flowerpot label."),
        ] = None,
        platform: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional compact platform context, for example Grasshopper document or component metadata. Do not include large payloads."
            ),
        ] = None,
        force_new: Annotated[
            bool,
            Field(
                description="When false, reuse an existing Flowerpot with the same source, target, and platform context. Set true only when a distinct handoff record is required."
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Create a registered Flowerpot from Garden entity content."""
        return service(
            garden_root=garden_root,
            source=source,
            target=target,
            label=label,
            platform=platform,
            force_new=force_new,
        )
