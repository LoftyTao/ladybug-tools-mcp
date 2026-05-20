"""Honeybee Radiance modifier foundation creation services."""

from __future__ import annotations

from typing import Any

from honeybee_radiance.modifier.material.glass import Glass
from honeybee_radiance.modifier.material.metal import Metal
from honeybee_radiance.modifier.material.mirror import Mirror
from honeybee_radiance.modifier.material.plastic import Plastic
from honeybee_radiance.modifier.material.trans import Trans
from honeybee_radiance.modifier.modifierbase import Modifier

from ladybug_tools_mcp.contracts.report import make_report
from garden.libraries.properties import save_garden_properties_library_object


def _validate_unit_interval(value: float, field_name: str) -> float:
    value = float(value)
    if value < 0 or value > 1:
        raise ValueError(f"{field_name} must be between 0 and 1.")
    return value


def _coerce_rgb(
    *,
    simple_value: float | None,
    red: float | None,
    green: float | None,
    blue: float | None,
    simple_name: str,
    channel_prefix: str,
    default: float,
) -> tuple[tuple[float, float, float], str]:
    channels = (red, green, blue)
    if simple_value is not None and any(value is not None for value in channels):
        raise ValueError(
            f"Use either {simple_name} or complete r/g/b_{channel_prefix} channels, not both."
        )
    if simple_value is not None:
        value = _validate_unit_interval(simple_value, simple_name)
        return (value, value, value), simple_name
    if any(value is not None for value in channels):
        if not all(value is not None for value in channels):
            raise ValueError(
                f"Provide all three r/g/b_{channel_prefix} channels together."
            )
        return (
            _validate_unit_interval(red, f"r_{channel_prefix}"),
            _validate_unit_interval(green, f"g_{channel_prefix}"),
            _validate_unit_interval(blue, f"b_{channel_prefix}"),
        ), f"rgb_{channel_prefix}"
    value = _validate_unit_interval(default, simple_name)
    return (value, value, value), "default"


def _reflectance_rgb(
    *,
    rgb_reflectance: float | None,
    r_reflectance: float | None,
    g_reflectance: float | None,
    b_reflectance: float | None,
    default: float,
) -> tuple[tuple[float, float, float], str]:
    return _coerce_rgb(
        simple_value=rgb_reflectance,
        red=r_reflectance,
        green=g_reflectance,
        blue=b_reflectance,
        simple_name="rgb_reflectance",
        channel_prefix="reflectance",
        default=default,
    )


def _glass_rgb(
    *,
    rgb_transmittance: float | None,
    r_transmittance: float | None,
    g_transmittance: float | None,
    b_transmittance: float | None,
    rgb_transmissivity: float | None,
    r_transmissivity: float | None,
    g_transmissivity: float | None,
    b_transmissivity: float | None,
) -> tuple[tuple[float, float, float], str, bool]:
    transmittance_values = (rgb_transmittance, r_transmittance, g_transmittance, b_transmittance)
    transmissivity_values = (
        rgb_transmissivity,
        r_transmissivity,
        g_transmissivity,
        b_transmissivity,
    )
    has_transmittance = any(value is not None for value in transmittance_values)
    has_transmissivity = any(value is not None for value in transmissivity_values)
    if has_transmittance and has_transmissivity:
        raise ValueError("Use either glass transmittance inputs or transmissivity inputs, not both.")
    if has_transmittance:
        rgb, mode = _coerce_rgb(
            simple_value=rgb_transmittance,
            red=r_transmittance,
            green=g_transmittance,
            blue=b_transmittance,
            simple_name="rgb_transmittance",
            channel_prefix="transmittance",
            default=0.0,
        )
        return rgb, mode, True
    rgb, mode = _coerce_rgb(
        simple_value=rgb_transmissivity,
        red=r_transmissivity,
        green=g_transmissivity,
        blue=b_transmissivity,
        simple_name="rgb_transmissivity",
        channel_prefix="transmissivity",
        default=0.6,
    )
    return rgb, mode, False


