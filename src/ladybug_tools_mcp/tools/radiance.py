"""radiance MCP tools."""

from __future__ import annotations

import time

from pathlib import Path
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.contracts import make_report


_TIME_ZONE_OFFSET_NAMES = {
    -9: "YST",
    -8: "PST",
    -7: "MST",
    -6: "CST",
    -5: "EST",
    -4: "AST",
    0: "GMT",
    1: "CET",
    2: "EET",
    3: "AST",
    4: "GST",
    5.5: "IST",
    9: "JST",
    12: "NZST",
}

def _normalize_time_zone(time_zone: str | int | float | None) -> str | None:
    if time_zone is None:
        return None
    if isinstance(time_zone, str):
        stripped = time_zone.strip()
        try:
            numeric = float(stripped)
        except ValueError:
            return stripped
    else:
        numeric = float(time_zone)
    key: int | float = int(numeric) if numeric.is_integer() else numeric
    return _TIME_ZONE_OFFSET_NAMES.get(key, str(time_zone))

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

VectorInput = list[float] | dict[str, float] | None

def _sensor_grid_vector(value: VectorInput, name: str) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        try:
            return [float(value["x"]), float(value["y"]), float(value["z"])]
        except KeyError as exc:
            raise ValueError(f"{name} dict must include x, y, and z.") from exc
    if len(value) != 3:
        raise ValueError(f"{name} must include exactly three numbers.")
    return [float(value[0]), float(value[1]), float(value[2])]

def _room_identifier_from_target(
    room_identifier: str | None,
    room_target: dict[str, Any] | None,
) -> str | None:
    if room_identifier is not None or not isinstance(room_target, dict):
        return room_identifier
    if str(room_target.get("object_type", "")).lower() == "room":
        value = room_target.get("object_identifier") or room_target.get("identifier")
        if isinstance(value, str) and value:
            return value
    return room_identifier

def _positions_from_rectangular_grid(
    *,
    positions: list[list[float]] | None,
    x_dim: float | None,
    y_dim: float | None,
    height: float | None,
    x_count: int | None,
    y_count: int | None,
    grid_spacing: float | None = None,
    origin: list[float] | None = None,
) -> list[list[float]]:
    if positions is not None:
        return positions
    if x_dim is not None and y_dim is not None:
        if grid_spacing is not None and grid_spacing > 0:
            x_count = max(1, int(float(x_dim) / float(grid_spacing)))
            y_count = max(1, int(float(y_dim) / float(grid_spacing)))
        x_count = 4 if x_count is None else x_count
        y_count = 4 if y_count is None else y_count
    if x_dim is None or y_dim is None or x_count is None or y_count is None:
        if x_count is not None and y_count is not None:
            x_dim = float(x_count) if x_dim is None else x_dim
            y_dim = float(y_count) if y_dim is None else y_dim
    if x_dim is None or y_dim is None or x_count is None or y_count is None:
        raise ValueError(
            "Provide positions, or provide x_dim, y_dim, x_count, and y_count to create a rectangular workplane grid."
        )
    if x_dim <= 0 or y_dim <= 0:
        raise ValueError("x_dim and y_dim must be greater than zero.")
    if x_count < 1 or y_count < 1:
        raise ValueError("x_count and y_count must be at least 1.")
    origin_values = origin or [0, 0, 0]
    if len(origin_values) != 3:
        raise ValueError("origin must include exactly three numbers when provided.")
    z = float(origin_values[2]) + float(0.8 if height is None else height)
    x_step = float(x_dim) / int(x_count)
    y_step = float(y_dim) / int(y_count)
    return [
        [
            float(origin_values[0]) + (x_index + 0.5) * x_step,
            float(origin_values[1]) + (y_index + 0.5) * y_step,
            z,
        ]
        for y_index in range(int(y_count))
        for x_index in range(int(x_count))
    ]

def _view_vector(value: VectorInput, field_name: str) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        try:
            return [float(value[axis]) for axis in ("x", "y", "z")]
        except KeyError as exc:
            raise ValueError(f"{field_name} dict must include x, y, and z.") from exc
    return [float(item) for item in value]

def _direction_from_target(
    position: list[float] | None,
    target: list[float] | None,
) -> list[float] | None:
    if target is None:
        return None
    origin = position or [0, 0, 0]
    if len(origin) != 3 or len(target) != 3:
        raise ValueError("position and target must both be [x, y, z] vectors.")
    return [float(target[index]) - float(origin[index]) for index in range(3)]

def _normalize_view_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.startswith("vt") and len(normalized) == 3:
        normalized = normalized[-1]
    allowed = {"v", "h", "l", "c", "a", "s"}
    if normalized not in allowed:
        raise ValueError("view_type must be one of v, h, l, c, a, s, or a Radiance vt* token.")
    return normalized

_FORMAL_ARTIFACT_TYPES = {
    "radiance_sky_file",
    "radiance_view",
    "radiance_sensor_grid",
    "radiance_hdr_image",
    "radiance_gif_image",
}

