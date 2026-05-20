"""Energy simulation output request services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from honeybee_energy.simulation.output import SimulationOutput
from honeybee_energy.simulation.parameter import SimulationParameter

from ladybug_tools_mcp.contracts.report import make_report
from garden.manifest import GardenManifest, utc_now_iso
from garden.paths import slugify_name, to_posix_relative

ENERGY_OUTPUT_REQUEST_TARGET_TYPE = "energy_output_request"
ENERGY_OUTPUT_REQUEST_DOMAIN = "honeybee_energy"
ENERGY_OUTPUT_REQUESTS_DIR = Path("runs") / "energy" / "output_requests"

_PRESET_METHODS = {
    "comfort_metrics": ("add_comfort_metrics", ()),
    "electricity_generation": ("add_electricity_generation", ()),
    "energy_balance": ("add_energy_balance_variables", ()),
    "gains_and_losses": ("add_gains_and_losses", ()),
    "glazing_solar": ("add_glazing_solar", ()),
    "hvac_energy_use": ("add_hvac_energy_use", ()),
    "surface_energy_flow": ("add_surface_energy_flow", ()),
    "surface_temperature": ("add_surface_temperature", ()),
    "unmet_hours": ("add_unmet_hours", ()),
    "zone_energy_use": ("add_zone_energy_use", ()),
}


def _garden_root(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _target(*, manifest: GardenManifest, identifier: str, path: Path | str) -> dict[str, Any]:
    return {
        "target_type": ENERGY_OUTPUT_REQUEST_TARGET_TYPE,
        "garden_id": manifest.garden_id,
        "domain": ENERGY_OUTPUT_REQUEST_DOMAIN,
        "identifier": identifier,
        "path": str(path).replace("\\", "/"),
    }


def _request_path(garden_root: Path, identifier: str) -> Path:
    return garden_root / ENERGY_OUTPUT_REQUESTS_DIR / f"{identifier}.json"


def _apply_preset(output: SimulationOutput, preset: str) -> None:
    key = preset.strip().lower().replace("-", "_")
    if key not in _PRESET_METHODS:
        allowed = ", ".join(sorted(_PRESET_METHODS))
        raise ValueError(f"Unsupported energy output preset: {preset}. Allowed: {allowed}.")
    method_name, args = _PRESET_METHODS[key]
    getattr(output, method_name)(*args)


def _summary(target: dict[str, Any], simulation_output: dict[str, Any]) -> dict[str, Any]:
    outputs = list(simulation_output.get("outputs", []))
    summary_reports = list(simulation_output.get("summary_reports", []))
    return {
        "target": target,
        "identifier": target["identifier"],
        "path": target["path"],
        "reporting_frequency": simulation_output.get("reporting_frequency"),
        "include_sqlite": simulation_output.get("include_sqlite", True),
        "include_html": simulation_output.get("include_html", True),
        "output_count": len(outputs),
        "summary_report_count": len(summary_reports),
        "outputs_preview": outputs[:10],
        "summary_reports": summary_reports,
    }


def create_energy_output_request(
    *,
    garden_root: str,
    identifier: str,
    presets: list[str] | None = None,
    custom_outputs: list[str] | None = None,
    summary_reports: list[str] | None = None,
    reporting_frequency: str = "Hourly",
    include_sqlite: bool = True,
    include_html: bool = True,
    unmet_setpoint_tolerance: float = 1.11,
) -> dict[str, Any]:
    """Create a Garden target describing requested EnergyPlus outputs."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    safe_identifier = slugify_name(identifier).replace("-", "_")
    output = SimulationOutput(
        outputs=[],
        reporting_frequency=reporting_frequency,
        include_sqlite=include_sqlite,
        include_html=include_html,
        summary_reports=summary_reports or (),
        unmet_setpoint_tolerance=unmet_setpoint_tolerance,
    )
    for preset in presets or []:
        _apply_preset(output, preset)
    for output_name in custom_outputs or []:
        output.add_output(output_name)

    simulation_output = output.to_dict()
    path = _request_path(garden_root_path, safe_identifier)
    path.parent.mkdir(parents=True, exist_ok=True)
    target = _target(
        manifest=manifest,
        identifier=safe_identifier,
        path=to_posix_relative(path, garden_root_path),
    )
    payload = {
        "type": "EnergyOutputRequest",
        "schema_version": "1",
        "identifier": safe_identifier,
        "target": target,
        "created_at": utc_now_iso(),
        "presets": list(presets or []),
        "custom_outputs": list(custom_outputs or []),
        "simulation_output": simulation_output,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "target": target,
        "energy_output_request_target": target,
        "summary_view": {
            "garden_target": manifest.target(),
            **_summary(target, simulation_output),
        },
        "persistence_receipt": {
            "status": "persisted",
            "garden_id": manifest.garden_id,
            "target": target,
            "persisted_path": target["path"],
        },
        "report": make_report(
            status="ok",
            message=f"Energy output request created: {safe_identifier}.",
        ),
    }


def read_energy_output_request(
    *,
    garden_root: str | Path,
    output_request_target: dict[str, Any],
) -> dict[str, Any]:
    """Read and validate an energy_output_request target payload."""
    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    if output_request_target.get("target_type") != ENERGY_OUTPUT_REQUEST_TARGET_TYPE:
        raise ValueError("output_request_target must be an energy_output_request target.")
    target_garden_id = output_request_target.get("garden_id")
    if target_garden_id != manifest.garden_id:
        raise ValueError("output_request_target belongs to a different Garden.")
    path_value = output_request_target.get("path")
    if not isinstance(path_value, str) or not path_value:
        raise ValueError("output_request_target requires a Garden-relative path.")
    path = (garden_root_path / path_value).resolve()
    path.relative_to(garden_root_path)
    if not path.is_file():
        raise ValueError("Energy output request file was not found.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "EnergyOutputRequest":
        raise ValueError("Energy output request payload has an unsupported type.")
    return payload


def simulation_parameter_with_output_request(
    *,
    garden_root: str | Path,
    output_request_target: dict[str, Any] | None,
    sim_par: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Merge an output request target into a SimulationParameter dictionary."""
    if output_request_target is None:
        return sim_par, None
    payload = read_energy_output_request(
        garden_root=garden_root,
        output_request_target=output_request_target,
    )
    output = SimulationOutput.from_dict(payload["simulation_output"])
    if sim_par is None:
        parameter = SimulationParameter(output=output)
    else:
        parameter = SimulationParameter.from_dict(sim_par)
        parameter.output = output
    return parameter.to_dict(), payload["target"]
