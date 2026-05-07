"""Create generic opaque Honeybee Radiance modifier MCP alias tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.modifiers import (
    create_radiance_glass_modifier as glass_service,
    create_radiance_opaque_modifier as service,
)


def register(mcp: FastMCP) -> None:
    """Register the create_radiance_modifier alias tool."""

    @mcp.tool(
        name="create_radiance_modifier",
        description="Agent-friendly alias for common Radiance modifier creation. Creates opaque/plastic modifiers from reflectance inputs and routes glass modifier_type requests to create_radiance_glass_modifier-style transmittance/transmissivity inputs.",
        tags={
            "honeybee-radiance",
            "radiance",
            "modifier",
            "material",
            "opaque",
            "plastic",
            "glass",
            "alias",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_radiance_modifier(
        identifier: Annotated[str, Field(description="Radiance modifier identifier.")],
        modifier_type: Annotated[
            str | None,
            Field(description="Optional Agent hint such as plastic or opaque. This alias creates opaque/plastic modifiers."),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional human-facing name hint accepted for Agent compatibility; Radiance modifiers use identifier as their persisted name."),
        ] = None,
        rgb_reflectance: Annotated[
            float | list[float] | None,
            Field(description="Simple reflectance or [r, g, b] reflectance values."),
        ] = None,
        reflectivity: Annotated[
            float | None,
            Field(description="Natural-language alias for rgb_reflectance on opaque/plastic modifiers."),
        ] = None,
        r_reflectance: Annotated[
            float | None,
            Field(description="Red reflectance. Provide with g_reflectance and b_reflectance."),
        ] = None,
        g_reflectance: Annotated[
            float | None,
            Field(description="Green reflectance. Provide with r_reflectance and b_reflectance."),
        ] = None,
        b_reflectance: Annotated[
            float | None,
            Field(description="Blue reflectance. Provide with r_reflectance and g_reflectance."),
        ] = None,
        transmittance: Annotated[
            float | list[float] | None,
            Field(description="Optional glass transmittance alias used when modifier_type is glass. Accepts a number or [r, g, b] values."),
        ] = None,
        transmissivity: Annotated[
            float | list[float] | None,
            Field(description="Optional glass transmissivity alias used when modifier_type is glass. Accepts a number or [r, g, b] values."),
        ] = None,
        transmission: Annotated[
            float | list[float] | None,
            Field(description="Natural-language glass transmission alias; interpreted as transmissivity when modifier_type is glass. Accepts a number or [r, g, b] values."),
        ] = None,
        modifier_dict: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Agent fallback dict. For glass, simple transmittance/transmissivity keys are extracted."),
        ] = None,
        specularity: Annotated[float, Field(description="Plastic specularity fraction.")] = 0.0,
        specular: Annotated[
            float | None,
            Field(description="Natural-language alias for specularity on opaque/plastic modifiers."),
        ] = None,
        roughness: Annotated[float, Field(description="Plastic roughness fraction.")] = 0.0,
        garden_root: Annotated[
            str | None,
            Field(description="Optional Garden root for saving this modifier."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full modifier object_dict. Set false with garden_root."),
        ] = True,
    ) -> dict:
        """Create an opaque Honeybee Radiance modifier through a generic alias."""
        _ = display_name
        normalized_type = None
        if modifier_type is not None:
            normalized_type = modifier_type.strip().lower().replace("-", "_").replace(" ", "_")
            if normalized_type not in {"plastic", "opaque", "opaque_modifier", "radiance_modifier", "glass"}:
                raise ValueError(
                    "create_radiance_modifier supports opaque/plastic and simple glass modifiers; use a specific Radiance modifier tool for metal, mirror, or trans."
                )
        if normalized_type == "glass":
            fallback = {
                str(key).strip().lower().replace(" ", "_"): value
                for key, value in (modifier_dict or {}).items()
            }
            if transmittance is None:
                transmittance = fallback.get("transmittance")
            if transmissivity is None:
                transmissivity = fallback.get("transmissivity")
            if transmissivity is None and transmission is not None:
                transmissivity = transmission
            r_transmittance = g_transmittance = b_transmittance = None
            r_transmissivity = g_transmissivity = b_transmissivity = None
            if isinstance(transmittance, list):
                if len(transmittance) != 3:
                    raise ValueError("transmittance list must have three values.")
                r_transmittance, g_transmittance, b_transmittance = [
                    float(value) for value in transmittance
                ]
                transmittance = None
            if isinstance(transmissivity, list):
                if len(transmissivity) != 3:
                    raise ValueError("transmissivity list must have three values.")
                r_transmissivity, g_transmissivity, b_transmissivity = [
                    float(value) for value in transmissivity
                ]
                transmissivity = None
            return glass_service(
                identifier=identifier,
                rgb_transmittance=transmittance,
                r_transmittance=r_transmittance,
                g_transmittance=g_transmittance,
                b_transmittance=b_transmittance,
                rgb_transmissivity=transmissivity,
                r_transmissivity=r_transmissivity,
                g_transmissivity=g_transmissivity,
                b_transmissivity=b_transmissivity,
                refraction_index=None,
                garden_root=garden_root,
                return_object_dict=return_object_dict,
            )
        if rgb_reflectance is None and reflectivity is not None:
            rgb_reflectance = reflectivity
        if specular is not None:
            specularity = specular
        if isinstance(rgb_reflectance, list):
            if len(rgb_reflectance) != 3:
                raise ValueError("rgb_reflectance list must have three values.")
            r_reflectance, g_reflectance, b_reflectance = [
                float(value) for value in rgb_reflectance
            ]
            rgb_reflectance = None
        return service(
            identifier=identifier,
            rgb_reflectance=rgb_reflectance,
            r_reflectance=r_reflectance,
            g_reflectance=g_reflectance,
            b_reflectance=b_reflectance,
            specularity=specularity,
            roughness=roughness,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
