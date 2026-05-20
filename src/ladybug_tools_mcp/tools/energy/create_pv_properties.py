"""Create PV Properties MCP tool."""

from __future__ import annotations
from typing import Annotated
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.ventilation import create_pv_properties as service


def register(mcp: FastMCP) -> None:
    """Register the create_pv_properties tool."""

    @mcp.tool(
        name="create_pv_properties",
        description="Create Honeybee Energy PVProperties for shade-attached photovoltaic electricity generation on Honeybee Shades. Use this for PV panels, solar photovoltaics, PVWatts, rated efficiency, active area fraction, mounting_type, and shade-attached electricity generation. mounting_type must be one of FixedOpenRack, FixedRoofMounted, OneAxis, OneAxisBacktracking, or TwoAxis; use FixedRoofMounted, not FixedRoofMount or FlushMount. In Garden mode, pass garden_root and return_object_dict=false to save directly as a pv_properties target for edit_honeybee_shade.pv_properties. Inverter and DC-to-AC sizing belong in create_electric_load_center; not pv_type and not dc_to_ac_size_ratio.",
        tags={
            "honeybee-energy",
            "garden-mode",
            "pv",
            "photovoltaic",
            "solar",
            "electricity-generation",
            "pvwatts",
            "shade",
            "write",
            "safe",
        },
        timeout=20,
    )
    def create_pv_properties(
        identifier: Annotated[
            str,
            Field(description="Unique PVProperties identifier."),
        ],
        rated_efficiency: Annotated[
            float,
            Field(description="PV module rated efficiency from 0 to 1."),
        ] = 0.15,
        active_area_fraction: Annotated[
            float,
            Field(description="Fraction of parent Shade area covered by active PV cells."),
        ] = 0.9,
        module_type: Annotated[
            str | None,
            Field(description="Optional module type: Standard, Premium, or ThinFilm. If omitted, SDK infers from efficiency."),
        ] = None,
        mounting_type: Annotated[
            str,
            Field(description="PV mounting type, for example FixedOpenRack, FixedRoofMounted, OneAxis, OneAxisBacktracking, or TwoAxis. Use exactly FixedRoofMounted, not FixedRoofMount."),
        ] = "FixedOpenRack",
        system_loss_fraction: Annotated[
            float,
            Field(description="Fraction of electricity output lost to soiling, wiring, mismatch, availability, age, and related losses."),
        ] = 0.14,
        tracking_ground_coverage_ratio: Annotated[
            float,
            Field(description="Ground coverage ratio for one-axis tracking PV arrays."),
        ] = 0.4,
        garden_root: Annotated[
            str | None,
            Field(description="Optional Garden root. If provided, saves directly to Garden Properties Library."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="When garden_root is provided, set false to return only compact target and summary."),
        ] = True,
    ) -> dict:
        """Create PV properties."""
        return service(
            identifier=identifier,
            rated_efficiency=rated_efficiency,
            active_area_fraction=active_area_fraction,
            module_type=module_type,
            mounting_type=mounting_type,
            system_loss_fraction=system_loss_fraction,
            tracking_ground_coverage_ratio=tracking_ground_coverage_ratio,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
