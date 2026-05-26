"""Get Energy simulation run MCP tool."""

from __future__ import annotations

import time
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.run_energy.annual import get_energy_run as service


def register(mcp: FastMCP) -> None:
    'Register the energyplus_poll_simulation tool.'

    @mcp.tool(
        name="poll_simulation",
        description='Get one Garden energy_run record by run_target or run_id without returning large result files. Use after energyplus_start_simulation. When the user asks to wait, pass wait_seconds instead of repeated immediate polling; this waits in the wrapper and does not change the EnergyPlus engine timeout. Returns runtime_status through summary_view.status, summary_view.run, result_evidence, summary_view.recommended_next_tools, summary_view.final_answer_guidance, and report. Treat a failed runtime_status as requiring report review. This polling tool has no top-level poll_next field.',
        tags={
            "energy",
            "simulate",
            "poll",
            "run",
        },
        annotations={"readOnlyHint": True},
        timeout=180,
    )
    def get_energy_run(
        garden_root: Annotated[
            str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='Energy run target returned by energyplus_start_simulation; pass run_target for polling unless you provide run_id.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        wait_seconds: Annotated[
            int | float | None,
            Field(
                description="Optional wrapper-side polling duration in seconds before returning; does not change the EnergyPlus/OpenStudio simulation timeout."
            ),
        ] = None,
        poll_interval: Annotated[
            int | float | None,
            Field(description="Optional wrapper-side polling interval in seconds when wait_seconds is supplied."),
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
