"""List Radiance HDR images MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.visual import list_radiance_hdr_images as service


def register(mcp: FastMCP) -> None:
    """Register the list_radiance_hdr_images tool."""

    @mcp.tool(
        name="list_radiance_hdr_images",
        description="List .hdr image files from a completed point-in-time-view Radiance run. This MCP visual postprocess path intentionally supports only .hdr inputs; .pic and .unf are not supported. Use before radiance_hdr_to_falsecolor or radiance_hdr_to_gif.",
        tags={
            "honeybee-radiance",
            "radiance",
            "run-radiance",
            "postprocess",
            "view",
            "image",
            "hdr",
            "list",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_hdr_images(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional radiance_run target returned by start_radiance_view_run."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
    ) -> dict[str, Any]:
        """List .hdr images for a Radiance view run."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