def _summary(modifier: Modifier, *, modifier_kind: str, input_mode: str) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "type": modifier.__class__.__name__,
        "identifier": modifier.identifier,
        "modifier_kind": modifier_kind,
        "input_mode": input_mode,
    }
    if all(hasattr(modifier, field) for field in ("r_reflectance", "g_reflectance", "b_reflectance")):
        summary["rgb_reflectance"] = [
            round(float(modifier.r_reflectance), 6),
            round(float(modifier.g_reflectance), 6),
            round(float(modifier.b_reflectance), 6),
        ]
    if all(
        hasattr(modifier, field)
        for field in ("r_transmissivity", "g_transmissivity", "b_transmissivity")
    ):
        summary["rgb_transmissivity"] = [
            round(float(modifier.r_transmissivity), 6),
            round(float(modifier.g_transmissivity), 6),
            round(float(modifier.b_transmissivity), 6),
        ]
    for field in (
        "average_reflectance",
        "average_transmittance",
        "specularity",
        "roughness",
        "transmitted_diff",
        "transmitted_spec",
        "refraction_index",
    ):
        if hasattr(modifier, field):
            value = getattr(modifier, field)
            summary[field] = round(float(value), 6) if isinstance(value, float) else value
    return summary


def _result(
    modifier: Modifier,
    *,
    modifier_kind: str,
    input_mode: str,
    garden_root: str | None,
    return_object_dict: bool,
) -> dict[str, Any]:
    result = {
        "object_dict": modifier.to_dict(),
        "summary_view": _summary(
            modifier,
            modifier_kind=modifier_kind,
            input_mode=input_mode,
        ),
        "report": make_report(
            status="ok",
            message=f"Created Honeybee Radiance {modifier.__class__.__name__}: {modifier.identifier}",
        ),
    }
    if not garden_root:
        return result
    saved = save_garden_properties_library_object(
        garden_root=garden_root,
        domain="honeybee_radiance",
        object_family="modifier",
        object_dict=result["object_dict"],
    )
    result["target"] = saved["target"]
    result["persistence_receipt"] = saved["persistence_receipt"]
    result["summary_view"]["target"] = saved["target"]
    result["summary_view"]["ready_for"] = "radiance modifier inputs"
    if not return_object_dict:
        result.pop("object_dict", None)
    return result


