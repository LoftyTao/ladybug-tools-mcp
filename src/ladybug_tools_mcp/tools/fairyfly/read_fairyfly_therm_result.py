"""Read Fairyfly THERM result MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.results import read_fairyfly_therm_result as service


def register(mcp: FastMCP) -> None:
    'Register the therm_read_result tool.'

    @mcp.tool(
        name="read_result",
        description=(
            "Read compact temperature or heat-flux statistics from a Fairyfly "
            "THERM THMZ file. Poll therm_poll_simulation before reading THERM "
            "results from a run_target. If the THMZ has no result arrays, "
            "returns status no_results with a clear diagnostic instead of fake values. "
            "Returns therm_result_target, summary_view, and report when values exist; "
            "it does not calculate U-factor summaries."
        ),
        tags={"fairyfly", "therm", "result", "data-collection", "temperature"},
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def read_fairyfly_therm_result(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']."),
        ],
        thmz_target: Annotated[
            dict[str, Any] | None,
            Field(description='Optional fairyfly_thmz target returned by therm_write_model_to_thmz.'),
        ] = None,
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='Optional completed fairyfly_therm_run target returned by therm_start_simulation. Poll before reading result data.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when thmz_target/run_target are omitted."),
        ] = None,
        data_type: Annotated[
            str,
            Field(description="Result data type: temperature or heat_flux."),
        ] = "temperature",
        include_values: Annotated[
            bool,
            Field(description="Whether to include raw numeric values in the tool response."),
        ] = False,
    ) -> dict[str, Any]:
        """Read Fairyfly THERM temperature or heat-flux result statistics."""
        return service(
            garden_root=garden_root,
            thmz_target=thmz_target,
            run_target=run_target,
            run_id=run_id,
            data_type=data_type,
            include_values=include_values,
        )
