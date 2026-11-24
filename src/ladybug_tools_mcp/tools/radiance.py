"""radiance MCP tools."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.contracts import (
    ArtifactResultModel,
    ArtifactTargetRef,
    BuildingModelTargetRef,
    BuildingObjectTargetRef,
    LibraryObjectTargetRef,
    MutationResultModel,
    QueryResultModel,
    RunResultModel,
    RunTargetRef,
    SkyTargetRef,
    WeatherTargetRef,
    dump_input,
    dump_target,
    dump_targets,
    validate_output,
)


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


def register(mcp: FastMCP) -> None:
    """Register radiance tools."""

    @mcp.tool(
        name="RAD_Create_Sky_Asset",
        description=(
            "Create a Radiance sky or weather asset in a Garden project. Supports ten "
            "asset_type modes: 'cie_sky' (gensky point-in-time .sky target), "
            "'climate_based_sky' (gendaylit point-in-time .sky target), "
            "'certain_irradiance' (fixed irradiance/illuminance sky incl. 0 lux dark sky), "
            "'from_epw_hoy' (climate-based sky from EPW at HOY or date/time), "
            "'skydome' (SkyDome/UniformSky for rfluxmtx), 'leed_illuminance' (LEED v4.1 Opt 2 "
            "9AM/3PM clear equinox skies), 'abnt_nbr_15575' (4 ABNT NBR 15575 skies), "
            "'wea_from_epw' (WEA file), 'wea_clear_sky' (ASHRAE clear-sky WEA), and "
            "'sky_matrix' (SkyMatrix from wea_target, EPW, stat_path, or location with optional "
            "hoys filter and benefit_matrix). Returns target, summary_view, persistence_receipt, and report."
        ),
        tags={
            "radiance",
            "sky",
            "weather",
            "wea",
            "sky-matrix",
            "author",
        },
        timeout=120,
    )
    def create_radiance_sky_asset(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually GD_Create['garden_root']; "
                    "required when saving or reading Garden targets."
                )
            ),
        ],
        asset_type: Annotated[
            Literal[
                "cie_sky",
                "climate_based_sky",
                "certain_irradiance",
                "from_epw_hoy",
                "skydome",
                "leed_illuminance",
                "abnt_nbr_15575",
                "wea_from_epw",
                "wea_clear_sky",
                "sky_matrix",
            ],
            Field(
                description=(
                    "Sky asset kind: cie_sky, climate_based_sky, certain_irradiance, "
                    "from_epw_hoy, skydome, leed_illuminance, abnt_nbr_15575, "
                    "wea_from_epw, wea_clear_sky, or sky_matrix."
                )
            ),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Optional stable identifier for the persisted sky/WEA/matrix artifact."),
        ] = None,
        month: Annotated[
            int | None,
            Field(description="Month number (1-12) for cie_sky, climate_based_sky, or from_epw_hoy.", ge=1, le=12),
        ] = None,
        day: Annotated[
            int | None,
            Field(description="Day of month for cie_sky, climate_based_sky, or from_epw_hoy.", ge=1, le=31),
        ] = None,
        time: Annotated[
            str | float | None,
            Field(description="Local time for cie_sky, climate_based_sky, or from_epw_hoy, e.g. '12:00' or 12.0."),
        ] = None,
        time_zone: Annotated[
            str | int | float | None,
            Field(
                description=(
                    "Optional Radiance time zone token (such as EST/MST) or numeric UTC offset "
                    "(required when constructing a Location from coordinates)."
                )
            ),
        ] = None,
        solar_time: Annotated[
            bool,
            Field(description="Use local solar time instead of local standard time for cie_sky/climate_based_sky."),
        ] = False,
        solar_altitude: Annotated[
            float | None,
            Field(description="Optional sun altitude angle in degrees (provide with solar_azimuth instead of month/day/time).", ge=-90, le=90),
        ] = None,
        solar_azimuth: Annotated[
            float | None,
            Field(description="Optional sun azimuth angle in degrees (provide with solar_altitude instead of month/day/time).", ge=-360, le=360),
        ] = None,
        sky_type: Annotated[
            str,
            Field(
                description=(
                    "CIE sky type for cie_sky: sunny, sunny_no_sun, cloudy, uniform_cloudy, "
                    "intermediate, or intermediate_no_sun."
                )
            ),
        ] = "sunny",
        latitude: Annotated[
            float | None,
            Field(description="Optional site latitude in degrees.", ge=-90, le=90),
        ] = None,
        longitude: Annotated[
            float | None,
            Field(description="Optional site longitude in degrees.", ge=-180, le=180),
        ] = None,
        standard_meridian: Annotated[
            float | None,
            Field(description="Optional standard meridian for gensky/gendaylit -m."),
        ] = None,
        ground_reflectance: Annotated[
            float | None,
            Field(description="Optional ground reflectance (-g). Defaults to 0.2.", ge=0, le=1),
        ] = None,
        sky_turbidity: Annotated[
            float | None,
            Field(description="Optional sky turbidity for cie_sky (gensky -t).", gt=0),
        ] = None,
        solar_radiance: Annotated[
            float | None,
            Field(description="Optional solar radiance for cie_sky (gensky -r).", ge=0),
        ] = None,
        direct_horizontal_irradiance: Annotated[
            float | None,
            Field(description="Optional direct horizontal irradiance for cie_sky (gensky -R).", ge=0),
        ] = None,
        zenith_brightness: Annotated[
            float | None,
            Field(description="Optional zenith brightness for cie_sky (gensky -b).", ge=0),
        ] = None,
        diffuse_horizontal_irradiance: Annotated[
            float | None,
            Field(description="Diffuse horizontal irradiance for cie_sky (gensky -B) or climate_based_sky (gendaylit -W).", ge=0),
        ] = None,
        direct_normal_irradiance: Annotated[
            float | None,
            Field(description="Direct normal irradiance for climate_based_sky (gendaylit -W).", ge=0),
        ] = None,
        direct_normal_illuminance: Annotated[
            float | None,
            Field(description="Direct normal illuminance for climate_based_sky (gendaylit -L).", ge=0),
        ] = None,
        diffuse_horizontal_illuminance: Annotated[
            float | None,
            Field(description="Diffuse horizontal illuminance for climate_based_sky (gendaylit -L).", ge=0),
        ] = None,
        output_mode: Annotated[
            int | None,
            Field(description="Optional gendaylit -O output mode for climate_based_sky."),
        ] = None,
        sky_part: Annotated[
            Literal["visible", "luminance", "solar", "radiance"] | None,
            Field(description="Optional climate_based_sky part: visible/luminance or solar/radiance."),
        ] = None,
        weather_target: Annotated[
            WeatherTargetRef | None,
            Field(description="Optional Garden weather_file target for EPW-backed skies/WEA/sky_matrix."),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative EPW path for EPW-backed skies/WEA/sky_matrix."),
        ] = None,
        stat_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative .stat file path for sky_matrix (Wea.from_stat_file)."),
        ] = None,
        wea_target: Annotated[
            ArtifactTargetRef | None,
            Field(description="Optional wea_file target for sky_matrix, leed_illuminance, or abnt_nbr_15575."),
        ] = None,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Ladybug Location dictionary for wea_clear_sky or sky_matrix."),
        ] = None,
        city: Annotated[
            str | None,
            Field(description="Optional city name when constructing a Location without location dict."),
        ] = None,
        region: Annotated[
            str | None,
            Field(description="Optional state/region when constructing a Location without location dict."),
        ] = None,
        elevation: Annotated[
            float | None,
            Field(description="Optional elevation when constructing a Location without location dict."),
        ] = None,
        sky_clearness: Annotated[
            float,
            Field(description="ASHRAE sky clearness value for wea_clear_sky or location-based sky_matrix.", ge=0),
        ] = 1,
        timestep: Annotated[
            int,
            Field(description="WEA timestep (default 1 for hourly data) for wea_from_epw or wea_clear_sky.", ge=1),
        ] = 1,
        hoys: Annotated[
            list[float] | None,
            Field(description="Optional hours of year filter for wea_from_epw or sky_matrix."),
        ] = None,
        hoy: Annotated[
            float | None,
            Field(description="Optional hour of year (0-8759) for from_epw_hoy.", ge=0, le=8784),
        ] = None,
        is_leap_year: Annotated[
            bool,
            Field(description="Whether to create a leap-year WEA for wea_clear_sky."),
        ] = False,
        write_hours: Annotated[
            bool,
            Field(description="Whether to write hour values into the WEA file."),
        ] = False,
        north: Annotated[
            float,
            Field(description="Counterclockwise north angle in degrees."),
        ] = 0,
        high_density: Annotated[
            bool,
            Field(description="Use Reinhart high-density sky patches instead of Tregenza patches for sky_matrix."),
        ] = False,
        compute: Annotated[
            bool,
            Field(description="When true, compute and persist direct/diffuse patch values for sky_matrix."),
        ] = False,
        irradiance: Annotated[
            float | None,
            Field(description="Horizontal diffuse irradiance (W/m2) for certain_irradiance.", ge=0),
        ] = None,
        illuminance: Annotated[
            float | None,
            Field(description="Horizontal illuminance (lux, including 0 for dark sky) for certain_irradiance.", ge=0),
        ] = None,
        uniform: Annotated[
            bool,
            Field(description="Use uniform sky instead of cloudy (for certain_irradiance) or UniformSky (for skydome)."),
        ] = False,
        cloudy: Annotated[
            bool | None,
            Field(description="Optional cloudy flag inverse of uniform for certain_irradiance."),
        ] = None,
        sky_density: Annotated[
            int,
            Field(description="Sky patch density for skydome (1=145 patches).", ge=1),
        ] = 1,
        ground_emittance: Annotated[
            float,
            Field(description="Ground emittance (0-1) for skydome.", ge=0, le=1),
        ] = 0.2,
        is_colored: Annotated[
            bool,
            Field(description="Colored sky flag for from_epw_hoy."),
        ] = False,
        benefit_matrix: Annotated[
            bool,
            Field(description="Generate a radiation benefit sky matrix from EPW dry-bulb temperature."),
        ] = False,
        balance_temperature: Annotated[
            float,
            Field(description="Balance temperature (C) for sky_matrix benefit_matrix."),
        ] = 15.0,
        balance_offset: Annotated[
            float,
            Field(description="Neutral deadband offset (C) around balance_temperature for benefit_matrix.", ge=0),
        ] = 2.0,
        output_subdir: Annotated[
            str | None,
            Field(description="Optional Garden-relative output folder override."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Return full Wea object_dict when creating WEA files. Keep false for compact handoff."),
        ] = False,
    ) -> ArtifactResultModel:
        """Create a Radiance sky, WEA, or SkyMatrix asset."""
        from garden.radiance.sky import create_radiance_sky_asset as service

        return validate_output(
            ArtifactResultModel,
            service(
                garden_root=garden_root,
                asset_type=asset_type,
                identifier=identifier,
                month=month,
                day=day,
                time=time,
                time_zone=time_zone,
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
                direct_normal_irradiance=direct_normal_irradiance,
                direct_normal_illuminance=direct_normal_illuminance,
                diffuse_horizontal_illuminance=diffuse_horizontal_illuminance,
                output_mode=output_mode,
                sky_part=sky_part,
                weather_target=dump_target(weather_target),
                epw_path=epw_path,
                stat_path=stat_path,
                wea_target=dump_target(wea_target),
                location=dump_input(location),
                city=city,
                region=region,
                elevation=elevation,
                sky_clearness=sky_clearness,
                timestep=timestep,
                hoys=hoys,
                hoy=hoy,
                is_leap_year=is_leap_year,
                write_hours=write_hours,
                north=north,
                high_density=high_density,
                compute=compute,
                irradiance=irradiance,
                illuminance=illuminance,
                uniform=uniform,
                cloudy=cloudy,
                sky_density=sky_density,
                ground_emittance=ground_emittance,
                is_colored=is_colored,
                benefit_matrix=benefit_matrix,
                balance_temperature=balance_temperature,
                balance_offset=balance_offset,
                output_subdir=output_subdir,
                return_object_dict=return_object_dict,
            ),
        )

    @mcp.tool(
        name="RAD_Create_Modifier",
        description=(
            "Create a Honeybee Radiance modifier ('opaque'/Plastic, 'glass', 'metal', "
            "'mirror', 'trans', 'bsdf', 'absdf', 'glow', 'light', 'spotlight', 'illum', "
            "'dielectric', 'brtdfunc', 'plastic2', 'metal2', 'trans2', or 'raw_rad' via "
            "Primitive.from_string), with optional parent modifier chaining. With garden_root "
            "and return_object_dict=false, saves a reusable Garden Properties Library target."
        ),
        tags={
            "radiance",
            "modifier",
            "material",
            "author",
        },
        timeout=20,
    )
    def create_radiance_modifier(
        modifier_type: Annotated[
            Literal[
                "opaque",
                "glass",
                "metal",
                "mirror",
                "trans",
                "bsdf",
                "absdf",
                "glow",
                "light",
                "spotlight",
                "illum",
                "dielectric",
                "brtdfunc",
                "plastic2",
                "metal2",
                "trans2",
                "raw_rad",
            ],
            Field(description="Modifier material kind."),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable Radiance modifier identifier."),
        ],
        rgb_reflectance: Annotated[
            float | list[float] | None,
            Field(description="Scalar or [r, g, b] reflectance (0-1) for opaque, metal, mirror, trans, or *2 materials."),
        ] = None,
        specularity: Annotated[
            float | None,
            Field(description="Specularity fraction (0-1) for opaque, metal, trans, plastic2, metal2, trans2.", ge=0, le=1),
        ] = None,
        roughness: Annotated[
            float | None,
            Field(description="Roughness fraction (0-1) for opaque, metal, or trans.", ge=0, le=1),
        ] = None,
        transmitted_diff: Annotated[
            float | None,
            Field(description="Diffuse transmitted fraction (0-1) for trans or trans2.", ge=0, le=1),
        ] = None,
        transmitted_spec: Annotated[
            float | None,
            Field(description="Specular transmitted fraction (0-1) for trans or trans2.", ge=0, le=1),
        ] = None,
        alternate_material: Annotated[
            LibraryObjectTargetRef | str | None,
            Field(description="Optional alternate material name (such as 'void') or modifier dict for mirror/illum."),
        ] = None,
        rgb_transmittance: Annotated[
            float | list[float] | None,
            Field(description="Scalar or [r, g, b] visible transmittance (0-1) for glass."),
        ] = None,
        rgb_transmissivity: Annotated[
            float | list[float] | None,
            Field(description="Scalar or [r, g, b] transmissivity (0-1) for glass."),
        ] = None,
        refraction_index: Annotated[
            float | None,
            Field(description="Optional refraction index for glass or dielectric (default 1.52).", gt=0),
        ] = None,
        modifier: Annotated[
            LibraryObjectTargetRef | str | None,
            Field(description="Optional parent modifier (library target, identifier, or dict) for modifier chaining."),
        ] = None,
        params: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional type-specific parameter overrides such as r/g/b channels, "
                    "bsdf_file, up_orientation, thickness, rgb_emittance, max_radius, angle, "
                    "direction, rgb_transmission, hartmann_constant, u_roughness, v_roughness, "
                    "rad_text, or values."
                )
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Garden root path containing garden.json. When supplied, saves the "
                    "modifier to the Garden Properties Library and returns a target."
                )
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full modifier object_dict. Set false with garden_root for compact handoff."),
        ] = True,
    ) -> MutationResultModel:
        """Create a Honeybee Radiance modifier."""
        from garden.radiance.modifiers import create_radiance_modifier as service

        return validate_output(
            MutationResultModel,
            service(
                modifier_type=modifier_type,
                identifier=identifier,
                rgb_reflectance=rgb_reflectance,
                specularity=specularity,
                roughness=roughness,
                transmitted_diff=transmitted_diff,
                transmitted_spec=transmitted_spec,
                alternate_material=dump_input(alternate_material),
                rgb_transmittance=rgb_transmittance,
                rgb_transmissivity=rgb_transmissivity,
                refraction_index=refraction_index,
                modifier=dump_input(modifier),
                params=dump_input(params),
                garden_root=garden_root,
                return_object_dict=return_object_dict,
            ),
        )

    @mcp.tool(
        name="RAD_Create_Modifier_Set",
        description=(
            "Create a Honeybee Radiance ModifierSet (optionally inheriting from base_modifier_set "
            "and overriding wall_set, floor_set, roof_ceiling_set, aperture_set, door_set, "
            "shade_set, or air_boundary_modifier). With garden_root, saves a reusable "
            "honeybee_radiance:modifier_set Garden Properties Library target."
        ),
        tags={
            "radiance",
            "modifier",
            "modifier-set",
            "author",
        },
        timeout=20,
    )
    def create_radiance_modifier_set(
        identifier: Annotated[
            str,
            Field(description="Stable Radiance ModifierSet identifier."),
        ],
        base_modifier_set: Annotated[
            LibraryObjectTargetRef | str | None,
            Field(description="Optional base ModifierSet target, standards identifier, or dict to inherit defaults from."),
        ] = None,
        wall_set: Annotated[
            dict[str, Any] | None,
            Field(description="Optional wall modifiers dict: {'exterior_modifier': ..., 'interior_modifier': ...}."),
        ] = None,
        floor_set: Annotated[
            dict[str, Any] | None,
            Field(description="Optional floor modifiers dict: {'exterior_modifier': ..., 'interior_modifier': ...}."),
        ] = None,
        roof_ceiling_set: Annotated[
            dict[str, Any] | None,
            Field(description="Optional roof/ceiling modifiers dict: {'exterior_modifier': ..., 'interior_modifier': ...}."),
        ] = None,
        aperture_set: Annotated[
            dict[str, Any] | None,
            Field(description="Optional aperture modifiers dict: {'window_modifier': ..., 'interior_modifier': ..., 'skylight_modifier': ..., 'operable_modifier': ...}."),
        ] = None,
        door_set: Annotated[
            dict[str, Any] | None,
            Field(description="Optional door modifiers dict: {'exterior_modifier': ..., 'interior_modifier': ..., 'exterior_glass_modifier': ..., 'interior_glass_modifier': ..., 'overhead_modifier': ...}."),
        ] = None,
        shade_set: Annotated[
            dict[str, Any] | None,
            Field(description="Optional shade modifiers dict: {'exterior_modifier': ..., 'interior_modifier': ...}."),
        ] = None,
        air_boundary_modifier: Annotated[
            LibraryObjectTargetRef | str | None,
            Field(description="Optional modifier for AirBoundary faces."),
        ] = None,
        return_detail: Annotated[
            Literal["summary", "full"],
            Field(description="Detail level for summary_view: 'summary' or 'full'."),
        ] = "summary",
        garden_root: Annotated[
            str | None,
            Field(description="Optional Garden root path containing garden.json to persist the ModifierSet."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Return full ModifierSet object_dict. Set false with garden_root for compact handoff."),
        ] = True,
    ) -> MutationResultModel:
        """Create a Honeybee Radiance ModifierSet."""
        from garden.radiance.modifiers import create_radiance_modifier_set as service

        return validate_output(
            MutationResultModel,
            service(
                identifier=identifier,
                base_modifier_set=dump_input(base_modifier_set),
                wall_set=dump_input(wall_set),
                floor_set=dump_input(floor_set),
                roof_ceiling_set=dump_input(roof_ceiling_set),
                aperture_set=dump_input(aperture_set),
                door_set=dump_input(door_set),
                shade_set=dump_input(shade_set),
                air_boundary_modifier=dump_input(air_boundary_modifier),
                return_detail=return_detail,
                garden_root=garden_root,
                return_object_dict=return_object_dict,
            ),
        )

    @mcp.tool(
        name="RAD_Manage_Luminaires",
        description=(
            "Create, attach, list, or remove Honeybee Radiance Luminaires (IES LM-63). "
            "Supports custom_lamp modes including predefined CustomLamp.from_lamp_name strings, "
            "action='create', action='attach', action='create_and_attach' (default), "
            "action='list', and action='remove'."
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
    def manage_radiance_luminaires(
        action: Annotated[
            Literal["create", "attach", "create_and_attach", "list", "remove"],
            Field(description="Operation: create, attach, create_and_attach (default), list, or remove."),
        ] = "create_and_attach",
        garden_root: Annotated[
            str | None,
            Field(
                description=(
                    "Garden root path containing garden.json, usually GD_Create['garden_root']; "
                    "required for attach/create_and_attach/list/remove."
                )
            ),
        ] = None,
        ies_content: Annotated[
            str | None,
            Field(description="IES LM-63 file text for create or create_and_attach."),
        ] = None,
        ies_path: Annotated[
            str | None,
            Field(description="Path to an existing IES LM-63 file for create or create_and_attach."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional Luminaire identifier."),
        ] = None,
        instances: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Optional LuminaireZone placement instances. Each item needs point ([x, y, z] "
                    "or Point3D dict) and optional spin, tilt, rotation, or aiming_point."
                )
            ),
        ] = None,
        custom_lamp: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional CustomLamp dict, settings ({'mode':'rgb','rgb':[1,0.8,0.6]}, "
                    "{'mode':'color_temperature','color_temperature':3000}, {'mode':'lamp_name','lamp_name':...}), "
                    "or direct legacy Honeybee lamp name string."
                )
            ),
        ] = None,
        light_loss_factor: Annotated[
            float,
            Field(description="Positive light loss multiplier for lamp/system depreciation.", gt=0),
        ] = 1.0,
        candela_multiplier: Annotated[
            float,
            Field(description="Positive candela multiplier applied to the IES distribution.", gt=0),
        ] = 1.0,
        luminaires: Annotated[
            list[LibraryObjectTargetRef] | None,
            Field(description="Existing Luminaire object_dict values or Garden luminaire targets for attach."),
        ] = None,
        luminaire_identifiers: Annotated[
            list[str] | str | None,
            Field(description="Luminaire identifier(s) or wildcard pattern(s) to remove when action='remove'."),
        ] = None,
        remove_all: Annotated[
            bool,
            Field(description="Remove all luminaires from model (and library if remove_from_library=true) when action='remove'."),
        ] = False,
        remove_from_library: Annotated[
            bool,
            Field(description="Also remove matching luminaire JSON files from Garden library when action='remove'."),
        ] = False,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Optional Honeybee model target. Defaults to the Garden base model."),
        ] = None,
        replace_existing: Annotated[
            bool,
            Field(description="Replace existing model luminaires with the same identifiers."),
        ] = False,
        return_object_dict: Annotated[
            bool,
            Field(description="Return the created Luminaire object_dict when creating."),
        ] = True,
    ) -> MutationResultModel:
        """Create, attach, list, or remove Honeybee Radiance Luminaires."""
        from garden.radiance.luminaires import (
            add_radiance_luminaire_to_model,
            create_radiance_luminaire,
            list_radiance_luminaires,
            remove_radiance_luminaire_from_model,
        )

        dumped_model_target = dump_target(model_target)
        dumped_luminaires = dump_targets(luminaires)
        dumped_instances = dump_input(instances)
        dumped_custom_lamp = dump_input(custom_lamp)

        if action == "list":
            return validate_output(
                MutationResultModel,
                list_radiance_luminaires(
                    garden_root=garden_root,
                    model_target=dumped_model_target,
                ),
            )
        if action == "remove":
            if not garden_root:
                raise ValueError("garden_root is required when action is 'remove'.")
            return validate_output(
                MutationResultModel,
                remove_radiance_luminaire_from_model(
                    garden_root=garden_root,
                    luminaire_identifiers=luminaire_identifiers,
                    model_target=dumped_model_target,
                    remove_all=remove_all,
                    remove_from_library=remove_from_library,
                ),
            )
        if action == "create":
            return validate_output(
                MutationResultModel,
                create_radiance_luminaire(
                    ies_content=ies_content,
                    ies_path=ies_path,
                    identifier=identifier,
                    instances=dumped_instances,
                    custom_lamp=dumped_custom_lamp,
                    light_loss_factor=light_loss_factor,
                    candela_multiplier=candela_multiplier,
                    garden_root=garden_root,
                    return_object_dict=return_object_dict,
                ),
            )
        if action == "attach":
            if not garden_root:
                raise ValueError("garden_root is required when action is 'attach'.")
            if not dumped_luminaires:
                raise ValueError("luminaires must be provided when action is 'attach'.")
            return validate_output(
                MutationResultModel,
                add_radiance_luminaire_to_model(
                    garden_root=garden_root,
                    luminaires=dumped_luminaires,
                    model_target=dumped_model_target,
                    replace_existing=replace_existing,
                ),
            )
        if not garden_root:
            raise ValueError("garden_root is required when action is 'create_and_attach'.")
        created = create_radiance_luminaire(
            ies_content=ies_content,
            ies_path=ies_path,
            identifier=identifier,
            instances=dumped_instances,
            custom_lamp=dumped_custom_lamp,
            light_loss_factor=light_loss_factor,
            candela_multiplier=candela_multiplier,
            garden_root=garden_root,
            return_object_dict=True,
        )
        to_attach: list[dict[str, Any]] = [created.get("target") or created["object_dict"]]
        if dumped_luminaires:
            to_attach.extend(dumped_luminaires)
        attached = add_radiance_luminaire_to_model(
            garden_root=garden_root,
            luminaires=to_attach,
            model_target=dumped_model_target,
            replace_existing=replace_existing,
        )
        if created.get("target") is not None:
            attached["luminaire_target"] = created["target"]
        if created.get("persistence_receipt") is not None:
            attached["luminaire_persistence_receipt"] = created["persistence_receipt"]
        if return_object_dict and "object_dict" in created:
            attached["object_dict"] = created["object_dict"]
        attached["summary_view"]["luminaire"] = created["summary_view"]
        return validate_output(MutationResultModel, attached)

    @mcp.tool(
        name="RAD_Setup_Dynamic_Group",
        description=(
            "Apply Radiance dynamic_group_identifier and states (supporting modifier_direct, "
            "vmtx_geometry, dmtx_geometry, and tmtx_thickness) to Shade/Aperture/Door targets, "
            "or set operation='auto_group' to automatically group exterior apertures using "
            "honeybee_radiance.dynamic.multiphase.automatic_aperture_grouping."
        ),
        tags={
            "dynamic",
            "radiance",
            "model",
            "edit",
        },
        timeout=120,
    )
    def setup_radiance_dynamic_group(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually GD_Create['garden_root']; "
                    "required when saving or reading Garden targets."
                )
            ),
        ],
        targets: Annotated[
            list[BuildingObjectTargetRef] | None,
            Field(
                description=(
                    "Shade, Aperture, or Door typed targets to update for replace_all/add/clear; "
                    "omit when operation='auto_group'."
                )
            ),
        ] = None,
        dynamic_group_identifier: Annotated[
            str | None,
            Field(description="Dynamic group identifier to set on targets (not used for auto_group)."),
        ] = None,
        states: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "List of Radiance state dicts supporting modifier, modifier_direct, shades, "
                    "vmtx_geometry, dmtx_geometry, and tmtx_thickness."
                )
            ),
        ] = None,
        operation: Annotated[
            Literal["replace_all", "add", "clear", "auto_group"],
            Field(description="Operation: replace_all, add, clear, or auto_group."),
        ] = "replace_all",
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Optional Honeybee model target for auto_group or tmtx_thickness."),
        ] = None,
        size: Annotated[
            float,
            Field(description="Aperture sensor grid cell size (m) for auto_group.", gt=0),
        ] = 0.2,
        threshold: Annotated[
            float,
            Field(description="View factor similarity threshold for clustering apertures in auto_group.", gt=0),
        ] = 0.001,
        ambient_division: Annotated[
            int,
            Field(description="Ambient divisions (-ad) for rfluxmtx view factor grouping in auto_group.", ge=1),
        ] = 1000,
        room_based: Annotated[
            bool,
            Field(description="Restrict aperture groups per room in auto_group."),
        ] = True,
        view_factor_or_orientation: Annotated[
            bool,
            Field(description="Group by rfluxmtx view factor (true) or aperture orientation only (false) in auto_group."),
        ] = True,
        vertical_tolerance: Annotated[
            float | None,
            Field(description="Optional vertical separation limit between apertures in the same group for auto_group.", ge=0),
        ] = None,
        tmtx_thickness: Annotated[
            float | None,
            Field(description="Optional default 3-phase transmission matrix thickness to auto-generate vmtx/dmtx geometries.", ge=0),
        ] = None,
    ) -> MutationResultModel:
        """Apply Radiance dynamic state settings or automatically group exterior apertures."""
        from garden.radiance.dynamic import setup_radiance_dynamic_group as service

        return validate_output(
            MutationResultModel,
            service(
                garden_root=garden_root,
                targets=dump_targets(targets),
                dynamic_group_identifier=dynamic_group_identifier,
                states=dump_input(states),
                operation=operation,
                model_target=dump_target(model_target),
                size=size,
                threshold=threshold,
                ambient_division=ambient_division,
                room_based=room_based,
                view_factor_or_orientation=view_factor_or_orientation,
                vertical_tolerance=vertical_tolerance,
                tmtx_thickness=tmtx_thickness,
            ),
        )

    @mcp.tool(
        name="RAD_Create_Scene_Asset",
        description=(
            "Create, generate from Honeybee Rooms, merge, split, or remove Radiance SensorGrids "
            "and Views. Persists a .json sidecar alongside .pts so mesh, room_identifier, "
            "group_identifier, and base_geometry survive reattachment. Supports asset_type modes: "
            "sensor_grid, view, room_floor_grid, room_radial_grid (for imageless glare), "
            "exterior_face_grid, exterior_aperture_grid, and room_view; plus action='remove'|'merge'|'split'."
        ),
        tags={
            "radiance",
            "sensor-grid",
            "view",
            "author",
        },
        timeout=60,
    )
    def create_radiance_scene_asset(
        asset_type: Annotated[
            Literal[
                "sensor_grid",
                "view",
                "room_floor_grid",
                "room_radial_grid",
                "exterior_face_grid",
                "exterior_aperture_grid",
                "room_view",
                "remove",
                "merge",
                "split",
            ]
            | None,
            Field(description="Scene asset type to create or action alias."),
        ] = None,
        action: Annotated[
            Literal["create", "remove", "merge", "split"],
            Field(description="Scene asset action: create (default), remove, merge, or split."),
        ] = "create",
        identifier: Annotated[
            str | None,
            Field(description="Stable identifier for the SensorGrid or View."),
        ] = None,
        positions: Annotated[
            list[list[float]] | None,
            Field(description="Explicit sensor positions [[x, y, z], ...] for sensor_grid or room_radial_grid."),
        ] = None,
        direction: Annotated[
            VectorInput,
            Field(description="Shared sensor direction or camera look direction as [x, y, z] or {x,y,z}."),
        ] = None,
        directions: Annotated[
            list[list[float]] | None,
            Field(description="Per-sensor directions [[x, y, z], ...] matching positions for sensor_grid."),
        ] = None,
        x_dim: Annotated[
            float | None,
            Field(description="Rectangular workplane width or room grid X spacing.", gt=0),
        ] = None,
        y_dim: Annotated[
            float | None,
            Field(description="Rectangular workplane depth or room grid Y spacing.", gt=0),
        ] = None,
        height: Annotated[
            float | None,
            Field(description="Workplane height above origin for rectangular sensor_grid (defaults to 0.8)."),
        ] = None,
        x_count: Annotated[
            int | None,
            Field(description="Sensor sample count along local x for rectangular or object sensor_grid.", ge=1),
        ] = None,
        y_count: Annotated[
            int | None,
            Field(description="Sensor sample count along local y for rectangular or object sensor_grid.", ge=1),
        ] = None,
        grid_spacing: Annotated[
            float | None,
            Field(description="Approximate sensor spacing in model units.", gt=0),
        ] = None,
        origin: Annotated[
            VectorInput,
            Field(description="Rectangular sensor_grid origin [x, y, z] or {x,y,z}. Defaults to [0, 0, 0]."),
        ] = None,
        object_target: Annotated[
            BuildingObjectTargetRef | None,
            Field(
                description=(
                    "Optional Honeybee face, aperture, door, or shade target to sample into a "
                    "mesh-backed sensor_grid (requires garden_root)."
                )
            ),
        ] = None,
        offset: Annotated[
            float | None,
            Field(description="Normal/floor offset distance (defaults to 0.01 object, 0.8 room floor, 1.2 radial, 0.1 exterior)."),
        ] = None,
        flip_direction: Annotated[
            bool,
            Field(description="Flip sensor normal and offset direction when sampling object_target."),
        ] = False,
        position: Annotated[
            VectorInput,
            Field(description="Camera position [x, y, z] or {x,y,z} for view (defaults to [0, 0, 0])."),
        ] = None,
        target: Annotated[
            VectorInput,
            Field(description="Optional camera look-at point [x, y, z] or {x,y,z} used to derive direction for view."),
        ] = None,
        up_vector: Annotated[
            VectorInput,
            Field(description="Camera up vector [x, y, z] or {x,y,z} for view (defaults to [0, 1, 0])."),
        ] = None,
        view_type: Annotated[
            str,
            Field(description="Radiance view type (v, h, l, c, a, s, or vt* token) for view or room_view."),
        ] = "v",
        h_size: Annotated[
            float,
            Field(description="Horizontal field of view/size for view.", gt=0),
        ] = 60,
        v_size: Annotated[
            float,
            Field(description="Vertical field of view/size for view.", gt=0),
        ] = 60,
        shift: Annotated[
            float | None,
            Field(description="Optional Radiance view shift (-vs) for view."),
        ] = None,
        lift: Annotated[
            float | None,
            Field(description="Optional Radiance view lift (-vl) for view."),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional display name."),
        ] = None,
        room_identifier: Annotated[
            str | None,
            Field(description="Optional Honeybee Room identifier for grid/view association or generation."),
        ] = None,
        room_target: Annotated[
            BuildingObjectTargetRef | None,
            Field(description="Optional Honeybee Room target used to infer room_identifier."),
        ] = None,
        group_identifier: Annotated[
            str | None,
            Field(description="Optional Radiance dynamic group identifier."),
        ] = None,
        wall_offset: Annotated[
            float,
            Field(description="Inset offset from room walls for room_floor_grid or room_radial_grid."),
        ] = 0.0,
        remove_out: Annotated[
            bool,
            Field(description="Remove grid vertices/sensors falling outside concave room boundaries."),
        ] = False,
        dir_count: Annotated[
            int,
            Field(description="Number of horizontal viewing directions per point for room_radial_grid.", ge=1),
        ] = 8,
        start_vector: Annotated[
            VectorInput,
            Field(description="Starting direction vector [x, y, z] for room_radial_grid."),
        ] = None,
        mesh_radius: Annotated[
            float | None,
            Field(description="Optional radial wedge mesh radius for room_radial_grid."),
        ] = None,
        face_type: Annotated[
            str,
            Field(description="Face type ('Wall', 'RoofCeiling', 'Floor', 'All') for exterior_face_grid."),
        ] = "Wall",
        punched_geometry: Annotated[
            bool,
            Field(description="Exclude apertures/doors from exterior_face_grid when true."),
        ] = False,
        aperture_type: Annotated[
            str,
            Field(description="Aperture type ('All', 'Window', 'Skylight') for exterior_aperture_grid."),
        ] = "All",
        target_kind: Annotated[
            Literal["all", "sensor_grid", "view"],
            Field(description="Asset kind filter for action='remove'."),
        ] = "all",
        grid_identifiers: Annotated[
            list[str] | str | None,
            Field(description="SensorGrid identifier(s) or pattern(s) for remove or merge."),
        ] = None,
        view_identifiers: Annotated[
            list[str] | str | None,
            Field(description="View identifier(s) or pattern(s) for remove."),
        ] = None,
        filter_pattern: Annotated[
            str,
            Field(description="Wildcard pattern for remove or merge."),
        ] = "*",
        remove_all: Annotated[
            bool,
            Field(description="Remove all matching SensorGrids/Views when action='remove'."),
        ] = False,
        sensor_grid_target: Annotated[
            ArtifactTargetRef | None,
            Field(description="Existing radiance_sensor_grid target to convert (radial) or split."),
        ] = None,
        sensor_grid_targets: Annotated[
            list[ArtifactTargetRef] | None,
            Field(description="List of radiance_sensor_grid targets for action='merge'."),
        ] = None,
        split_count: Annotated[
            int,
            Field(description="Number of chunks when action='split'.", ge=2),
        ] = 2,
        max_sensors: Annotated[
            int | None,
            Field(description="Maximum sensors per chunk when action='split'.", ge=1),
        ] = None,
        replace_existing: Annotated[
            bool,
            Field(description="Replace original model grids when merging or splitting."),
        ] = True,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json."),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Optional Honeybee model target. Defaults to the Garden base model when attaching."),
        ] = None,
        attach_to_model: Annotated[
            bool,
            Field(description="When true, attach the SensorGrid or View to model.properties.radiance and save."),
        ] = False,
        output_subdir: Annotated[
            str | None,
            Field(description="Optional Garden-relative output folder override."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Return the full SensorGrid or View object_dict. Set false for compact handoff."),
        ] = True,
    ) -> ArtifactResultModel:
        """Create, generate from rooms, merge, split, or remove Radiance SensorGrids and Views."""
        from garden.radiance.assets import create_radiance_scene_asset as service

        return validate_output(
            ArtifactResultModel,
            service(
                asset_type=asset_type,
                action=action,
                identifier=identifier,
                positions=positions,
                direction=dump_input(direction),
                directions=directions,
                x_dim=x_dim,
                y_dim=y_dim,
                height=height,
                x_count=x_count,
                y_count=y_count,
                grid_spacing=grid_spacing,
                origin=dump_input(origin),
                object_target=dump_target(object_target),
                offset=offset,
                flip_direction=flip_direction,
                position=dump_input(position),
                target=dump_input(target),
                up_vector=dump_input(up_vector),
                view_type=view_type,
                h_size=h_size,
                v_size=v_size,
                shift=shift,
                lift=lift,
                display_name=display_name,
                room_identifier=room_identifier,
                room_target=dump_target(room_target),
                group_identifier=group_identifier,
                wall_offset=wall_offset,
                remove_out=remove_out,
                dir_count=dir_count,
                start_vector=dump_input(start_vector),
                mesh_radius=mesh_radius,
                face_type=face_type,
                punched_geometry=punched_geometry,
                aperture_type=aperture_type,
                target_kind=target_kind,
                grid_identifiers=grid_identifiers,
                view_identifiers=view_identifiers,
                filter_pattern=filter_pattern,
                remove_all=remove_all,
                sensor_grid_target=dump_target(sensor_grid_target),
                sensor_grid_targets=dump_targets(sensor_grid_targets),
                split_count=split_count,
                max_sensors=max_sensors,
                replace_existing=replace_existing,
                garden_root=garden_root,
                model_target=dump_target(model_target),
                attach_to_model=attach_to_model,
                output_subdir=output_subdir,
                return_object_dict=return_object_dict,
            ),
        )

    @mcp.tool(
        name="RAD_Create_Parameters",
        description=(
            "Create recommended Radiance command parameters for all rtrace, rpict, rfluxmtx, "
            "rcontrib, dcglare, evalglare, annual daylight/compliance, or comfort-map recipes. "
            "Pass the returned radiance_parameters string or target to RAD_Start_Simulation or "
            "RAD_Manage_Recipes. Returns target, summary_view, and report."
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
                description=(
                    "Radiance recipe or command name (including point-in-time-grid, daylight-factor, "
                    "sky-view, point-in-time-view, annual-daylight, annual-daylight-enhanced, "
                    "direct-sun-hours, annual-irradiance, cumulative-radiation, imageless-annual-glare, "
                    "leed-daylight-option-one, leed-daylight-option-two, annual-daylight-en17037, "
                    "well-daylight, breeam-daylight-4b, pmv-comfort-map, utci-comfort-map, "
                    "adaptive-comfort-map, rtrace, rpict, rfluxmtx, rcontrib, dcglare, or evalglare)."
                ),
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
    ) -> QueryResultModel:
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
        return validate_output(QueryResultModel, result)

    @mcp.tool(
        name="RAD_Start_Simulation",
        description=(
            "Start any Garden Honeybee Radiance or comfort-map simulation recipe in the background "
            "(or wait until completion/timeout when wait_seconds is provided). Select recipe from: "
            "point-in-time-grid, daylight-factor, sky-view, point-in-time-view, annual-daylight, "
            "annual-daylight-enhanced, annual-irradiance, cumulative-radiation, direct-sun-hours, "
            "imageless-annual-glare, leed-daylight-option-one, leed-daylight-option-two, "
            "annual-daylight-en17037, breeam-daylight-4b, well-daylight, pmv-comfort-map, "
            "utci-comfort-map, or adaptive-comfort-map. Poll with GD_Poll_Run and read with RAD_Read_Results."
        ),
        tags={
            "start",
            "radiance",
            "simulate",
            "poll",
        },
        timeout=3600,
    )
    def start_radiance_simulation(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually GD_Create['garden_root']; "
                    "required when saving or reading Garden targets."
                )
            ),
        ],
        recipe: Annotated[
            Literal[
                "point-in-time-grid",
                "daylight-factor",
                "sky-view",
                "point-in-time-view",
                "annual-daylight",
                "annual-daylight-enhanced",
                "annual-irradiance",
                "cumulative-radiation",
                "direct-sun-hours",
                "imageless-annual-glare",
                "leed-daylight-option-one",
                "leed-daylight-option-two",
                "annual-daylight-en17037",
                "breeam-daylight-4b",
                "well-daylight",
                "pmv-comfort-map",
                "utci-comfort-map",
                "adaptive-comfort-map",
            ],
            Field(description="Exact Honeybee Radiance or comfort-map recipe name to run."),
        ],
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(
                description=(
                    "Optional Honeybee model target with target_type=honeybee_model. Defaults to "
                    "the Garden base model."
                )
            ),
        ] = None,
        radiance_sky_file: Annotated[
            SkyTargetRef | None,
            Field(
                description=(
                    "Radiance sky file target from RAD_Create_Sky_Asset (required for "
                    "point-in-time-grid and point-in-time-view unless sky is given)."
                )
            ),
        ] = None,
        sky: Annotated[
            str | None,
            Field(description="Optional raw recipe sky string instead of radiance_sky_file."),
        ] = None,
        wea_target: Annotated[
            ArtifactTargetRef | None,
            Field(
                description=(
                    "Garden WEA target from RAD_Create_Sky_Asset for matrix, glare, "
                    "leed-daylight-option-one/two, or breeam-daylight-4b."
                )
            ),
        ] = None,
        wea_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative .wea path. Prefer wea_target."),
        ] = None,
        weather_file_target: Annotated[
            WeatherTargetRef | None,
            Field(
                description=(
                    "Garden weather_file target (with annual epw_path) required for "
                    "annual-daylight-en17037, well-daylight, or comfort-map recipes."
                )
            ),
        ] = None,
        grid_filter: Annotated[
            str,
            Field(description="SensorGrid identifier or pattern ('*' for all attached SensorGrids)."),
        ] = "*",
        sensor_grid_target: Annotated[
            ArtifactTargetRef | None,
            Field(description="Optional radiance_sensor_grid target used when grid_filter is '*'."),
        ] = None,
        view_filter: Annotated[
            str,
            Field(description="Radiance View identifier or pattern ('*' for all attached Views)."),
        ] = "*",
        view_target: Annotated[
            ArtifactTargetRef | None,
            Field(description="Optional radiance_view target used when view_filter is '*'."),
        ] = None,
        north: Annotated[
            float | None,
            Field(description="Optional north angle in degrees."),
        ] = None,
        min_sensor_count: Annotated[
            int,
            Field(description="Minimum sensors per redistributed grid batch.", ge=1),
        ] = 1,
        radiance_parameters: Annotated[
            ArtifactTargetRef | str | None,
            Field(description="Optional Radiance parameters string or RAD_Create_Parameters result."),
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
            Field(description="Reload existing recipe results in the run folder when available."),
        ] = False,
        silent: Annotated[
            bool,
            Field(description="Run the Radiance recipe silently."),
        ] = True,
        wait_seconds: Annotated[
            float | None,
            Field(
                description="Optional maximum seconds to wait for completion before returning.",
                ge=0,
            ),
        ] = None,
        poll_interval: Annotated[
            float,
            Field(description="Polling interval in seconds when wait_seconds is supplied.", gt=0),
        ] = 1.0,
        metric: Annotated[
            str | None,
            Field(
                description=(
                    "Optional point-in-time metric (illuminance, irradiance, luminance, or radiance). "
                    "Defaults to illuminance for grid and luminance for view."
                )
            ),
        ] = None,
        cloudy_sky: Annotated[
            Literal["uniform", "cloudy"] | None,
            Field(description="Sky View condition ('uniform' or 'cloudy') for sky-view."),
        ] = None,
        resolution: Annotated[
            int | None,
            Field(description="Optional image resolution for point-in-time-view.", ge=1),
        ] = None,
        skip_overture: Annotated[
            bool | None,
            Field(description="Optional skip-overture flag for point-in-time-view."),
        ] = None,
        timestep: Annotated[
            int | None,
            Field(description="Optional timestep for matrix recipes.", ge=1),
        ] = None,
        schedule: Annotated[
            LibraryObjectTargetRef | list[float] | str | None,
            Field(description="Optional annual occupancy schedule (Garden schedule target, 8760 list, CSV path, or inline CSV text)."),
        ] = None,
        thresholds: Annotated[
            str | None,
            Field(description="Optional DA/UDI threshold string for annual-daylight or annual-daylight-en17037."),
        ] = None,
        output_type: Annotated[
            str | None,
            Field(description="Optional output-type ('solar' or 'visible') for annual-irradiance."),
        ] = None,
        sky_density: Annotated[
            int | None,
            Field(description="Optional sky-density for cumulative-radiation.", ge=1),
        ] = None,
        grid_metrics: Annotated[
            list[dict[str, Any]] | dict[str, Any] | str | None,
            Field(description="Optional native grid-metrics list[dict], dict (auto-wrapped to list), or JSON/file string."),
        ] = None,
        dgp_threshold: Annotated[
            float | None,
            Field(description="DGP threshold (0-1) for imageless-annual-glare.", ge=0, le=1),
        ] = None,
        luminance_factor: Annotated[
            float | None,
            Field(description="Luminance threshold in cd/m2 for imageless-annual-glare.", gt=0),
        ] = None,
        diffuse_transmission: Annotated[
            float | None,
            Field(
                description="Diffuse blind transmission fraction (0.0001-1) for leed-daylight-option-one or well-daylight.",
                ge=0.0001,
                le=1,
            ),
        ] = None,
        specular_transmission: Annotated[
            float | None,
            Field(
                description="Specular blind transmission fraction (0.0001-1) for leed-daylight-option-one or well-daylight.",
                ge=0.0001,
                le=1,
            ),
        ] = None,
        glare_control_devices: Annotated[
            Literal["glare-control", "no-glare-control"] | None,
            Field(description="Glare control enum for leed-daylight-option-two."),
        ] = None,
        debug_folder: Annotated[
            str | None,
            Field(description="Optional Garden-relative debug folder path passed to RecipeSettings."),
        ] = None,
        recipe_options: Annotated[
            dict[str, Any] | None,
            Field(description="Optional extra recipe option overrides dictionary (including comfort-map inputs)."),
        ] = None,
    ) -> RunResultModel:
        """Start a Honeybee Radiance or comfort-map simulation recipe."""
        from garden.radiance.run import start_radiance_simulation as service

        return validate_output(
            RunResultModel,
            service(
                garden_root=garden_root,
                recipe=recipe,
                model_target=dump_target(model_target),
                radiance_sky_file=dump_target(radiance_sky_file),
                sky=sky,
                wea_target=dump_target(wea_target),
                wea_path=wea_path,
                weather_file_target=dump_target(weather_file_target),
                grid_filter=grid_filter,
                sensor_grid_target=dump_target(sensor_grid_target),
                view_filter=view_filter,
                view_target=dump_target(view_target),
                north=north,
                min_sensor_count=min_sensor_count,
                radiance_parameters=dump_input(radiance_parameters),
                run_id=run_id,
                workers=workers,
                reload_old=reload_old,
                silent=silent,
                wait_seconds=wait_seconds,
                poll_interval=poll_interval,
                metric=metric,
                cloudy_sky=cloudy_sky,
                resolution=resolution,
                skip_overture=skip_overture,
                timestep=timestep,
                schedule=dump_input(schedule),
                thresholds=thresholds,
                output_type=output_type,
                sky_density=sky_density,
                grid_metrics=dump_input(grid_metrics),
                dgp_threshold=dgp_threshold,
                luminance_factor=luminance_factor,
                diffuse_transmission=diffuse_transmission,
                specular_transmission=specular_transmission,
                glare_control_devices=glare_control_devices,
                debug_folder=debug_folder,
                recipe_options=dump_input(recipe_options),
            ),
        )

    @mcp.tool(
        name="RAD_Manage_Recipes",
        description=(
            "Schema-driven generic Queenbee / lbt-recipes runner supporting all 19 installed "
            "lbt-recipes packages (including pmv-comfort-map, utci-comfort-map, adaptive-comfort-map, "
            "and annual-energy-use) plus external local Queenbee recipe folder paths. "
            "Use action='list' to enumerate installed recipes, action='describe' for full input/output "
            "schemas, or action='start' to resolve Garden targets and execute via GD_Poll_Run."
        ),
        tags={
            "recipe",
            "queenbee",
            "radiance",
            "comfort",
            "simulate",
        },
        timeout=3600,
    )
    def manage_recipes(
        action: Annotated[
            Literal["list", "describe", "start"],
            Field(description="Recipe action: list, describe, or start."),
        ],
        recipe: Annotated[
            str | None,
            Field(description="Installed lbt-recipes name or local Queenbee recipe folder path (required for describe and start)."),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json (required for start)."),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Optional Honeybee model target resolved automatically for 'model' input."),
        ] = None,
        weather_file_target: Annotated[
            WeatherTargetRef | None,
            Field(description="Optional Garden weather_file target resolved for 'epw', 'ddy', or 'wea' inputs."),
        ] = None,
        weather_target: Annotated[
            WeatherTargetRef | None,
            Field(description="Alias for weather_file_target."),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative EPW path."),
        ] = None,
        ddy_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative DDY path."),
        ] = None,
        wea_target: Annotated[
            ArtifactTargetRef | None,
            Field(description="Optional WEA target for 'wea' input."),
        ] = None,
        wea_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative WEA path."),
        ] = None,
        radiance_sky_file: Annotated[
            SkyTargetRef | None,
            Field(description="Optional Radiance sky target for 'sky' input."),
        ] = None,
        sky: Annotated[
            str | None,
            Field(description="Optional sky string for 'sky' input."),
        ] = None,
        schedule: Annotated[
            LibraryObjectTargetRef | list[float] | str | None,
            Field(description="Optional Garden schedule target, list, or CSV text materialized to .csv."),
        ] = None,
        sim_par: Annotated[
            LibraryObjectTargetRef | str | None,
            Field(description="Optional EnergyPlus simulation parameter target or dict for 'sim-par'."),
        ] = None,
        radiance_parameters: Annotated[
            ArtifactTargetRef | str | None,
            Field(description="Optional Radiance parameters string or target."),
        ] = None,
        inputs: Annotated[
            dict[str, Any] | None,
            Field(description="Recipe-specific input dictionary matching schema input names."),
        ] = None,
        recipe_options: Annotated[
            dict[str, Any] | None,
            Field(description="Optional alias/override dictionary merged with inputs."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier."),
        ] = None,
        workers: Annotated[
            int | None,
            Field(description="Optional cpu-count worker limit.", ge=1),
        ] = None,
        reload_old: Annotated[
            bool,
            Field(description="Reload previous intermediate task results if present."),
        ] = False,
        silent: Annotated[
            bool,
            Field(description="Suppress console output in worker process."),
        ] = True,
        debug_folder: Annotated[
            str | None,
            Field(description="Optional Garden-relative debug folder path."),
        ] = None,
    ) -> RunResultModel:
        """List, describe, or start any lbt-recipes or local Queenbee recipe."""
        from garden.recipes.runner import manage_recipes as service

        return validate_output(
            RunResultModel,
            service(
                action=action,
                recipe=recipe,
                garden_root=garden_root,
                model_target=dump_target(model_target),
                weather_file_target=dump_target(weather_file_target),
                weather_target=dump_target(weather_target),
                epw_path=epw_path,
                ddy_path=ddy_path,
                wea_target=dump_target(wea_target),
                wea_path=wea_path,
                radiance_sky_file=dump_target(radiance_sky_file),
                sky=sky,
                schedule=dump_input(schedule),
                sim_par=dump_input(sim_par),
                radiance_parameters=dump_input(radiance_parameters),
                inputs=dump_input(inputs),
                recipe_options=dump_input(recipe_options),
                run_id=run_id,
                workers=workers,
                reload_old=reload_old,
                silent=silent,
                debug_folder=debug_folder,
            ),
        )

    @mcp.tool(
        name="RAD_Read_Results",
        description=(
            "Read compact quantitative results or run postprocessing on a completed Garden Radiance or "
            "comfort-map run. Supports nine result_kind modes: 'annual_daylight', 'glare', 'compliance', "
            "'grid_summary' (numeric stats for point-in-time-grid/DF/sky-view/radiation/sun-hours/comfort grids), "
            "'annual_postprocess' (post-hoc DA/cDA/UDI/sDA/ASE/uniformity/HOY-filtered stats via honeybee_radiance_postprocess), "
            "'daylight_control_schedule' (8760 electric dimming schedules persisted to Garden for EnergyPlus), "
            "'dynamic_schedule' (sensor_maximum, ies_lm_83, or leed aperture blind schedules), "
            "'comfort_map' (TCP/HSP/CSP summary), and 'list_outputs' (grid folders, HDR images, raw outputs)."
        ),
        tags={
            "radiance",
            "metrics",
            "compliance",
            "glare",
            "result",
            "summary",
        },
        timeout=120,
    )
    def read_radiance_results(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually GD_Create['garden_root']; "
                    "required when saving or reading Garden targets."
                )
            ),
        ],
        result_kind: Annotated[
            Literal[
                "annual_daylight",
                "glare",
                "compliance",
                "grid_summary",
                "annual_postprocess",
                "daylight_control_schedule",
                "dynamic_schedule",
                "comfort_map",
                "list_outputs",
            ],
            Field(description="Result summary / postprocessing mode."),
        ],
        run_target: Annotated[
            RunTargetRef | None,
            Field(description="Completed radiance_run target returned by RAD_Start_Simulation, RAD_Manage_Recipes, or GD_Poll_Run."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Completed Radiance run identifier when run_target is omitted."),
        ] = None,
        grid_identifier: Annotated[
            str | None,
            Field(description="Optional grid identifier for report provenance."),
        ] = None,
        grid_filter: Annotated[
            str,
            Field(description="SensorGrid pattern filter for grid_summary, annual_postprocess, schedules."),
        ] = "*",
        output_name: Annotated[
            str | None,
            Field(description="Optional specific output folder name for grid_summary."),
        ] = None,
        metrics: Annotated[
            list[str] | None,
            Field(description="Optional metric list for annual_daylight, for example ['sda', 'ase', 'da', 'udi']."),
        ] = None,
        view_identifier: Annotated[
            str | None,
            Field(description="Optional view identifier for glare report provenance."),
        ] = None,
        dgp_threshold: Annotated[
            float,
            Field(description="DGP exceedance threshold for glare summary.", ge=0, le=1),
        ] = 0.4,
        thresholds: Annotated[
            dict[str, Any] | None,
            Field(description="Custom threshold dictionary for annual_postprocess."),
        ] = None,
        threshold: Annotated[
            float,
            Field(description="Illuminance threshold (lux) for DA/sDA in annual_postprocess.", ge=0),
        ] = 300.0,
        min_threshold: Annotated[
            float,
            Field(description="Minimum UDI threshold (lux) for annual_postprocess.", ge=0),
        ] = 100.0,
        max_threshold: Annotated[
            float,
            Field(description="Maximum UDI threshold (lux) for annual_postprocess.", ge=0),
        ] = 3000.0,
        target_time: Annotated[
            float,
            Field(description="Occupied hours percentage threshold for sDA in annual_postprocess.", ge=0, le=100),
        ] = 50.0,
        ase_threshold: Annotated[
            float,
            Field(description="Direct illuminance threshold (lux) for ASE in annual_postprocess.", ge=0),
        ] = 1000.0,
        ase_occ_hours: Annotated[
            int,
            Field(description="Maximum annual direct hours for ASE in annual_postprocess.", ge=0),
        ] = 250,
        uniformity_threshold: Annotated[
            float,
            Field(description="Minimum uniformity ratio threshold for annual_postprocess.", ge=0, le=1),
        ] = 0.5,
        schedule: Annotated[
            LibraryObjectTargetRef | list[float] | str | None,
            Field(description="Optional occupancy/base schedule target, 8760 list, or CSV path."),
        ] = None,
        dynamic_schedule: Annotated[
            LibraryObjectTargetRef | str | None,
            Field(description="Optional DynamicSchedule target, dict, or JSON path for postprocess or dimming."),
        ] = None,
        hoys: Annotated[
            list[float] | None,
            Field(description="Optional hours of year filter for HOY-filtered statistics in annual_postprocess."),
        ] = None,
        res_type: Annotated[
            Literal["total", "direct"],
            Field(description="Result component for postprocess / dynamic_schedule: total or direct."),
        ] = "total",
        mode: Annotated[
            str | None,
            Field(description="Optional mode override ('auto'|'daylight'|'irradiance' for annual_postprocess; 'sensor_maximum'|'ies_lm_83'|'leed' for dynamic_schedule)."),
        ] = None,
        ill_setpoint: Annotated[
            float,
            Field(description="Target workplane illuminance setpoint (lux) for daylight_control_schedule.", gt=0),
        ] = 300.0,
        min_power_in: Annotated[
            float,
            Field(description="Minimum ballast power fraction at full dimming for daylight_control_schedule.", ge=0, le=1),
        ] = 0.3,
        min_light_out: Annotated[
            float,
            Field(description="Minimum light output fraction before clamping for daylight_control_schedule.", ge=0, le=1),
        ] = 0.2,
        off_at_min: Annotated[
            bool,
            Field(description="Switch electric lighting off completely when below min_light_out for daylight_control_schedule."),
        ] = False,
        identifier_prefix: Annotated[
            str | None,
            Field(description="Identifier prefix for persisted daylight_control_schedule artifacts."),
        ] = None,
        persist_to_garden: Annotated[
            bool,
            Field(description="Persist ScheduleFixedInterval library targets into Garden for daylight_control_schedule."),
        ] = True,
        sensor_index: Annotated[
            dict[str, list[int]] | None,
            Field(description="Map {grid_full_id: [sensor_idx]} for dynamic_schedule mode='sensor_maximum'."),
        ] = None,
        maximum: Annotated[
            float,
            Field(description="Maximum allowed illuminance (lux) on control sensor for dynamic_schedule mode='sensor_maximum'.", ge=0),
        ] = 3000.0,
        shade_transmittance: Annotated[
            float | dict[str, float],
            Field(description="Shade transmittance multiplier or per-aperture-group dict for ies_lm_83 / leed dynamic_schedule."),
        ] = 0.05,
        use_states: Annotated[
            bool,
            Field(description="Use simulated blind states instead of shade_transmittance multiplier for ies_lm_83 / leed."),
        ] = False,
        save_report: Annotated[
            bool,
            Field(description="Save a compact JSON report artifact."),
        ] = True,
        include_values: Annotated[
            bool,
            Field(description="Return raw sensor/metric arrays. Keep false for compact handoff."),
        ] = False,
        page: Annotated[
            int,
            Field(description="One-based space summary page number for compliance.", ge=1),
        ] = 1,
        page_size: Annotated[
            int,
            Field(description="Compliance space row page size (1-50).", ge=1, le=50),
        ] = 25,
    ) -> QueryResultModel:
        """Read compact metrics, run postprocessing, export schedules, or inspect outputs."""
        dumped_run_target = dump_target(run_target)
        if result_kind == "annual_daylight":
            from garden.radiance.metrics import summarize_annual_daylight_metrics

            return validate_output(
                QueryResultModel,
                summarize_annual_daylight_metrics(
                    garden_root=garden_root,
                    run_target=dumped_run_target,
                    run_id=run_id,
                    grid_identifier=grid_identifier,
                    metrics=metrics,
                    save_report=save_report,
                    include_values=include_values,
                ),
            )
        if result_kind == "glare":
            from garden.radiance.metrics import summarize_radiance_glare_metrics

            return validate_output(
                QueryResultModel,
                summarize_radiance_glare_metrics(
                    garden_root=garden_root,
                    run_target=dumped_run_target,
                    run_id=run_id,
                    view_identifier=view_identifier,
                    dgp_threshold=dgp_threshold,
                    save_report=save_report,
                    include_values=include_values,
                ),
            )
        if result_kind == "grid_summary":
            from garden.radiance.metrics import summarize_radiance_grid_results

            return validate_output(
                QueryResultModel,
                summarize_radiance_grid_results(
                    garden_root=garden_root,
                    run_target=dumped_run_target,
                    run_id=run_id,
                    output_name=output_name,
                    grid_filter=grid_filter,
                    save_report=save_report,
                    include_values=include_values,
                ),
            )
        if result_kind == "annual_postprocess":
            from garden.radiance.metrics import run_annual_postprocess

            return validate_output(
                QueryResultModel,
                run_annual_postprocess(
                    garden_root=garden_root,
                    run_target=dumped_run_target,
                    run_id=run_id,
                    grid_filter=grid_filter,
                    thresholds=dump_input(thresholds),
                    threshold=threshold,
                    min_threshold=min_threshold,
                    max_threshold=max_threshold,
                    target_time=target_time,
                    ase_threshold=ase_threshold,
                    ase_occ_hours=ase_occ_hours,
                    uniformity_threshold=uniformity_threshold,
                    schedule=dump_input(schedule),
                    dynamic_schedule=dump_input(dynamic_schedule),
                    hoys=hoys,
                    res_type=res_type,
                    mode=mode or "auto",
                    save_report=save_report,
                    include_values=include_values,
                ),
            )
        if result_kind == "daylight_control_schedule":
            from garden.radiance.metrics import export_daylight_control_schedules

            return validate_output(
                QueryResultModel,
                export_daylight_control_schedules(
                    garden_root=garden_root,
                    run_target=dumped_run_target,
                    run_id=run_id,
                    grid_filter=grid_filter,
                    schedule=dump_input(schedule),
                    dynamic_schedule=dump_input(dynamic_schedule),
                    ill_setpoint=ill_setpoint,
                    min_power_in=min_power_in,
                    min_light_out=min_light_out,
                    off_at_min=off_at_min,
                    identifier_prefix=identifier_prefix,
                    persist_to_garden=persist_to_garden,
                ),
            )
        if result_kind == "dynamic_schedule":
            from garden.radiance.metrics import generate_radiance_dynamic_schedule

            return validate_output(
                QueryResultModel,
                generate_radiance_dynamic_schedule(
                    garden_root=garden_root,
                    run_target=dumped_run_target,
                    run_id=run_id,
                    mode=mode or "sensor_maximum",
                    grid_filter=grid_filter,
                    sensor_index=sensor_index,
                    maximum=maximum,
                    shade_transmittance=dump_input(shade_transmittance),
                    use_states=use_states,
                    res_type=res_type,
                ),
            )
        if result_kind == "comfort_map":
            from garden.radiance.metrics import summarize_comfort_map_metrics

            return validate_output(
                QueryResultModel,
                summarize_comfort_map_metrics(
                    garden_root=garden_root,
                    run_target=dumped_run_target,
                    run_id=run_id,
                    save_report=save_report,
                    include_values=include_values,
                ),
            )
        if result_kind == "list_outputs":
            from garden.radiance.metrics import list_radiance_run_all_outputs

            return validate_output(
                QueryResultModel,
                list_radiance_run_all_outputs(
                    garden_root=garden_root,
                    run_target=dumped_run_target,
                    run_id=run_id,
                ),
            )
        from garden.radiance.compliance_results import read_daylight_compliance

        return validate_output(
            QueryResultModel,
            read_daylight_compliance(
                garden_root=garden_root,
                run_target=dumped_run_target,
                run_id=run_id,
                page=page,
                page_size=page_size,
            ),
        )

    @mcp.tool(
        name="RAD_Process_HDR_Image",
        description=(
            "Analyze or process a Radiance .hdr image artifact. Supports operations: "
            "'falsecolor' (falsecolor .hdr), 'gif' (ra_gif preview), 'png' (ra_bmp + PNG preview), "
            "'bmp' (ra_bmp preview), 'evalglare' (structured dgp, dgi, ugr, vcp, cgi, ev, glare sources "
            "+ optional check HDR), 'pcond' (human vision tone-mapping), 'pfilt' (resize/exposure filter), "
            "'pcomb' (combine/arithmetic expression on one or multiple HDRs), and 'getinfo' (header/dimensions)."
        ),
        tags={
            "artifact",
            "convert",
            "radiance",
            "image",
            "result",
        },
        timeout=120,
    )
    def process_radiance_hdr_image(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually GD_Create['garden_root']; "
                    "required when saving or reading Garden targets."
                )
            ),
        ],
        operation: Annotated[
            Literal[
                "falsecolor",
                "gif",
                "png",
                "bmp",
                "evalglare",
                "pcond",
                "pfilt",
                "pcomb",
                "getinfo",
            ],
            Field(description="HDR operation: falsecolor, gif, png, bmp, evalglare, pcond, pfilt, pcomb, or getinfo."),
        ],
        run_target: Annotated[
            RunTargetRef | None,
            Field(description="Optional completed point-in-time-view radiance_run target."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional completed view run identifier when run_target is omitted."),
        ] = None,
        image_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative .hdr image path for direct processing."),
        ] = None,
        image_paths: Annotated[
            list[str] | None,
            Field(description="Optional list of Garden-relative .hdr paths for multi-image pcomb."),
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
            Field(description="Optional falsecolor legend scale (number or Radiance auto scale)."),
        ] = None,
        legend_label: Annotated[
            str | None,
            Field(description="Optional falsecolor legend label, such as Lux or cd/m2."),
        ] = None,
        legend_multiplier: Annotated[
            float | None,
            Field(description="Optional falsecolor multiplier (-m)."),
        ] = None,
        contour_lines: Annotated[
            bool | None,
            Field(description="Optional falsecolor contour line flag (-cl)."),
        ] = None,
        contour_bands: Annotated[
            bool | None,
            Field(description="Optional falsecolor contour band flag (-cb)."),
        ] = None,
        palette: Annotated[
            str | None,
            Field(description="Optional falsecolor palette (-pal)."),
        ] = None,
        exposure: Annotated[
            str | float | int | None,
            Field(description="Optional exposure compensation (for gif, bmp/png ['auto'|'human'|'linear'|'+/-stops'], pcond, pfilt)."),
        ] = None,
        gamma: Annotated[
            float | None,
            Field(description="Optional gamma correction (for gif, bmp, png).", gt=0),
        ] = None,
        black_and_white: Annotated[
            bool | None,
            Field(description="Optional black-and-white output flag (-b) for gif, bmp, png."),
        ] = None,
        colors: Annotated[
            int | None,
            Field(description="Optional color count limit (-c) for gif.", ge=2),
        ] = None,
        sampling_factor: Annotated[
            int | None,
            Field(description="Optional sampling factor (-n) for gif.", ge=1),
        ] = None,
        detailed: Annotated[
            bool,
            Field(description="Include detailed evalglare metrics (-d, including Ev and glare sources)."),
        ] = True,
        threshold_factor: Annotated[
            float | None,
            Field(description="Optional luminance threshold factor (-b, cd/m2) for evalglare.", gt=0),
        ] = None,
        correction_mode: Annotated[
            str | None,
            Field(description="Optional evalglare luminance correction mode ('0', 'l+', or 'l-')."),
        ] = None,
        check_image: Annotated[
            bool,
            Field(description="Save evalglare glare-source check HDR (-c) artifact when true."),
        ] = False,
        check_image_name: Annotated[
            str | None,
            Field(description="Optional artifact name for evalglare check HDR."),
        ] = None,
        human_vision: Annotated[
            bool | None,
            Field(description="Apply human-vision dynamic compression (-h) for pcond."),
        ] = None,
        x_res: Annotated[
            int | None,
            Field(description="Target X pixel resolution (-x) for pfilt.", ge=1),
        ] = None,
        y_res: Annotated[
            int | None,
            Field(description="Target Y pixel resolution (-y) for pfilt.", ge=1),
        ] = None,
        radius: Annotated[
            float | None,
            Field(description="Gaussian filter radius (-r) for pfilt.", gt=0),
        ] = None,
        pixel_aspect: Annotated[
            float | None,
            Field(description="Pixel aspect ratio (-p) for pfilt.", gt=0),
        ] = None,
        expression: Annotated[
            str | None,
            Field(description="Radiance pixel expression (-e) for pcomb."),
        ] = None,
        dimensions_only: Annotated[
            bool | None,
            Field(description="Return only image resolution header (-d) for getinfo."),
        ] = None,
        additional_options: Annotated[
            str | None,
            Field(description="Optional raw Radiance CLI options string."),
        ] = None,
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative output folder for image artifacts."),
        ] = "artifacts/radiance/images",
    ) -> ArtifactResultModel:
        """Process or inspect a Radiance HDR image."""
        from garden.radiance.visual import process_radiance_hdr_image as service

        return validate_output(
            ArtifactResultModel,
            service(
                garden_root=garden_root,
                operation=operation,
                run_target=dump_target(run_target),
                run_id=run_id,
                image_path=image_path,
                image_paths=image_paths,
                image_name=image_name,
                name=name,
                scale=scale,
                legend_label=legend_label,
                legend_multiplier=legend_multiplier,
                contour_lines=contour_lines,
                contour_bands=contour_bands,
                palette=palette,
                exposure=exposure,
                gamma=gamma,
                black_and_white=black_and_white,
                colors=colors,
                sampling_factor=sampling_factor,
                detailed=detailed,
                threshold_factor=threshold_factor,
                correction_mode=correction_mode,
                check_image=check_image,
                check_image_name=check_image_name,
                human_vision=human_vision,
                x_res=x_res,
                y_res=y_res,
                radius=radius,
                pixel_aspect=pixel_aspect,
                expression=expression,
                dimensions_only=dimensions_only,
                additional_options=additional_options,
                output_subdir=output_subdir,
            ),
        )

    @mcp.tool(
        name="RAD_Grid_Result_To_Visualization_Set",
        description=(
            "Create a Ladybug Display VisualizationSet target from Radiance SensorGrid result "
            "folders using honeybee_display.model_to_vis_set(grid_data_path=...). Poll the run "
            "with GD_Poll_Run (include_outputs=true) before converting."
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
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Garden root path containing garden.json, usually GD_Create['garden_root']; "
                    "required when saving or reading Garden targets."
                )
            ),
        ],
        run_target: Annotated[
            RunTargetRef | None,
            Field(
                description=(
                    "Optional completed radiance_run target with SensorGrid result outputs. Poll "
                    "the run with GD_Poll_Run before converting result data."
                )
            ),
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
            BuildingModelTargetRef | None,
            Field(description="Optional model target override. Defaults to the model_target recorded on the run."),
        ] = None,
        color_by: Annotated[
            Literal["type", "boundary_condition", "none"] | None,
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
            Literal["Surface", "SurfaceWithEdges", "Wireframe", "Points"],
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
            Field(
                description=(
                    "Return the full VisualizationSet dict. Set false to save a compact Garden "
                    "visualization_set_target for export tools."
                )
            ),
        ] = True,
    ) -> ArtifactResultModel:
        """Create a VisualizationSet from Radiance grid results."""
        from garden.radiance.visual import radiance_grid_result_to_visualization_set as service

        return validate_output(
            ArtifactResultModel,
            service(
                garden_root=garden_root,
                run_target=dump_target(run_target),
                run_id=run_id,
                grid_data_path=grid_data_path,
                output_name=output_name,
                result_subfolder=result_subfolder,
                model_target=dump_target(model_target),
                color_by=color_by,
                include_wireframe=include_wireframe,
                use_mesh=use_mesh,
                hide_color_by=hide_color_by,
                grid_data_display_mode=grid_data_display_mode,
                active_grid_data=active_grid_data,
                name=name,
                return_visualization_set=return_visualization_set,
            ),
        )
