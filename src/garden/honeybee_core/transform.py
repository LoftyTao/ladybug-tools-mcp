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

from ladybug_tools_mcp.contracts import make_persistence_receipt, make_report
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


def _normalize_xyz_dict(value: Any, *, field_name: str) -> dict[str, Any]:
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return {
            "x": float(value[0]),
            "y": float(value[1]),
            "z": float(value[2]),
        }
    if isinstance(value, dict):
        return value
    raise ValueError(f"{field_name} must be a dict or [x, y, z] list.")


def move_object(
    *,
    garden_root: str,
    target: dict[str, Any],
    vector: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Move a Honeybee model object along a Vector3D."""
    vec = vector3d_from_dict(_normalize_xyz_dict(vector, field_name="vector"))
    return _transform_object(
        garden_root=garden_root,
        target=target,
        model_target=model_target,
        operation="move_object",
        operation_details={"vector": vector},
        apply=lambda obj: obj.move(vec),
        postprocess_strategy=postprocess_strategy,
    )


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
    axis_vec = vector3d_from_dict(_normalize_xyz_dict(axis, field_name="axis"))
    origin_pt = point3d_from_dict(_normalize_xyz_dict(origin, field_name="origin"))
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
        apply=lambda obj: obj.rotate(axis_vec, float(angle_degrees), origin_pt),
        postprocess_strategy=postprocess_strategy,
    )


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
    parsed_origin = (
        point3d_from_dict(_normalize_xyz_dict(origin, field_name="origin"))
        if origin is not None
        else None
    )
    return _transform_object(
        garden_root=garden_root,
        target=target,
        model_target=model_target,
        operation="scale_object",
        operation_details={"factor": factor, "origin": origin},
        apply=lambda obj: obj.scale(float(factor), parsed_origin),
        postprocess_strategy=postprocess_strategy,
    )


def mirror_object(
    *,
    garden_root: str,
    target: dict[str, Any],
    plane: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Mirror a Honeybee model object by reflecting it across a Plane."""
    parsed_plane = plane_from_dict(plane)
    return _transform_object(
        garden_root=garden_root,
        target=target,
        model_target=model_target,
        operation="mirror_object",
        operation_details={"plane": plane},
        apply=lambda obj: obj.reflect(parsed_plane),
        postprocess_strategy=postprocess_strategy,
    )


def transform_objects(
    *,
    garden_root: str,
    operation: str,
    target: dict[str, Any] | None = None,
    targets: list[dict[str, Any]] | None = None,
    model_target: dict[str, Any] | None = None,
    vector: dict[str, Any] | list[float] | None = None,
    axis: dict[str, Any] | list[float] | None = None,
    angle_degrees: float | None = None,
    origin: dict[str, Any] | list[float] | None = None,
    factor: float | None = None,
    plane: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Transform one or more Honeybee model or object targets in a single save."""
    if (target is None) == (targets is None):
        raise ValueError("Provide exactly one of target or targets.")

    op_name = str(operation or "").strip().lower()
    if op_name not in {"move", "rotate", "scale", "mirror"}:
        raise ValueError("operation must be one of move, rotate, scale, or mirror.")

    if op_name == "move":
        if vector is None:
            raise ValueError("vector is required when operation is 'move'.")
        vec = vector3d_from_dict(_normalize_xyz_dict(vector, field_name="vector"))
        op_key = "move_object"
        operation_details: dict[str, Any] = {"vector": vector}
        apply_fn = lambda obj: obj.move(vec)
    elif op_name == "rotate":
        if axis is None or angle_degrees is None or origin is None:
            raise ValueError(
                "axis, angle_degrees, and origin are required when operation is 'rotate'."
            )
        axis_vec = vector3d_from_dict(_normalize_xyz_dict(axis, field_name="axis"))
        origin_pt = point3d_from_dict(_normalize_xyz_dict(origin, field_name="origin"))
        angle_val = float(angle_degrees)
        op_key = "rotate_object"
        operation_details = {
            "axis": axis,
            "angle_degrees": angle_val,
            "origin": origin,
        }
        apply_fn = lambda obj: obj.rotate(axis_vec, angle_val, origin_pt)
    elif op_name == "scale":
        if factor is None:
            raise ValueError("factor is required when operation is 'scale'.")
        factor_val = float(factor)
        if factor_val <= 0:
            raise ValueError("factor must be greater than 0.")
        parsed_origin = (
            point3d_from_dict(_normalize_xyz_dict(origin, field_name="origin"))
            if origin is not None
            else None
        )
        op_key = "scale_object"
        operation_details = {"factor": factor_val, "origin": origin}
        apply_fn = lambda obj: obj.scale(factor_val, parsed_origin)
    else:
        if plane is None:
            raise ValueError("plane is required when operation is 'mirror'.")
        parsed_plane = plane_from_dict(plane)
        op_key = "mirror_object"
        operation_details = {"plane": plane}
        apply_fn = lambda obj: obj.reflect(parsed_plane)

    if target is not None:
        return _transform_object(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            operation=op_key,
            operation_details=operation_details,
            apply=apply_fn,
            postprocess_strategy=postprocess_strategy,
        )

    if not isinstance(targets, list) or not targets:
        raise ValueError("targets must be a non-empty list of Honeybee typed targets.")

    normalized_targets: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str]] = set()
    explicit_model_target = model_target
    for index, raw_target in enumerate(targets):
        try:
            norm = normalize_honeybee_target(raw_target)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"targets[{index}] must be a Honeybee model or object typed target."
            ) from exc
        t_type = str(norm.get("target_type"))
        if t_type == "honeybee_model":
            if explicit_model_target is None:
                explicit_model_target = norm
            elif norm.get("model_identifier") != explicit_model_target.get("model_identifier"):
                raise ValueError("targets identify different Honeybee models.")
            key = ("model", str(norm.get("model_identifier")), "")
        else:
            key = (
                "object",
                str(norm.get("object_type")),
                str(norm.get("object_identifier")),
            )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        normalized_targets.append(norm)

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(
        garden_root_path,
        explicit_model_target,
    )
    expected_model_id = str(resolved_model_target["model_identifier"])
    for index, norm in enumerate(normalized_targets):
        if norm.get("garden_id") and norm.get("garden_id") != manifest.garden_id:
            raise ValueError(f"targets[{index}] belongs to a different Garden.")
        if norm.get("model_identifier") != expected_model_id:
            raise ValueError(
                f"targets[{index}] belongs to Honeybee model "
                f"{norm.get('model_identifier')!r}, expected {expected_model_id!r}."
            )

    model = load_honeybee_model(garden_root_path, resolved_model_target)
    working_model = model.duplicate()
    resolved_pairs: list[tuple[dict[str, Any], Transformable]] = [
        (norm, _resolve_transform_target(working_model, norm, resolved_model_target))
        for norm in normalized_targets
    ]
    for _, obj in resolved_pairs:
        apply_fn(obj)

    object_types = [
        "model" if isinstance(obj, Model) else str(norm.get("object_type"))
        for norm, obj in resolved_pairs
    ]
    unique_types = list(dict.fromkeys(object_types))
    working_model, postprocess = apply_honeybee_postprocess(
        model=working_model,
        garden_id=manifest.garden_id,
        model_identifier=expected_model_id,
        operation=op_key,
        target=normalized_targets[0],
        object_type=unique_types[0] if len(unique_types) == 1 else None,
        object_types=unique_types,
        strategy=postprocess_strategy,
    )

    updated_model_target, persisted_path = save_honeybee_model(
        garden_root_path,
        manifest,
        working_model,
        name=expected_model_id,
        set_base=manifest.base_honeybee_model == resolved_model_target,
    )
    summaries = [
        _summary_for_target(
            target=norm,
            obj=obj,
            updated_model_target=updated_model_target,
            operation=op_key,
            operation_details=operation_details,
        )
        for norm, obj in resolved_pairs
    ]
    warnings: list[str] = []
    for norm, obj in resolved_pairs:
        for warning in _transform_warnings(norm, obj):
            if warning not in warnings:
                warnings.append(warning)

    return attach_postprocess_result(
        {
            "target": normalized_targets[0],
            "targets": normalized_targets,
            "model_target": updated_model_target,
            "summary_view": {
                "operation": op_key,
                "transformed_count": len(resolved_pairs),
                "object_types": unique_types,
                "objects": summaries,
                "model_target": updated_model_target,
                **operation_details,
            },
            "persistence_receipt": make_persistence_receipt(
                status="persisted",
                garden_id=manifest.garden_id,
                model_target=updated_model_target,
                persisted_path=persisted_path,
                warnings=warnings,
                change_summary={
                    "operation": op_key,
                    "targets": normalized_targets,
                    "transformed_count": len(resolved_pairs),
                    **operation_details,
                },
            ),
            "report": make_report(
                status="ok",
                message=(
                    f"Transformed {len(resolved_pairs)} Honeybee target(s) "
                    f"with {op_name}."
                ),
                warnings=warnings,
                details={"operation": op_key},
            ),
        },
        postprocess,
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
        set_base=manifest.base_honeybee_model == resolved_model_target,
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
    if target.get("target_type") == "honeybee_model" and target.get("domain") == "honeybee":
        return target
    return None


def _resolve_transform_target(
    model: Model,
    target: dict[str, Any],
    model_target: dict[str, Any],
) -> Transformable:
    if target.get("target_type") == "honeybee_model" and target.get("domain") == "honeybee":
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
        "HB_Relate_Model and HB_Validate_Model when those relationships matter."
    ]
    if target.get("parent"):
        warnings.append(
            "The target has parent context; verify that transformed child geometry still "
            "belongs to its host."
        )
    return warnings


def _target_label(target: dict[str, Any]) -> str:
    if target.get("target_type") == "honeybee_model":
        return f"model: {target.get('model_identifier')}"
    return f"{target.get('object_type')}: {target.get('object_identifier')}"
