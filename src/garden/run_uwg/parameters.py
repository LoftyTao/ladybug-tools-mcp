"""UWG simulation parameter target services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dragonfly_uwg.simulation.boundary import BoundaryLayerParameter
from dragonfly_uwg.simulation.parameter import UWGSimulationParameter
from dragonfly_uwg.simulation.refsite import ReferenceEPWSite
from dragonfly_uwg.simulation.runperiod import UWGRunPeriod
from dragonfly_uwg.simulation.vegetation import VegetationParameter
from ladybug.dt import Date

from garden.manifest import GardenManifest
from garden.paths import slugify_name, to_posix_relative
from garden.run_uwg import UWG_ARTIFACT_DIR, UWG_DOMAIN, UWG_PARAMETER_TARGET_TYPE
from ladybug_tools_mcp.contracts.receipts import make_artifact_receipt
from ladybug_tools_mcp.contracts.report import make_report

PARAMETERS_DIR = UWG_ARTIFACT_DIR / "parameters"


def create_uwg_simulation_parameter(
    *,
    garden_root: str,
    identifier: str | None = None,
    climate_zone: str | None = None,
    run_period: dict[str, Any] | None = None,
    timestep: int = 12,
    vegetation_parameter: dict[str, Any] | None = None,
    reference_epw_site: dict[str, Any] | None = None,
    boundary_layer_parameter: dict[str, Any] | None = None,
    save: bool = True,
    include_body: bool = False,
) -> dict[str, Any]:
    """Create and optionally persist a UWGSimulationParameter."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest = GardenManifest.read(garden_root_path)
    parameter = _build_parameter(
        climate_zone=climate_zone,
        run_period=run_period,
        timestep=timestep,
        vegetation_parameter=vegetation_parameter,
        reference_epw_site=reference_epw_site,
        boundary_layer_parameter=boundary_layer_parameter,
    )
    object_dict = parameter.to_dict()
    summary_view = _parameter_summary(object_dict)
    result: dict[str, Any] = {
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message="Created UWG simulation parameter.",
        ),
    }
    if include_body or not save:
        result["object_dict"] = object_dict
    if not save:
        return result

    identifier_value = slugify_name(identifier or "uwg_simulation_parameter")
    output_dir = garden_root_path / PARAMETERS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{identifier_value}.json"
    output_path.write_text(
        json.dumps(object_dict, indent=2) + "\n",
        encoding="utf-8",
    )
    target = make_uwg_simulation_parameter_target(
        garden_id=manifest.garden_id,
        identifier=identifier_value,
        path=to_posix_relative(output_path, garden_root_path),
    )
    artifact = {
        "target_type": "artifact",
        "garden_id": manifest.garden_id,
        "artifact_type": "uwg_simulation_parameter",
        "identifier": identifier_value,
        "path": target["path"],
        "source": target,
    }
    manifest.artifacts = [
        item
        for item in manifest.artifacts
        if not (
            item.get("artifact_type") == artifact["artifact_type"]
            and item.get("identifier") == identifier_value
        )
    ]
    manifest.artifacts.append(artifact)
    manifest.write(garden_root_path)
    result.update(
        {
            "target": target,
            "uwg_simulation_parameter_target": target,
            "artifact_receipt": make_artifact_receipt(
                status="persisted",
                garden_id=manifest.garden_id,
                artifact_type="uwg_simulation_parameter",
                artifact_path=target["path"],
                absolute_path=str(output_path),
                source=target,
            ),
        }
    )
    result["summary_view"]["target"] = target
    return result


def make_uwg_simulation_parameter_target(
    *,
    garden_id: str,
    identifier: str,
    path: str,
) -> dict[str, Any]:
    """Build a persisted UWG simulation parameter target."""
    return {
        "target_type": UWG_PARAMETER_TARGET_TYPE,
        "garden_id": garden_id,
        "domain": UWG_DOMAIN,
        "identifier": identifier,
        "path": path,
    }


