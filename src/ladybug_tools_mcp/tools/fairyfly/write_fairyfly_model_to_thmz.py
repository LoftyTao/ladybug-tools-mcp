"""Write Fairyfly model to THERM THMZ MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.fairyfly.therm import write_fairyfly_model_to_thmz as service


def register(mcp: FastMCP) -> None:
    """Register the write_fairyfly_model_to_thmz tool."""

    @mcp.tool(
        name="write_fairyfly_model_to_thmz",
        description=(
            "Write a Garden Fairyfly two-dimensional heat-transfer model to a "
            "THERM THMZ artifact without starting THERM. Use this when a user "
            "needs an inspectable THERM input file, or before a separate "
            "start_fairyfly_therm_run call."
        ),
        tags={
            "fairyfly",
            "therm",
            "2d-heat-transfer",
            "thmz",
            "export",
            "garden-mode",
            "write",
            "safe",
        },
        timeout=60,
    )
    def write_fairyfly_model_to_thmz(
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
            Field(description="Optional stable run or artifact identifier. Omit to generate one."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional THMZ file stem. Defaults to model."),
        ] = None,
    ) -> dict[str, Any]:
        """Write a Fairyfly model to a THMZ artifact."""
        return service(
            garden_root=garden_root,
            model_target=model_target,
            run_id=run_id,
            name=name,
        )
