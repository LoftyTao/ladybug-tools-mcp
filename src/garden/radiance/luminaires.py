"""Honeybee Radiance Luminaire / IES creation services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from honeybee_radiance.luminaire import (
    CustomLamp,
    Luminaire,
    LuminaireInstance,
    LuminaireZone,
)
from ladybug_geometry.geometry3d.pointvector import Point3D

from garden.libraries.properties import save_garden_properties_library_object
from ladybug_tools_mcp.contracts.report import make_report


def _positive(value: float, field_name: str) -> float:
    value = float(value)
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than 0.")
    return value


def _unit_interval(value: float, field_name: str) -> float:
    value = float(value)
    if value < 0 or value > 1:
        raise ValueError(f"{field_name} must be between 0 and 1.")
    return value


def _point3d_from_input(data: Any, *, field_name: str) -> Point3D:
    if isinstance(data, Point3D):
        return data
    if isinstance(data, dict):
        if data.get("type") not in {None, "Point3D"}:
            raise ValueError(f"{field_name} must be a Point3D dict or [x, y, z].")
        try:
            return Point3D(float(data["x"]), float(data["y"]), float(data["z"]))
        except KeyError as exc:
            raise ValueError(f"{field_name} Point3D dict must include x, y, and z.") from exc
    if isinstance(data, (list, tuple)) and len(data) == 3:
        return Point3D(float(data[0]), float(data[1]), float(data[2]))
    raise ValueError(f"{field_name} must be a Point3D dict or [x, y, z].")


def _custom_lamp_from_input(data: dict[str, Any] | None) -> CustomLamp | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("custom_lamp must be a CustomLamp dictionary or simple lamp settings.")

    mode = str(data.get("mode", data.get("lamp_mode", ""))).strip().lower()
    if mode == "" and {"rgb", "white_xy"} & set(data):
        return CustomLamp.from_dict(data)

    name = str(data.get("name") or "custom_lamp")
    depreciation_factor = _unit_interval(
        data.get("depreciation_factor", 1.0),
        "custom_lamp.depreciation_factor",
    )
    if mode in {"", "default_white", "default", "white"}:
        return CustomLamp.from_default_white(name, depreciation_factor=depreciation_factor)
    if mode in {"color_temperature", "cct"}:
        return CustomLamp.from_color_temperature(
            name,
            float(data["color_temperature"]),
            depreciation_factor=depreciation_factor,
        )
    if mode == "rgb":
        rgb = list(data["rgb"])
        if all(0 <= float(value) <= 1 for value in rgb[:3]):
            rgb = [float(value) * 255 for value in rgb]
        return CustomLamp.from_rgb_colors(name, rgb, depreciation_factor=depreciation_factor)
    if mode in {"xy", "white_xy"}:
        return CustomLamp.from_xy_coordinates(
            name,
            _unit_interval(data["x"], "custom_lamp.x"),
            _unit_interval(data["y"], "custom_lamp.y"),
            depreciation_factor=depreciation_factor,
            color_space=int(data.get("color_space", 0)),
        )
    if mode in {"lamp_name", "legacy"}:
        return CustomLamp.from_lamp_name(str(data["lamp_name"]))
    raise ValueError(
        "custom_lamp.mode must be default_white, color_temperature, rgb, xy, or lamp_name."
    )


def _instance_from_input(data: dict[str, Any], *, index: int) -> LuminaireInstance:
    if not isinstance(data, dict):
        raise ValueError("Each luminaire instance must be a dictionary.")
    point = _point3d_from_input(data.get("point"), field_name=f"instances[{index}].point")
    spin = float(data.get("spin", 0))
    tilt = float(data.get("tilt", 0))
    rotation = float(data.get("rotation", 0))
    if data.get("aiming_point") is not None:
        aiming_point = _point3d_from_input(
            data["aiming_point"],
            field_name=f"instances[{index}].aiming_point",
        )
        return LuminaireInstance.from_aiming_point(
            point,
            aiming_point,
            spin=spin,
            tilt=tilt,
            rotation=rotation,
        )
    return LuminaireInstance(point, spin=spin, tilt=tilt, rotation=rotation)


def _luminaire_zone_from_input(instances: list[dict[str, Any]] | None) -> LuminaireZone | None:
    if instances is None:
        return None
    if not isinstance(instances, list) or len(instances) == 0:
        raise ValueError("instances must be a non-empty list when provided.")
    return LuminaireZone(
        [_instance_from_input(instance, index=index) for index, instance in enumerate(instances)]
    )


def _summary(luminaire: Luminaire, *, input_kind: str) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "type": "Luminaire",
        "identifier": luminaire.identifier,
        "input_kind": input_kind,
        "light_loss_factor": luminaire.light_loss_factor,
        "candela_multiplier": luminaire.candela_multiplier,
        "instance_count": 0
        if luminaire.luminaire_zone is None
        else len(luminaire.luminaire_zone.instances),
        "has_custom_lamp": luminaire.custom_lamp is not None,
    }
    try:
        luminaire.parse_photometric_data()
    except Exception as exc:  # pragma: no cover - SDK diagnostics vary by IES file
        summary["photometric_parse_error"] = str(exc)
        return summary
    summary.update(
        {
            "vertical_angle_count": len(luminaire.vertical_angles),
            "horizontal_angle_count": len(luminaire.horizontal_angles),
            "max_candela": round(float(luminaire.max_candela), 6),
            "unit_type": luminaire.unit_type,
            "dimensions": {
                "width": luminaire.width,
                "length": luminaire.length,
                "height": luminaire.height,
            },
        }
    )
    return summary


def create_radiance_luminaire(
    *,
    ies_content: str | None = None,
    ies_path: str | None = None,
    identifier: str | None = None,
    instances: list[dict[str, Any]] | None = None,
    custom_lamp: dict[str, Any] | None = None,
    light_loss_factor: float = 1.0,
    candela_multiplier: float = 1.0,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Radiance Luminaire from IES content or an IES file."""
    if bool(ies_content) == bool(ies_path):
        raise ValueError("Provide exactly one of ies_content or ies_path.")
    if ies_path is not None:
        path = Path(ies_path).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"ies_path was not found: {path}")
        ies_input = str(path)
        input_kind = "ies_path"
    else:
        ies_input = str(ies_content)
        input_kind = "ies_content"

    luminaire = Luminaire(
        ies_input,
        identifier=identifier,
        luminaire_zone=_luminaire_zone_from_input(instances),
        custom_lamp=_custom_lamp_from_input(custom_lamp),
        light_loss_factor=_positive(light_loss_factor, "light_loss_factor"),
        candela_multiplier=_positive(candela_multiplier, "candela_multiplier"),
    )
    result = {
        "object_dict": luminaire.to_dict(),
        "summary_view": _summary(luminaire, input_kind=input_kind),
        "report": make_report(
            status="ok",
            message=f"Created Honeybee Radiance Luminaire: {luminaire.identifier}",
        ),
    }
    if not garden_root:
        return result

    saved = save_garden_properties_library_object(
        garden_root=garden_root,
        domain="honeybee_radiance",
        object_family="luminaire",
        object_dict=result["object_dict"],
    )
    result["target"] = saved["target"]
    result["luminaire_target"] = saved["target"]
    result["persistence_receipt"] = saved["persistence_receipt"]
    result["summary_view"]["target"] = saved["target"]
    result["summary_view"]["ready_for"] = "radiance luminaire / IES workflows"
    if not return_object_dict:
        result.pop("object_dict", None)
    return result
