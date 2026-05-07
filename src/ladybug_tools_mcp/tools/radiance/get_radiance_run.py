"""Get Radiance run MCP tool."""

from __future__ import annotations

import time
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.run import get_radiance_run as service


def register(mcp: FastMCP) -> None:
    """Register the get_radiance_run tool."""

    @mcp.tool(
        name="get_radiance_run",
        description="Get one Garden radiance_run record by target or run_id without returning large Radiance result files. Use after start_radiance_grid_run, start_radiance_view_run, or start_radiance_matrix_run. When the user asks to wait or poll until completion, pass wait_seconds instead of making many tight repeated status calls.",
        tags={
            "honeybee-radiance",
            "radiance",
            "run-radiance",
            "daylight",
            "simulation",
            "run",
            "ledger",
            "get",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_radiance_run(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional radiance_run target returned by a start_radiance_*_run tool."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        wait: Annotated[
            int | float | None,
            Field(description="Optional Agent compatibility hint: poll for up to this many seconds before returning. Prefer wait_seconds=60 or higher for real Radiance runs instead of repeated immediate calls."),
        ] = None,
        wait_seconds: Annotated[
            int | float | None,
            Field(description="Alias for wait accepted for Agent compatibility. Prefer this when waiting for a background Radiance run to finish."),
        ] = None,
        poll_interval: Annotated[
            int | float | None,
            Field(description="Optional polling interval in seconds when wait is supplied."),
        ] = None,
    ) -> dict[str, Any]:
        """Get one Radiance simulation run."""
        if wait is None and wait_seconds is not None:
            wait = wait_seconds
        interval = max(float(poll_interval or 1.0), 0.2)
        deadline = time.monotonic() + max(float(wait or 0), 0)
        result = service(garden_root=garden_root, run_target=run_target, run_id=run_id)
        while wait and result.get("status") in {"queued", "running"} and time.monotonic() < deadline:
            time.sleep(min(interval, max(deadline - time.monotonic(), 0.0)))
            result = service(garden_root=garden_root, run_target=run_target, run_id=run_id)
        if wait:
            result.setdefault("summary_view", {})["wait_seconds_requested"] = wait
        return result
