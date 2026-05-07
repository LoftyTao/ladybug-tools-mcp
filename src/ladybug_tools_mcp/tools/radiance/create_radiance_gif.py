"""Natural-language alias for Radiance HDR to GIF postprocess."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.visual import radiance_hdr_to_gif as service
from ladybug_tools_mcp.tools.radiance.create_radiance_falsecolor import _source_to_inputs


def register(mcp: FastMCP) -> None:
    """Register create_radiance_gif as an alias."""

    @mcp.tool(
        name="create_radiance_gif",
        description="Alias for radiance_hdr_to_gif. Create a GIF Garden artifact from a listed Radiance HDR image or completed view run.",
        tags={
            "honeybee-radiance",
            "radiance",
            "postprocess",
            "view",
            "image",
            "hdr",
            "gif",
            "artifact",
            "write",
            "safe",
            "alias",
        },
        timeout=60,
    )
    def create_radiance_gif(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional completed point-in-time-view radiance_run target."),
        ] = None,
        run_id: Annotated[str | None, Field(description="Optional run identifier.")] = None,
        image_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative .hdr image path."),
        ] = None,
        input_path: Annotated[
            str | None,
            Field(description="Alias for image_path accepted for Agent compatibility."),
        ] = None,
        hdr_image_path: Annotated[
            str | None,
            Field(description="Alias for image_path accepted for Agent compatibility."),
        ] = None,
        hdr_image_target: Annotated[
            str | dict[str, Any] | None,
            Field(description="Alias for hdr_image accepted for Agent compatibility."),
        ] = None,
        hdr_image: Annotated[
            str | dict[str, Any] | None,
            Field(description="Alias for image_path. Accepts a listed HDR match dict."),
        ] = None,
        source_hdr_target: Annotated[
            str | dict[str, Any] | None,
            Field(description="Alias for hdr_image or run_target accepted for Agent compatibility."),
        ] = None,
        hdr_run_output_target: Annotated[
            dict[str, Any] | None,
            Field(description="Alias for run_target accepted for Agent compatibility when the HDR comes from a completed view run."),
        ] = None,
        image_name: Annotated[str | None, Field(description="Optional .hdr file name.")] = None,
        output_name: Annotated[
            str | None,
            Field(description="Optional Agent output-name hint. Used as image_name only when it looks like an .hdr file name."),
        ] = None,
        name: Annotated[str | None, Field(description="Optional output artifact name.")] = None,
        identifier: Annotated[str | None, Field(description="Alias for name.")] = None,
        exposure: Annotated[int | None, Field(description="Optional exposure compensation.")] = None,
        gamma: Annotated[float | None, Field(description="Optional gamma correction.")] = None,
        colors: Annotated[int | None, Field(description="Optional color count limit.")] = None,
        max_width: Annotated[
            int | None,
            Field(description="Optional Agent size hint accepted for compatibility. Ignored by ra_gif."),
        ] = None,
        max_height: Annotated[
            int | None,
            Field(description="Optional Agent size hint accepted for compatibility. Ignored by ra_gif."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a GIF artifact from HDR input."""
        _ = (max_width, max_height)
        if run_target is None and hdr_run_output_target is not None:
            run_target = hdr_run_output_target
        if image_path is None and input_path is not None:
            image_path = input_path
        if image_path is None and hdr_image_path is not None:
            image_path = hdr_image_path
        if image_path is None and hdr_image_target is not None:
            hdr_image = hdr_image_target
        if image_path is None and hdr_image is not None:
            image_path, source_run = _source_to_inputs(hdr_image)
            run_target = run_target or source_run
        if image_path is None and source_hdr_target is not None:
            image_path, source_run = _source_to_inputs(source_hdr_target)
            run_target = run_target or source_run
        if name is None and identifier is not None:
            name = identifier
        if image_name is None and output_name and str(output_name).lower().endswith(".hdr"):
            image_name = output_name
        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            image_path=image_path,
            image_name=image_name,
            name=name,
            exposure=exposure,
            gamma=gamma,
            colors=colors,
        )
