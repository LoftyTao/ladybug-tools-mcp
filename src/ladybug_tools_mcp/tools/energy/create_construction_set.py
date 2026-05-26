"""Create ConstructionSet MCP tool."""

from __future__ import annotations
from typing import Annotated, Any
from fastmcp import FastMCP
from pydantic import Field
from garden.energy.constructionsets import create_construction_set as service


def register(mcp: FastMCP) -> None:
    'Register the energy_create_construction_set tool.'

    @mcp.tool(
        name='create_construction_set',
        description='Create a saved Honeybee Energy ConstructionSet, the envelope default set for wall, floor, roof/ceiling, aperture, door, shade, and air-boundary constructions. Start from a standards-library or Garden base ConstructionSet, then pass subset object_dict overrides or direct construction targets for common slots. Returns object_dict plus summary_view, or saved target plus persistence_receipt when garden_root and return_object_dict=false are supplied; use energy_create_window_construction first for low-U, SHGC, or visible-transmittance window requests.',
        tags={
            "energy",
            "construction-set",
            "construction",
            "envelope",
            "author",
        },
        timeout=20,
    )
    def create_construction_set(
        identifier: Annotated[str, Field(description="ConstructionSet identifier.")],
        base_construction_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional base ConstructionSet object_dict, Garden target, or standards-library identifier such as a generic construction set."
            ),
        ] = None,
        wall_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional WallConstructionSet object_dict override, or OpaqueConstruction dict/Garden target/standards identifier to wrap as the exterior wall slot."
            ),
        ] = None,
        floor_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional FloorConstructionSet object_dict override, or OpaqueConstruction dict/Garden target/standards identifier to wrap as the exterior floor slot."
            ),
        ] = None,
        roof_ceiling_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional RoofCeilingConstructionSet object_dict override, or OpaqueConstruction dict/Garden target/standards identifier to wrap as the exterior roof slot."
            ),
        ] = None,
        aperture_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional ApertureConstructionSet object_dict override, or WindowConstruction dict, Garden target, or standards identifier to wrap as the exterior fixed-window slot."
            ),
        ] = None,
        door_set: Annotated[
            dict[str, Any] | None,
            Field(description="Optional DoorConstructionSet object_dict override; door subset tools return object_dict values rather than Garden targets."),
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
                description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."
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
