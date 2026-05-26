'MCP tool for detailed_hvac_district_heating.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_district_heating tool.'

    @mcp.tool(
        name='district_heating',
        description=(
            'Create IB_DistrictHeating, an obsolete Ironbug wrapper backed by the purchased hot-water DistrictHeatingWater object. Prefer detailed_hvac_district_heating_water for new hot-water plant loops; keep this only when an existing Ironbug graph still references IB_DistrictHeating. This authors Ironbug DetailedHVAC input only; it does not create a boiler, steam plant, district-scale simulation, or Energy run. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'plant-loop',
            'plant-component',
            'district-energy',
            'purchased-energy',
            'hot-water',
            'heating',
            'schedule',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_district_heating(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
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
            Field(description="Stable DetailedHVAC object identifier for this legacy purchased hot-water component."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional display label shown in Ironbug/Garden summaries."),
        ] = None,
        nominal_capacity: Annotated[
            float | str | None,
            Field(description='Nominal purchased hot-water heating demand in W; autosize-compatible inputs accepted by Ironbug/OpenStudio are also valid.'),
        ] = None,
        capacity_fraction_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for non-negative capacity fraction over time; omit for a constant 1.0 fraction.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio object name for the legacy DistrictHeating wrapper; defaults to the identifier when omitted.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_DistrictHeating as reviewed legacy purchased heating data."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if nominal_capacity is not None:
            source_fields['NominalCapacity'] = nominal_capacity
        if capacity_fraction_schedule_target is not None:
            source_field_targets['CapacityFractionSchedule'] = capacity_fraction_schedule_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_DistrictHeating',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            overwrite=overwrite,
        )
