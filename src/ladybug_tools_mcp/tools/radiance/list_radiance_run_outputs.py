"""List Radiance run outputs MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.run import list_radiance_run_outputs as service


def register(mcp: FastMCP) -> None:
    """Register the list_radiance_run_outputs tool."""

    @mcp.tool(
        name="list_radiance_run_outputs",
        description="List known output names and paths for one Garden radiance_run without reading large result files after start Radiance daylight grid, view, or matrix runs with radiance parameters. Use before later Radiance postprocess tools.",
        tags={
            "honeybee-radiance",
            "radiance",
            "run-radiance",
            "daylight",
            "simulation",
            "outputs",
            "postprocess",
            "grid",
            "view",
            "matrix",
            "parameters",
            "run",
            "ledger",
            "list",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_run_outputs(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional radiance_run target returned by a start_radiance_*_run tool."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        output_name: Annotated[
            str | None,
            Field(description="Optional Agent output filter hint accepted for compatibility. Ignored; this tool always returns the compact output list."),
        ] = None,
    ) -> dict[str, Any]:
        """List outputs for one Radiance simulation run."""
        _ = output_name
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
