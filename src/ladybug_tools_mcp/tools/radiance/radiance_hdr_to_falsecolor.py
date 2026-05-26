"""Radiance HDR falsecolor MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.visual import radiance_hdr_to_falsecolor as service


def register(mcp: FastMCP) -> None:
    """Register the radiance_hdr_to_falsecolor tool."""

    @mcp.tool(
        name="hdr_to_falsecolor",
        description=(
            "Convert a Radiance HDR image artifact to a falsecolor image "
            "artifact for daylight or glare review. Pass image_target from "
            "radiance_list_hdr_images or radiance_search_images. This converts "
            "an existing HDR artifact; it does not render a new view or read "
            "grid results. Returns target, image_target, artifact_path, "
            "summary_view, and report."
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
    def radiance_hdr_to_falsecolor(
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
