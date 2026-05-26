"""Start Fairyfly THERM run MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.therm import start_fairyfly_therm_run as service


def register(mcp: FastMCP) -> None:
    'Register the therm_start_simulation tool.'

    @mcp.tool(
        name="start_simulation",
        description=(
            "Start a Fairyfly THERM two-dimensional heat-transfer run for a "
            "Garden Fairyfly model and return a fairyfly_therm_run target. "
            "Use this for a start Fairyfly THERM run request. "
            "THERM execution is Windows-only; when the THERM executable is "
            "unavailable, the tool saves readiness_status=blocked with "
            "intervention_reason=missing_runtime. Returns run_target, "
            "runtime_status, poll_next, and report; poll before reading THERM "
            "or U-factor results. Treat a failed runtime_status as requiring "
            "report review. This is the run starter, not a result reader."
        ),
        tags={"fairyfly", "therm", "simulate", "u-factor", "runtime", "start"},
        timeout=120,
    )
    def start_fairyfly_therm_run(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Fairyfly Model target dict, usually therm_create_model['target']; "
                    "defaults to the Garden base Fairyfly Model."
                )
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable THERM run identifier for the Garden run ledger. Omit to generate one."),
        ] = None,
        silent: Annotated[
            bool,
            Field(description="Run THERM silently when the runtime supports it."),
        ] = True,
    ) -> dict[str, Any]:
        """Start a Fairyfly THERM run and return a run target."""
        return service(
            garden_root=garden_root,
            model_target=model_target,
            run_id=run_id,
            silent=silent,
        )
