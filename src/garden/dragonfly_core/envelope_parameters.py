"""Dragonfly envelope parameter services backed by SDK parameter objects."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dragonfly.building import Building
from dragonfly.clerestoryparameter import DetailedClerestory
from dragonfly.model import Model
from dragonfly.roof import RoofSpecification
from dragonfly.room2d import Room2D
from dragonfly.shadingparameter import (
    ExtrudedBorder,
    LouversByCount,
    LouversByDistance,
    Overhang,
)
from dragonfly.skylightparameter import (
    DetailedSkylights,
    GriddedSkylightArea,
    GriddedSkylightRatio,
)
from dragonfly.story import Story
from dragonfly.windowparameter import (
    DetailedWindows,
    RectangularWindows,
    RepeatingWindowRatio,
    RepeatingWindowWidthHeight,
    SimpleWindowArea,
    SimpleWindowRatio,
    SingleWindow,
)
from honeybee.boundarycondition import boundary_conditions
from ladybug_geometry.geometry2d import LineSegment2D, Point2D, Polygon2D, Vector2D
from ladybug_geometry.geometry3d import Point3D

from garden.dragonfly_core.model_io import (
    load_dragonfly_model,
    resolve_model_target,
    save_dragonfly_model,
)
from garden.dragonfly_core.targets import (
    make_dragonfly_object_target,
    normalize_dragonfly_object_target,
)
from ladybug_tools_mcp.contracts import make_persistence_receipt, make_report


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


def _unwrap_parameter_dict(data: dict[str, Any], *keys: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Parameter input must be a dictionary.")
    for key in keys:
        nested = data.get(key)
        if isinstance(nested, dict):
            return nested
    return data


def _point2d_list(points: Any) -> list[Point2D]:
    return [Point2D(float(pt[0]), float(pt[1])) for pt in points]


def _polygon2d_list(polygons: Any) -> list[Polygon2D]:
    result: list[Polygon2D] = []
    for poly in polygons:
        if isinstance(poly, Polygon2D):
            result.append(poly)
        elif isinstance(poly, dict):
            result.append(Polygon2D.from_dict(poly))
        else:
            result.append(Polygon2D(_point2d_list(poly)))
    return result


def _window_parameter_from_dict(data: dict[str, Any]) -> Any:
    data = _unwrap_parameter_dict(data, "parameter", "window_parameter")
    parameter_type = data.get("type") or data.get("parameter_type")
    if not parameter_type:
        if data.get("polygons") is not None:
            parameter_type = "detailed_windows"
        elif data.get("origins") is not None:
            parameter_type = "rectangular_windows"
        elif data.get("window_width") is not None:
            parameter_type = "repeating_window_width_height"
        elif data.get("window_area") is not None:
            parameter_type = "simple_window_area"
        elif data.get("width") is not None and data.get("height") is not None:
            parameter_type = "single_window"
        elif any(
            data.get(field) is not None
            for field in ("window_height", "sill_height", "horizontal_separation")
        ):
            parameter_type = "repeating_window_ratio"
        elif data.get("window_ratio") is not None:
            parameter_type = "simple_window_ratio"
    normalized_type = _normalize_parameter_type(str(parameter_type or ""))
    alias_map = {
        "singlewindow": "single_window",
        "simplewindowarea": "simple_window_area",
        "simplewindowratio": "simple_window_ratio",
        "repeatingwindowratio": "repeating_window_ratio",
        "repeatingwindowwidthheight": "repeating_window_width_height",
        "rectangularwindows": "rectangular_windows",
        "detailedwindows": "detailed_windows",
    }
    normalized_type = alias_map.get(normalized_type, normalized_type)
    if normalized_type == "single_window":
        return SingleWindow(
            float(data["width"]),
            float(data["height"]),
            sill_height=float(data.get("sill_height", 1)),
        )
    if normalized_type == "simple_window_area":
        return SimpleWindowArea(
            float(data["window_area"]),
            rect_split=bool(data.get("rect_split", True)),
        )
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
    if normalized_type == "repeating_window_width_height":
        return RepeatingWindowWidthHeight(
            float(data["window_height"]),
            float(data["window_width"]),
            float(data["sill_height"]),
            float(data["horizontal_separation"]),
        )
    if normalized_type == "rectangular_windows":
        origins = [
            pt if isinstance(pt, Point2D) else Point2D(float(pt[0]), float(pt[1]))
            for pt in data["origins"]
        ]
        widths = [float(w) for w in data["widths"]]
        heights = [float(h) for h in data["heights"]]
        are_doors = data.get("are_doors")
        return RectangularWindows(origins, widths, heights, are_doors=are_doors)
    if normalized_type == "detailed_windows":
        polygons = _polygon2d_list(data["polygons"])
        are_doors = data.get("are_doors")
        return DetailedWindows(polygons, are_doors=are_doors)
    raise ValueError(
        "Unsupported Dragonfly window parameter type. Supported values are "
        "single_window, simple_window_area, simple_window_ratio, "
        "repeating_window_ratio, repeating_window_width_height, "
        "rectangular_windows, and detailed_windows."
    )


def _shading_parameter_from_dict(data: dict[str, Any]) -> Any:
    data = _unwrap_parameter_dict(data, "parameter", "shading_parameter")
    parameter_type = data.get("type") or data.get("parameter_type")
    if not parameter_type:
        if data.get("louver_count") is not None:
            parameter_type = "louvers_by_count"
        elif data.get("distance") is not None:
            parameter_type = "louvers_by_distance"
        elif data.get("depth") is not None and "angle" in data:
            parameter_type = "overhang"
    normalized_type = _normalize_parameter_type(str(parameter_type or ""))
    alias_map = {
        "extrudedborder": "extruded_border",
        "louversbydistance": "louvers_by_distance",
        "louversbycount": "louvers_by_count",
    }
    normalized_type = alias_map.get(normalized_type, normalized_type)
    if normalized_type == "overhang":
        return Overhang(float(data["depth"]), angle=float(data.get("angle", 0)))
    if normalized_type == "extruded_border":
        return ExtrudedBorder(float(data["depth"]))
    if normalized_type == "louvers_by_distance":
        cv = data.get("contour_vector")
        contour_vector = (
            Vector2D(float(cv[0]), float(cv[1])) if cv is not None else Vector2D(0, 1)
        )
        return LouversByDistance(
            float(data["distance"]),
            float(data["depth"]),
            offset=float(data.get("offset", 0)),
            angle=float(data.get("angle", 0)),
            contour_vector=contour_vector,
            flip_start_side=bool(data.get("flip_start_side", False)),
        )
    if normalized_type == "louvers_by_count":
        cv = data.get("contour_vector")
        contour_vector = (
            Vector2D(float(cv[0]), float(cv[1])) if cv is not None else Vector2D(0, 1)
        )
        return LouversByCount(
            int(data["louver_count"]),
            float(data["depth"]),
            offset=float(data.get("offset", 0)),
            angle=float(data.get("angle", 0)),
            contour_vector=contour_vector,
            flip_start_side=bool(data.get("flip_start_side", False)),
        )
    raise ValueError(
        "Unsupported Dragonfly shading parameter type. Supported values are "
        "overhang, extruded_border, louvers_by_distance, and louvers_by_count."
    )


def _skylight_parameter_from_dict(data: dict[str, Any]) -> Any:
    data = _unwrap_parameter_dict(data, "parameter", "skylight_parameter")
    parameter_type = data.get("type") or data.get("parameter_type")
    if not parameter_type:
        if data.get("polygons") is not None:
            parameter_type = "detailed_skylights"
        elif data.get("skylight_area") is not None:
            parameter_type = "gridded_skylight_area"
        elif data.get("skylight_ratio") is not None:
            parameter_type = "gridded_skylight_ratio"
    normalized_type = _normalize_parameter_type(str(parameter_type or ""))
    alias_map = {
        "griddedskylightarea": "gridded_skylight_area",
        "griddedskylightratio": "gridded_skylight_ratio",
        "detailedskylights": "detailed_skylights",
    }
    normalized_type = alias_map.get(normalized_type, normalized_type)
    spacing = data.get("spacing")
    if normalized_type == "gridded_skylight_area":
        if spacing is None or spacing == "Autocalculate":
            return GriddedSkylightArea(float(data["skylight_area"]))
        return GriddedSkylightArea(float(data["skylight_area"]), spacing=float(spacing))
    if normalized_type == "gridded_skylight_ratio":
        if spacing is None or spacing == "Autocalculate":
            return GriddedSkylightRatio(float(data["skylight_ratio"]))
        return GriddedSkylightRatio(float(data["skylight_ratio"]), spacing=float(spacing))
    if normalized_type == "detailed_skylights":
        return DetailedSkylights(
            _polygon2d_list(data["polygons"]),
            are_doors=data.get("are_doors"),
        )
    raise ValueError(
        "Unsupported Dragonfly skylight parameter type. Supported values are "
        "gridded_skylight_area, gridded_skylight_ratio, and detailed_skylights."
    )


def _clerestory_parameter_from_dict(data: dict[str, Any]) -> DetailedClerestory:
    data = _unwrap_parameter_dict(data, "parameter", "clerestory_parameter")
    if data.get("type") == "DetailedClerestory" and isinstance(data.get("base_line"), dict):
        return DetailedClerestory.from_dict(data)
    raw_line = data.get("base_line")
    if isinstance(raw_line, LineSegment2D):
        base_line = raw_line
    elif isinstance(raw_line, dict):
        base_line = LineSegment2D.from_dict(raw_line)
    elif isinstance(raw_line, (list, tuple)) and len(raw_line) == 2:
        pts = [Point2D(float(p[0]), float(p[1])) for p in raw_line]
        base_line = LineSegment2D.from_end_points(pts[0], pts[1])
    else:
        raise ValueError("DetailedClerestory requires base_line as two 2D points or a LineSegment2D dict.")
    return DetailedClerestory(
        base_line,
        float(data["elevation"]),
        _polygon2d_list(data["polygons"]),
        are_doors=data.get("are_doors"),
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
    window_ratio: float | None = None,
    rect_split: bool = True,
    window_height: float | None = None,
    sill_height: float | None = None,
    horizontal_separation: float | None = None,
    vertical_separation: float = 0,
    width: float | None = None,
    height: float | None = None,
    window_area: float | None = None,
    window_width: float | None = None,
    origins: list[list[float]] | None = None,
    widths: list[float] | None = None,
    heights: list[float] | None = None,
    polygons: list[list[list[float]]] | None = None,
    are_doors: list[bool] | None = None,
) -> dict[str, Any]:
    """Create a compact Dragonfly WindowParameter artifact."""
    garden_root_path = _garden_root(garden_root)
    manifest, _model_target = resolve_model_target(garden_root_path, None)
    payload = {
        k: v
        for k, v in {
            "parameter_type": parameter_type,
            "window_ratio": window_ratio,
            "rect_split": rect_split,
            "window_height": window_height,
            "sill_height": sill_height,
            "horizontal_separation": horizontal_separation,
            "vertical_separation": vertical_separation,
            "width": width,
            "height": height,
            "window_area": window_area,
            "window_width": window_width,
            "origins": origins,
            "widths": widths,
            "heights": heights,
            "polygons": polygons,
            "are_doors": are_doors,
        }.items()
        if v is not None
    }
    try:
        parameter = _window_parameter_from_dict(payload)
    except KeyError as exc:
        raise ValueError(f"{parameter_type} requires field: {exc.args[0]}.") from exc
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
    distance: float | None = None,
    louver_count: int | None = None,
    offset: float = 0,
    contour_vector: list[float] | None = None,
    flip_start_side: bool = False,
) -> dict[str, Any]:
    """Create a compact Dragonfly ShadingParameter artifact."""
    garden_root_path = _garden_root(garden_root)
    manifest, _model_target = resolve_model_target(garden_root_path, None)
    payload = {
        k: v
        for k, v in {
            "parameter_type": parameter_type,
            "depth": depth,
            "angle": angle,
            "distance": distance,
            "louver_count": louver_count,
            "offset": offset,
            "contour_vector": contour_vector,
            "flip_start_side": flip_start_side,
        }.items()
        if v is not None
    }
    try:
        parameter = _shading_parameter_from_dict(payload)
    except KeyError as exc:
        raise ValueError(f"{parameter_type} requires field: {exc.args[0]}.") from exc
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


def create_dragonfly_skylight_parameter(
    *,
    garden_root: str,
    parameter_type: str,
    skylight_area: float | None = None,
    skylight_ratio: float | None = None,
    spacing: float | str | None = None,
    polygons: list[list[list[float]]] | None = None,
    are_doors: list[bool] | None = None,
) -> dict[str, Any]:
    """Create a compact Dragonfly SkylightParameter artifact."""
    garden_root_path = _garden_root(garden_root)
    manifest, _model_target = resolve_model_target(garden_root_path, None)
    payload = {
        k: v
        for k, v in {
            "parameter_type": parameter_type,
            "skylight_area": skylight_area,
            "skylight_ratio": skylight_ratio,
            "spacing": spacing,
            "polygons": polygons,
            "are_doors": are_doors,
        }.items()
        if v is not None
    }
    try:
        parameter = _skylight_parameter_from_dict(payload)
    except KeyError as exc:
        raise ValueError(f"{parameter_type} requires field: {exc.args[0]}.") from exc
    artifact = _parameter_artifact(
        garden_id=manifest.garden_id,
        parameter_kind="skylight",
        parameter=parameter,
    )
    return {
        "parameter": artifact,
        "skylight_parameter": artifact,
        "object_dict": artifact,
        "target": artifact,
        "summary_view": {
            "parameter_kind": "skylight",
            "parameter_type": artifact["parameter_type"],
        },
        "report": make_report(
            status="ok",
            message=f"Created Dragonfly skylight parameter: {artifact['parameter_type']}",
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
    model_target: dict[str, Any],
    host_type: str,
    host_identifier: str | None,
) -> dict[str, Any]:
    if host_type == "model":
        return model_target
    return make_dragonfly_object_target(
        garden_id=str(model_target["garden_id"]),
        model_identifier=str(model_target["model_identifier"]),
        object_type=host_type,
        object_identifier=str(host_identifier),
    )


def _is_segment_scope(application_scope: str, segment_index: int | list[int] | None) -> bool:
    if segment_index is not None:
        return True
    return _normalize_parameter_type(application_scope) in {"segment", "segmentindex"}


def _apply_to_host(
    *,
    model: Model,
    host_type: str,
    host_target: dict[str, Any] | None,
    parameter: Any,
    parameter_kind: str,
    application_scope: str,
    segment_index: int | list[int] | None,
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

    is_segment = _is_segment_scope(application_scope, segment_index)
    if parameter_kind == "window":
        if host_type == "room2d" and is_segment:
            if segment_index is None:
                raise ValueError("segment_index is required for segment application.")
            if isinstance(segment_index, (list, tuple)):
                if not segment_index:
                    raise ValueError("segment_index list must not be empty.")
                for idx in segment_index:
                    host.set_window_parameter(int(idx), parameter)
            else:
                host.set_window_parameter(int(segment_index), parameter)
        elif is_segment:
            raise ValueError("Segment application requires host_type='room2d'.")
        else:
            host.set_outdoor_window_parameters(parameter)
    elif parameter_kind == "shading":
        if host_type == "room2d" and is_segment:
            if segment_index is None:
                raise ValueError("segment_index is required for segment application.")
            indices = (
                [int(i) for i in segment_index]
                if isinstance(segment_index, (list, tuple))
                else [int(segment_index)]
            )
            if not indices:
                raise ValueError("segment_index list must not be empty.")
            updated = list(host.shading_parameters)
            for idx in indices:
                updated[idx] = parameter
            host.shading_parameters = updated
        elif is_segment:
            raise ValueError("Segment application requires host_type='room2d'.")
        else:
            host.set_outdoor_shading_parameters(parameter)
    elif parameter_kind == "skylight":
        if host_type == "room2d":
            host.skylight_parameters = parameter
        elif host_type == "story":
            for room in host.room_2ds:
                room.skylight_parameters = parameter
        elif host_type == "building":
            for room in host.unique_room_2ds:
                room.skylight_parameters = parameter
        else:
            for room in model.room_2ds:
                room.skylight_parameters = parameter
    else:
        raise ValueError("parameter_kind must be window, shading, or skylight.")
    return host_type, host_identifier


def _parameter_counts(model: Model) -> dict[str, int]:
    window_count = 0
    shading_count = 0
    skylight_count = 0
    for room in model.room_2ds:
        window_count += sum(1 for item in room.window_parameters if item is not None)
        shading_count += sum(1 for item in room.shading_parameters if item is not None)
        if getattr(room, "skylight_parameters", None) is not None:
            skylight_count += 1
    return {
        "room2d_count": len(model.room_2ds),
        "window_parameter_count": window_count,
        "shading_parameter_count": shading_count,
        "skylight_parameter_count": skylight_count,
    }


def apply_dragonfly_window_parameter(
    *,
    garden_root: str,
    window_parameter: dict[str, Any],
    host_type: str | None = None,
    host_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
    application_scope: str = "all_outdoor",
    segment_index: int | list[int] | None = None,
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
        model_target=updated_model_target,
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
    segment_index: int | list[int] | None = None,
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
        segment_index=segment_index,
    )
    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    target = _target_for_host(
        model_target=updated_model_target,
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


def apply_dragonfly_skylight_parameter(
    *,
    garden_root: str,
    skylight_parameter: dict[str, Any],
    host_type: str | None = None,
    host_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply a Dragonfly SkylightParameter to a Room2D, Story, Building, or Model."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    parameter = _skylight_parameter_from_dict(skylight_parameter)
    resolved_host_type = _host_type_from_target(host_type, host_target)
    resolved_host_type, host_identifier = _apply_to_host(
        model=model,
        host_type=resolved_host_type,
        host_target=host_target,
        parameter=parameter,
        parameter_kind="skylight",
        application_scope="roof",
        segment_index=None,
    )
    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    target = _target_for_host(
        model_target=updated_model_target,
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
            "parameter_type": parameter.to_dict()["type"],
            **counts,
        },
        "persistence_receipt": _receipt(
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            operation="apply_dragonfly_skylight_parameter",
            target=target,
            change_details={
                "parameter_type": parameter.to_dict()["type"],
                **counts,
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Applied Dragonfly skylight parameter to {resolved_host_type}.",
        ),
    }


def apply_dragonfly_clerestory_parameter(
    *,
    garden_root: str,
    clerestory_parameter: dict[str, Any],
    host_target: dict[str, Any] | None = None,
    story_identifier: str | None = None,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach a DetailedClerestory to a Story's RoofSpecification."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    if story_identifier is None and host_target is not None:
        normalized = normalize_dragonfly_object_target(host_target, expected_type="story")
        story_identifier = str(normalized["object_identifier"])
    if not story_identifier:
        raise ValueError("apply_dragonfly_clerestory_parameter requires a Story target or story_identifier.")
    story = _story_by_identifier(model, story_identifier)
    if story.roof is None:
        raise ValueError(
            f"Story {story.identifier} must have roof geometry assigned before adding clerestories."
        )
    clerestory = _clerestory_parameter_from_dict(clerestory_parameter)
    existing = list(story.roof.clerestory_parameters or ())
    story.roof = RoofSpecification(
        list(story.roof.geometry),
        clerestory_parameters=[*existing, clerestory],
    )
    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    target = _target_for_host(
        model_target=updated_model_target,
        host_type="story",
        host_identifier=story.identifier,
    )
    return {
        "target": target,
        "model_target": updated_model_target,
        "parameter": clerestory.to_dict(),
        "summary_view": {
            "applied_to": target,
            "clerestory_count": len(story.roof.clerestory_parameters or ()),
        },
        "persistence_receipt": _receipt(
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            operation="apply_dragonfly_clerestory_parameter",
            target=target,
            change_details={"clerestory_count": len(story.roof.clerestory_parameters or ())},
        ),
        "report": make_report(
            status="ok",
            message=f"Added DetailedClerestory to Story {story.identifier} roof.",
        ),
    }


def _resolve_boundary_condition(value: Any) -> Any:
    if isinstance(value, str):
        return boundary_conditions.by_name(value)
    if isinstance(value, dict):
        bc_type = value.get("type")
        if bc_type == "OtherSideTemperature":
            from honeybee.boundarycondition import OtherSideTemperature

            return OtherSideTemperature.from_dict(value)
        if isinstance(bc_type, str):
            return boundary_conditions.by_name(bc_type)
    raise ValueError(
        "boundary_condition must be Outdoors, Ground, Adiabatic, Surface, or OtherSideTemperature dict."
    )


def apply_dragonfly_wall_properties(
    *,
    garden_root: str,
    host_target: dict[str, Any] | None = None,
    host_type: str | None = None,
    model_target: dict[str, Any] | None = None,
    segment_index: int | list[int] | None = None,
    air_boundary: bool | None = None,
    air_boundaries: list[bool] | None = None,
    boundary_condition: str | dict[str, Any] | None = None,
    guide_lines: list[list[list[float]]] | None = None,
    room_identifiers: list[str] | None = None,
    wall_modifiers: dict[str, Any] | None = None,
    tolerance: float = 0.01,
) -> dict[str, Any]:
    """Configure Room2D air boundaries, wall boundary conditions, or Story wall modifiers."""
    garden_root_path, manifest, resolved_model_target, model = _load_target_model(
        garden_root,
        model_target,
    )
    resolved_host_type = _host_type_from_target(host_type, host_target)
    host_identifier = model.identifier
    if wall_modifiers is not None:
        parsed_modifiers: dict[str, tuple[list[Any], list[Any]]] = {}
        from ladybug_geometry.geometry2d.line import LineSegment2D
        from ladybug_geometry.geometry2d.polyline import Polyline2D

        for story_id, pair in wall_modifiers.items():
            raw_geos, raw_props = pair
            geos: list[Any] = []
            for raw_geo in raw_geos:
                if isinstance(raw_geo, dict):
                    if raw_geo.get("type") == "Polygon2D":
                        geos.append(Polygon2D.from_dict(raw_geo))
                    elif raw_geo.get("type") == "Polyline2D":
                        geos.append(Polyline2D.from_dict(raw_geo))
                    else:
                        geos.append(LineSegment2D.from_dict(raw_geo))
                elif len(raw_geo) == 2:
                    geos.append(
                        LineSegment2D.from_end_points(
                            Point2D(float(raw_geo[0][0]), float(raw_geo[0][1])),
                            Point2D(float(raw_geo[1][0]), float(raw_geo[1][1])),
                        )
                    )
                else:
                    geos.append(Polygon2D(_point2d_list(raw_geo)))
            props = [
                p if p in {"AirBoundary", "Ground", "Adiabatic"} else _resolve_boundary_condition(p)
                for p in raw_props
            ]
            parsed_modifiers[story_id] = (geos, props)
        model.resolve_wall_properties(wall_modifiers=parsed_modifiers)
    elif resolved_host_type == "story":
        if host_target is None:
            raise ValueError("host_target is required for story wall properties.")
        normalized = normalize_dragonfly_object_target(host_target, expected_type="story")
        host_identifier = str(normalized["object_identifier"])
        story = _story_by_identifier(model, host_identifier)
        from ladybug_geometry.geometry2d.line import LineSegment2D

        parsed_lines = (
            [
                LineSegment2D.from_end_points(
                    Point2D(float(line[0][0]), float(line[0][1])),
                    Point2D(float(line[1][0]), float(line[1][1])),
                )
                for line in guide_lines
            ]
            if guide_lines
            else None
        )
        story.set_adjacent_air_boundary(
            room_ids=room_identifiers,
            guide_lines=parsed_lines,
            tolerance=float(tolerance),
        )
    elif resolved_host_type == "room2d":
        if host_target is None:
            raise ValueError("host_target is required for room2d wall properties.")
        normalized = normalize_dragonfly_object_target(host_target, expected_type="room2d")
        host_identifier = str(normalized["object_identifier"])
        room = _room_by_identifier(model, host_identifier)
        indices = (
            [int(i) for i in segment_index]
            if isinstance(segment_index, (list, tuple))
            else ([int(segment_index)] if segment_index is not None else [])
        )
        if boundary_condition is not None:
            if not indices:
                raise ValueError("segment_index is required when setting boundary_condition on a Room2D.")
            bc = _resolve_boundary_condition(boundary_condition)
            if bc.__class__.__name__ not in {"Outdoors", "Surface"}:
                win_params = list(room.window_parameters)
                for idx in indices:
                    win_params[idx] = None
                room.window_parameters = win_params
            for idx in indices:
                room.set_boundary_condition(idx, bc)
        if air_boundaries is not None:
            updated = [bool(val) for val in air_boundaries]
            room.window_parameters = [
                None if flag else wp for flag, wp in zip(updated, room.window_parameters)
            ]
            room.air_boundaries = updated
        elif air_boundary is not None:
            if not indices:
                raise ValueError("segment_index is required when setting air_boundary on a Room2D.")
            updated = list(room.air_boundaries)
            for idx in indices:
                updated[idx] = bool(air_boundary)
            room.window_parameters = [
                None if flag else wp for flag, wp in zip(updated, room.window_parameters)
            ]
            room.air_boundaries = updated
        elif boundary_condition is None:
            raise ValueError("Provide air_boundary, air_boundaries, or boundary_condition.")
    else:
        raise ValueError(
            "Wall properties require room2d host, story host (adjacent air boundaries), "
            "or wall_modifiers dict."
        )

    updated_model_target, persisted_path = _save_changed_model(
        garden_root_path,
        manifest,
        resolved_model_target,
        model,
    )
    target = _target_for_host(
        model_target=updated_model_target,
        host_type=resolved_host_type,
        host_identifier=host_identifier,
    )
    return {
        "target": target,
        "model_target": updated_model_target,
        "summary_view": {
            "applied_to": target,
            "host_type": resolved_host_type,
            "host_identifier": host_identifier,
        },
        "persistence_receipt": _receipt(
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            operation="apply_dragonfly_wall_properties",
            target=target,
        ),
        "report": make_report(
            status="ok",
            message=f"Applied Dragonfly wall properties to {resolved_host_type}.",
        ),
    }
