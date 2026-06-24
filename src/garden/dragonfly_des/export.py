"""Dragonfly Model to URBANopt / DES artifact export services."""

from __future__ import annotations

from hashlib import sha1
from pathlib import Path
from typing import Any
from uuid import uuid4

import dragonfly_energy._extend_dragonfly  # noqa: F401
from dragonfly_energy.writer import model_to_des as sdk_model_to_des
from dragonfly_energy.writer import model_to_urbanopt as sdk_model_to_urbanopt
from ladybug.location import Location
from ladybug_geometry.geometry2d.pointvector import Point2D

from garden.dragonfly_core.model_io import load_dragonfly_model, resolve_model_target
from garden.manifest import GardenManifest
from garden.paths import slugify_name, to_posix_relative
from ladybug_tools_mcp.contracts.receipts import make_artifact_receipt
from ladybug_tools_mcp.contracts.report import make_report

from .artifacts import (
    DES_EXPORT_BUNDLE_ARTIFACT_TYPE,
    DES_FEATURE_GEOJSON_ARTIFACT_TYPE,
    DES_HONEYBEE_HBJSON_ARTIFACT_TYPE,
    DES_SCENARIO_CSV_ARTIFACT_TYPE,
    DES_SYSTEM_PARAMETER_JSON_ARTIFACT_TYPE,
    artifact_target_for_path,
    register_des_artifacts,
)
from .serialization import load_des_object

DES_EXPORTS_DIR = Path("")
MAX_EXPORT_ID_LENGTH = 32


def export_urbanopt_model(
    *,
    garden_root: str,
    location: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    des_loop_target: dict[str, Any] | None = None,
    point: list[float] | None = None,
    folder_name: str | None = None,
    shade_distance: float | None = None,
    use_multiplier: bool = True,
    exclude_plenums: bool = False,
    solve_ceiling_adjacencies: bool = False,
    merge_method: str = "None",
    tolerance: float | None = None,
) -> dict[str, Any]:
    """Export a Dragonfly Model to URBANopt feature GeoJSON and HBJSON artifacts."""
    garden_root_path = _garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    des_loop = (
        load_des_object(garden_root=garden_root_path, target=des_loop_target)
        if des_loop_target
        else None
    )
    export_id = _export_id(folder_name, getattr(model, "identifier", "dragonfly"), "urbanopt")
    export_dir = garden_root_path / DES_EXPORTS_DIR / export_id
    export_dir.mkdir(parents=True, exist_ok=True)

    try:
        feature_geojson, hb_model_jsons, hb_models = sdk_model_to_urbanopt(
            model=model,
            location=_location_from_dict(location),
            point=_point2d(point),
            shade_distance=shade_distance,
            use_multiplier=use_multiplier,
            exclude_plenums=exclude_plenums,
            solve_ceiling_adjacencies=solve_ceiling_adjacencies,
            merge_method=merge_method,
            des_loop=des_loop,
            folder=str(export_dir),
            tolerance=tolerance,
        )
    except AssertionError as exc:
        blocked = _urbanopt_writer_path_blocked(exc, export_dir=export_dir)
        if blocked is not None:
            return blocked
        raise

    bundle_target = artifact_target_for_path(
        manifest=manifest,
        garden_root=garden_root_path,
        identifier=export_id,
        artifact_type=DES_EXPORT_BUNDLE_ARTIFACT_TYPE,
        path=export_dir,
    )
    feature_target = artifact_target_for_path(
        manifest=manifest,
        garden_root=garden_root_path,
        identifier=f"{export_id}_feature_geojson",
        artifact_type=DES_FEATURE_GEOJSON_ARTIFACT_TYPE,
        path=_bounded_existing_path(garden_root_path, feature_geojson, suffix=".geojson"),
    )
    hb_targets = [
        artifact_target_for_path(
            manifest=manifest,
            garden_root=garden_root_path,
            identifier=f"{export_id}_{slugify_name(Path(path).stem)}",
            artifact_type=DES_HONEYBEE_HBJSON_ARTIFACT_TYPE,
            path=_bounded_existing_path(garden_root_path, path, suffix=".hbjson"),
        )
        for path in hb_model_jsons
    ]
    targets = [bundle_target, feature_target, *hb_targets]
    register_des_artifacts(manifest=manifest, garden_root=garden_root_path, targets=targets)

    receipt = make_artifact_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        artifact_type=DES_EXPORT_BUNDLE_ARTIFACT_TYPE,
        artifact_path=bundle_target["path"],
        absolute_path=str(export_dir),
        source={
            "model_target": resolved_model_target,
            "des_loop_target": des_loop_target or {},
            "writer": "dragonfly_energy.writer.model_to_urbanopt",
        },
    )
    return {
        "target": bundle_target,
        "feature_geojson_target": feature_target,
        "honeybee_model_targets": hb_targets,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": bundle_target,
            "export_id": export_id,
            "export_type": "urbanopt",
            "model_target": resolved_model_target,
            "des_loop_target": des_loop_target or {},
            "feature_geojson_target": feature_target,
            "honeybee_model_count": len(hb_targets),
            "honeybee_model_identifiers": [
                getattr(hb_model, "identifier", Path(path).stem)
                for hb_model, path in zip(hb_models, hb_model_jsons, strict=False)
            ],
        },
        "persistence_receipt": receipt,
        "artifact_receipts": [
            _artifact_receipt(manifest, target, garden_root_path)
            for target in targets
        ],
        "report": make_report(
            status="ok",
            message=f"Exported Dragonfly Model to URBANopt artifacts: {export_id}",
        ),
    }


