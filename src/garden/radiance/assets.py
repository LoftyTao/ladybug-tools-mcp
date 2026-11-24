"""Honeybee Radiance sensor grid and view foundation services."""

from __future__ import annotations

import json
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from honeybee.room import Room
from honeybee_radiance.sensorgrid import SensorGrid
from honeybee_radiance.view import View
from ladybug_geometry.geometry3d.pointvector import Vector3D

from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target,
    save_honeybee_model,
)
from garden.honeybee_core.locate import find_object
from garden.honeybee_core.targets import normalize_honeybee_object_target
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from ladybug_tools_mcp.contracts import (
    make_artifact_receipt,
    make_persistence_receipt,
    make_report,
)

SENSOR_GRID_TARGET_TYPE = "radiance_sensor_grid"
SENSOR_GRID_ARTIFACT_TYPE = "radiance_sensor_grid"
VIEW_TARGET_TYPE = "radiance_view"
VIEW_ARTIFACT_TYPE = "radiance_view"
SENSOR_GRID_OUTPUT_SUBDIR = "artifacts/radiance/sensors"
VIEW_OUTPUT_SUBDIR = "artifacts/radiance/views"


def _vector3(value: list[float] | tuple[float, float, float], field_name: str) -> tuple[float, float, float]:
    if len(value) != 3:
        raise ValueError(f"{field_name} must include exactly three numbers.")
    return (float(value[0]), float(value[1]), float(value[2]))


def _vectors3(values: list[list[float]], field_name: str) -> list[tuple[float, float, float]]:
    if not values:
        raise ValueError(f"{field_name} must include at least one [x, y, z] value.")
    return [_vector3(value, field_name) for value in values]


