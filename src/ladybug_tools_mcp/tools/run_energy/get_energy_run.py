"""Get Energy simulation run MCP tool."""

from __future__ import annotations

import time
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.annual import get_energy_run as service


def register(mcp: FastMCP) -> None:
    """Register the get_energy_run tool."""

    @mcp.tool(
        name="get_energy_run",
        description="Get one Garden energy_run record by target or run_id without returning large result files. Use after start_energy_run. When the user asks to wait or poll until completion, pass wait_seconds instead of making many repeated immediate status calls.",
        tags={
            "run-energy",
            "energy",
            "simulation",
            "run",
            "ledger",
            "get",
            "read-only",
            "safe",
        },
        annotations={"readOnlyHint": True},
        timeout=180,
    )
    def get_energy_run(
        garden_root: Annotated[
            str, Field(description="Garden root containing garden.json.")
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional energy_run target returned by run_energy."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        wait_seconds: Annotated[
            int | float | None,
            Field(
                description="Optional polling duration in seconds before returning."
            ),
        ] = None,
        poll_interval: Annotated[
            int | float | None,
            Field(description="Optional polling interval in seconds when wait is supplied."),
        ] = None,
    ) -> dict[str, Any]:
        """Get one Energy simulation run."""
        requested_wait = max(float(wait_seconds or 0), 0.0)
        applied_wait = min(requested_wait, 150.0)
        interval = max(float(poll_interval or 1.0), 0.2)
        deadline = time.monotonic() + applied_wait
        result = service(garden_root=garden_root, run_target=run_target, run_id=run_id)
        while applied_wait and time.monotonic() < deadline:
            status = (
                result.get("summary_view", {})
                .get("run", {})
                .get("status")
            )
            if status not in {"queued", "running"}:
                break
            time.sleep(min(interval, max(deadline - time.monotonic(), 0.0)))
            result = service(garden_root=garden_root, run_target=run_target, run_id=run_id)
        if requested_wait:
            result.setdefault("summary_view", {})["wait_seconds_requested"] = wait_seconds
            result.setdefault("summary_view", {})["wait_seconds_applied"] = applied_wait
        return result
