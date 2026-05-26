"""Garden services for Ironbug-Core ibjson models."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ironbug.hvac import IB_HVACSystem, IB_Model

from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report
from garden.manifest import GardenManifest
from garden.ironbug_core.model_io import (
    load_ironbug_model,
    save_ironbug_model,
)
from garden.ironbug_core.assembly import component_library_matches
from garden.ironbug_core.targets import make_ironbug_model_object_target


def _garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def _display_name(model: IB_Model) -> str | None:
    return model.display_name or None


def _model_identifier(model: IB_Model, fallback: str) -> str:
    return model.identifier or fallback


def _hvac_summary(hvac: IB_HVACSystem | None) -> dict[str, Any]:
    if hvac is None:
        return {
            "exists": False,
            "air_loop_count": 0,
            "plant_loop_count": 0,
            "vrf_count": 0,
        }
    return {
        "exists": True,
        "source_class": hvac.SOURCE_CLASS,
        "air_loop_count": len(hvac.AirLoops or []),
        "plant_loop_count": len(hvac.PlantLoops or []),
        "vrf_count": len(hvac.VariableRefrigerantFlows or []),
    }


def _model_summary(
    model: IB_Model,
    target: dict[str, Any],
) -> dict[str, Any]:
    return {
        "model": {
            "identifier": _model_identifier(model, str(target["id"])),
            "display_name": _display_name(model),
            "root_type": model.type,
            "target": target,
        },
        "hvac_system": _hvac_summary(model.HVACSystem),
        "energy_management_system": {
            "exists": model.EnergyManagementSystem is not None,
        },
        "electric_load_center": {
            "exists": model.ElectricLoadCenter is not None,
        },
    }


def _validation_issue(message: str, *, issue_type: str = "validation_error") -> dict[str, Any]:
    return {
        "type": issue_type,
        "message": message,
    }


def _is_ibjson_validation_error(exc: ValueError) -> bool:
    return str(exc).startswith("ibjson ")


def create_ironbug_model(
    *,
    garden_root: str,
    identifier: str,
    display_name: str | None = None,
    include_hvac_system: bool = True,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create and persist an Ironbug-Core IB_Model as Garden ibjson."""

    garden_root_path = _garden_root(garden_root)
    manifest = GardenManifest.read(garden_root_path)
    model = IB_Model(
        identifier=identifier,
        display_name=display_name,
        HVACSystem=IB_HVACSystem(
            AirLoops=[],
            PlantLoops=[],
            VariableRefrigerantFlows=[],
        )
        if include_hvac_system
        else None,
    )
    target, persisted_path = save_ironbug_model(
        garden_root_path,
        manifest,
        model,
        identifier=identifier,
        overwrite=overwrite,
    )
    receipt = make_persistence_receipt(
        status="persisted",
        garden_id=manifest.garden_id,
        model_target=target,
        persisted_path=persisted_path,
        change_summary={
            "operation": "create_ironbug_model",
            "target": target,
        },
    )
    return {
        "target": target,
        "model_target": target,
        "summary_view": _model_summary(model, target),
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=f"Created Ironbug model: {identifier}",
        ),
    }


def validate_ironbug_model(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any] | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    """Validate a Garden-managed Ironbug ibjson model."""

    garden_root_path = _garden_root(garden_root)
    try:
        _, target, _, model = load_ironbug_model(
            garden_root_path,
            ironbug_model_target=ironbug_model_target,
            path=path,
        )
    except ValidationError as exc:
        issues = [_validation_issue(str(exc))]
        return {
            "is_valid": False,
            "valid": False,
            "target": ironbug_model_target or {},
            "issues": issues,
            "summary_view": {
                "is_valid": False,
                "issue_count": len(issues),
            },
            "report": make_report(
                status="invalid",
                message="Ironbug model failed validation.",
                details={"issue_count": len(issues)},
            ),
        }
    except ValueError as exc:
        if not _is_ibjson_validation_error(exc):
            raise
        issues = [_validation_issue(str(exc))]
        return {
            "is_valid": False,
            "valid": False,
            "target": ironbug_model_target or {},
            "issues": issues,
            "summary_view": {
                "is_valid": False,
                "issue_count": len(issues),
            },
            "report": make_report(
                status="invalid",
                message="Ironbug model failed validation.",
                details={"issue_count": len(issues)},
            ),
        }

    return {
        "is_valid": True,
        "valid": True,
        "target": target,
        "issues": [],
        "summary_view": {
            **_model_summary(model, target),
            "is_valid": True,
            "issue_count": 0,
        },
        "report": make_report(
            status="ok",
            message=f"Ironbug model is valid: {target['id']}",
        ),
    }


def _query_matches(value: str, query: str | None) -> bool:
    if not query:
        return True
    return query.strip().lower() in value.lower()


def _match(
    *,
    model_target: dict[str, Any],
    object_type: str,
    object_path: str,
    source_class: str,
    identifier: str,
    summary_view: dict[str, Any],
) -> dict[str, Any]:
    target = make_ironbug_model_object_target(
        model_target=model_target,
        object_type=object_type,
        object_path=object_path,
        source_class=source_class,
        identifier=identifier,
    )
    return {
        "object_type": object_type,
        "identifier": identifier,
        "source_class": source_class,
        "target": target,
        "summary_view": summary_view,
    }


