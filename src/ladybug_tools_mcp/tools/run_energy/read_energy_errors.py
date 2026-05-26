"""Read Energy ERR MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.annual import read_energy_errors as service


def register(mcp: FastMCP) -> None:
    'Register the energyplus_read_errors tool.'

    @mcp.tool(
        name="read_errors",
        description=(
            "Read a bounded EnergyPlus ERR text output for one Garden energy_run "
            "target and summarize warning/severe/fatal counts. If the ERR "
            "contains Severe or Fatal errors, the response returns report.status "
            "blocked with energy_blocker, last_severe_error, severe_errors, and "
            "fatal_errors so the caller can report a precise EnergyPlus blocker. "
            "If the ERR file is missing, this returns a missing_err_output blocker "
            "instead of raising, with recommended_next_tools for run/status checks."
        ),
        tags={
            "energy",
            "result",
            "err",
            "diagnostics",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def read_energy_errors(
        garden_root: Annotated[
            str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='Energy run target returned by energyplus_start_simulation; pass run_target unless you provide run_id.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        max_chars: Annotated[
            int, Field(description="Maximum ERR text characters to return.")
        ] = 12000,
    ) -> dict[str, Any]:
        """Read Energy ERR output."""
        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            max_chars=max_chars,
        )
