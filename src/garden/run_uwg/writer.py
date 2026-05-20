"""Dragonfly Model to UWG JSON artifact services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import dragonfly_uwg._extend_dragonfly  # noqa: F401
from dragonfly_uwg.writer import model_to_uwg as sdk_model_to_uwg

from garden.dragonfly_core.model_io import load_dragonfly_model, resolve_model_target
from garden.manifest import GardenManifest
from garden.paths import slugify_name, to_posix_relative
from garden.run_uwg import UWG_ARTIFACT_DIR, UWG_JSON_ARTIFACT_TYPE
from garden.run_uwg.parameters import load_uwg_simulation_parameter
from ladybug_tools_mcp.contracts.receipts import make_artifact_receipt
from ladybug_tools_mcp.contracts.report import make_report

UWG_JSON_DIR = UWG_ARTIFACT_DIR / "json"


def dragonfly_model_to_uwg(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    weather_target: dict[str, Any] | None = None,
    simulation_parameter_target: dict[str, Any] | None = None,
    simulation_parameter: dict[str, Any] | None = None,
    name: str | None = None,
    include_body: bool = False,
) -> dict[str, Any]:
    """Write a UWG JSON artifact from a Dragonfly model and EPW."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    resolved_epw = resolve_epw_path(
        garden_root=garden_root_path,
        manifest=manifest,
        weather_target=weather_target,
    )
    parameter, parameter_target, parameter_dict = load_uwg_simulation_parameter(
        garden_root=garden_root_path,
        simulation_parameter_target=simulation_parameter_target,
        simulation_parameter=simulation_parameter,
    )
    uwg_dict = sdk_model_to_uwg(
        model,
        str(resolved_epw),
        simulation_parameter=parameter,
    )
    identifier = slugify_name(name or f"{model.identifier}_uwg")
    output_dir = garden_root_path / UWG_JSON_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{identifier}.json"
    output_path.write_text(
        json.dumps(uwg_dict, indent=2) + "\n",
        encoding="utf-8",
    )
    target = make_uwg_json_artifact_target(
        manifest=manifest,
        identifier=identifier,
        path=to_posix_relative(output_path, garden_root_path),
    )
    _register_artifact(manifest, garden_root_path, target)

    summary_view = {
        "target": target,
        "uwg_json_artifact_target": target,
        "model_target": resolved_model_target,
        "weather_target": weather_target or {},
        "epw_path": to_posix_relative(resolved_epw, garden_root_path),
        "simulation_parameter_target": parameter_target,
        "has_simulation_parameter": parameter is not None,
        "path": target["path"],
    }
    if parameter_dict is not None:
        summary_view["simulation_parameter_summary"] = {
            "timestep": parameter_dict.get("timestep"),
            "climate_zone": parameter_dict.get("climate_zone"),
        }
    result = {
        "target": target,
        "uwg_json_artifact_target": target,
        "summary_view": summary_view,
        "artifact_receipt": make_artifact_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            artifact_type=UWG_JSON_ARTIFACT_TYPE,
            artifact_path=target["path"],
            absolute_path=str(output_path),
            source={
                "model_target": resolved_model_target,
                "weather_target": weather_target or {},
                "simulation_parameter_target": parameter_target or {},
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Wrote UWG JSON artifact: {identifier}",
        ),
    }
    if include_body:
        result["object_dict"] = uwg_dict
    return result


def resolve_epw_path(
    *,
    garden_root: Path,
    manifest: GardenManifest,
    weather_target: dict[str, Any] | None,
) -> Path:
    """Resolve an exact Garden weather_file target to its EPW path."""
    if weather_target is None:
        raise ValueError("weather_target is required.")
    if not isinstance(weather_target, dict):
        raise ValueError("weather_target must be a dictionary.")
    if weather_target.get("target_type") != "weather_file":
        raise ValueError("weather_target must be a Garden weather_file target.")
    if weather_target.get("garden_id") != manifest.garden_id:
        raise ValueError("weather_target belongs to a different Garden.")
    path_value = weather_target.get("epw_path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("weather_target requires epw_path.")
    if Path(path_value).is_absolute():
        raise ValueError("weather_target epw_path must be Garden-relative.")
    return _resolve_existing_garden_file(garden_root, path_value, suffix=".epw")


def make_uwg_json_artifact_target(
    *,
    manifest: GardenManifest,
    identifier: str,
    path: str,
) -> dict[str, Any]:
    """Build a UWG JSON artifact target."""
    return {
        "target_type": "artifact",
        "garden_id": manifest.garden_id,
        "domain": "dragonfly_uwg",
        "artifact_type": UWG_JSON_ARTIFACT_TYPE,
        "identifier": identifier,
        "path": path,
    }


def _register_artifact(
    manifest: GardenManifest,
    garden_root: Path,
    target: dict[str, Any],
) -> None:
    manifest.artifacts = [
        item
        for item in manifest.artifacts
        if not (
            item.get("artifact_type") == target["artifact_type"]
            and item.get("identifier") == target["identifier"]
        )
    ]
    manifest.artifacts.append(target)
    manifest.write(garden_root)


def _resolve_existing_garden_file(garden_root: Path, value: str, *, suffix: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = garden_root / path
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(garden_root.resolve())
    except ValueError as exc:
        raise ValueError("UWG weather input paths must stay inside the Garden.") from exc
    if resolved.suffix.lower() != suffix:
        raise ValueError(f"Expected a {suffix} file: {value}")
    if not resolved.is_file():
        raise ValueError(f"Weather file not found: {value}")
    return resolved
