"""Fairyfly model authoring services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fairyfly.boundary import Boundary
from fairyfly.model import Model
from fairyfly.shape import Shape
from fairyfly_therm.condition.steadystate import SteadyState
from fairyfly_therm.material.dictutil import dict_to_material
from ladybug.color import Color

from garden.fairyfly.geometry2d import (
    face3d_from_vertices_2d,
    line_segments3d_from_segments_2d,
)
from garden.fairyfly.model_io import (
    load_fairyfly_model,
    resolve_model_target,
    save_fairyfly_model,
)
from garden.manifest import GardenManifest
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report


def _garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def _model_counts(model: Model) -> dict[str, int]:
    return {
        "shapes": len(getattr(model, "shapes", []) or []),
        "boundaries": len(getattr(model, "boundaries", []) or []),
    }


def _color_from_rgb(rgb_color: list[int] | None) -> Color | None:
    if rgb_color is None:
        return None
    if len(rgb_color) != 3:
        raise ValueError("rgb_color must be [r, g, b].")
    return Color(*(int(value) for value in rgb_color))


def _save_changed_model(
    garden_root: Path,
    manifest: GardenManifest,
    model_target: dict[str, Any],
    model: Model,
) -> tuple[dict[str, Any], str]:
    return save_fairyfly_model(
        garden_root,
        manifest,
        model,
        name=str(model_target["model_identifier"]),
        set_base=manifest.base_fairyfly_model == model_target,
    )


def _persistence_receipt(
    *,
    garden_id: str,
    model_target: dict[str, Any],
    persisted_path: str,
    operation: str,
    change_details: dict[str, Any],
) -> dict[str, Any]:
    return make_persistence_receipt(
        status="persisted",
        garden_id=garden_id,
        model_target=model_target,
        persisted_path=persisted_path,
        change_summary={
            "operation": operation,
            "target": model_target,
            **change_details,
        },
    )


def _model_update_response(
    *,
    model: Model,
    model_target: dict[str, Any],
    garden_id: str,
    persisted_path: str,
    operation: str,
    message: str,
    change_details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "object_dict": model_target,
        "target": model_target,
        "model_target": model_target,
        "fairyfly_model_target": model_target,
        "summary_view": {
            "model_target": model_target,
            "object_counts": _model_counts(model),
            **change_details,
        },
        "persistence_receipt": _persistence_receipt(
            garden_id=garden_id,
            model_target=model_target,
            persisted_path=persisted_path,
            operation=operation,
            change_details=change_details,
        ),
        "report": make_report(status="ok", message=message),
    }


def create_fairyfly_model(
    *,
    garden_root: str,
    identifier: str,
    units: str = "Millimeters",
    tolerance: float | None = None,
    angle_tolerance: float = 1.0,
    display_name: str | None = None,
    save_back: bool = True,
    set_base: bool = True,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create a Fairyfly Model and optionally persist it to a Garden."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    model = Model(
        units=units,
        tolerance=tolerance,
        angle_tolerance=angle_tolerance,
    )
    model.display_name = display_name or identifier
    receipt: dict[str, Any] | None = None
    if save_back:
        model_target, persisted_path = save_fairyfly_model(
            garden_root_path,
            manifest,
            model,
            name=identifier,
            set_base=set_base,
        )
        object_dict = model_target
        receipt = make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            model_target=model_target,
            persisted_path=persisted_path,
            change_summary={
                "operation": "create_fairyfly_model",
                "target": model_target,
                "base_fairyfly_model_changed": bool(set_base),
            },
        )
    else:
        object_dict = (
            model.to_dict()
            if include_body
            else {"domain": "fairyfly", "model_identifier": identifier}
        )

    return {
        "object_dict": object_dict,
        "target": object_dict,
        "model_target": object_dict,
        "fairyfly_model_target": object_dict,
        "summary_view": {
            "model_identifier": identifier,
            "sdk_identifier": model.identifier,
            "display_name": model.display_name,
            "domain": "fairyfly",
            "units": model.units,
            "saved": save_back,
            "base_fairyfly_model_changed": bool(save_back and set_base),
            "object_counts": _model_counts(model),
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=f"Created Fairyfly model: {identifier}",
        ),
    }


def add_fairyfly_shape_to_model(
    *,
    garden_root: str,
    vertices_2d: list[list[float]],
    material: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    name: str | None = None,
    holes_2d: list[list[list[float]]] | None = None,
    rgb_color: list[int] | None = None,
    tolerance: float | None = None,
) -> dict[str, Any]:
    """Add a 2D Fairyfly Shape to a Garden-backed model."""
    garden_root_path = _garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(
        garden_root_path,
        model_target,
    )
    model = load_fairyfly_model(garden_root_path, resolved_model_target)
    shape = Shape(
        face3d_from_vertices_2d(
            vertices_2d,
            holes_2d=holes_2d,
            tolerance=tolerance,
        )
    )
    if name:
        shape.display_name = name
    material_obj = dict_to_material(material)
    color = _color_from_rgb(rgb_color)
    if color is not None:
        material_obj.color = color
    shape.properties.therm.material = material_obj
    model.add_shape(shape)
    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    return _model_update_response(
        model=model,
        model_target=updated_model_target,
        garden_id=manifest.garden_id,
        persisted_path=persisted_path,
        operation="add_fairyfly_shape_to_model",
        message=f"Added Fairyfly shape: {shape.display_name}",
        change_details={
            "added_shape": {
                "display_name": shape.display_name,
                "area": shape.area,
                "material": shape.properties.therm.material.display_name,
            }
        },
    )


def add_fairyfly_boundary_to_model(
    *,
    garden_root: str,
    line_segments_2d: list[list[list[float]]],
    temperature: float,
    film_coefficient: float,
    model_target: dict[str, Any] | None = None,
    name: str | None = None,
    emissivity: float = 1.0,
    radiant_temperature: float | None = None,
    heat_flux: float = 0,
    relative_humidity: float = 0.5,
    u_factor_tag: str | None = None,
    rgb_color: list[int] | None = None,
) -> dict[str, Any]:
    """Add a 2D Fairyfly Boundary to a Garden-backed model."""
    garden_root_path = _garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(
        garden_root_path,
        model_target,
    )
    model = load_fairyfly_model(garden_root_path, resolved_model_target)
    boundary = Boundary(line_segments3d_from_segments_2d(line_segments_2d))
    if name:
        boundary.display_name = name
    condition = SteadyState(
        temperature=temperature,
        film_coefficient=film_coefficient,
        emissivity=emissivity,
        radiant_temperature=radiant_temperature,
        heat_flux=heat_flux,
        relative_humidity=relative_humidity,
    )
    condition.display_name = name or f"{temperature}C boundary"
    color = _color_from_rgb(rgb_color)
    if color is not None:
        condition.color = color
    else:
        condition.color = Color(50, 110, 200)
    boundary.properties.therm.condition = condition
    boundary.properties.therm.u_factor_tag = u_factor_tag
    model.add_boundary(boundary)
    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    return _model_update_response(
        model=model,
        model_target=updated_model_target,
        garden_id=manifest.garden_id,
        persisted_path=persisted_path,
        operation="add_fairyfly_boundary_to_model",
        message=f"Added Fairyfly boundary: {boundary.display_name}",
        change_details={
            "added_boundary": {
                "display_name": boundary.display_name,
                "length": boundary.length,
                "condition": condition.display_name,
                "u_factor_tag": u_factor_tag,
            }
        },
    )