def export_model_to_des(
    *,
    garden_root: str,
    des_loop_target: dict[str, Any],
    weather_target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    location: dict[str, Any] | None = None,
    point: list[float] | None = None,
    folder_name: str | None = None,
    tolerance: float | None = None,
) -> dict[str, Any]:
    """Export a Dragonfly Model and DES loop to SDK-native DES artifacts."""
    garden_root_path = _garden_root(garden_root)
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    des_loop = load_des_object(garden_root=garden_root_path, target=des_loop_target)
    epw_path = _resolve_weather_epw(
        garden_root=garden_root_path,
        manifest=manifest,
        weather_target=weather_target,
    )
    export_id = _export_id(folder_name, getattr(model, "identifier", "dragonfly"), "des")
    export_dir = garden_root_path / DES_EXPORTS_DIR / export_id
    export_dir.mkdir(parents=True, exist_ok=True)

    try:
        feature_geojson, scenario_csv, system_parameters = sdk_model_to_des(
            model=model,
            des_loop=des_loop,
            epw_file=str(epw_path),
            location=_location_from_dict(location) if location else None,
            point=_point2d(point),
            folder=str(export_dir),
            tolerance=tolerance,
        )
    except AssertionError as exc:
        blocked = _urbanopt_writer_path_blocked(exc, export_dir=export_dir)
        if blocked is not None:
            return blocked
        raise

    bundle_target = artifact_target_for_path(
        manifest=manifest,
        garden_root=garden_root_path,
        identifier=export_id,
        artifact_type=DES_EXPORT_BUNDLE_ARTIFACT_TYPE,
        path=export_dir,
    )
    feature_target = artifact_target_for_path(
        manifest=manifest,
        garden_root=garden_root_path,
        identifier=f"{export_id}_feature_geojson",
        artifact_type=DES_FEATURE_GEOJSON_ARTIFACT_TYPE,
        path=_bounded_existing_path(garden_root_path, feature_geojson, suffix=".geojson"),
    )
    scenario_target = artifact_target_for_path(
        manifest=manifest,
        garden_root=garden_root_path,
        identifier=f"{export_id}_scenario_csv",
        artifact_type=DES_SCENARIO_CSV_ARTIFACT_TYPE,
        path=_bounded_existing_path(garden_root_path, scenario_csv, suffix=".csv"),
    )
    system_target = artifact_target_for_path(
        manifest=manifest,
        garden_root=garden_root_path,
        identifier=f"{export_id}_system_parameter_json",
        artifact_type=DES_SYSTEM_PARAMETER_JSON_ARTIFACT_TYPE,
        path=_bounded_existing_path(garden_root_path, system_parameters, suffix=".json"),
    )
    targets = [bundle_target, feature_target, scenario_target, system_target]
    register_des_artifacts(manifest=manifest, garden_root=garden_root_path, targets=targets)

    receipt = make_artifact_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        artifact_type=DES_EXPORT_BUNDLE_ARTIFACT_TYPE,
        artifact_path=bundle_target["path"],
        absolute_path=str(export_dir),
        source={
            "model_target": resolved_model_target,
            "des_loop_target": des_loop_target,
            "weather_target": weather_target,
            "writer": "dragonfly_energy.writer.model_to_des",
        },
    )
    return {
        "target": bundle_target,
        "feature_geojson_target": feature_target,
        "scenario_csv_target": scenario_target,
        "system_parameter_json_target": system_target,
        "summary_view": {
            "garden_target": manifest.target(),
            "target": bundle_target,
            "export_id": export_id,
            "export_type": "des",
            "model_target": resolved_model_target,
            "des_loop_target": des_loop_target,
            "weather_target": weather_target,
            "feature_geojson_target": feature_target,
            "scenario_csv_target": scenario_target,
            "system_parameter_json_target": system_target,
        },
        "persistence_receipt": receipt,
        "artifact_receipts": [
            _artifact_receipt(manifest, target, garden_root_path)
            for target in targets
        ],
        "report": make_report(
            status="ok",
            message=f"Exported Dragonfly Model to DES artifacts: {export_id}",
        ),
    }


