"""Create ConstructionSet MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import create_construction_set as service


def register(mcp: FastMCP) -> None:
    """Register the create_construction_set tool."""

    @mcp.tool(
        name="create_construction_set",
        description="Create a Honeybee Energy ConstructionSet from optional base ConstructionSet and explicit wall, floor, roof/ceiling, aperture, door, shade, and air-boundary overrides. With no base, unspecified slots use Honeybee Energy generic defaults. Prefer Garden Properties Library targets for base_construction_set, wall_set, floor_set, roof_ceiling_set, aperture_set, shade_construction, and air_boundary_construction. wall_set, floor_set, and roof_ceiling_set may be full subset object_dicts or a single OpaqueConstruction dict/target to wrap as the exterior slot. aperture_set may be an ApertureConstructionSet or a WindowConstruction/window construction dict/target to wrap as the exterior window slot; for natural low-U window, U-factor, SHGC, or visible transmittance requests, first create_window_construction with u_factor/shgc/vt and then pass that target as aperture_set. Use garden_root and return_object_dict=false to save the final ConstructionSet. Returns object_dict plus summary_view with all key slot identifiers and modified construction/material counts.",
        tags={
            "honeybee-energy",
            "energy",
            "construction-set",
            "construction",
            "window-construction",
            "aperture-set",
            "exterior-window-slot",
            "low-u-window",
            "u-factor",
            "shgc",
            "material",
            "create",
            "safe",
        },
        timeout=20,
    )
    def create_construction_set(
        identifier: Annotated[str, Field(description="ConstructionSet identifier.")],
        base_construction_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional base ConstructionSet dict, Garden target, or library identifier."
            ),
        ] = None,
        wall_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional WallConstructionSet object_dict override, or OpaqueConstruction dict/Garden target/library identifier to wrap as exterior wall."
            ),
        ] = None,
        floor_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional FloorConstructionSet object_dict override, or OpaqueConstruction dict/Garden target/library identifier to wrap as exterior floor."
            ),
        ] = None,
        roof_ceiling_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional RoofCeilingConstructionSet object_dict override, or OpaqueConstruction dict/Garden target/library identifier to wrap as exterior roof."
            ),
        ] = None,
        aperture_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional ApertureConstructionSet object_dict override, or WindowConstruction dict, Garden target, or library identifier to wrap as the exterior window slot."
            ),
        ] = None,
        door_set: Annotated[
            dict[str, Any] | None,
            Field(description="Optional DoorConstructionSet object_dict override."),
        ] = None,
        shade_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional ShadeConstruction dict, Garden target, or library identifier override."
            ),
        ] = None,
        air_boundary_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional AirBoundaryConstruction or OpaqueConstruction dict, Garden target, or library identifier override."
            ),
        ] = None,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key slot identifiers and counts; full also returns slot_matrix and material_matrix rows."
            ),
        ] = "summary",
        garden_root: Annotated[
            str | None,
            Field(
                description="Optional Garden root for consuming construction targets and saving this ConstructionSet."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Return the full ConstructionSet object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy ConstructionSet object."""
        return service(
            identifier=identifier,
            base_construction_set=base_construction_set,
            wall_set=wall_set,
            floor_set=floor_set,
            roof_ceiling_set=roof_ceiling_set,
            aperture_set=aperture_set,
            door_set=door_set,
            shade_construction=shade_construction,
            air_boundary_construction=air_boundary_construction,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )
