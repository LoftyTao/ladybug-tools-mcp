"""Dragonfly envelope parameter services backed by SDK parameter objects."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dragonfly.building import Building
from dragonfly.model import Model
from dragonfly.room2d import Room2D
from dragonfly.shadingparameter import ExtrudedBorder, Overhang
from dragonfly.story import Story
from dragonfly.windowparameter import RepeatingWindowRatio, SimpleWindowRatio

from garden.dragonfly_core.model_io import (
    load_dragonfly_model,
    resolve_model_target,
    save_dragonfly_model,
)
from garden.dragonfly_core.targets import (
    make_dragonfly_object_target,
    normalize_dragonfly_object_target,
)
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report


def _garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def _load_target_model(
    garden_root: str,
    model_target: dict[str, Any] | None,
) -> tuple[Path, Any, dict[str, Any], Model]:
    garden_root_path = _garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    return garden_root_path, manifest, resolved_model_target, model


def _save_changed_model(
    garden_root: Path,
    manifest: Any,
    model_target: dict[str, Any],
    model: Model,
) -> tuple[dict[str, Any], str]:
    return save_dragonfly_model(
        garden_root,
        manifest,
        model,
        name=str(model_target["model_identifier"]),
        set_base=manifest.base_dragonfly_model == model_target,
    )


def _receipt(
    *,
    garden_id: str,
    model_target: dict[str, Any],
    persisted_path: str,
    operation: str,
    target: dict[str, Any],
    change_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return make_persistence_receipt(
        status="persisted",
        garden_id=garden_id,
        model_target=model_target,
        persisted_path=persisted_path,
        change_summary={
            "operation": operation,
            "target": target,
            **(change_details or {}),
        },
    )


def _one_by_identifier(objects: list[Any], identifier: str, object_type: str) -> Any:
    if len(objects) == 1:
        return objects[0]
    if not objects:
        raise ValueError(f"Dragonfly {object_type} not found: {identifier}.")
    raise ValueError(f"Dragonfly {object_type} identifier is ambiguous: {identifier}.")


def _room_by_identifier(model: Model, identifier: str) -> Room2D:
    return _one_by_identifier(
        model.room_2ds_by_identifier([identifier]),
        identifier,
        "Room2D",
    )


def _story_by_identifier(model: Model, identifier: str) -> Story:
    return _one_by_identifier(
        model.stories_by_identifier([identifier]),
        identifier,
        "Story",
    )


def _building_by_identifier(model: Model, identifier: str) -> Building:
    return _one_by_identifier(
        model.buildings_by_identifier([identifier]),
        identifier,
        "Building",
    )


def _normalize_parameter_type(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def _window_parameter_from_dict(data: dict[str, Any]) -> Any:
    parameter_type = data.get("type") or data.get("parameter_type")
    normalized_type = _normalize_parameter_type(str(parameter_type or ""))
    if normalized_type == "simplewindowratio":
        normalized_type = "simple_window_ratio"
    if normalized_type == "repeatingwindowratio":
        normalized_type = "repeating_window_ratio"
    if normalized_type == "simple_window_ratio":
        return SimpleWindowRatio(
            float(data["window_ratio"]),
            rect_split=bool(data.get("rect_split", True)),
        )
    if normalized_type == "repeating_window_ratio":
        return RepeatingWindowRatio(
            float(data["window_ratio"]),
            float(data["window_height"]),
            float(data["sill_height"]),
            float(data["horizontal_separation"]),
            vertical_separation=float(data.get("vertical_separation", 0)),
        )
    raise ValueError(
        "Unsupported Dragonfly window parameter type. Supported values are "
        "simple_window_ratio and repeating_window_ratio."
    )


def _shading_parameter_from_dict(data: dict[str, Any]) -> Any:
    parameter_type = data.get("type") or data.get("parameter_type")
    normalized_type = _normalize_parameter_type(str(parameter_type or ""))
    if normalized_type == "extrudedborder":
        normalized_type = "extruded_border"
    if normalized_type == "overhang":
        return Overhang(float(data["depth"]), angle=float(data.get("angle", 0)))
    if normalized_type == "extruded_border":
        return ExtrudedBorder(float(data["depth"]))
    raise ValueError(
        "Unsupported Dragonfly shading parameter type. Supported values are "
        "overhang and extruded_border."
    )


def _parameter_artifact(
    *,
    garden_id: str,
    parameter_kind: str,
    parameter: Any,
) -> dict[str, Any]:
    parameter_dict = parameter.to_dict()
    return {
        "target_type": f"dragonfly_{parameter_kind}_parameter",
        "domain": "dragonfly",
        "garden_id": garden_id,
        "parameter_kind": parameter_kind,
        "parameter_type": parameter_dict["type"],
        **parameter_dict,
    }


def create_dragonfly_window_parameter(
    *,
    garden_root: str,
    parameter_type: str,
    window_ratio: float,
    rect_split: bool = True,
    window_height: float | None = None,
    sill_height: float | None = None,
    horizontal_separation: float | None = None,
    vertical_separation: float = 0,
) -> dict[str, Any]:
    """Create a compact Dragonfly WindowParameter artifact."""
    garden_root_path = _garden_root(garden_root)
    manifest, _model_target = resolve_model_target(garden_root_path, None)
    normalized_type = _normalize_parameter_type(parameter_type)
    if normalized_type == "simple_window_ratio":
        parameter = SimpleWindowRatio(window_ratio, rect_split=rect_split)
    elif normalized_type == "repeating_window_ratio":
        missing = [
            name
            for name, value in {
                "window_height": window_height,
                "sill_height": sill_height,
                "horizontal_separation": horizontal_separation,
            }.items()
            if value is None
        ]
        if missing:
            raise ValueError(
                "repeating_window_ratio requires: " + ", ".join(missing) + "."
            )
        parameter = RepeatingWindowRatio(
            window_ratio,
            float(window_height),
            float(sill_height),
            float(horizontal_separation),
            vertical_separation=vertical_separation,
        )
    else:
        raise ValueError(
            "parameter_type must be simple_window_ratio or repeating_window_ratio."
        )
    artifact = _parameter_artifact(
        garden_id=manifest.garden_id,
        parameter_kind="window",
        parameter=parameter,
    )
    return {
        "parameter": artifact,
        "window_parameter": artifact,
        "object_dict": artifact,
        "target": artifact,
        "summary_view": {
            "parameter_kind": "window",
            "parameter_type": artifact["parameter_type"],
        },
        "report": make_report(
            status="ok",
            message=f"Created Dragonfly window parameter: {artifact['parameter_type']}",
        ),
    }


def create_dragonfly_shading_parameter(
    *,
    garden_root: str,
    parameter_type: str,
    depth: float,
    angle: float = 0,
) -> dict[str, Any]:
    """Create a compact Dragonfly ShadingParameter artifact."""
    garden_root_path = _garden_root(garden_root)
    manifest, _model_target = resolve_model_target(garden_root_path, None)
    normalized_type = _normalize_parameter_type(parameter_type)
    if normalized_type == "overhang":
        parameter = Overhang(depth, angle=angle)
    elif normalized_type == "extruded_border":
        parameter = ExtrudedBorder(depth)
    else:
        raise ValueError("parameter_type must be overhang or extruded_border.")
    artifact = _parameter_artifact(
        garden_id=manifest.garden_id,
        parameter_kind="shading",
        parameter=parameter,
    )
    return {
        "parameter": artifact,
        "shading_parameter": artifact,
        "object_dict": artifact,
        "target": artifact,
        "summary_view": {
            "parameter_kind": "shading",
            "parameter_type": artifact["parameter_type"],
        },
        "report": make_report(
            status="ok",
            message=f"Created Dragonfly shading parameter: {artifact['parameter_type']}",
        ),
    }


def _host_type_from_target(host_type: str | None, host_target: dict[str, Any] | None) -> str:
    if host_type:
        return _normalize_parameter_type(host_type)
    if host_target:
        return _normalize_parameter_type(str(host_target.get("object_type") or ""))
    return "model"


def _target_for_host(
    *,
    garden_id: str,
    model_identifier: str,
    host_type: str,
    host_identifier: str | None,
) -> dict[str, Any]:
    if host_type == "model":
        return {
            "target_type": "model",
            "garden_id": garden_id,
            "domain": "dragonfly",
            "model_identifier": model_identifier,
        }
    return make_dragonfly_object_target(
        garden_id=garden_id,
        model_identifier=model_identifier,
        object_type=host_type,
        object_identifier=str(host_identifier),
    )


def _apply_to_host(
    *,
    model: Model,
    host_type: str,
    host_target: dict[str, Any] | None,
    parameter: Any,
    parameter_kind: str,
    application_scope: str,
    segment_index: int | None,
) -> tuple[str, str | None]:
    if host_type == "model":
        host = model
        host_identifier = model.identifier
    else:
        if host_target is None:
            raise ValueError(f"host_target is required for host_type {host_type}.")
        normalized_target = normalize_dragonfly_object_target(
            host_target,
            expected_type=host_type,
        )
        host_identifier = str(normalized_target["object_identifier"])
        if host_type == "room2d":
            host = _room_by_identifier(model, host_identifier)
        elif host_type == "story":
            host = _story_by_identifier(model, host_identifier)
        elif host_type == "building":
            host = _building_by_identifier(model, host_identifier)
        else:
            raise ValueError(
                "host_type must be room2d, story, building, or model."
            )

    if parameter_kind == "window":
        if (
            host_type == "room2d"
            and _normalize_parameter_type(application_scope) == "segment"
        ):
            if segment_index is None:
                raise ValueError("segment_index is required for segment application.")
            host.set_window_parameter(segment_index, parameter)
        else:
            host.set_outdoor_window_parameters(parameter)
    elif parameter_kind == "shading":
        if _normalize_parameter_type(application_scope) == "segment":
            raise ValueError(
                "Dragonfly SDK exposes segment application for window parameters, "
                "not shading parameters."
            )
        host.set_outdoor_shading_parameters(parameter)
    else:
        raise ValueError("parameter_kind must be window or shading.")
    return host_type, host_identifier


def _parameter_counts(model: Model) -> dict[str, int]:
    window_count = 0
    shading_count = 0
    for room in model.room_2ds:
        window_count += sum(1 for item in room.window_parameters if item is not None)
        shading_count += sum(1 for item in room.shading_parameters if item is not None)
    return {
        "room2d_count": len(model.room_2ds),
        "window_parameter_count": window_count,
        "shading_parameter_count": shading_count,
    }


def apply_dragonfly_window_parameter(
    *,
    garden_root: str,
    window_parameter: dict[str, Any],
    host_type: str | None = None,
    host_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
    application_scope: str = "all_outdoor",
    segment_index: int | None = None,
) -> dict[str, Any]:
    """Apply a Dragonfly WindowParameter using public SDK set methods."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    parameter = _window_parameter_from_dict(window_parameter)
    resolved_host_type = _host_type_from_target(host_type, host_target)
    resolved_host_type, host_identifier = _apply_to_host(
        model=model,
        host_type=resolved_host_type,
        host_target=host_target,
        parameter=parameter,
        parameter_kind="window",
        application_scope=application_scope,
        segment_index=segment_index,
    )
    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    target = _target_for_host(
        garden_id=manifest.garden_id,
        model_identifier=str(updated_model_target["model_identifier"]),
        host_type=resolved_host_type,
        host_identifier=host_identifier,
    )
    counts = _parameter_counts(model)
    return {
        "target": target,
        "model_target": updated_model_target,
        "parameter": parameter.to_dict(),
        "summary_view": {
            "applied_to": target,
            "application_scope": application_scope,
            "parameter_type": parameter.to_dict()["type"],
            **counts,
        },
        "persistence_receipt": _receipt(
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            operation="apply_dragonfly_window_parameter",
            target=target,
            change_details={
                "application_scope": application_scope,
                "parameter_type": parameter.to_dict()["type"],
                **counts,
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Applied Dragonfly window parameter to {resolved_host_type}.",
        ),
    }


def apply_dragonfly_shading_parameter(
    *,
    garden_root: str,
    shading_parameter: dict[str, Any],
    host_type: str | None = None,
    host_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
    application_scope: str = "all_outdoor",
) -> dict[str, Any]:
    """Apply a Dragonfly ShadingParameter using public SDK set methods."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    parameter = _shading_parameter_from_dict(shading_parameter)
    resolved_host_type = _host_type_from_target(host_type, host_target)
    resolved_host_type, host_identifier = _apply_to_host(
        model=model,
        host_type=resolved_host_type,
        host_target=host_target,
        parameter=parameter,
        parameter_kind="shading",
        application_scope=application_scope,
        segment_index=None,
    )
    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    target = _target_for_host(
        garden_id=manifest.garden_id,
        model_identifier=str(updated_model_target["model_identifier"]),
        host_type=resolved_host_type,
        host_identifier=host_identifier,
    )
    counts = _parameter_counts(model)
    return {
        "target": target,
        "model_target": updated_model_target,
        "parameter": parameter.to_dict(),
        "summary_view": {
            "applied_to": target,
            "application_scope": application_scope,
            "parameter_type": parameter.to_dict()["type"],
            **counts,
        },
        "persistence_receipt": _receipt(
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            operation="apply_dragonfly_shading_parameter",
            target=target,
            change_details={
                "application_scope": application_scope,
                "parameter_type": parameter.to_dict()["type"],
                **counts,
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Applied Dragonfly shading parameter to {resolved_host_type}.",
        ),
    }
