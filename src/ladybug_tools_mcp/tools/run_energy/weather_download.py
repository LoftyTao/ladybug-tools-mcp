"""Public LB weather download MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register the LB_weather_download tool."""

    @mcp.tool(
        name="LB_weather_download",
        description=(
            "Search and download one EPW or ZIP weather file into a Garden and "
            "register a reusable weather_file target. The tool checks the public "
            "epwapi service first; search uses GET /v1/files, and known files "
            "prefer the direct epwfile OSS object URL. If epwapi or its search "
            "fails, it lists epwfile/ with OSS ListObjectsV2 pagination and "
            "matches the file name. Pass the returned weather_file target to "
            "EP_start_simulation, EP_read_weather_file_data, UWG, or URBANopt. "
            "Use a specific query, region/country/admin_region, file_name, "
            "file_id, object_key, or file_target; ambiguous matches are rejected. "
            "No token or cloud credentials are required."
        ),
        tags={"ladybug", "weather", "epw", "download", "energy", "garden"},
        timeout=360,
    )
    def weather_download(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        query: Annotated[
            str | None,
            Field(
                description=(
                    "Case-insensitive EPW file, station, WMO number, region, "
                    "country, or admin-region query."
                )
            ),
        ] = None,
        file_id: Annotated[
            str | None,
            Field(description="Opaque id returned by epwapi /v1/files; pass it unchanged."),
        ] = None,
        file_name: Annotated[
            str | None,
            Field(description="Exact EPW or ZIP file name when using the epwfile fallback."),
        ] = None,
        object_key: Annotated[
            str | None,
            Field(description="Known epwfile object key beginning with epwfile/."),
        ] = None,
        file_target: Annotated[
            dict[str, Any] | None,
            Field(description="One file item returned by epwapi /v1/files, including id/name and directory fields."),
        ] = None,
        region: Annotated[
            str | None,
            Field(description="Exact epwapi region name, for example WMO_Region_2_Asia."),
        ] = None,
        country: Annotated[
            str | None,
            Field(description="Exact epwapi country name, for example CHN_China."),
        ] = None,
        admin_region: Annotated[
            str | None,
            Field(description="Exact epwapi administrative-region name, for example SD_Shandong."),
        ] = None,
        format: Annotated[
            str,
            Field(
                description=(
                    "File format filter matching epwapi /v1/files: epw or zip. "
                    "ZIP is the default so sibling DDY/STAT files can be "
                    "registered when present."
                )
            ),
        ] = "zip",
        page_size: Annotated[
            int,
            Field(description="epwapi page_size from 1 to 200."),
        ] = 20,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing Garden weather folder with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Download one public EPW weather file and register it in the Garden."""
        from garden.run_energy.weather_download import download_weather as service

        return service(
            garden_root=garden_root,
            query=query,
            file_id=file_id,
            file_name=file_name,
            object_key=object_key,
            file_target=file_target,
            region=region,
            country=country,
            admin_region=admin_region,
            file_format=format,
            page_size=page_size,
            overwrite=overwrite,
        )
