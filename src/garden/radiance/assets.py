"""Honeybee Radiance sensor grid and view foundation services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from honeybee_radiance.sensorgrid import SensorGrid
from honeybee_radiance.view import View

from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target,
    save_honeybee_model,
    with_honeybee_model_write_lock,
)
from garden.honeybee_core.locate import find_object
from garden.honeybee_core.targets import normalize_honeybee_object_target
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from ladybug_tools_mcp.contracts.receipts import (
    make_artifact_receipt,
    make_persistence_receipt,
)
from ladybug_tools_mcp.contracts.report import make_report

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
    manifest.artifacts = [
        item
        for item in manifest.artifacts
        if not (
            item.get("artifact_type") == artifact_type
            and item.get("path") == path
        )
    ]
    manifest.artifacts.append(record)
    return record


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


def _add(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


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


@with_honeybee_model_write_lock
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


@with_honeybee_model_write_lock
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


@with_honeybee_model_write_lock
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


@with_honeybee_model_write_lock
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


@with_honeybee_model_write_lock
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
