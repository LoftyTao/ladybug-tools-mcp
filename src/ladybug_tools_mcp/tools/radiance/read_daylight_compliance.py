"""Read native Radiance daylight compliance results MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the RAD_read_daylight_compliance tool."""

    @mcp.tool(
        name="RAD_read_daylight_compliance",
        description=(
            "Read one completed native Radiance daylight compliance run for "
            "LEED Option 1/2, EN 17037, WELL, or BREEAM 4b. Returns aggregate "
            "credit or criteria summaries, a bounded paginated space/program "
            "summary, indexed output paths, and a reusable visualization_set "
            "target when the recipe VSF exists. Poll the run first with "
            "RAD_poll_simulation. This reads summary JSON/CSV and VSF paths; "
            "it never returns annual illuminance matrices."
        ),
        tags={
            "radiance",
            "compliance",
            "result",
            "summary",
            "visualize",
        },
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def read_daylight_compliance(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually "
                    "GD_create['garden_root']."
                )
            ),
        ],
        run_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Completed radiance_run target returned by a native daylight "
                    "compliance start tool. The recipe type is checked before "
                    "reading results."
                )
            ),
        ],
        page: Annotated[
            int,
            Field(description="One-based space summary page number.", ge=1),
        ] = 1,
        page_size: Annotated[
            int,
            Field(
                description="Number of space rows to return; capped at 50 to keep handoffs compact.",
                ge=1,
                le=50,
            ),
        ] = 25,
    ) -> dict[str, Any]:
        """Read compact daylight compliance outputs."""
        from garden.radiance.compliance_results import (
            read_daylight_compliance as service,
        )

        return service(
            garden_root=garden_root,
            run_target=run_target,
            page=page,
            page_size=page_size,
        )