def search_ironbug_model_objects(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    object_type: str = "all",
    identifier: str | None = None,
    query: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Search compact objects inside a Garden-managed Ironbug model."""

    garden_root_path = _garden_root(garden_root)
    _, target, _, model = load_ironbug_model(
        garden_root_path,
        ironbug_model_target=ironbug_model_target,
    )
    normalized_type = object_type.strip().lower().replace("-", "_").replace(" ", "_")
    allowed = {
        "all",
        "model",
        "hvac_system",
        "air_loop",
        "plant_loop",
        "component",
        "vrf",
        "energy_management_system",
        "electric_load_center",
    }
    if normalized_type not in allowed:
        raise ValueError(f"Unsupported Ironbug object_type: {object_type}")

    model_id = _model_identifier(model, str(target["id"]))
    candidates: list[dict[str, Any]] = [
        _match(
            model_target=target,
            object_type="model",
            object_path="",
            source_class=model.SOURCE_CLASS,
            identifier=model_id,
            summary_view=_model_summary(model, target),
        )
    ]
    if model.HVACSystem is not None:
        candidates.append(
            _match(
                model_target=target,
                object_type="hvac_system",
                object_path="HVACSystem",
                source_class=model.HVACSystem.SOURCE_CLASS,
                identifier=f"{model_id}/HVACSystem",
                summary_view=_hvac_summary(model.HVACSystem),
            )
        )
        for index, air_loop in enumerate(model.HVACSystem.AirLoops or []):
            candidates.append(
                _match(
                    model_target=target,
                    object_type="air_loop",
                    object_path=f"HVACSystem.AirLoops[{index}]",
                    source_class=air_loop.SOURCE_CLASS,
                    identifier=f"{model_id}/HVACSystem/AirLoops/{index}",
                    summary_view={"source_class": air_loop.SOURCE_CLASS},
                )
            )
        for index, plant_loop in enumerate(model.HVACSystem.PlantLoops or []):
            candidates.append(
                _match(
                    model_target=target,
                    object_type="plant_loop",
                    object_path=f"HVACSystem.PlantLoops[{index}]",
                    source_class=plant_loop.SOURCE_CLASS,
                    identifier=f"{model_id}/HVACSystem/PlantLoops/{index}",
                    summary_view={"source_class": plant_loop.SOURCE_CLASS},
                )
            )
        candidates.extend(component_library_matches(model, target))
        for index, vrf in enumerate(model.HVACSystem.VariableRefrigerantFlows or []):
            candidates.append(
                _match(
                    model_target=target,
                    object_type="vrf",
                    object_path=f"HVACSystem.VariableRefrigerantFlows[{index}]",
                    source_class=vrf.SOURCE_CLASS,
                    identifier=f"{model_id}/HVACSystem/VariableRefrigerantFlows/{index}",
                    summary_view={"source_class": vrf.SOURCE_CLASS},
                )
            )
    if model.EnergyManagementSystem is not None:
        candidates.append(
            _match(
                model_target=target,
                object_type="energy_management_system",
                object_path="EnergyManagementSystem",
                source_class=model.EnergyManagementSystem.SOURCE_CLASS,
                identifier=f"{model_id}/EnergyManagementSystem",
                summary_view={"exists": True},
            )
        )
    if model.ElectricLoadCenter is not None:
        candidates.append(
            _match(
                model_target=target,
                object_type="electric_load_center",
                object_path="ElectricLoadCenter",
                source_class=model.ElectricLoadCenter.SOURCE_CLASS,
                identifier=f"{model_id}/ElectricLoadCenter",
                summary_view={"exists": True},
            )
        )

    matches = [
        item
        for item in candidates
        if (normalized_type == "all" or item["object_type"] == normalized_type)
        and (identifier is None or item["identifier"] == identifier)
        and _query_matches(item["identifier"], query)
    ]
    if limit is not None:
        matches = matches[: max(int(limit), 0)]
    return {
        "matches": matches,
        "summary_view": {
            "model_target": target,
            "object_type": normalized_type,
            "count": len(matches),
        },
        "report": make_report(
            status="ok",
            message=f"Found {len(matches)} Ironbug object(s).",
        ),
    }


def validate_ironbug_energy_readiness(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    honeybee_model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check whether an Ironbug model is ready for a future Energy bridge."""

    garden_root_path = _garden_root(garden_root)
    _, target, _, model = load_ironbug_model(
        garden_root_path,
        ironbug_model_target=ironbug_model_target,
    )
    blocking_issues = [
        {
            "code": "ironbug_openstudio_translator_missing",
            "message": (
                "Ironbug-Core has no source-backed OpenStudio translator yet, "
                "so Ironbug HVAC cannot be applied to an Energy simulation model."
            ),
        }
    ]
    if model.HVACSystem is None:
        blocking_issues.append(
            {
                "code": "ironbug_hvac_system_missing",
                "message": "Ironbug model has no HVACSystem.",
            }
        )
    return {
        "ready": False,
        "target": target,
        "blocking_issues": blocking_issues,
        "warnings": [],
        "summary_view": {
            "ironbug_model": _model_summary(model, target)["model"],
            "hvac_system": _hvac_summary(model.HVACSystem),
            "honeybee_model_target_present": honeybee_model_target is not None,
            "energy_bridge": {
                "status": "not_ready",
                "reason": "Ironbug-Core has no source-backed OpenStudio translator yet.",
            },
        },
        "report": make_report(
            status="blocked",
            message="Ironbug model is not ready for Energy simulation.",
            details={"blocking_issue_count": len(blocking_issues)},
        ),
    }
