"""External worker entrypoint for Flowerpot platform operations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from honeybee.model import Model

from ladybug_tools_mcp.contracts.report import make_report
from flowerpot.active_context import write_active_context
from flowerpot.properties_input import read_properties_input
from flowerpot.registry import create_flowerpot, get_flowerpot
from garden.manifest import GardenManifest
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
