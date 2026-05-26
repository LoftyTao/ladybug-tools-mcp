"""List Radiance run outputs MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.run import list_radiance_run_outputs as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_list_run_outputs tool.'

    @mcp.tool(
        name="list_run_outputs",
        description=(
            "List indexed outputs for one Garden Radiance run, including grid "
            "results, HDR images, matrices, parameters, and reports when "
            "present. Use after radiance_poll_simulation reports a finished "
            "runtime_status. This is an output inventory; it does not read "
            "result payloads or convert artifacts. Returns matches, "
            "summary_view, and report."
        ),
        tags={
            "artifact",
            "outputs",
            "radiance",
            "result",
            "search",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_run_outputs(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional radiance_run target returned by a start_radiance_*_run tool. Poll the run before listing outputs."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is not supplied."),
        ] = None,
    ) -> dict[str, Any]:
        """List outputs for one Radiance simulation run."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
