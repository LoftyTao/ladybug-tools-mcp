"""Radiance HDR falsecolor MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.visual import radiance_hdr_to_falsecolor as service


def register(mcp: FastMCP) -> None:
    """Register the radiance_hdr_to_falsecolor tool."""

    @mcp.tool(
        name="radiance_hdr_to_falsecolor",
        description="Canonical Radiance HDR falsecolor postprocess tool. Create a falsecolor .hdr Garden artifact from a Radiance .hdr image using the SDK Falsecolor command wrapper. This tool only accepts .hdr input and writes .hdr output; .pic and .unf are intentionally unsupported. Use list_radiance_hdr_images to select an image from a completed view run.",
        tags={
            "honeybee-radiance",
            "radiance",
            "run-radiance",
            "postprocess",
            "view",
            "image",
            "hdr",
            "falsecolor",
            "artifact",
            "write",
            "safe",
        },
        timeout=60,
    )
    def radiance_hdr_to_falsecolor(
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
        scale: Annotated[
            str | float | None,
            Field(description="Optional falsecolor legend scale. Use a number or Radiance auto scale text."),
        ] = None,
        legend_label: Annotated[
            str | None,
            Field(description="Optional legend label, such as Lux or cd/m2."),
        ] = None,
        legend_multiplier: Annotated[
            float | None,
            Field(description="Optional falsecolor multiplier, equivalent to -m."),
        ] = None,
        contour_lines: Annotated[
            bool | None,
            Field(description="Optional contour line flag, equivalent to -cl."),
        ] = None,
        contour_bands: Annotated[
            bool | None,
            Field(description="Optional contour band flag, equivalent to -cb."),
        ] = None,
        palette: Annotated[
            str | None,
            Field(description="Optional falsecolor palette, equivalent to -pal."),
        ] = None,
        additional_options: Annotated[
            str | None,
            Field(description="Optional raw Falsecolor options string for SDK update_from_string."),
        ] = None,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for image artifacts."),
        ] = "artifacts/radiance/images",
    ) -> dict[str, Any]:
        """Create a falsecolor HDR artifact."""
        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            image_path=image_path,
            image_name=image_name,
            name=name,
            scale=scale,
            legend_label=legend_label,
            legend_multiplier=legend_multiplier,
            contour_lines=contour_lines,
            contour_bands=contour_bands,
            palette=palette,
            additional_options=additional_options,
            output_subdir=output_subdir,
        )
