"""Create Radiance parameter MCP tool."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.radiance.parameters import create_radiance_parameters as service


RAW_RADIANCE_FLAGS = (
    "ab",
    "ad",
    "as",
    "ar",
    "aa",
    "dj",
    "ds",
    "dt",
    "dc",
    "dr",
    "dp",
    "st",
    "lr",
    "lw",
    "ss",
    "ps",
    "pt",
    "pj",
    "c",
)


def _raw_radiance_options(values: dict[str, Any]) -> str | None:
    parts: list[str] = []
    for flag in RAW_RADIANCE_FLAGS:
        value = values.get(flag)
        if value is None:
            continue
        if isinstance(value, bool):
            if value:
                parts.append(f"-{flag}")
            continue
        if isinstance(value, str):
            try:
                float(value)
            except ValueError:
                continue
        parts.extend((f"-{flag}", str(value)))
    return " ".join(parts) or None


def register(mcp: FastMCP) -> None:
    """Register the create_radiance_parameters tool."""

    @mcp.tool(
        name="create_radiance_parameters",
        description="Create recommended Radiance parameters for rtrace grid, rpict view, or rfluxmtx annual/matrix daylight recipes. Pass the returned radiance_parameters string or full result into start_radiance_grid_run, start_radiance_view_run, or start_radiance_matrix_run.",
        tags={
            "honeybee-radiance",
            "radiance",
            "radiance-parameters",
            "rtrace",
            "rpict",
            "rfluxmtx",
            "daylight",
            "recipe",
            "parameters",
            "safe",
            "read-only",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def create_radiance_parameters(
        recipe_type: Annotated[
            str,
            Field(
                description="Recipe family or command: point-in-time-grid, daylight-factor, point-in-time-view, annual-daylight, annual-irradiance, cumulative-radiation, rtrace, rpict, or rfluxmtx.",
            ),
        ],
        detail_level: Annotated[
            str | int | None,
            Field(description="Quality/detail level: 0/low, 1/medium, or 2/high. Defaults to low."),
        ] = None,
        additional_par: Annotated[
            str | None,
            Field(description="Optional Radiance command syntax overrides, for example '-ab 5 -lw 0.001'."),
        ] = None,
        ab: Annotated[int | float | str | None, Field(description="Optional raw Radiance -ab ambient bounces override.")] = None,
        ad: Annotated[int | float | str | None, Field(description="Optional raw Radiance -ad ambient divisions override.")] = None,
        ambient_supersamples: Annotated[
            int | float | str | None,
            Field(description="Optional raw Radiance -as ambient super-samples override."),
        ] = None,
        ar: Annotated[int | float | str | None, Field(description="Optional raw Radiance -ar ambient resolution override.")] = None,
        aa: Annotated[int | float | str | None, Field(description="Optional raw Radiance -aa ambient accuracy override.")] = None,
        dj: Annotated[int | float | str | None, Field(description="Optional raw Radiance -dj direct jitter override.")] = None,
        ds: Annotated[int | float | str | None, Field(description="Optional raw Radiance -ds direct sampling override.")] = None,
        dt: Annotated[int | float | str | None, Field(description="Optional raw Radiance -dt direct threshold override.")] = None,
        dc: Annotated[int | float | str | None, Field(description="Optional raw Radiance -dc direct certainty override.")] = None,
        dr: Annotated[int | float | str | None, Field(description="Optional raw Radiance -dr direct relays override.")] = None,
        dp: Annotated[int | float | str | None, Field(description="Optional raw Radiance -dp direct pretest density override.")] = None,
        st: Annotated[int | float | str | None, Field(description="Optional raw Radiance -st specular threshold override.")] = None,
        lr: Annotated[int | float | str | None, Field(description="Optional raw Radiance -lr limit reflection override.")] = None,
        lw: Annotated[int | float | str | None, Field(description="Optional raw Radiance -lw limit weight override.")] = None,
        ss: Annotated[int | float | str | None, Field(description="Optional raw Radiance -ss specular sampling override.")] = None,
        ps: Annotated[int | float | str | None, Field(description="Optional raw Radiance -ps pixel sampling override for view recipes.")] = None,
        pt: Annotated[int | float | str | None, Field(description="Optional raw Radiance -pt pixel threshold override for view recipes.")] = None,
        pj: Annotated[int | float | str | None, Field(description="Optional raw Radiance -pj pixel jitter override for view recipes.")] = None,
        c: Annotated[int | float | str | None, Field(description="Optional raw Radiance -c sample count override for matrix recipes.")] = None,
    ) -> dict[str, Any]:
        """Create recommended Radiance parameters."""
        raw_options = _raw_radiance_options(
            {
                "ab": ab,
                "ad": ad,
                "as": ambient_supersamples,
                "ar": ar,
                "aa": aa,
                "dj": dj,
                "ds": ds,
                "dt": dt,
                "dc": dc,
                "dr": dr,
                "dp": dp,
                "st": st,
                "lr": lr,
                "lw": lw,
                "ss": ss,
                "ps": ps,
                "pt": pt,
                "pj": pj,
                "c": c,
            }
        )
        combined_additional_par = " ".join(
            part for part in (additional_par, raw_options) if part
        ) or None
        result = service(
            recipe_type=recipe_type,
            detail_level=detail_level,
            additional_par=combined_additional_par,
        )
        result["summary_view"]["raw_options_applied"] = raw_options is not None
        return result
