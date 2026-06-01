"""Ironbug-Core bridge to Honeybee Energy DetailedHVAC."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from honeybee.model import Model
from honeybee.room import Room
from honeybee_energy.hvac.detailed import DetailedHVAC
from ironbug import hvac as ironbug_hvac
from ironbug.hvac import IB_Model
from pydantic import BaseModel

from garden.dragonfly_core.conversion import dragonfly_model_to_honeybee
from garden.dragonfly_core.model_io import (
    load_dragonfly_model,
    resolve_model_target as resolve_dragonfly_model_target,
    save_dragonfly_model,
)
from garden.dragonfly_core.targets import normalize_dragonfly_object_target
from garden.honeybee_core.locate import find_object
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target,
    save_honeybee_model,
    with_honeybee_model_write_lock,
)
from garden.honeybee_core.targets import normalize_honeybee_object_target
from garden.ironbug_core.assembly import _component_library, _hydrate_source_object
from garden.ironbug_core.model_io import load_ironbug_model
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report


NO_AIR_LOOP_TYPE = "Ironbug.HVAC.IB_NoAirLoop, Ironbug.HVAC"
ROOM_REFERENCE_ERROR_CODES = {"020012", "020013"}
SIMULATION_READINESS_ERROR_CODES = {"020011"}
ROOM_SERVING_PREFIXES = ("IB_AirTerminal", "IB_ZoneHVAC")
ROOM_SERVING_CLASSES = {
    "IB_AirLoopHVACUnitarySystem",
    "IB_FanZoneExhaust",
    "IB_WaterHeaterHeatPump",
    "IB_WaterHeaterMixed",
    "IB_ZoneEquipmentGroup",
}


def _garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def build_detailed_hvac_specification(
    *,
    room_identifiers: list[str],
) -> dict[str, Any]:
    """Build the minimal IronBug no-air-loop DetailedHVAC specification."""

    normalized_room_ids = _normalize_room_identifiers(room_identifiers)
    return {
        "AirLoops": [
            {
                "$type": NO_AIR_LOOP_TYPE,
                "ThermalZones": [
                    {
                        "CustomAttributes": [
                            {
                                "Field": {"FullName": "Name"},
                                "Value": room_identifier,
                            }
                        ]
                    }
                    for room_identifier in normalized_room_ids
                ],
            }
        ]
    }


def build_chiller_condenser_loop_detailed_hvac_specification(
    *,
    ironbug_model: IB_Model,
    room_identifiers: list[str],
) -> dict[str, Any]:
    """Build an Ironbug Console specification for Example 1-style plant loops."""

    _ensure_ironbug_hvac_system(ironbug_model)
    specification = build_detailed_hvac_specification(
        room_identifiers=room_identifiers,
    )
    specification["PlantLoops"] = [
        _ironbug_console_spec_value(loop) for loop in _plant_loops(ironbug_model)
    ]
    return specification


def build_ironbug_model_detailed_hvac_specification(
    *,
    ironbug_model: IB_Model,
    room_identifiers: list[str],
) -> dict[str, Any]:
    """Build a DetailedHVAC specification from the source-backed Ironbug graph."""

    _ensure_ironbug_hvac_system(ironbug_model)
    air_loops = _air_loops(ironbug_model)
    plant_loops = _plant_loops(ironbug_model)
    vrfs = _variable_refrigerant_flows(ironbug_model)
    _ensure_explicit_room_linked_thermal_zones(
        ironbug_model,
        air_loops=air_loops,
        plant_loops=plant_loops,
        vrfs=vrfs,
    )

    if not air_loops and not vrfs:
        thermal_zones = _component_thermal_zones(ironbug_model)
        if thermal_zones:
            specification = {
                "AirLoops": [
                    {
                        "$type": NO_AIR_LOOP_TYPE,
                        "ThermalZones": [
                            _ironbug_console_spec_value(zone) for zone in thermal_zones
                        ],
                    }
                ]
            }
        else:
            specification = build_detailed_hvac_specification(
                room_identifiers=room_identifiers,
            )
    else:
        thermal_zones = _component_thermal_zones(ironbug_model)
        specification = {
            "AirLoops": [_ironbug_console_spec_value(loop) for loop in air_loops]
        }
        if not specification["AirLoops"] and thermal_zones:
            specification["AirLoops"] = [
                {
                    "$type": NO_AIR_LOOP_TYPE,
                    "ThermalZones": [
                        _ironbug_console_spec_value(zone) for zone in thermal_zones
                    ],
                }
            ]
        if not specification["AirLoops"]:
            specification["AirLoops"] = build_detailed_hvac_specification(
                room_identifiers=room_identifiers,
            )["AirLoops"]
    if plant_loops:
        specification["PlantLoops"] = [
            _ironbug_console_spec_value(loop) for loop in plant_loops
        ]
    if vrfs:
        specification["VariableRefrigerantFlows"] = [
            _ironbug_console_spec_value(vrf) for vrf in vrfs
        ]
    if ironbug_model.EnergyManagementSystem is not None:
        specification["EnergyManagementSystem"] = _ironbug_console_spec_value(
            ironbug_model.EnergyManagementSystem
        )
    if ironbug_model.ElectricLoadCenter is not None:
        specification["ElectricLoadCenter"] = _ironbug_console_spec_value(
            ironbug_model.ElectricLoadCenter
        )
    return specification


def create_detailed_hvac_from_ironbug_model(
    model: IB_Model,
    *,
    identifier: str,
    room_identifiers: list[str],
) -> DetailedHVAC:
    """Create a Honeybee Energy DetailedHVAC from an Ironbug model."""

    _ensure_ironbug_hvac_system(model)
    specification = build_ironbug_model_detailed_hvac_specification(
        ironbug_model=model,
        room_identifiers=room_identifiers,
    )
    try:
        return DetailedHVAC(identifier, specification)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Failed to create DetailedHVAC. {exc}") from exc


def create_ironbug_detailed_hvac(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    room_identifiers: list[str],
    detailed_hvac_identifier: str | None = None,
) -> dict[str, Any]:
    """Create a compact DetailedHVAC bridge summary without mutating a model."""

    garden_root_path = _garden_root(garden_root)
    _, resolved_ironbug_target, _, ironbug_model = load_ironbug_model(
        garden_root_path,
        ironbug_model_target=ironbug_model_target,
    )
    hvac_identifier = _detailed_hvac_identifier(
        detailed_hvac_identifier=detailed_hvac_identifier,
        ironbug_model=ironbug_model,
        ironbug_model_target=resolved_ironbug_target,
    )
    hvac = create_detailed_hvac_from_ironbug_model(
        ironbug_model,
        identifier=hvac_identifier,
        room_identifiers=room_identifiers,
    )
    summary = _detailed_hvac_summary(
        hvac=hvac,
        ironbug_model_target=resolved_ironbug_target,
        honeybee_model_target=None,
        detailed_hvac_room_reference_valid=None,
        energy_ready=False,
        validation_status="not_applied",
        blocking_issues=[],
    )
    target = _detailed_hvac_target(
        ironbug_model_target=resolved_ironbug_target,
        hvac=hvac,
    )
    return {
        "target": target,
        "detailed_hvac_target": target,
        "summary_view": summary,
        "report": make_report(
            status="ok",
            message=f"Created DetailedHVAC bridge summary: {hvac.identifier}",
        ),
    }


@with_honeybee_model_write_lock
def apply_ironbug_detailed_hvac_to_honeybee_model(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    honeybee_model_target: dict[str, Any] | None = None,
    room_targets: list[dict[str, Any]] | None = None,
    room_identifiers: list[str] | None = None,
    apply_to_all_rooms: bool = False,
    detailed_hvac_identifier: str | None = None,
) -> dict[str, Any]:
    """Apply an Ironbug-backed DetailedHVAC to selected Honeybee Rooms."""

    garden_root_path = _garden_root(garden_root)
    manifest, resolved_honeybee_target = resolve_model_target(
        garden_root_path,
        honeybee_model_target,
    )
    honeybee_model = load_honeybee_model(garden_root_path, resolved_honeybee_target)
    _, resolved_ironbug_target, _, ironbug_model = load_ironbug_model(
        garden_root_path,
        ironbug_model_target=ironbug_model_target,
    )
    selected_rooms = _resolve_selected_rooms(
        honeybee_model,
        resolved_honeybee_target,
        room_targets=room_targets,
        room_identifiers=room_identifiers,
        apply_to_all_rooms=apply_to_all_rooms,
    )
    selected_room_identifiers = [room.identifier for room in selected_rooms]
    hvac_identifier = _detailed_hvac_identifier(
        detailed_hvac_identifier=detailed_hvac_identifier,
        ironbug_model=ironbug_model,
        ironbug_model_target=resolved_ironbug_target,
    )
    hvac = create_detailed_hvac_from_ironbug_model(
        ironbug_model,
        identifier=hvac_identifier,
        room_identifiers=selected_room_identifiers,
    )
    original_room_hvacs = {
        room.identifier: room.properties.energy.hvac for room in selected_rooms
    }
    for room in selected_rooms:
        room.properties.energy.hvac = hvac

    validation_issues = _check_detailed_hvac_rooms(honeybee_model)
    blocking_issues = _room_reference_issues(validation_issues)
    simulation_readiness_issues = [
        *_simulation_readiness_issues(validation_issues),
        *_ironbug_thermal_zone_room_binding_issues(
            ironbug_model=ironbug_model,
            selected_room_identifiers=selected_room_identifiers,
        ),
        *_ironbug_graph_simulation_readiness_issues(
            garden_root=str(garden_root_path),
            ironbug_model_target=resolved_ironbug_target,
        ),
    ]
    room_reference_valid = not any(
        issue.get("code") in ROOM_REFERENCE_ERROR_CODES for issue in blocking_issues
    )
    energy_ready = room_reference_valid
    simulation_ready = room_reference_valid and not simulation_readiness_issues
    if simulation_ready:
        updated_target, persisted_path = save_honeybee_model(
            garden_root_path,
            manifest,
            honeybee_model,
            name=str(resolved_honeybee_target["model_identifier"]),
            set_base=manifest.base_honeybee_model == resolved_honeybee_target,
        )
        persistence_status = "persisted"
    else:
        for room in selected_rooms:
            room.properties.energy.hvac = original_room_hvacs[room.identifier]
        updated_target = resolved_honeybee_target
        persisted_path = str(resolved_honeybee_target.get("path", ""))
        persistence_status = "blocked"
    hvac_target = _detailed_hvac_target(
        ironbug_model_target=resolved_ironbug_target,
        honeybee_model_target=updated_target,
        hvac=hvac,
    )
    summary = _detailed_hvac_summary(
        hvac=hvac,
        ironbug_model_target=resolved_ironbug_target,
        honeybee_model_target=updated_target,
        detailed_hvac_room_reference_valid=room_reference_valid,
        energy_ready=energy_ready,
        validation_status="valid" if room_reference_valid else "invalid",
        blocking_issues=blocking_issues,
    )
    summary["selected_room_count"] = len(selected_rooms)
    summary["simulation_ready"] = simulation_ready
    summary["simulation_readiness_issues"] = simulation_readiness_issues
    summary["simulation_readiness_issue_count"] = len(simulation_readiness_issues)
    summary["detailed_hvac_persisted"] = simulation_ready
    receipt = make_persistence_receipt(
        status=persistence_status,
        garden_id=manifest.garden_id,
        model_target=updated_target,
        persisted_path=persisted_path,
        change_summary={
            "operation": "apply_ironbug_detailed_hvac_to_honeybee_model",
            "ironbug_model_target": resolved_ironbug_target,
            "detailed_hvac_target": hvac_target,
            "room_identifiers": selected_room_identifiers,
        },
    )
    return {
        "target": hvac_target,
        "detailed_hvac_target": hvac_target,
        "updated_model_target": updated_target,
        "honeybee_model_target": updated_target,
        "summary_view": summary,
        "persistence_receipt": receipt,
        "report": make_report(
            status=(
                "invalid"
                if not room_reference_valid
                else "blocked"
                if simulation_readiness_issues
                else "ok"
            ),
            message=(
                f"Applied Ironbug DetailedHVAC to {len(selected_rooms)} Honeybee Room(s)."
            ),
            details={
                "detailed_hvac_room_reference_valid": room_reference_valid,
                "energy_ready": energy_ready,
                "simulation_ready": simulation_ready,
                "blocking_issue_count": len(blocking_issues),
                "simulation_readiness_issue_count": len(simulation_readiness_issues),
            },
        ),
    }


def probe_chiller_condenser_loop_detailed_hvac(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    honeybee_model_target: dict[str, Any] | None = None,
    room_targets: list[dict[str, Any]] | None = None,
    room_identifiers: list[str] | None = None,
    detailed_hvac_identifier: str | None = None,
) -> dict[str, Any]:
    """Probe Example System 1 DetailedHVAC translation without running EnergyPlus."""

    applied = apply_ironbug_detailed_hvac_to_honeybee_model(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        honeybee_model_target=honeybee_model_target,
        room_targets=room_targets,
        room_identifiers=room_identifiers,
        apply_to_all_rooms=False,
        detailed_hvac_identifier=detailed_hvac_identifier,
    )
    _, _, _, ironbug_model = load_ironbug_model(
        _garden_root(garden_root),
        ironbug_model_target=ironbug_model_target,
    )
    plant_loop_count = _plant_loop_count(ironbug_model)
    plant_loop_identifiers = _plant_loop_identifiers(ironbug_model)
    operation_scheme_status = _operation_scheme_status(ironbug_model)
    blocking_issue = {
        "code": "detailed_hvac_plant_loop_translator",
        "message": (
            "The source-backed Ironbug plant loops are present, but the Garden "
            "bridge currently emits only a no-air-loop ThermalZone DetailedHVAC "
            "specification. Simulation stays gated until plant loops, "
            "operation schemes, and equipment bindings are translated."
        ),
    }
    summary = {
        **applied["summary_view"],
        "plant_loop_count": plant_loop_count,
        "plant_loop_identifiers": plant_loop_identifiers,
        "plant_loop_translation_status": "blocked",
        "blocking_gap": "detailed_hvac_plant_loop_translator",
        "blocking_issues": [
            *applied["summary_view"].get("blocking_issues", []),
            blocking_issue,
        ],
        "operation_scheme_status": operation_scheme_status,
        "energy_ready": False,
        "simulation_ready": False,
        "energyplus_runtime_ready": False,
        "runtime_attempted": False,
        "simulation_readiness_issues": [
            *applied["summary_view"].get("simulation_readiness_issues", []),
            blocking_issue,
        ],
    }
    summary["simulation_readiness_issue_count"] = len(
        summary["simulation_readiness_issues"]
    )
    return {
        **applied,
        "summary_view": summary,
        "report": make_report(
            status="blocked",
            message=(
                "Generated a no-air-loop DetailedHVAC probe for the selected "
                "Honeybee Room(s), but plant-loop translation is blocked."
            ),
            details={
                "plant_loop_translation_status": "blocked",
                "blocking_gap": "detailed_hvac_plant_loop_translator",
                "energyplus_runtime_ready": False,
                "runtime_attempted": False,
                "plant_loop_count": plant_loop_count,
                "plant_loop_identifiers": plant_loop_identifiers,
                "operation_scheme_status": operation_scheme_status,
            },
        ),
    }


def apply_ironbug_detailed_hvac_to_dragonfly_model(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    dragonfly_model_target: dict[str, Any] | None = None,
    room_identifiers: list[str] | None = None,
    apply_to_all_rooms: bool = False,
    detailed_hvac_identifier: str | None = None,
) -> dict[str, Any]:
    """Convert Dragonfly to Honeybee, then apply the Ironbug DetailedHVAC bridge."""

    conversion = dragonfly_model_to_honeybee(
        garden_root=garden_root,
        model_target=dragonfly_model_target,
        set_base=False,
    )
    honeybee_targets = conversion.get("honeybee_model_targets") or conversion.get(
        "model_targets"
    )
    if not honeybee_targets:
        raise ValueError("Dragonfly conversion produced zero Honeybee models.")
    honeybee_model_target = honeybee_targets[0]
    applied = apply_ironbug_detailed_hvac_to_honeybee_model(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
        honeybee_model_target=honeybee_model_target,
        room_identifiers=room_identifiers,
        apply_to_all_rooms=apply_to_all_rooms,
        detailed_hvac_identifier=detailed_hvac_identifier,
    )
    summary = {
        **applied["summary_view"],
        "source_dragonfly_model_target": dragonfly_model_target
        or conversion.get("source_model_target"),
        "honeybee_model_target": honeybee_model_target,
    }
    return {
        **applied,
        "source_dragonfly_model_target": dragonfly_model_target
        or conversion.get("source_model_target"),
        "honeybee_model_target": honeybee_model_target,
        "summary_view": summary,
        "report": make_report(
            status=applied["report"]["status"],
            message="Converted Dragonfly model to Honeybee and applied Ironbug DetailedHVAC.",
            details=applied["report"].get("details", {}),
        ),
    }


def apply_ironbug_detailed_hvac_to_dragonfly_energy_properties(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    host_target: dict[str, Any],
    dragonfly_model_target: dict[str, Any] | None = None,
    detailed_hvac_identifier: str | None = None,
    conditioned_only: bool = True,
) -> dict[str, Any]:
    """Apply an Ironbug-backed DetailedHVAC to Dragonfly Energy HVAC properties."""

    garden_root_path = _garden_root(garden_root)
    manifest, resolved_dragonfly_target = resolve_dragonfly_model_target(
        garden_root_path,
        dragonfly_model_target,
    )
    dragonfly_model = load_dragonfly_model(
        garden_root_path,
        resolved_dragonfly_target,
    )
    normalized_host_target = normalize_dragonfly_object_target(host_target)
    host_type = normalized_host_target["object_type"]
    if host_type not in {"room2d", "story", "building"}:
        raise ValueError(
            "Dragonfly DetailedHVAC assignment supports room2d, story, and "
            "building targets."
        )
    _ensure_dragonfly_host_belongs_to_model(
        normalized_host_target,
        resolved_dragonfly_target,
    )
    host = _dragonfly_host_from_target(dragonfly_model, normalized_host_target)
    host_room2ds = _dragonfly_room2ds_for_host(host, host_type)
    if not host_room2ds:
        raise ValueError("Dragonfly HVAC host has no Room2Ds.")

    _, resolved_ironbug_target, _, ironbug_model = load_ironbug_model(
        garden_root_path,
        ironbug_model_target=ironbug_model_target,
    )
    hvac_room2ds = _dragonfly_room2ds_for_hvac_specification(
        host_room2ds,
        host_type,
        conditioned_only=conditioned_only,
    )
    room_identifiers = [room.identifier for room in hvac_room2ds]
    hvac_identifier = _detailed_hvac_identifier(
        detailed_hvac_identifier=detailed_hvac_identifier,
        ironbug_model=ironbug_model,
        ironbug_model_target=resolved_ironbug_target,
    )
    hvac = create_detailed_hvac_from_ironbug_model(
        ironbug_model,
        identifier=hvac_identifier,
        room_identifiers=room_identifiers,
    )
    if host_type == "room2d":
        host.properties.energy.hvac = hvac
    else:
        host.properties.energy.set_all_room_2d_hvac(
            hvac,
            conditioned_only=conditioned_only,
        )

    affected_room2ds = [
        room
        for room in host_room2ds
        if _identifier(getattr(room.properties.energy, "hvac", None)) is not None
    ]
    affected_room2d_identifiers = [room.identifier for room in affected_room2ds]
    assigned_hvac_identifiers = sorted(
        {
            _identifier(getattr(room.properties.energy, "hvac", None))
            for room in affected_room2ds
        }
        - {None}
    )

    updated_model_target, persisted_path = save_dragonfly_model(
        garden_root_path,
        manifest,
        dragonfly_model,
        name=str(resolved_dragonfly_target["model_identifier"]),
        included_prop=["energy", "radiance", "uwg"],
        set_base=manifest.base_dragonfly_model == resolved_dragonfly_target,
    )
    hvac_target = _dragonfly_detailed_hvac_target(
        ironbug_model_target=resolved_ironbug_target,
        dragonfly_model_target=updated_model_target,
        host_target=normalized_host_target,
        hvac_identifier=assigned_hvac_identifiers[0]
        if len(assigned_hvac_identifiers) == 1
        else hvac.identifier,
    )
    summary = {
        "ironbug_model_target": resolved_ironbug_target,
        "dragonfly_model_target": updated_model_target,
        "host_target": normalized_host_target,
        "host_type": host_type,
        "identifier": normalized_host_target["object_identifier"],
        "updated_fields": ["hvac"],
        "detailed_hvac_identifier": hvac.identifier,
        "assigned_hvac_identifiers": assigned_hvac_identifiers,
        "affected_room2d_count": len(affected_room2d_identifiers),
        "affected_room2d_identifiers": affected_room2d_identifiers,
        "conditioned_only": bool(conditioned_only),
        "setpoint_managed_by": "program",
        "energy_ready": bool(affected_room2d_identifiers),
        "simulation_ready": False,
        "simulation_readiness_issues": [
            {
                "code": "setpoint-managed-by-program",
                "message": (
                    "Dragonfly-native Ironbug HVAC assignment only sets HVAC; "
                    "Room2D setpoints are managed through ProgramType."
                ),
            }
        ],
        "simulation_readiness_issue_count": 1,
    }
    receipt = make_persistence_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        model_target=updated_model_target,
        persisted_path=persisted_path,
        change_summary={
            "operation": "apply_ironbug_detailed_hvac_to_dragonfly_energy_properties",
            "ironbug_model_target": resolved_ironbug_target,
            "host_target": normalized_host_target,
            "updated_fields": ["hvac"],
            "conditioned_only": bool(conditioned_only),
            "affected_room2d_count": len(affected_room2d_identifiers),
        },
    )
    return {
        "target": hvac_target,
        "detailed_hvac_target": hvac_target,
        "updated_model_target": updated_model_target,
        "dragonfly_model_target": updated_model_target,
        "host_target": normalized_host_target,
        "summary_view": summary,
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=(
                "Applied Ironbug DetailedHVAC to Dragonfly "
                f"{host_type}: {normalized_host_target['object_identifier']}."
            ),
            details={
                "affected_room2d_count": len(affected_room2d_identifiers),
                "conditioned_only": bool(conditioned_only),
                "simulation_ready": False,
            },
        ),
    }


def _ensure_ironbug_hvac_system(model: IB_Model) -> None:
    if model.HVACSystem is None:
        raise ValueError("Ironbug model has no HVACSystem.")


def _plant_loop_count(model: IB_Model) -> int:
    return len(_plant_loops(model))


def _plant_loop_identifiers(model: IB_Model) -> list[str]:
    return [
        str(identifier)
        for loop in _plant_loops(model)
        if (identifier := getattr(loop, "identifier", None))
    ]


def _plant_loops(model: IB_Model) -> list[Any]:
    hvac_system = model.HVACSystem
    if hvac_system is None:
        return []
    return list(getattr(hvac_system, "PlantLoops", None) or [])


def _air_loops(model: IB_Model) -> list[Any]:
    hvac_system = model.HVACSystem
    if hvac_system is None:
        return []
    return list(getattr(hvac_system, "AirLoops", None) or [])


def _variable_refrigerant_flows(model: IB_Model) -> list[Any]:
    hvac_system = model.HVACSystem
    if hvac_system is None:
        return []
    return list(getattr(hvac_system, "VariableRefrigerantFlows", None) or [])


def _component_source_classes(model: IB_Model) -> set[str]:
    classes: set[str] = set()
    for record in _component_library(model).values():
        if isinstance(record, dict) and record.get("source_class"):
            classes.add(str(record["source_class"]))
    return classes


def _is_room_serving_source_class(source_class: str) -> bool:
    return (
        source_class in ROOM_SERVING_CLASSES
        or source_class.startswith(ROOM_SERVING_PREFIXES)
    )


def _requires_explicit_thermal_zone(
    model: IB_Model,
    *,
    air_loops: list[Any],
    plant_loops: list[Any],
    vrfs: list[Any],
) -> bool:
    if air_loops or plant_loops or vrfs or model.ElectricLoadCenter is not None:
        return True
    return any(
        _is_room_serving_source_class(source_class)
        for source_class in _component_source_classes(model)
    )


def _ensure_explicit_room_linked_thermal_zones(
    model: IB_Model,
    *,
    air_loops: list[Any],
    plant_loops: list[Any],
    vrfs: list[Any],
) -> None:
    if _component_thermal_zones(model):
        return
    if not _requires_explicit_thermal_zone(
        model,
        air_loops=air_loops,
        plant_loops=plant_loops,
        vrfs=vrfs,
    ):
        return
    raise ValueError(
        "Ironbug DetailedHVAC models with plant loops, air loops, VRF systems, "
        "ElectricLoadCenter, air terminals, or zone equipment require explicit "
        "room-linked "
        "IB_ThermalZone objects before application. Create one IB_ThermalZone "
        "per Honeybee Room with matching identifier/Name and bind the zone "
        "equipment or air terminal to that thermal zone."
    )


def _component_thermal_zones(model: IB_Model) -> list[Any]:
    zones: list[Any] = []
    for record in _component_library(model).values():
        if not isinstance(record, dict):
            continue
        if record.get("source_class") != "IB_ThermalZone":
            continue
        data = record.get("data")
        if isinstance(data, dict):
            zones.append(_hydrate_source_object(dict(data)))
        elif data is not None:
            zones.append(data)
    return zones


def _ironbug_console_spec_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        if not _is_ironbug_source_model(value):
            raise TypeError(
                "Ironbug Console specification export only accepts source-backed "
                f"Ironbug models, not {value.__class__.__name__}."
            )
        data = value.model_dump(by_alias=True, exclude_none=True)
        for field_name, field_info in value.__class__.model_fields.items():
            key = field_info.serialization_alias or field_info.alias or field_name
            if key in data:
                data[key] = _ironbug_console_spec_value(getattr(value, field_name))
        for key, item in (getattr(value, "__pydantic_extra__", None) or {}).items():
            if key in data:
                data[key] = _ironbug_console_spec_value(item)
        if isinstance(data.get("CustomAttributes"), dict):
            data["CustomAttributes"] = _custom_attributes_with_tracking_id(
                data["CustomAttributes"],
                getattr(value, "identifier", None),
            )
            if getattr(value.__class__, "SOURCE_CLASS", None) == "IB_ThermalZone":
                data["CustomAttributes"] = _thermal_zone_name_attributes(
                    data["CustomAttributes"],
                    getattr(value, "identifier", None),
                )
                data.setdefault(
                    "SizingZone",
                    _with_console_type({}, ironbug_hvac.IB_SizingZone),
                )
            data["CustomAttributes"] = _console_custom_attributes(
                data["CustomAttributes"]
            )
        data = _move_source_properties_to_ib_properties(data, value.__class__)
        data = _wrap_explicit_ib_properties(data)
        return _with_console_type(data, value.__class__)
    if isinstance(value, list):
        return [_ironbug_console_spec_value(item) for item in value]
    if isinstance(value, tuple):
        return [_ironbug_console_spec_value(item) for item in value]
    if isinstance(value, dict):
        source_type = value.get("type")
        if isinstance(source_type, str) and hasattr(ironbug_hvac, source_type):
            source_cls = getattr(ironbug_hvac, source_type)
            if isinstance(source_cls, type):
                return _source_dict_console_spec_value(value, source_cls)
        return {
            key: _ironbug_console_spec_value(item)
            for key, item in value.items()
            if item is not None
        }
    return value


def _source_dict_console_spec_value(
    value: dict[str, Any],
    source_cls: type[Any],
) -> dict[str, Any]:
    source_type = str(value.get("type") or "")
    data = {
        key: _ironbug_console_spec_value(item)
        for key, item in value.items()
        if key != "type" and item is not None
    }
    if isinstance(data.get("CustomAttributes"), dict):
        data["CustomAttributes"] = _custom_attributes_with_tracking_id(
            data["CustomAttributes"],
            value.get("identifier"),
        )
        if source_type == "IB_ThermalZone":
            data["CustomAttributes"] = _thermal_zone_name_attributes(
                data["CustomAttributes"],
                value.get("identifier"),
            )
            data.setdefault(
                "SizingZone",
                _with_console_type({}, ironbug_hvac.IB_SizingZone),
            )
        data["CustomAttributes"] = _console_custom_attributes(data["CustomAttributes"])
    data = _move_source_properties_to_ib_properties(data, source_cls)
    data = _wrap_explicit_ib_properties(data)
    return _with_console_type(data, source_cls)


def _wrap_explicit_ib_properties(data: dict[str, Any]) -> dict[str, Any]:
    ib_properties = data.get("IBProperties")
    if not isinstance(ib_properties, dict) or not ib_properties:
        return data
    data["IBProperties"] = _with_console_type(
        ib_properties,
        ironbug_hvac.IB_PropArgumentSet,
    )
    return data


def _custom_attributes_with_tracking_id(
    attributes: dict[str, Any],
    identifier: Any,
) -> dict[str, Any]:
    if not identifier or "Comment" in attributes:
        return attributes
    return {
        **attributes,
        "Comment": f"TrackingID:#[{identifier}]",
    }


def _thermal_zone_name_attributes(
    attributes: dict[str, Any],
    identifier: Any,
) -> dict[str, Any]:
    if "Name" in attributes or not identifier:
        return attributes
    return {**attributes, "Name": str(identifier)}


def _console_custom_attributes(attributes: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for key, value in attributes.items():
        if value is None:
            continue
        console_value = _console_field_value(value)
        result.append(
            {
                "Field": {
                    "FullName": key,
                    "DataTypeName": _console_field_data_type_name(console_value),
                },
                "Value": console_value,
            }
        )
    return result


def _console_field_data_type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "System.Boolean"
    if isinstance(value, int | float):
        return "System.Double"
    return "System.String"


def _console_field_value(value: Any) -> Any:
    if isinstance(value, str) and value.strip().lower() == "autosize":
        return -9999
    return value


def _move_source_properties_to_ib_properties(
    data: dict[str, Any],
    source_cls: type[Any],
) -> dict[str, Any]:
    property_names = set(getattr(source_cls, "SOURCE_PROPERTIES", ()))
    data_member_names = set(getattr(source_cls, "SOURCE_DATA_MEMBERS", ()))
    ib_property_names = property_names - data_member_names
    moved = {
        key: data.pop(key)
        for key in list(data)
        if key in ib_property_names and data.get(key) is not None
    }
    if not moved:
        return data
    ib_properties = dict(data.get("IBProperties") or {})
    ib_properties.update(moved)
    data["IBProperties"] = _with_console_type(
        ib_properties,
        ironbug_hvac.IB_PropArgumentSet,
    )
    return data


def _is_ironbug_source_model(value: BaseModel) -> bool:
    source_path = getattr(value.__class__, "SOURCE_PATH", "")
    return bool(
        getattr(value.__class__, "SOURCE_CLASS", None)
        and getattr(value.__class__, "SOURCE_NAMESPACE", None)
        and str(source_path).startswith("src/Ironbug.")
    )


def _with_console_type(data: dict[str, Any], source_cls: type[Any]) -> dict[str, Any]:
    source_class = getattr(source_cls, "SOURCE_CLASS", None)
    if not source_class:
        return data
    source_namespace = getattr(source_cls, "SOURCE_NAMESPACE", None)
    data.pop("type", None)
    if source_namespace:
        assembly_name = _console_assembly_name(str(source_namespace))
        data["$type"] = f"{source_namespace}.{source_class}, {assembly_name}"
    else:
        data["$type"] = str(source_class)
    return data


def _console_assembly_name(source_namespace: str) -> str:
    if source_namespace.startswith("Ironbug.HVAC."):
        return "Ironbug.HVAC"
    return source_namespace


def _operation_scheme_status(model: IB_Model) -> dict[str, Any]:
    operation_schemes = [
        operation_scheme
        for loop in _plant_loops(model)
        if (operation_scheme := getattr(loop, "OperationScheme", None)) is not None
    ]
    source_classes = sorted(
        {
            getattr(operation_scheme, "SOURCE_CLASS", operation_scheme.__class__.__name__)
            for operation_scheme in operation_schemes
        }
    )
    binding_count = sum(
        len(_operation_scheme_equipment_items(operation_scheme))
        for operation_scheme in operation_schemes
    )
    status = "ready" if binding_count else "blocked"
    return {
        "status": status,
        "source_operation_scheme_classes": source_classes,
        "source_method_dependency": "IB_PlantEquipmentOperationSchemeBase.AddEquipment",
        "translated_equipment_binding_count": binding_count,
        "message": (
            "Operation schemes include source-backed equipment limit/object bindings."
            if binding_count
            else (
                "Operation schemes are source-backed, but equipment limit/object pairs "
                "are missing."
            )
        ),
    }


def _operation_scheme_equipment_items(operation_scheme: Any) -> list[Any]:
    ib_properties = getattr(operation_scheme, "IBProperties", None) or {}
    if isinstance(ib_properties, dict):
        items = ib_properties.get("_equipments")
        if isinstance(items, list):
            return items
    extra = getattr(operation_scheme, "__pydantic_extra__", None) or {}
    if isinstance(extra, dict):
        items = extra.get("_equipments")
        if isinstance(items, list):
            return items
    return []


def _normalize_room_identifiers(room_identifiers: list[str]) -> list[str]:
    normalized = [str(identifier).strip() for identifier in room_identifiers]
    normalized = [identifier for identifier in normalized if identifier]
    if not normalized:
        raise ValueError("DetailedHVAC requires at least one Honeybee Room identifier.")
    duplicates = sorted(
        identifier for identifier in set(normalized) if normalized.count(identifier) > 1
    )
    if duplicates:
        raise ValueError(f"Duplicate Honeybee Room identifiers: {', '.join(duplicates)}")
    return normalized


def _detailed_hvac_identifier(
    *,
    detailed_hvac_identifier: str | None,
    ironbug_model: IB_Model,
    ironbug_model_target: dict[str, Any],
) -> str:
    if detailed_hvac_identifier:
        return detailed_hvac_identifier
    model_identifier = ironbug_model.identifier or str(ironbug_model_target["id"])
    return f"{model_identifier}_detailed_hvac"


def _resolve_selected_rooms(
    model: Model,
    model_target: dict[str, Any],
    *,
    room_targets: list[dict[str, Any]] | None,
    room_identifiers: list[str] | None,
    apply_to_all_rooms: bool,
) -> list[Room]:
    selection_modes = sum(
        [
            bool(room_targets),
            bool(room_identifiers),
            bool(apply_to_all_rooms),
        ]
    )
    if selection_modes == 0:
        raise ValueError(
            "Select Honeybee Rooms with room_targets, room_identifiers, "
            "or apply_to_all_rooms=true."
        )
    if selection_modes > 1:
        raise ValueError(
            "Pass only one room selection mode: room_targets, room_identifiers, "
            "or apply_to_all_rooms=true."
        )
    if apply_to_all_rooms:
        rooms = list(model.rooms)
    elif room_targets:
        rooms = [
            _room_from_target(model, model_target, room_target)
            for room_target in room_targets
        ]
    else:
        wanted = _normalize_room_identifiers(room_identifiers or [])
        rooms_by_id = {room.identifier: room for room in model.rooms}
        missing = [identifier for identifier in wanted if identifier not in rooms_by_id]
        if missing:
            raise ValueError(f"Honeybee Room identifiers not found: {', '.join(missing)}")
        rooms = [rooms_by_id[identifier] for identifier in wanted]
    identifiers = [room.identifier for room in rooms]
    if not identifiers:
        raise ValueError("Honeybee model has no selected Rooms.")
    _normalize_room_identifiers(identifiers)
    return rooms


def _room_from_target(
    model: Model,
    model_target: dict[str, Any],
    room_target: dict[str, Any],
) -> Room:
    target = normalize_honeybee_object_target(room_target)
    if target["object_type"] != "room":
        raise ValueError("room_targets must identify Honeybee Room objects.")
    if target.get("garden_id") != model_target.get("garden_id"):
        raise ValueError("Selected Room target does not belong to the Honeybee model.")
    if target["model_identifier"] != model_target["model_identifier"]:
        raise ValueError("Selected Room target does not belong to the Honeybee model.")
    room = find_object(model, target)
    if not isinstance(room, Room):
        raise ValueError("room_targets must identify Honeybee Room objects.")
    return room


def _check_detailed_hvac_rooms(model: Model) -> list[dict[str, Any]]:
    issues = model.properties.energy.check_detailed_hvac_rooms(
        raise_exception=False,
        detailed=True,
    )
    return [issue for issue in issues if isinstance(issue, dict)]


def _room_reference_issues(validation_issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _issues_with_codes(validation_issues, ROOM_REFERENCE_ERROR_CODES)


def _simulation_readiness_issues(
    validation_issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return _issues_with_codes(validation_issues, SIMULATION_READINESS_ERROR_CODES)


def _ironbug_graph_simulation_readiness_issues(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
) -> list[dict[str, Any]]:
    from garden.ironbug_core.readiness import validate_ironbug_energyplus_readiness

    readiness = validate_ironbug_energyplus_readiness(
        garden_root=garden_root,
        ironbug_model_target=ironbug_model_target,
    )
    return [
        {
            "code": str(issue.get("code") or ""),
            "message": str(issue.get("message") or issue.get("code") or ""),
            "source_class": issue.get("source_class"),
            "identifier": issue.get("identifier"),
            "repair_tool": issue.get("repair_tool"),
        }
        for issue in readiness.get("report", {}).get("issues", [])
        if issue.get("severity") == "error"
    ]


def _ironbug_thermal_zone_room_binding_issues(
    *,
    ironbug_model: IB_Model,
    selected_room_identifiers: list[str],
) -> list[dict[str, Any]]:
    selected = set(selected_room_identifiers)
    room_serving_zone_names: list[str] = []
    for zone in _component_thermal_zones(ironbug_model):
        if getattr(zone, "AirTerminal", None) is None and not (
            getattr(zone, "ZoneEquipments", None) or []
        ):
            continue
        room_serving_zone_names.append(_thermal_zone_room_name(zone))
    if not room_serving_zone_names:
        return []
    unmatched = sorted(name for name in room_serving_zone_names if name not in selected)
    if not unmatched:
        return []
    missing = sorted(selected.difference(room_serving_zone_names))
    return [
        {
            "code": "ironbug_thermal_zone_room_binding_mismatch",
            "message": (
                "Room-serving IB_ThermalZone Name/identifier values must match "
                "the selected Honeybee Room identifiers before EnergyPlus. "
                f"Unmatched Ironbug zones: {', '.join(unmatched)}. "
                f"Missing selected rooms: {', '.join(missing) if missing else 'none'}."
            ),
            "source_class": "IB_ThermalZone",
            "identifier": ", ".join(unmatched),
            "repair_tool": "detailed_hvac_thermal_zone",
        }
    ]


def _thermal_zone_room_name(zone: Any) -> str:
    attributes = getattr(zone, "CustomAttributes", None) or {}
    if isinstance(attributes, dict):
        name = attributes.get("Name")
        if name:
            return str(name)
    return str(getattr(zone, "identifier", ""))


def _issues_with_codes(
    validation_issues: list[dict[str, Any]],
    codes: set[str],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for issue in validation_issues:
        code = str(issue.get("code") or "")
        if code not in codes:
            continue
        issues.append(
            {
                "code": code,
                "message": str(issue.get("message") or issue.get("error_type") or code),
                "error_type": issue.get("error_type"),
                "element_type": issue.get("element_type"),
                "element_id": issue.get("element_id"),
            }
        )
    return issues


def _detailed_hvac_target(
    *,
    ironbug_model_target: dict[str, Any],
    hvac: DetailedHVAC,
    honeybee_model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    target: dict[str, Any] = {
        "target_type": "ironbug_detailed_hvac",
        "id": hvac.identifier,
        "identifier": hvac.identifier,
        "domain": "ironbug",
        "source": "honeybee_energy.DetailedHVAC",
        "ironbug_model_target": ironbug_model_target,
    }
    if "garden_id" in ironbug_model_target:
        target["garden_id"] = ironbug_model_target["garden_id"]
    if honeybee_model_target is not None:
        target["honeybee_model_target"] = honeybee_model_target
    return target


def _dragonfly_detailed_hvac_target(
    *,
    ironbug_model_target: dict[str, Any],
    dragonfly_model_target: dict[str, Any],
    host_target: dict[str, Any],
    hvac_identifier: str,
) -> dict[str, Any]:
    return {
        "target_type": "ironbug_detailed_hvac",
        "id": hvac_identifier,
        "identifier": hvac_identifier,
        "domain": "ironbug",
        "source": "dragonfly_energy.Room2DEnergyProperties.hvac",
        "garden_id": dragonfly_model_target.get("garden_id")
        or ironbug_model_target.get("garden_id"),
        "ironbug_model_target": ironbug_model_target,
        "dragonfly_model_target": dragonfly_model_target,
        "host_target": host_target,
    }


def _detailed_hvac_summary(
    *,
    hvac: DetailedHVAC,
    ironbug_model_target: dict[str, Any],
    honeybee_model_target: dict[str, Any] | None,
    detailed_hvac_room_reference_valid: bool | None,
    energy_ready: bool,
    validation_status: str,
    blocking_issues: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "ironbug_model_target": ironbug_model_target,
        "honeybee_model_target": honeybee_model_target,
        "detailed_hvac_identifier": hvac.identifier,
        "thermal_zone_count": len(hvac.thermal_zones),
        "thermal_zones": list(hvac.thermal_zones),
        "selected_room_count": len(hvac.thermal_zones),
        "design_type": hvac.design_type,
        "air_loop_count": hvac.air_loop_count,
        "detailed_hvac_room_reference_valid": detailed_hvac_room_reference_valid,
        "energy_ready": energy_ready,
        "simulation_ready": False,
        "simulation_readiness_issues": [],
        "simulation_readiness_issue_count": 0,
        "validation_status": validation_status,
        "blocking_issues": blocking_issues,
    }


def _dragonfly_host_from_target(model: Any, target: dict[str, Any]) -> Any:
    object_type = target["object_type"]
    identifier = target["object_identifier"]
    if object_type == "room2d":
        return _one_dragonfly_object(
            model.room_2ds_by_identifier([identifier]),
            identifier,
            "Room2D",
        )
    if object_type == "story":
        return _one_dragonfly_object(
            model.stories_by_identifier([identifier]),
            identifier,
            "Story",
        )
    if object_type == "building":
        return _one_dragonfly_object(
            model.buildings_by_identifier([identifier]),
            identifier,
            "Building",
        )
    raise ValueError(f"Unsupported Dragonfly DetailedHVAC host type: {object_type}.")


def _ensure_dragonfly_host_belongs_to_model(
    host_target: dict[str, Any],
    model_target: dict[str, Any],
) -> None:
    if host_target.get("garden_id") not in {None, model_target.get("garden_id")}:
        raise ValueError(
            "Selected Dragonfly host target does not belong to the Dragonfly model."
        )
    if host_target.get("model_identifier") != model_target.get("model_identifier"):
        raise ValueError(
            "Selected Dragonfly host target does not belong to the Dragonfly model."
        )


def _dragonfly_room2ds_for_host(host: Any, host_type: str) -> list[Any]:
    if host_type == "room2d":
        return [host]
    if host_type == "story":
        return list(host.room_2ds)
    if host_type == "building":
        return list(host.unique_room_2ds)
    raise ValueError(f"Unsupported Dragonfly DetailedHVAC host type: {host_type}.")


def _dragonfly_room2ds_for_hvac_specification(
    room2ds: list[Any],
    host_type: str,
    *,
    conditioned_only: bool,
) -> list[Any]:
    if host_type == "room2d" or not conditioned_only:
        return room2ds
    conditioned_room2ds = [
        room for room in room2ds if room.properties.energy.is_conditioned
    ]
    if not conditioned_room2ds:
        raise ValueError(
            "Dragonfly HVAC host has no conditioned Room2Ds. Set "
            "conditioned_only=false to assign HVAC to all child Room2Ds."
        )
    return conditioned_room2ds


def _one_dragonfly_object(objects: list[Any], identifier: str, object_type: str) -> Any:
    if len(objects) == 1:
        return objects[0]
    if not objects:
        raise ValueError(f"Dragonfly {object_type} not found: {identifier}.")
    raise ValueError(f"Dragonfly {object_type} identifier is ambiguous: {identifier}.")


def _identifier(value: Any) -> str | None:
    identifier = getattr(value, "identifier", None)
    return str(identifier) if identifier else None
