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
            list[dict[str, Any]] | None,
            Field(description="Luminaire object_dict values or Garden Properties Library luminaire targets."),
        ] = None,
        luminaire_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Alias for luminaires when passing saved luminaire targets."),
        ] = None,
        luminaire_target: Annotated[
            dict[str, Any] | None,
            Field(description="Alias for one saved luminaire target."),
        ] = None,
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
        resolved_luminaires = luminaires
        if resolved_luminaires is None:
            resolved_luminaires = luminaire_targets
        if resolved_luminaires is None and luminaire_target is not None:
            resolved_luminaires = [luminaire_target]
        if resolved_luminaires is None:
            raise ValueError("Provide luminaires, luminaire_targets, or luminaire_target.")
        return service(
            garden_root=garden_root,
            luminaires=resolved_luminaires,
            model_target=model_target,
            replace_existing=replace_existing,
        )