def _garden_root(value: str | Path) -> Path:
    return Path(value).expanduser()


def _export_id(folder_name: str | None, model_identifier: str, suffix: str) -> str:
    if folder_name:
        return _bounded_export_id(slugify_name(folder_name))
    return _bounded_export_id(slugify_name(f"{model_identifier}_{suffix}_{uuid4().hex[:8]}"))


def _bounded_export_id(value: str) -> str:
    if len(value) <= MAX_EXPORT_ID_LENGTH:
        return value
    digest = sha1(value.encode("utf-8")).hexdigest()[:8]
    prefix = value[: MAX_EXPORT_ID_LENGTH - len(digest) - 1].rstrip("_-")
    return f"{prefix}_{digest}"


def _urbanopt_writer_path_blocked(exc: AssertionError, *, export_dir: Path) -> dict[str, Any] | None:
    message = str(exc)
    if "too long to be used with URBANopt" not in message:
        return None
    return {
        "runtime_status": "blocked",
        "summary_view": {
            "status": "blocked",
            "reason": "urbanopt_writer_path_too_long",
            "export_folder": str(export_dir),
            "export_folder_length": len(str(export_dir)),
            "required_max_length": 59,
        },
        "poll_next": None,
        "report": make_report(
            status="blocked",
            message=(
                "Dragonfly Energy URBANopt writer requires the export folder path "
                "to be shorter than 60 characters. Create the Garden in a shorter "
                "root path or use a shorter folder_name."
            ),
            details={
                "diagnostics": [
                    {
                        "code": "urbanopt_writer_path_too_long",
                        "message": message,
                        "path": str(export_dir),
                    }
                ],
                "recommended_action": "Create the Garden in a shorter root path.",
            },
        ),
    }


def _location_from_dict(value: dict[str, Any]) -> Location:
    if not isinstance(value, dict):
        raise ValueError("location must be a dictionary with latitude and longitude.")
    return Location(
        city=value.get("city"),
        state=value.get("state"),
        country=value.get("country"),
        latitude=value.get("latitude", 0),
        longitude=value.get("longitude", 0),
        time_zone=value.get("time_zone"),
        elevation=value.get("elevation", 0),
        station_id=value.get("station_id"),
        source=value.get("source"),
    )


def _point2d(value: list[float] | None) -> Point2D:
    if value is None:
        return Point2D(0, 0)
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("point must be [x, y].")
    return Point2D(value[0], value[1])


def _bounded_existing_path(garden_root: Path, value: str | Path, *, suffix: str) -> Path:
    path = Path(value).expanduser().resolve()
    try:
        path.relative_to(garden_root.resolve())
    except ValueError as exc:
        raise ValueError("Dragonfly DES export artifacts must stay inside the Garden.") from exc
    if path.suffix.lower() != suffix:
        raise ValueError(f"Expected a {suffix} export artifact: {path}")
    if not path.is_file():
        raise ValueError(f"Dragonfly DES export artifact not found: {path}")
    return path


def _resolve_weather_epw(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    weather_target: dict[str, Any],
) -> Path:
    if not isinstance(weather_target, dict):
        raise ValueError("weather_target must be a Garden weather_file target.")
    if weather_target.get("target_type") != "weather_file":
        raise ValueError("weather_target must have target_type 'weather_file'.")
    if weather_target.get("garden_id") != manifest.garden_id:
        raise ValueError("weather_target belongs to a different Garden.")
    path_value = weather_target.get("epw_path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("weather_target requires epw_path.")
    if Path(path_value).is_absolute():
        raise ValueError("weather_target epw_path must be Garden-relative.")
    epw_path = (garden_root / path_value).resolve()
    try:
        epw_path.relative_to(garden_root.resolve())
    except ValueError as exc:
        raise ValueError("weather_target epw_path must stay inside the Garden.") from exc
    if epw_path.suffix.lower() != ".epw":
        raise ValueError("weather_target epw_path must reference a .epw file.")
    if not epw_path.is_file():
        raise ValueError(f"EPW file not found: {path_value}")
    return epw_path


def _artifact_receipt(
    manifest: GardenManifest,
    target: dict[str, Any],
    garden_root: Path,
) -> dict[str, Any]:
    return make_artifact_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        artifact_type=target["artifact_type"],
        artifact_path=target["path"],
        absolute_path=str((garden_root / target["path"]).resolve()),
        source={"target": target},
    )
