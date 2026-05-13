"""Read Fairyfly THERM result MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.results import read_fairyfly_therm_result as service


def register(mcp: FastMCP) -> None:
    """Register the read_fairyfly_therm_result tool."""

    @mcp.tool(
        name="read_fairyfly_therm_result",
        description=(
            "Read compact temperature or heat-flux statistics from a completed "
            "Fairyfly THERM THMZ file. If the THMZ has not been simulated yet, "
            "returns status no_results with a clear diagnostic instead of fake values."
        ),
        tags={
            "fairyfly",
            "therm",
            "result",
            "temperature",
            "heat-flux",
            "2d-heat-transfer",
            "garden-mode",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def read_fairyfly_therm_result(
        garden_root: Annotated[
            str,
            Field(description="Garden root containing garden.json."),
        ],
        thmz_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional fairyfly_thmz target returned by write_fairyfly_model_to_thmz."),
        ] = None,
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional fairyfly_therm_run target returned by start_fairyfly_therm_run."),
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
