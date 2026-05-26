'MCP tool for detailed_hvac_air_loop_branches.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import set_ironbug_loop_branches



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_air_loop_branches tool.'

    @mcp.tool(
        name='air_loop_branches',
        description=(
            'Create IB_AirLoopBranches, an air-loop component used on air-side supply or demand branches, from the Ironbug LoopObjs / AirLoopObjects source mirror. For DOAS, VAV, CAV, and room-serving air loops, pass one inner branch list per served room or zone through branch_component_targets, usually with a room-linked IB_ThermalZone target after an AirTerminal has been bound. Then pass this AirLoopBranches target to detailed_hvac_air_loop_hvac demand_component_targets. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={'ironbug', 'detailed-hvac', 'air-loop', 'doas', 'vav', 'component', 'author'},
        timeout=20,
    )
    def create_ironbug_air_loop_branches(
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
            Field(description="Stable identifier for the new IB_AirLoopBranches object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        branch_component_targets: Annotated[
            list[list[dict[str, Any] | str]] | None,
            Field(
                description=(
                    "Optional ordered air-loop branch component targets. Each "
                    "inner list is one branch; for zone demand branches pass "
                    "IB_ThermalZone targets or same-model identifiers whose "
                    "ThermalZone already has an AirTerminal bound."
                )
            ),
        ] = None,
        branch1_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional target for Ironbug component Parameter 'Branch1' "
                    "on IB_AirLoopBranches."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_AirLoopBranches as a reviewed Ironbug LoopObjs / AirLoopObjects authoring object."""

        child_targets = [
            branch1_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_AirLoopBranches',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            child_targets=child_targets if any(item is not None for item in child_targets) else None,
            overwrite=overwrite,
        )
        if branch_component_targets is None:
            created["summary_view"] = {
                **created["summary_view"],
                "branch_components_bound": False,
            }
            return created

        updated = set_ironbug_loop_branches(
            garden_root=garden_root,
            ironbug_model_target=created["updated_model_target"],
            branches_target=created["target"],
            branch_component_targets=branch_component_targets,
        )
        created["target"] = updated["target"]
        created["updated_model_target"] = updated["updated_model_target"]
        created["summary_view"] = {
            **created["summary_view"],
            "branch_components_bound": True,
            "branch_count": updated["summary_view"]["branch_count"],
            "branch_lengths": updated["summary_view"]["branch_lengths"],
        }
        return created
