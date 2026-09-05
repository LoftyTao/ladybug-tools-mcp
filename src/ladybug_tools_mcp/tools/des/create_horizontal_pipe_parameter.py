"""Create Dragonfly DES HorizontalPipeParameter MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field



def register(mcp: FastMCP) -> None:
    """Register the DES horizontal pipe parameter tool."""

    @mcp.tool(
        name="DF_des_create_horizontal_pipe_parameter",
        description=(
            "Create a Dragonfly DES HorizontalPipeParameter for thermal connector "
            "pipe sizing, burial, insulation, pressure-drop, and pump defaults. Use "
            "the returned target in fifth-generation or GHE thermal loop creation. "
            "Returns target, summary_view, persistence_receipt, and report."
        ),
        tags={"dragonfly", "district-energy", "author", "parameter", "pipe", "target"},
        timeout=20,
    )
    def create_horizontal_pipe_parameter(
        garden_root: Annotated[str, Field(description="Required Garden root path containing garden.json, usually GD_create['garden_root'].")],
        identifier: Annotated[str, Field(description="Stable identifier for the saved HorizontalPipeParameter target.")],
        buried_depth: Annotated[float | None, Field(description="Optional pipe buried depth in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        diameter_ratio: Annotated[float | None, Field(description="Optional pipe diameter ratio from 11 to 17; omitted values use the Dragonfly Energy SDK default.")] = None,
        pressure_drop_per_meter: Annotated[float | None, Field(description="Optional pressure drop per meter in Pa/m; omitted values use the Dragonfly Energy SDK default.")] = None,
        insulation_conductivity: Annotated[float | None, Field(description="Optional insulation conductivity in W/m-K; omitted values use the Dragonfly Energy SDK default.")] = None,
        insulation_thickness: Annotated[float | None, Field(description="Optional insulation thickness in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        heat_capacity: Annotated[float | None, Field(description="Optional pipe heat capacity in J/m3-K; omitted values use the Dragonfly Energy SDK default.")] = None,
        roughness: Annotated[float | None, Field(description="Optional pipe roughness in meters; omitted values use the Dragonfly Energy SDK default.")] = None,
        hydraulic_diameter: Annotated[float | None, Field(description="Optional hydraulic diameter in meters; omit to keep the SDK Autosize value.")] = None,
        pump_design_head: Annotated[float | None, Field(description="Optional pump design head in Pa; omit to keep the SDK Autosize value.")] = None,
        pump_flow_rate: Annotated[float | None, Field(description="Optional pump flow rate in m3/s; omit to keep the SDK Autosize value.")] = None,
    ) -> dict[str, Any]:
        """Create a Dragonfly DES HorizontalPipeParameter."""
        from garden.dragonfly_des.authoring import create_horizontal_pipe_parameter as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            buried_depth=buried_depth,
            diameter_ratio=diameter_ratio,
            pressure_drop_per_meter=pressure_drop_per_meter,
            insulation_conductivity=insulation_conductivity,
            insulation_thickness=insulation_thickness,
            heat_capacity=heat_capacity,
            roughness=roughness,
            hydraulic_diameter=hydraulic_diameter,
            pump_design_head=pump_design_head,
            pump_flow_rate=pump_flow_rate,
        )
