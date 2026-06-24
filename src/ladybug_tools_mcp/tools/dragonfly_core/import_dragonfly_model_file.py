"""Import Dragonfly model file MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_core.model_files import import_dragonfly_model_file as service


def register(mcp: FastMCP) -> None:
    """Register the dragonfly_import_model_file tool."""

    @mcp.tool(
        name="import_model_file",
        description=(
            "Import a Garden-local Dragonfly DFJSON or Dragonfly-compatible "
            "geoJSON file and save it as a Dragonfly model target. This is the "
            "MCP artifact/target form of Grasshopper Load Objects and Model "
            "From geoJSON; do not pass panel strings or large JSON bodies."
        ),
        tags={"dragonfly", "dfjson", "geojson", "import", "artifact", "garden"},
        timeout=60,
    )
    def import_dragonfly_model_file(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json."),
        ],
        file_path: Annotated[
            str,
            Field(description="Garden-relative DFJSON or geoJSON file path."),
        ],
        file_type: Annotated[
            str,
            Field(description="File type to import: dfjson or geojson."),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Optional stored Dragonfly model identifier."),
        ] = None,
        set_base: Annotated[
            bool,
            Field(description="Whether to set the imported model as base_dragonfly_model."),
        ] = True,
        include_body: Annotated[
            bool,
            Field(description="Whether to return the full model body; false keeps response compact."),
        ] = False,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Optional geoJSON import location dict with city, latitude, longitude, and time_zone."),
        ] = None,
        point: Annotated[
            list[float] | None,
            Field(description="Optional geoJSON origin point as [x, y]."),
        ] = None,
        all_polygons_to_buildings: Annotated[
            bool,
            Field(description="For geoJSON, convert all polygons to buildings when supported by Dragonfly."),
        ] = False,
        existing_to_context: Annotated[
            bool,
            Field(description="For geoJSON, convert existing polygons to context shade when supported."),
        ] = False,
        units: Annotated[
            str,
            Field(description="Dragonfly model units for geoJSON import."),
        ] = "Meters",
        tolerance: Annotated[
            float | None,
            Field(description="Optional Dragonfly geometry tolerance for geoJSON import."),
        ] = None,
        angle_tolerance: Annotated[
            float,
            Field(description="Dragonfly angle tolerance for geoJSON import."),
        ] = 1.0,
    ) -> dict[str, Any]:
        """Import a Dragonfly model file."""
        return service(
            garden_root=garden_root,
            file_path=file_path,
            file_type=file_type,
            identifier=identifier,
            set_base=set_base,
            include_body=include_body,
            location=location,
            point=point,
            all_polygons_to_buildings=all_polygons_to_buildings,
            existing_to_context=existing_to_context,
            units=units,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
        )
