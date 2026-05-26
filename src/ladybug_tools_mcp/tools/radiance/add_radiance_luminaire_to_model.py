"""Attach Honeybee Radiance Luminaire / IES resources to a model."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.luminaires import add_radiance_luminaire_to_model as service


def register(mcp: FastMCP) -> None:
    'Register the radiance_add_luminaire_to_model tool.'

    @mcp.tool(
        name="add_luminaire_to_model",
        description=(
            "Attach Radiance luminaire targets to a Garden Honeybee model for "
            "electric-lighting Radiance studies. Pass luminaire targets from "
            "radiance_create_luminaire plus an optional Honeybee model target. "
            "This edits model.properties.radiance.luminaires; it does not "
            "create Energy lighting loads or run rpict/grid recipes. Returns "
            "target, model_target, summary_view, persistence_receipt, and "
            "report for later search or simulation calls."
        ),
        tags={
            "radiance",
            "model",
            "edit",
            "luminaire",
            "electric-lighting",
        },
        timeout=60,
    )
    def add_radiance_luminaire_to_model(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually garden_create['garden_root']; required when saving or reading Garden targets."),
        ],
        luminaires: Annotated[
            list[dict[str, Any]],
            Field(description="Radiance Luminaire object_dict values or Garden Properties Library luminaire targets."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target. Defaults to the Garden base model."),
        ] = None,
        replace_existing: Annotated[
            bool,
            Field(description="Replace existing model luminaires with the same identifiers."),
        ] = False,
    ) -> dict[str, Any]:
        """Attach Radiance Luminaire objects to a Garden Honeybee model."""
        return service(
            garden_root=garden_root,
            luminaires=luminaires,
            model_target=model_target,
            replace_existing=replace_existing,
        )
