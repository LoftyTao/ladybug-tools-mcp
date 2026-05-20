"""Attach Honeybee Radiance Luminaire / IES resources to a model."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.luminaires import add_radiance_luminaire_to_model as service


def register(mcp: FastMCP) -> None:
    """Register the add_radiance_luminaire_to_model tool."""

    @mcp.tool(
        name="add_radiance_luminaire_to_model",
        description="Attach Honeybee Radiance Luminaire / IES resources to a Garden Honeybee model by writing them into model.properties.radiance.luminaires. Use this after create_radiance_luminaire; it is Radiance electric lighting, not Honeybee Energy Lighting.",
        tags={
            "honeybee-radiance",
            "radiance",
            "luminaire",
            "ies",
            "electric-lighting",
            "model-authoring",
            "garden-mode",
            "write",
            "safe",
        },
        timeout=60,
    )
    def add_radiance_luminaire_to_model(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path string containing garden.json."),
        ],
        luminaires: Annotated[
            list[dict[str, Any]],
            Field(description="Luminaire object_dict values or Garden Properties Library luminaire targets."),
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
