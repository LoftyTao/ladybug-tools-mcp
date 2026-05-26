"""Create Flowerpot MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from flowerpot.registry import create_flowerpot as service


def register(mcp: FastMCP) -> None:
    'Register the flowerpot_create tool.'

    @mcp.tool(
        name='create',
        description=(
            "Create or reuse an opaque Garden-local Flowerpot handoff record from "
            "existing Garden truth, a base Honeybee/Dragonfly model slot, or a "
            "registered typed target. Use this for platform handoff, such as a "
            "Grasshopper component context, while keeping the Flowerpot dictionary "
            "opaque to the Agent. Returns flowerpot, flowerpot_id, target, "
            "summary_view, persistence_receipt, and report. It is not a generic "
            "payload wrapper and must not receive full model bodies, SDK object_dict "
            "payloads, inline target bodies, or arguments null."
        ),
        tags={
            "context",
            "flowerpot",
            "handoff",
            "target",
        },
        timeout=20,
    )
    def create_flowerpot(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually garden_create['garden_root']."
            ),
        ],
        source: Annotated[
            str,
            Field(
                description=(
                    "Flowerpot source value: garden, base_honeybee_model, "
                    "base_dragonfly_model, or target. Use garden for the whole "
                    "Garden handoff and target when passing a registered typed "
                    "target through the target parameter."
                )
            ),
        ] = "garden",
        target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Registered typed target dict with target_type, usually from a "
                    "previous MCP tool result; required when source='target'. Do "
                    "not pass inline payload bodies, full model dictionaries, or "
                    "SDK object_dict values."
                )
            ),
        ] = None,
        label: Annotated[
            str | None,
            Field(description="Optional user-facing label for the Flowerpot summary_view."),
        ] = None,
        platform: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional compact platform context, for example Grasshopper "
                    "document or component metadata. Keep this as small metadata; "
                    "do not include model payloads or large files."
                )
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
