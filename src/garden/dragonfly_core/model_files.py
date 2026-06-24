"""Dragonfly model file import/export services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dragonfly.model import Model
from honeybee.typing import clean_string
from ladybug.location import Location
from ladybug_geometry.geometry2d.pointvector import Point2D

from garden.dragonfly_core.model_io import (
    load_dragonfly_model,
    resolve_model_target,
    save_dragonfly_model,
)
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative
from ladybug_tools_mcp.contracts.receipts import (
    make_artifact_receipt,
    make_persistence_receipt,
)
from ladybug_tools_mcp.contracts.report import make_report


DRAGONFLY_MODEL_FILE_ARTIFACT_TYPE = "dragonfly_model_file"
MODEL_FILE_ARTIFACT_DIR = Path("artifacts") / "dragonfly" / "model_files"


def _garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def _resolve_garden_file(garden_root: Path, file_path: str) -> Path:
    resolved = (garden_root / file_path).resolve()
    resolved.relative_to(garden_root)
    if not resolved.is_file():
        raise ValueError(f"Dragonfly model file was not found: {file_path}")
    return resolved


def _validate_model_target_path(garden_root: Path, model_target: dict[str, Any]) -> None:
    path_value = model_target.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("Dragonfly model target requires a Garden-relative path.")
    resolved = (garden_root / path_value).resolve()
    try:
        resolved.relative_to(garden_root)
    except ValueError as exc:
        raise ValueError(
            "Dragonfly model target path must be a Garden-relative path."
        ) from exc


def _normalize_file_type(file_type: str) -> str:
    normalized = file_type.strip().lower()
    if normalized not in {"dfjson", "geojson"}:
        raise ValueError("file_type must be dfjson or geojson.")
    return normalized


def _location_from_value(value: Location | dict[str, Any] | None) -> Location:
    if isinstance(value, Location):
        return value
    if value is None:
        return Location("Unknown", latitude=0, longitude=0)
    return Location(
        city=str(value.get("city") or "Unknown"),
        state=value.get("state"),
        country=value.get("country"),
        latitude=float(value.get("latitude") or 0),
        longitude=float(value.get("longitude") or 0),
        time_zone=float(value.get("time_zone") or 0),
        elevation=float(value.get("elevation") or 0),
    )


def _point_from_value(value: Point2D | list[float] | tuple[float, ...] | None) -> Point2D:
    if isinstance(value, Point2D):
        return value
    if value is None:
        return Point2D(0, 0)
    if len(value) < 2:
        raise ValueError("point must include x and y values.")
    return Point2D(float(value[0]), float(value[1]))


def _artifact_target(
    *,
    manifest: GardenManifest,
    name: str,
    path: str,
    file_type: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    target = {
        "target_type": "artifact",
        "garden_id": manifest.garden_id,
        "domain": "dragonfly",
        "artifact_type": DRAGONFLY_MODEL_FILE_ARTIFACT_TYPE,
        "file_type": file_type,
        "name": name,
        "path": path,
        "source": source,
        "created_at": utc_now_iso(),
    }
    manifest.artifacts = [
        item
        for item in manifest.artifacts
        if not (
            item.get("artifact_type") == DRAGONFLY_MODEL_FILE_ARTIFACT_TYPE
            and item.get("path") == path
        )
    ]
    manifest.artifacts.append(target)
    return target


def _flatten_geojson_output(output_path: Path, artifact_dir: Path, stem: str) -> Path:
    target_path = artifact_dir / f"{stem}.geojson"
    if output_path.resolve() == target_path.resolve():
        return output_path
    output_path.replace(target_path)
    parent = output_path.parent
    try:
        parent.rmdir()
    except OSError:
        pass
    return target_path


def import_dragonfly_model_file(
    *,
    garden_root: str,
    file_path: str,
    file_type: str,
    identifier: str | None = None,
    set_base: bool = True,
    include_body: bool = False,
    location: Location | dict[str, Any] | None = None,
    point: Point2D | list[float] | tuple[float, ...] | None = None,
    all_polygons_to_buildings: bool = False,
    existing_to_context: bool = False,
    units: str = "Meters",
    tolerance: float | None = None,
    angle_tolerance: float = 1.0,
) -> dict[str, Any]:
    """Import a Garden-local DFJSON or geoJSON file as a Dragonfly model target."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    source_path = _resolve_garden_file(garden_root_path, file_path)
    normalized_type = _normalize_file_type(file_type)

    if normalized_type == "dfjson":
        model = Model.from_dfjson(str(source_path), cleanup_irrational=False)
    else:
        model = Model.from_geojson(
            str(source_path),
            location=_location_from_value(location),
            point=_point_from_value(point),
            all_polygons_to_buildings=all_polygons_to_buildings,
            existing_to_context=existing_to_context,
            units=units,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
        )

    if identifier:
        model.identifier = clean_string(identifier, "dragonfly model identifier")
        model.display_name = identifier

    model_target, persisted_path = save_dragonfly_model(
        garden_root_path,
        manifest,
        model,
        name=model.identifier,
        set_base=set_base,
    )
    result: dict[str, Any] = {
        "target": model_target,
        "model_target": model_target,
        "summary_view": {
            "source_file_type": normalized_type,
            "source_path": to_posix_relative(source_path, garden_root_path),
            "model_identifier": model.identifier,
            "building_count": len(model.buildings),
            "context_shade_count": len(model.context_shades),
            "base_dragonfly_model_changed": bool(set_base),
        },
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            base_dragonfly_model_changed=bool(set_base),
            model_target=model_target,
            persisted_path=persisted_path,
            change_summary={
                "operation": "import_dragonfly_model_file",
                "source_path": to_posix_relative(source_path, garden_root_path),
                "source_file_type": normalized_type,
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Imported Dragonfly {normalized_type} model.",
        ),
    }
    if include_body:
        result["model_body"] = model.to_dict()
    return result


