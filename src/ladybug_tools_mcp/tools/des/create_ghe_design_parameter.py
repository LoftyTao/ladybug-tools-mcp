"""Create Dragonfly DES GHEDesignParameter MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the DES GHE design parameter tool."""

    @mcp.tool(
        name="DF_des_create_ghe_design_parameter",
        description=(
            "Create a Dragonfly DES GHEDesignParameter for GHE sizing criteria, "
            "including flow rate, flow type, entering-fluid temperature limits, "
            "simulation month count, and sizing method. Returns target, summary_view, "
            "persistence_receipt, and report."
        ),
        tags={"dragonfly", "district-energy", "author", "geothermal", "parameter", "sizing", "target"},
        timeout=20,
    )
    def create_ghe_design_parameter(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually GD_create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved GHEDesignParameter target.")],
        flow_rate: Annotated[float | None, Field(description="Optional GHE design flow rate; omitted values use the Dragonfly Energy SDK default.")] = None,
        flow_type: Annotated[str | None, Field(description="Optional SDK flow type such as Borehole; omitted values use the Dragonfly Energy SDK default.")] = None,
        max_eft: Annotated[float | None, Field(description="Optional maximum entering-fluid temperature in Celsius; omitted values use the Dragonfly Energy SDK default.")] = None,
        min_eft: Annotated[float | None, Field(description="Optional minimum entering-fluid temperature in Celsius; omitted values use the Dragonfly Energy SDK default.")] = None,
        month_count: Annotated[int | None, Field(description="Optional simulation month count for design sizing; omitted values use the Dragonfly Energy SDK default.")] = None,
        method: Annotated[str | None, Field(description="Optional SDK design method such as AreaProportional; omitted values use the Dragonfly Energy SDK default.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES GHEDesignParameter."""
        from garden.dragonfly_des.authoring import create_ghe_design_parameter as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            flow_rate=flow_rate,
            flow_type=flow_type,
            max_eft=max_eft,
            min_eft=min_eft,
            month_count=month_count,
            method=method,
        )
