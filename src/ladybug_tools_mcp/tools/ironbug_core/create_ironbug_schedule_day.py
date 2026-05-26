'MCP tool for detailed_hvac_schedule_day.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_schedule_day tool.'

    @mcp.tool(
        name='schedule_day',
        description=(
            'Create IB_ScheduleDay, a low-level OpenStudio ScheduleDay target for one daily HVAC profile inside Ironbug DetailedHVAC schedules. This wrapper creates the day-profile object; use detailed_hvac_schedule_rule or detailed_hvac_schedule_ruleset when you need one-value or 24-hour values and annual date rules. This is not a full year schedule, Schedule:File, Honeybee Energy schedule library object, or Energy run. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'schedule', 'schedule-day', 'daily-schedule', 'author'},
        timeout=20,
    )
    def create_ironbug_schedule_day(
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
            Field(description="Stable identifier for the new IB_ScheduleDay object."),
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
        """Create an Ironbug ScheduleDay daily-profile target."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ScheduleDay',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            overwrite=overwrite,
        )
