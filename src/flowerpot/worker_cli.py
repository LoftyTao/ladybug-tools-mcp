"""External worker entrypoint for Flowerpot platform operations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from honeybee.model import Model
from ironbug import hvac as ironbug_hvac

from ladybug_tools_mcp.contracts.report import make_report
from flowerpot.active_context import write_active_context
from flowerpot.properties_input import read_properties_input
from flowerpot.registry import create_flowerpot, get_flowerpot
from garden.manifest import GardenManifest
from garden.ironbug_core.detailed_hvac import (
    build_ironbug_model_detailed_hvac_specification,
    _component_thermal_zones,
    _ironbug_console_spec_value,
    _thermal_zone_names,
)
from garden.ironbug_core.model_io import load_ironbug_model
from garden.ironbug_core.readiness import validate_ironbug_energyplus_readiness
from garden.store import create_garden, get_base_honeybee_model, list_gardens
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    save_honeybee_model,
)


def main(argv: list[str] | None = None) -> int:
    """Run the worker CLI and print a JSON response to stdout."""
    parser = argparse.ArgumentParser(prog="flowerpot-worker")
    parser.add_argument(
        "--session",
        action="store_true",
        help="Read JSON Lines requests from stdin and keep the worker process alive.",
    )
    parser.add_argument(
        "action",
        nargs="?",
        choices=(
            "garden_create",
            "garden_list",
            "honeybee_link",
            "ironbug_hvac_specification",
            "energy_properties_input",
            "radiance_properties_input",
        ),
    )
    args = parser.parse_args(argv)

    if args.session:
        return _run_session()
    if not args.action:
        parser.error("action is required unless --session is used")

    try:
        request = json.loads(sys.stdin.read() or "{}")
        response = _dispatch(args.action, request)
    except Exception as error:
        response = {"error": str(error)}

    sys.stdout.write(json.dumps(response, ensure_ascii=False))
    sys.stdout.flush()
    return 0


def _run_session() -> int:
    """Run a persistent JSON Lines worker session over stdin/stdout."""
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            action = message["action"]
            request = message.get("request") or {}
            result = _dispatch(action, request)
            response = {"ok": True, "result": result}
        except Exception as error:
            response = {"ok": False, "error": str(error)}
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


def _dispatch(action: str, request: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a worker request to the matching implementation."""
    if action == "garden_create":
        return _garden_create(request)
    if action == "garden_list":
        return _garden_list(request)
    if action == "honeybee_link":
        return _honeybee_link(request)
    if action == "ironbug_hvac_specification":
        return _ironbug_hvac_specification(request)
    if action == "energy_properties_input":
        return _properties_input(request, "honeybee_energy")
    if action == "radiance_properties_input":
        return _properties_input(request, "honeybee_radiance")
    raise ValueError(f"Unsupported action: {action}")


def _garden_create(request: dict[str, Any]) -> dict[str, Any]:
    """Create one Garden and return an opaque Flowerpot handle."""
    name = _require_text(request.get("name"), "name")
    garden = create_garden(
        name=name,
        root_dir=request.get("root_folder"),
        description=request.get("description"),
    )
    flowerpot = create_flowerpot(
        garden_root=garden["garden_root"],
        source="garden",
        label=name,
        platform={"adapter": "grasshopper"},
    )
    return {
        "flowerpot": flowerpot["flowerpot"],
        "flowerpot_id": flowerpot["flowerpot_id"],
        "garden_root": garden["garden_root"],
        "garden_target": garden["garden_target"],
        "report": flowerpot.get("report") or garden.get("report"),
    }


def _garden_list(request: dict[str, Any]) -> dict[str, Any]:
    """List Gardens as opaque Flowerpot handles."""
    listed = list_gardens(root_dir=request.get("root_folder"))
    flowerpots: list[dict[str, Any]] = []
    garden_roots: list[str] = []
    names: list[str] = []
    warnings: list[str] = []

    for match in listed.get("matches", []):
        garden_root = match.get("path")
        if not garden_root:
            continue
        try:
            created = create_flowerpot(
                garden_root=garden_root,
                source="garden",
                label=match.get("name"),
                platform={"adapter": "grasshopper"},
            )
        except Exception as error:
            warnings.append(str(error))
            continue
        flowerpots.append(created["flowerpot"])
        garden_roots.append(garden_root)
        names.append(match.get("name"))

    return {
        "flowerpots": flowerpots,
        "garden_roots": garden_roots,
        "names": names,
        "report": make_report(
            status="ok",
            message=f"Found {len(flowerpots)} Garden Flowerpot(s).",
            warnings=[*listed.get("report", {}).get("warnings", []), *warnings],
        ),
    }


