"""Create Radiance parameter MCP tool."""

from __future__ import annotations

import shlex
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


def _split_radiance_parameters(value: str | None) -> tuple[str | None, str | None]:
    """Split Agent shorthand like 'view ab=5 ad=1000' into recipe and flags."""
    if value is None:
        return None, None
    tokens = shlex.split(value)
    if not tokens:
        return None, None
    recipe = None
    option_tokens = tokens
    first = tokens[0]
    if first.lstrip("-") in RAW_RADIANCE_FLAGS:
        option_tokens = tokens
    elif not first.startswith("-") and "=" not in first:
        recipe = first
        option_tokens = tokens[1:]
    parts: list[str] = []
    index = 0
    while index < len(option_tokens):
        token = option_tokens[index]
        if token.startswith("-"):
            parts.append(token)
            if index + 1 < len(option_tokens) and not option_tokens[index + 1].startswith("-"):
                index += 1
                parts.append(option_tokens[index])
        elif "=" in token:
            key, raw_value = token.split("=", 1)
            key = key.strip().lstrip("-")
            if key:
                parts.extend((f"-{key}", raw_value))
        elif token in RAW_RADIANCE_FLAGS and index + 1 < len(option_tokens):
            parts.extend((f"-{token}", option_tokens[index + 1]))
            index += 1
        else:
            pass
        index += 1
    return recipe, (" ".join(parts) or None)