def _resolve_output_dir(garden_root: Path, output_subdir: str) -> Path:
    normalized_subdir = output_subdir.strip().lower().replace("\\", "/")
    if normalized_subdir in {
        "sensorgrids",
        "sensor_grids",
        "radiance/sensorgrids",
        "radiance/sensor_grids",
        "radiance/sensors",
        "artifacts/radiance/sensorgrids",
        "artifacts/radiance/sensor_grids",
    }:
        output_subdir = SENSOR_GRID_OUTPUT_SUBDIR
    elif normalized_subdir in {
        "views",
        "radiance/views",
        "radiance/view",
        "artifacts/radiance/view",
    }:
        output_subdir = VIEW_OUTPUT_SUBDIR
    output_dir = (garden_root / output_subdir).resolve()
    output_dir.relative_to(garden_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _register_artifact(
    manifest: GardenManifest,
    *,
    artifact_type: str,
    name: str,
    path: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    record = {
        "artifact_type": artifact_type,
        "name": name,
        "path": path,
        "source": source,
        "created_at": utc_now_iso(),
    }
    return manifest.upsert_artifact(record)


def _target(
    *,
    manifest: GardenManifest,
    target_type: str,
    identifier: str,
    path: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target = {
        "target_type": target_type,
        "domain": "honeybee_radiance",
        "garden_id": manifest.garden_id,
        "identifier": identifier,
        "path": path,
    }
    if metadata:
        target.update(metadata)
    return target


def _write_artifact(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    identifier: str,
    output_subdir: str,
    extension: str,
    text: str,
    artifact_type: str,
    source: dict[str, Any],
    target_type: str,
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    output_dir = _resolve_output_dir(garden_root, output_subdir)
    artifact_path_abs = (output_dir / f"{identifier}.{extension}").resolve()
    artifact_path_abs.relative_to(garden_root)
    artifact_path_abs.write_text(f"{text.rstrip()}\n", encoding="utf-8", newline="\n")
    artifact_path = to_posix_relative(artifact_path_abs, garden_root)
    artifact = _register_artifact(
        manifest,
        artifact_type=artifact_type,
        name=identifier,
        path=artifact_path,
        source=source,
    )
    target = _target(
        manifest=manifest,
        target_type=target_type,
        identifier=identifier,
        path=artifact_path,
    )
    return target, artifact, artifact_path_abs


def _save_model_with_radiance_asset(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    model_target: dict[str, Any],
    model: Any,
    operation: str,
    asset_target: dict[str, Any],
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    updated_model_target, persisted_path = save_honeybee_model(
        garden_root,
        manifest,
        model,
        name=str(model_target["model_identifier"]),
        set_base=manifest.base_honeybee_model == model_target,
    )
    receipt = make_persistence_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        model_target=updated_model_target,
        persisted_path=persisted_path,
        change_summary={
            "operation": operation,
            "asset_target": asset_target,
        },
    )
    return updated_model_target, persisted_path, receipt


def _sensor_grid_summary(
    sensor_grid: SensorGrid,
    *,
    target: dict[str, Any] | None,
    attached_to_model: bool,
) -> dict[str, Any]:
    return {
        "type": "SensorGrid",
        "identifier": sensor_grid.identifier,
        "target": target,
        "sensor_count": len(sensor_grid.sensors),
        "room_identifier": sensor_grid.room_identifier,
        "group_identifier": sensor_grid.group_identifier,
        "attached_to_model": attached_to_model,
    }


def _view_summary(
    view: View,
    *,
    target: dict[str, Any] | None,
    attached_to_model: bool,
) -> dict[str, Any]:
    return {
        "type": "View",
        "identifier": view.identifier,
        "target": target,
        "view_type": view.type,
        "position": list(view.position),
        "direction": list(view.direction),
        "up_vector": list(view.up_vector),
        "h_size": view.h_size,
        "v_size": view.v_size,
        "room_identifier": view.room_identifier,
        "group_identifier": view.group_identifier,
        "attached_to_model": attached_to_model,
    }


def _sensor_grid_from_inputs(
    *,
    identifier: str,
    positions: list[list[float]],
    direction: list[float] | None,
    directions: list[list[float]] | None,
) -> SensorGrid:
    position_values = _vectors3(positions, "positions")
    if direction is not None and directions is not None:
        raise ValueError("Use either direction or directions, not both.")
    if directions is not None:
        direction_values = _vectors3(directions, "directions")
        if len(direction_values) != len(position_values):
            raise ValueError("directions must have the same length as positions.")
    else:
        single_direction = _vector3(direction or [0, 0, 1], "direction")
        direction_values = [single_direction for _ in position_values]
    return SensorGrid.from_position_and_direction(
        identifier,
        position_values,
        direction_values,
    )


def _sensor_grid_from_face3d(
    *,
    identifier: str,
    geometry: Any,
    grid_spacing: float | None,
    x_count: int | None,
    y_count: int | None,
    offset: float,
    flip_direction: bool,
) -> SensorGrid:
    if geometry is None or geometry.__class__.__name__ != "Face3D":
        raise ValueError("Object target must expose Face3D geometry.")
    raw_vertices = getattr(geometry, "vertices", None) or getattr(geometry, "boundary", None)
    vertices = [_point3(vertex) for vertex in raw_vertices or []]
    if len(vertices) < 3:
        raise ValueError("Object Face3D geometry must include at least three vertices.")
    normal = _normalize(_point3(geometry.normal), "surface normal")
    origin = vertices[0]
    x_axis = None
    for vertex in vertices[1:]:
        edge = _subtract(vertex, origin)
        if _length(edge) > 1e-9:
            x_axis = _normalize(edge, "surface x-axis")
            break
    if x_axis is None:
        raise ValueError("Object Face3D geometry must include a non-zero edge.")
    y_axis = _normalize(_cross(normal, x_axis), "surface y-axis")
    local_vertices = [
        (_dot(_subtract(vertex, origin), x_axis), _dot(_subtract(vertex, origin), y_axis))
        for vertex in vertices
    ]
    width = max(point[0] for point in local_vertices) - min(
        point[0] for point in local_vertices
    )
    depth = max(point[1] for point in local_vertices) - min(
        point[1] for point in local_vertices
    )
    if width <= 0 or depth <= 0:
        raise ValueError("Object Face3D geometry must span a two-dimensional area.")
    if grid_spacing is not None:
        if grid_spacing <= 0:
            raise ValueError("grid_spacing must be greater than zero.")
        x_count = max(1, int(width / grid_spacing)) if x_count is None else x_count
        y_count = max(1, int(depth / grid_spacing)) if y_count is None else y_count
    else:
        x_count = 1 if x_count is None else x_count
        y_count = 1 if y_count is None else y_count
    if x_count < 1 or y_count < 1:
        raise ValueError("x_count and y_count must be at least 1.")
    x_dim = width / x_count
    y_dim = depth / y_count
    return SensorGrid.from_face3d(
        identifier,
        [geometry],
        x_dim,
        y_dim,
        offset=offset,
        flip=flip_direction,
    )


def _point3(value: Any) -> tuple[float, float, float]:
    if hasattr(value, "x") and hasattr(value, "y") and hasattr(value, "z"):
        return (float(value.x), float(value.y), float(value.z))
    return (float(value[0]), float(value[1]), float(value[2]))


def _subtract(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _length(value: tuple[float, float, float]) -> float:
    return (_dot(value, value)) ** 0.5


def _normalize(value: tuple[float, float, float], field_name: str) -> tuple[float, float, float]:
    length = _length(value)
    if length <= 0:
        raise ValueError(f"{field_name} must not be a zero-length vector.")
    return (value[0] / length, value[1] / length, value[2] / length)


def _persist_sensor_grid(
    *,
    sensor_grid: SensorGrid,
    garden_root: str | None,
    model_target: dict[str, Any] | None,
    attach_to_model: bool,
    output_subdir: str,
    return_object_dict: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "object_dict": sensor_grid.to_dict(),
        "summary_view": _sensor_grid_summary(
            sensor_grid,
            target=None,
            attached_to_model=False,
        ),
        "report": make_report(
            status="ok",
            message=f"Created Radiance SensorGrid: {sensor_grid.identifier}",
        ),
    }
    if garden_root is None:
        return result

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    source = {
        "source_type": "sensor_grid",
        "sensor_count": len(sensor_grid.sensors),
        "attached_to_model": attach_to_model,
        "has_mesh": sensor_grid.mesh is not None,
    }
    target, artifact, artifact_path_abs = _write_artifact(
        garden_root=garden_root_path,
        manifest=manifest,
        identifier=sensor_grid.identifier,
        output_subdir=output_subdir,
        extension="pts",
        text=sensor_grid.to_radiance(),
        artifact_type=SENSOR_GRID_ARTIFACT_TYPE,
        source=source,
        target_type=SENSOR_GRID_TARGET_TYPE,
    )
    json_path_abs = artifact_path_abs.with_suffix(".json")
    json_path_abs.write_text(
        json.dumps(sensor_grid.to_dict(), indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    json_rel = to_posix_relative(json_path_abs, garden_root_path)
    source["json_path"] = json_rel
    target["json_path"] = json_rel
    result.update(
        {
            "target": target,
            "sensor_grid_target": target,
            "artifact": artifact,
            "persistence_receipt": make_artifact_receipt(
                status="persisted",
                garden_id=manifest.garden_id,
                artifact_type=SENSOR_GRID_ARTIFACT_TYPE,
                artifact_path=target["path"],
                absolute_path=str(artifact_path_abs),
                source=source,
            ),
        }
    )
    result["summary_view"] = _sensor_grid_summary(
        sensor_grid,
        target=target,
        attached_to_model=False,
    )
    result["summary_view"]["has_mesh"] = sensor_grid.mesh is not None
    result["summary_view"]["json_path"] = json_rel

    if attach_to_model:
        manifest.write(garden_root_path)
        manifest, resolved_model_target = resolve_model_target(
            garden_root_path,
            model_target,
        )
        model = load_honeybee_model(garden_root_path, resolved_model_target)
        model.properties.radiance.add_sensor_grid(sensor_grid)
        updated_model_target, persisted_path, model_receipt = _save_model_with_radiance_asset(
            garden_root=garden_root_path,
            manifest=manifest,
            model_target=resolved_model_target,
            model=model,
            operation="create_radiance_sensor_grid",
            asset_target=target,
        )
        result["model_target"] = updated_model_target
        result["model_persistence_receipt"] = model_receipt
        result["summary_view"]["attached_to_model"] = True
        result["summary_view"]["model_target"] = updated_model_target
        result["summary_view"]["model_path"] = persisted_path
    else:
        manifest.write(garden_root_path)

    if not return_object_dict:
        result.pop("object_dict", None)
    return result


def _sensor_grid_from_target(
    garden_root: Path,
    target: dict[str, Any],
) -> SensorGrid:
    if target.get("target_type") != SENSOR_GRID_TARGET_TYPE:
        raise ValueError("add_sensor_grids entries must be radiance_sensor_grid targets.")
    relative_path = target.get("path")
    if not isinstance(relative_path, str) or not relative_path:
        raise ValueError("radiance_sensor_grid target must include a Garden-relative path.")
    pts_path = (garden_root / relative_path).resolve()
    pts_path.relative_to(garden_root)
    json_rel = target.get("json_path")
    sidecar_path = (
        (garden_root / json_rel).resolve()
        if isinstance(json_rel, str) and json_rel
        else pts_path.with_suffix(".json")
    )
    sidecar_path.relative_to(garden_root)
    if sidecar_path.is_file():
        return SensorGrid.from_dict(json.loads(sidecar_path.read_text(encoding="utf-8")))
    positions: list[list[float]] = []
    directions: list[list[float]] = []
    for line in pts_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        values = [float(value) for value in stripped.split()]
        if len(values) != 6:
            raise ValueError("Radiance sensor grid .pts lines must contain x y z dx dy dz.")
        positions.append(values[:3])
        directions.append(values[3:])
    identifier = str(target.get("identifier") or pts_path.stem)
    return _sensor_grid_from_inputs(
        identifier=identifier,
        positions=positions,
        direction=None,
        directions=directions,
    )


def _view_from_target(
    garden_root: Path,
    target: dict[str, Any],
) -> View:
    if target.get("target_type") != VIEW_TARGET_TYPE:
        raise ValueError("add_radiance_views entries must be radiance_view targets.")
    relative_path = target.get("path")
    if not isinstance(relative_path, str) or not relative_path:
        raise ValueError("radiance_view target must include a Garden-relative path.")
    vf_path = (garden_root / relative_path).resolve()
    vf_path.relative_to(garden_root)
    identifier = str(target.get("identifier") or vf_path.stem)
    view = View.from_string(identifier, vf_path.read_text(encoding="utf-8"))
    if view.identifier != identifier:
        view.identifier = identifier
    return view


def attach_radiance_sensor_grids_to_model(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None,
    sensor_grid_targets: list[dict[str, Any]],
) -> dict[str, Any]:
    """Attach existing Garden SensorGrid artifacts to a Honeybee model."""
    if not sensor_grid_targets:
        raise ValueError("sensor_grid_targets must include at least one target.")
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(
        garden_root_path,
        model_target,
    )
    model = load_honeybee_model(garden_root_path, resolved_model_target)
    attached_identifiers: list[str] = []
    for sensor_grid_target in sensor_grid_targets:
        sensor_grid = _sensor_grid_from_target(garden_root_path, sensor_grid_target)
        model.properties.radiance.add_sensor_grid(sensor_grid)
        attached_identifiers.append(sensor_grid.identifier)
    updated_model_target, persisted_path, receipt = _save_model_with_radiance_asset(
        garden_root=garden_root_path,
        manifest=manifest,
        model_target=resolved_model_target,
        model=model,
        operation="attach_radiance_sensor_grids_to_model",
        asset_target={"sensor_grid_targets": sensor_grid_targets},
    )
    return {
        "target": updated_model_target,
        "model_target": updated_model_target,
        "summary_view": {
            "model_identifier": updated_model_target.get("identifier"),
            "radiance_sensor_grid_count": len(model.properties.radiance.sensor_grids),
            "attached_sensor_grid_identifiers": attached_identifiers,
            "model_path": persisted_path,
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=f"Attached {len(attached_identifiers)} Radiance SensorGrid target(s) to model.",
        ),
    }


def attach_radiance_views_to_model(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None,
    view_targets: list[dict[str, Any]],
) -> dict[str, Any]:
    """Attach existing Garden View artifacts to a Honeybee model."""
    if not view_targets:
        raise ValueError("view_targets must include at least one target.")
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(
        garden_root_path,
        model_target,
    )
    model = load_honeybee_model(garden_root_path, resolved_model_target)
    attached_identifiers: list[str] = []
    for view_target in view_targets:
        view = _view_from_target(garden_root_path, view_target)
        model.properties.radiance.add_view(view)
        attached_identifiers.append(view.identifier)
    updated_model_target, persisted_path, receipt = _save_model_with_radiance_asset(
        garden_root=garden_root_path,
        manifest=manifest,
        model_target=resolved_model_target,
        model=model,
        operation="attach_radiance_views_to_model",
        asset_target={"view_targets": view_targets},
    )
    return {
        "target": updated_model_target,
        "model_target": updated_model_target,
        "summary_view": {
            "model_identifier": updated_model_target.get("identifier"),
            "radiance_view_count": len(model.properties.radiance.views),
            "attached_view_identifiers": attached_identifiers,
            "model_path": persisted_path,
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=f"Attached {len(attached_identifiers)} Radiance View target(s) to model.",
        ),
    }


def create_radiance_sensor_grid(
    *,
    identifier: str,
    positions: list[list[float]],
    direction: list[float] | None = None,
    directions: list[list[float]] | None = None,
    display_name: str | None = None,
    room_identifier: str | None = None,
    group_identifier: str | None = None,
    garden_root: str | None = None,
    model_target: dict[str, Any] | None = None,
    attach_to_model: bool = False,
    output_subdir: str = SENSOR_GRID_OUTPUT_SUBDIR,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Radiance SensorGrid and optionally attach it to a model."""
    safe_identifier = slugify_name(identifier)
    sensor_grid = _sensor_grid_from_inputs(
        identifier=safe_identifier,
        positions=positions,
        direction=direction,
        directions=directions,
    )
    if display_name is not None:
        sensor_grid.display_name = display_name
    if room_identifier is not None:
        sensor_grid.room_identifier = room_identifier
    if group_identifier is not None:
        sensor_grid.group_identifier = group_identifier

    return _persist_sensor_grid(
        sensor_grid=sensor_grid,
        garden_root=garden_root,
        model_target=model_target,
        attach_to_model=attach_to_model,
        output_subdir=output_subdir,
        return_object_dict=return_object_dict,
    )


def create_radiance_sensor_grid_from_object(
    *,
    identifier: str,
    object_target: dict[str, Any],
    garden_root: str,
    grid_spacing: float | None = None,
    x_count: int | None = None,
    y_count: int | None = None,
    offset: float = 0.01,
    flip_direction: bool = False,
    display_name: str | None = None,
    group_identifier: str | None = None,
    model_target: dict[str, Any] | None = None,
    attach_to_model: bool = False,
    output_subdir: str = SENSOR_GRID_OUTPUT_SUBDIR,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Radiance SensorGrid by sampling a Honeybee object surface."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    normalized_object_target = normalize_honeybee_object_target(object_target)
    allowed_types = {"face", "aperture", "door", "shade"}
    if normalized_object_target["object_type"] not in allowed_types:
        raise ValueError(
            "object_target must identify a Honeybee face, aperture, door, or shade."
        )
    if (
        normalized_object_target.get("model_identifier")
        != resolved_model_target.get("model_identifier")
    ):
        matching_model_target = next(
            (
                item
                for item in manifest.models
                if item.get("model_identifier")
                == normalized_object_target["model_identifier"]
            ),
            None,
        )
        if matching_model_target is None:
            raise ValueError(
                "object_target references a Honeybee model that is not registered in this Garden."
            )
        resolved_model_target = matching_model_target
    model = load_honeybee_model(garden_root_path, resolved_model_target)
    obj = find_object(model, normalized_object_target)
    sensor_grid = _sensor_grid_from_face3d(
        identifier=slugify_name(identifier),
        geometry=getattr(obj, "geometry", None),
        grid_spacing=grid_spacing,
        x_count=x_count,
        y_count=y_count,
        offset=float(offset),
        flip_direction=flip_direction,
    )
    parent = getattr(obj, "parent", None)
    while parent is not None:
        if isinstance(parent, Room):
            sensor_grid.room_identifier = parent.identifier
            break
        parent = getattr(parent, "parent", None)
    if display_name is not None:
        sensor_grid.display_name = display_name
    if group_identifier is not None:
        sensor_grid.group_identifier = group_identifier
    result = _persist_sensor_grid(
        sensor_grid=sensor_grid,
        garden_root=garden_root,
        model_target=resolved_model_target,
        attach_to_model=attach_to_model,
        output_subdir=output_subdir,
        return_object_dict=return_object_dict,
    )
    source_object = {
        "object_type": normalized_object_target["object_type"],
        "object_identifier": normalized_object_target["object_identifier"],
        "model_identifier": normalized_object_target["model_identifier"],
    }
    result["summary_view"]["source_object"] = source_object
    if isinstance(result.get("target"), dict):
        result["target"]["source_object"] = source_object
        result["sensor_grid_target"] = result["target"]
    result["summary_view"]["grid_generation"] = {
        "method": "object_face3d",
        "grid_spacing": grid_spacing,
        "x_count": x_count,
        "y_count": y_count,
        "offset": offset,
        "flip_direction": flip_direction,
    }
    return result


def create_radiance_view(
    *,
    identifier: str,
    position: list[float] | None = None,
    direction: list[float] | None = None,
    up_vector: list[float] | None = None,
    view_type: str = "v",
    h_size: float = 60,
    v_size: float = 60,
    shift: float | None = None,
    lift: float | None = None,
    display_name: str | None = None,
    room_identifier: str | None = None,
    group_identifier: str | None = None,
    garden_root: str | None = None,
    model_target: dict[str, Any] | None = None,
    attach_to_model: bool = False,
    output_subdir: str = VIEW_OUTPUT_SUBDIR,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Radiance View and optionally attach it to a model."""
    safe_identifier = slugify_name(identifier)
    view = View(
        safe_identifier,
        position=_vector3(position or [0, 0, 0], "position"),
        direction=_vector3(direction or [0, 0, 1], "direction"),
        up_vector=_vector3(up_vector or [0, 1, 0], "up_vector"),
        type=view_type,
        h_size=h_size,
        v_size=v_size,
        shift=shift,
        lift=lift,
    )
    if display_name is not None:
        view.display_name = display_name
    if room_identifier is not None:
        view.room_identifier = room_identifier
    if group_identifier is not None:
        view.group_identifier = group_identifier

    result: dict[str, Any] = {
        "object_dict": view.to_dict(),
        "summary_view": _view_summary(
            view,
            target=None,
            attached_to_model=False,
        ),
        "report": make_report(
            status="ok",
            message=f"Created Radiance View: {safe_identifier}",
        ),
    }
    if garden_root is None:
        return result

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    source = {
        "source_type": "view",
        "view_type": view.type,
        "attached_to_model": attach_to_model,
    }
    target, artifact, artifact_path_abs = _write_artifact(
        garden_root=garden_root_path,
        manifest=manifest,
        identifier=safe_identifier,
        output_subdir=output_subdir,
        extension="vf",
        text=view.to_radiance(),
        artifact_type=VIEW_ARTIFACT_TYPE,
        source=source,
        target_type=VIEW_TARGET_TYPE,
    )
    result.update(
        {
            "target": target,
            "view_target": target,
            "artifact": artifact,
            "persistence_receipt": make_artifact_receipt(
                status="persisted",
                garden_id=manifest.garden_id,
                artifact_type=VIEW_ARTIFACT_TYPE,
                artifact_path=target["path"],
                absolute_path=str(artifact_path_abs),
                source=source,
            ),
        }
    )
    result["summary_view"] = _view_summary(
        view,
        target=target,
        attached_to_model=False,
    )

    if attach_to_model:
        manifest.write(garden_root_path)
        manifest, resolved_model_target = resolve_model_target(
            garden_root_path,
            model_target,
        )
        model = load_honeybee_model(garden_root_path, resolved_model_target)
        model.properties.radiance.add_view(view)
        updated_model_target, persisted_path, model_receipt = _save_model_with_radiance_asset(
            garden_root=garden_root_path,
            manifest=manifest,
            model_target=resolved_model_target,
            model=model,
            operation="create_radiance_view",
            asset_target=target,
        )
        result["model_target"] = updated_model_target
        result["model_persistence_receipt"] = model_receipt
        result["summary_view"]["attached_to_model"] = True
        result["summary_view"]["model_target"] = updated_model_target
        result["summary_view"]["model_path"] = persisted_path
    else:
        manifest.write(garden_root_path)

    if not return_object_dict:
        result.pop("object_dict", None)
    return result


def _coerce_vector3_optional(
    value: list[float] | dict[str, float] | None,
    field_name: str,
) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        try:
            return [float(value["x"]), float(value["y"]), float(value["z"])]
        except KeyError as exc:
            raise ValueError(f"{field_name} dict must include x, y, and z.") from exc
    if len(value) != 3:
        raise ValueError(f"{field_name} must include exactly three numbers.")
    return [float(value[0]), float(value[1]), float(value[2])]


def _room_identifier_from_target(
    room_identifier: str | None,
    room_target: dict[str, Any] | None,
) -> str | None:
    if room_identifier is not None or not isinstance(room_target, dict):
        return room_identifier
    if str(room_target.get("object_type", "")).lower() == "room":
        value = room_target.get("object_identifier") or room_target.get("identifier")
        if isinstance(value, str) and value:
            return value
    return room_identifier


def _positions_from_rectangular_grid(
    *,
    positions: list[list[float]] | None,
    x_dim: float | None,
    y_dim: float | None,
    height: float | None,
    x_count: int | None,
    y_count: int | None,
    grid_spacing: float | None = None,
    origin: list[float] | None = None,
) -> list[list[float]]:
    if positions is not None:
        return positions
    if (
        x_dim is None
        and y_dim is None
        and grid_spacing is not None
        and x_count is not None
        and y_count is not None
    ):
        x_dim = float(grid_spacing) * int(x_count)
        y_dim = float(grid_spacing) * int(y_count)
    if x_dim is not None and y_dim is not None:
        if grid_spacing is not None and grid_spacing > 0:
            x_count = max(1, int(float(x_dim) / float(grid_spacing)))
            y_count = max(1, int(float(y_dim) / float(grid_spacing)))
        x_count = 4 if x_count is None else x_count
        y_count = 4 if y_count is None else y_count
    if x_dim is None or y_dim is None or x_count is None or y_count is None:
        if x_count is not None and y_count is not None:
            x_dim = float(x_count) if x_dim is None else x_dim
            y_dim = float(y_count) if y_dim is None else y_dim
    if x_dim is None or y_dim is None or x_count is None or y_count is None:
        raise ValueError(
            "Provide positions, or provide x_dim, y_dim, x_count, and y_count to create a rectangular workplane grid."
        )
    if x_dim <= 0 or y_dim <= 0:
        raise ValueError("x_dim and y_dim must be greater than zero.")
    if x_count < 1 or y_count < 1:
        raise ValueError("x_count and y_count must be at least 1.")
    origin_values = origin or [0, 0, 0]
    if len(origin_values) != 3:
        raise ValueError("origin must include exactly three numbers when provided.")
    z = float(origin_values[2]) + float(0.8 if height is None else height)
    x_step = float(x_dim) / int(x_count)
    y_step = float(y_dim) / int(y_count)
    return [
        [
            float(origin_values[0]) + (x_index + 0.5) * x_step,
            float(origin_values[1]) + (y_index + 0.5) * y_step,
            z,
        ]
        for y_index in range(int(y_count))
        for x_index in range(int(x_count))
    ]


def _direction_from_target(
    position: list[float] | None,
    target: list[float] | None,
) -> list[float] | None:
    if target is None:
        return None
    origin = position or [0, 0, 0]
    if len(origin) != 3 or len(target) != 3:
        raise ValueError("position and target must both be [x, y, z] vectors.")
    return [float(target[index]) - float(origin[index]) for index in range(3)]


def _normalize_view_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.startswith("vt") and len(normalized) == 3:
        normalized = normalized[-1]
    allowed = {"v", "h", "l", "c", "a", "s"}
    if normalized not in allowed:
        raise ValueError("view_type must be one of v, h, l, c, a, s, or a Radiance vt* token.")
    return normalized


def _coerce_bool_attach(model_target: dict[str, Any] | None, attach_to_model: bool) -> bool:
    return True if model_target is not None and not attach_to_model else attach_to_model


def _resolve_rooms_from_model(
    model: Any,
    *,
    room_identifier: str | None = None,
    room_target: dict[str, Any] | None = None,
) -> list[Room]:
    resolved_id = _room_identifier_from_target(room_identifier, room_target)
    if resolved_id:
        return list(model.rooms_by_identifier([resolved_id]))
    rooms = list(model.rooms)
    if not rooms:
        raise ValueError("Honeybee model does not contain any Rooms.")
    return rooms


def _persist_grid_batch(
    *,
    grids: list[SensorGrid],
    garden_root: str | None,
    model_target: dict[str, Any] | None,
    attach_to_model: bool,
    output_subdir: str,
    return_object_dict: bool,
    operation_label: str,
) -> dict[str, Any]:
    if not grids:
        raise ValueError(f"{operation_label} produced no SensorGrid objects.")
    if len(grids) == 1:
        res = _persist_sensor_grid(
            sensor_grid=grids[0],
            garden_root=garden_root,
            model_target=model_target,
            attach_to_model=attach_to_model,
            output_subdir=output_subdir,
            return_object_dict=return_object_dict,
        )
        if "target" in res:
            res["targets"] = [res["target"]]
        return res

    # Multi-grid persistence + single model save
    per_grid_targets: list[dict[str, Any]] = []
    per_grid_summaries: list[dict[str, Any]] = []
    per_grid_dicts: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    for grid in grids:
        single = _persist_sensor_grid(
            sensor_grid=grid,
            garden_root=garden_root,
            model_target=model_target,
            attach_to_model=False,
            output_subdir=output_subdir,
            return_object_dict=return_object_dict,
        )
        if "target" in single:
            per_grid_targets.append(single["target"])
        per_grid_summaries.append(single["summary_view"])
        if "object_dict" in single:
            per_grid_dicts.append(single["object_dict"])
        if "persistence_receipt" in single:
            receipts.append(single["persistence_receipt"])

    result: dict[str, Any] = {
        "targets": per_grid_targets,
        "target": per_grid_targets[0] if per_grid_targets else None,
        "sensor_grid_target": per_grid_targets[0] if per_grid_targets else None,
        "sensor_grid_targets": per_grid_targets,
        "summary_view": {
            "operation": operation_label,
            "grid_count": len(grids),
            "grid_identifiers": [grid.identifier for grid in grids],
            "total_sensor_count": sum(len(grid.sensors) for grid in grids),
            "grids": per_grid_summaries,
            "attached_to_model": False,
        },
        "report": make_report(
            status="ok",
            message=f"Created {len(grids)} Radiance SensorGrid(s) via {operation_label}.",
        ),
    }
    if return_object_dict:
        result["object_dicts"] = per_grid_dicts
    if receipts:
        result["persistence_receipt"] = receipts[0]

    if attach_to_model and garden_root is not None:
        garden_root_path = Path(garden_root).expanduser().resolve()
        manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
        model = load_honeybee_model(garden_root_path, resolved_model_target)
        for grid in grids:
            model.properties.radiance.add_sensor_grid(grid)
        updated_model_target, persisted_path, model_receipt = _save_model_with_radiance_asset(
            garden_root=garden_root_path,
            manifest=manifest,
            model_target=resolved_model_target,
            model=model,
            operation=operation_label,
            asset_target={"sensor_grid_targets": per_grid_targets},
        )
        result["model_target"] = updated_model_target
        result["model_persistence_receipt"] = model_receipt
        result["summary_view"]["attached_to_model"] = True
        result["summary_view"]["model_target"] = updated_model_target
        result["summary_view"]["model_path"] = persisted_path
    return result


def remove_radiance_scene_assets(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    target_kind: str = "all",
    grid_identifiers: list[str] | str | None = None,
    view_identifiers: list[str] | str | None = None,
    filter_pattern: str | None = None,
    remove_all: bool = False,
) -> dict[str, Any]:
    """Remove SensorGrids and/or Views from a Honeybee model."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_honeybee_model(garden_root_path, resolved_model_target)
    kind = target_kind.strip().lower().replace("-", "_")
    if kind not in {"sensor_grid", "view", "all"}:
        raise ValueError("target_kind must be sensor_grid, view, or all.")

    def _patterns(raw: list[str] | str | None) -> list[str]:
        if raw is None:
            return [filter_pattern] if filter_pattern else []
        if isinstance(raw, str):
            return [raw]
        return [str(x) for x in raw]

    removed_grids: list[str] = []
    removed_views: list[str] = []
    if kind in {"sensor_grid", "all"}:
        grid_pats = _patterns(grid_identifiers)
        if remove_all or grid_pats:
            kept_grids = []
            for grid in list(model.properties.radiance.sensor_grids):
                if remove_all or any(fnmatch(grid.identifier, pat) for pat in grid_pats):
                    removed_grids.append(grid.identifier)
                else:
                    kept_grids.append(grid)
            model.properties.radiance._sensor_grids = kept_grids
    if kind in {"view", "all"}:
        view_pats = _patterns(view_identifiers)
        if remove_all or view_pats:
            kept_views = []
            for view in list(model.properties.radiance.views):
                if remove_all or any(fnmatch(view.identifier, pat) for pat in view_pats):
                    removed_views.append(view.identifier)
                else:
                    kept_views.append(view)
            model.properties.radiance._views = kept_views

    if not removed_grids and not removed_views:
        raise ValueError("No SensorGrids or Views matched the removal criteria.")

    updated_model_target, persisted_path, receipt = _save_model_with_radiance_asset(
        garden_root=garden_root_path,
        manifest=manifest,
        model_target=resolved_model_target,
        model=model,
        operation="remove_radiance_scene_assets",
        asset_target={"removed_grids": removed_grids, "removed_views": removed_views},
    )
    return {
        "target": updated_model_target,
        "model_target": updated_model_target,
        "updated_model_target": updated_model_target,
        "summary_view": {
            "operation": "remove",
            "model_target": updated_model_target,
            "model_path": persisted_path,
            "removed_sensor_grids": removed_grids,
            "removed_views": removed_views,
            "remaining_sensor_grid_count": len(model.properties.radiance.sensor_grids),
            "remaining_view_count": len(model.properties.radiance.views),
        },
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=(
                f"Removed {len(removed_grids)} sensor grid(s) and "
                f"{len(removed_views)} view(s) from Honeybee model."
            ),
        ),
    }


def merge_radiance_sensor_grids(
    *,
    garden_root: str,
    identifier: str | None = None,
    sensor_grid_targets: list[dict[str, Any]] | None = None,
    model_target: dict[str, Any] | None = None,
    grid_identifiers: list[str] | str | None = None,
    filter_pattern: str = "*",
    replace_existing: bool = True,
    attach_to_model: bool = True,
    group_identifier: str | None = None,
    output_subdir: str = SENSOR_GRID_OUTPUT_SUBDIR,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Merge multiple SensorGrid targets or model SensorGrids into one SensorGrid."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    grids_to_merge: list[SensorGrid] = []
    source_from_model = False
    model = None
    manifest = None
    resolved_model_target = None

    if sensor_grid_targets:
        grids_to_merge = [
            _sensor_grid_from_target(garden_root_path, item) for item in sensor_grid_targets
        ]
    else:
        source_from_model = True
        manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
        model = load_honeybee_model(garden_root_path, resolved_model_target)
        pats = (
            [grid_identifiers]
            if isinstance(grid_identifiers, str)
            else ([str(x) for x in grid_identifiers] if grid_identifiers else [filter_pattern])
        )
        grids_to_merge = [
            grid
            for grid in model.properties.radiance.sensor_grids
            if any(fnmatch(grid.identifier, pat) for pat in pats)
        ]

    if len(grids_to_merge) < 2:
        raise ValueError("merge requires at least two matching SensorGrids.")

    merged = SensorGrid.from_merged_grids(grids_to_merge)
    merged.identifier = slugify_name(identifier or f"{grids_to_merge[0].identifier}_merged")
    if group_identifier is not None:
        merged.group_identifier = group_identifier

    if source_from_model and replace_existing and model is not None and resolved_model_target is not None:
        merged_ids = {grid.identifier for grid in grids_to_merge}
        model.properties.radiance._sensor_grids = [
            grid
            for grid in model.properties.radiance.sensor_grids
            if grid.identifier not in merged_ids
        ]
        model.properties.radiance.add_sensor_grid(merged)
        assert manifest is not None
        updated_model_target, persisted_path, model_receipt = _save_model_with_radiance_asset(
            garden_root=garden_root_path,
            manifest=manifest,
            model_target=resolved_model_target,
            model=model,
            operation="merge_radiance_sensor_grids",
            asset_target={"merged_into": merged.identifier, "source_grids": sorted(merged_ids)},
        )
        res = _persist_sensor_grid(
            sensor_grid=merged,
            garden_root=garden_root,
            model_target=updated_model_target,
            attach_to_model=False,
            output_subdir=output_subdir,
            return_object_dict=return_object_dict,
        )
        res["model_target"] = updated_model_target
        res["model_persistence_receipt"] = model_receipt
        res["summary_view"]["attached_to_model"] = True
        res["summary_view"]["model_target"] = updated_model_target
        res["summary_view"]["model_path"] = persisted_path
        res["summary_view"]["merged_source_identifiers"] = [g.identifier for g in grids_to_merge]
        return res

    res = _persist_sensor_grid(
        sensor_grid=merged,
        garden_root=garden_root,
        model_target=model_target,
        attach_to_model=attach_to_model,
        output_subdir=output_subdir,
        return_object_dict=return_object_dict,
    )
    res["summary_view"]["merged_source_identifiers"] = [g.identifier for g in grids_to_merge]
    return res


def split_radiance_sensor_grid(
    *,
    garden_root: str,
    identifier: str | None = None,
    sensor_grid_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
    split_count: int = 2,
    max_sensors: int | None = None,
    replace_existing: bool = True,
    attach_to_model: bool = True,
    output_subdir: str = SENSOR_GRID_OUTPUT_SUBDIR,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Split a SensorGrid into smaller sub-grids by split_count or max_sensors."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    model = None
    manifest = None
    resolved_model_target = None
    source_grid: SensorGrid | None = None

    if sensor_grid_target is not None:
        source_grid = _sensor_grid_from_target(garden_root_path, sensor_grid_target)
    else:
        manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
        model = load_honeybee_model(garden_root_path, resolved_model_target)
        grids = list(model.properties.radiance.sensor_grids)
        if identifier:
            source_grid = next((g for g in grids if g.identifier == identifier), None)
        elif len(grids) == 1:
            source_grid = grids[0]
        elif grids:
            source_grid = grids[0]
    if source_grid is None:
        raise ValueError("Could not find a SensorGrid to split.")

    sensors = list(source_grid.sensors)
    if len(sensors) < 2:
        raise ValueError("SensorGrid must contain at least 2 sensors to split.")

    if max_sensors is not None:
        chunk_size = max(1, int(max_sensors))
    else:
        n_chunks = max(2, int(split_count))
        chunk_size = max(1, (len(sensors) + n_chunks - 1) // n_chunks)

    sub_grids: list[SensorGrid] = []
    base_id = slugify_name(identifier or source_grid.identifier)
    for idx, start in enumerate(range(0, len(sensors), chunk_size), 1):
        chunk = [s.duplicate() for s in sensors[start : start + chunk_size]]
        sub_grid = SensorGrid(f"{base_id}_{idx}", chunk)
        if source_grid.room_identifier:
            sub_grid.room_identifier = source_grid.room_identifier
        if source_grid.group_identifier:
            sub_grid.group_identifier = source_grid.group_identifier
        sub_grids.append(sub_grid)

    if model is not None and resolved_model_target is not None and replace_existing:
        model.properties.radiance._sensor_grids = [
            g for g in model.properties.radiance.sensor_grids if g.identifier != source_grid.identifier
        ]
        for sub_grid in sub_grids:
            model.properties.radiance.add_sensor_grid(sub_grid)
        assert manifest is not None
        updated_model_target, persisted_path, model_receipt = _save_model_with_radiance_asset(
            garden_root=garden_root_path,
            manifest=manifest,
            model_target=resolved_model_target,
            model=model,
            operation="split_radiance_sensor_grid",
            asset_target={"source_grid": source_grid.identifier, "split_grids": [g.identifier for g in sub_grids]},
        )
        res = _persist_grid_batch(
            grids=sub_grids,
            garden_root=garden_root,
            model_target=updated_model_target,
            attach_to_model=False,
            output_subdir=output_subdir,
            return_object_dict=return_object_dict,
            operation_label="split",
        )
        res["model_target"] = updated_model_target
        res["model_persistence_receipt"] = model_receipt
        res["summary_view"]["attached_to_model"] = True
        res["summary_view"]["model_target"] = updated_model_target
        res["summary_view"]["model_path"] = persisted_path
        res["summary_view"]["source_grid_identifier"] = source_grid.identifier
        return res

    res = _persist_grid_batch(
        grids=sub_grids,
        garden_root=garden_root,
        model_target=model_target,
        attach_to_model=attach_to_model,
        output_subdir=output_subdir,
        return_object_dict=return_object_dict,
        operation_label="split",
    )
    res["summary_view"]["source_grid_identifier"] = source_grid.identifier
    return res


def create_radiance_scene_asset(
    *,
    asset_type: str | None = None,
    action: str = "create",
    identifier: str | None = None,
    positions: list[list[float]] | None = None,
    direction: list[float] | dict[str, float] | None = None,
    directions: list[list[float]] | None = None,
    x_dim: float | None = None,
    y_dim: float | None = None,
    height: float | None = None,
    x_count: int | None = None,
    y_count: int | None = None,
    grid_spacing: float | None = None,
    origin: list[float] | dict[str, float] | None = None,
    object_target: dict[str, Any] | None = None,
    offset: float | None = None,
    flip_direction: bool = False,
    position: list[float] | dict[str, float] | None = None,
    target: list[float] | dict[str, float] | None = None,
    up_vector: list[float] | dict[str, float] | None = None,
    view_type: str = "v",
    h_size: float = 60,
    v_size: float = 60,
    shift: float | None = None,
    lift: float | None = None,
    display_name: str | None = None,
    room_identifier: str | None = None,
    room_target: dict[str, Any] | None = None,
    group_identifier: str | None = None,
    wall_offset: float = 0.0,
    remove_out: bool = False,
    dir_count: int = 8,
    start_vector: list[float] | dict[str, float] | None = None,
    mesh_radius: float | None = None,
    face_type: str = "Wall",
    punched_geometry: bool = False,
    aperture_type: str = "All",
    target_kind: str = "all",
    grid_identifiers: list[str] | str | None = None,
    view_identifiers: list[str] | str | None = None,
    filter_pattern: str = "*",
    remove_all: bool = False,
    sensor_grid_target: dict[str, Any] | None = None,
    sensor_grid_targets: list[dict[str, Any]] | None = None,
    split_count: int = 2,
    max_sensors: int | None = None,
    replace_existing: bool = True,
    garden_root: str | None = None,
    model_target: dict[str, Any] | None = None,
    attach_to_model: bool = False,
    output_subdir: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create, generate from Room, merge, split, or remove Radiance SensorGrids and Views."""
    normalized_action = str(action or "create").strip().lower().replace("-", "_").replace(" ", "_")
    normalized_type = (
        str(asset_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    )
    if normalized_type in {"remove", "merge", "split"}:
        normalized_action = normalized_type

    if normalized_action == "remove":
        if not garden_root:
            raise ValueError("garden_root is required when action='remove'.")
        return remove_radiance_scene_assets(
            garden_root=garden_root,
            model_target=model_target,
            target_kind=target_kind if target_kind != "all" or not normalized_type else (
                normalized_type if normalized_type in {"sensor_grid", "view"} else "all"
            ),
            grid_identifiers=grid_identifiers,
            view_identifiers=view_identifiers,
            filter_pattern=None if filter_pattern == "*" else filter_pattern,
            remove_all=remove_all,
        )
    if normalized_action == "merge":
        if not garden_root:
            raise ValueError("garden_root is required when action='merge'.")
        return merge_radiance_sensor_grids(
            garden_root=garden_root,
            identifier=identifier,
            sensor_grid_targets=sensor_grid_targets,
            model_target=model_target,
            grid_identifiers=grid_identifiers,
            filter_pattern=filter_pattern,
            replace_existing=replace_existing,
            attach_to_model=True if attach_to_model or model_target is not None else False,
            group_identifier=group_identifier,
            output_subdir=output_subdir or SENSOR_GRID_OUTPUT_SUBDIR,
            return_object_dict=return_object_dict,
        )
    if normalized_action == "split":
        if not garden_root:
            raise ValueError("garden_root is required when action='split'.")
        return split_radiance_sensor_grid(
            garden_root=garden_root,
            identifier=identifier,
            sensor_grid_target=sensor_grid_target,
            model_target=model_target,
            split_count=split_count,
            max_sensors=max_sensors,
            replace_existing=replace_existing,
            attach_to_model=True if attach_to_model or model_target is not None else False,
            output_subdir=output_subdir or SENSOR_GRID_OUTPUT_SUBDIR,
            return_object_dict=return_object_dict,
        )

    if normalized_type in {"room_floor_grid", "room_radial_grid", "exterior_face_grid", "exterior_aperture_grid", "room_view"}:
        if not garden_root:
            raise ValueError(f"garden_root is required when asset_type='{normalized_type}'.")
        garden_root_path = Path(garden_root).expanduser().resolve()
        attach = _coerce_bool_attach(model_target, attach_to_model)

        if normalized_type == "room_radial_grid" and (positions is not None or sensor_grid_target is not None or (x_dim is not None and y_dim is not None and model_target is None and room_identifier is None and room_target is None)):
            if sensor_grid_target is not None:
                base_grid = _sensor_grid_from_target(garden_root_path, sensor_grid_target)
            else:
                resolved_origin = _coerce_vector3_optional(origin, "origin")
                resolved_positions = _positions_from_rectangular_grid(
                    positions=positions,
                    x_dim=x_dim,
                    y_dim=y_dim,
                    height=height,
                    x_count=x_count,
                    y_count=y_count,
                    grid_spacing=grid_spacing,
                    origin=resolved_origin,
                )
                base_grid = _sensor_grid_from_inputs(
                    identifier=slugify_name(identifier or "radial_grid"),
                    positions=resolved_positions,
                    direction=[0, 0, 1],
                    directions=None,
                )
            sv = _coerce_vector3_optional(start_vector, "start_vector") or [0.0, -1.0, 0.0]
            radial_grid = base_grid.to_radial_grid(
                dir_count=int(dir_count),
                start_vector=Vector3D(*sv),
                mesh_radius=0 if mesh_radius is None else float(mesh_radius),
            )
            if identifier:
                radial_grid.identifier = slugify_name(identifier)
            if display_name is not None:
                radial_grid.display_name = display_name
            if group_identifier is not None:
                radial_grid.group_identifier = group_identifier
            return _persist_sensor_grid(
                sensor_grid=radial_grid,
                garden_root=garden_root,
                model_target=model_target,
                attach_to_model=attach,
                output_subdir=output_subdir or SENSOR_GRID_OUTPUT_SUBDIR,
                return_object_dict=return_object_dict,
            )

        manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
        model = load_honeybee_model(garden_root_path, resolved_model_target)
        rooms = _resolve_rooms_from_model(
            model,
            room_identifier=room_identifier,
            room_target=room_target,
        )

        if normalized_type == "room_view":
            room = rooms[0]
            resolved_dir = _coerce_vector3_optional(direction, "direction") or [0.0, 1.0, 0.0]
            resolved_up = _coerce_vector3_optional(up_vector, "up_vector") or [0.0, 0.0, 1.0]
            view_obj = room.properties.radiance.generate_view(
                direction=Vector3D(*resolved_dir),
                up_vector=Vector3D(*resolved_up),
                type=_normalize_view_type(view_type),
                h_size=h_size,
                v_size=v_size,
                shift=shift,
                lift=lift,
            )
            return create_radiance_view(
                identifier=identifier or view_obj.identifier,
                position=[float(v) for v in view_obj.position],
                direction=[float(v) for v in view_obj.direction],
                up_vector=[float(v) for v in view_obj.up_vector],
                view_type=view_obj.type,
                h_size=view_obj.h_size,
                v_size=view_obj.v_size,
                shift=view_obj.shift,
                lift=view_obj.lift,
                display_name=display_name or view_obj.display_name,
                room_identifier=room.identifier,
                group_identifier=group_identifier,
                garden_root=garden_root,
                model_target=resolved_model_target,
                attach_to_model=attach,
                output_subdir=output_subdir or VIEW_OUTPUT_SUBDIR,
                return_object_dict=return_object_dict,
            )

        grids: list[SensorGrid] = []
        cell_x = float(grid_spacing or x_dim or 1.0)
        cell_y = float(y_dim) if y_dim is not None else None
        for room in rooms:
            generated: SensorGrid | None = None
            if normalized_type == "room_floor_grid":
                generated = room.properties.radiance.generate_sensor_grid(
                    x_dim=cell_x,
                    y_dim=cell_y,
                    offset=0.8 if offset is None else float(offset),
                    remove_out=bool(remove_out),
                    wall_offset=float(wall_offset),
                )
            elif normalized_type == "room_radial_grid":
                sv = _coerce_vector3_optional(start_vector, "start_vector") or [0.0, -1.0, 0.0]
                generated = room.properties.radiance.generate_sensor_grid_radial(
                    x_dim=cell_x,
                    y_dim=cell_y,
                    offset=1.2 if offset is None else float(offset),
                    remove_out=bool(remove_out),
                    wall_offset=float(wall_offset),
                    dir_count=int(dir_count),
                    start_vector=Vector3D(*sv),
                    mesh_radius=mesh_radius,
                )
            elif normalized_type == "exterior_face_grid":
                generated = room.properties.radiance.generate_exterior_face_sensor_grid(
                    dimension=cell_x,
                    offset=0.1 if offset is None else float(offset),
                    face_type=face_type,
                    punched_geometry=bool(punched_geometry),
                )
            elif normalized_type == "exterior_aperture_grid":
                generated = room.properties.radiance.generate_exterior_aperture_sensor_grid(
                    dimension=cell_x,
                    offset=0.1 if offset is None else float(offset),
                    aperture_type=aperture_type,
                )
            if generated is None:
                continue
            if identifier:
                generated.identifier = (
                    slugify_name(identifier)
                    if len(rooms) == 1
                    else slugify_name(f"{identifier}_{room.identifier}")
                )
            if display_name is not None:
                generated.display_name = display_name
            if group_identifier is not None:
                generated.group_identifier = group_identifier
            grids.append(generated)

        if not grids:
            raise ValueError(
                f"No geometry matched '{normalized_type}' on the selected model room(s)."
            )
        return _persist_grid_batch(
            grids=grids,
            garden_root=garden_root,
            model_target=resolved_model_target,
            attach_to_model=attach,
            output_subdir=output_subdir or SENSOR_GRID_OUTPUT_SUBDIR,
            return_object_dict=return_object_dict,
            operation_label=normalized_type,
        )

    if normalized_type == "sensor_grid":
        eff_offset = 0.01 if offset is None else float(offset)
        if object_target is not None:
            if not garden_root:
                raise ValueError(
                    "garden_root is required when creating a sensor_grid from object_target."
                )
            return create_radiance_sensor_grid_from_object(
                identifier=identifier or "object_sensor_grid",
                object_target=object_target,
                garden_root=garden_root,
                grid_spacing=grid_spacing,
                x_count=x_count,
                y_count=y_count,
                offset=eff_offset,
                flip_direction=flip_direction,
                display_name=display_name,
                group_identifier=group_identifier,
                model_target=model_target,
                attach_to_model=attach_to_model,
                output_subdir=output_subdir or SENSOR_GRID_OUTPUT_SUBDIR,
                return_object_dict=return_object_dict,
            )
        if model_target is not None and not attach_to_model:
            attach_to_model = True
        resolved_origin = _coerce_vector3_optional(origin, "origin")
        resolved_direction = _coerce_vector3_optional(direction, "direction")
        resolved_positions = _positions_from_rectangular_grid(
            positions=positions,
            x_dim=x_dim,
            y_dim=y_dim,
            height=height,
            x_count=x_count,
            y_count=y_count,
            grid_spacing=grid_spacing,
            origin=resolved_origin,
        )
        resolved_room_id = _room_identifier_from_target(room_identifier, room_target)
        return create_radiance_sensor_grid(
            identifier=identifier or "sensor_grid",
            positions=resolved_positions,
            direction=resolved_direction,
            directions=directions,
            display_name=display_name,
            room_identifier=resolved_room_id,
            group_identifier=group_identifier,
            garden_root=garden_root,
            model_target=model_target,
            attach_to_model=attach_to_model,
            output_subdir=output_subdir or SENSOR_GRID_OUTPUT_SUBDIR,
            return_object_dict=return_object_dict,
        )
    if normalized_type == "view":
        if model_target is not None and not attach_to_model:
            attach_to_model = True
        resolved_position = _coerce_vector3_optional(position, "position")
        resolved_direction = _coerce_vector3_optional(direction, "direction")
        resolved_target = _coerce_vector3_optional(target, "target")
        resolved_up_vector = _coerce_vector3_optional(up_vector, "up_vector")
        if resolved_direction is None:
            resolved_direction = _direction_from_target(resolved_position, resolved_target)
        resolved_view_type = _normalize_view_type(view_type)
        resolved_room_id = _room_identifier_from_target(room_identifier, room_target)
        return create_radiance_view(
            identifier=identifier or "view",
            position=resolved_position,
            direction=resolved_direction,
            up_vector=resolved_up_vector,
            view_type=resolved_view_type,
            h_size=h_size,
            v_size=v_size,
            shift=shift,
            lift=lift,
            display_name=display_name,
            room_identifier=resolved_room_id,
            group_identifier=group_identifier,
            garden_root=garden_root,
            model_target=model_target,
            attach_to_model=attach_to_model,
            output_subdir=output_subdir or VIEW_OUTPUT_SUBDIR,
            return_object_dict=return_object_dict,
        )
    raise ValueError(
        "asset_type must be one of: sensor_grid, view, room_floor_grid, "
        "room_radial_grid, exterior_face_grid, exterior_aperture_grid, room_view "
        "(or use action='remove' | 'merge' | 'split')."
    )
