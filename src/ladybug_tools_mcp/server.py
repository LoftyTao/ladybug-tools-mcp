"""FastMCP server factory for Ladybug Tools MCP."""

from __future__ import annotations

import ast
import asyncio
import contextlib
import io
import re
import textwrap
from pathlib import Path
from typing import Any, Callable

from fastmcp import FastMCP
from fastmcp.experimental.transforms.code_mode import CodeMode, MontySandboxProvider
from fastmcp.server.providers.skills import SkillProvider
from fastmcp.server.transforms.search import BM25SearchTransform
from fastmcp.server.transforms.visibility import Visibility

from ladybug_tools_mcp import __version__
from ladybug_tools_mcp.registry import register_tools

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_PATH = PROJECT_ROOT / ".agents" / "skills" / "ladybug-tools-mcp-use"
_PRINT_CALL_RE = re.compile(r"^(?P<indent>\s*)print\s*\(")
_IMPORT_LINE_RE = re.compile(r"^(?P<indent>\s*)(?:from\s+\S+\s+import\s+.+|import\s+.+)\s*$")
_TIME_SLEEP_RE = re.compile(r"\btime\.sleep\s*\(")
_TOOL_RESULT_VALUE_ACCESS_RE = re.compile(
    r"(?P<name>\b[A-Za-z_][A-Za-z0-9_]*\b)\s*\[\s*([\"'])value\2\s*\]"
)
_GARDEN_RESULT_TARGET_ACCESS_RE = re.compile(
    r"(?P<name>\b[A-Za-z_]*garden[A-Za-z0-9_]*\b)\s*\[\s*([\"'])target\2\s*\]",
    re.IGNORECASE,
)
_LITERAL_GARDEN_ROOT_ASSIGNMENT_RE = re.compile(
    r"(?m)^\s*garden_root\s*=\s*(?:r|R)?(?P<quote>[\"'])(?P<path>.+?)(?P=quote)\s*$"
)
_DIRECT_AWAIT_TOOL_CALL_RE = re.compile(
    r"\bawait\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("
)
_GARDEN_CONTEXT_AUTOFILL_EXCLUDED = {
    "compose_visualization_sets",
    "create_2d_legend_parameter",
    "create_radiance_parameters",
    "edit_2d_legend_parameter",
    "list_gardens",
    "search_epw_map",
}


def _suppress_code_mode_print_calls(code: str) -> str:
    """Replace top-level print statements in Code Mode snippets with no-ops."""
    lines = code.splitlines(keepends=True)
    rewritten: list[str] = []
    skip_print_call = False
    paren_balance = 0

    for line in lines:
        if skip_print_call:
            paren_balance += line.count("(") - line.count(")")
            if paren_balance <= 0:
                skip_print_call = False
            continue

        match = _PRINT_CALL_RE.match(line)
        if match is None:
            rewritten.append(line)
            continue

        indent = match.group("indent")
        newline = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
        rewritten.append(f"{indent}None{newline}")
        paren_balance = line.count("(") - line.count(")")
        if paren_balance > 0:
            skip_print_call = True

    return "".join(rewritten)


def _suppress_code_mode_imports(code: str) -> str:
    """Replace import lines in Code Mode snippets with no-ops.

    Monty Code Mode exposes `call_tool` directly and intentionally does not
    provide a normal Python module environment. Low-intelligence models often
    invent imports before calling `call_tool`, causing retries that burn tokens.
    """
    rewritten: list[str] = []
    for line in code.splitlines(keepends=True):
        match = _IMPORT_LINE_RE.match(line.rstrip("\r\n"))
        if match is None:
            rewritten.append(line)
            continue
        newline = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
        rewritten.append(f"{match.group('indent')}None{newline}")
    return "".join(rewritten)


def _normalize_code_mode_sleep_calls(code: str) -> str:
    """Convert common time.sleep calls into the injected async sleep helper."""
    return _TIME_SLEEP_RE.sub("await sleep(", code)


def _with_code_mode_helpers(
    external_functions: dict[str, Callable[..., Any]] | None,
) -> dict[str, Callable[..., Any]] | None:
    """Expose safe helper functions for common Agent polling snippets."""
    if external_functions is None:
        return None
    enhanced = dict(external_functions)

    async def sleep(seconds: int | float) -> None:
        await asyncio.sleep(max(float(seconds), 0.0))

    enhanced.setdefault("sleep", sleep)
    return enhanced


def _normalize_code_mode_tool_result_value_access(code: str) -> str:
    """Normalize common MCP wrapper access in Code Mode snippets.

    Some low-intelligence models assume `await call_tool(...)` returns an SDK-style
    wrapper with a `value` field. FastMCP Code Mode returns the structured tool
    result directly, so `result["value"]["target"]` should be `result["target"]`.
    """
    return _TOOL_RESULT_VALUE_ACCESS_RE.sub(r"\g<name>", code)


