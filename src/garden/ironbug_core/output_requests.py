"""Garden helpers for Ironbug output-variable requests."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from ironbug import hvac

from garden.ironbug_core.assembly import _save_update
from garden.ironbug_core.model_io import load_ironbug_model
from garden.ironbug_core.relationships import (
    _load_for_update,
    _object_identifier,
    _resolve_object,
)
from ladybug_tools_mcp.contracts.report import make_report


REPORTING_FREQUENCIES = {"Detail", "Hourly", "Daily", "Monthly", "RunPeriod"}


def _garden_root(garden_root: str) -> Path:
    return Path(garden_root).expanduser().resolve()


def _output_request_dict(variable_name: str, reporting_frequency: str) -> dict[str, str]:
    return {"VariableName": variable_name, "TimeStep": reporting_frequency}


def _validate_request_inputs(
    *,
    variable_names: list[str],
    reporting_frequency: str,
) -> list[str]:
    if reporting_frequency not in REPORTING_FREQUENCIES:
        raise ValueError(
            f"Unsupported Ironbug output reporting frequency: {reporting_frequency}"
        )
    cleaned_names = [name.strip() for name in variable_names if name.strip()]
    if not cleaned_names:
        raise ValueError("Pass at least one output variable name.")
    return cleaned_names


def _output_variable_object(variable_name: str, reporting_frequency: str) -> Any:
    return hvac.IB_OutputVariable(
        VariableName=variable_name,
        TimeStep=reporting_frequency,
    )


def _output_variable_summary(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            "VariableName": value.get("VariableName"),
            "TimeStep": value.get("TimeStep"),
        }
    return {
        "VariableName": getattr(value, "VariableName", None),
        "TimeStep": getattr(value, "TimeStep", None),
    }


def add_output_variable_requests_to_object_data(
    data: dict[str, Any],
    *,
    variable_names: list[str],
    reporting_frequency: str,
) -> dict[str, Any]:
    """Return source object data with selected CustomOutputVariables appended."""

    cleaned_names = _validate_request_inputs(
        variable_names=variable_names,
        reporting_frequency=reporting_frequency,
    )
    updated = deepcopy(data)
    existing = [
        _output_variable_summary(item)
        for item in list(updated.get("CustomOutputVariables") or [])
    ]
    for name in cleaned_names:
        request = _output_request_dict(name, reporting_frequency)
        if request not in existing:
            existing.append(request)
    updated["CustomOutputVariables"] = existing
    return updated


def list_ironbug_output_variables(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    object_target: dict[str, Any] | str,
) -> dict[str, Any]:
    """List available output variable names recorded on an Ironbug object."""

    _, _, model_target, model = _load_for_update(garden_root, ironbug_model_target)
    resolved = _resolve_object(model, model_target, object_target)
    variables = list(getattr(resolved.obj, "SimulationOutputVariables", None) or [])
    availability = "source_object_metadata" if variables else "unavailable_before_translation"
    return {
        "target": resolved.target,
        "summary_view": {
            "identifier": _object_identifier(resolved.obj),
            "source_class": getattr(
                resolved.obj, "SOURCE_CLASS", resolved.obj.__class__.__name__
            ),
            "available_variables": sorted(str(item) for item in variables),
            "availability": availability,
        },
        "report": make_report(
            status="ok",
            message="Listed Ironbug output variables.",
            details={"availability": availability, "count": len(variables)},
        ),
    }


def _save_output_request_update(
    *,
    garden_root_path: Path,
    manifest: Any,
    model_target: dict[str, Any],
    model: Any,
    target: dict[str, Any],
    operation: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    updated_target, persisted_path, receipt = _save_update(
        garden_root_path=garden_root_path,
        manifest=manifest,
        target=model_target,
        model=model,
        operation=operation,
        change_summary=details,
    )
    target["model_target"] = updated_target
    return {
        "target": target,
        "updated_model_target": updated_target,
        "summary_view": details,
        "persistence_receipt": receipt,
        "report": make_report(
            status="updated",
            message=f"Updated Ironbug output requests: {operation}",
            details={"persisted_path": persisted_path, **details},
        ),
    }


def add_ironbug_output_variable_requests(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    object_target: dict[str, Any] | str,
    variable_names: list[str],
    reporting_frequency: str,
) -> dict[str, Any]:
    """Attach CustomOutputVariables to an Ironbug object."""

    cleaned_names = _validate_request_inputs(
        variable_names=variable_names,
        reporting_frequency=reporting_frequency,
    )
    garden_root_path, manifest, model_target, model = _load_for_update(
        garden_root,
        ironbug_model_target,
    )
    resolved = _resolve_object(model, model_target, object_target)
    existing = list(getattr(resolved.obj, "CustomOutputVariables", None) or [])
    existing_summary = [_output_variable_summary(item) for item in existing]
    added: list[dict[str, str]] = []
    for name in cleaned_names:
        summary = _output_request_dict(name, reporting_frequency)
        if summary in existing_summary:
            continue
        existing.append(_output_variable_object(name, reporting_frequency))
        existing_summary.append(summary)
        added.append(summary)
    resolved.obj.CustomOutputVariables = existing
    resolved.save(resolved.obj)
    details = {
        "identifier": _object_identifier(resolved.obj),
        "source_class": getattr(resolved.obj, "SOURCE_CLASS", resolved.obj.__class__.__name__),
        "requested_count": len(existing_summary),
        "added_count": len(added),
        "added_requests": added,
        "reporting_frequency": reporting_frequency,
    }
    return _save_output_request_update(
        garden_root_path=garden_root_path,
        manifest=manifest,
        model_target=model_target,
        model=model,
        target=resolved.target,
        operation="add_ironbug_output_variable_requests",
        details=details,
    )


def clear_ironbug_output_variable_requests(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
    object_target: dict[str, Any] | str,
) -> dict[str, Any]:
    """Clear CustomOutputVariables from an Ironbug object."""

    garden_root_path, manifest, model_target, model = _load_for_update(
        garden_root,
        ironbug_model_target,
    )
    resolved = _resolve_object(model, model_target, object_target)
    existing = list(getattr(resolved.obj, "CustomOutputVariables", None) or [])
    resolved.obj.CustomOutputVariables = None
    resolved.save(resolved.obj)
    details = {
        "identifier": _object_identifier(resolved.obj),
        "source_class": getattr(resolved.obj, "SOURCE_CLASS", resolved.obj.__class__.__name__),
        "removed_count": len(existing),
    }
    return _save_output_request_update(
        garden_root_path=garden_root_path,
        manifest=manifest,
        model_target=model_target,
        model=model,
        target=resolved.target,
        operation="clear_ironbug_output_variable_requests",
        details=details,
    )


def validate_ironbug_output_variable_requests(
    *,
    garden_root: str,
    ironbug_model_target: dict[str, Any],
) -> dict[str, Any]:
    """Validate CustomOutputVariables currently stored in an Ironbug model."""

    garden_root_path = _garden_root(garden_root)
    _, target, _, model = load_ironbug_model(
        garden_root_path,
        ironbug_model_target=ironbug_model_target,
    )
    issues: list[dict[str, Any]] = []

    def visit(obj: Any) -> None:
        identifier = getattr(obj, "identifier", None)
        requests = list(getattr(obj, "CustomOutputVariables", None) or [])
        for index, request in enumerate(requests):
            summary = _output_variable_summary(request)
            if not summary.get("VariableName"):
                issues.append(
                    {
                        "code": "missing_output_variable_name",
                        "identifier": identifier,
                        "index": index,
                    }
                )
            if summary.get("TimeStep") not in REPORTING_FREQUENCIES:
                issues.append(
                    {
                        "code": "unsupported_reporting_frequency",
                        "identifier": identifier,
                        "index": index,
                        "reporting_frequency": summary.get("TimeStep"),
                    }
                )
        for child in list(getattr(obj, "Children", None) or []):
            visit(child)

    if model.HVACSystem is not None:
        visit(model.HVACSystem)
        for collection_name in (
            "AirLoops",
            "PlantLoops",
            "VariableRefrigerantFlows",
        ):
            for item in list(getattr(model.HVACSystem, collection_name, None) or []):
                visit(item)
    for record in dict(getattr(model, "user_data", None) or {}).get(
        "ironbug_component_library",
        {},
    ).values():
        data = dict(record.get("data") or {})
        for index, request in enumerate(data.get("CustomOutputVariables") or []):
            summary = _output_variable_summary(request)
            if not summary.get("VariableName"):
                issues.append(
                    {
                        "code": "missing_output_variable_name",
                        "identifier": data.get("identifier"),
                        "index": index,
                    }
                )
            if summary.get("TimeStep") not in REPORTING_FREQUENCIES:
                issues.append(
                    {
                        "code": "unsupported_reporting_frequency",
                        "identifier": data.get("identifier"),
                        "index": index,
                        "reporting_frequency": summary.get("TimeStep"),
                    }
                )

    ready = not issues
    return {
        "target": target,
        "ready": ready,
        "summary_view": {
            "ready": ready,
            "issue_count": len(issues),
            "issues": issues,
        },
        "report": make_report(
            status="ok" if ready else "blocked",
            message=(
                "Ironbug output variable requests are valid."
                if ready
                else "Ironbug output variable requests have issues."
            ),
            details={"issue_count": len(issues), "issues": issues},
        ),
    }