def _honeybee_link(request: dict[str, Any]) -> dict[str, Any]:
    """Write or read a Honeybee Model through a Flowerpot Garden context."""
    flowerpot = request.get("flowerpot")
    if not isinstance(flowerpot, dict):
        raise ValueError("flowerpot is required.")

    garden_root = _garden_root_from_flowerpot(flowerpot)
    payload = request.get("payload")
    write = bool(request.get("write"))
    follow = bool(request.get("follow"))
    if payload is not None and write:
        model = Model.from_dict(payload)
        garden_path = Path(garden_root).expanduser().resolve()
        manifest = GardenManifest.read(garden_path)
        model_target, persisted_path = save_honeybee_model(
            garden_path,
            manifest,
            model,
            name=model.identifier,
            set_base=True,
        )
        created = create_flowerpot(
            garden_root=str(garden_path),
            source="base_honeybee_model",
            target=model_target,
            label=getattr(model, "display_name", None) or model.identifier,
            platform={"adapter": "grasshopper"},
        )
        report = make_report(
            status="ok",
            message="Linked Honeybee model into Flowerpot Garden.",
            details={"persisted_path": persisted_path},
        )
        _write_grasshopper_context(
            garden_root=str(garden_path),
            flowerpot=created["flowerpot"],
            request=request,
            mode="write",
            changed=True,
            model_target=model_target,
            model_identifier=model.identifier,
            model_display_name=getattr(model, "display_name", None),
            report_status=report["status"],
        )
        return {
            "model": model.to_dict(),
            "flowerpot": created["flowerpot"],
            "model_target": model_target,
            "changed": True,
            "report": report,
        }

    if payload is not None and not follow:
        model_identifier, model_display_name = _model_identity_from_payload(payload)
        report = make_report(
            status="ok",
            message="Honeybee model passed through; _write is False.",
        )
        _write_grasshopper_context(
            garden_root=garden_root,
            flowerpot=flowerpot,
            request=request,
            mode="pass_through",
            changed=False,
            model_target=_model_target_from_flowerpot(
                flowerpot,
                garden_root=garden_root,
                payload=payload,
                model_identifier=model_identifier,
            ),
            model_identifier=model_identifier,
            model_display_name=model_display_name,
            report_status=report["status"],
        )
        return {
            "model": payload,
            "flowerpot": flowerpot,
            "model_target": None,
            "changed": False,
            "report": report,
        }

    base = get_base_honeybee_model(garden_root=garden_root)
    model_target = base.get("model_target") or base.get("target")
    if not model_target:
        report = make_report(
            status="ok",
            message="Flowerpot Garden has no Honeybee base model.",
        )
        _write_grasshopper_context(
            garden_root=garden_root,
            flowerpot=flowerpot,
            request=request,
            mode="follow" if follow else "idle",
            changed=False,
            model_target=None,
            model_identifier=None,
            model_display_name=None,
            report_status=report["status"],
        )
        return {
            "model": None,
            "flowerpot": flowerpot,
            "model_target": None,
            "changed": False,
            "report": report,
        }

    model = load_honeybee_model(Path(garden_root), model_target)
    created = create_flowerpot(
        garden_root=garden_root,
        source="base_honeybee_model",
        target=model_target,
        label=model_target.get("model_identifier"),
        platform={"adapter": "grasshopper", "follow": follow},
    )
    report = make_report(status="ok", message="Loaded Honeybee base model.")
    _write_grasshopper_context(
        garden_root=garden_root,
        flowerpot=created["flowerpot"],
        request=request,
        mode="follow",
        changed=False,
        model_target=model_target,
        model_identifier=getattr(model, "identifier", None),
        model_display_name=getattr(model, "display_name", None),
        report_status=report["status"],
    )
    return {
        "model": model.to_dict(),
        "flowerpot": created["flowerpot"],
        "model_target": model_target,
        "changed": False,
        "report": report,
    }