def _normalize_artifact_type(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized:
        return None
    if normalized not in _FORMAL_ARTIFACT_TYPES:
        allowed = ", ".join(sorted(_FORMAL_ARTIFACT_TYPES))
        raise ValueError(f"artifact_type must be one of: {allowed}.")
    return normalized

def _run_id_from_target(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("run_id", "identifier", "id"):
            found = value.get(key)
            if found:
                return str(found)
        target = value.get("target")
        if target is not None:
            return _run_id_from_target(target)
    return None

def _relative_run_parameter_match(
    garden_root_path: Path,
    garden_id: str,
    record: dict[str, Any],
) -> dict[str, Any] | None:
    parameter_path = record.get("radiance_parameters_path")
    if not parameter_path:
        return None
    path = (garden_root_path / str(parameter_path)).resolve()
    try:
        path.relative_to(garden_root_path)
    except ValueError:
        return None
    if not path.is_file():
        return None
    radiance_parameters = path.read_text(encoding="utf-8").strip()
    identifier = f"{record.get('run_id')}_radiance_parameters"
    target = {
        "target_type": "radiance_parameters",
        "domain": "honeybee_radiance",
        "garden_id": garden_id,
        "identifier": identifier,
        "path": str(parameter_path).replace("\\", "/"),
        "radiance_parameters": radiance_parameters,
        "value": radiance_parameters,
    }
    return {
        "identifier": identifier,
        "run_id": record.get("run_id"),
        "recipe": record.get("recipe"),
        "path": target["path"],
        "target": target,
        "radiance_parameters": radiance_parameters,
    }

def _sensor_grid_target_from_artifact(artifact: dict[str, Any], garden_target: dict[str, Any]) -> dict[str, Any]:
    path = str(artifact.get("path") or "")
    name = artifact.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("radiance_sensor_grid artifact requires a name.")
    return {
        "target_type": "radiance_sensor_grid",
        "domain": "honeybee_radiance",
        "garden_id": garden_target.get("garden_id"),
        "identifier": name,
        "path": path,
    }

def _sky_file_target_from_artifact(artifact: dict[str, Any], garden_target: dict[str, Any]) -> dict[str, Any]:
    path = str(artifact.get("path") or "")
    name = artifact.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("radiance_sky_file artifact requires a name.")
    return {
        "target_type": "radiance_sky_file",
        "domain": "honeybee_radiance",
        "garden_id": garden_target.get("garden_id"),
        "identifier": name,
        "path": path,
    }

def _view_target_from_artifact(artifact: dict[str, Any], garden_target: dict[str, Any]) -> dict[str, Any]:
    path = str(artifact.get("path") or "")
    name = artifact.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("radiance_view artifact requires a name.")
    return {
        "target_type": "radiance_view",
        "domain": "honeybee_radiance",
        "garden_id": garden_target.get("garden_id"),
        "identifier": name,
        "path": path,
    }

def _requires_radiance_sky_file(calculation_type: str) -> bool:
    return calculation_type.strip().lower().replace("-", "_").replace(" ", "_") == "point_in_time"

def _view_filter_from_target(view_target: dict[str, Any] | None) -> str | None:
    if not isinstance(view_target, dict):
        return None
    if view_target.get("target_type") != "radiance_view":
        raise ValueError("view_target must be a radiance_view target.")
    identifier = view_target.get("identifier")
    return str(identifier) if identifier else None


def register(mcp: FastMCP) -> None:
    """Register radiance tools."""

    @mcp.tool(
        name="RAD_Add_Luminaire_To_Model",
        description=(
            'Attach Radiance luminaire targets to a Garden Honeybee model for electric-lighting '
            'Radiance studies. Pass luminaire targets from RAD_Create_Luminaire plus an optional '
            'Honeybee model target. This edits model.properties.radiance.luminaires. Returns '
            'target, model_target, summary_view, persistence_receipt, and report for later search '
            'or simulation calls.'
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
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
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
        from garden.radiance.luminaires import add_radiance_luminaire_to_model as service

        return service(
            garden_root=garden_root,
            luminaires=luminaires,
            model_target=model_target,
            replace_existing=replace_existing,
        )

    @mcp.tool(
        name="RAD_Create_ASHRAE_Clear_Sky_WEA",
        description=(
            'Create a Radiance WEA file from ASHRAE Clear Sky conditions for a Garden location. '
            'Use this for clear-sky daylight or irradiance setup when the workflow needs '
            'synthetic WEA weather for RAD_Create_Sky_Matrix. This writes WEA data for Radiance '
            'sky workflows. Returns target, wea_target, summary_view, persistence_receipt, and '
            'report.'
        ),
        tags={
            "radiance",
            "sky",
            "weather",
            "wea",
            "ashrae-clear-sky",
        },
        timeout=60,
    )
    def create_ashrae_clear_sky_wea(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Stable identifier for the ASHRAE clear-sky WEA artifact and target."),
        ] = None,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Ladybug Location dictionary with city, latitude, longitude, time_zone, and optional elevation."),
        ] = None,
        city: Annotated[
            str | None,
            Field(description="Optional city name accepted when location is omitted."),
        ] = None,
        region: Annotated[
            str | None,
            Field(description="Optional state or region value used when location is omitted."),
        ] = None,
        latitude: Annotated[
            float | None,
            Field(description="Optional latitude accepted when location is omitted."),
        ] = None,
        longitude: Annotated[
            float | None,
            Field(description="Optional longitude accepted when location is omitted."),
        ] = None,
        time_zone: Annotated[
            float | None,
            Field(description="Optional time zone accepted when location is omitted."),
        ] = None,
        elevation: Annotated[
            float | None,
            Field(description="Optional elevation accepted when location is omitted."),
        ] = None,
        sky_clearness: Annotated[
            float,
            Field(description="ASHRAE sky clearness value. Default 1."),
        ] = 1,
        timestep: Annotated[
            int,
            Field(description="WEA timestep. Default 1 for hourly data."),
        ] = 1,
        is_leap_year: Annotated[
            bool,
            Field(description="Whether to create a leap-year WEA."),
        ] = False,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for WEA artifacts."),
        ] = "artifacts/radiance/wea",
        write_hours: Annotated[
            bool,
            Field(description="Whether to write hour values into the WEA file."),
        ] = False,
        return_object_dict: Annotated[
            bool,
            Field(description='Return the full Wea object_dict. Keep false for compact target handoff.'),
        ] = False,
    ) -> dict[str, Any]:
        """Create a clear-sky WEA target."""
        from garden.radiance.sky import create_ashrae_clear_sky_wea as service

        if identifier is None:
            identifier = city or "ashrae_clear_sky_wea"
        if location is None:
            if latitude is None or longitude is None or time_zone is None:
                raise ValueError(
                    "Provide location, or provide latitude, longitude, and time_zone."
                )
            location = {
                "type": "Location",
                "city": city or identifier,
                "state": region,
                "latitude": latitude,
                "longitude": longitude,
                "time_zone": time_zone,
                "elevation": 0 if elevation is None else elevation,
            }
        return service(
            garden_root=garden_root,
            identifier=identifier,
            location=location,
            sky_clearness=sky_clearness,
            timestep=timestep,
            is_leap_year=is_leap_year,
            output_subdir=output_subdir,
            write_hours=write_hours,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="RAD_Create_CIE_Standard_Sky",
        description=(
            'Create a Garden radiance_sky_file target backed by a Radiance gensky command. Use '
            'this for a single-timestep CIE standard sky such as sunny, cloudy, uniform cloudy, '
            'or intermediate. The persisted .sky file starts with !gensky and serves as a compact '
            'Radiance scene include.'
        ),
        tags={
            "radiance",
            "sky",
            "weather",
            "point-in-time",
            "cie",
        },
        timeout=60,
    )
    def create_cie_standard_sky(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Stable identifier for the point-in-time CIE Radiance .sky artifact and target."),
        ] = None,
        month: Annotated[
            int | None,
            Field(description="Month number for date/time mode. Required unless solar angles are used."),
        ] = None,
        day: Annotated[
            int | None,
            Field(description="Day of month for date/time mode. Required unless solar angles are used."),
        ] = None,
        time: Annotated[
            str | float | None,
            Field(description="Time for date/time mode, for example 12:00 or 12.0."),
        ] = None,
        time_zone: Annotated[
            str | int | float | None,
            Field(description="Optional Radiance time zone token such as MST or EST. Numeric offsets like -5 are accepted and normalized to common Radiance tokens."),
        ] = None,
        solar_time: Annotated[
            bool,
            Field(description="Use local solar time instead of local standard time."),
        ] = False,
        solar_altitude: Annotated[
            float | None,
            Field(description="Optional sun altitude angle in degrees. Provide with solar_azimuth instead of month/day/time."),
        ] = None,
        solar_azimuth: Annotated[
            float | None,
            Field(description="Optional sun azimuth angle in degrees. Provide with solar_altitude instead of month/day/time."),
        ] = None,
        sky_type: Annotated[
            str,
            Field(description="CIE sky type: sunny, sunny_no_sun, cloudy, uniform_cloudy, intermediate, or intermediate_no_sun."),
        ] = "sunny",
        latitude: Annotated[
            float | None,
            Field(description="Optional site latitude in degrees for the gensky -a option."),
        ] = None,
        longitude: Annotated[
            float | None,
            Field(description="Optional site longitude in degrees for the gensky -o option."),
        ] = None,
        standard_meridian: Annotated[
            float | None,
            Field(description="Optional standard meridian for the gensky -m option."),
        ] = None,
        ground_reflectance: Annotated[
            float | None,
            Field(description="Optional average ground reflectance for the gensky -g option."),
        ] = None,
        sky_turbidity: Annotated[
            float | None,
            Field(description="Optional sky turbidity for the gensky -t option."),
        ] = None,
        solar_radiance: Annotated[
            float | None,
            Field(description="Optional solar radiance for the gensky -r option."),
        ] = None,
        direct_horizontal_irradiance: Annotated[
            float | None,
            Field(description="Optional direct horizontal irradiance for the gensky -R option."),
        ] = None,
        zenith_brightness: Annotated[
            float | None,
            Field(description="Optional zenith brightness for the gensky -b option."),
        ] = None,
        diffuse_horizontal_irradiance: Annotated[
            float | None,
            Field(description="Optional diffuse horizontal irradiance for the gensky -B option."),
        ] = None,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for Radiance .sky artifacts."),
        ] = "artifacts/radiance/sky",
    ) -> dict[str, Any]:
        """Create a CIE standard Radiance sky file."""
        from garden.radiance.sky import create_cie_standard_sky as service

        if identifier is None:
            identifier = "cie_standard_sky"
        return service(
            garden_root=garden_root,
            identifier=identifier,
            month=month,
            day=day,
            time=time,
            time_zone=_normalize_time_zone(time_zone),
            solar_time=solar_time,
            solar_altitude=solar_altitude,
            solar_azimuth=solar_azimuth,
            sky_type=sky_type,
            latitude=latitude,
            longitude=longitude,
            standard_meridian=standard_meridian,
            ground_reflectance=ground_reflectance,
            sky_turbidity=sky_turbidity,
            solar_radiance=solar_radiance,
            direct_horizontal_irradiance=direct_horizontal_irradiance,
            zenith_brightness=zenith_brightness,
            diffuse_horizontal_irradiance=diffuse_horizontal_irradiance,
            output_subdir=output_subdir,
        )

    @mcp.tool(
        name="RAD_Create_Climate_Based_Sky",
        description=(
            'Create a Garden radiance_sky_file target backed by a Radiance gendaylit command. Use '
            'this for a single-timestep climate-based sky from direct normal plus diffuse '
            'horizontal irradiance or illuminance. The persisted .sky file starts with !gendaylit '
            'and serves as a compact Radiance scene include.'
        ),
        tags={
            "radiance",
            "sky",
            "weather",
            "point-in-time",
            "climate-based",
        },
        timeout=60,
    )
    def create_climate_based_sky(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Stable identifier for the point-in-time climate-based Radiance .sky artifact and target."),
        ] = None,
        month: Annotated[
            int | None,
            Field(description="Month number for date/time mode. Required unless solar angles are used."),
        ] = None,
        day: Annotated[
            int | None,
            Field(description="Day of month for date/time mode. Required unless solar angles are used."),
        ] = None,
        time: Annotated[
            str | float | None,
            Field(description="Time for date/time mode, for example 12:00 or 12.0."),
        ] = None,
        time_zone: Annotated[
            str | int | float | None,
            Field(description="Optional Radiance time zone token such as MST or EST. Numeric offsets like -7 are accepted and normalized to common Radiance tokens."),
        ] = None,
        solar_time: Annotated[
            bool,
            Field(description="Use local solar time instead of local standard time."),
        ] = False,
        solar_altitude: Annotated[
            float | None,
            Field(description="Optional sun altitude angle in degrees. Provide with solar_azimuth instead of month/day/time."),
        ] = None,
        solar_azimuth: Annotated[
            float | None,
            Field(description="Optional sun azimuth angle in degrees. Provide with solar_altitude instead of month/day/time."),
        ] = None,
        direct_normal_irradiance: Annotated[
            float | None,
            Field(description="Direct normal irradiance for the gendaylit -W option. Provide with diffuse_horizontal_irradiance."),
        ] = None,
        diffuse_horizontal_irradiance: Annotated[
            float | None,
            Field(description="Diffuse horizontal irradiance for the gendaylit -W option. Provide with direct_normal_irradiance."),
        ] = None,
        direct_normal_illuminance: Annotated[
            float | None,
            Field(description="Direct normal illuminance for the gendaylit -L option. Provide with diffuse_horizontal_illuminance."),
        ] = None,
        diffuse_horizontal_illuminance: Annotated[
            float | None,
            Field(description="Diffuse horizontal illuminance for the gendaylit -L option. Provide with direct_normal_illuminance."),
        ] = None,
        output_mode: Annotated[
            int | None,
            Field(description="Optional gendaylit -O output mode, for example 0 for visible radiation."),
        ] = None,
        sky_part: Annotated[
            str | None,
            Field(description="Optional sky part value: visible/luminance or solar/radiance."),
        ] = None,
        latitude: Annotated[
            float | None,
            Field(description="Optional site latitude in degrees for the gendaylit -a option."),
        ] = None,
        longitude: Annotated[
            float | None,
            Field(description="Optional site longitude in degrees for the gendaylit -o option."),
        ] = None,
        standard_meridian: Annotated[
            float | None,
            Field(description="Optional standard meridian for the gendaylit -m option."),
        ] = None,
        ground_reflectance: Annotated[
            float | None,
            Field(description="Optional average ground reflectance for the gendaylit -g option."),
        ] = None,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for Radiance .sky artifacts."),
        ] = "artifacts/radiance/sky",
    ) -> dict[str, Any]:
        """Create a climate-based Radiance sky file."""
        from garden.radiance.sky import create_climate_based_sky as service

        if identifier is None:
            identifier = "climate_based_sky"
        return service(
            garden_root=garden_root,
            identifier=identifier,
            month=month,
            day=day,
            time=time,
            time_zone=_normalize_time_zone(time_zone),
            solar_time=solar_time,
            solar_altitude=solar_altitude,
            solar_azimuth=solar_azimuth,
            direct_normal_irradiance=direct_normal_irradiance,
            diffuse_horizontal_irradiance=diffuse_horizontal_irradiance,
            direct_normal_illuminance=direct_normal_illuminance,
            diffuse_horizontal_illuminance=diffuse_horizontal_illuminance,
            output_mode=output_mode,
            sky_part=sky_part,
            latitude=latitude,
            longitude=longitude,
            standard_meridian=standard_meridian,
            ground_reflectance=ground_reflectance,
            output_subdir=output_subdir,
        )

    @mcp.tool(
        name="RAD_Create_Glass_Modifier",
        description=(
            'Create a Honeybee Radiance Glass modifier for daylight and view workflows. The SDK '
            'glass interface uses transmittance or transmissivity values, not reflectance. Use '
            'garden_root and return_object_dict=false to save a reusable Garden Properties '
            'Library modifier target.'
        ),
        tags={
            "radiance",
            "modifier",
            "material",
            "author",
            "glass",
        },
        timeout=20,
    )
    def create_radiance_glass_modifier(
        identifier: Annotated[str, Field(description="Radiance Glass modifier identifier.")],
        rgb_transmittance: Annotated[
            float | list[float] | None,
            Field(description="Simple visible transmittance for all channels, or [r, g, b] transmittance values."),
        ] = None,
        transmittance: Annotated[
            float | list[float] | None,
            Field(description="Optional natural synonym for rgb_transmittance. Accepts a number or [r, g, b] values."),
        ] = None,
        r_transmittance: Annotated[
            float | None,
            Field(description="Red transmittance. Provide with g_transmittance and b_transmittance."),
        ] = None,
        g_transmittance: Annotated[
            float | None,
            Field(description="Green transmittance. Provide with r_transmittance and b_transmittance."),
        ] = None,
        b_transmittance: Annotated[
            float | None,
            Field(description="Blue transmittance. Provide with r_transmittance and g_transmittance."),
        ] = None,
        rgb_transmissivity: Annotated[
            float | list[float] | None,
            Field(description="Simple transmissivity for all channels, or [r, g, b] transmissivity values."),
        ] = None,
        transmissivity: Annotated[
            float | list[float] | None,
            Field(description="Optional natural synonym for rgb_transmissivity. Accepts a number or [r, g, b] values."),
        ] = None,
        r_transmissivity: Annotated[
            float | None,
            Field(description="Red transmissivity. Provide with g_transmissivity and b_transmissivity."),
        ] = None,
        g_transmissivity: Annotated[
            float | None,
            Field(description="Green transmissivity. Provide with r_transmissivity and b_transmissivity."),
        ] = None,
        b_transmissivity: Annotated[
            float | None,
            Field(description="Blue transmissivity. Provide with r_transmissivity and g_transmissivity."),
        ] = None,
        refraction_index: Annotated[
            float | None,
            Field(description="Optional glass refraction index, such as 1.52 for float glass."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full modifier object_dict. Set false with garden_root."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance Glass modifier."""
        from garden.radiance.modifiers import create_radiance_glass_modifier as service

        if rgb_transmittance is None:
            rgb_transmittance = transmittance
        if rgb_transmissivity is None:
            rgb_transmissivity = transmissivity
        if isinstance(rgb_transmittance, list):
            if len(rgb_transmittance) != 3:
                raise ValueError("rgb_transmittance list must have three values.")
            r_transmittance, g_transmittance, b_transmittance = [
                float(value) for value in rgb_transmittance
            ]
            rgb_transmittance = None
        if isinstance(rgb_transmissivity, list):
            if len(rgb_transmissivity) != 3:
                raise ValueError("rgb_transmissivity list must have three values.")
            r_transmissivity, g_transmissivity, b_transmissivity = [
                float(value) for value in rgb_transmissivity
            ]
            rgb_transmissivity = None
        return service(
            identifier=identifier,
            rgb_transmittance=rgb_transmittance,
            r_transmittance=r_transmittance,
            g_transmittance=g_transmittance,
            b_transmittance=b_transmittance,
            rgb_transmissivity=rgb_transmissivity,
            r_transmissivity=r_transmissivity,
            g_transmissivity=g_transmissivity,
            b_transmissivity=b_transmissivity,
            refraction_index=refraction_index,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="RAD_Create_Luminaire",
        description=(
            'Create a Honeybee Radiance Luminaire from IES LM-63 text or a Garden-contained IES '
            'file path. Supports LuminaireZone placement instances, CustomLamp settings, and '
            'Garden Properties Library saving with garden_root and return_object_dict=false. Use '
            'the returned target as a reusable luminaire or IES resource for Radiance workflows.'
        ),
        tags={
            "radiance",
            "model",
            "edit",
            "luminaire",
            "electric-lighting",
        },
        timeout=20,
    )
    def create_radiance_luminaire(
        ies_content: Annotated[
            str | None,
            Field(description="IES LM-63 file text. Provide exactly one of ies_content or ies_path."),
        ] = None,
        ies_path: Annotated[
            str | None,
            Field(description="Path to an existing IES LM-63 file. Provide exactly one of ies_path or ies_content."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional Luminaire identifier. If omitted, the SDK derives one from IES metadata or file name."),
        ] = None,
        instances: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional LuminaireZone instances. Each item needs point as [x,y,z] or Point3D dict, and may include spin, tilt, rotation, or aiming_point."),
        ] = None,
        custom_lamp: Annotated[
            dict[str, Any] | None,
            Field(description="Optional SDK CustomLamp dict or simple settings like {'mode':'rgb','rgb':[1,0.8,0.6]} or {'mode':'color_temperature','color_temperature':3000}."),
        ] = None,
        light_loss_factor: Annotated[
            float,
            Field(description="Positive light loss multiplier for lamp/system depreciation."),
        ] = 1.0,
        candela_multiplier: Annotated[
            float,
            Field(description="Positive candela multiplier applied to the IES distribution."),
        ] = 1.0,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description=(
                'Return the full Luminaire object_dict. Set false with garden_root for a compact '
                'target response.'
            )),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance Luminaire from IES content or path."""
        from garden.radiance.luminaires import create_radiance_luminaire as service

        return service(
            ies_content=ies_content,
            ies_path=ies_path,
            identifier=identifier,
            instances=instances,
            custom_lamp=custom_lamp,
            light_loss_factor=light_loss_factor,
            candela_multiplier=candela_multiplier,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="RAD_Create_Metal_Modifier",
        description=(
            'Create a Honeybee Radiance Metal modifier with RGB reflectance, specularity, and '
            'roughness. Use garden_root and return_object_dict=false to save a reusable Garden '
            'Properties Library modifier target. This controls Radiance optical appearance.'
        ),
        tags={
            "radiance",
            "modifier",
            "material",
            "author",
            "metal",
        },
        timeout=20,
    )
    def create_radiance_metal_modifier(
        identifier: Annotated[str, Field(description="Radiance Metal modifier identifier.")],
        rgb_reflectance: Annotated[
            float | None,
            Field(description="Simple reflectance for red, green, and blue channels."),
        ] = None,
        r_reflectance: Annotated[
            float | None,
            Field(description="Red reflectance. Provide with g_reflectance and b_reflectance."),
        ] = None,
        g_reflectance: Annotated[
            float | None,
            Field(description="Green reflectance. Provide with r_reflectance and b_reflectance."),
        ] = None,
        b_reflectance: Annotated[
            float | None,
            Field(description="Blue reflectance. Provide with r_reflectance and g_reflectance."),
        ] = None,
        specularity: Annotated[float, Field(description="Metal specularity fraction.")] = 0.9,
        roughness: Annotated[float, Field(description="Metal roughness fraction.")] = 0.0,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full modifier object_dict. Set false with garden_root."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance Metal modifier."""
        from garden.radiance.modifiers import create_radiance_metal_modifier as service

        return service(
            identifier=identifier,
            rgb_reflectance=rgb_reflectance,
            r_reflectance=r_reflectance,
            g_reflectance=g_reflectance,
            b_reflectance=b_reflectance,
            specularity=specularity,
            roughness=roughness,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="RAD_Create_Mirror_Modifier",
        description=(
            'Create a Honeybee Radiance Mirror modifier with RGB reflectance for planar '
            'virtual-source reflections. Use garden_root and return_object_dict=false to save a '
            'reusable Garden Properties Library modifier target.'
        ),
        tags={
            "radiance",
            "modifier",
            "material",
            "author",
            "mirror",
        },
        timeout=20,
    )
    def create_radiance_mirror_modifier(
        identifier: Annotated[str, Field(description="Radiance Mirror modifier identifier.")],
        rgb_reflectance: Annotated[
            float | None,
            Field(description="Simple reflectance for red, green, and blue channels."),
        ] = None,
        r_reflectance: Annotated[
            float | None,
            Field(description="Red reflectance. Provide with g_reflectance and b_reflectance."),
        ] = None,
        g_reflectance: Annotated[
            float | None,
            Field(description="Green reflectance. Provide with r_reflectance and b_reflectance."),
        ] = None,
        b_reflectance: Annotated[
            float | None,
            Field(description="Blue reflectance. Provide with r_reflectance and g_reflectance."),
        ] = None,
        alternate_material: Annotated[
            str | None,
            Field(description="Optional alternate material for non-source rays, such as void."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full modifier object_dict. Set false with garden_root."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance Mirror modifier."""
        from garden.radiance.modifiers import create_radiance_mirror_modifier as service

        return service(
            identifier=identifier,
            rgb_reflectance=rgb_reflectance,
            r_reflectance=r_reflectance,
            g_reflectance=g_reflectance,
            b_reflectance=b_reflectance,
            alternate_material=alternate_material,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="RAD_Create_Opaque_Modifier",
        description=(
            'Create an opaque Honeybee Radiance modifier using the SDK Plastic material with RGB '
            'reflectance. Use garden_root and return_object_dict=false to save a reusable Garden '
            'Properties Library modifier target for Honeybee face, aperture, door, or shade '
            'Radiance modifier fields.'
        ),
        tags={
            "radiance",
            "modifier",
            "material",
            "author",
            "opaque",
        },
        timeout=20,
    )
    def create_radiance_opaque_modifier(
        identifier: Annotated[str, Field(description="Radiance Plastic/Opaque modifier identifier.")],
        rgb_reflectance: Annotated[
            float | list[float] | None,
            Field(description="Simple reflectance for red, green, and blue channels."),
        ] = None,
        r_reflectance: Annotated[
            float | None,
            Field(description="Red reflectance. Provide with g_reflectance and b_reflectance."),
        ] = None,
        g_reflectance: Annotated[
            float | None,
            Field(description="Green reflectance. Provide with r_reflectance and b_reflectance."),
        ] = None,
        b_reflectance: Annotated[
            float | None,
            Field(description="Blue reflectance. Provide with r_reflectance and g_reflectance."),
        ] = None,
        specularity: Annotated[float, Field(description="Plastic specularity fraction.")] = 0.0,
        roughness: Annotated[float, Field(description="Plastic roughness fraction.")] = 0.0,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full modifier object_dict. Set false with garden_root."),
        ] = True,
    ) -> dict[str, Any]:
        """Create an opaque Honeybee Radiance modifier."""
        from garden.radiance.modifiers import create_radiance_opaque_modifier as service

        if isinstance(rgb_reflectance, list):
            if len(rgb_reflectance) != 3:
                raise ValueError("rgb_reflectance list must have three values.")
            r_reflectance, g_reflectance, b_reflectance = [
                float(value) for value in rgb_reflectance
            ]
            rgb_reflectance = None
        return service(
            identifier=identifier,
            rgb_reflectance=rgb_reflectance,
            r_reflectance=r_reflectance,
            g_reflectance=g_reflectance,
            b_reflectance=b_reflectance,
            specularity=specularity,
            roughness=roughness,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="RAD_Create_Parameters",
        description=(
            'Create recommended Radiance command parameters for rtrace grid, rpict view, or '
            'rfluxmtx annual/matrix daylight recipes. Pass the returned radiance_parameters '
            'string or target to RAD_Start_Grid_Simulation, RAD_Start_View_Simulation, or '
            'RAD_Start_Matrix_Simulation. Returns target, summary_view, and report.'
        ),
        tags={
            "radiance",
            "simulate",
            "author",
            "parameters",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def create_radiance_parameters(
        recipe_type: Annotated[
            str,
            Field(
                description="Radiance recipe family or command: point-in-time-grid, daylight-factor, point-in-time-view, annual-daylight, annual-irradiance, cumulative-radiation, rtrace, rpict, or rfluxmtx.",
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
        from garden.radiance.parameters import create_radiance_parameters as service

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

    @mcp.tool(
        name="RAD_Create_Sensor_Grid",
        description=(
            'Create a Honeybee Radiance SensorGrid from explicit sensor positions or rectangular '
            'workplane dimensions. With garden_root, the tool writes a Garden .pts artifact and '
            'returns a compact radiance_sensor_grid target. Set attach_to_model=true to add the '
            'SensorGrid to the Honeybee model Radiance properties for later daylight recipes.'
        ),
        tags={
            "radiance",
            "sensor-grid",
            "author",
            "pts",
        },
        timeout=60,
    )
    def create_radiance_sensor_grid(
        identifier: Annotated[
            str | None,
            Field(description="Stable Radiance SensorGrid identifier. Defaults to sensor_grid when omitted."),
        ] = None,
        positions: Annotated[
            list[list[float]] | None,
            Field(description="Sensor positions as [[x, y, z], ...]. Omit only when using x_dim/y_dim/x_count/y_count."),
        ] = None,
        direction: Annotated[
            list[float] | None,
            Field(description="Optional shared sensor direction [x, y, z]. Default is [0, 0, 1]. Use instead of directions."),
        ] = None,
        directions: Annotated[
            list[list[float]] | None,
            Field(description="Optional per-position directions as [[x, y, z], ...]. Must match positions length. Use instead of direction."),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional display name."),
        ] = None,
        room_identifier: Annotated[
            str | None,
            Field(description="Optional Honeybee Room identifier associated with this grid."),
        ] = None,
        room_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee Room target used to infer room_identifier when provided."),
        ] = None,
        x_dim: Annotated[
            float | None,
            Field(description="Optional rectangular workplane width in model units. Used only when positions is omitted."),
        ] = None,
        y_dim: Annotated[
            float | None,
            Field(description="Optional rectangular workplane depth in model units. Used only when positions is omitted."),
        ] = None,
        height: Annotated[
            float | None,
            Field(description="Optional workplane height above origin. Defaults to 0.8 when generating positions."),
        ] = None,
        x_count: Annotated[
            int | None,
            Field(description="Optional number of sensors along x when generating a rectangular grid."),
        ] = None,
        y_count: Annotated[
            int | None,
            Field(description="Optional number of sensors along y when generating a rectangular grid."),
        ] = None,
        grid_spacing: Annotated[
            float | None,
            Field(description="Optional spacing used to derive x_count/y_count from x_dim/y_dim."),
        ] = None,
        origin: Annotated[
            VectorInput,
            Field(description="Optional rectangular grid origin [x, y, z], or {'x': x, 'y': y, 'z': z}. Defaults to [0, 0, 0]."),
        ] = None,
        group_identifier: Annotated[
            str | None,
            Field(description="Optional Radiance group identifier."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target. Used when attach_to_model is true; omitted means Garden base model."),
        ] = None,
        attach_to_model: Annotated[
            bool,
            Field(description="When true, add the SensorGrid to model.properties.radiance.sensor_grids and save the model."),
        ] = False,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for Radiance sensor .pts artifacts."),
        ] = "artifacts/radiance/sensors",
        return_object_dict: Annotated[
            bool,
            Field(description=(
                'Return the full SensorGrid object_dict. Keep false for compact target handoff.'
            )),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance SensorGrid."""
        from garden.radiance.assets import create_radiance_sensor_grid as service

        if identifier is None:
            identifier = "sensor_grid"
        if model_target is not None and not attach_to_model:
            attach_to_model = True
        origin = _sensor_grid_vector(origin, "origin")
        if (
            positions is None
            and x_dim is None
            and y_dim is None
            and grid_spacing is not None
            and x_count is not None
            and y_count is not None
        ):
            x_dim = float(grid_spacing) * int(x_count)
            y_dim = float(grid_spacing) * int(y_count)
        positions = _positions_from_rectangular_grid(
            positions=positions,
            x_dim=x_dim,
            y_dim=y_dim,
            height=height,
            x_count=x_count,
            y_count=y_count,
            grid_spacing=grid_spacing,
            origin=origin,
        )
        room_identifier = _room_identifier_from_target(room_identifier, room_target)
        return service(
            identifier=identifier,
            positions=positions,
            direction=direction,
            directions=directions,
            display_name=display_name,
            room_identifier=room_identifier,
            group_identifier=group_identifier,
            garden_root=garden_root,
            model_target=model_target,
            attach_to_model=attach_to_model,
            output_subdir=output_subdir,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="RAD_Create_Sensor_Grid_From_Object",
        description=(
            "Create a Honeybee Radiance SensorGrid by sampling the surface of "
            "a Honeybee Face, Aperture, Door, Shade, shading panel, PV panel, "
            "or solar collector target. Use this for object-hosted grids, "
            "shade irradiance sensors, and PV solar-potential studies. Pass "
            "object_target from Honeybee object search or shade creation plus "
            "garden_root. Set attach_to_model=true to attach the grid for "
            "Radiance grid or annual-irradiance recipes. This samples existing "
            "geometry and preserves its mesh. Room-hosted surfaces also set "
            "room_identifier for daylight compliance assessments. Use a room "
            "floor face with flip_direction=true and offset=0.8 for an upward "
            "workplane grid."
        ),
        tags={
            "radiance",
            "sensor-grid",
            "author",
            "object-surface",
        },
        timeout=60,
    )
    def create_radiance_sensor_grid_from_object(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        object_target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee face, aperture, door, or shade target to sample into a Radiance SensorGrid. Pass matches[i].target from HB_Search_Model_Objects or target from HB_Create_Shade.'
            ),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Stable SensorGrid identifier. Defaults to object_sensor_grid."),
        ] = None,
        grid_spacing: Annotated[
            float | None,
            Field(description="Optional approximate spacing in model units used to derive x_count/y_count."),
        ] = None,
        x_count: Annotated[
            int | None,
            Field(description="Optional number of samples along the local object x direction."),
        ] = None,
        y_count: Annotated[
            int | None,
            Field(description="Optional number of samples along the local object y direction."),
        ] = None,
        offset: Annotated[
            float,
            Field(description="Offset distance along the object normal. Defaults to 0.01 model units."),
        ] = 0.01,
        flip_direction: Annotated[
            bool,
            Field(description="When true, flip the sensor direction and offset to the reverse normal."),
        ] = False,
        display_name: Annotated[
            str | None,
            Field(description="Optional display name."),
        ] = None,
        group_identifier: Annotated[
            str | None,
            Field(description="Optional Radiance group identifier."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target. Defaults to the Garden base model."),
        ] = None,
        attach_to_model: Annotated[
            bool,
            Field(description="When true, add the SensorGrid to model.properties.radiance.sensor_grids and save the model."),
        ] = False,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for Radiance sensor .pts artifacts."),
        ] = "artifacts/radiance/sensors",
        return_object_dict: Annotated[
            bool,
            Field(description=(
                'Return the full SensorGrid object_dict. Keep false for compact target handoff.'
            )),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance SensorGrid from an object surface."""
        from garden.radiance.assets import create_radiance_sensor_grid_from_object as service

        if identifier is None:
            identifier = "object_sensor_grid"
        return service(
            identifier=identifier,
            object_target=object_target,
            garden_root=garden_root,
            grid_spacing=grid_spacing,
            x_count=x_count,
            y_count=y_count,
            offset=offset,
            flip_direction=flip_direction,
            display_name=display_name,
            group_identifier=group_identifier,
            model_target=model_target,
            attach_to_model=attach_to_model,
            output_subdir=output_subdir,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="RAD_Create_Shade_State",
        description=(
            "Create a Honeybee RadianceShadeState dictionary for dynamic "
            "Shades. Optional modifier may be a modifier dict, Garden "
            "Properties Library modifier target, or standards-library "
            "identifier. Optional shades is a list of StateGeometry "
            "dictionaries from RAD_Create_State_Geometry. Return value is "
            "an object_dict/state_dict, not a Garden target; pass it into "
            "RAD_Setup_Dynamic_Group states=[...] before running recipes."
        ),
        tags={
            "radiance",
            "model",
            "edit",
            "shade-state",
            "dynamic-state",
        },
        timeout=20,
    )
    def create_radiance_shade_state(
        modifier: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Radiance modifier dict, Garden Properties Library modifier target, or standards-library identifier."
            ),
        ] = None,
        shades: Annotated[
            list[dict[str, Any] | None] | None,
            Field(description="Optional list of Radiance StateGeometry dictionaries for dynamic shade geometry."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee RadianceShadeState."""
        from garden.radiance.dynamic import create_radiance_shade_state as service

        if shades is not None:
            shades = [shade for shade in shades if shade is not None]
        result = service(modifier=modifier, shades=shades, garden_root=garden_root)
        result.setdefault("state_dict", result.get("object_dict"))
        return result

    @mcp.tool(
        name="RAD_Create_Sky",
        description=(
            'Create a Radiance sky definition artifact from standard sky inputs for point-in-time '
            'daylight workflows. Use RAD_Create_Sky_File when a recipe needs a persisted sky file '
            'target. This creates sky input data only. Returns target, sky_target, summary_view, '
            'persistence_receipt, and report.'
        ),
        tags={
            "radiance",
            "sky",
            "weather",
            "point-in-time",
            "sky-file",
        },
        timeout=60,
    )
    def create_radiance_sky(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        identifier: Annotated[str, Field(description="Stable identifier for the point-in-time Radiance .sky artifact and target.")] = "radiance_sky",
        month: Annotated[int, Field(description="Month number for date/time mode.")] = 6,
        day: Annotated[int, Field(description="Day of month for date/time mode.")] = 21,
        time: Annotated[str | float, Field(description="Time for date/time mode, for example 12:00 or 12.0.")] = "12:00",
        sky_type: Annotated[str, Field(description="CIE sky type such as sunny, cloudy, or intermediate.")] = "sunny",
        latitude: Annotated[float | None, Field(description="Optional site latitude.")] = None,
        longitude: Annotated[float | None, Field(description="Optional site longitude.")] = None,
        standard_meridian: Annotated[float | None, Field(description="Optional standard meridian.")] = None,
        ground_reflectance: Annotated[float | None, Field(description="Optional average ground reflectance.")] = None,
        output_subdir: Annotated[str, Field(description="Garden-relative output folder for Radiance .sky artifacts.")] = "artifacts/radiance/sky",
    ) -> dict[str, Any]:
        """Create a CIE standard Radiance sky file."""
        from garden.radiance.sky import create_cie_standard_sky as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            month=month,
            day=day,
            time=time,
            sky_type=sky_type,
            latitude=latitude,
            longitude=longitude,
            standard_meridian=standard_meridian,
            ground_reflectance=ground_reflectance,
            output_subdir=output_subdir,
        )

    @mcp.tool(
        name="RAD_Create_Sky_File",
        description=(
            'Create a Garden Radiance .sky file target for point-in-time grid or view recipes. '
            'Pass a Radiance sky definition or sky dictionary from RAD_Create_Sky, '
            'RAD_Create_CIE_Standard_Sky, or RAD_Create_Climate_Based_Sky. This persists a sky '
            'include for recipes. Returns target, sky_file_target, summary_view, '
            'persistence_receipt, and report.'
        ),
        tags={
            "radiance",
            "sky",
            "weather",
            "point-in-time",
            "sky-file",
        },
        timeout=60,
    )
    def create_radiance_sky_file(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        identifier: Annotated[str, Field(description="Stable identifier for the point-in-time Radiance .sky artifact and target.")] = "radiance_sky_file",
        month: Annotated[int, Field(description="Month number for date/time mode.")] = 6,
        day: Annotated[int, Field(description="Day of month for date/time mode.")] = 21,
        time: Annotated[str | float, Field(description="Time for date/time mode.")] = "12:00",
        sky_type: Annotated[str, Field(description="CIE sky type such as sunny or cloudy.")] = "sunny",
        ground_reflectance: Annotated[float | None, Field(description="Optional average ground reflectance.")] = None,
        output_subdir: Annotated[str, Field(description="Garden-relative output folder.")] = "artifacts/radiance/sky",
    ) -> dict[str, Any]:
        """Create a Radiance sky file."""
        from garden.radiance.sky import create_cie_standard_sky as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            month=month,
            day=day,
            time=time,
            sky_type=sky_type,
            ground_reflectance=ground_reflectance,
            output_subdir=output_subdir,
        )

    @mcp.tool(
        name="RAD_Create_State_Geometry",
        description=(
            'Create a Honeybee Radiance StateGeometry dictionary for dynamic shade or subface '
            'states. Provide geometry as a Ladybug Face3D dict or vertices as [[x, y, z], ...]. '
            'Optional modifier may be a modifier dict, Garden Properties Library modifier target, '
            'or standards-library identifier. This returns a state-geometry object_dict for state '
            'tools.'
        ),
        tags={
            "radiance",
            "model",
            "edit",
            "state-geometry",
            "dynamic-state",
        },
        timeout=20,
    )
    def create_radiance_state_geometry(
        identifier: Annotated[
            str | None,
            Field(description=(
                "Honeybee Radiance StateGeometry identifier. Defaults to 'state_geometry' when "
                'omitted.'
            )),
        ] = None,
        geometry: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Ladybug Geometry Face3D dictionary."),
        ] = None,
        vertices: Annotated[
            list[list[float]] | None,
            Field(description="Optional vertices as [[x, y, z], ...]. Use instead of geometry."),
        ] = None,
        modifier: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Radiance modifier dict, Garden Properties Library modifier target, or standards-library identifier."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance StateGeometry."""
        from garden.radiance.dynamic import create_radiance_state_geometry as service

        identifier = identifier or "state_geometry"
        return service(
            identifier=identifier,
            geometry=geometry,
            vertices=vertices,
            modifier=modifier,
            garden_root=garden_root,
        )

    @mcp.tool(
        name="RAD_Create_Subface_State",
        description=(
            'Create a Honeybee RadianceSubFaceState dictionary for dynamic Apertures or Doors. '
            'Optional modifier may be a modifier dict, Garden Properties Library modifier target, '
            'or standards-library identifier. Optional shades is a list of StateGeometry '
            'dictionaries from RAD_Create_State_Geometry. This returns an object_dict for dynamic '
            'state assembly.'
        ),
        tags={
            "radiance",
            "model",
            "edit",
            "subface-state",
            "dynamic-state",
        },
        timeout=20,
    )
    def create_radiance_subface_state(
        modifier: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Radiance modifier dict, Garden Properties Library modifier target, or standards-library identifier."
            ),
        ] = None,
        shades: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional list of Radiance StateGeometry dictionaries for dynamic aperture/door shade geometry."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee RadianceSubFaceState."""
        from garden.radiance.dynamic import create_radiance_subface_state as service

        return service(modifier=modifier, shades=shades, garden_root=garden_root)

    @mcp.tool(
        name="RAD_Create_Trans_Modifier",
        description=(
            'Create a Honeybee Radiance Trans translucent modifier with RGB reflectance plus '
            'transmitted diffuse and specular fractions. Use garden_root and '
            'return_object_dict=false to save a reusable Garden Properties Library modifier '
            'target.'
        ),
        tags={
            "radiance",
            "modifier",
            "material",
            "author",
            "trans",
        },
        timeout=20,
    )
    def create_radiance_trans_modifier(
        identifier: Annotated[str, Field(description="Radiance Trans modifier identifier.")],
        rgb_reflectance: Annotated[
            float | None,
            Field(description="Simple reflectance for red, green, and blue channels."),
        ] = None,
        r_reflectance: Annotated[
            float | None,
            Field(description="Red reflectance. Provide with g_reflectance and b_reflectance."),
        ] = None,
        g_reflectance: Annotated[
            float | None,
            Field(description="Green reflectance. Provide with r_reflectance and b_reflectance."),
        ] = None,
        b_reflectance: Annotated[
            float | None,
            Field(description="Blue reflectance. Provide with r_reflectance and g_reflectance."),
        ] = None,
        specularity: Annotated[float, Field(description="Trans specularity fraction.")] = 0.0,
        roughness: Annotated[float, Field(description="Trans roughness fraction.")] = 0.0,
        transmitted_diff: Annotated[
            float,
            Field(description="Diffuse transmitted fraction."),
        ] = 0.0,
        transmitted_spec: Annotated[
            float,
            Field(description="Specular transmitted fraction."),
        ] = 0.0,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full modifier object_dict. Set false with garden_root."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance Trans modifier."""
        from garden.radiance.modifiers import create_radiance_trans_modifier as service

        return service(
            identifier=identifier,
            rgb_reflectance=rgb_reflectance,
            r_reflectance=r_reflectance,
            g_reflectance=g_reflectance,
            b_reflectance=b_reflectance,
            specularity=specularity,
            roughness=roughness,
            transmitted_diff=transmitted_diff,
            transmitted_spec=transmitted_spec,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="RAD_Create_View",
        description=(
            'Create a Radiance View / Honeybee Radiance View for rpict daylight rendering from '
            'position, direction or look-at point, up vector, view type, and view size. With '
            'garden_root, the tool writes a Garden .vf artifact and returns a compact '
            'radiance_view target. Set attach_to_model=true to add the View to the Honeybee model '
            'Radiance properties for later view or glare recipes.'
        ),
        tags={
            "radiance",
            "view",
            "author",
            "camera",
        },
        timeout=60,
    )
    def create_radiance_view(
        identifier: Annotated[
            str | None,
            Field(description="Stable View identifier. Defaults to view when omitted."),
        ] = None,
        position: Annotated[
            list[float] | dict[str, float] | None,
            Field(description="View position [x, y, z]. Default is [0, 0, 0]."),
        ] = None,
        direction: Annotated[
            list[float] | dict[str, float] | None,
            Field(description="View direction [x, y, z]. Default is [0, 0, 1]."),
        ] = None,
        target: Annotated[
            list[float] | dict[str, float] | None,
            Field(description="Optional look-at point [x, y, z]. Used to derive direction as target - position when direction is omitted."),
        ] = None,
        up_view_vector: Annotated[
            list[float] | dict[str, float] | None,
            Field(description="View up vector [x, y, z]. Default is [0, 1, 0]."),
        ] = None,
        view_type: Annotated[
            str,
            Field(description="Radiance view type character: v, h, l, c, a, or s. Radiance CLI tokens like vtv/vth/vtl/vtc/vta/vts are accepted."),
        ] = "v",
        h_size: Annotated[
            float,
            Field(description="Horizontal view size or field of view."),
        ] = 60,
        v_size: Annotated[
            float,
            Field(description="Vertical view size or field of view."),
        ] = 60,
        shift: Annotated[
            float | None,
            Field(description="Optional Radiance view shift (-vs)."),
        ] = None,
        lift: Annotated[
            float | None,
            Field(description="Optional Radiance view lift (-vl)."),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional display name."),
        ] = None,
        room_identifier: Annotated[
            str | None,
            Field(description="Optional Honeybee Room identifier associated with this view."),
        ] = None,
        group_identifier: Annotated[
            str | None,
            Field(description="Optional Radiance group identifier."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target with target_type=honeybee_model. Used when attach_to_model is true; omitted means Garden base model."),
        ] = None,
        attach_to_model: Annotated[
            bool,
            Field(description="When true, add the View to model.properties.radiance.views and save the model."),
        ] = False,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for Radiance view .vf artifacts."),
        ] = "artifacts/radiance/views",
        return_object_dict: Annotated[
            bool,
            Field(description='Return the full View object_dict. Keep false for compact target handoff.'),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Radiance View."""
        from garden.radiance.assets import create_radiance_view as service

        if identifier is None:
            identifier = "view"
        if model_target is not None and not attach_to_model:
            attach_to_model = True
        position = _view_vector(position, "position")
        direction = _view_vector(direction, "direction")
        target = _view_vector(target, "target")
        up_view_vector = _view_vector(up_view_vector, "up_view_vector")
        if direction is None:
            direction = _direction_from_target(position, target)
        view_type = _normalize_view_type(view_type)
        return service(
            identifier=identifier,
            position=position,
            direction=direction,
            up_view_vector=up_view_vector,
            view_type=view_type,
            h_size=h_size,
            v_size=v_size,
            shift=shift,
            lift=lift,
            display_name=display_name,
            room_identifier=room_identifier,
            group_identifier=group_identifier,
            garden_root=garden_root,
            model_target=model_target,
            attach_to_model=attach_to_model,
            output_subdir=output_subdir,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="RAD_Create_Sky_Matrix",
        description=(
            'Create a Garden sky_matrix target for Ladybug Radiance studies from a wea_file '
            'target, Garden weather_file target, Garden-relative EPW path, or ASHRAE clear-sky '
            'Location. This prepares gendaymtx/SkyMatrix inputs for annual or matrix recipes; '
            'compute=true also stores direct and diffuse sky patch values.'
        ),
        tags={
            "radiance",
            "sky",
            "weather",
            "sky-matrix",
            "wea",
        },
        timeout=120,
    )
    def create_sky_matrix(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        identifier: Annotated[
            str | None,
            Field(description=(
                "Stable identifier for the Radiance sky_matrix target. Defaults to 'sky_matrix' "
                'when omitted.'
            )),
        ] = None,
        wea_target: Annotated[
            dict[str, Any] | None,
            Field(description='Optional wea_file target from RAD_Create_WEA_From_Weather_File or RAD_Create_ASHRAE_Clear_Sky_WEA.'),
        ] = None,
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden weather_file target. Use instead of wea_target, epw_path, or location."),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative EPW path. Use instead of wea_target, weather_target, or location."),
        ] = None,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Ladybug Location dict for ASHRAE clear-sky SkyMatrix. Use instead of wea/weather/epw inputs."),
        ] = None,
        sky_clearness: Annotated[
            float,
            Field(description="ASHRAE sky clearness when location is used."),
        ] = 1,
        north: Annotated[
            float,
            Field(description="Counterclockwise north angle in degrees."),
        ] = 0,
        high_density: Annotated[
            bool,
            Field(description="Use Reinhart high-density sky patches instead of default Tregenza patches."),
        ] = False,
        ground_reflectance: Annotated[
            float,
            Field(description="Average ground reflectance for the sky matrix."),
        ] = 0.2,
        compute: Annotated[
            bool,
            Field(description="When true, compute and persist direct/diffuse sky patch values. Keep false for compact setup."),
        ] = False,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for sky matrix JSON artifacts."),
        ] = "artifacts/radiance/sky",
    ) -> dict[str, Any]:
        """Create a SkyMatrix target."""
        from garden.radiance.sky import create_sky_matrix as service

        if identifier is None:
            identifier = "sky_matrix"
        return service(
            garden_root=garden_root,
            identifier=identifier,
            wea_target=wea_target,
            weather_target=weather_target,
            epw_path=epw_path,
            location=location,
            sky_clearness=sky_clearness,
            north=north,
            high_density=high_density,
            ground_reflectance=ground_reflectance,
            compute=compute,
            output_subdir=output_subdir,
        )

    @mcp.tool(
        name="RAD_Create_WEA_From_Weather_File",
        description=(
            'Create a Radiance/DAYSIM WEA file artifact from a Garden-managed weather_file target '
            'or Garden-relative EPW path. Pass weather_target returned by EP_Import_Local_Weather '
            'or EP_Search_Weather_Files. Returns a compact wea_file target for '
            'RAD_Create_Sky_Matrix and later Radiance matrix workflows.'
        ),
        tags={
            "radiance",
            "sky",
            "weather",
            "wea",
            "epw",
        },
        timeout=60,
    )
    def create_wea_from_weather_file(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for the WEA artifact and target derived from a Garden EPW weather file."),
        ],
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description='Optional Garden weather_file target from EP_Import_Local_Weather or EP_Search_Weather_Files.'),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative EPW path. Use instead of weather_target."),
        ] = None,
        timestep: Annotated[
            int,
            Field(description="WEA timestep. Default 1 for hourly data."),
        ] = 1,
        hoys: Annotated[
            list[float] | None,
            Field(description="Optional hours of year to keep in the WEA."),
        ] = None,
        write_hours: Annotated[
            bool,
            Field(description="Whether to write hour values into the WEA file."),
        ] = False,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for WEA artifacts."),
        ] = "artifacts/radiance/wea",
        return_object_dict: Annotated[
            bool,
            Field(description='Return the full Wea object_dict. Keep false for compact target handoff.'),
        ] = False,
    ) -> dict[str, Any]:
        """Create a WEA file target from EPW weather data."""
        from garden.radiance.sky import create_wea_from_weather_file as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            weather_target=weather_target,
            epw_path=epw_path,
            timestep=timestep,
            hoys=hoys,
            write_hours=write_hours,
            output_subdir=output_subdir,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="RAD_Poll_Simulation",
        description=(
            "Get one Garden radiance_run record by target or run_id without "
            "returning large Radiance result files. Use after "
            "RAD_Start_Grid_Simulation, RAD_Start_View_Simulation, "
            "RAD_Start_Matrix_Simulation, RAD_Start_Imageless_Annual_Glare, "
            "or a daylight compliance start tool. "
            "When the user asks to wait, "
            "pass wait_seconds to throttle polling. Returns runtime_status "
            "through summary_view.status, poll_next, and report. Treat failed "
            "runtime_status as requiring report review."
        ),
        tags={
            "radiance",
            "simulate",
            "poll",
            "run-ledger",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_radiance_run(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description=(
                'Optional Garden radiance_run target returned by RAD_Start_Grid_Simulation, '
                'RAD_Start_View_Simulation, or RAD_Start_Matrix_Simulation.'
            )),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        wait_seconds: Annotated[
            int | float | None,
            Field(description="Optional maximum polling duration in seconds before returning."),
        ] = None,
        poll_interval: Annotated[
            int | float | None,
            Field(description="Optional polling interval in seconds when wait_seconds is supplied."),
        ] = None,
    ) -> dict[str, Any]:
        """Get one Radiance simulation run."""
        from garden.radiance.run import get_radiance_run as service

        interval = max(float(poll_interval or 1.0), 0.2)
        deadline = time.monotonic() + max(float(wait_seconds or 0), 0)
        result = service(garden_root=garden_root, run_target=run_target, run_id=run_id)
        while wait_seconds and result.get("status") in {"queued", "running"} and time.monotonic() < deadline:
            time.sleep(min(interval, max(deadline - time.monotonic(), 0.0)))
            result = service(garden_root=garden_root, run_target=run_target, run_id=run_id)
        if wait_seconds:
            result.setdefault("summary_view", {})["wait_seconds_requested"] = wait_seconds
        return result

    @mcp.tool(
        name="RAD_List_Artifact_Files",
        description=(
            'List Garden-managed Radiance artifact file records such as HDR images, falsecolor '
            'images, grid result files, and VisualizationSet exports. Use this to find artifact '
            'paths before export or preview. This reads Garden artifact metadata and compact '
            'paths. Returns matches, artifact_paths, summary_view, and report.'
        ),
        tags={
            "artifact",
            "radiance",
            "result",
            "search",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_artifact_files(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        artifact_type: Annotated[str | None, Field(description="Optional formal Radiance artifact target_type, such as radiance_sky_file, radiance_view, radiance_sensor_grid, radiance_hdr_image, or radiance_gif_image. Omit to list all Radiance artifact files.")] = None,
        query: Annotated[str | None, Field(description="Optional artifact name or Garden-relative path substring filter.")] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """List Radiance artifact records from the Garden manifest."""
        from garden.store import list_garden_artifacts as service

        normalized_artifact_type = _normalize_artifact_type(artifact_type)
        result = service(garden_root=garden_root, artifact_type=normalized_artifact_type)
        query_text = (query or "").strip().lower()
        matches = list(result["matches"])
        if query_text:
            matches = [
                artifact
                for artifact in matches
                if query_text
                in " ".join(
                    str(value)
                    for value in (
                        artifact.get("name"),
                        artifact.get("path"),
                        artifact.get("artifact_type"),
                    )
                    if value
                ).lower()
            ]
        if limit is not None:
            matches = matches[:limit]
        result["matches"] = matches
        result["files"] = matches
        result["summary_view"]["artifact_type"] = normalized_artifact_type
        result["summary_view"]["requested_artifact_type"] = artifact_type
        result["summary_view"]["query"] = query
        result["summary_view"]["count"] = len(matches)
        grouped: dict[str, list[dict[str, Any]]] = {
            "sky_files": [],
            "views": [],
            "sensor_grids": [],
            "hdr_images": [],
            "falsecolor": [],
            "gifs": [],
        }
        for artifact in matches:
            artifact_type_value = artifact.get("artifact_type")
            if artifact_type_value == "radiance_sky_file":
                grouped["sky_files"].append(artifact)
            elif artifact_type_value == "radiance_view":
                grouped["views"].append(artifact)
            elif artifact_type_value == "radiance_sensor_grid":
                grouped["sensor_grids"].append(artifact)
            elif artifact_type_value == "radiance_hdr_image":
                grouped["hdr_images"].append(artifact)
                producer = artifact.get("source", {}).get("producer") if isinstance(artifact.get("source"), dict) else None
                if producer == "RAD_HDR_To_Falsecolor":
                    grouped["falsecolor"].append(artifact)
            elif artifact_type_value == "radiance_gif_image":
                grouped["gifs"].append(artifact)
        result.update(grouped)
        if len(matches) == 1:
            result["artifact"] = matches[0]
        return result

    @mcp.tool(
        name="RAD_List_Artifacts",
        description=(
            'List Garden-managed Radiance artifact records and compact artifact_paths. Use this '
            'to find saved Radiance files without reading large image, matrix, or grid payloads. '
            'Artifact inventory only. Returns matches, artifact_paths, summary_view, and report.'
        ),
        tags={
            "artifact",
            "radiance",
            "result",
            "search",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_artifacts(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        artifact_type: Annotated[str | None, Field(description="Optional formal Radiance artifact target_type filter. Omit to list every registered Radiance artifact.")] = None,
        query: Annotated[str | None, Field(description="Optional artifact name or Garden-relative path substring filter.")] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """List Radiance artifacts."""
        from garden.store import list_garden_artifacts as service

        result = service(
            garden_root=garden_root,
            artifact_type=_normalize_artifact_type(artifact_type),
        )
        query_text = (query or "").strip().lower()
        matches = list(result["matches"])
        if query_text:
            matches = [
                artifact
                for artifact in matches
                if query_text
                in " ".join(
                    str(value)
                    for value in (
                        artifact.get("name"),
                        artifact.get("path"),
                        artifact.get("artifact_type"),
                    )
                    if value
                ).lower()
            ]
        if limit is not None:
            matches = matches[:limit]
        result["matches"] = matches
        result["artifact_paths"] = [item.get("path") for item in matches if item.get("path")]
        result["summary_view"]["count"] = len(matches)
        result["summary_view"]["query"] = query
        return result

    @mcp.tool(
        name="RAD_List_Grid_Results",
        description=(
            'List SensorGrid result folders from a completed Radiance run using SDK folder '
            'conventions: folders with grids_info.json and result files such as .res or .ill. Use '
            'before RAD_Grid_Result_To_Visualization_Set. This lists result folders and metadata. '
            'Returns matches/grids, summary_view, and report.'
        ),
        tags={
            "artifact",
            "radiance",
            "sensor-grid",
            "result",
            "visualize",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_grid_results(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional completed radiance_run target from a grid or matrix recipe. Poll the run before listing result folders."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier for a completed grid or matrix run when run_target is not supplied."),
        ] = None,
    ) -> dict[str, Any]:
        """List Radiance SensorGrid result folders."""
        from garden.radiance.visual import list_radiance_grid_results as service

        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)

    @mcp.tool(
        name="RAD_List_HDR_Images",
        description=(
            'List HDR image artifacts from completed Radiance view runs. Use this before '
            'falsecolor, GIF, or image search workflows. This returns image artifact metadata and '
            'paths only. Returns matches, artifact_paths, summary_view, and report.'
        ),
        tags={
            "artifact",
            "radiance",
            "image",
            "result",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_hdr_images(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='Optional completed view radiance_run target returned by RAD_Start_View_Simulation. Poll the run before listing HDR images.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier for a completed view run when run_target is not supplied."),
        ] = None,
    ) -> dict[str, Any]:
        """List .hdr images for a Radiance view run."""
        from garden.radiance.visual import list_radiance_hdr_images as service

        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)

    @mcp.tool(
        name="RAD_List_Run_Outputs",
        description=(
            'List indexed outputs for one Garden Radiance run, including grid results, HDR '
            'images, matrices, parameters, and reports when present. Use after '
            'RAD_Poll_Simulation reports a finished runtime_status. Output inventory only. '
            'Returns matches, summary_view, and report.'
        ),
        tags={
            "artifact",
            "outputs",
            "radiance",
            "result",
            "search",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_run_outputs(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description=(
                'Optional radiance_run target returned by RAD_Start_Grid_Simulation, '
                'RAD_Start_View_Simulation, or RAD_Start_Matrix_Simulation. Poll the run before '
                'listing outputs.'
            )),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is not supplied."),
        ] = None,
    ) -> dict[str, Any]:
        """List outputs for one Radiance simulation run."""
        from garden.radiance.run import list_radiance_run_outputs as service

        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)

    @mcp.tool(
        name="RAD_List_Runs",
        description=(
            'List Radiance simulation runs recorded in a Garden run ledger. Use this to find '
            'run_id, run_target, status, or run folder metadata before polling or reading '
            'results. This reads the run ledger only. Returns matches, summary_view, and report.'
        ),
        tags={
            "ledger",
            "radiance",
            "simulate",
            "poll",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_radiance_runs(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        status: Annotated[
            str | None,
            Field(description="Optional runtime_status filter for Garden run ledger records, such as running, completed, failed, or cancelled."),
        ] = None,
    ) -> dict[str, Any]:
        """List Radiance simulation runs."""
        from garden.radiance.run import list_radiance_runs as service

        return service(garden_root=garden_root, status=status)

    @mcp.tool(
        name="RAD_Grid_Result_To_Visualization_Set",
        description=(
            'Create a Ladybug Display VisualizationSet target from Radiance SensorGrid result '
            'folders using honeybee_display.model_to_vis_set(grid_data_path=...). This converts '
            'existing grid results into a VisualizationSet.'
        ),
        tags={
            "artifact",
            "radiance",
            "sensor-grid",
            "result",
            "visualize",
            "visualization-set",
        },
        timeout=60,
    )
    def radiance_grid_result_to_visualization_set(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional completed radiance_run target with SensorGrid result outputs. Poll the run before converting result data."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier for a completed grid or matrix run when run_target is not supplied."),
        ] = None,
        grid_data_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative folder containing grids_info.json for direct result-folder conversion."),
        ] = None,
        output_name: Annotated[
            str | None,
            Field(description="Optional run output name to use. Defaults to results when resolving from a run."),
        ] = None,
        result_subfolder: Annotated[
            str | None,
            Field(description="Optional subfolder inside the selected output, for example da or cumulative_radiation."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional model target override. Defaults to the model_target recorded on the run."),
        ] = None,
        color_by: Annotated[
            str | None,
            Field(description="Model context coloring: type, boundary_condition, or none. Use none for result-first views."),
        ] = "none",
        include_wireframe: Annotated[
            bool,
            Field(description="Include model wireframe context in the VisualizationSet."),
        ] = True,
        use_mesh: Annotated[
            bool,
            Field(description="Whether model context geometry should be DisplayMesh3D instead of DisplayFace3D."),
        ] = False,
        hide_color_by: Annotated[
            bool,
            Field(description="Hide colored model context by default when result data is primary."),
        ] = True,
        grid_data_display_mode: Annotated[
            str,
            Field(description="Result display mode: Surface, SurfaceWithEdges, Wireframe, or Points."),
        ] = "Surface",
        active_grid_data: Annotated[
            str | None,
            Field(description="Optional active grid data folder name when grid_data_path contains multiple datasets."),
        ] = None,
        name: Annotated[
            str,
            Field(description="VisualizationSet identifier and artifact name."),
        ] = "radiance_grid_result",
        return_visualization_set: Annotated[
            bool,
            Field(description="Return the full VisualizationSet dict. Set false to save a compact Garden visualization_set_target for export tools."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a VisualizationSet from Radiance grid results."""
        from garden.radiance.visual import radiance_grid_result_to_visualization_set as service

        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            grid_data_path=grid_data_path,
            output_name=output_name,
            result_subfolder=result_subfolder,
            model_target=model_target,
            color_by=color_by,
            include_wireframe=include_wireframe,
            use_mesh=use_mesh,
            hide_color_by=hide_color_by,
            grid_data_display_mode=grid_data_display_mode,
            active_grid_data=active_grid_data,
            name=name,
            return_visualization_set=return_visualization_set,
        )

    @mcp.tool(
        name="RAD_HDR_To_Falsecolor",
        description=(
            'Convert a Radiance HDR image artifact to a falsecolor image artifact for daylight or '
            'glare review. Pass image_target from RAD_List_HDR_Images or RAD_Search_Images. This '
            'converts an existing HDR artifact. Returns target, image_target, artifact_path, '
            'summary_view, and report.'
        ),
        tags={
            "artifact",
            "convert",
            "radiance",
            "image",
            "result",
        },
        timeout=60,
    )
    def radiance_hdr_to_falsecolor(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional completed point-in-time view radiance_run target. Poll the run before converting HDR artifacts."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        image_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative .hdr image path for direct artifact conversion."),
        ] = None,
        image_name: Annotated[
            str | None,
            Field(description="Optional .hdr file name inside the view run results folder."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional output artifact name without extension."),
        ] = None,
        scale: Annotated[
            str | float | None,
            Field(description="Optional falsecolor legend scale. Use a number or Radiance auto scale text."),
        ] = None,
        legend_label: Annotated[
            str | None,
            Field(description="Optional legend label, such as Lux or cd/m2."),
        ] = None,
        legend_multiplier: Annotated[
            float | None,
            Field(description="Optional falsecolor multiplier, equivalent to -m."),
        ] = None,
        contour_lines: Annotated[
            bool | None,
            Field(description="Optional contour line flag, equivalent to -cl."),
        ] = None,
        contour_bands: Annotated[
            bool | None,
            Field(description="Optional contour band flag, equivalent to -cb."),
        ] = None,
        palette: Annotated[
            str | None,
            Field(description="Optional falsecolor palette, equivalent to -pal."),
        ] = None,
        additional_options: Annotated[
            str | None,
            Field(description="Optional raw Falsecolor options string for SDK update_from_string."),
        ] = None,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for image artifacts."),
        ] = "artifacts/radiance/images",
    ) -> dict[str, Any]:
        """Create a falsecolor HDR artifact."""
        from garden.radiance.visual import radiance_hdr_to_falsecolor as service

        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            image_path=image_path,
            image_name=image_name,
            name=name,
            scale=scale,
            legend_label=legend_label,
            legend_multiplier=legend_multiplier,
            contour_lines=contour_lines,
            contour_bands=contour_bands,
            palette=palette,
            additional_options=additional_options,
            output_subdir=output_subdir,
        )

    @mcp.tool(
        name="RAD_HDR_To_GIF",
        description=(
            'Convert a Radiance HDR image artifact to a GIF image artifact for lightweight '
            'preview or sharing. Pass image_target from RAD_List_HDR_Images or RAD_Search_Images. '
            'This converts an existing HDR artifact. Returns target, image_target, artifact_path, '
            'summary_view, and report.'
        ),
        tags={
            "artifact",
            "convert",
            "radiance",
            "image",
            "result",
        },
        timeout=60,
    )
    def radiance_hdr_to_gif(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional completed point-in-time view radiance_run target. Poll the run before converting HDR artifacts."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        image_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative .hdr image path for direct artifact conversion."),
        ] = None,
        image_name: Annotated[
            str | None,
            Field(description="Optional .hdr file name inside the view run results folder."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional output artifact name without extension."),
        ] = None,
        exposure: Annotated[
            int | None,
            Field(description="Optional exposure compensation in f-stops, equivalent to -e."),
        ] = None,
        gamma: Annotated[
            float | None,
            Field(description="Optional gamma correction, equivalent to -g."),
        ] = None,
        black_and_white: Annotated[
            bool | None,
            Field(description="Optional black-and-white output flag, equivalent to -b."),
        ] = None,
        colors: Annotated[
            int | None,
            Field(description="Optional color count limit, equivalent to -c."),
        ] = None,
        sampling_factor: Annotated[
            int | None,
            Field(description="Optional sampling factor for large images, equivalent to -n."),
        ] = None,
        additional_options: Annotated[
            str | None,
            Field(description="Optional raw ra_gif options string for SDK update_from_string."),
        ] = None,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for image artifacts."),
        ] = "artifacts/radiance/images",
    ) -> dict[str, Any]:
        """Create a GIF artifact from HDR input."""
        from garden.radiance.visual import radiance_hdr_to_gif as service

        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            image_path=image_path,
            image_name=image_name,
            name=name,
            exposure=exposure,
            gamma=gamma,
            black_and_white=black_and_white,
            colors=colors,
            sampling_factor=sampling_factor,
            additional_options=additional_options,
            output_subdir=output_subdir,
        )

    @mcp.tool(
        name="RAD_Read_Daylight_Compliance",
        description=(
            "Read one completed native Radiance daylight compliance run for "
            "LEED Option 1/2, EN 17037, WELL, or BREEAM 4b. Returns aggregate "
            "credit or criteria summaries, a bounded paginated space/program "
            "summary, indexed output paths, and a reusable visualization_set "
            "target when the recipe VSF exists. Poll the run first with "
            "RAD_Poll_Simulation. This reads summary JSON/CSV and VSF paths; "
            "it never returns annual illuminance matrices."
        ),
        tags={
            "radiance",
            "compliance",
            "result",
            "summary",
            "visualize",
        },
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def read_daylight_compliance(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']."
                )
            ),
        ],
        run_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Completed radiance_run target returned by a native daylight "
                    "compliance start tool. The recipe type is checked before "
                    "reading results."
                )
            ),
        ],
        page: Annotated[
            int,
            Field(description="One-based space summary page number.", ge=1),
        ] = 1,
        page_size: Annotated[
            int,
            Field(
                description="Number of space rows to return; capped at 50 to keep handoffs compact.",
                ge=1,
                le=50,
            ),
        ] = 25,
    ) -> dict[str, Any]:
        """Read compact daylight compliance outputs."""
        from garden.radiance.compliance_results import (
            read_daylight_compliance as service,
        )

        return service(
            garden_root=garden_root,
            run_target=run_target,
            page=page,
            page_size=page_size,
        )

    @mcp.tool(
        name="RAD_Search_Images",
        description=(
            'Search Garden-managed Radiance image artifacts such as HDR, falsecolor, and GIF '
            'outputs. Use this before image conversion or preview tools. This searches registered '
            'image metadata and paths. Returns matches, image_targets, summary_view, and report.'
        ),
        tags={
            "artifact",
            "radiance",
            "image",
            "result",
            "search",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_radiance_images(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        run_id: Annotated[str | None, Field(description="Optional completed Radiance view run identifier for narrowing image results.")] = None,
        run_target: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional completed radiance_run target used to identify a view run."),
        ] = None,
        file_type: Annotated[
            str | None,
            Field(description="Optional formal image artifact type such as radiance_hdr_image or radiance_gif_image."),
        ] = None,
        query: Annotated[str | None, Field(description="Optional image artifact name or Garden-relative path substring filter.")] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """Search Radiance images."""
        from garden.radiance.visual import list_radiance_hdr_images

        from garden.store import list_garden_artifacts

        if run_id is None:
            run_id = _run_id_from_target(run_target)
        query_text = (query or "").strip().lower()
        matches: list[dict[str, Any]] = []

        normalized_artifact_type = _normalize_artifact_type(file_type)
        if normalized_artifact_type in {None, "radiance_hdr_image"}:
            try:
                hdrs = list_radiance_hdr_images(garden_root=garden_root, run_id=run_id)
            except Exception:
                hdrs = {"matches": []}
            for image in hdrs.get("matches", []):
                searchable = " ".join(str(value) for value in image.values() if value).lower()
                if query_text and query_text not in searchable:
                    continue
                matches.append(
                    {
                        "kind": "run_hdr",
                        "image_type": "hdr",
                        "path": image.get("path"),
                        "name": image.get("name"),
                        "run_id": image.get("run_id"),
                        "image": image,
                    }
                )

        listed = list_garden_artifacts(
            garden_root=garden_root,
            artifact_type=normalized_artifact_type,
        )
        for artifact in listed.get("matches", []):
            searchable = " ".join(
                str(value)
                for value in (
                    artifact.get("name"),
                    artifact.get("path"),
                    artifact.get("artifact_type"),
                )
                if value
            ).lower()
            if query_text and query_text not in searchable:
                continue
            matches.append(
                {
                    "kind": "artifact",
                    "image_type": artifact.get("artifact_type"),
                    "path": artifact.get("path"),
                    "name": artifact.get("name"),
                    "artifact": artifact,
                }
            )
        if limit is not None:
            matches = matches[:limit]
        hdr_images = [item for item in matches if item.get("image_type") == "hdr"]
        return {
            "matches": matches,
            "images": matches,
            "hdr_images": hdr_images,
            "summary_view": {
                "garden_target": listed.get("summary_view", {}).get("garden_target"),
                "count": len(matches),
                "query": query,
                "file_type": file_type,
                "recommended_hdr_tool": 'RAD_List_HDR_Images',
            },
        }

    @mcp.tool(
        name="RAD_Search_Library_Objects",
        description=(
            'Search Honeybee Radiance standards library identifiers for modifiers, materials, and '
            'modifier sets. Use returned identifiers in Radiance authoring tools or Honeybee '
            'Radiance properties. Searches built-in Radiance standards libraries. Returns '
            'matches, summary_view, and report.'
        ),
        tags={
            "search",
            "radiance",
            "modifier",
            "material",
            "author",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_radiance_library_objects(
        query: Annotated[
            str,
            Field(
                description="Required non-empty search text, such as 'generic wall' or 'modifier set'."
            ),
        ],
        object_family: Annotated[
            str | None,
            Field(
                description="Optional library family filter: modifier, modifier_set, material, or all."
            ),
        ] = None,
        limit: Annotated[
            int, Field(description="Maximum number of identifiers to return.")
        ] = 10,
    ) -> dict[str, Any]:
        """Search Honeybee Radiance standards library identifiers."""
        from garden.radiance.libraries import (
            search_radiance_library_objects as service,
        )

        return service(
            query=query,
            object_family=object_family,
            limit=limit,
        )

    @mcp.tool(
        name="RAD_Search_Parameters",
        description=(
            'Search Radiance parameter strings recorded on Garden Radiance runs and return '
            'compact radiance_parameters targets usable with RAD_Start_Grid_Simulation, '
            'RAD_Start_View_Simulation, or RAD_Start_Matrix_Simulation. This searches saved '
            'parameter records. If no stored parameters exist, call RAD_Create_Parameters or pass '
            'a Radiance parameter string.'
        ),
        tags={
            "parameters",
            "radiance",
            "result",
            "search",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_radiance_parameters(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        query: Annotated[str | None, Field(description="Optional run_id, identifier, Garden path, or Radiance parameter text substring filter.")] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """Search stored Radiance parameter inputs."""
        from garden.manifest import GardenManifest

        from garden.radiance.run import _read_index

        garden_root_path = Path(garden_root).expanduser().resolve()
        manifest = GardenManifest.read(garden_root_path)
        query_text = (query or "").strip().lower()
        matches: list[dict[str, Any]] = []
        for record in _read_index(garden_root_path):
            match = _relative_run_parameter_match(
                garden_root_path,
                manifest.garden_id,
                record,
            )
            if match is None:
                continue
            searchable = " ".join(
                str(value)
                for value in (
                    match.get("identifier"),
                    match.get("run_id"),
                    match.get("recipe"),
                    match.get("path"),
                    match.get("radiance_parameters"),
                )
                if value
            ).lower()
            if query_text and query_text not in searchable:
                continue
            matches.append(match)
            if limit is not None and len(matches) >= limit:
                break
        result: dict[str, Any] = {
            "matches": matches,
            "summary_view": {
                "garden_target": manifest.target(),
                "count": len(matches),
                "query": query,
                "recommended_tool": 'RAD_Create_Parameters',
            },
            "report": make_report(
                status="ok",
                message=f"Found {len(matches)} stored Radiance parameter input(s).",
            ),
        }
        if len(matches) == 1:
            result["target"] = matches[0]["target"]
        return result

    @mcp.tool(
        name="RAD_Search_Sensor_Grids",
        description=(
            'Search Garden Radiance SensorGrid .pts artifacts and return compact '
            'radiance_sensor_grid targets for grid recipe handoff. This searches saved '
            'sensor-grid artifacts.'
        ),
        tags={
            "artifact",
            "radiance",
            "sensor-grid",
            "author",
            "search",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_radiance_sensor_grids(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        query: Annotated[str | None, Field(description="Optional SensorGrid identifier or Garden-relative .pts path substring filter.")] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """Search Radiance SensorGrid artifacts."""
        from garden.store import list_garden_artifacts

        listed = list_garden_artifacts(
            garden_root=garden_root,
            artifact_type="radiance_sensor_grid",
        )
        garden_target = listed["summary_view"]["garden_target"]
        query_text = (query or "").strip().lower()
        matches: list[dict[str, Any]] = []
        for artifact in listed["matches"]:
            searchable = " ".join(
                str(value)
                for value in (
                    artifact.get("name"),
                    artifact.get("path"),
                    artifact.get("artifact_type"),
                )
                if value
            ).lower()
            if query_text and query_text not in searchable:
                continue
            target = _sensor_grid_target_from_artifact(artifact, garden_target)
            matches.append({"artifact": artifact, "target": target, **target})
            if limit is not None and len(matches) >= limit:
                break
        result: dict[str, Any] = {
            "matches": matches,
            "summary_view": {
                "garden_target": garden_target,
                "count": len(matches),
                "query": query,
                "artifact_type": "radiance_sensor_grid",
            },
        }
        if len(matches) == 1:
            result["target"] = matches[0]["target"]
        return result

    @mcp.tool(
        name="RAD_Search_Sky_Files",
        description=(
            'Search Garden Radiance sky_file artifacts and return compact radiance_sky_file '
            'targets for point-in-time Radiance runs. This searches saved .sky inputs.'
        ),
        tags={
            "artifact",
            "radiance",
            "sky",
            "weather",
            "search",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_radiance_sky_files(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        query: Annotated[str | None, Field(description="Optional sky identifier or Garden-relative .sky path substring filter.")] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """Search Radiance sky file artifacts."""
        from garden.store import list_garden_artifacts

        listed = list_garden_artifacts(
            garden_root=garden_root,
            artifact_type="radiance_sky_file",
        )
        garden_target = listed["summary_view"]["garden_target"]
        query_text = (query or "").strip().lower()
        matches: list[dict[str, Any]] = []
        for artifact in listed["matches"]:
            searchable = " ".join(
                str(value)
                for value in (
                    artifact.get("name"),
                    artifact.get("path"),
                    artifact.get("artifact_type"),
                )
                if value
            ).lower()
            if query_text and query_text not in searchable:
                continue
            target = _sky_file_target_from_artifact(artifact, garden_target)
            matches.append({"artifact": artifact, "target": target, **target})
            if limit is not None and len(matches) >= limit:
                break
        result: dict[str, Any] = {
            "matches": matches,
            "summary_view": {
                "garden_target": garden_target,
                "count": len(matches),
                "query": query,
                "artifact_type": "radiance_sky_file",
            },
        }
        if len(matches) == 1:
            result["target"] = matches[0]["target"]
        return result

    @mcp.tool(
        name="RAD_Search_Views",
        description=(
            'Search Garden Radiance View artifacts and return compact radiance_view targets for '
            'point-in-time view runs. This searches saved .vf inputs.'
        ),
        tags={
            "artifact",
            "radiance",
            "view",
            "author",
            "search",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_radiance_views(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        query: Annotated[str | None, Field(description="Optional View identifier or Garden-relative .vf path substring filter.")] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """Search Radiance View artifacts."""
        from garden.store import list_garden_artifacts

        listed = list_garden_artifacts(
            garden_root=garden_root,
            artifact_type="radiance_view",
        )
        garden_target = listed["summary_view"]["garden_target"]
        query_text = (query or "").strip().lower()
        matches: list[dict[str, Any]] = []
        for artifact in listed["matches"]:
            searchable = " ".join(
                str(value)
                for value in (
                    artifact.get("name"),
                    artifact.get("path"),
                    artifact.get("artifact_type"),
                )
                if value
            ).lower()
            if query_text and query_text not in searchable:
                continue
            target = _view_target_from_artifact(artifact, garden_target)
            matches.append({"artifact": artifact, "target": target, **target})
            if limit is not None and len(matches) >= limit:
                break
        result: dict[str, Any] = {
            "matches": matches,
            "summary_view": {
                "garden_target": garden_target,
                "count": len(matches),
                "query": query,
                "artifact_type": "radiance_view",
            },
        }
        if len(matches) == 1:
            result["target"] = matches[0]["target"]
        return result

    @mcp.tool(
        name="RAD_Search_Visualizations",
        description=(
            'Search Garden-managed Radiance image and visualization artifacts such as HDR '
            'falsecolor images and GIF previews. For raw run HDR outputs, use RAD_List_HDR_Images '
            'with a run target or run_id.'
        ),
        tags={
            "artifact",
            "radiance",
            "result",
            "search",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_radiance_visualizations(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        artifact_type: Annotated[str | None, Field(description="Optional formal Radiance artifact target_type: radiance_hdr_image, radiance_gif_image, radiance_view, or radiance_sensor_grid.")] = None,
        query: Annotated[str | None, Field(description="Optional visualization artifact name or Garden-relative path substring filter.")] = None,
        limit: Annotated[int | None, Field(description="Optional maximum number of matches.")] = None,
    ) -> dict[str, Any]:
        """Search Radiance visualization artifacts."""
        from garden.store import list_garden_artifacts as service

        normalized_artifact_type = _normalize_artifact_type(artifact_type)
        result = service(garden_root=garden_root, artifact_type=normalized_artifact_type)
        query_text = (query or "").strip().lower()
        matches = list(result["matches"])
        if query_text:
            matches = [
                artifact
                for artifact in matches
                if query_text
                in " ".join(
                    str(value)
                    for value in (
                        artifact.get("name"),
                        artifact.get("path"),
                        artifact.get("artifact_type"),
                    )
                    if value
                ).lower()
            ]
        if limit is not None:
            matches = matches[:limit]
        result["matches"] = matches
        result["summary_view"]["artifact_type"] = normalized_artifact_type
        result["summary_view"]["requested_artifact_type"] = artifact_type
        result["summary_view"]["query"] = query
        result["summary_view"]["count"] = len(matches)
        if len(matches) == 1:
            result["artifact"] = matches[0]
        return result

    @mcp.tool(
        name="RAD_Setup_Dynamic_Group",
        description=(
            'Apply the same Honeybee Radiance dynamic_group_identifier and state update to '
            'multiple Shade, Aperture, or Door targets in a Garden model. This creates model-side '
            'grouping by setting object properties. For replace_all/add, pass at least one state '
            'from RAD_Create_Shade_State or RAD_Create_Subface_State.'
        ),
        tags={
            "dynamic",
            "radiance",
            "model",
            "edit",
        },
        timeout=60,
    )
    def setup_radiance_dynamic_group(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Shade, Aperture, or Door typed targets to update; all targets receive the same dynamic_group_identifier."),
        ] = None,
        dynamic_group_identifier: Annotated[
            str | None,
            Field(description="Dynamic group identifier to set on every target."),
        ] = None,
        states: Annotated[
            list[dict[str, Any]] | None,
            Field(description="State dictionaries from RAD_Create_Shade_State or RAD_Create_Subface_State. Required for replace_all and add; omit for clear."),
        ] = None,
        operation: Annotated[
            str,
            Field(description="State operation on the target objects: replace_all, add, or clear."),
        ] = "replace_all",
    ) -> dict[str, Any]:
        """Apply Radiance dynamic state settings to multiple Honeybee objects."""
        from garden.radiance.dynamic import setup_radiance_dynamic_group as service

        if targets is None:
            raise ValueError("Provide targets.")
        if dynamic_group_identifier is None:
            raise ValueError("Provide dynamic_group_identifier.")
        return service(
            garden_root=garden_root,
            targets=targets,
            dynamic_group_identifier=dynamic_group_identifier,
            states=states,
            operation=operation,
        )

    @mcp.tool(
        name="RAD_Start_Annual_Daylight_EN17037",
        description=(
            "Start a background Radiance annual daylight EN 17037 recipe for "
            "a Honeybee model with attached, ungrouped SensorGrids. Use grids with meshes "
            "for area-weighted criteria; point-only grids use sensor counts. "
            "RAD_Create_Sensor_Grid_From_Object preserves the mesh. Provide a Garden "
            "weather_file target returned by EP_Import_Local_Weather or "
            "EP_Search_Weather_Files; its epw_path must reference an annual "
            "hourly EPW file. Optional grid_metrics and thresholds configure "
            "the accompanying annual metrics. Poll with RAD_Poll_Simulation, "
            "then pass run_target to RAD_Read_Daylight_Compliance. Returns "
            "run_target, radiance_run_target, and runtime_status through "
            "summary_view.status, poll_next, and report."
        ),
        tags={
            "start",
            "radiance",
            "simulate",
            "compliance",
            "en17037",
            "poll",
        },
        timeout=60,
    )
    def start_annual_daylight_en17037(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']; required when saving or reading "
                    "Garden targets."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Honeybee model target with "
                    "target_type=honeybee_model. Defaults to the Garden base "
                    "model and should already have SensorGrids attached."
                )
            ),
        ] = None,
        weather_file_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Garden weather_file target returned by "
                    "EP_Import_Local_Weather or EP_Search_Weather_Files. "
                    "It must include a Garden-relative epw_path for an annual "
                    "hourly EPW file. Required for EN 17037."
                )
            ),
        ] = None,
        grid_filter: Annotated[
            str,
            Field(
                description=(
                    "Honeybee Radiance grid-filter input. Use '*' for all "
                    "attached SensorGrids or pass a SensorGrid identifier or "
                    "pattern."
                )
            ),
        ] = "*",
        north: Annotated[
            float | None,
            Field(description="Optional north angle in degrees."),
        ] = None,
        min_sensor_count: Annotated[
            int,
            Field(
                description=(
                    "Minimum sensor count per redistributed batch; controls "
                    "how grids are split between workers."
                ),
                ge=1,
            ),
        ] = 1,
        radiance_parameters: Annotated[
            str | dict[str, Any] | None,
            Field(
                description=(
                    "Optional Radiance parameters string or dictionary returned "
                    "by RAD_Create_Parameters."
                )
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier. Omit to generate one."),
        ] = None,
        workers: Annotated[
            int | None,
            Field(description="Optional recipe worker count.", ge=1),
        ] = None,
        reload_old: Annotated[
            bool,
            Field(
                description=(
                    "Ask the recipe to reload existing results in the run "
                    "folder when available."
                )
            ),
        ] = False,
        silent: Annotated[
            bool,
            Field(description="Run the Radiance recipe silently."),
        ] = True,
        grid_metrics: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional native grid-metrics input for additional grid summaries."
            ),
        ] = None,
        thresholds: Annotated[
            str | None,
            Field(description=(
                "Optional DA/UDI threshold string, such as '-t 300 -lt 100 -ut 3000'. "
                "Changes the accompanying annual metrics, not EN 17037 criteria."
            )),
        ] = None,
    ) -> dict[str, Any]:
        """Start an annual daylight EN 17037 Radiance run."""
        from garden.radiance.run import (
            start_radiance_compliance_run as service,
        )

        return service(
            garden_root=garden_root,
            recipe_name="annual-daylight-en17037",
            model_target=model_target,
            weather_file_target=weather_file_target,
            wea_target=None,
            grid_filter=grid_filter,
            north=north,
            min_sensor_count=min_sensor_count,
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            recipe_options={"grid-metrics": grid_metrics, "thresholds": thresholds},
        )

    @mcp.tool(
        name="RAD_Start_BREEAM_Daylight_4B",
        description=(
            "Start a background Radiance BREEAM daylight 4b recipe for a "
            "Honeybee model with attached, ungrouped SensorGrids. Provide a WEA target "
            "from RAD_Create_WEA_From_Weather_File or "
            "RAD_Create_ASHRAE_Clear_Sky_WEA. BREEAM requires each selected "
            "SensorGrid to have a mesh and a valid room_identifier; generate "
            "the grid from room floor faces when needed. The recipe evaluates "
            "daylight by room program type, and the SDK treats unrecognized "
            "room program types as office occupied spaces. Poll with "
            "RAD_Poll_Simulation while summary_view.poll_next is present, "
            "then pass run_target to RAD_Read_Daylight_Compliance. Returns "
            "run_target, radiance_run_target, and runtime_status through "
            "summary_view.status, poll_next, and report."
        ),
        tags={
            "start",
            "radiance",
            "simulate",
            "compliance",
            "breeam",
            "poll",
        },
        timeout=60,
    )
    def start_breeam_daylight_4b(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']; required when saving or reading "
                    "Garden targets."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Honeybee model target with "
                    "target_type=honeybee_model. Defaults to the Garden base "
                    "model and should already have SensorGrids attached."
                )
            ),
        ] = None,
        wea_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Garden WEA target returned by "
                    "RAD_Create_WEA_From_Weather_File or "
                    "RAD_Create_ASHRAE_Clear_Sky_WEA. It must reference an "
                    "annual hourly weather file and is required for BREEAM "
                    "4b."
                )
            ),
        ] = None,
        grid_filter: Annotated[
            str,
            Field(
                description=(
                    "Honeybee Radiance grid-filter input. Use '*' for all "
                    "attached SensorGrids or pass a SensorGrid identifier or "
                    "pattern."
                )
            ),
        ] = "*",
        north: Annotated[
            float | None,
            Field(description="Optional north angle in degrees."),
        ] = None,
        min_sensor_count: Annotated[
            int,
            Field(
                description=(
                    "Minimum sensor count per redistributed batch; controls "
                    "how grids are split between workers."
                ),
                ge=1,
            ),
        ] = 1,
        radiance_parameters: Annotated[
            str | dict[str, Any] | None,
            Field(
                description=(
                    "Optional Radiance parameters string or dictionary returned "
                    "by RAD_Create_Parameters."
                )
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier. Omit to generate one."),
        ] = None,
        workers: Annotated[
            int | None,
            Field(description="Optional recipe worker count.", ge=1),
        ] = None,
        reload_old: Annotated[
            bool,
            Field(
                description=(
                    "Ask the recipe to reload existing results in the run "
                    "folder when available."
                )
            ),
        ] = False,
        silent: Annotated[
            bool,
            Field(description="Run the Radiance recipe silently."),
        ] = True,
    ) -> dict[str, Any]:
        """Start a BREEAM daylight 4b Radiance run."""
        from garden.radiance.run import (
            start_radiance_compliance_run as service,
        )

        return service(
            garden_root=garden_root,
            recipe_name="breeam-daylight-4b",
            model_target=model_target,
            wea_target=wea_target,
            weather_file_target=None,
            grid_filter=grid_filter,
            north=north,
            min_sensor_count=min_sensor_count,
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
        )

    @mcp.tool(
        name="RAD_Start_Imageless_Annual_Glare",
        description=(
            "Start the native imageless-annual-glare Radiance recipe in the "
            "background for a Honeybee model with attached SensorGrids and at "
            "least one attached View. Provide a WEA target or Garden-relative "
            "WEA path. The recipe produces annual DGP matrices and glare "
            "autonomy (GA) outputs; dynamic Radiance states on the model are "
            "handled by the native recipe. Poll with RAD_Poll_Simulation, then "
            "pass the completed run_target to RAD_Summarize_Glare_Metrics."
        ),
        tags={
            "start",
            "radiance",
            "simulate",
            "glare",
            "poll",
        },
        timeout=60,
    )
    def start_imageless_annual_glare(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']; required when saving or reading "
                    "Garden targets."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Honeybee model target with "
                    "target_type=honeybee_model. Defaults to the Garden base "
                    "model."
                )
            ),
        ] = None,
        wea_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Garden WEA target returned by "
                    "RAD_Create_WEA_From_Weather_File or "
                    "RAD_Create_ASHRAE_Clear_Sky_WEA."
                )
            ),
        ] = None,
        wea_path: Annotated[
            str | None,
            Field(description="Garden-relative .wea path. Prefer wea_target."),
        ] = None,
        view_filter: Annotated[
            str,
            Field(
                description=(
                    "Radiance View identifier or pattern. Use '*' for all "
                    "attached Views."
                )
            ),
        ] = "*",
        view_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional radiance_view target used to select one View."),
        ] = None,
        grid_filter: Annotated[
            str,
            Field(
                description=(
                    "SensorGrid identifier or pattern. Use '*' for all "
                    "attached SensorGrids."
                )
            ),
        ] = "*",
        north: Annotated[
            float | None,
            Field(description="Optional north angle in degrees."),
        ] = None,
        schedule: Annotated[
            str | None,
            Field(
                description=(
                    "Optional annual occupancy schedule file/path or schedule "
                    "text accepted by the recipe."
                )
            ),
        ] = None,
        dgp_threshold: Annotated[
            float,
            Field(
                description="DGP threshold used to calculate glare autonomy.",
                ge=0,
                le=1,
            ),
        ] = 0.4,
        luminance_factor: Annotated[
            float,
            Field(
                description=(
                    "Luminance threshold in cd/m2 used to detect glare sources."
                ),
                gt=0,
            ),
        ] = 2000.0,
        min_sensor_count: Annotated[
            int,
            Field(description="Minimum sensors per redistributed grid batch.", ge=1),
        ] = 1,
        radiance_parameters: Annotated[
            str | dict[str, Any] | None,
            Field(
                description=(
                    "Optional Radiance parameters string or RAD_Create_Parameters "
                    "result."
                )
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier."),
        ] = None,
        workers: Annotated[
            int | None,
            Field(description="Optional recipe worker count.", ge=1),
        ] = None,
        reload_old: Annotated[
            bool,
            Field(
                description=(
                    "Reload existing recipe results in the run folder when "
                    "available."
                )
            ),
        ] = False,
        silent: Annotated[
            bool,
            Field(description="Run the Radiance recipe silently."),
        ] = True,
    ) -> dict[str, Any]:
        """Start an imageless annual glare Radiance run."""
        from garden.radiance.run import (
            start_radiance_imageless_annual_glare as service,
        )

        if view_filter == "*":
            view_filter = _view_filter_from_target(view_target) or view_filter
        return service(
            garden_root=garden_root,
            model_target=model_target,
            wea_target=wea_target,
            wea_path=wea_path,
            view_filter=view_filter,
            grid_filter=grid_filter,
            north=north,
            schedule=schedule,
            dgp_threshold=dgp_threshold,
            luminance_factor=luminance_factor,
            min_sensor_count=min_sensor_count,
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
        )

    @mcp.tool(
        name="RAD_Start_LEED_Daylight_Option_One",
        description=(
            "Start a background Radiance LEED daylight Option 1 recipe for a "
            "Honeybee model with attached SensorGrids. Provide a WEA target "
            "from RAD_Create_WEA_From_Weather_File or "
            "RAD_Create_ASHRAE_Clear_Sky_WEA. The recipe applies aperture "
            "group blinds, evaluates annual sDA and ASE, and calculates LEED "
            "daylight credits using the 2% rule. diffuse_transmission is the "
            "unitless diffuse light transmission fraction of the blinds; "
            "specular_transmission is the unitless specular light transmission "
            "fraction. Both accept values from 0.0001 to 1. Poll with "
            "RAD_Poll_Simulation while summary_view.poll_next is present, "
            "then pass run_target to RAD_Read_Daylight_Compliance. Returns "
            "run_target, radiance_run_target, and runtime_status through "
            "summary_view.status, poll_next, and report."
        ),
        tags={
            "start",
            "radiance",
            "simulate",
            "compliance",
            "leed",
            "poll",
        },
        timeout=60,
    )
    def start_leed_daylight_option_one(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']; required when saving or reading "
                    "Garden targets."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Honeybee model target with "
                    "target_type=honeybee_model. Defaults to the Garden base "
                    "model and should already have SensorGrids attached."
                )
            ),
        ] = None,
        wea_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Garden WEA target returned by "
                    "RAD_Create_WEA_From_Weather_File or "
                    "RAD_Create_ASHRAE_Clear_Sky_WEA. It must reference an "
                    "annual hourly weather file and is required for LEED "
                    "Option 1."
                )
            ),
        ] = None,
        grid_filter: Annotated[
            str,
            Field(
                description=(
                    "Honeybee Radiance grid-filter input. Use '*' for all "
                    "attached SensorGrids or pass a SensorGrid identifier or "
                    "pattern."
                )
            ),
        ] = "*",
        north: Annotated[
            float | None,
            Field(description="Optional north angle in degrees."),
        ] = None,
        min_sensor_count: Annotated[
            int,
            Field(
                description=(
                    "Minimum sensor count per redistributed batch; controls "
                    "how grids are split between workers."
                ),
                ge=1,
            ),
        ] = 1,
        diffuse_transmission: Annotated[
            float,
            Field(
                description=(
                    "Diffuse light transmission fraction of the aperture group "
                    "blinds. The native recipe accepts 0.0001 to 1 and defaults "
                    "to 0.05 (5%)."
                ),
                ge=0.0001,
                le=1,
            ),
        ] = 0.05,
        specular_transmission: Annotated[
            float,
            Field(
                description=(
                    "Specular light transmission fraction of the aperture group "
                    "blinds. The native recipe accepts 0.0001 to 1 and defaults "
                    "to 0.0001 (0.01%)."
                ),
                ge=0.0001,
                le=1,
            ),
        ] = 0.0001,
        radiance_parameters: Annotated[
            str | dict[str, Any] | None,
            Field(
                description=(
                    "Optional Radiance parameters string or dictionary returned "
                    "by RAD_Create_Parameters."
                )
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier. Omit to generate one."),
        ] = None,
        workers: Annotated[
            int | None,
            Field(description="Optional recipe worker count.", ge=1),
        ] = None,
        reload_old: Annotated[
            bool,
            Field(
                description=(
                    "Ask the recipe to reload existing results in the run "
                    "folder when available."
                )
            ),
        ] = False,
        silent: Annotated[
            bool,
            Field(description="Run the Radiance recipe silently."),
        ] = True,
    ) -> dict[str, Any]:
        """Start a LEED daylight Option 1 Radiance run."""
        from garden.radiance.run import (
            start_radiance_compliance_run as service,
        )

        return service(
            garden_root=garden_root,
            recipe_name="leed-daylight-option-one",
            model_target=model_target,
            wea_target=wea_target,
            weather_file_target=None,
            grid_filter=grid_filter,
            north=north,
            min_sensor_count=min_sensor_count,
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            recipe_options={
                "diffuse-transmission": diffuse_transmission,
                "specular-transmission": specular_transmission,
            },
        )

    @mcp.tool(
        name="RAD_Start_LEED_Daylight_Option_Two",
        description=(
            "Start a background Radiance LEED daylight Option 2 recipe for a "
            "Honeybee model with attached, ungrouped SensorGrids (empty "
            "group_identifier). Provide a WEA target "
            "from RAD_Create_WEA_From_Weather_File or "
            "RAD_Create_ASHRAE_Clear_Sky_WEA. The recipe runs the 9AM and "
            "3PM point-in-time illuminance checks and evaluates LEED credits. "
            "Use glare_control_devices='glare-control' when the model has "
            "view-preserving automatic glare-control devices; use "
            "'no-glare-control' otherwise. Poll with RAD_Poll_Simulation "
            "then pass run_target to RAD_Read_Daylight_Compliance. Returns run_target, "
            "radiance_run_target, and runtime_status through summary_view.status, "
            "poll_next, and report."
        ),
        tags={
            "start",
            "radiance",
            "simulate",
            "compliance",
            "leed",
            "poll",
        },
        timeout=60,
    )
    def start_leed_daylight_option_two(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']; required when saving or reading "
                    "Garden targets."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Honeybee model target with "
                    "target_type=honeybee_model. Defaults to the Garden base "
                    "model and should already have SensorGrids attached."
                )
            ),
        ] = None,
        wea_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Garden WEA target returned by "
                    "RAD_Create_WEA_From_Weather_File or "
                    "RAD_Create_ASHRAE_Clear_Sky_WEA. Required for LEED Option "
                    "2."
                )
            ),
        ] = None,
        grid_filter: Annotated[
            str,
            Field(
                description=(
                    "Honeybee Radiance grid-filter input. Use '*' for all "
                    "attached SensorGrids or pass a SensorGrid identifier or "
                    "pattern."
                )
            ),
        ] = "*",
        north: Annotated[
            float | None,
            Field(description="Optional north angle in degrees."),
        ] = None,
        min_sensor_count: Annotated[
            int,
            Field(
                description=(
                    "Minimum sensor count per redistributed batch; controls "
                    "how grids are split between workers."
                ),
                ge=1,
            ),
        ] = 1,
        glare_control_devices: Annotated[
            Literal["glare-control", "no-glare-control"],
            Field(
                description=(
                    "LEED recipe glare-control-devices enum. Use "
                    "'glare-control' when the model has view-preserving "
                    "automatic glare-control devices with manual override; "
                    "use 'no-glare-control' otherwise."
                )
            ),
        ] = "glare-control",
        radiance_parameters: Annotated[
            str | dict[str, Any] | None,
            Field(
                description=(
                    "Optional Radiance parameters string or dictionary returned "
                    "by RAD_Create_Parameters."
                )
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier. Omit to generate one."),
        ] = None,
        workers: Annotated[
            int | None,
            Field(description="Optional recipe worker count.", ge=1),
        ] = None,
        reload_old: Annotated[
            bool,
            Field(
                description=(
                    "Ask the recipe to reload existing results in the run "
                    "folder when available."
                )
            ),
        ] = False,
        silent: Annotated[
            bool,
            Field(description="Run the Radiance recipe silently."),
        ] = True,
    ) -> dict[str, Any]:
        """Start a LEED daylight Option 2 Radiance run."""
        from garden.radiance.run import (
            start_radiance_compliance_run as service,
        )

        return service(
            garden_root=garden_root,
            recipe_name="leed-daylight-option-two",
            model_target=model_target,
            wea_target=wea_target,
            weather_file_target=None,
            grid_filter=grid_filter,
            north=north,
            min_sensor_count=min_sensor_count,
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            recipe_options={"glare-control-devices": glare_control_devices},
        )

    @mcp.tool(
        name="RAD_Start_Grid_Simulation",
        description=(
            "Start a background Radiance daylight grid recipe for a Honeybee "
            "model with attached SensorGrids. Use for point-in-time-grid, "
            "daylight-factor, Sky View, and rtrace calculations. Provide a sky_file "
            "target for point-in-time runs and poll with "
            "RAD_Poll_Simulation before reading artifacts. Returns "
            "run_target, radiance_run_target, runtime_status through "
            "summary_view.status, poll_next, and report. Treat failed "
            "runtime_status as requiring report review."
        ),
        tags={
            "start",
            "radiance",
            "simulate",
            "poll",
        },
        timeout=60,
    )
    def start_radiance_grid_run(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target with target_type=honeybee_model. Defaults to the Garden base model and should already have SensorGrids attached."),
        ] = None,
        calculation_type: Annotated[
            str,
            Field(description="Grid calculation type: point_in_time, daylight_factor, or sky_view."),
        ] = "point_in_time",
        radiance_sky_file: Annotated[
            dict[str, Any] | None,
            Field(description='Radiance sky file target from RAD_Create_CIE_Standard_Sky, RAD_Create_Climate_Based_Sky, RAD_Create_Sky, or RAD_Create_Sky_File. Required for point_in_time runs.'),
        ] = None,
        grid_filter: Annotated[
            str,
            Field(description="Honeybee Radiance grid-filter input. Use '*' for all attached SensorGrids or pass one SensorGrid identifier."),
        ] = "*",
        sensor_grid_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional SensorGrid target. When supplied and grid_filter is '*', its identifier is used as grid-filter."),
        ] = None,
        metric: Annotated[
            str,
            Field(description="Point-in-time metric, usually illuminance, irradiance, luminance, or radiance depending on recipe."),
        ] = "illuminance",
        min_sensor_count: Annotated[
            int | None,
            Field(description='Minimum sensor count per split grid (default 1).'),
        ] = 1,
        grid_metrics: Annotated[
            dict[str, Any] | None,
            Field(description="Optional daylight-factor grid-metrics input when needed by the recipe."),
        ] = None,
        cloudy_sky: Annotated[
            str,
            Field(description="Sky View sky condition: uniform or cloudy."),
        ] = "uniform",
        radiance_parameters: Annotated[
            str | dict[str, Any] | None,
            Field(description="Optional Radiance parameters string or dictionary returned by RAD_Create_Parameters."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier. Omit to generate one."),
        ] = None,
        workers: Annotated[int | None, Field(description="Optional recipe worker count.")] = None,
        reload_old: Annotated[
            bool,
            Field(description="Ask the recipe to reload existing results in the run folder when available."),
        ] = False,
        silent: Annotated[bool, Field(description="Run the Radiance recipe silently.")] = True,
    ) -> dict[str, Any]:
        """Start a Radiance grid run."""
        from garden.radiance.run import start_radiance_grid_run as service

        if _requires_radiance_sky_file(calculation_type) and radiance_sky_file is None:
            raise ValueError("Provide radiance_sky_file for point_in_time Radiance grid runs.")
        if grid_filter == "*" and isinstance(sensor_grid_target, dict):
            if sensor_grid_target.get("target_type") != "radiance_sensor_grid":
                raise ValueError("sensor_grid_target must be a radiance_sensor_grid target.")
            identifier = sensor_grid_target.get("identifier")
            if identifier:
                grid_filter = str(identifier)
        return service(
            garden_root=garden_root,
            model_target=model_target,
            calculation_type=calculation_type,
            sky_file_target=radiance_sky_file,
            sky=None,
            grid_filter=grid_filter,
            metric=metric,
            min_sensor_count=min_sensor_count,
            grid_metrics=grid_metrics,
            cloudy_sky=cloudy_sky,
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
        )

    @mcp.tool(
        name="RAD_Start_Matrix_Simulation",
        description=(
            "Start a background Radiance annual or matrix daylight recipe for "
            "a Honeybee model with attached SensorGrids and a WEA target. Use "
            "for annual-daylight (with optional enhanced two-phase mode), "
            "annual-irradiance, cumulative-radiation, direct-sun-hours, and "
            "rfluxmtx calculations. Poll with RAD_Poll_Simulation before "
            "reading artifacts. Returns run_target, radiance_run_target, "
            "runtime_status through summary_view.status, poll_next, and "
            "report. Treat failed runtime_status as requiring report review."
        ),
        tags={
            "start",
            "radiance",
            "simulate",
            "poll",
        },
        timeout=60,
    )
    def start_radiance_matrix_run(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target with target_type=honeybee_model. Defaults to the Garden base model and should already have SensorGrids attached."),
        ] = None,
        calculation_type: Annotated[
            str,
            Field(description="Matrix calculation type: annual_daylight, annual_irradiance, cumulative_radiation, or direct_sun_hours."),
        ] = "annual_daylight",
        enhanced: Annotated[
            bool,
            Field(description="Use the annual-daylight-enhanced two-phase recipe when calculation_type is annual_daylight. Defaults to true."),
        ] = True,
        wea_target: Annotated[
            dict[str, Any] | None,
            Field(description='Garden WEA target returned by RAD_Create_WEA_From_Weather_File or RAD_Create_ASHRAE_Clear_Sky_WEA.'),
        ] = None,
        wea_path: Annotated[
            str | None,
            Field(description="Garden-relative .wea path for controlled workflows. Prefer wea_target."),
        ] = None,
        grid_filter: Annotated[
            str,
            Field(description="Honeybee Radiance grid-filter input. Use '*' for all attached SensorGrids or pass one SensorGrid identifier."),
        ] = "*",
        north: Annotated[float | None, Field(description="Optional north angle in degrees.")] = None,
        timestep: Annotated[int | None, Field(description="Optional recipe timestep.")] = None,
        schedule: Annotated[
            str | None,
            Field(description="Optional annual-daylight schedule file/path or schedule text accepted by the recipe."),
        ] = None,
        thresholds: Annotated[
            str | None,
            Field(description="Optional annual-daylight thresholds string accepted by the recipe."),
        ] = None,
        output_type: Annotated[
            str | None,
            Field(description="Optional annual-irradiance output-type, for example solar or visible."),
        ] = None,
        sky_density: Annotated[
            int | None,
            Field(description="Optional cumulative-radiation sky-density."),
        ] = None,
        min_sensor_count: Annotated[
            int | None,
            Field(description='Minimum sensor count per split grid (default 1).'),
        ] = 1,
        grid_metrics: Annotated[
            dict[str, Any] | None,
            Field(description="Optional annual-daylight grid-metrics input when needed by the recipe."),
        ] = None,
        radiance_parameters: Annotated[
            str | dict[str, Any] | None,
            Field(description='Optional Radiance parameters string or dictionary returned by RAD_Create_Parameters.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier. Omit to generate one."),
        ] = None,
        workers: Annotated[int | None, Field(description="Optional recipe worker count.")] = None,
        reload_old: Annotated[
            bool,
            Field(description="Ask the recipe to reload existing results in the run folder when available."),
        ] = False,
        silent: Annotated[bool, Field(description="Run the Radiance recipe silently.")] = True,
    ) -> dict[str, Any]:
        """Start a Radiance matrix run."""
        from garden.radiance.run import start_radiance_matrix_run as service

        return service(
            garden_root=garden_root,
            model_target=model_target,
            calculation_type=calculation_type,
            enhanced=enhanced,
            wea_target=wea_target,
            wea_path=wea_path,
            grid_filter=grid_filter,
            north=north,
            timestep=timestep,
            schedule=schedule,
            thresholds=thresholds,
            output_type=output_type,
            sky_density=sky_density,
            min_sensor_count=min_sensor_count,
            grid_metrics=grid_metrics,
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
        )

    @mcp.tool(
        name="RAD_Start_View_Simulation",
        description=(
            "Start a background Radiance daylight view recipe for a Honeybee "
            "model with attached Views. Use for point-in-time-view and rpict "
            "image calculations with view_filter or view_target from "
            "RAD_Create_View. Poll with RAD_Poll_Simulation before "
            "reading HDR or image artifacts. Returns run_target, "
            "radiance_run_target, runtime_status through summary_view.status, "
            "poll_next, and report. Treat failed runtime_status as requiring "
            "report review."
        ),
        tags={
            "start",
            "radiance",
            "simulate",
            "poll",
        },
        timeout=60,
    )
    def start_radiance_view_run(
        garden_root: Annotated[str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target with target_type=honeybee_model. Defaults to the Garden base model and should already have Views attached."),
        ] = None,
        calculation_type: Annotated[
            str,
            Field(description="View calculation type. Currently point_in_time."),
        ] = "point_in_time",
        radiance_sky_file: Annotated[
            dict[str, Any] | None,
            Field(description='Radiance sky file target from RAD_Create_CIE_Standard_Sky, RAD_Create_Climate_Based_Sky, RAD_Create_Sky, or RAD_Create_Sky_File. Required for point_in_time view runs.'),
        ] = None,
        view_filter: Annotated[
            str,
            Field(description="Honeybee Radiance view-filter input. Use '*' for all attached Views or one View identifier."),
        ] = "*",
        view_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional radiance_view target. When supplied and view_filter is '*', its identifier is used as the view-filter."),
        ] = None,
        metric: Annotated[
            str,
            Field(description="Point-in-time image metric, usually luminance or radiance."),
        ] = "luminance",
        resolution: Annotated[
            int | None,
            Field(description="Optional image resolution passed to the recipe."),
        ] = None,
        skip_overture: Annotated[
            bool | None,
            Field(description="Optional skip-overture recipe flag."),
        ] = None,
        radiance_parameters: Annotated[
            str | dict[str, Any] | None,
            Field(description="Optional Radiance parameters string or dictionary returned by RAD_Create_Parameters."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier. Omit to generate one."),
        ] = None,
        workers: Annotated[int | None, Field(description="Optional recipe worker count.")] = None,
        reload_old: Annotated[
            bool,
            Field(description="Ask the recipe to reload existing results in the run folder when available."),
        ] = False,
        silent: Annotated[bool, Field(description="Run the Radiance recipe silently.")] = True,
    ) -> dict[str, Any]:
        """Start a Radiance view run."""
        from garden.radiance.run import start_radiance_view_run as service

        if radiance_sky_file is None:
            raise ValueError("Provide radiance_sky_file for Radiance view runs.")
        if view_filter == "*":
            view_filter = _view_filter_from_target(view_target) or view_filter
        return service(
            garden_root=garden_root,
            model_target=model_target,
            calculation_type=calculation_type,
            sky_file_target=radiance_sky_file,
            sky=None,
            view_filter=view_filter,
            metric=metric,
            resolution=resolution,
            skip_overture=skip_overture,
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
        )

    @mcp.tool(
        name="RAD_Start_WELL_Daylight",
        description=(
            "Start a background Radiance WELL daylight recipe for a Honeybee "
            "model with attached SensorGrids. Provide a Garden weather_file "
            "target returned by EP_Import_Local_Weather or "
            "EP_Search_Weather_Files; its epw_path must reference an annual "
            "hourly EPW file. The recipe evaluates WELL L01 and L06 daylight "
            "criteria, creates dynamic shading schedules, and reports the "
            "WELL version used by the result. diffuse_transmission is the "
            "unitless diffuse light transmission fraction of the aperture group "
            "blinds; specular_transmission is the unitless specular light "
            "transmission fraction. Both accept values from 0.0001 to 1. Poll "
            "with RAD_Poll_Simulation while summary_view.poll_next is present, "
            "then pass run_target to RAD_Read_Daylight_Compliance. Returns "
            "run_target, radiance_run_target, and runtime_status through "
            "summary_view.status, poll_next, and report, with L01, L06, and "
            "WELL version result paths among the compliance outputs."
        ),
        tags={
            "start",
            "radiance",
            "simulate",
            "compliance",
            "well",
            "poll",
        },
        timeout=60,
    )
    def start_well_daylight(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']; required when saving or reading "
                    "Garden targets."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Honeybee model target with "
                    "target_type=honeybee_model. Defaults to the Garden base "
                    "model and should already have SensorGrids attached."
                )
            ),
        ] = None,
        weather_file_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Garden weather_file target returned by "
                    "EP_Import_Local_Weather or EP_Search_Weather_Files. "
                    "It must include a Garden-relative epw_path for an annual "
                    "hourly EPW file. Required for WELL daylight."
                )
            ),
        ] = None,
        grid_filter: Annotated[
            str,
            Field(
                description=(
                    "Honeybee Radiance grid-filter input. Use '*' for all "
                    "attached SensorGrids or pass a SensorGrid identifier or "
                    "pattern."
                )
            ),
        ] = "*",
        north: Annotated[
            float | None,
            Field(description="Optional north angle in degrees."),
        ] = None,
        min_sensor_count: Annotated[
            int,
            Field(
                description=(
                    "Minimum sensor count per redistributed batch; controls "
                    "how grids are split between workers."
                ),
                ge=1,
            ),
        ] = 1,
        diffuse_transmission: Annotated[
            float,
            Field(
                description=(
                    "Diffuse light transmission fraction of the aperture group "
                    "blinds. The native recipe accepts 0.0001 to 1 and defaults "
                    "to 0.05 (5%)."
                ),
                ge=0.0001,
                le=1,
            ),
        ] = 0.05,
        specular_transmission: Annotated[
            float,
            Field(
                description=(
                    "Specular light transmission fraction of the aperture group "
                    "blinds. The native recipe accepts 0.0001 to 1 and defaults "
                    "to 0.0001 (0.01%)."
                ),
                ge=0.0001,
                le=1,
            ),
        ] = 0.0001,
        radiance_parameters: Annotated[
            str | dict[str, Any] | None,
            Field(
                description=(
                    "Optional Radiance parameters string or dictionary returned "
                    "by RAD_Create_Parameters."
                )
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier. Omit to generate one."),
        ] = None,
        workers: Annotated[
            int | None,
            Field(description="Optional recipe worker count.", ge=1),
        ] = None,
        reload_old: Annotated[
            bool,
            Field(
                description=(
                    "Ask the recipe to reload existing results in the run "
                    "folder when available."
                )
            ),
        ] = False,
        silent: Annotated[
            bool,
            Field(description="Run the Radiance recipe silently."),
        ] = True,
    ) -> dict[str, Any]:
        """Start a WELL daylight Radiance run."""
        from garden.radiance.run import (
            start_radiance_compliance_run as service,
        )

        return service(
            garden_root=garden_root,
            recipe_name="well-daylight",
            model_target=model_target,
            wea_target=None,
            weather_file_target=weather_file_target,
            grid_filter=grid_filter,
            north=north,
            min_sensor_count=min_sensor_count,
            radiance_parameters=radiance_parameters,
            run_id=run_id,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            recipe_options={
                "diffuse-transmission": diffuse_transmission,
                "specular-transmission": specular_transmission,
            },
        )

    @mcp.tool(
        name="RAD_Summarize_Annual_Daylight_Metrics",
        description=(
            'Summarize completed Honeybee Radiance annual daylight metrics such as sDA, ASE, DA, '
            'CDA, UDI, daylight autonomy, annual sunlight exposure, and too-much-sun risk into a '
            'compact Garden-backed report. Use after a completed annual daylight run. This reads '
            'Radiance daylight metric artifacts. Pass/fail interpretation requires project or '
            'rating-system thresholds.'
        ),
        tags={
            "metrics",
            "radiance",
            "result",
        },
        timeout=60,
    )
    def summarize_annual_daylight_metrics(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional completed annual-daylight radiance_run target. Poll the run before summarizing metrics."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(
                description="Optional completed annual daylight run identifier when run_target is omitted."
            ),
        ] = None,
        grid_identifier: Annotated[
            str | None,
            Field(description="Optional grid identifier for report provenance and future filtering."),
        ] = None,
        metrics: Annotated[
            list[str] | None,
            Field(
                description="Optional metrics to summarize, for example ['sda', 'ase', 'da', 'udi']."
            ),
        ] = None,
        save_report: Annotated[
            bool,
            Field(description="Save a compact JSON report artifact in the Garden and return a target."),
        ] = True,
        include_values: Annotated[
            bool,
            Field(description="Return raw metric values. Keep false for compact report handoff."),
        ] = False,
    ) -> dict[str, Any]:
        """Summarize annual daylight metrics."""
        from garden.radiance.metrics import summarize_annual_daylight_metrics as service

        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            grid_identifier=grid_identifier,
            metrics=metrics,
            save_report=save_report,
            include_values=include_values,
        )

    @mcp.tool(
        name="RAD_Summarize_Glare_Metrics",
        description=(
            'Summarize annual Radiance glare metrics from a completed imageless-annual-glare or '
            'glare-capable run into compact DGP, GA, and visual-discomfort statistics. Use after '
            'RAD_Poll_Simulation and output listing confirm results exist. This reads glare '
            'metric artifacts. Returns target, summary_view, metrics, and report.'
        ),
        tags={
            "radiance",
            "glare",
            "metrics",
            "result",
        },
        timeout=60,
    )
    def summarize_radiance_glare_metrics(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional completed radiance_run target with DGP/glare result outputs. Poll the run before summarizing metrics."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional completed glare-capable Radiance run identifier."),
        ] = None,
        view_identifier: Annotated[
            str | None,
            Field(description="Optional view identifier for report provenance."),
        ] = None,
        dgp_threshold: Annotated[
            float,
            Field(
                description="DGP threshold for exceedance summary. Pass/fail still depends on user/project criteria."
            ),
        ] = 0.4,
        save_report: Annotated[
            bool,
            Field(description="Save a compact JSON glare report artifact in the Garden and return a target."),
        ] = True,
        include_values: Annotated[
            bool,
            Field(description="Return raw DGP values. Keep false for compact report handoff."),
        ] = False,
    ) -> dict[str, Any]:
        """Summarize DGP/glare metrics."""
        from garden.radiance.metrics import summarize_radiance_glare_metrics as service

        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            view_identifier=view_identifier,
            dgp_threshold=dgp_threshold,
            save_report=save_report,
            include_values=include_values,
        )