def _normalize_code_mode_garden_root_access(code: str) -> str:
    """Normalize Garden result target access when a string root is needed."""
    return _GARDEN_RESULT_TARGET_ACCESS_RE.sub(r"\g<name>['garden_root']", code)


def _normalize_code_mode_trailing_expression_return(code: str) -> str:
    """Treat a final bare expression as the explicit Code Mode return value."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code
    if not tree.body:
        return code
    last = tree.body[-1]
    if not isinstance(last, ast.Expr):
        return code
    if isinstance(last.value, ast.Constant) and last.value.value is None:
        return code
    lines = code.splitlines(keepends=True)
    index = last.lineno - 1
    lines[index] = "return " + lines[index]
    return "".join(lines)


def _direct_tool_function_names(code: str) -> set[str]:
    """Find direct awaited tool-function shapes commonly produced by Agents."""
    blocked_names = {"call_tool"}
    return {
        match.group("name")
        for match in _DIRECT_AWAIT_TOOL_CALL_RE.finditer(code)
        if match.group("name") not in blocked_names
    }


def _with_direct_tool_function_proxies(
    external_functions: dict[str, Callable[..., Any]] | None,
    code: str,
) -> dict[str, Callable[..., Any]] | None:
    """Expose direct tool-name async proxies inside Code Mode.

    Low-intelligence Agents often write `from ladybug_tools_mcp import
    create_garden` and then call `await create_garden(...)`. Import lines are
    suppressed because the sandbox has no normal module environment, but the
    direct call shape is recoverable by delegating to the injected `call_tool`.
    """
    if not external_functions or "call_tool" not in external_functions:
        return external_functions

    call_tool = external_functions["call_tool"]
    enhanced = dict(external_functions)

    for tool_name in _direct_tool_function_names(code):
        if tool_name in enhanced:
            continue

        async def tool_proxy(
            *args: Any,
            __tool_name: str = tool_name,
            **kwargs: Any,
        ) -> Any:
            if len(args) == 1 and isinstance(args[0], dict) and not kwargs:
                arguments = dict(args[0])
            elif not args:
                arguments = dict(kwargs)
            else:
                raise TypeError(
                    f"{__tool_name} proxy accepts keyword arguments or one dict."
                )
            return await call_tool(__tool_name, arguments)

        enhanced[tool_name] = tool_proxy

    return enhanced


def _find_garden_root(value: Any) -> str | None:
    """Find a Garden root string in compact MCP results or arguments."""
    if isinstance(value, dict):
        for key in ("garden_root", "root_dir"):
            item = value.get(key)
            if isinstance(item, str) and item:
                return item
        for item in value.values():
            found = _find_garden_root(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_garden_root(item)
            if found:
                return found
    return None


def _literal_garden_root_from_code(code: str) -> str | None:
    """Extract a literal garden_root assignment from an Agent Code Mode block."""
    match = _LITERAL_GARDEN_ROOT_ASSIGNMENT_RE.search(code)
    if match is None:
        return None
    path = match.group("path")
    return path if path else None


def _normalize_code_mode_tool_arguments(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Normalize narrow, observed Agent handoff drift before schema validation."""
    normalized = dict(arguments)
    if (
        tool_name == "download_epw"
        and "epw_map_target" not in normalized
        and isinstance(normalized.get("target"), dict)
    ):
        normalized["epw_map_target"] = normalized.pop("target")
    return normalized


