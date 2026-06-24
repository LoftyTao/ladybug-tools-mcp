"""Export Dragonfly Model to URBANopt artifacts MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_des.export import export_urbanopt_model as service


def register(mcp: FastMCP) -> None:
    """Register the URBANopt artifact export tool."""

    @mcp.tool(
        name="export_urbanopt_model",
        description=(
            "Translate a Garden Dragonfly Model into the URBANopt files needed "
            "for district energy workflows. The response gives Garden artifact "
            "targets for the feature GeoJSON and generated Honeybee HBJSON files, "
            "plus summary_view, persistence_receipt, and report. Use a DES loop "
            "target only when the exported GeoJSON should carry district thermal "
            "loop data; full file bodies stay on disk."
        ),
        tags={"dragonfly", "district-energy", "urbanopt", "export", "artifact", "target"},
        timeout=60,
    )
    def export_urbanopt_model(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; export artifacts are saved inside this Garden.")],
        location: Annotated[dict[str, Any], Field(description="Ladybug Location fields for the URBANopt project, including latitude and longitude.")],
        model_target: Annotated[dict[str, Any] | None, Field(description="Specific Dragonfly Model target to export; omit to export the Garden base_dragonfly_model.") ] = None,
        des_loop_target: Annotated[dict[str, Any] | None, Field(description="Optional DES thermal-loop target to embed in the URBANopt feature GeoJSON.") ] = None,
        point: Annotated[list[float] | None, Field(description="Optional [x, y] model coordinate for the project location marker.") ] = None,
        folder_name: Annotated[str | None, Field(description="Optional Garden DES export folder name; long names are shortened to keep URBANopt paths usable on Windows.") ] = None,
        shade_distance: Annotated[float | None, Field(description="Optional shade search distance passed to the Dragonfly Energy URBANopt writer.") ] = None,
        use_multiplier: Annotated[bool, Field(description="Keep Dragonfly Story multipliers as Honeybee Room multipliers when translating buildings.") ] = True,
        exclude_plenums: Annotated[bool, Field(description="Exclude generated ceiling and floor plenum rooms from the Honeybee translation.") ] = False,
        solve_ceiling_adjacencies: Annotated[bool, Field(description="Solve matching ceiling adjacencies between interior stories before writing HBJSON files.") ] = False,
        merge_method: Annotated[str, Field(description="Dragonfly Energy room merge method, such as None, Zones, PlenumZones, Stories, or PlenumStories.") ] = "None",
        tolerance: Annotated[float | None, Field(description="Optional geometry tolerance for the Dragonfly Energy URBANopt writer.") ] = None,
    ) -> dict[str, Any]:
        """Export a Dragonfly Model to URBANopt artifacts."""
        return service(
            garden_root=garden_root,
            location=location,
            model_target=model_target,
            des_loop_target=des_loop_target,
            point=point,
            folder_name=folder_name,
            shade_distance=shade_distance,
            use_multiplier=use_multiplier,
            exclude_plenums=exclude_plenums,
            solve_ceiling_adjacencies=solve_ceiling_adjacencies,
            merge_method=merge_method,
            tolerance=tolerance,
        )