def _ironbug_hvac_specification(request: dict[str, Any]) -> dict[str, Any]:
    """Return the selected Garden Ironbug HVAC specification for CLR handoff."""
    flowerpot = request.get("flowerpot")
    if not isinstance(flowerpot, dict):
        return _ironbug_hvac_error("flowerpot is required.")

    try:
        garden_root = _garden_root_from_flowerpot(flowerpot)
        manifest = GardenManifest.read(Path(garden_root))
        candidates = [
            dict(item)
            for item in manifest.models
            if item.get("domain") == "ironbug"
            and item.get("target_type") == "ironbug_model"
        ]
        candidate_ids = [str(item.get("id")) for item in candidates]
        requested_id = request.get("model_identifier")
        requested_id = (
            str(requested_id).strip() if requested_id is not None else ""
        )
        if requested_id:
            matches = [item for item in candidates if item.get("id") == requested_id]
            if not matches:
                return _ironbug_hvac_error(
                    f"Ironbug authoring model not found: {requested_id}",
                    candidate_identifiers=candidate_ids,
                )
            selected = matches[0]
        elif len(candidates) == 1:
            selected = candidates[0]
        elif not candidates:
            return _ironbug_hvac_error("Garden has no Ironbug authoring models.")
        else:
            return _ironbug_hvac_error(
                "Garden has multiple Ironbug authoring models; connect model_ with "
                "an exact identifier.",
                candidate_identifiers=candidate_ids,
            )

        _, selected, model_path, model = load_ironbug_model(
            Path(garden_root), ironbug_model_target=selected
        )
        identifier = str(model.identifier or selected["id"])
        display_name = str(model.display_name or identifier)
        if model.HVACSystem is None:
            return _ironbug_hvac_error(
                f"Ironbug authoring model has no HVAC system: {identifier}"
            )
        has_hvac_graph = bool(
            model.HVACSystem.AirLoops
            or model.HVACSystem.PlantLoops
            or model.HVACSystem.VariableRefrigerantFlows
            or _component_thermal_zones(model)
        )
        specification = (
            build_ironbug_model_detailed_hvac_specification(
                ironbug_model=model,
                room_identifiers=[],
                validate_room_links=False,
            )
            if has_hvac_graph
            else _ironbug_console_spec_value(model.HVACSystem)
        )
        allowlist = _ironbug_hvac_type_allowlist()
        try:
            _validate_specification_types(specification, allowlist)
        except ValueError as error:
            return _ironbug_hvac_error(str(error), failed_gate="allowlist")
        specification.pop("$type", None)
        specification["DisplayName"] = display_name
        excluded_roots = [
            name
            for name in ("EnergyManagementSystem", "ElectricLoadCenter")
            if getattr(model, name, None) is not None
        ]
        for name in excluded_roots:
            specification.pop(name, None)
        readiness = _ironbug_hvac_readiness(
            garden_root=garden_root,
            ironbug_model_target=selected,
        )
        room_binding = _ironbug_room_binding(
            garden_root=garden_root,
            model=model,
        )
        all_readiness_issues = [
            *room_binding.get("issues", []),
            *readiness.get("issues", []),
        ]
        readiness_issues = [
            issue
            for issue in all_readiness_issues
            if issue.get("severity") != "warning"
        ]
        blocked = bool(readiness_issues)
        metadata = {
            "model_identifier": identifier,
            "model_display_name": display_name,
            "expected_assembly_name": "Ironbug.HVAC",
            "expected_assembly_version": "1.26.0",
            "thermal_zones": room_binding["thermal_zone_names"],
            "thermal_zone_details": room_binding["thermal_zones"],
            "room_binding": room_binding,
            "energy_readiness": readiness,
            "excluded_roots": excluded_roots,
            "failed_gate": None,
        }
        return {
            "specification": specification,
            "allowlist": sorted(allowlist),
            "metadata": metadata,
            "follow_path": str(model_path),
            "report": make_report(
                status="blocked" if blocked else "ok",
                message=(
                    f"Prepared native Ironbug HVAC handoff: {identifier}"
                    + ("; readiness checks are blocked." if blocked else ".")
                ),
                warnings=[
                    str(issue.get("message") or issue.get("code"))
                    for issue in all_readiness_issues
                ],
                details=metadata,
            ),
        }
    except Exception as error:
        return _ironbug_hvac_error(str(error))


