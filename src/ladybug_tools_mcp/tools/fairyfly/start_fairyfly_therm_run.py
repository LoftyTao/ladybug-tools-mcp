"""Start Fairyfly THERM run MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.therm import start_fairyfly_therm_run as service


def register(mcp: FastMCP) -> None:
    """Register the start_fairyfly_therm_run tool."""

    @mcp.tool(
        name="start_fairyfly_therm_run",
        description=(
            "Start a Fairyfly THERM two-dimensional heat-transfer run for a "
            "Garden Fairyfly model and return a fairyfly_therm_run target. "
            "Use this for a start Fairyfly THERM run request. "
            "THERM execution is Windows-only; when the THERM executable is "
            "unavailable, the tool saves a blocked run record with the disabled "
            "reason instead of pretending the simulation succeeded."
        ),
        tags={
            "fairyfly",
            "therm",
            "simulation",
            "2d-heat-transfer",
            "u-factor",
            "run",
            "garden-mode",
            "write",
            "safe",
        },
        timeout=120,
    )
    def start_fairyfly_therm_run(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Fairyfly model target. Defaults to the Garden base Fairyfly model."
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable THERM run identifier. Omit to generate one."),
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
