'MCP tool for detailed_hvac_schedule_type_limits.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_schedule_type_limits tool.'

    @mcp.tool(
        name='schedule_type_limits',
        description=(
            'Create IB_ScheduleTypeLimits, an OpenStudio ScheduleTypeLimits target that constrains schedule lower/upper values, numeric type, and unit type for Ironbug DetailedHVAC schedules. Use it with ScheduleRuleset or Schedule:File targets; this is not a schedule values object, CSV schedule, Honeybee Energy schedule library object, or Energy run. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'schedule', 'schedule-type-limit', 'bounds', 'unit-type', 'numeric-type', 'author'},
        timeout=20,
    )
    def create_ironbug_schedule_type_limits(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, for example garden_create['garden_root']."),
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
            Field(description="Stable identifier for the new IB_ScheduleTypeLimits object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="Optional EnergyPlus/OpenStudio object name for this ScheduleTypeLimits target; maps to Name."
            ),
        ] = None,
        lower_limit_value: Annotated[
            float | None,
            Field(
                description="Optional lower bound for allowed schedule values; maps to LowerLimitValue."
            ),
        ] = None,
        upper_limit_value: Annotated[
            float | None,
            Field(
                description="Optional upper bound for allowed schedule values; maps to UpperLimitValue."
            ),
        ] = None,
        unit_type: Annotated[
            str | None,
            Field(
                description="Optional ScheduleTypeLimits unit type such as Dimensionless or Temperature; maps to UnitType."
            ),
        ] = None,
        numeric_type: Annotated[
            str | None,
            Field(
                description="Optional ScheduleTypeLimits numeric type such as Continuous or Discrete; maps to NumericType."
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug ScheduleTypeLimits target."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if lower_limit_value is not None:
            source_fields['LowerLimitValue'] = lower_limit_value
        if upper_limit_value is not None:
            source_fields['UpperLimitValue'] = upper_limit_value
        if unit_type is not None:
            source_fields['UnitType'] = unit_type
        if numeric_type is not None:
            source_fields['NumericType'] = numeric_type
        source_properties: dict[str, Any] = {}
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ScheduleTypeLimits',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            overwrite=overwrite,
        )
