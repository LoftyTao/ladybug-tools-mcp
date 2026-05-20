"""FastMCP server factory for Ladybug Tools MCP."""

from __future__ import annotations

import ast
import asyncio
import contextlib
import io
import re
import textwrap
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Any, Callable

from fastmcp import FastMCP
from fastmcp.experimental.transforms.code_mode import (
    CodeMode,
    GetSchemas,
    GetToolCatalog,
    MontySandboxProvider,
    SearchFn,
    ToolDetailLevel,
    _render_tools,
)
from fastmcp.server.context import Context
from fastmcp.server.providers.skills import SkillProvider
from fastmcp.server.transforms.search import BM25SearchTransform
from fastmcp.server.transforms.visibility import Visibility
from fastmcp.tools.base import Tool

from ladybug_tools_mcp import __version__
from ladybug_tools_mcp.registry import register_tools
from web_view.auto_preview import maybe_record_code_mode_preview

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_PATH = PROJECT_ROOT / ".agents" / "skills" / "ladybug-tools-mcp-use"
_TIME_SLEEP_RE = re.compile(r"\btime\.sleep\s*\(")


def _coerce_optional_positive_int(value: int | str | None, *, field_name: str) -> int | None:
    if value is None or isinstance(value, int):
        return value
    text = value.strip()
    if not text:
        return None
    try:
        parsed = int(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an integer or numeric string.") from exc
    if parsed < 0:
        raise ValueError(f"{field_name} must be greater than or equal to 0.")
    return parsed


class LenientCodeModeSearch:
    """Code Mode search tool that accepts numeric-string limits from Agents."""

    def __init__(
        self,
        *,
        search_fn: SearchFn | None = None,
        name: str = "search",
        default_detail: ToolDetailLevel | None = None,
        default_limit: int | None = None,
    ) -> None:
        if search_fn is None:
            _bm25 = BM25SearchTransform(max_results=default_limit or 50)
            search_fn = _bm25._search
        self._search_fn = search_fn
        self._name = name
        self._default_detail: ToolDetailLevel = default_detail or "brief"
        self._default_limit = default_limit

    def __call__(self, get_catalog: GetToolCatalog) -> Tool:
        search_fn = self._search_fn
        default_detail = self._default_detail
        default_limit = self._default_limit

        async def search(
            query: Annotated[str, "Search query to find available tools"],
            tags: Annotated[
                list[str] | None,
                "Filter to tools with any of these tags before searching",
            ] = None,
            detail: Annotated[
                ToolDetailLevel,
                "'brief' for names and descriptions, 'detailed' for parameter schemas as markdown, 'full' for complete JSON schemas",
            ] = default_detail,
            limit: Annotated[
                int | str | None,
                "Maximum number of results to return. Numeric strings are accepted.",
            ] = default_limit,
            ctx: Context = None,  # type: ignore[assignment]
        ) -> str:
            """Search for available tools by query.

            Returns matching tools ranked by relevance.
            """
            limit_value = _coerce_optional_positive_int(limit, field_name="limit")
            catalog = await get_catalog(ctx)
            catalog_size = len(catalog)
            tools: Sequence[Tool] = catalog
            if tags:
                tag_set = set(tags)
                has_untagged = "untagged" in tag_set
                real_tags = tag_set - {"untagged"}
                tools = [
                    tool
                    for tool in tools
                    if (tool.tags & real_tags) or (has_untagged and not tool.tags)
                ]
            results = await search_fn(tools, query)
            if limit_value is not None:
                results = results[:limit_value]
            rendered = _render_tools(results, detail)
            if len(results) < catalog_size and detail != "full":
                rendered = f"{len(results)} of {catalog_size} tools:\n\n{rendered}"
            return rendered

        return Tool.from_function(fn=search, name=self._name)


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


class QuietMontySandboxProvider:
    """Run Code Mode while preventing user-code prints from corrupting stdio."""

    def __init__(self) -> None:
        self._provider = MontySandboxProvider()

    def _with_call_tool_preview(
        self,
        external_functions: dict[str, Callable[..., Any]] | None,
    ) -> dict[str, Callable[..., Any]] | None:
        if not external_functions or "call_tool" not in external_functions:
            return external_functions

        call_tool = external_functions["call_tool"]
        enhanced = dict(external_functions)

        async def call_tool_with_preview(tool_name: str, arguments: Any) -> Any:
            result = await call_tool(tool_name, arguments)
            maybe_record_code_mode_preview(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
            )
            return result

        enhanced["call_tool"] = call_tool_with_preview
        return enhanced

    async def run(
        self,
        code: str,
        *,
        inputs: dict[str, Any] | None = None,
        external_functions: dict[str, Callable[..., Any]] | None = None,
    ) -> Any:
        code = textwrap.dedent(code)
        code = _normalize_code_mode_sleep_calls(code)
        code = _normalize_code_mode_trailing_expression_return(code)
        external_functions = _with_code_mode_helpers(external_functions)
        external_functions = self._with_call_tool_preview(external_functions)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return await self._provider.run(
                code,
                inputs=inputs,
                external_functions=external_functions,
            )


def create_mcp() -> FastMCP:
    """Create the Ladybug Tools MCP server.

    The public MCP surface is Code Mode only: search, get_schema, execute.
    Domain tools are called inside execute with await call_tool(name, arguments).
    """
    providers = []
    if SKILL_PATH.exists():
        providers.append(SkillProvider(SKILL_PATH, supporting_files="template"))

    transforms = [
        Visibility(
            False,
            tags={"debug", "internal", "experimental"},
        ),
        CodeMode(
            sandbox_provider=QuietMontySandboxProvider(),
            discovery_tools=[LenientCodeModeSearch(), GetSchemas()],
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
                "For UWG Alternative Weather workflows, create or select a Dragonfly "
                "model, create or select a Garden-managed `weather_file` target or "
                "Garden-relative EPW, call `create_uwg_simulation_parameter` when "
                "custom UWG settings are needed, then call `start_uwg_run` and poll "
                "`get_uwg_run`; use the returned morphed `weather_target` with "
                "`start_energy_run` only when downstream Energy simulation is requested. "
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
            ),
        ),
    ]

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


mcp = create_mcp()


if __name__ == "__main__":
    mcp.run()
