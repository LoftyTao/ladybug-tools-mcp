"""flowerpot MCP tools."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from flowerpot.active_context import read_active_context, read_latest_active_context


def get_active_flowerpot_context(
    garden_root: str | None = None,
    platform: str = "grasshopper",
    root_folder: str | None = None,
) -> dict[str, Any]:
    """Read the active Garden-local Flowerpot context."""
    if garden_root:
        return read_active_context(garden_root=garden_root, platform=platform)
    if root_folder:
        return read_latest_active_context(root_folder=root_folder, platform=platform)
    raise ValueError("garden_root or root_folder is required.")


def register(mcp: FastMCP) -> None:
    """Register flowerpot tools."""

    @mcp.tool(
        name="FP_Cleanup_All",
        description=(
            'Clean only Garden-local Flowerpot handoff maintenance state: registry entries and '
            'Flowerpot item files. Use orphaned for missing item files, expired with '
            'older_than_days for stale handoff records, or all for a full handoff reset. Returns '
            'removed, skipped, summary_view, persistence_receipt, and report.'
        ),
        tags={
            "cleanup",
            "flowerpot",
            "handoff",
        },
        timeout=20,
    )
    def cleanup_flowerpots(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        cleanup_scope: Annotated[
            str,
            Field(
                description=(
                    "Cleanup scope: orphaned for registry entries missing item "
                    "files, expired with older_than_days for stale records, or all "
                    "for every Flowerpot handoff item in this Garden."
                )
            ),
        ] = "orphaned",
        dry_run: Annotated[
            bool,
            Field(description="Preview cleanup without deleting Flowerpot files."),
        ] = False,
        older_than_days: Annotated[
            int | None,
            Field(
                description="Optional age threshold in days for cleanup_scope=expired."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Clean registered Flowerpot handoff state."""
        from flowerpot.registry import cleanup_flowerpots as service

        return service(
            garden_root=garden_root,
            cleanup_scope=cleanup_scope,
            dry_run=dry_run,
            older_than_days=older_than_days,
        )

    @mcp.tool(
        name="FP_Create",
        description=(
            'Create or reuse an opaque Garden-local Flowerpot handoff record from existing Garden '
            'truth, a base Honeybee/Dragonfly model slot, or a registered typed target. Use this '
            'for platform handoff, such as a Grasshopper component context, treating the '
            'Flowerpot dictionary as an opaque handoff handle. Returns flowerpot, flowerpot_id, '
            'target, summary_view, persistence_receipt, and report.'
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
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
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
                    'Registered typed target dict with target_type from a prior MCP result; required '
                    "when source='target'."
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
                    'Optional compact platform metadata, such as Grasshopper document or component '
                    'context.'
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
        from flowerpot.registry import create_flowerpot as service

        return service(
            garden_root=garden_root,
            source=source,
            target=target,
            label=label,
            platform=platform,
            force_new=force_new,
        )

    @mcp.tool(
        name="FP_Get_Active_Context",
        description=(
            'Read the Garden-local active Flowerpot context file for prompts about Grasshopper, '
            'current model, active model, 当前模型, or 正在编辑的模型. Use garden_root for an exact Garden '
            'or root_folder to find the most recent active-context file under a folder of '
            'Gardens. Returns exists, active_context, flowerpot, model_target, summary_view, and '
            'report with sanitized context only. Returns sanitized context only without falling '
            'back to the registry when no active-context file exists.'
        ),
        tags={
            "context",
            "flowerpot",
            "grasshopper",
            "handoff",
        },
        timeout=20,
        annotations={"readOnlyHint": True},
    )
    def get_active_context(
        garden_root: Annotated[
            str | None,
            Field(description="Optional Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ] = None,
        platform: Annotated[
            str,
            Field(
                description=(
                    "Platform active-context key. Defaults to grasshopper for the "
                    "active Grasshopper model context file."
                )
            ),
        ] = "grasshopper",
        root_folder: Annotated[
            str | None,
            Field(
                description=(
                    "Optional folder containing one or more Gardens. When "
                    "garden_root is unknown, this searches for the most recently "
                    "updated flowerpots/active_context/<platform>.json file and "
                    "derives its Garden root from the file path."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Read active Flowerpot context."""
        return get_active_flowerpot_context(
            garden_root=garden_root,
            platform=platform,
            root_folder=root_folder,
        )

    @mcp.tool(
        name="FP_Get",
        description=(
            'Read, list, or summarize Garden-local Flowerpot handoff context while keeping '
            'Flowerpot dictionaries opaque. Use garden_root alone to list registered Flowerpots, '
            'garden_root plus flowerpot_id to read one registered item, or flowerpot to summarize '
            'a passed handoff dict. Returns flowerpot, target, matches, summary_view, and report.'
        ),
        tags={
            "context",
            "flowerpot",
            "handoff",
            "target",
        },
        timeout=20,
        annotations={"readOnlyHint": True},
    )
    def get_flowerpot(
        garden_root: Annotated[
            str | None,
            Field(
                description="Optional Garden root path containing garden.json, usually GD_Create['garden_root']; required when using flowerpot_id or listing registered Flowerpots."
            ),
        ] = None,
        flowerpot_id: Annotated[
            str | None,
            Field(
                description='Optional registered Flowerpot id returned by FP_Create. Omit with garden_root to list registered Flowerpots.'
            ),
        ] = None,
        flowerpot: Annotated[
            dict[str, Any] | None,
            Field(
                description='Optional opaque Flowerpot dict to summarize (pass unchanged).'
            ),
        ] = None,
        include_body: Annotated[
            bool,
            Field(
                description=(
                    "Requesting full body is not supported in the current "
                    "Flowerpot contract. Leave false for target/summary handoff; "
                    "true returns the same lightweight context with a warning."
                )
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Get, list, or summarize Flowerpot context."""
        from flowerpot.registry import get_flowerpot as service

        return service(
            garden_root=garden_root,
            flowerpot_id=flowerpot_id,
            flowerpot=flowerpot,
            include_body=include_body,
        )
