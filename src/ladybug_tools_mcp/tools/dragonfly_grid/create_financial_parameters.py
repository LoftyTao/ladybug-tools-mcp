"""Create Dragonfly Electric Grid FinancialParameter MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_grid.authoring import create_financial_parameters as service


def register(mcp: FastMCP) -> None:
    """Register the Grid FinancialParameter authoring tool."""

    @mcp.tool(
        name="financial_parameters",
        description=(
            "Create Dragonfly Energy REopt FinancialParameter settings for "
            "Grid/REopt workflows. This authors financial assumptions only; use "
            "df_grid_start_reopt for runtime-gated REopt execution. Returns "
            "target, summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "electric-grid", "reopt", "financial", "author", "target"},
        timeout=20,
    )
    def create_financial_parameters(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json.")],
        identifier: Annotated[str, Field(description="Stable identifier for the FinancialParameter target.")],
        analysis_years: Annotated[int, Field(description="REopt analysis period in years.")] = 25,
        escalation_rate: Annotated[float, Field(description="Annual escalation rate fraction.")] = 0.023,
        tax_rate: Annotated[float, Field(description="Tax rate fraction.")] = 0.26,
        discount_rate: Annotated[float, Field(description="Discount rate fraction.")] = 0.083,
    ) -> dict[str, Any]:
        """Create Dragonfly Energy REopt FinancialParameter settings."""
        return service(
            garden_root=garden_root,
            identifier=identifier,
            analysis_years=analysis_years,
            escalation_rate=escalation_rate,
            tax_rate=tax_rate,
            discount_rate=discount_rate,
        )