def _ironbug_hvac_readiness(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
) -> dict[str, Any]:
    """Return compact EnergyPlus readiness without blocking native handoff."""
    try:
        result = validate_ironbug_energyplus_readiness(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
        )
        report = result.get("report") or {}
        issues = [
            dict(issue)
            for issue in report.get("issues", [])
            if isinstance(issue, dict)
        ]
        return {
            "status": str(report.get("status") or "unknown"),
            "ready": report.get("status") == "pass",
            "issue_count": len(issues),
            "blocking_issue_count": sum(
                1 for issue in issues if issue.get("severity") != "warning"
            ),
            "issues": issues,
        }
    except Exception as error:
        return {
            "status": "blocked",
            "ready": False,
            "issue_count": 1,
            "blocking_issue_count": 1,
            "issues": [
                {
                    "code": "ironbug_energy_readiness_check_failed",
                    "message": str(error),
                }
            ],
        }


def _ironbug_room_binding(*, garden_root: str, model: Any) -> dict[str, Any]:
    """Compare optional base Honeybee Room ids with Ironbug ThermalZone names."""
    zones = _component_thermal_zones(model)
    thermal_zones = [
        {
            "identifier": str(getattr(zone, "identifier", "") or ""),
            "names": sorted(_thermal_zone_names(zone)),
        }
        for zone in zones
    ]
    base = get_base_honeybee_model(garden_root=garden_root)
    base_target = base.get("target") or base.get("model_target")
    if not base_target:
        return {
            "status": "not_checked",
            "room_identifiers": [],
            "thermal_zone_names": sorted(
                {name for zone in thermal_zones for name in zone["names"]}
            ),
            "missing_room_identifiers": [],
            "unmatched_thermal_zone_names": [],
            "thermal_zones": thermal_zones,
            "issues": [],
        }

    try:
        honeybee_model = load_honeybee_model(Path(garden_root), base_target)
        room_identifiers = sorted(str(room.identifier) for room in honeybee_model.rooms)
    except Exception as error:
        return {
            "status": "blocked",
            "room_identifiers": [],
            "thermal_zone_names": sorted(
                {name for zone in thermal_zones for name in zone["names"]}
            ),
            "missing_room_identifiers": [],
            "unmatched_thermal_zone_names": [],
            "thermal_zones": thermal_zones,
            "issues": [
                {
                    "code": "honeybee_base_model_load_failed",
                    "message": str(error),
                }
            ],
        }

    thermal_zone_names = sorted(
        {name for zone in thermal_zones for name in zone["names"]}
    )
    zone_name_sets = [set(zone["names"]) for zone in thermal_zones]
    room_ids = set(room_identifiers)
    missing = sorted(
        room_id
        for room_id in room_identifiers
        if not any(room_id in names for names in zone_name_sets)
    )
    unmatched = sorted(
        {
            name
            for names in zone_name_sets
            if names.isdisjoint(room_ids)
            for name in names
        }
    )
    issues = []
    if missing or unmatched:
        issues.append(
            {
                "code": "ironbug_thermal_zone_room_binding_mismatch",
                "message": (
                    "Honeybee Room identifiers must match Ironbug ThermalZone "
                    "Name or identifier values."
                ),
                "missing_room_identifiers": missing,
                "unmatched_thermal_zone_names": unmatched,
            }
        )
    return {
        "status": "mismatch" if issues else "matched",
        "room_identifiers": room_identifiers,
        "thermal_zone_names": thermal_zone_names,
        "missing_room_identifiers": missing,
        "unmatched_thermal_zone_names": unmatched,
        "thermal_zones": thermal_zones,
        "issues": issues,
    }


def _ironbug_hvac_type_allowlist() -> set[str]:
    """Return exact Ironbug.HVAC types confirmed by the source-backed mirror."""
    allowed: set[str] = set()
    for value in vars(ironbug_hvac).values():
        if not isinstance(value, type):
            continue
        source_class = getattr(value, "SOURCE_CLASS", None)
        namespace = getattr(value, "SOURCE_NAMESPACE", None)
        source_path = str(getattr(value, "SOURCE_PATH", "") or "")
        if not source_class or not namespace or not source_path.startswith(
            "src/Ironbug.HVAC"
        ):
            continue
        allowed.add(f"{namespace}.{source_class}, Ironbug.HVAC")
    return allowed


