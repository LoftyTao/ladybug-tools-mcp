"""Fairyfly THERM material payload services."""

from __future__ import annotations

from typing import Any

from fairyfly_therm.material.solid import SolidMaterial
from ladybug.color import Color

from ladybug_tools_mcp.contracts.report import make_report


def _color_from_rgb(rgb_color: list[int] | None) -> Color | None:
    if rgb_color is None:
        return None
    if len(rgb_color) != 3:
        raise ValueError("rgb_color must be [r, g, b].")
    return Color(*(int(value) for value in rgb_color))


def _material_summary(material_dict: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": material_dict.get("type"),
        "identifier": material_dict.get("identifier"),
        "display_name": material_dict.get("display_name")
        or material_dict.get("identifier"),
        "conductivity": material_dict.get("conductivity"),
        "emissivity": material_dict.get("emissivity"),
        "color": material_dict.get("color"),
    }


def create_fairyfly_solid_material(
    *,
    name: str,
    conductivity: float,
    emissivity: float = 0.9,
    emissivity_back: float | None = None,
    density: float | None = None,
    porosity: float | None = None,
    specific_heat: float | None = None,
    vapor_diffusion_resistance: float | None = None,
    reflectance: float | None = None,
    transmittance: float | None = None,
    rgb_color: list[int] | None = None,
) -> dict[str, Any]:
    """Create a Fairyfly SolidMaterial payload."""
    material = SolidMaterial(
        conductivity=conductivity,
        emissivity=emissivity,
        emissivity_back=emissivity_back,
        density=density,
        porosity=porosity,
        specific_heat=specific_heat,
        vapor_diffusion_resistance=vapor_diffusion_resistance,
        reflectance=reflectance,
        transmittance=transmittance,
    )
    material.display_name = name
    material.color = _color_from_rgb(rgb_color) or Color(180, 180, 180)
    material_dict = material.to_dict()
    return {
        "object_dict": material_dict,
        "target": material_dict,
        "summary_view": _material_summary(material_dict),
        "report": make_report(
            status="ok",
            message=f"Created Fairyfly solid material: {name}",
        ),
    }
