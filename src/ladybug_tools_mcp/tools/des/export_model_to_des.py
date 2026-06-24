"""Export Dragonfly Model to DES artifacts MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.dragonfly_des.export import export_model_to_des as service


def register(mcp: FastMCP) -> None:
    """Register the DES artifact export tool."""

    @mcp.tool(
        name="export_model",
        description=(
            "Write the Dragonfly Energy DES handoff files for a Dragonfly Model, "
            "thermal loop, and EPW weather target. The response gives Garden "
            "artifact targets for feature GeoJSON, scenario CSV, and the SDK "
            "system_params JSON file, plus summary_view, persistence_receipt, "
            "and report. Use this before DES load, sys-param, or Modelica "
            "candidate steps; file contents are not returned inline."
        ),
        tags={"dragonfly", "district-energy", "export", "artifact", "epw", "weather", "target"},
        timeout=60,
    )
    def export_model_to_des(
        garden_root: Annotated[str, Field(description="Garden root containing garden.json; DES export artifacts are saved inside this Garden.")],
        des_loop_target: Annotated[dict[str, Any], Field(description="DES thermal-loop target that should be translated into system parameters.")],
        weather_target: Annotated[dict[str, Any], Field(description="Garden weather_file target with an EPW path for the DES export.")],
        model_target: Annotated[dict[str, Any] | None, Field(description="Specific Dragonfly Model target to export; omit to export the Garden base_dragonfly_model.") ] = None,
        location: Annotated[dict[str, Any] | None, Field(description="Optional Ladybug Location override; omit to let the writer read location from the EPW.") ] = None,
        point: Annotated[list[float] | None, Field(description="Optional [x, y] model coordinate for the weather location marker.") ] = None,
        folder_name: Annotated[str | None, Field(description="Optional Garden DES export folder name; long names are shortened to keep URBANopt paths usable on Windows.") ] = None,
        tolerance: Annotated[float | None, Field(description="Optional geometry tolerance for the Dragonfly Energy DES writer.") ] = None,
    ) -> dict[str, Any]:
        """Export a Dragonfly Model to DES artifacts."""
        return service(
            garden_root=garden_root,
            des_loop_target=des_loop_target,
            weather_target=weather_target,
            model_target=model_target,
            location=location,
            point=point,
            folder_name=folder_name,
            tolerance=tolerance,
        )