class QuietMontySandboxProvider:
    """Run Code Mode while preventing user-code prints from corrupting stdio."""

    def __init__(self) -> None:
        self._provider = MontySandboxProvider()
        self._last_garden_root: str | None = None
        self._execute_last_tool_result: Any = None

    def _with_call_tool_context(
        self,
        external_functions: dict[str, Callable[..., Any]] | None,
    ) -> dict[str, Callable[..., Any]] | None:
        if not external_functions or "call_tool" not in external_functions:
            return external_functions

        call_tool = external_functions["call_tool"]
        enhanced = dict(external_functions)

        async def call_tool_with_context(tool_name: str, arguments: Any) -> Any:
            if isinstance(arguments, dict):
                arguments = _normalize_code_mode_tool_arguments(tool_name, arguments)
                garden_root = _find_garden_root(arguments)
                if garden_root:
                    self._last_garden_root = garden_root
                elif (
                    self._last_garden_root
                    and "garden_root" not in arguments
                    and tool_name not in _GARDEN_CONTEXT_AUTOFILL_EXCLUDED
                ):
                    arguments["garden_root"] = self._last_garden_root

            result = await call_tool(tool_name, arguments)
            self._execute_last_tool_result = result
            garden_root = _find_garden_root(result)
            if garden_root:
                self._last_garden_root = garden_root
            return result

        enhanced["call_tool"] = call_tool_with_context
        return enhanced

    async def run(
        self,
        code: str,
        *,
        inputs: dict[str, Any] | None = None,
        external_functions: dict[str, Callable[..., Any]] | None = None,
    ) -> Any:
        code = textwrap.dedent(code)
        code = _normalize_code_mode_tool_result_value_access(code)
        code = _normalize_code_mode_garden_root_access(code)
        code = _suppress_code_mode_imports(code)
        code = _normalize_code_mode_sleep_calls(code)
        code = _suppress_code_mode_print_calls(code)
        code = _normalize_code_mode_trailing_expression_return(code)
        literal_garden_root = _literal_garden_root_from_code(code)
        if literal_garden_root:
            self._last_garden_root = literal_garden_root
        external_functions = _with_code_mode_helpers(external_functions)
        external_functions = self._with_call_tool_context(external_functions)
        external_functions = _with_direct_tool_function_proxies(
            external_functions,
            code,
        )
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self._execute_last_tool_result = None
            result = await self._provider.run(
                code,
                inputs=inputs,
                external_functions=external_functions,
            )
            if result is None and self._execute_last_tool_result is not None:
                return self._execute_last_tool_result
            return result


def create_mcp(*, code_mode: bool = False) -> FastMCP:
    """Create the single Ladybug Tools MCP service.

    The production server enables FastMCP Code Mode to expose a small
    discovery/execute surface for token-efficient multi-tool workflows. Tests
    and legacy clients can still request the older search_tools/call_tool
    surface with ``code_mode=False``.
    """
    providers = []
    if SKILL_PATH.exists():
        providers.append(SkillProvider(SKILL_PATH, supporting_files="template"))

    transforms = [
        Visibility(False, tags={"debug", "internal", "experimental"}),
    ]
    if code_mode:
        transforms.append(
            CodeMode(
                sandbox_provider=QuietMontySandboxProvider(),
                execute_description=(
                    "The only way to run Ladybug Tools domain tools in Code Mode. "
                    "Call domain tools inside this Python block with "
                    "`await call_tool(tool_name: str, arguments: dict)`. "
                    "Tool names returned by search/get_schema are strings for "
                    "call_tool only; never call them as outer MCP tools. "
                    "Each execute call is isolated; variables do not persist "
                    "between execute calls. Do not import modules or use asyncio; "
                    "call tools sequentially. Do not call `call_tool('search', ...)` "
                    "or `call_tool('get_schema', ...)` inside execute; search and "
                    "get_schema are outer Code Mode tools. "
                    "execute code is Python, so use True, False, and None instead "
                    "of JSON true, false, and null. "
                    "For blank-project workflows, call `create_garden` before "
                    "any tool that takes `garden_root`; a "
                    "directory alone is not a Garden until `garden.json` exists. "
                    "For energy simulation in Agent workflows, call "
                    "`search_epw_map` without `garden_root`, then `download_epw` "
                    "with the selected `epw_map_target` and the same `garden_root`; "
                    "weather files are managed by the Garden, not a separate folder. "
                    "Then call `start_energy_run` and poll `get_energy_run`; avoid blocking "
                    "`run_energy` unless the user explicitly asks to wait. "
                    "For Radiance simulation, first attach SensorGrids or Views to the "
                    "Honeybee model, create a `radiance_sky_file` for point-in-time "
                    "grid/view recipes or a `wea_file` for annual/matrix recipes, create "
                    "Radiance parameters when needed, then call `start_radiance_grid_run`, "
                    "`start_radiance_view_run`, or `start_radiance_matrix_run` and poll "
                    "`get_radiance_run`. "
                    "Chain dependent create/edit/simulate calls in one block and "
                    "`await call_tool` returns the tool result dict directly; use "
                    "`result['target']` or `result['garden_root']`, not `result['value']`. "
                    "Return one compact JSON-compatible dictionary. Do not print "
                    "and do not serialize tool results with json.dumps."
                )
            )
        )
    else:
        transforms.append(BM25SearchTransform(max_results=8))

    mcp = FastMCP(
        "Ladybug Tools MCP",
        version=__version__,
        providers=providers,
        transforms=transforms,
        on_duplicate="error",
        strict_input_validation=True,
        mask_error_details=False,
    )
    register_tools(mcp)
    return mcp


mcp = create_mcp(code_mode=True)


if __name__ == "__main__":
    mcp.run()