def create_radiance_opaque_modifier(
    *,
    identifier: str,
    rgb_reflectance: float | None = None,
    r_reflectance: float | None = None,
    g_reflectance: float | None = None,
    b_reflectance: float | None = None,
    specularity: float = 0.0,
    roughness: float = 0.0,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create an opaque Radiance modifier using the SDK Plastic material."""
    rgb, input_mode = _reflectance_rgb(
        rgb_reflectance=rgb_reflectance,
        r_reflectance=r_reflectance,
        g_reflectance=g_reflectance,
        b_reflectance=b_reflectance,
        default=0.5,
    )
    modifier = Plastic(
        identifier,
        *rgb,
        specularity=_validate_unit_interval(specularity, "specularity"),
        roughness=_validate_unit_interval(roughness, "roughness"),
    )
    return _result(
        modifier,
        modifier_kind="opaque",
        input_mode=input_mode,
        garden_root=garden_root,
        return_object_dict=return_object_dict,
    )


def create_radiance_mirror_modifier(
    *,
    identifier: str,
    rgb_reflectance: float | None = None,
    r_reflectance: float | None = None,
    g_reflectance: float | None = None,
    b_reflectance: float | None = None,
    alternate_material: str | None = None,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Radiance Mirror modifier."""
    rgb, input_mode = _reflectance_rgb(
        rgb_reflectance=rgb_reflectance,
        r_reflectance=r_reflectance,
        g_reflectance=g_reflectance,
        b_reflectance=b_reflectance,
        default=1.0,
    )
    modifier = Mirror(
        identifier,
        *rgb,
        alternate_material=alternate_material,
    )
    return _result(
        modifier,
        modifier_kind="mirror",
        input_mode=input_mode,
        garden_root=garden_root,
        return_object_dict=return_object_dict,
    )


def create_radiance_metal_modifier(
    *,
    identifier: str,
    rgb_reflectance: float | None = None,
    r_reflectance: float | None = None,
    g_reflectance: float | None = None,
    b_reflectance: float | None = None,
    specularity: float = 0.9,
    roughness: float = 0.0,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Radiance Metal modifier."""
    rgb, input_mode = _reflectance_rgb(
        rgb_reflectance=rgb_reflectance,
        r_reflectance=r_reflectance,
        g_reflectance=g_reflectance,
        b_reflectance=b_reflectance,
        default=0.7,
    )
    modifier = Metal(
        identifier,
        *rgb,
        specularity=_validate_unit_interval(specularity, "specularity"),
        roughness=_validate_unit_interval(roughness, "roughness"),
    )
    return _result(
        modifier,
        modifier_kind="metal",
        input_mode=input_mode,
        garden_root=garden_root,
        return_object_dict=return_object_dict,
    )


def create_radiance_trans_modifier(
    *,
    identifier: str,
    rgb_reflectance: float | None = None,
    r_reflectance: float | None = None,
    g_reflectance: float | None = None,
    b_reflectance: float | None = None,
    specularity: float = 0.0,
    roughness: float = 0.0,
    transmitted_diff: float = 0.0,
    transmitted_spec: float = 0.0,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Radiance Trans modifier."""
    rgb, input_mode = _reflectance_rgb(
        rgb_reflectance=rgb_reflectance,
        r_reflectance=r_reflectance,
        g_reflectance=g_reflectance,
        b_reflectance=b_reflectance,
        default=0.4,
    )
    modifier = Trans(
        identifier,
        *rgb,
        specularity=_validate_unit_interval(specularity, "specularity"),
        roughness=_validate_unit_interval(roughness, "roughness"),
        transmitted_diff=_validate_unit_interval(transmitted_diff, "transmitted_diff"),
        transmitted_spec=_validate_unit_interval(transmitted_spec, "transmitted_spec"),
    )
    return _result(
        modifier,
        modifier_kind="trans",
        input_mode=input_mode,
        garden_root=garden_root,
        return_object_dict=return_object_dict,
    )


def create_radiance_glass_modifier(
    *,
    identifier: str,
    rgb_transmittance: float | None = None,
    r_transmittance: float | None = None,
    g_transmittance: float | None = None,
    b_transmittance: float | None = None,
    rgb_transmissivity: float | None = None,
    r_transmissivity: float | None = None,
    g_transmissivity: float | None = None,
    b_transmissivity: float | None = None,
    refraction_index: float | None = None,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Radiance Glass modifier."""
    rgb, input_mode, is_transmittance = _glass_rgb(
        rgb_transmittance=rgb_transmittance,
        r_transmittance=r_transmittance,
        g_transmittance=g_transmittance,
        b_transmittance=b_transmittance,
        rgb_transmissivity=rgb_transmissivity,
        r_transmissivity=r_transmissivity,
        g_transmissivity=g_transmissivity,
        b_transmissivity=b_transmissivity,
    )
    if is_transmittance:
        modifier = Glass.from_transmittance(
            identifier,
            *rgb,
            refraction_index=refraction_index,
        )
    else:
        modifier = Glass(
            identifier,
            *rgb,
            refraction_index=refraction_index,
        )
    result = _result(
        modifier,
        modifier_kind="glass",
        input_mode=input_mode,
        garden_root=garden_root,
        return_object_dict=return_object_dict,
    )
    if is_transmittance:
        result["summary_view"]["rgb_transmittance"] = [
            round(float(rgb[0]), 6),
            round(float(rgb[1]), 6),
            round(float(rgb[2]), 6),
        ]
    return result
