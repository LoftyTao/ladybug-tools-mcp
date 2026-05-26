"""Create Honeybee Radiance Luminaire / IES MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.luminaires import create_radiance_luminaire as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_create_luminaire tool.'

    @mcp.tool(
        name="create_luminaire",
        description=(
            "Create a Honeybee Radiance Luminaire from IES LM-63 text or a "
            "Garden-contained IES file path. Supports LuminaireZone placement "
            "instances, CustomLamp settings, and Garden Properties Library "
            "saving with garden_root and return_object_dict=false. Use the "
            "returned target as a reusable luminaire or IES resource for "
            "Radiance workflows. This is not a Honeybee Energy lighting load."
        ),
        tags={
            "radiance",
            "model",
            "edit",
            "luminaire",
            "electric-lighting",
        },
        timeout=20,
    )
    def create_radiance_luminaire(
        ies_content: Annotated[
            str | None,
            Field(description="IES LM-63 file text. Provide exactly one of ies_content or ies_path."),
        ] = None,
        ies_path: Annotated[
            str | None,
            Field(description="Path to an existing IES LM-63 file. Provide exactly one of ies_path or ies_content."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional Luminaire identifier. If omitted, the SDK derives one from IES metadata or file name."),
        ] = None,
        instances: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional LuminaireZone instances. Each item needs point as [x,y,z] or Point3D dict, and may include spin, tilt, rotation, or aiming_point."),
        ] = None,
        custom_lamp: Annotated[
            dict[str, Any] | None,
            Field(description="Optional SDK CustomLamp dict or simple settings like {'mode':'rgb','rgb':[1,0.8,0.6]} or {'mode':'color_temperature','color_temperature':3000}."),
        ] = None,
        light_loss_factor: Annotated[
            float,
            Field(description="Positive light loss multiplier for lamp/system depreciation."),
        ] = 1.0,
        candela_multiplier: Annotated[
            float,
            Field(description="Positive candela multiplier applied to the IES distribution."),
        ] = 1.0,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full Luminaire object_dict. Set false with garden_root to keep Agent context compact."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance Luminaire from IES content or path."""
        return service(
            ies_content=ies_content,
            ies_path=ies_path,
            identifier=identifier,
            instances=instances,
            custom_lamp=custom_lamp,
            light_loss_factor=light_loss_factor,
            candela_multiplier=candela_multiplier,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
