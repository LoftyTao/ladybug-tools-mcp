"""Upsert typed Ironbug components into a Garden Ironbug system."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.tools.ironbug._schemas import (
    IronbugComponentSpec,
    IronbugModelTargetRef,
    IronbugSystemMutationResult,
    NamedIronbugComponentSpec,
    dump_components,
    dump_target,
)


def register(mcp: FastMCP) -> None:
    """Register IB_upsert_components."""

    @mcp.tool(
        name="IB_upsert_components",
        description=(
            "Add, update, or remove typed Ironbug components in a system draft and "
            "serialize through C# Ironbug.HVAC. Reference child component IDs in "
            "ctor_args, fields, or wiring; reusing an ID across loops links it via "
            "TrackingID."
        ),
        tags={"ironbug", "detailed-hvac", "hvac", "author", "edit"},
        annotations={"read_only_hint": False, "destructive_hint": False},
        timeout=30,
    )
    def ib_upsert_components(
        garden_root: Annotated[
            str,
            Field(min_length=1, description="Required Garden root path containing garden.json."),
        ],
        components: Annotated[
            dict[str, IronbugComponentSpec] | list[NamedIronbugComponentSpec] | None,
            Field(
                description=(
                    "Mapping of component_id to spec, or list of specs with 'id', "
                    "using IB_describe_component types (leave unset when removing via remove_ids)."
                )
            ),
        ] = None,
        ironbug_model_target: Annotated[
            IronbugModelTargetRef | None,
            Field(description="Target returned by IB_create_system. Optional when only one Ironbug system exists in the Garden."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional Ironbug system identifier when ironbug_model_target is unset."),
        ] = None,
        remove_ids: Annotated[
            list[str] | None,
            Field(description="Optional list of component IDs to delete from the draft."),
        ] = None,
        replace: Annotated[
            bool,
            Field(description="If true, replace all existing components; if false, merge into existing components."),
        ] = False,
    ) -> IronbugSystemMutationResult:
        """Add or update typed components in an Ironbug system."""
        from garden.ironbug.service import upsert_ironbug_components

        return IronbugSystemMutationResult.model_validate(
            upsert_ironbug_components(
                garden_root=garden_root,
                components=dump_components(components),
                ironbug_model_target=dump_target(ironbug_model_target),
                identifier=identifier,
                remove_ids=remove_ids,
                replace=replace,
            )
        )
