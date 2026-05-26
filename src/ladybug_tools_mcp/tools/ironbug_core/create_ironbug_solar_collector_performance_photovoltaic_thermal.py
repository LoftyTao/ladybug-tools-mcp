'MCP tool for detailed_hvac_solar_collector_performance_photovoltaic_thermal.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_solar_collector_performance_photovoltaic_thermal tool.'

    @mcp.tool(
        name='solar_collector_performance_photovoltaic_thermal',
        description=(
            'Create IB_SolarCollectorPerformancePhotovoltaicThermal, the abstract Ironbug photovoltaic-thermal performance base target used by PVT collector variants. Prefer the Simple or BIPVT performance tools when you need EnergyPlus-ready parameters. This base wrapper is not a PV generator, flat-plate water performance object, collector surface, or Energy result reader. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'performance', 'solar-collector', 'photovoltaic-thermal', 'photovoltaic', 'pv', 'author'},
        timeout=20,
    )
    def create_ironbug_solar_collector_performance_photovoltaic_thermal(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json for the Ironbug model."),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Required Ironbug model target returned by detailed_hvac_create_model; '
                    "pass result['target'], not the .ibjson file path."
                )
            ),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for the new IB_SolarCollectorPerformancePhotovoltaicThermal object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug photovoltaic-thermal performance base target."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SolarCollectorPerformancePhotovoltaicThermal',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            overwrite=overwrite,
        )
