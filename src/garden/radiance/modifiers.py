"""Honeybee Radiance modifier foundation creation services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from honeybee_radiance.lib.modifiers import modifier_by_identifier
from honeybee_radiance.lib.modifiersets import modifier_set_by_identifier
from honeybee_radiance.modifier.material.absdf import aBSDF
from honeybee_radiance.modifier.material.brtdfunc import BRTDfunc
from honeybee_radiance.modifier.material.bsdf import BSDF
from honeybee_radiance.modifier.material.dielectric import Dielectric
from honeybee_radiance.modifier.material.glass import Glass
from honeybee_radiance.modifier.material.glow import Glow
from honeybee_radiance.modifier.material.illum import Illum
from honeybee_radiance.modifier.material.light import Light
from honeybee_radiance.modifier.material.metal import Metal
from honeybee_radiance.modifier.material.metal2 import Metal2
from honeybee_radiance.modifier.material.mirror import Mirror
from honeybee_radiance.modifier.material.plastic import Plastic
from honeybee_radiance.modifier.material.plastic2 import Plastic2
from honeybee_radiance.modifier.material.spotlight import Spotlight
from honeybee_radiance.modifier.material.trans import Trans
from honeybee_radiance.modifier.material.trans2 import Trans2
from honeybee_radiance.modifier.modifierbase import Modifier
from honeybee_radiance.modifierset import (
    ApertureModifierSet,
    DoorModifierSet,
    FloorModifierSet,
    ModifierSet,
    RoofCeilingModifierSet,
    ShadeModifierSet,
    WallModifierSet,
)
from honeybee_radiance.mutil import dict_to_modifier
from honeybee_radiance.primitive import Primitive, Void

from garden.libraries.properties import (
    get_garden_properties_library_object,
    save_garden_properties_library_object,
)
from ladybug_tools_mcp.contracts import make_report


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


def _resolve_modifier_input(
    value: Any,
    *,
    garden_root: str | None = None,
    field_name: str = "modifier",
) -> Modifier | None:
    """Resolve a parent or child Radiance Modifier from target, string id, or dict."""
    if value is None:
        return None
    if isinstance(value, Modifier):
        return value
    if isinstance(value, dict) and value.get("target_type") == "garden_properties_library_object":
        if not garden_root:
            raise ValueError(f"{field_name} library target requires garden_root.")
        if value.get("domain") != "honeybee_radiance" or value.get("object_family") != "modifier":
            raise ValueError(f"{field_name} target must reference honeybee_radiance:modifier.")
        value = get_garden_properties_library_object(
            garden_root=garden_root,
            target=value,
        )["object_dict"]
    if isinstance(value, dict) and isinstance(value.get("object_dict"), dict):
        value = value["object_dict"]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped.lower() == "void":
            return None if field_name == "modifier" else Void()
        try:
            return modifier_by_identifier(stripped)
        except Exception as exc:
            raise ValueError(f"Unknown {field_name} identifier '{value}': {exc}") from exc
    if isinstance(value, dict):
        try:
            return dict_to_modifier(value)
        except Exception as exc:
            raise ValueError(f"Invalid {field_name} dict: {exc}") from exc
    raise ValueError(f"{field_name} must be a modifier identifier, dict, or Garden library target.")


def create_radiance_opaque_modifier(
    *,
    identifier: str,
    rgb_reflectance: float | None = None,
    r_reflectance: float | None = None,
    g_reflectance: float | None = None,
    b_reflectance: float | None = None,
    specularity: float = 0.0,
    roughness: float = 0.0,
    modifier: dict[str, Any] | str | None = None,
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
    parent = _resolve_modifier_input(modifier, garden_root=garden_root)
    mod_obj = Plastic(
        identifier,
        *rgb,
        specularity=_validate_unit_interval(specularity, "specularity"),
        roughness=_validate_unit_interval(roughness, "roughness"),
        modifier=parent,
    )
    return _result(
        mod_obj,
        modifier_kind="opaque",
        input_mode=input_mode,
        garden_root=garden_root,
        return_object_dict=return_object_dict,
    )


def _resolve_alternate_material(value: Any, *, garden_root: str | None = None) -> Any:
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() == "void":
        return Void()
    return _resolve_modifier_input(value, garden_root=garden_root, field_name="alternate_material")


def create_radiance_mirror_modifier(
    *,
    identifier: str,
    rgb_reflectance: float | None = None,
    r_reflectance: float | None = None,
    g_reflectance: float | None = None,
    b_reflectance: float | None = None,
    alternate_material: str | dict[str, Any] | None = None,
    modifier: dict[str, Any] | str | None = None,
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
    parent = _resolve_modifier_input(modifier, garden_root=garden_root)
    mod_obj = Mirror(
        identifier,
        *rgb,
        alternate_material=_resolve_alternate_material(
            alternate_material, garden_root=garden_root
        ),
    )
    if parent is not None:
        mod_obj.modifier = parent
    return _result(
        mod_obj,
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
    modifier: dict[str, Any] | str | None = None,
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
    parent = _resolve_modifier_input(modifier, garden_root=garden_root)
    mod_obj = Metal(
        identifier,
        *rgb,
        specularity=_validate_unit_interval(specularity, "specularity"),
        roughness=_validate_unit_interval(roughness, "roughness"),
        modifier=parent,
    )
    return _result(
        mod_obj,
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
    modifier: dict[str, Any] | str | None = None,
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
    parent = _resolve_modifier_input(modifier, garden_root=garden_root)
    mod_obj = Trans(
        identifier,
        *rgb,
        specularity=_validate_unit_interval(specularity, "specularity"),
        roughness=_validate_unit_interval(roughness, "roughness"),
        transmitted_diff=_validate_unit_interval(transmitted_diff, "transmitted_diff"),
        transmitted_spec=_validate_unit_interval(transmitted_spec, "transmitted_spec"),
        modifier=parent,
    )
    return _result(
        mod_obj,
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
    modifier: dict[str, Any] | str | None = None,
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
    parent = _resolve_modifier_input(modifier, garden_root=garden_root)
    if is_transmittance:
        mod_obj = Glass.from_transmittance(
            identifier,
            *rgb,
            refraction_index=refraction_index,
            modifier=parent,
        )
    else:
        mod_obj = Glass(
            identifier,
            *rgb,
            refraction_index=refraction_index,
            modifier=parent,
        )
    result = _result(
        mod_obj,
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


def _non_negative_rgb(
    merged: dict[str, Any],
    *,
    simple_key: str,
    prefix: str,
    default: float,
) -> tuple[float, float, float]:
    simple_val = merged.get(simple_key)
    r_val = merged.get(f"r_{prefix}")
    g_val = merged.get(f"g_{prefix}")
    b_val = merged.get(f"b_{prefix}")
    if isinstance(simple_val, (list, tuple)):
        if len(simple_val) != 3:
            raise ValueError(f"{simple_key} list must have three values.")
        rgb = (float(simple_val[0]), float(simple_val[1]), float(simple_val[2]))
    elif simple_val is not None:
        v = float(simple_val)
        rgb = (v, v, v)
    elif any(val is not None for val in (r_val, g_val, b_val)):
        if not all(val is not None for val in (r_val, g_val, b_val)):
            raise ValueError(f"Provide all three r/g/b_{prefix} channels together.")
        rgb = (float(r_val), float(g_val), float(b_val))
    else:
        v = float(default)
        rgb = (v, v, v)
    if any(ch < 0 for ch in rgb):
        raise ValueError(f"{prefix} values must be non-negative.")
    return rgb


def _resolve_bsdf_file(bsdf_file: str, *, garden_root: str | None) -> str:
    candidate = Path(bsdf_file).expanduser()
    if not candidate.is_absolute() and garden_root:
        rooted = (Path(garden_root).expanduser().resolve() / candidate).resolve()
        if rooted.is_file():
            return str(rooted)
    resolved = candidate.resolve()
    if not resolved.is_file():
        raise ValueError(f"BSDF XML file was not found: {bsdf_file}")
    return str(resolved)


def _create_anisotropic_modifier(
    modifier_type: str,
    *,
    identifier: str,
    merged: dict[str, Any],
    parent: Modifier | None,
) -> Modifier:
    if merged.get("values") is not None:
        vals = merged["values"]
    else:
        rgb_r, r_r, g_r, b_r = _unpack_rgb_channels(
            merged,
            simple_key="rgb_reflectance",
            channel_prefix="reflectance",
        )
        rgb, _ = _reflectance_rgb(
            rgb_reflectance=rgb_r,
            r_reflectance=r_r,
            g_reflectance=g_r,
            b_reflectance=b_r,
            default=0.7 if modifier_type == "metal2" else 0.5,
        )
        direction = merged.get("direction", [1, 0, 0])
        if not isinstance(direction, (list, tuple)) or len(direction) != 3:
            raise ValueError("direction must be [ux, uy, uz] for anisotropic materials.")
        funcfile = str(merged.get("function_file") or ".")
        spec = _validate_unit_interval(
            merged["specularity"] if merged.get("specularity") is not None else (0.9 if modifier_type == "metal2" else 0.0),
            "specularity",
        )
        u_rough = _validate_unit_interval(
            merged["u_roughness"] if merged.get("u_roughness") is not None else 0.05,
            "u_roughness",
        )
        v_rough = _validate_unit_interval(
            merged["v_roughness"] if merged.get("v_roughness") is not None else 0.1,
            "v_roughness",
        )
        reals = [rgb[0], rgb[1], rgb[2], spec, u_rough, v_rough]
        if modifier_type == "trans2":
            reals.extend([
                _validate_unit_interval(
                    merged["transmitted_diff"] if merged.get("transmitted_diff") is not None else 0.0,
                    "transmitted_diff",
                ),
                _validate_unit_interval(
                    merged["transmitted_spec"] if merged.get("transmitted_spec") is not None else 0.0,
                    "transmitted_spec",
                ),
            ])
        vals = [[str(direction[0]), str(direction[1]), str(direction[2]), funcfile], [], reals]
    cls_map = {"plastic2": Plastic2, "metal2": Metal2, "trans2": Trans2}
    return cls_map[modifier_type](
        identifier,
        modifier=parent,
        values=vals,
        is_opaque=modifier_type != "trans2",
    )


def _create_raw_rad_modifier(
    *,
    identifier: str,
    rad_text: str,
    parent: Modifier | None,
) -> Primitive:
    text = rad_text.strip()
    if not text:
        raise ValueError("rad_text must contain a Radiance primitive definition.")
    try:
        prim = Primitive.from_string(text)
    except Exception:
        blocks: list[list[str]] = []
        current: list[str] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            tokens = line.split()
            if len(tokens) == 3 and not tokens[0].isdigit() and current:
                blocks.append(current)
                current = [line]
            else:
                current.append(line)
        if current:
            blocks.append(current)
        if not blocks:
            raise ValueError("Could not parse Radiance primitive from rad_text.")
        parsed = [Primitive.from_string("\n".join(blk)) for blk in blocks]
        prim = parsed[-1]
        if len(parsed) > 1:
            prim = Primitive(
                prim.type,
                prim.identifier,
                modifier=prim.modifier,
                values=prim.values,
                is_opaque=prim.is_opaque,
                dependencies=parsed[:-1],
            )
    if identifier:
        prim.identifier = identifier
    if parent is not None:
        prim.modifier = parent
    try:
        return dict_to_modifier(prim.to_dict())
    except Exception:
        return prim


_MODIFIER_ALLOWED_KEYS = {
    "opaque": {
        "rgb_reflectance",
        "r_reflectance",
        "g_reflectance",
        "b_reflectance",
        "specularity",
        "roughness",
        "modifier",
    },
    "metal": {
        "rgb_reflectance",
        "r_reflectance",
        "g_reflectance",
        "b_reflectance",
        "specularity",
        "roughness",
        "modifier",
    },
    "mirror": {
        "rgb_reflectance",
        "r_reflectance",
        "g_reflectance",
        "b_reflectance",
        "alternate_material",
        "modifier",
    },
    "trans": {
        "rgb_reflectance",
        "r_reflectance",
        "g_reflectance",
        "b_reflectance",
        "specularity",
        "roughness",
        "transmitted_diff",
        "transmitted_spec",
        "modifier",
    },
    "glass": {
        "rgb_transmittance",
        "r_transmittance",
        "g_transmittance",
        "b_transmittance",
        "rgb_transmissivity",
        "r_transmissivity",
        "g_transmissivity",
        "b_transmissivity",
        "refraction_index",
        "modifier",
    },
    "bsdf": {
        "bsdf_file",
        "xml_path",
        "up_orientation",
        "thickness",
        "function_file",
        "transform",
        "angle_basis",
        "modifier",
    },
    "absdf": {
        "bsdf_file",
        "xml_path",
        "up_orientation",
        "function_file",
        "transform",
        "angle_basis",
        "modifier",
    },
    "glow": {
        "rgb_emittance",
        "r_emittance",
        "g_emittance",
        "b_emittance",
        "max_radius",
        "modifier",
    },
    "light": {
        "rgb_emittance",
        "r_emittance",
        "g_emittance",
        "b_emittance",
        "modifier",
    },
    "spotlight": {
        "rgb_emittance",
        "r_emittance",
        "g_emittance",
        "b_emittance",
        "angle",
        "cone_angle",
        "direction",
        "values",
        "modifier",
    },
    "illum": {
        "rgb_emittance",
        "r_emittance",
        "g_emittance",
        "b_emittance",
        "alternate_material",
        "values",
        "modifier",
    },
    "dielectric": {
        "rgb_transmission",
        "r_transmission",
        "g_transmission",
        "b_transmission",
        "refraction_index",
        "hartmann_constant",
        "values",
        "modifier",
    },
    "brtdfunc": {
        "values",
        "is_opaque",
        "modifier",
    },
    "plastic2": {
        "rgb_reflectance",
        "r_reflectance",
        "g_reflectance",
        "b_reflectance",
        "specularity",
        "u_roughness",
        "v_roughness",
        "direction",
        "function_file",
        "values",
        "modifier",
    },
    "metal2": {
        "rgb_reflectance",
        "r_reflectance",
        "g_reflectance",
        "b_reflectance",
        "specularity",
        "u_roughness",
        "v_roughness",
        "direction",
        "function_file",
        "values",
        "modifier",
    },
    "trans2": {
        "rgb_reflectance",
        "r_reflectance",
        "g_reflectance",
        "b_reflectance",
        "specularity",
        "u_roughness",
        "v_roughness",
        "transmitted_diff",
        "transmitted_spec",
        "direction",
        "function_file",
        "values",
        "modifier",
    },
    "raw_rad": {
        "rad_text",
        "primitive_string",
        "radiance_string",
        "modifier",
    },
}

_MODIFIER_ALIASES = {
    "reflectance": "rgb_reflectance",
    "transmittance": "rgb_transmittance",
    "transmissivity": "rgb_transmissivity",
    "emittance": "rgb_emittance",
    "transmission": "rgb_transmission",
    "xml_path": "bsdf_file",
    "primitive_string": "rad_text",
    "radiance_string": "rad_text",
    "cone_angle": "angle",
}


def _unpack_rgb_channels(
    merged: dict[str, Any],
    *,
    simple_key: str,
    channel_prefix: str,
) -> tuple[float | None, float | None, float | None, float | None]:
    simple_val = merged.get(simple_key)
    r_val = merged.get(f"r_{channel_prefix}")
    g_val = merged.get(f"g_{channel_prefix}")
    b_val = merged.get(f"b_{channel_prefix}")
    if isinstance(simple_val, (list, tuple)):
        if len(simple_val) != 3:
            raise ValueError(f"{simple_key} list must have three values.")
        if any(channel is not None for channel in (r_val, g_val, b_val)):
            raise ValueError(
                f"Use either {simple_key} or r/g/b_{channel_prefix} channels, not both."
            )
        return None, float(simple_val[0]), float(simple_val[1]), float(simple_val[2])
    return (
        float(simple_val) if simple_val is not None else None,
        float(r_val) if r_val is not None else None,
        float(g_val) if g_val is not None else None,
        float(b_val) if b_val is not None else None,
    )


def create_radiance_modifier(
    *,
    modifier_type: str,
    identifier: str,
    rgb_reflectance: float | list[float] | None = None,
    specularity: float | None = None,
    roughness: float | None = None,
    transmitted_diff: float | None = None,
    transmitted_spec: float | None = None,
    alternate_material: str | dict[str, Any] | None = None,
    rgb_transmittance: float | list[float] | None = None,
    rgb_transmissivity: float | list[float] | None = None,
    refraction_index: float | None = None,
    modifier: dict[str, Any] | str | None = None,
    params: dict[str, Any] | None = None,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Radiance modifier (opaque, glass, metal, mirror, trans, bsdf, glow, etc.)."""
    normalized_type = modifier_type.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized_type == "plastic":
        normalized_type = "opaque"
    if normalized_type not in _MODIFIER_ALLOWED_KEYS:
        raise ValueError(
            "modifier_type must be one of: " + ", ".join(sorted(_MODIFIER_ALLOWED_KEYS)) + "."
        )

    merged: dict[str, Any] = {}
    if params is not None:
        if not isinstance(params, dict):
            raise ValueError("params must be a dictionary of modifier parameters.")
        merged.update(params)

    for alias_key, canonical_key in _MODIFIER_ALIASES.items():
        if alias_key in merged:
            alias_value = merged.pop(alias_key)
            if canonical_key not in merged:
                merged[canonical_key] = alias_value

    for key, value in (
        ("rgb_reflectance", rgb_reflectance),
        ("specularity", specularity),
        ("roughness", roughness),
        ("transmitted_diff", transmitted_diff),
        ("transmitted_spec", transmitted_spec),
        ("alternate_material", alternate_material),
        ("rgb_transmittance", rgb_transmittance),
        ("rgb_transmissivity", rgb_transmissivity),
        ("refraction_index", refraction_index),
        ("modifier", modifier),
    ):
        if value is not None:
            merged[key] = value

    unknown = sorted(set(merged) - _MODIFIER_ALLOWED_KEYS[normalized_type])
    if unknown:
        raise ValueError(
            f"Unsupported parameter(s) for modifier_type='{normalized_type}': "
            + ", ".join(unknown)
        )

    parent = _resolve_modifier_input(merged.get("modifier"), garden_root=garden_root)

    if normalized_type == "glass":
        rgb_t, r_t, g_t, b_t = _unpack_rgb_channels(
            merged,
            simple_key="rgb_transmittance",
            channel_prefix="transmittance",
        )
        rgb_tv, r_tv, g_tv, b_tv = _unpack_rgb_channels(
            merged,
            simple_key="rgb_transmissivity",
            channel_prefix="transmissivity",
        )
        return create_radiance_glass_modifier(
            identifier=identifier,
            rgb_transmittance=rgb_t,
            r_transmittance=r_t,
            g_transmittance=g_t,
            b_transmittance=b_t,
            rgb_transmissivity=rgb_tv,
            r_transmissivity=r_tv,
            g_transmissivity=g_tv,
            b_transmissivity=b_tv,
            refraction_index=merged.get("refraction_index"),
            modifier=parent,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    if normalized_type in {"opaque", "metal", "mirror", "trans"}:
        rgb_r, r_r, g_r, b_r = _unpack_rgb_channels(
            merged,
            simple_key="rgb_reflectance",
            channel_prefix="reflectance",
        )
        if normalized_type == "opaque":
            return create_radiance_opaque_modifier(
                identifier=identifier,
                rgb_reflectance=rgb_r,
                r_reflectance=r_r,
                g_reflectance=g_r,
                b_reflectance=b_r,
                specularity=float(merged["specularity"]) if merged.get("specularity") is not None else 0.0,
                roughness=float(merged["roughness"]) if merged.get("roughness") is not None else 0.0,
                modifier=parent,
                garden_root=garden_root,
                return_object_dict=return_object_dict,
            )
        if normalized_type == "metal":
            return create_radiance_metal_modifier(
                identifier=identifier,
                rgb_reflectance=rgb_r,
                r_reflectance=r_r,
                g_reflectance=g_r,
                b_reflectance=b_r,
                specularity=float(merged["specularity"]) if merged.get("specularity") is not None else 0.9,
                roughness=float(merged["roughness"]) if merged.get("roughness") is not None else 0.0,
                modifier=parent,
                garden_root=garden_root,
                return_object_dict=return_object_dict,
            )
        if normalized_type == "mirror":
            return create_radiance_mirror_modifier(
                identifier=identifier,
                rgb_reflectance=rgb_r,
                r_reflectance=r_r,
                g_reflectance=g_r,
                b_reflectance=b_r,
                alternate_material=merged.get("alternate_material"),
                modifier=parent,
                garden_root=garden_root,
                return_object_dict=return_object_dict,
            )
        return create_radiance_trans_modifier(
            identifier=identifier,
            rgb_reflectance=rgb_r,
            r_reflectance=r_r,
            g_reflectance=g_r,
            b_reflectance=b_r,
            specularity=float(merged["specularity"]) if merged.get("specularity") is not None else 0.0,
            roughness=float(merged["roughness"]) if merged.get("roughness") is not None else 0.0,
            transmitted_diff=(
                float(merged["transmitted_diff"])
                if merged.get("transmitted_diff") is not None
                else 0.0
            ),
            transmitted_spec=(
                float(merged["transmitted_spec"])
                if merged.get("transmitted_spec") is not None
                else 0.0
            ),
            modifier=parent,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    if normalized_type in {"bsdf", "absdf"}:
        bsdf_file_raw = merged.get("bsdf_file")
        if not isinstance(bsdf_file_raw, str) or not bsdf_file_raw.strip():
            raise ValueError(f"bsdf_file is required for modifier_type='{normalized_type}'.")
        resolved_xml = _resolve_bsdf_file(bsdf_file_raw, garden_root=garden_root)
        up_orientation = merged.get("up_orientation")
        func_file = str(merged.get("function_file") or ".")
        transform = merged.get("transform")
        angle_basis = merged.get("angle_basis")
        if normalized_type == "bsdf":
            mod_obj = BSDF(
                resolved_xml,
                identifier=identifier,
                up_orientation=up_orientation,
                thickness=float(merged.get("thickness") or 0.0),
                modifier=parent,
                function_file=func_file,
                transform=transform,
                angle_basis=angle_basis,
            )
        else:
            mod_obj = aBSDF(
                resolved_xml,
                identifier=identifier,
                up_orientation=up_orientation,
                modifier=parent,
                function_file=func_file,
                transform=transform,
                angle_basis=angle_basis,
            )
        return _result(
            mod_obj,
            modifier_kind=normalized_type,
            input_mode="bsdf_xml",
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    if normalized_type == "glow":
        rgb = _non_negative_rgb(merged, simple_key="rgb_emittance", prefix="emittance", default=1.0)
        mod_obj = Glow(
            identifier,
            *rgb,
            max_radius=float(merged.get("max_radius") or 0.0),
            modifier=parent,
        )
        return _result(
            mod_obj,
            modifier_kind="glow",
            input_mode="rgb_emittance",
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    if normalized_type == "light":
        rgb = _non_negative_rgb(merged, simple_key="rgb_emittance", prefix="emittance", default=1.0)
        mod_obj = Light(identifier, *rgb, modifier=parent)
        return _result(
            mod_obj,
            modifier_kind="light",
            input_mode="rgb_emittance",
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    if normalized_type == "spotlight":
        if merged.get("values") is not None:
            vals = merged["values"]
        else:
            rgb = _non_negative_rgb(merged, simple_key="rgb_emittance", prefix="emittance", default=1.0)
            angle = float(merged["angle"] if merged.get("angle") is not None else 60.0)
            direction = merged.get("direction", [0, 0, -1])
            if not isinstance(direction, (list, tuple)) or len(direction) != 3:
                raise ValueError("direction must be [x, y, z] for spotlight.")
            vals = [[], [], [rgb[0], rgb[1], rgb[2], angle, float(direction[0]), float(direction[1]), float(direction[2])]]
        mod_obj = Spotlight(identifier, modifier=parent, values=vals, is_opaque=False)
        return _result(
            mod_obj,
            modifier_kind="spotlight",
            input_mode="spotlight",
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    if normalized_type == "illum":
        if merged.get("values") is not None:
            vals = merged["values"]
        else:
            rgb = _non_negative_rgb(merged, simple_key="rgb_emittance", prefix="emittance", default=1.0)
            alt = merged.get("alternate_material") or "void"
            if isinstance(alt, dict):
                alt = str(alt.get("identifier") or "void")
            vals = [[str(alt)], [], [rgb[0], rgb[1], rgb[2]]]
        mod_obj = Illum(identifier, modifier=parent, values=vals, is_opaque=False)
        return _result(
            mod_obj,
            modifier_kind="illum",
            input_mode="illum",
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    if normalized_type == "dielectric":
        if merged.get("values") is not None:
            vals = merged["values"]
        else:
            rgb = _non_negative_rgb(
                merged,
                simple_key="rgb_transmission",
                prefix="transmission",
                default=0.9,
            )
            n_val = float(merged["refraction_index"] if merged.get("refraction_index") is not None else 1.52)
            hc = float(merged["hartmann_constant"] if merged.get("hartmann_constant") is not None else 0.0)
            vals = [[], [], [rgb[0], rgb[1], rgb[2], n_val, hc]]
        mod_obj = Dielectric(identifier, modifier=parent, values=vals, is_opaque=False)
        return _result(
            mod_obj,
            modifier_kind="dielectric",
            input_mode="dielectric",
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    if normalized_type == "brtdfunc":
        vals = merged.get("values")
        if vals is None:
            vals = [
                ["0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "0", "0", "0", "."],
                [],
                [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.0, 0.0, 0.0],
            ]
        mod_obj = BRTDfunc(
            identifier,
            modifier=parent,
            values=vals,
            is_opaque=bool(merged.get("is_opaque", False)),
        )
        return _result(
            mod_obj,
            modifier_kind="brtdfunc",
            input_mode="values",
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    if normalized_type in {"plastic2", "metal2", "trans2"}:
        mod_obj = _create_anisotropic_modifier(
            normalized_type,
            identifier=identifier,
            merged=merged,
            parent=parent,
        )
        return _result(
            mod_obj,
            modifier_kind=normalized_type,
            input_mode="anisotropic",
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    rad_text = merged.get("rad_text")
    if not isinstance(rad_text, str) or not rad_text.strip():
        raise ValueError("rad_text is required for modifier_type='raw_rad'.")
    mod_obj = _create_raw_rad_modifier(
        identifier=identifier,
        rad_text=rad_text,
        parent=parent,
    )
    return _result(
        mod_obj,
        modifier_kind="raw_rad",
        input_mode="raw_rad",
        garden_root=garden_root,
        return_object_dict=return_object_dict,
    )


def _modifier_set_from_input(
    data: dict[str, Any] | str | None,
    *,
    garden_root: str | None = None,
) -> ModifierSet | None:
    if data is None:
        return None
    if isinstance(data, dict) and data.get("target_type") == "garden_properties_library_object":
        if not garden_root:
            raise ValueError("base_modifier_set library target requires garden_root.")
        if data.get("domain") != "honeybee_radiance" or data.get("object_family") != "modifier_set":
            raise ValueError("base_modifier_set target must reference honeybee_radiance:modifier_set.")
        data = get_garden_properties_library_object(
            garden_root=garden_root,
            target=data,
        )["object_dict"]
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        data = data["object_dict"]
    if isinstance(data, str):
        return modifier_set_by_identifier(data)
    if isinstance(data, dict):
        return ModifierSet.from_dict(data)
    raise ValueError("base_modifier_set must be a ModifierSet identifier, dict, or Garden library target.")


def _opaque_modifier_subset_from_input(
    data: dict[str, Any] | str | None,
    subset_cls: type[WallModifierSet] | type[FloorModifierSet] | type[RoofCeilingModifierSet] | type[ShadeModifierSet],
    *,
    field_name: str,
    garden_root: str | None,
    base_subset: Any = None,
) -> Any:
    if data is None:
        return base_subset.duplicate() if base_subset is not None else None
    if not isinstance(data, dict):
        raise ValueError(f"{field_name} must be a dictionary with exterior_modifier / interior_modifier.")
    ext = data.get("exterior_modifier")
    int_m = data.get("interior_modifier")
    return subset_cls(
        exterior_modifier=_resolve_modifier_input(ext, garden_root=garden_root, field_name=f"{field_name}.exterior_modifier")
        if ext is not None
        else (base_subset.exterior_modifier if base_subset else None),
        interior_modifier=_resolve_modifier_input(int_m, garden_root=garden_root, field_name=f"{field_name}.interior_modifier")
        if int_m is not None
        else (base_subset.interior_modifier if base_subset else None),
    )


def _aperture_modifier_subset_from_input(
    data: dict[str, Any] | None,
    *,
    garden_root: str | None,
    base_subset: ApertureModifierSet | None = None,
) -> ApertureModifierSet | None:
    if data is None:
        return base_subset.duplicate() if base_subset is not None else None
    if not isinstance(data, dict):
        raise ValueError("aperture_set must be a dictionary.")
    return ApertureModifierSet(
        window_modifier=_resolve_modifier_input(data["window_modifier"], garden_root=garden_root, field_name="aperture_set.window_modifier")
        if data.get("window_modifier") is not None
        else (base_subset.window_modifier if base_subset else None),
        interior_modifier=_resolve_modifier_input(data["interior_modifier"], garden_root=garden_root, field_name="aperture_set.interior_modifier")
        if data.get("interior_modifier") is not None
        else (base_subset.interior_modifier if base_subset else None),
        skylight_modifier=_resolve_modifier_input(data["skylight_modifier"], garden_root=garden_root, field_name="aperture_set.skylight_modifier")
        if data.get("skylight_modifier") is not None
        else (base_subset.skylight_modifier if base_subset else None),
        operable_modifier=_resolve_modifier_input(data["operable_modifier"], garden_root=garden_root, field_name="aperture_set.operable_modifier")
        if data.get("operable_modifier") is not None
        else (base_subset.operable_modifier if base_subset else None),
    )


def _door_modifier_subset_from_input(
    data: dict[str, Any] | None,
    *,
    garden_root: str | None,
    base_subset: DoorModifierSet | None = None,
) -> DoorModifierSet | None:
    if data is None:
        return base_subset.duplicate() if base_subset is not None else None
    if not isinstance(data, dict):
        raise ValueError("door_set must be a dictionary.")
    return DoorModifierSet(
        exterior_modifier=_resolve_modifier_input(data["exterior_modifier"], garden_root=garden_root, field_name="door_set.exterior_modifier")
        if data.get("exterior_modifier") is not None
        else (base_subset.exterior_modifier if base_subset else None),
        interior_modifier=_resolve_modifier_input(data["interior_modifier"], garden_root=garden_root, field_name="door_set.interior_modifier")
        if data.get("interior_modifier") is not None
        else (base_subset.interior_modifier if base_subset else None),
        exterior_glass_modifier=_resolve_modifier_input(data["exterior_glass_modifier"], garden_root=garden_root, field_name="door_set.exterior_glass_modifier")
        if data.get("exterior_glass_modifier") is not None
        else (base_subset.exterior_glass_modifier if base_subset else None),
        interior_glass_modifier=_resolve_modifier_input(data["interior_glass_modifier"], garden_root=garden_root, field_name="door_set.interior_glass_modifier")
        if data.get("interior_glass_modifier") is not None
        else (base_subset.interior_glass_modifier if base_subset else None),
        overhead_modifier=_resolve_modifier_input(data["overhead_modifier"], garden_root=garden_root, field_name="door_set.overhead_modifier")
        if data.get("overhead_modifier") is not None
        else (base_subset.overhead_modifier if base_subset else None),
    )


def _modifier_set_summary(
    modifier_set: ModifierSet,
    *,
    return_detail: str = "summary",
) -> dict[str, Any]:
    normalized = str(return_detail or "summary").strip().lower()
    if normalized not in {"summary", "full"}:
        raise ValueError("return_detail must be 'summary' or 'full'.")

    def _id_of(obj: Any) -> str | None:
        return obj.identifier if obj is not None else None

    summary: dict[str, Any] = {
        "type": "ModifierSet",
        "identifier": modifier_set.identifier,
        "air_boundary_modifier": _id_of(modifier_set.air_boundary_modifier),
        "wall_set": {
            "exterior_modifier": _id_of(modifier_set.wall_set.exterior_modifier),
            "interior_modifier": _id_of(modifier_set.wall_set.interior_modifier),
        },
        "floor_set": {
            "exterior_modifier": _id_of(modifier_set.floor_set.exterior_modifier),
            "interior_modifier": _id_of(modifier_set.floor_set.interior_modifier),
        },
        "roof_ceiling_set": {
            "exterior_modifier": _id_of(modifier_set.roof_ceiling_set.exterior_modifier),
            "interior_modifier": _id_of(modifier_set.roof_ceiling_set.interior_modifier),
        },
        "aperture_set": {
            "window_modifier": _id_of(modifier_set.aperture_set.window_modifier),
            "interior_modifier": _id_of(modifier_set.aperture_set.interior_modifier),
            "skylight_modifier": _id_of(modifier_set.aperture_set.skylight_modifier),
            "operable_modifier": _id_of(modifier_set.aperture_set.operable_modifier),
        },
        "door_set": {
            "exterior_modifier": _id_of(modifier_set.door_set.exterior_modifier),
            "interior_modifier": _id_of(modifier_set.door_set.interior_modifier),
            "exterior_glass_modifier": _id_of(modifier_set.door_set.exterior_glass_modifier),
            "interior_glass_modifier": _id_of(modifier_set.door_set.interior_glass_modifier),
            "overhead_modifier": _id_of(modifier_set.door_set.overhead_modifier),
        },
        "shade_set": {
            "exterior_modifier": _id_of(modifier_set.shade_set.exterior_modifier),
            "interior_modifier": _id_of(modifier_set.shade_set.interior_modifier),
        },
        "modifier_count": len(modifier_set.modifiers),
    }
    if normalized == "full":
        summary["modifiers"] = [mod.identifier for mod in modifier_set.modifiers]
    return summary


def create_radiance_modifier_set(
    *,
    identifier: str,
    base_modifier_set: dict[str, Any] | str | None = None,
    wall_set: dict[str, Any] | None = None,
    floor_set: dict[str, Any] | None = None,
    roof_ceiling_set: dict[str, Any] | None = None,
    aperture_set: dict[str, Any] | None = None,
    door_set: dict[str, Any] | None = None,
    shade_set: dict[str, Any] | None = None,
    air_boundary_modifier: dict[str, Any] | str | None = None,
    return_detail: str = "summary",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Radiance ModifierSet object (mirroring EP_Create_Construction_Set)."""
    base = _modifier_set_from_input(base_modifier_set, garden_root=garden_root)
    modifier_set = ModifierSet(
        identifier,
        wall_set=_opaque_modifier_subset_from_input(
            wall_set,
            WallModifierSet,
            field_name="wall_set",
            garden_root=garden_root,
            base_subset=base.wall_set if base else None,
        ),
        floor_set=_opaque_modifier_subset_from_input(
            floor_set,
            FloorModifierSet,
            field_name="floor_set",
            garden_root=garden_root,
            base_subset=base.floor_set if base else None,
        ),
        roof_ceiling_set=_opaque_modifier_subset_from_input(
            roof_ceiling_set,
            RoofCeilingModifierSet,
            field_name="roof_ceiling_set",
            garden_root=garden_root,
            base_subset=base.roof_ceiling_set if base else None,
        ),
        aperture_set=_aperture_modifier_subset_from_input(
            aperture_set,
            garden_root=garden_root,
            base_subset=base.aperture_set if base else None,
        ),
        door_set=_door_modifier_subset_from_input(
            door_set,
            garden_root=garden_root,
            base_subset=base.door_set if base else None,
        ),
        shade_set=_opaque_modifier_subset_from_input(
            shade_set,
            ShadeModifierSet,
            field_name="shade_set",
            garden_root=garden_root,
            base_subset=base.shade_set if base else None,
        ),
        air_boundary_modifier=_resolve_modifier_input(
            air_boundary_modifier,
            garden_root=garden_root,
            field_name="air_boundary_modifier",
        )
        if air_boundary_modifier is not None
        else (base.air_boundary_modifier.duplicate() if base and base.air_boundary_modifier else None),
    )
    object_dict = modifier_set.to_dict()
    result: dict[str, Any] = {
        "object_dict": object_dict,
        "summary_view": _modifier_set_summary(modifier_set, return_detail=return_detail),
        "report": make_report(
            status="ok",
            message=f"Created ModifierSet: {identifier}",
        ),
    }
    if not garden_root:
        if not return_object_dict:
            result.pop("object_dict", None)
        return result
    saved = save_garden_properties_library_object(
        garden_root=garden_root,
        domain="honeybee_radiance",
        object_family="modifier_set",
        object_dict=object_dict,
    )
    result["target"] = saved["target"]
    result["persistence_receipt"] = saved["persistence_receipt"]
    result["summary_view"]["target"] = saved["target"]
    result["summary_view"]["ready_for"] = "honeybee model or room radiance modifier_set"
    if not return_object_dict:
        result.pop("object_dict", None)
    return result
