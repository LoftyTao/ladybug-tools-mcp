'MCP tool for detailed_hvac_outdoor_air_system.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    set_ironbug_outdoor_air_system_controller,
    set_ironbug_outdoor_air_system_oa_stream,
    set_ironbug_outdoor_air_system_relief_stream,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_outdoor_air_system tool.'

    @mcp.tool(
        name='outdoor_air_system',
        description=(
            'Create IB_OutdoorAirSystem, an EnergyPlus AirLoopHVAC:OutdoorAirSystem subsystem for the outdoor-air intake and relief-air streams of an AirLoopHVAC or DOAS path. Pass ControllerOutdoorAir, OA stream objects such as heat recovery or coils, and relief stream objects in addition order; this is not a complete AirLoopHVAC by itself or a ventilation schedule. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'air-loop',
            'outdoor-air',
            'doas',
            'ventilation',
            'controller',
            'heat-recovery',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_outdoor_air_system(
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
            Field(description="Stable identifier for the new IB_OutdoorAirSystem object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        oa_stream_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional Ironbug HVAC object targets or same-model identifiers for the outdoor-air intake stream, in the order to add them."
            ),
        ] = None,
        relief_stream_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional Ironbug HVAC object targets or same-model identifiers for the relief/exhaust stream, in the order to add them."
            ),
        ] = None,
        controller_outdoor_air_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ControllerOutdoorAir target or same-model "
                    "identifier to bind as this outdoor-air system's controller. "
                    "For DOAS/outdoor-air supply paths, provide this instead of "
                    "leaving the outdoor-air system bare."
                )
            ),
        ] = None,
        heat_recovery_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_HeatExchangerAirToAirSensibleAndLatent target or same-model identifier "
                    "to prepend to the outdoor-air stream as heat recovery."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_OutdoorAirSystem as a reviewed Ironbug LoopObjs / AirLoopObjects authoring object."""

        effective_oa_stream_targets = list(oa_stream_targets or [])
        if heat_recovery_target is not None:
            effective_oa_stream_targets = [
                heat_recovery_target,
                *[
                    target
                    for target in effective_oa_stream_targets
                    if target != heat_recovery_target
                ],
            ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_OutdoorAirSystem',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            overwrite=overwrite,
        )
        latest_model_target = created["updated_model_target"]
        binding_summary: dict[str, Any] = {}
        if effective_oa_stream_targets:
            oa_stream = set_ironbug_outdoor_air_system_oa_stream(
                garden_root=garden_root,
                ironbug_model_target=latest_model_target,
                outdoor_air_system_target=created["target"],
                oa_stream_targets=effective_oa_stream_targets,
            )
            latest_model_target = oa_stream["updated_model_target"]
            created["target"] = oa_stream["target"]
            binding_summary["oa_stream_bound"] = True
            binding_summary["oa_stream_count"] = oa_stream["summary_view"][
                "oa_stream_count"
            ]
        else:
            binding_summary["oa_stream_bound"] = False
        if relief_stream_targets is not None:
            relief_stream = set_ironbug_outdoor_air_system_relief_stream(
                garden_root=garden_root,
                ironbug_model_target=latest_model_target,
                outdoor_air_system_target=created["target"],
                relief_stream_targets=relief_stream_targets,
            )
            latest_model_target = relief_stream["updated_model_target"]
            created["target"] = relief_stream["target"]
            binding_summary["relief_stream_bound"] = True
            binding_summary["relief_stream_count"] = relief_stream["summary_view"][
                "relief_stream_count"
            ]
        else:
            binding_summary["relief_stream_bound"] = False
        if controller_outdoor_air_target is None:
            created["updated_model_target"] = latest_model_target
            created["summary_view"] = {
                **created["summary_view"],
                **binding_summary,
                "controller_bound": False,
            }
            return created

        updated = set_ironbug_outdoor_air_system_controller(
            garden_root=garden_root,
            ironbug_model_target=latest_model_target,
            outdoor_air_system_target=created["target"],
            controller_outdoor_air_target=controller_outdoor_air_target,
        )
        created["target"] = updated["target"]
        created["updated_model_target"] = updated["updated_model_target"]
        created["summary_view"] = {
            **created["summary_view"],
            **binding_summary,
            "controller_bound": True,
            "controller_identifier": updated["summary_view"]["controller_identifier"],
        }
        return created
