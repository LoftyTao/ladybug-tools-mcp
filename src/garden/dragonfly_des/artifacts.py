"""Garden artifact helpers for Dragonfly DES exports and projects."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from garden.manifest import GardenManifest
from garden.paths import to_posix_relative

DES_ARTIFACT_DOMAIN = "dragonfly_des"
DES_EXPORT_BUNDLE_ARTIFACT_TYPE = "dragonfly_des_export_bundle"
DES_FEATURE_GEOJSON_ARTIFACT_TYPE = "dragonfly_des_feature_geojson"
DES_HONEYBEE_HBJSON_ARTIFACT_TYPE = "dragonfly_des_honeybee_hbjson"
DES_SCENARIO_CSV_ARTIFACT_TYPE = "dragonfly_des_scenario_csv"
DES_SYSTEM_PARAMETER_JSON_ARTIFACT_TYPE = "dragonfly_des_system_parameter_json"
DES_MODELICA_PROJECT_ARTIFACT_TYPE = "dragonfly_des_modelica_project"


def make_des_artifact_target(
    *,
    manifest: GardenManifest,
    identifier: str,
    artifact_type: str,
    path: str,
) -> dict[str, Any]:
    """Build a compact Dragonfly DES Garden artifact target."""
    return {
        "target_type": "artifact",
        "domain": DES_ARTIFACT_DOMAIN,
        "garden_id": manifest.garden_id,
        "artifact_type": artifact_type,
        "identifier": identifier,
        "path": path,
    }


def register_des_artifacts(
    *,
    manifest: GardenManifest,
    garden_root: Path,
    targets: list[dict[str, Any]],
) -> None:
    """Register DES artifact targets in the Garden manifest."""
    for target in targets:
        manifest.artifacts = [
            item
            for item in manifest.artifacts
            if not (
                item.get("domain") == DES_ARTIFACT_DOMAIN
                and item.get("artifact_type") == target["artifact_type"]
                and item.get("identifier") == target["identifier"]
            )
        ]
        manifest.artifacts.append(target)
    manifest.write(garden_root)


def artifact_target_for_path(
    *,
    manifest: GardenManifest,
    garden_root: Path,
    identifier: str,
    artifact_type: str,
    path: Path,
) -> dict[str, Any]:
    """Build a DES artifact target from an absolute Garden-bounded path."""
    return make_des_artifact_target(
        manifest=manifest,
        identifier=identifier,
        artifact_type=artifact_type,
        path=to_posix_relative(path, garden_root),
    )


def resolve_des_artifact_path(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    target: dict[str, Any],
    expected_artifact_type: str | None = None,
    suffix: str | None = None,
    expect_directory: bool = False,
) -> Path:
    """Resolve and validate a DES artifact target path inside one Garden."""
    if not isinstance(target, dict):
        raise ValueError("Expected a Dragonfly DES artifact target dictionary.")
    if target.get("target_type") != "artifact":
        raise ValueError("DES artifact target must have target_type 'artifact'.")
    if target.get("domain") != DES_ARTIFACT_DOMAIN:
        raise ValueError("DES artifact target must reference domain 'dragonfly_des'.")
    if target.get("garden_id") != manifest.garden_id:
        raise ValueError("DES artifact target belongs to a different Garden.")
    if expected_artifact_type is not None and target.get("artifact_type") != expected_artifact_type:
        raise ValueError(f"Expected DES artifact type '{expected_artifact_type}'.")
    path_value = target.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("DES artifact target requires a non-empty path.")
    if Path(path_value).is_absolute():
        raise ValueError("DES artifact target path must be Garden-relative.")
    path = (garden_root / path_value).resolve()
    try:
        path.relative_to(garden_root.resolve())
    except ValueError as exc:
        raise ValueError("DES artifact target path must stay inside the Garden.") from exc
    if expect_directory:
        if not path.is_dir():
            raise ValueError(f"DES artifact target must reference an existing directory: {path_value}")
    else:
        if suffix is not None and path.suffix.lower() != suffix:
            raise ValueError(f"DES artifact target must reference a {suffix} file.")
        if not path.is_file():
            raise ValueError(f"DES artifact file not found: {path_value}")
    return path