def register(mcp: FastMCP) -> None:
    """Register the create_radiance_parameters tool."""

    @mcp.tool(
        name="create_radiance_parameters",
        description="Create recommended Radiance parameters for rtrace grid, rpict view, or rfluxmtx annual/matrix daylight recipes. Pass the returned radiance_parameters string or full result into start_radiance_grid_run, start_radiance_view_run, or start_radiance_matrix_run. Natural recipe aliases like view, render, image, hdr, grid, annual, and raw Radiance flags like ab/ad/as/ar/aa/dj are accepted. garden_root and identifier are accepted as harmless Agent context hints.",
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
            str | None,
            Field(
                description="Recipe family or command: point-in-time-grid, daylight-factor, point-in-time-view, view, render, image, hdr, annual-daylight, annual-irradiance, cumulative-radiation, rtrace, rpict, or rfluxmtx. Defaults to point-in-time-view when image output hints are supplied, otherwise point-in-time-grid.",
            ),
        ] = None,
        detail_level: Annotated[
            str | int | None,
            Field(description="Quality/detail level: 0/low, 1/medium, or 2/high. Defaults to low."),
        ] = None,
        quality: Annotated[
            str | int | None,
            Field(description="Alias for detail_level accepted for Agent compatibility."),
        ] = None,
        recipe: Annotated[
            str | None,
            Field(description="Alias for recipe_type accepted for Agent compatibility."),
        ] = None,
        radiance_parameters: Annotated[
            str | None,
            Field(description="Agent alias for recipe_type when values like grid, view, or annual are supplied."),
        ] = None,
        radiance_recipe: Annotated[
            str | None,
            Field(description="Agent alias for recipe_type when values like grid, view, or annual are supplied."),
        ] = None,
        additional_par: Annotated[
            str | None,
            Field(description="Optional Radiance command syntax overrides, for example '-ab 5 -lw 0.001'."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Optional Garden context hint accepted for Agent compatibility. Ignored by this read-only helper."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional label accepted for Agent compatibility. Ignored by this read-only helper."),
        ] = None,
        ab: Annotated[int | float | str | None, Field(description="Optional raw Radiance -ab ambient bounces override.")] = None,
        ab_matrix: Annotated[
            int | float | str | None,
            Field(description="Agent alias for ab accepted for matrix/annual recipes."),
        ] = None,
        ad: Annotated[int | float | str | None, Field(description="Optional raw Radiance -ad ambient divisions override.")] = None,
        ad_direct: Annotated[
            int | float | str | None,
            Field(description="Agent alias for ad accepted for direct/matrix recipes."),
        ] = None,
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
        sj: Annotated[int | float | str | None, Field(description="Agent specular-jitter hint accepted for compatibility; not emitted here.")] = None,
        dl: Annotated[int | float | str | None, Field(description="Agent direct-limit hint accepted for compatibility; not emitted here.")] = None,
        pm: Annotated[int | float | str | None, Field(description="Agent photon-map hint accepted for compatibility; not emitted here.")] = None,
        vd: Annotated[
            list[float] | tuple[float, ...] | str | None,
            Field(description="Agent view-direction hint accepted for compatibility; use create_radiance_view for actual view direction."),
        ] = None,
        c: Annotated[int | float | str | None, Field(description="Optional raw Radiance -c sample count override for matrix recipes.")] = None,
        p: Annotated[int | float | str | None, Field(description="Optional Agent image/metric hint accepted for compatibility; not emitted as a Radiance flag.")] = None,
        o: Annotated[int | float | str | None, Field(description="Optional Agent output-format hint such as hdr accepted for compatibility; not emitted as a Radiance flag.")] = None,
        d: Annotated[int | float | str | None, Field(description="Agent rpict mode hint accepted for compatibility; not emitted here.")] = None,
        e: Annotated[int | float | str | None, Field(description="Agent rpict mode hint accepted for compatibility; not emitted here.")] = None,
        i: Annotated[int | float | str | None, Field(description="Agent rpict mode hint accepted for compatibility; not emitted here.")] = None,
        jr: Annotated[int | float | str | None, Field(description="Agent rpict jitter hint accepted for compatibility; not emitted here.")] = None,
        jw: Annotated[int | float | str | None, Field(description="Agent rpict jitter hint accepted for compatibility; not emitted here.")] = None,
        me: Annotated[int | float | str | None, Field(description="Agent exposure hint accepted for compatibility; not emitted here.")] = None,
        n: Annotated[int | float | str | None, Field(description="Agent worker/process hint accepted for compatibility; use run tools for actual worker count.")] = None,
        of: Annotated[int | float | str | None, Field(description="Agent output-format hint accepted for compatibility; not emitted here.")] = None,
        af: Annotated[int | float | str | None, Field(description="Agent ambient-file hint accepted for compatibility; not emitted here.")] = None,
        s: Annotated[int | float | str | None, Field(description="Agent sampling hint accepted for compatibility; not emitted here.")] = None,
        t: Annotated[int | float | str | None, Field(description="Agent time/threshold hint accepted for compatibility; not emitted here.")] = None,
        x: Annotated[int | float | str | None, Field(description="Agent image width hint accepted for compatibility; use start_radiance_view_run.resolution for actual image size.")] = None,
        y: Annotated[int | float | str | None, Field(description="Agent image height hint accepted for compatibility; use start_radiance_view_run.resolution for actual image size.")] = None,
        modifier_action: Annotated[
            str | None,
            Field(description="Optional Agent modifier-action hint accepted for compatibility. Ignored."),
        ] = None,
        resolution: Annotated[
            int | None,
            Field(description="Optional image resolution hint accepted for compatibility. Use start_radiance_view_run.resolution for the actual recipe input."),
        ] = None,
    ) -> dict[str, Any]:
        """Create recommended Radiance parameters."""
        ignored_agent_hints = {
            "d": d,
            "e": e,
            "i": i,
            "jr": jr,
            "jw": jw,
            "me": me,
            "n": n,
            "of": of,
            "af": af,
            "s": s,
            "t": t,
            "x": x,
            "y": y,
            "sj": sj,
            "dl": dl,
            "pm": pm,
            "vd": vd,
        }
        _ = (modifier_action, resolution)
        parsed_recipe, parsed_options = _split_radiance_parameters(radiance_parameters)
        if recipe_type is None and recipe is not None:
            recipe_type = recipe
        if recipe_type is None and parsed_recipe is not None:
            recipe_type = parsed_recipe
        elif recipe_type is None and radiance_parameters is not None and parsed_options is None:
            recipe_type = radiance_parameters
        if recipe_type is None and radiance_recipe is not None:
            recipe_type = radiance_recipe
        if detail_level is None and quality is not None:
            detail_level = quality
        if ab is None and ab_matrix is not None:
            ab = ab_matrix
        if ad is None and ad_direct is not None:
            ad = ad_direct
        inferred_recipe_type = recipe_type is None
        if recipe_type is None:
            recipe_type = "point-in-time-view" if (p is not None or o is not None) else "point-in-time-grid"
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
            part for part in (additional_par, parsed_options, raw_options) if part
        ) or None
        result = service(
            recipe_type=recipe_type,
            detail_level=detail_level,
            additional_par=combined_additional_par,
        )
        result["summary_view"]["inferred_recipe_type"] = inferred_recipe_type
        result["summary_view"]["raw_options_applied"] = raw_options is not None
        result["summary_view"]["parsed_radiance_parameters"] = parsed_options is not None
        if p is not None or o is not None:
            result["summary_view"]["agent_output_hints"] = {"p": p, "o": o}
        ignored_agent_hints = {
            key: value for key, value in ignored_agent_hints.items() if value is not None
        }
        if ignored_agent_hints:
            result["summary_view"]["ignored_agent_hints"] = sorted(ignored_agent_hints)
        return result
