"""Project-specific integration around FastMCP Code Mode."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastmcp.experimental.transforms.code_mode import CodeMode, MontySandboxProvider


class PreviewMontySandboxProvider(MontySandboxProvider):
    """Record Web View previews after tools run through Code Mode."""

    async def run(
        self,
        code: str,
        *,
        inputs: dict[str, Any] | None = None,
        external_functions: dict[str, Callable[..., Any]] | None = None,
    ) -> Any:
        if external_functions and "call_tool" in external_functions:
            call_tool = external_functions["call_tool"]
            external_functions = dict(external_functions)

            async def call_tool_with_preview(tool_name: str, arguments: Any) -> Any:
                result = await call_tool(tool_name, arguments)
                from web_view.auto_preview import maybe_record_code_mode_preview

                maybe_record_code_mode_preview(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=result,
                )
                return result

            external_functions["call_tool"] = call_tool_with_preview

        return await super().run(
            code,
            inputs=inputs,
            external_functions=external_functions,
        )


def create_code_mode_transform() -> CodeMode:
    """Create Code Mode with the Web View preview hook."""
    return CodeMode(
        sandbox_provider=PreviewMontySandboxProvider(),
    )
