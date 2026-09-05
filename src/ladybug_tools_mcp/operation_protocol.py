"""Expose Garden operation controls and unified results across MCP tools."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4

import mcp_types as mt
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.server.transforms import GetToolNext, Transform
from fastmcp.tools.base import Tool, ToolResult
from fastmcp.utilities.versions import VersionSpec

from garden.manifest import GardenManifest
from garden.operations import (
    GardenOperationError,
    GardenOperationRecord,
    GardenRecoveryError,
    GardenRevisionConflictError,
    operation_controls,
    read_operation_record,
)
from ladybug_tools_mcp.contracts.operations import GardenOperationResult
from ladybug_tools_mcp.contracts.report import make_report
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt


_CONTROL_DESCRIPTION = (
    " Returns operation_result with operation target, runtime/readiness status, "
    "revisions, affected targets, receipt, report, and checkpoint target. Reuse "
    "operation_id only for the same immutable retry; pass expected_revision to "
    "reject a write based on stale Garden state."
)


def _supports_operation_controls(tool: Tool) -> bool:
    properties = tool.parameters.get("properties", {})
    return (
        "garden_root" in properties
        and bool({"author", "edit", "remove", "checkpoint", "apply"} & set(tool.tags))
    ) or tool.name in {
        "GD_create",
        "GD_library_normalize_garden_properties_storage",
    }


def _transform_tool(tool: Tool) -> Tool:
    if not _supports_operation_controls(tool):
        return tool
    parameters = deepcopy(tool.parameters)
    properties = parameters.setdefault("properties", {})
    properties["operation_id"] = {
        "anyOf": [{"type": "string"}, {"type": "null"}],
        "default": None,
        "description": (
            "Optional stable Garden operation identifier. Reuse only when retrying "
            "the same immutable mutation intent."
        ),
    }
    properties["expected_revision"] = {
        "anyOf": [{"type": "integer", "minimum": 0}, {"type": "null"}],
        "default": None,
        "description": (
            "Optional Garden revision read before this mutation. A stale value "
            "returns a structured conflict result instead of overwriting newer state."
        ),
    }

    output_schema = deepcopy(tool.output_schema) or {
        "type": "object",
        "additionalProperties": True,
    }
    operation_schema = GardenOperationResult.model_json_schema()
    operation_schema.pop("title", None)
    output_schema.setdefault("properties", {})["operation_result"] = operation_schema
    if "$defs" in operation_schema:
        output_schema.setdefault("$defs", {}).update(operation_schema.pop("$defs"))

    description = tool.description or ""
    if _CONTROL_DESCRIPTION.strip() not in description:
        description += _CONTROL_DESCRIPTION
    return tool.model_copy(
        update={
            "description": description,
            "parameters": parameters,
            "output_schema": output_schema,
        },
    )


class GardenOperationTransform(Transform):
    """Add operation controls and output schema before Code Mode catalogs tools."""

    async def list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]:
        return [_transform_tool(tool) for tool in tools]

    async def get_tool(
        self,
        name: str,
        call_next: GetToolNext,
        *,
        version: VersionSpec | None = None,
    ) -> Tool | None:
        tool = await call_next(name, version=version)
        return _transform_tool(tool) if tool else None


def _affected_targets(
    payload: dict[str, Any], record: GardenOperationRecord | None
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for key in ("target", "object_target", "model_target", "version_target"):
        value = payload.get(key)
        if isinstance(value, dict) and value:
            marker = repr(sorted(value.items()))
            if marker not in seen:
                targets.append(value)
                seen.add(marker)
    if record:
        for path in record.affected_paths:
            target = {
                "target_type": "garden_authoring_path",
                "garden_id": record.garden_id,
                "path": path,
            }
            marker = repr(sorted(target.items()))
            if marker not in seen:
                targets.append(target)
                seen.add(marker)
    return targets


def _checkpoint_target(payload: dict[str, Any]) -> dict[str, Any] | None:
    value = payload.get("checkpoint_target")
    if isinstance(value, dict) and value:
        return value
    value = payload.get("version_target")
    if isinstance(value, dict) and value:
        return value
    new_version = payload.get("new_version")
    if isinstance(new_version, dict) and isinstance(new_version.get("target"), dict):
        return new_version["target"]
    return None


def _result_from_payload(
    *, payload: dict[str, Any], operation_id: str, garden_root: str
) -> dict[str, Any]:
    receipt = payload["persistence_receipt"]
    report = payload.get("report") or make_report(status="ok", message="Operation completed.")
    garden_id = str(receipt["garden_id"])
    change_summary = receipt.get("change_summary") or {}
    operation_type = str(change_summary.get("operation") or "garden_authoring")
    record = read_operation_record(Path(garden_root), operation_id)
    if record:
        runtime_status = (
            "replayed"
            if record.phase == "committed" and record.replay_count > 0
            else record.phase
        )
        before_revision = record.before_revision
        after_revision = record.after_revision
        reason = (
            str((record.error or {}).get("message") or record.recovery_action or "")
            or None
        )
        readiness_status = {
            "committed": "ready",
            "replayed": "ready",
            "interrupted": "retryable",
            "prepared": "retryable",
            "committing": "retryable",
            "rolling_back": "retryable",
            "recovery_blocked": "intervention_required",
            "failed": "intervention_required",
        }[runtime_status]
        operation_type = record.operation_type
    else:
        runtime_status = "no_change" if receipt.get("status") == "no_change" else "committed"
        readiness_status = "ready"
        reason = None
        before_revision = change_summary.get("before_revision")
        after_revision = change_summary.get("after_revision")
        if before_revision is None or after_revision is None:
            revision = GardenManifest.read(Path(garden_root)).revision
            before_revision = revision
            after_revision = revision

    return GardenOperationResult(
        operation_target={
            "garden_id": garden_id,
            "operation_id": operation_id,
            "operation_type": operation_type,
        },
        runtime_status=runtime_status,
        readiness_status=readiness_status,
        intervention_reason=reason,
        before_revision=before_revision,
        after_revision=after_revision,
        affected_targets=_affected_targets(payload, record),
        persistence_receipt=receipt,
        report=report,
        checkpoint_target=_checkpoint_target(payload),
    ).model_dump(mode="json")


def _error_result(
    *,
    operation_id: str,
    operation_type: str,
    garden_root: str,
    arguments: dict[str, Any],
    error: GardenOperationError,
) -> dict[str, Any]:
    root = Path(garden_root)
    try:
        manifest = GardenManifest.read(root)
        garden_id = manifest.garden_id
        current_revision: int | None = manifest.revision
    except (OSError, RuntimeError, ValueError):
        try:
            manifest = GardenManifest._read_unlocked(root)
            garden_id = manifest.garden_id
            current_revision = manifest.revision
        except (OSError, RuntimeError, ValueError):
            from garden.versions import get_garden_version_status

            status = get_garden_version_status(garden_root=str(root))
            garden_id = str(status["summary_view"]["garden_target"]["garden_id"])
            current_revision = None
    if isinstance(error, GardenRevisionConflictError):
        runtime_status = "conflict"
        readiness_status = "reload_required"
        before_revision = error.expected_revision
        after_revision = error.current_revision
    elif isinstance(error, GardenRecoveryError):
        runtime_status = "recovery_blocked"
        readiness_status = "intervention_required"
        before_revision = after_revision = current_revision
    else:
        runtime_status = "failed"
        readiness_status = "intervention_required"
        before_revision = after_revision = current_revision
    receipt = make_persistence_receipt(
        status=runtime_status,
        garden_id=garden_id,
        change_summary={"operation": operation_type, "operation_id": operation_id},
    )
    report = make_report(status="error", message=str(error))
    return GardenOperationResult(
        operation_target={
            "garden_id": garden_id,
            "operation_id": operation_id,
            "operation_type": operation_type,
        },
        runtime_status=runtime_status,
        readiness_status=readiness_status,
        intervention_reason=str(error),
        before_revision=before_revision,
        after_revision=after_revision,
        affected_targets=[
            value
            for key, value in arguments.items()
            if key.endswith("target") and isinstance(value, dict) and value
        ],
        persistence_receipt=receipt,
        report=report,
        checkpoint_target=None,
    ).model_dump(mode="json")


class GardenOperationMiddleware(Middleware):
    """Route public controls to Garden and enrich mutation responses."""

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        fastmcp = context.fastmcp_context.fastmcp if context.fastmcp_context else None
        tool = await fastmcp.get_tool(context.message.name) if fastmcp else None
        if tool is None or not _supports_operation_controls(tool):
            return await call_next(context)

        arguments = dict(context.message.arguments or {})
        operation_id = arguments.pop("operation_id", None) or f"op_{uuid4().hex}"
        expected_revision = arguments.pop("expected_revision", None)
        context.message.arguments = arguments
        garden_root = arguments.get("garden_root")

        with operation_controls(
            operation_id=str(operation_id), expected_revision=expected_revision
        ):
            try:
                result = await call_next(context)
            except Exception as error:
                garden_error: GardenOperationError | None = None
                cause: BaseException | None = error
                while cause is not None:
                    if isinstance(cause, GardenOperationError):
                        garden_error = cause
                        break
                    cause = cause.__cause__
                if garden_error is None:
                    raise
                if not isinstance(garden_root, str):
                    raise
                return ToolResult(
                    structured_content={
                        "operation_result": _error_result(
                            operation_id=str(operation_id),
                            operation_type=context.message.name,
                            garden_root=garden_root,
                            arguments=arguments,
                            error=garden_error,
                        )
                    }
                )

        payload = result.structured_content
        if isinstance(payload, dict) and "operation_result" in payload:
            return result
        if not isinstance(payload, dict) or not isinstance(
            payload.get("persistence_receipt"), dict
        ):
            return result
        resolved_root = garden_root or payload.get("garden_root")
        if not isinstance(resolved_root, str):
            return result
        payload = dict(payload)
        payload["operation_result"] = _result_from_payload(
            payload=payload,
            operation_id=str(operation_id),
            garden_root=resolved_root,
        )
        return ToolResult(
            structured_content=payload,
            meta=result.meta,
            is_error=result.is_error,
        )