def export_dragonfly_model_file(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    file_type: str,
    artifact_name: str | None = None,
    include_body: bool = False,
    location: Location | dict[str, Any] | None = None,
    point: Point2D | list[float] | tuple[float, ...] | None = None,
    tolerance: float | None = None,
) -> dict[str, Any]:
    """Export a Garden Dragonfly model as a Garden file artifact."""
    garden_root_path = _garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    _validate_model_target_path(garden_root_path, resolved_model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    normalized_type = _normalize_file_type(file_type)
    if normalized_type == "geojson" and (location is None or point is None):
        raise ValueError("geojson export requires explicit location and point inputs.")
    stem = slugify_name(artifact_name or model.identifier)
    artifact_dir = (garden_root_path / MODEL_FILE_ARTIFACT_DIR).resolve()
    artifact_dir.relative_to(garden_root_path)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    if normalized_type == "dfjson":
        model.to_dfjson(name=stem, folder=str(artifact_dir), indent=2)
        output_path = artifact_dir / f"{stem}.dfjson"
    else:
        sdk_output = Path(
            model.to_geojson(
                _location_from_value(location),
                point=_point_from_value(point),
                folder=str(artifact_dir),
                tolerance=tolerance,
            )
        ).resolve()
        output_path = _flatten_geojson_output(sdk_output, artifact_dir, stem)

    artifact_path = to_posix_relative(output_path, garden_root_path)
    source = {
        "operation": "export_dragonfly_model_file",
        "model_target": resolved_model_target,
        "model_identifier": model.identifier,
        "file_type": normalized_type,
    }
    target = _artifact_target(
        manifest=manifest,
        name=stem,
        path=artifact_path,
        file_type=normalized_type,
        source=source,
    )
    manifest.write(garden_root_path)

    result: dict[str, Any] = {
        "target": target,
        "artifact_target": target,
        "model_target": resolved_model_target,
        "summary_view": {
            "artifact_target": target,
            "source_model_target": resolved_model_target,
            "file_type": normalized_type,
            "body_returned": False,
        },
        "persistence_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=DRAGONFLY_MODEL_FILE_ARTIFACT_TYPE,
            artifact_path=artifact_path,
            absolute_path=str(output_path),
            source=source,
        ),
        "report": make_report(
            status="ok",
            message=f"Exported Dragonfly model as {normalized_type}.",
        ),
    }
    if include_body:
        result["file_body"] = json.loads(output_path.read_text(encoding="utf-8"))
        result["summary_view"]["body_returned"] = True
    return result
