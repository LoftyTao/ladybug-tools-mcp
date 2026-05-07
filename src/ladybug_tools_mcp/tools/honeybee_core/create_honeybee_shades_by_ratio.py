"""Create Honeybee Shades By Ratio alias MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.honeybee_core.creation import create_honeybee_shades_by_parameters as service


def register(mcp: FastMCP) -> None:
    """Register the create_honeybee_shades_by_ratio alias tool."""

    @mcp.tool(
        name="create_honeybee_shades_by_ratio",
        description="Agent compatibility alias for creating a simple exterior shade/overhang on a Face or Aperture target. Prefer create_honeybee_shades_by_parameters for planned calls.",
        tags={
            "honeybee-core",
            "garden-mode",
            "shade",
            "overhang",
            "sunshade",
            "ratio",
            "alias",
            "create",
            "write",
            "safe",
        },
        timeout=20,
    )
    def create_honeybee_shades_by_ratio(
        garden_root: Annotated[
            str,
            Field(description="Required exact Garden root path string containing garden.json."),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(description="Honeybee face or aperture typed target."),
        ],
        ratio: Annotated[
            float | None,
            Field(description="Natural shade ratio hint. Accepted as a compatibility hint; depth controls geometry."),
        ] = None,
        offset: Annotated[
            float | None,
            Field(description="Optional shade depth/offset hint. Used as depth when depth is omitted."),
        ] = None,
        depth: Annotated[
            float | None,
            Field(description="Optional shade depth. Defaults to offset, then 1.0."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional shade identifier prefix."),
        ] = None,
        identifier_prefix: Annotated[
            str | None,
            Field(description="Optional shade identifier prefix."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target dict."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a simple shade through the parameterized shade service."""
        _ = ratio
        shade_depth = depth if depth is not None else offset if offset is not None else 1.0
        parameters: dict[str, Any] = {
            "depth": shade_depth,
            "louver_count": 1,
        }
        name_prefix = identifier_prefix or identifier
        if name_prefix is not None:
            parameters["base_name"] = name_prefix
        return service(
            garden_root=garden_root,
            host_target=host_target,
            generation_mode="louver_by_count",
            parameters=parameters,
            model_target=model_target,
        )
