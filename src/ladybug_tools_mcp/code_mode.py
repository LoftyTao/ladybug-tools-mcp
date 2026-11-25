"""Project-specific integration around FastMCP Code Mode."""

from __future__ import annotations

import asyncio
import inspect
import os
from collections.abc import Callable
from typing import Any

from fastmcp.experimental.transforms.code_mode import (
    CodeMode,
    GetSchemas,
    GetTags,
    ListTools,
    MontySandboxProvider,
    Search,
    _DEFAULT_LIMITS,
    _UNSET,
    _UnsetType,
)

DEFAULT_MAX_TOOL_CALLS = 100


def _env_positive_int(name: str, default: int | None = None) -> int | None:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer, got {raw!r}.") from exc
    if value < 1:
        raise ValueError(f"{name} must be >= 1, got {value}.")
    return value


def _env_positive_float(name: str, default: float | None = None) -> float | None:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive number, got {raw!r}.") from exc
    if value <= 0:
        raise ValueError(f"{name} must be > 0, got {value}.")
    return value


def resolve_sandbox_limits() -> dict[str, Any]:
    """Build Monty sandbox ResourceLimits from defaults and environment overrides."""
    limits: dict[str, Any] = dict(_DEFAULT_LIMITS)
    max_duration = _env_positive_float("LBT_MCP_SANDBOX_MAX_DURATION_SECS")
    if max_duration is not None:
        limits["max_duration_secs"] = max_duration
    max_memory = _env_positive_int("LBT_MCP_SANDBOX_MAX_MEMORY")
    if max_memory is not None:
        limits["max_memory"] = max_memory
    return limits


def _accepts_changed_targets(fn: Callable[..., Any]) -> bool:
    """Return whether ``fn`` (or a mock's ``side_effect``) accepts ``changed_targets``."""
    target = getattr(fn, "side_effect", None)
    check_fn = target if callable(target) else fn
    try:
        sig = inspect.signature(check_fn)
    except (TypeError, ValueError):
        return False
    for param in sig.parameters.values():
        if param.name == "changed_targets" or param.kind == inspect.Parameter.VAR_KEYWORD:
            return True
    return False


class PreviewMontySandboxProvider(MontySandboxProvider):
    """Record Web View previews after tools run through Code Mode."""

    def __init__(self, *, limits: Any | _UnsetType = _UNSET) -> None:
        resolved_limits = resolve_sandbox_limits() if isinstance(limits, _UnsetType) else limits
        super().__init__(limits=resolved_limits)

    async def run(
        self,
        code: str,
        *,
        inputs: dict[str, Any] | None = None,
        external_functions: dict[str, Callable[..., Any]] | None = None,
    ) -> Any:
        pending_previews: dict[str, tuple[str, Any, Any]] = {}
        changed_targets_by_garden: dict[str, list[dict[str, Any]]] = {}
        changed_target_keys_by_garden: dict[str, set[tuple[str, ...]]] = {}
        last_tool_error: tuple[str, BaseException] | None = None
        if external_functions and "call_tool" in external_functions:
            call_tool = external_functions["call_tool"]
            external_functions = dict(external_functions)

            async def call_tool_with_preview(
                tool_name: str, arguments: Any = None
            ) -> Any:
                nonlocal last_tool_error
                last_tool_error = None
                try:
                    result = await call_tool(tool_name, arguments)
                except BaseException as exc:
                    # Preserve the inner tool error in case Monty fails to serialize a multiline StackFrame.
                    last_tool_error = (tool_name, exc)
                    raise
                try:
                    from web_view import extract_changed_targets, preview_event_garden_root

                    garden_key = preview_event_garden_root(
                        tool_name=tool_name,
                        arguments=arguments,
                        result=result,
                    )
                except Exception:
                    garden_key = None
                    extract_changed_targets = None
                if garden_key is not None:
                    pending_previews[garden_key] = (tool_name, arguments, result)
                    if extract_changed_targets is not None:
                        bucket = changed_targets_by_garden.setdefault(garden_key, [])
                        seen_keys = changed_target_keys_by_garden.setdefault(garden_key, set())
                        for target in extract_changed_targets(result=result, arguments=arguments):
                            key = (
                                str(target.get("target_type") or ""),
                                str(target.get("domain") or ""),
                                str(target.get("model_identifier") or ""),
                                str(target.get("object_type") or ""),
                                str(target.get("object_identifier") or target.get("identifier") or ""),
                            )
                            if key not in seen_keys:
                                seen_keys.add(key)
                                bucket.append(target)
                return result

            external_functions["call_tool"] = call_tool_with_preview

        try:
            try:
                return await super().run(
                    code,
                    inputs=inputs,
                    external_functions=external_functions,
                )
            except RuntimeError as exc:
                if (
                    last_tool_error is not None
                    and "monty worker protocol error: invalid exception payload"
                    in str(exc)
                ):
                    failed_tool, inner_exc = last_tool_error
                    raise RuntimeError(
                        f"Error calling tool '{failed_tool}': {inner_exc}"
                    ) from inner_exc
                raise
        finally:
            if pending_previews:
                try:
                    from web_view import maybe_record_code_mode_preview
                except Exception:
                    maybe_record_code_mode_preview = None
                if maybe_record_code_mode_preview is not None:
                    pass_changed_targets = _accepts_changed_targets(maybe_record_code_mode_preview)
                    for garden_key, (tool_name, arguments, result) in pending_previews.items():
                        try:
                            kwargs: dict[str, Any] = {
                                "tool_name": tool_name,
                                "arguments": arguments,
                                "result": result,
                            }
                            if pass_changed_targets:
                                kwargs["changed_targets"] = list(
                                    changed_targets_by_garden.get(garden_key, ())
                                )
                            await asyncio.to_thread(
                                maybe_record_code_mode_preview,
                                **kwargs,
                            )
                        except Exception:
                            continue


def create_code_mode_transform() -> CodeMode:
    """Create Code Mode with full discovery tools, env limits, and Web View preview hook."""
    max_tool_calls = _env_positive_int("LBT_MCP_MAX_TOOL_CALLS", DEFAULT_MAX_TOOL_CALLS)
    return CodeMode(
        discovery_tools=[Search(), GetSchemas(), GetTags(), ListTools()],
        sandbox_provider=PreviewMontySandboxProvider(),
        max_tool_calls=max_tool_calls,
    )
