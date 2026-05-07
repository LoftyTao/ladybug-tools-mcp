"""Natural-language alias for Radiance HDR falsecolor postprocess."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.visual import radiance_hdr_to_falsecolor as service


def _source_to_inputs(
    source: str | dict[str, Any] | None,
) -> tuple[str | None, dict[str, Any] | None]:
    if source is None:
        return None, None
    if isinstance(source, str):
        return source, None
    target = source.get("target") if isinstance(source.get("target"), dict) else source
    if target.get("target_type") == "radiance_run":
        return None, target
    return target.get("path") or target.get("image_path") or source.get("path"), None


def register(mcp: FastMCP) -> None:
    """Register create_radiance_falsecolor as an alias."""

    @mcp.tool(
        name="create_radiance_falsecolor",
        description="Alias for radiance_hdr_to_falsecolor. Create a falsecolor .hdr Garden artifact from a listed Radiance HDR image or completed view run.",
        tags={
            "honeybee-radiance",
            "radiance",
            "postprocess",
            "view",
            "image",
            "hdr",
            "falsecolor",
            "artifact",
            "write",
            "safe",
            "alias",
        },
        timeout=60,
    )
    def create_radiance_falsecolor(
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
        scale: Annotated[str | float | None, Field(description="Optional falsecolor legend scale.")] = None,
        limit: Annotated[str | float | None, Field(description="Alias for scale accepted for Agent compatibility.")] = None,
        legend_label: Annotated[str | None, Field(description="Optional legend label.")] = None,
        additional_options: Annotated[
            str | None,
            Field(description="Optional raw Falsecolor options string."),
        ] = None,
        spec: Annotated[
            str | None,
            Field(description="Optional falsecolor scale/spec hint accepted for Agent compatibility."),
        ] = None,
        specification: Annotated[
            str | None,
            Field(description="Alias for spec accepted for Agent compatibility."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a falsecolor HDR artifact."""
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
        if scale is None and limit is not None:
            scale = limit
        if image_name is None and output_name and str(output_name).lower().endswith(".hdr"):
            image_name = output_name
        _ = (spec, specification)
        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            image_path=image_path,
            image_name=image_name,
            name=name,
            scale=scale,
            legend_label=legend_label,
            additional_options=additional_options,
        )
