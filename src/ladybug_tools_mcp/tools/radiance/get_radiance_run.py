"""Get Radiance run MCP tool."""

from __future__ import annotations

import time
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    'Register the RAD_poll_simulation tool.'

    @mcp.tool(
        name="RAD_poll_simulation",
        description=(
            "Get one Garden radiance_run record by target or run_id without "
            "returning large Radiance result files. Use after "
            "RAD_start_grid_simulation, RAD_start_view_simulation, "
            "RAD_start_matrix_simulation, RAD_start_imageless_annual_glare, "
            "or a daylight compliance start tool. "
            "When the user asks to wait, "
            "pass wait_seconds to throttle polling. Returns runtime_status "
            "through summary_view.status, poll_next, and report. Treat failed "
            "runtime_status as requiring report review."
        ),
        tags={
            "radiance",
            "simulate",
            "poll",
            "run-ledger",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_radiance_run(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_create['garden_root']; required when saving or reading Garden targets.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden radiance_run target returned by a start_radiance_*_run tool."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        wait_seconds: Annotated[
            int | float | None,
            Field(description="Optional maximum polling duration in seconds before returning."),
        ] = None,
        poll_interval: Annotated[
            int | float | None,
            Field(description="Optional polling interval in seconds when wait_seconds is supplied."),
        ] = None,
    ) -> dict[str, Any]:
        """Get one Radiance simulation run."""
        from garden.radiance.run import get_radiance_run as service

        interval = max(float(poll_interval or 1.0), 0.2)
        deadline = time.monotonic() + max(float(wait_seconds or 0), 0)
        result = service(garden_root=garden_root, run_target=run_target, run_id=run_id)
        while wait_seconds and result.get("status") in {"queued", "running"} and time.monotonic() < deadline:
            time.sleep(min(interval, max(deadline - time.monotonic(), 0.0)))
            result = service(garden_root=garden_root, run_target=run_target, run_id=run_id)
        if wait_seconds:
            result.setdefault("summary_view", {})["wait_seconds_requested"] = wait_seconds
        return result
