"""List Radiance HDR images MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.visual import list_radiance_hdr_images as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_list_hdr_images tool.'

    @mcp.tool(
        name="list_hdr_images",
        description=(
            "List HDR image artifacts from completed Radiance view runs. Use "
            "this before falsecolor, GIF, or image search workflows. This "
            "returns image artifact metadata and paths only; it does not "
            "render views, convert images, or embed binary image data. Returns "
            "matches, artifact_paths, summary_view, and report."
        ),
        tags={
            "artifact",
            "radiance",
            "image",
            "result",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_hdr_images(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='Optional completed view radiance_run target returned by radiance_start_view_simulation. Poll the run before listing HDR images.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier for a completed view run when run_target is not supplied."),
        ] = None,
    ) -> dict[str, Any]:
        """List .hdr images for a Radiance view run."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
