"""Intent-driven EnergyPlus result summary MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the EP_summarize_results tool."""

    @mcp.tool(
        name="EP_summarize_results",
        description=(
            "Summarize one completed Garden energy_run by intent. Use "
            "summary_kind=energy_use, loads, or peaks; the tool reads existing "
            "EUI, SQL, and sizing outputs, returns compact metrics with units, "
            "period, scope, aggregation, conversion, and source provenance, "
            "and never starts a run. If outputs are insufficient, inspect "
            "energy_blocker.output_request_suggestion and use the suggested "
            "EP_create_output_request before the next EP_start_simulation. "
            "Use EP_read_result_data for expert-level raw SQL/DataCollection "
            "access."
        ),
        tags={"energy", "result", "summary", "loads", "peaks", "eui"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def summarize_energy_results(
        garden_root: Annotated[
            str,
            Field(
                description="Garden root path containing garden.json and the energy_run target."
            ),
        ],
        summary_kind: Annotated[
            str,
            Field(
                description="Summary intent: energy_use for EUI/end uses, loads for annual or monthly end-use loads, or peaks for heating/cooling sizing peaks."
            ),
        ],
        energy_run_target: Annotated[
            dict[str, Any],
            Field(
                description="Energy run target returned by EP_start_simulation or another Energy run tool."
            ),
        ],
        scope: Annotated[
            str | dict[str, Any] | None,
            Field(
                description="Optional zone or identifier substring scope. For energy_use, the EUI remains whole-building and the scope is recorded but not applied."
            ),
        ] = None,
        period: Annotated[
            str,
            Field(description="Requested time range: annual or monthly."),
        ] = "annual",
        unit_preference: Annotated[
            str | None,
            Field(
                description="Optional target unit such as kWh, MWh, W, or kW. Unsupported conversions retain the source unit and return a warning."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Return a compact intent-driven Energy result summary."""
        from garden.run_energy.summary import summarize_energy_results as service

        return service(
            garden_root=garden_root,
            energy_run_target=energy_run_target,
            summary_kind=summary_kind,
            scope=scope,
            period=period,
            unit_preference=unit_preference,
        )
