"""Radiance HDR to GIF MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.visual import radiance_hdr_to_gif as service


def register(mcp: FastMCP) -> None:
    """Register the radiance_hdr_to_gif tool."""

    @mcp.tool(
        name="hdr_to_gif",
        description=(
            "Convert a Radiance HDR image artifact to a GIF image artifact for "
            "lightweight preview or sharing. Pass image_target from "
            "radiance_list_hdr_images or radiance_search_images. This converts "
            "an existing HDR artifact; it does not render a new view, create "
            "falsecolor output, or read grid results. Returns target, "
            "image_target, artifact_path, summary_view, and report."
        ),
        tags={
            "artifact",
            "convert",
            "radiance",
            "image",
            "result",
        },
        timeout=60,
    )
    def radiance_hdr_to_gif(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional completed point-in-time view radiance_run target. Poll the run before converting HDR artifacts."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        image_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative .hdr image path for direct artifact conversion."),
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
