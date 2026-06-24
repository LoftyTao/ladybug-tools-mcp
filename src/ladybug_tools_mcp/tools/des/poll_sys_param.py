"""Poll Dragonfly DES system-parameter run MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_des.runs import poll_sys_param as service


def register(mcp: FastMCP) -> None:
    """Register the DES system-parameter poll tool."""

    @mcp.tool(
        name="poll_sys_param",
        description=(
            "Read the compact Garden ledger for a DES system-parameter run. Use "
            "after the start tool to check runtime_status and confirm whether a "
            "system_parameter_json_target is ready for Modelica candidate steps. "
            "The response keeps the JSON body on disk."
        ),
        tags={"dragonfly", "district-energy", "poll", "runtime", "run", "sizing", "target"},
        timeout=20,
    )
    def poll_sys_param(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; the sys-param run ledger is read from this Garden.")],
        run_target: Annotated[dict[str, Any] | None, Field(description="DES system-parameter run target returned by the start tool.") ] = None,
        run_id: Annotated[str | None, Field(description="System-parameter run id to poll when run_target is not available.") ] = None,
    ) -> dict[str, Any]:
        """Poll a DES system-parameter run."""
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)
