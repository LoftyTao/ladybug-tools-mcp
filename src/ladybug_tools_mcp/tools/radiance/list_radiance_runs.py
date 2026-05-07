"""List Radiance runs MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.run import list_radiance_runs as service


def register(mcp: FastMCP) -> None:
    """Register the list_radiance_runs tool."""

    @mcp.tool(
        name="list_radiance_runs",
        description="List Garden radiance_run records for Radiance daylight grid, view, and annual/matrix simulations, optionally filtered by status.",
        tags={
            "honeybee-radiance",
            "radiance",
            "run-radiance",
            "daylight",
            "simulation",
            "run",
            "ledger",
            "list",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_runs(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        status: Annotated[
            str | None,
            Field(description="Optional status filter, for example running, completed, or failed."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Agent context hint accepted for compatibility. Ignored; Radiance runs are listed at Garden scope."),
        ] = None,
    ) -> dict[str, Any]:
        """List Radiance simulation runs."""
        _ = model_target
        return service(garden_root=garden_root, status=status)
