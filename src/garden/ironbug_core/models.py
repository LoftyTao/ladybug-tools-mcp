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
from garden.ironbug_core.assembly import (
    _component_library,
    _component_target,
    _save_update,
)
from garden.ironbug_core.object_references import component_reference_graph
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
        ),
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
    component_graph = component_reference_graph(model)
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
    candidates.extend(
        {
            "object_type": "component",
            "identifier": identifier,
            "component_type": record.component_type,
            "source_class": record.source_class,
            "target": _component_target(
                model_target=target,
                identifier=identifier,
                source_class=record.source_class,
            ),
            "summary_view": component_graph.summary(identifier),
        }
        for identifier, record in component_graph.records.items()
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


def _normalize_component_target(
    value: Any,
    *,
    model_target: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(
            "Ironbug component operation requires a typed component target; "
            "pass matches[i].target, not an identifier string."
        )
    if value.get("target_type") != "ironbug_model_object":
        raise ValueError(
            "Ironbug component operation requires target_type "
            "'ironbug_model_object'."
        )
    if value.get("domain") != "ironbug" or value.get("object_type") != "component":
        raise ValueError("Ironbug component operation requires object_type='component'.")
    identifier = value.get("identifier")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("Ironbug component target requires a non-empty identifier.")
    nested_model_target = value.get("model_target")
    if isinstance(nested_model_target, dict):
        if nested_model_target.get("id") != model_target.get("id"):
            raise ValueError("Ironbug component target belongs to a different model.")
        if nested_model_target.get("garden_id") != model_target.get("garden_id"):
            raise ValueError("Ironbug component target belongs to a different Garden.")
    return dict(value)


def remove_ironbug_component(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    target: dict[str, Any] | None = None,
    cleanup_orphans: bool = False,
) -> dict[str, Any]:
    """Safely remove one unreferenced component or clean all orphan subgraphs."""

    garden_root_path = _garden_root(garden_root)
    manifest, model_target, _, model = load_ironbug_model(
        garden_root_path,
        ironbug_model_target=ironbug_model_target,
    )
    if cleanup_orphans and target is not None:
        raise ValueError("Pass either target or cleanup_orphans=true, not both.")
    if not cleanup_orphans and target is None:
        raise ValueError("Pass a typed component target or cleanup_orphans=true.")

    graph = component_reference_graph(model)
    if cleanup_orphans:
        removed_identifiers = sorted(graph.orphan_ids)
    else:
        component_target = _normalize_component_target(target, model_target=model_target)
        identifier = component_target["identifier"]
        if identifier not in graph.records:
            raise ValueError(f"Ironbug component not found: {identifier}")
        owners = [
            owner
            for owner in graph.reference_owners.get(identifier, ())
            if not (owner.object_type == "component" and owner.identifier == identifier)
        ]
        if owners:
            owner_labels = ", ".join(
                f"{owner.object_type}/{owner.identifier}" for owner in owners
            )
            raise ValueError(
                f"Cannot remove referenced Ironbug component: {identifier}; "
                f"referenced by {owner_labels}."
            )
        if identifier in graph.active_ids:
            raise ValueError(
                f"Cannot remove active Ironbug component: {identifier}; "
                "it belongs to an active graph."
            )
        removed_identifiers = [identifier]

    receipt: dict[str, Any] | None = None
    persisted_path: str | None = None
    updated_target = model_target
    if removed_identifiers:
        library = _component_library(model)
        for identifier in removed_identifiers:
            library.pop(identifier, None)
        updated_target, persisted_path, receipt = _save_update(
            garden_root_path=garden_root_path,
            manifest=manifest,
            target=model_target,
            model=model,
            operation="remove_ironbug_component",
            change_summary={
                "removed_identifiers": removed_identifiers,
                "cleanup_orphans": cleanup_orphans,
            },
        )
    else:
        receipt = make_persistence_receipt(
            status="no_change",
            garden_id=manifest.garden_id,
            model_target=model_target,
            change_summary={
                "operation": "remove_ironbug_component",
                "removed_identifiers": [],
                "cleanup_orphans": True,
            },
        )

    summary_view = {
        "model_target": updated_target,
        "removed_count": len(removed_identifiers),
        "removed_identifiers": removed_identifiers,
        "cleanup_orphans": cleanup_orphans,
    }
    result: dict[str, Any] = {
        "summary_view": summary_view,
        "persistence_receipt": receipt,
        "report": make_report(
            status="ok",
            message=(
                f"Removed {len(removed_identifiers)} Ironbug component(s)."
                if removed_identifiers
                else "No orphaned Ironbug components found."
            ),
            details={"persisted_path": persisted_path} if persisted_path else {},
        ),
    }
    if target is not None:
        result["target"] = target
    return result


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
