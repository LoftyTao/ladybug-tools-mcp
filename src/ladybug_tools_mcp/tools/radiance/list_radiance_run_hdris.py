"""Alias for listing Radiance HDR images from a view run."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.visual import list_radiance_hdr_images as service


def register(mcp: FastMCP) -> None:
    """Register the list_radiance_run_hdris alias tool."""

    @mcp.tool(
        name="list_radiance_run_hdris",
        description="Alias for list_radiance_hdr_images. List HDR/HDRI .hdr images from a completed point-in-time Radiance view run before falsecolor or GIF postprocess.",
        tags={
            "honeybee-radiance",
            "radiance",
            "run-radiance",
            "postprocess",
            "view",
            "image",
            "hdr",
            "hdri",
            "list",
            "read-only",
            "safe",
            "alias",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_run_hdris(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional completed point-in-time-view radiance_run target."),
        ] = None,
        run_id: Annotated[str | None, Field(description="Optional run identifier.")] = None,
    ) -> dict[str, Any]:
        """List .hdr images for a Radiance view run."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
