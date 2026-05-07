"""Radiance parameter recommendation services."""

from __future__ import annotations

from typing import Any

from honeybee_radiance_command.options.rfluxmtx import RfluxmtxOptions
from honeybee_radiance_command.options.rpict import RpictOptions
from honeybee_radiance_command.options.rtrace import RtraceOptions

from ladybug_tools_mcp.contracts.report import make_report

RTRACE = {
    "ab": [2, 3, 6],
    "ad": [512, 2048, 4096],
    "as_": [128, 2048, 4096],
    "ar": [16, 64, 128],
    "aa": [0.25, 0.2, 0.1],
    "dj": [0, 0.5, 1],
    "ds": [0.5, 0.25, 0.05],
    "dt": [0.5, 0.25, 0.15],
    "dc": [0.25, 0.5, 0.75],
    "dr": [0, 1, 3],
    "dp": [64, 256, 512],
    "st": [0.85, 0.5, 0.15],
    "lr": [4, 6, 8],
    "lw": [0.05, 0.01, 0.005],
    "ss": [0, 0.7, 1],
}

RPICT = {
    **RTRACE,
    "ps": [8, 4, 2],
    "pt": [0.15, 0.10, 0.05],
    "pj": [0.6, 0.9, 0.9],
}

RFLUXMTX = {
    "ab": [3, 5, 6],
    "ad": [5000, 15000, 25000],
    "as_": [128, 2048, 4096],
    "ds": [0.5, 0.25, 0.05],
    "dt": [0.5, 0.25, 0.15],
    "dc": [0.25, 0.5, 0.75],
    "dr": [0, 1, 3],
    "dp": [64, 256, 512],
    "st": [0.85, 0.5, 0.15],
    "lr": [4, 6, 8],
    "lw": [0.000002, 6.67e-07, 4e-07],
    "ss": [0, 0.7, 1],
    "c": [1, 1, 1],
}

RECIPE_TYPES = {
    "0": "rtrace",
    "grid": "rtrace",
    "point-in-time-grid": "rtrace",
    "point_in_time_grid": "rtrace",
    "illuminance": "rtrace",
    "illuminance-grid": "rtrace",
    "illuminance_grid": "rtrace",
    "daylight-factor": "rtrace",
    "daylight_factor": "rtrace",
    "sky-view": "rtrace",
    "sky_view": "rtrace",
    "rtrace": "rtrace",
    "1": "rpict",
    "point-in-time-view": "rpict",
    "point_in_time_view": "rpict",
    "point-in-time-image": "rpict",
    "point_in_time_image": "rpict",
    "view": "rpict",
    "render": "rpict",
    "rendering": "rpict",
    "image": "rpict",
    "hdr": "rpict",
    "picture": "rpict",
    "rpict-view": "rpict",
    "rpict_view": "rpict",
    "rpict": "rpict",
    "2": "rfluxmtx",
    "annual": "rfluxmtx",
    "annual-daylight": "rfluxmtx",
    "annual_daylight": "rfluxmtx",
    "annual-irradiance": "rfluxmtx",
    "annual_irradiance": "rfluxmtx",
    "cumulative-radiation": "rfluxmtx",
    "cumulative_radiation": "rfluxmtx",
    "rfluxmtx": "rfluxmtx",
}

DETAIL_LEVELS = {
    "0": 0,
    "low": 0,
    "1": 1,
    "medium": 1,
    "2": 2,
    "high": 2,
    "3": 2,
    "quick": 0,
    "fast": 0,
}
DETAIL_LABELS = ("low", "medium", "high")


def _normalize_text(value: str | int | None, *, default: str | None = None) -> str:
    if value is None:
        if default is None:
            raise ValueError("A value is required.")
        return default
    return str(value).strip().lower().replace(" ", "-")


def create_radiance_parameters(
    *,
    recipe_type: str | int,
    detail_level: str | int | None = None,
    additional_par: str | None = None,
) -> dict[str, Any]:
    """Create recommended Radiance parameters for a recipe family."""
    normalized_recipe_type = _normalize_text(recipe_type)
    command_name = RECIPE_TYPES.get(normalized_recipe_type)
    if command_name is None:
        options = ", ".join(sorted(RECIPE_TYPES))
        raise ValueError(f"Unsupported recipe_type. Choose one of: {options}.")

    normalized_detail = _normalize_text(detail_level, default="0")
    if normalized_detail not in DETAIL_LEVELS:
        raise ValueError("detail_level must be one of 0/low, 1/medium, or 2/high.")
    detail_index = DETAIL_LEVELS[normalized_detail]

    if command_name == "rtrace":
        option_dict = RTRACE
        option_obj = RtraceOptions()
    elif command_name == "rpict":
        option_dict = RPICT
        option_obj = RpictOptions()
    else:
        option_dict = RFLUXMTX
        option_obj = RfluxmtxOptions()

    for option_name, option_values in option_dict.items():
        setattr(option_obj, option_name, option_values[detail_index])
    if additional_par:
        option_obj.update_from_string(additional_par)

    rad_par = option_obj.to_radiance()
    detail_label = DETAIL_LABELS[detail_index]
    target = {
        "target_type": "radiance_parameters",
        "recipe_type": normalized_recipe_type,
        "command_name": command_name,
        "detail_level": detail_label,
        "radiance_parameters": rad_par,
        "value": rad_par,
    }
    return {
        "target": target,
        "radiance_parameters_target": target,
        "value": rad_par,
        "radiance_parameters": rad_par,
        "rad_par": rad_par,
        "summary_view": {
            "recipe_type": normalized_recipe_type,
            "command_name": command_name,
            "detail_level": detail_label,
            "additional_par_applied": bool(additional_par),
        },
        "report": make_report(
            status="ok",
            message=(
                "Created Radiance parameters for "
                f"{command_name} at {detail_label} detail."
            ),
        ),
    }
