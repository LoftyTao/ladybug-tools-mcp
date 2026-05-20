"""Radiance HDR to GIF MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.visual import radiance_hdr_to_gif as service


def register(mcp: FastMCP) -> None:
    """Register the radiance_hdr_to_gif tool."""

    @mcp.tool(
        name="radiance_hdr_to_gif",
        description="Canonical Radiance HDR GIF postprocess tool. Create a .gif Garden artifact from a Radiance .hdr image using the SDK Ra_GIF command wrapper. This tool only accepts .hdr input and writes .gif output; .pic and .unf are intentionally unsupported. Use list_radiance_hdr_images to select an image from a completed view run.",
        tags={
            "honeybee-radiance",
            "radiance",
            "run-radiance",
            "postprocess",
            "view",
            "image",
            "hdr",
            "gif",
            "artifact",
            "write",
            "safe",
        },
        timeout=60,
    )
    def radiance_hdr_to_gif(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional completed point-in-time-view radiance_run target."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        image_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative .hdr image path. Use this instead of run_target/run_id."),
        ] = None,
        image_name: Annotated[
            str | None,
            Field(description="Optional .hdr file name inside the view run results folder."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional output artifact name without extension."),
        ] = None,
        exposure: Annotated[
            int | None,
            Field(description="Optional exposure compensation in f-stops, equivalent to -e."),
        ] = None,
        gamma: Annotated[
            float | None,
            Field(description="Optional gamma correction, equivalent to -g."),
        ] = None,
        black_and_white: Annotated[
            bool | None,
            Field(description="Optional black-and-white output flag, equivalent to -b."),
        ] = None,
        colors: Annotated[
            int | None,
            Field(description="Optional color count limit, equivalent to -c."),
        ] = None,
        sampling_factor: Annotated[
            int | None,
            Field(description="Optional sampling factor for large images, equivalent to -n."),
        ] = None,
        additional_options: Annotated[
            str | None,
            Field(description="Optional raw ra_gif options string for SDK update_from_string."),
        ] = None,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for image artifacts."),
        ] = "artifacts/radiance/images",
    ) -> dict[str, Any]:
        """Create a GIF artifact from HDR input."""
        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            image_path=image_path,
            image_name=image_name,
            name=name,
            exposure=exposure,
            gamma=gamma,
            black_and_white=black_and_white,
            colors=colors,
            sampling_factor=sampling_factor,
            additional_options=additional_options,
            output_subdir=output_subdir,
        )