def normalize_uwg_simulation_parameter_target(value: Any) -> dict[str, Any]:
    """Validate a UWG simulation parameter target."""
    if not isinstance(value, dict):
        raise ValueError("UWG simulation parameter target must be a dictionary.")
    if value.get("target_type") != UWG_PARAMETER_TARGET_TYPE:
        raise ValueError(
            "UWG simulation parameter target must have target_type "
            f"{UWG_PARAMETER_TARGET_TYPE!r}."
        )
    if value.get("domain") != UWG_DOMAIN:
        raise ValueError("UWG simulation parameter target must have domain 'dragonfly_uwg'.")
    if not value.get("path"):
        raise ValueError("UWG simulation parameter target requires path.")
    return dict(value)


def load_uwg_simulation_parameter(
    *,
    garden_root: Path,
    simulation_parameter_target: dict[str, Any] | None = None,
    simulation_parameter: dict[str, Any] | None = None,
) -> tuple[UWGSimulationParameter | None, dict[str, Any] | None, dict[str, Any] | None]:
    """Resolve a target or inline dictionary to a UWGSimulationParameter."""
    if simulation_parameter_target is not None and simulation_parameter is not None:
        raise ValueError(
            "Pass either simulation_parameter_target or simulation_parameter, not both."
        )
    if simulation_parameter_target is not None:
        target = normalize_uwg_simulation_parameter_target(simulation_parameter_target)
        path = _resolve_garden_path(garden_root, str(target["path"]))
        data = json.loads(path.read_text(encoding="utf-8"))
        return UWGSimulationParameter.from_dict(data), target, data
    if simulation_parameter is not None:
        return UWGSimulationParameter.from_dict(simulation_parameter), None, simulation_parameter
    return None, None, None


def _build_parameter(
    *,
    climate_zone: str | None,
    run_period: dict[str, Any] | None,
    timestep: int,
    vegetation_parameter: dict[str, Any] | None,
    reference_epw_site: dict[str, Any] | None,
    boundary_layer_parameter: dict[str, Any] | None,
) -> UWGSimulationParameter:
    kwargs: dict[str, Any] = {"timestep": timestep}
    if climate_zone is not None:
        kwargs["climate_zone"] = climate_zone
    if run_period is not None:
        kwargs["run_period"] = _run_period_from_input(run_period)
    if vegetation_parameter is not None:
        kwargs["vegetation_parameter"] = VegetationParameter.from_dict(
            vegetation_parameter
        )
    if reference_epw_site is not None:
        kwargs["reference_epw_site"] = ReferenceEPWSite.from_dict(reference_epw_site)
    if boundary_layer_parameter is not None:
        kwargs["boundary_layer_parameter"] = BoundaryLayerParameter.from_dict(
            boundary_layer_parameter
        )
    return UWGSimulationParameter(**kwargs)


def _run_period_from_input(value: dict[str, Any] | None) -> UWGRunPeriod | None:
    if value is None:
        return None
    if value.get("type") == "UWGRunPeriod":
        return UWGRunPeriod.from_dict(value)
    return UWGRunPeriod(
        start_date=Date(int(value["start_month"]), int(value["start_day"])),
        end_date=Date(int(value["end_month"]), int(value["end_day"])),
    )


def _parameter_summary(data: dict[str, Any]) -> dict[str, Any]:
    run_period = data.get("run_period") or {}
    return {
        "type": data.get("type"),
        "climate_zone": data.get("climate_zone"),
        "timestep": data.get("timestep"),
        "run_period": run_period,
        "has_vegetation_parameter": bool(data.get("vegetation_parameter")),
        "has_reference_epw_site": bool(data.get("reference_epw_site")),
        "has_boundary_layer_parameter": bool(data.get("boundary_layer_parameter")),
    }


def _resolve_garden_path(garden_root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = garden_root / path
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(garden_root.resolve())
    except ValueError as exc:
        raise ValueError("UWG simulation parameter path must stay inside the Garden.") from exc
    if not resolved.is_file():
        raise ValueError(f"UWG simulation parameter file not found: {value}")
    return resolved