def _validate_specification_types(value: Any, allowlist: set[str]) -> None:
    """Reject unsupported type metadata before it reaches the CLR runtime."""
    if isinstance(value, dict):
        if "$type" in value:
            type_name = value["$type"]
            if not isinstance(type_name, str) or type_name not in allowlist:
                raise ValueError(
                    f"Ironbug specification contains disallowed $type: {type_name}"
                )
        for item in value.values():
            _validate_specification_types(item, allowlist)
    elif isinstance(value, list):
        for item in value:
            _validate_specification_types(item, allowlist)


def _ironbug_hvac_error(
    message: str,
    *,
    candidate_identifiers: list[str] | None = None,
    failed_gate: str = "selection",
) -> dict[str, Any]:
    details = {
        "candidate_identifiers": candidate_identifiers or [],
        "expected_assembly_name": "Ironbug.HVAC",
        "expected_assembly_version": "1.26.0",
        "failed_gate": failed_gate,
    }
    return {
        "specification": None,
        "allowlist": [],
        "metadata": details,
        "follow_path": None,
        "report": make_report(
            status="error",
            message=message,
            warnings=[message],
            details=details,
        ),
    }


def _write_grasshopper_context(
    *,
    garden_root: str,
    flowerpot: dict[str, Any],
    request: dict[str, Any],
    mode: str,
    changed: bool,
    model_target: dict[str, Any] | None,
    model_identifier: str | None,
    model_display_name: str | None,
    report_status: str,
) -> None:
    write_active_context(
        garden_root=garden_root,
        platform="grasshopper",
        flowerpot=flowerpot,
        mode=mode,
        follow=bool(request.get("follow")),
        changed=changed,
        component=(
            request.get("component")
            if isinstance(request.get("component"), dict)
            else {}
        ),
        model_target=model_target,
        model_identifier=model_identifier,
        model_display_name=model_display_name,
        report_status=report_status,
    )


def _model_identity_from_payload(payload: Any) -> tuple[str | None, str | None]:
    if isinstance(payload, dict):
        return payload.get("identifier"), payload.get("display_name")
    return None, None


def _model_target_from_flowerpot(
    flowerpot: dict[str, Any],
    *,
    garden_root: str,
    payload: Any,
    model_identifier: str | None,
) -> dict[str, Any] | None:
    target = flowerpot.get("target")
    if not (
        isinstance(target, dict)
        and target.get("target_type") == "honeybee_model"
        and target.get("model_identifier") == model_identifier
    ):
        return None
    try:
        current_model = Model.from_dict(payload)
        persisted_model = load_honeybee_model(Path(garden_root), target)
    except Exception:
        return None
    if persisted_model.to_dict() == current_model.to_dict():
        return target
    return None


def _properties_input(request: dict[str, Any], domain: str) -> dict[str, Any]:
    """Read Garden Properties Library objects for a Grasshopper properties input."""
    flowerpot = request.get("flowerpot")
    properties_type_value = request.get("type")
    value = request.get("value")
    try:
        if not isinstance(flowerpot, dict):
            raise ValueError("flowerpot is required.")
        properties_type = _require_text(properties_type_value, "type")
        return read_properties_input(
            flowerpot=flowerpot,
            domain=domain,
            properties_type=properties_type,
            value=None if value is None else str(value),
        )
    except Exception as error:
        return {
            "property": None,
            "properties": [],
            "targets": [],
            "follow_path": None,
            "report": make_report(
                status="error",
                message=str(error),
                warnings=[str(error)],
                details={
                    "domain": domain,
                    "type": properties_type_value,
                    "query": None if value is None else str(value),
                    "match_count": 0,
                    "targets": [],
                },
            ),
        }


def _garden_root_from_flowerpot(flowerpot: dict[str, Any]) -> str:
    """Return the Garden root encoded inside an opaque Flowerpot."""
    get_flowerpot(flowerpot=flowerpot)
    payload_context = flowerpot.get("payload_context", {})
    garden_root = payload_context.get("garden_root")
    if not garden_root:
        raise ValueError("Flowerpot does not include a Garden root context.")
    return str(Path(garden_root).expanduser().resolve())


def _require_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} is required.")
    return text


if __name__ == "__main__":
    raise SystemExit(main())
