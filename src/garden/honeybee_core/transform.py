"""Honeybee object transform services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from honeybee.aperture import Aperture
from honeybee.door import Door
from honeybee.face import Face
from honeybee.model import Model
from honeybee.room import Room
from honeybee.shade import Shade

from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report
from garden.honeybee_core.geometry import (
    plane_from_dict,
    point3d_from_dict,
    vector3d_from_dict,
)
from garden.honeybee_core.locate import find_object
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target,
    save_honeybee_model,
    with_honeybee_model_write_lock,
)
from garden.honeybee_core.postprocess import (
    apply_honeybee_postprocess,
    attach_postprocess_result,
)
from garden.honeybee_core.targets import (
    normalize_honeybee_target,
    object_summary,
)

Transformable = Model | Room | Face | Aperture | Door | Shade


@with_honeybee_model_write_lock
def move_object(
    *,
    garden_root: str,
    target: dict[str, Any],
    vector: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Move a Honeybee model object along a Vector3D."""
    return _transform_object(
        garden_root=garden_root,
        target=target,
        model_target=model_target,
        operation="move_object",
        operation_details={"vector": vector},
        apply=lambda obj: obj.move(vector3d_from_dict(vector)),
        postprocess_strategy=postprocess_strategy,
    )


@with_honeybee_model_write_lock
def rotate_object(
    *,
    garden_root: str,
    target: dict[str, Any],
    axis: dict[str, Any],
    angle_degrees: float,
    origin: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Rotate a Honeybee model object around an axis and origin."""
    return _transform_object(
        garden_root=garden_root,
        target=target,
        model_target=model_target,
        operation="rotate_object",
        operation_details={
            "axis": axis,
            "angle_degrees": angle_degrees,
            "origin": origin,
        },
        apply=lambda obj: obj.rotate(
            vector3d_from_dict(axis),
            angle_degrees,
            point3d_from_dict(origin),
        ),
        postprocess_strategy=postprocess_strategy,
    )


@with_honeybee_model_write_lock
def scale_object(
    *,
    garden_root: str,
    target: dict[str, Any],
    factor: float,
    origin: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Scale a Honeybee model object from an optional origin point."""
    if factor <= 0:
        raise ValueError("factor must be greater than 0.")
    parsed_origin = point3d_from_dict(origin) if origin is not None else None
    return _transform_object(
        garden_root=garden_root,
        target=target,
        model_target=model_target,
        operation="scale_object",
        operation_details={"factor": factor, "origin": origin},
        apply=lambda obj: obj.scale(factor, parsed_origin),
        postprocess_strategy=postprocess_strategy,
    )


@with_honeybee_model_write_lock
def mirror_object(
    *,
    garden_root: str,
    target: dict[str, Any],
    plane: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Mirror a Honeybee model object by reflecting it across a Plane."""
    return _transform_object(
        garden_root=garden_root,
        target=target,
        model_target=model_target,
        operation="mirror_object",
        operation_details={"plane": plane},
        apply=lambda obj: obj.reflect(plane_from_dict(plane)),
        postprocess_strategy=postprocess_strategy,
    )


def _transform_object(
    *,
    garden_root: str,
    target: dict[str, Any],
    model_target: dict[str, Any] | None,
    operation: str,
    operation_details: dict[str, Any],
    apply,
    postprocess_strategy: str | None,
) -> dict[str, Any]:
    target = normalize_honeybee_target(target)
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(
        garden_root_path,
        _model_target_from_target(target) or model_target,
    )
    model = load_honeybee_model(garden_root_path, resolved_model_target)
    obj = _resolve_transform_target(model, target, resolved_model_target)
    apply(obj)
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(resolved_model_target["model_identifier"]),
        operation=operation,
        target=target,
        strategy=postprocess_strategy,
    )

    updated_model_target, persisted_path = save_honeybee_model(
        garden_root_path,
        manifest,
        model,
        name=str(resolved_model_target["model_identifier"]),
        set_base=manifest.base_model == resolved_model_target,
    )
    summary_view = _summary_for_target(
        target=target,
        obj=obj,
        updated_model_target=updated_model_target,
        operation=operation,
        operation_details=operation_details,
    )
    warnings = _transform_warnings(target, obj)
    return attach_postprocess_result({
        "target": target,
        "summary_view": summary_view,
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            warnings=warnings,
            change_summary={
                "operation": operation,
                "target": target,
                **operation_details,
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Transformed Honeybee {_target_label(target)}.",
            warnings=warnings,
            details={"operation": operation},
        ),
    }, postprocess)


def _model_target_from_target(target: dict[str, Any]) -> dict[str, Any] | None:
    if target.get("target_type") == "model" and target.get("domain") == "honeybee":
        return target
    return None


def _resolve_transform_target(
    model: Model,
    target: dict[str, Any],
    model_target: dict[str, Any],
) -> Transformable:
    if target.get("target_type") == "model" and target.get("domain") == "honeybee":
        if target.get("model_identifier") != model_target.get("model_identifier"):
            raise ValueError("target and model_target identify different Honeybee models.")
        return model
    if target.get("target_type") != "honeybee_object":
        raise ValueError("target must be a Honeybee model target or Honeybee object typed target.")
    obj = find_object(model, target)
    if not isinstance(obj, (Room, Face, Aperture, Door, Shade)):
        raise ValueError("target does not resolve to a transformable Honeybee object.")
    return obj


def _summary_for_target(
    *,
    target: dict[str, Any],
    obj: Transformable,
    updated_model_target: dict[str, Any],
    operation: str,
    operation_details: dict[str, Any],
) -> dict[str, Any]:
    if isinstance(obj, Model):
        return {
            "target": updated_model_target,
            "model_identifier": updated_model_target["model_identifier"],
            "type": "Model",
            "operation": operation,
            **operation_details,
            "object_counts": {
                "rooms": len(obj.rooms),
                "faces": len(obj.faces),
                "apertures": len(obj.apertures),
                "doors": len(obj.doors),
                "shades": len(obj.shades),
            },
        }
    summary = object_summary(target, obj.to_dict())
    summary["operation"] = operation
    summary.update(operation_details)
    return summary


def _transform_warnings(target: dict[str, Any], obj: Transformable) -> list[str]:
    if isinstance(obj, Model):
        return []
    warnings = [
        "Partial object transforms can break adjacency, host boundary containment, "
        "coplanar sub-face relationships, or dynamic state geometry. Run "
        "relate_honeybee_model and validate_honeybee_model when those relationships matter."
    ]
    if target.get("parent"):
        warnings.append(
            "The target has parent context; verify that transformed child geometry still "
            "belongs to its host."
        )
    return warnings


def _target_label(target: dict[str, Any]) -> str:
    if target.get("target_type") == "model":
        return f"model: {target.get('model_identifier')}"
    return f"{target.get('object_type')}: {target.get('object_identifier')}"
