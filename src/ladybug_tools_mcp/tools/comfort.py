"""comfort MCP tools."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.comfort_schemas import (
    ComfortModelName,
    DataCollectionAction,
    normalize_comfort_inputs,
    normalize_data_collection_inputs,
)
from ladybug_tools_mcp.contracts import (
    ArtifactResultModel,
    DataCollectionTargetRef,
    MutationResultModel,
    WeatherTargetRef,
    dump_input,
    dump_target,
    validate_output,
)


def register(mcp: FastMCP) -> None:
    """Register comfort tools."""

    @mcp.tool(
        name="LB_Calculate_Comfort",
        description=(
            "Compute thermal comfort indices (pmv, adaptive, utci, pet, solarcal, indoor/outdoor solar MRT, "
            "passive_strategy, prevailing_temperature, clo_schiavon, local_discomfort, heat_stress) from "
            "DataCollection targets or EPW shortcuts. Returns summary_view with method/assumptions/applicable_scope."
        ),
        tags={
            "ladybug",
            "comfort",
            "thermal-comfort",
            "data-collection",
            "pmv",
            "adaptive",
            "utci",
            "passive-strategy",
            "solarcal",
            "solar-mrt",
        },
        timeout=60,
    )
    def calculate_comfort(
        garden_root: Annotated[
            str,
            Field(description="Garden root directory."),
        ],
        model: Annotated[
            ComfortModelName,
            Field(description="Thermal comfort model."),
        ],
        weather_target: Annotated[
            Any,
            Field(description="EPW weather target shortcut."),
        ] = None,
        epw_path: Annotated[
            Any,
            Field(description="EPW path shortcut."),
        ] = None,
        include_wind: Annotated[
            bool,
            Field(description="Include EPW wind speed."),
        ] = True,
        include_sun: Annotated[
            bool,
            Field(description="Include SolarCal MRT."),
        ] = True,
        location: Annotated[
            Any,
            Field(description="Location dict (SolarCal)."),
        ] = None,
        solarcal_type: Annotated[
            str,
            Field(description="outdoor, indoor, horizontal, horizontal_ref."),
        ] = "outdoor",
        direct_normal_solar_target: Annotated[
            Any,
            Field(description="Direct normal solar target (W/m2)."),
        ] = None,
        diffuse_horizontal_solar_target: Annotated[
            Any,
            Field(description="Diffuse horizontal solar target (W/m2)."),
        ] = None,
        direct_horizontal_solar_target: Annotated[
            Any,
            Field(description="Direct horizontal solar target (W/m2)."),
        ] = None,
        reflected_horizontal_solar_target: Annotated[
            Any,
            Field(description="Reflected horizontal solar target (W/m2)."),
        ] = None,
        horizontal_infrared_target: Annotated[
            Any,
            Field(description="Horizontal IR target (W/m2)."),
        ] = None,
        surface_temperatures: Annotated[
            Any,
            Field(description="Surface temp C (target/list/float)."),
        ] = None,
        longwave_mrt: Annotated[
            Any,
            Field(description="Longwave MRT C (target/list/float)."),
        ] = None,
        fraction_body_exposed: Annotated[
            Any,
            Field(description="Exposed fraction 0-1 (target/list/float)."),
        ] = None,
        sky_exposure: Annotated[
            Any,
            Field(description="Sky view 0-1 (target/list/float)."),
        ] = None,
        floor_reflectance: Annotated[
            Any,
            Field(description="Floor reflectance 0-1 (target/list/float)."),
        ] = None,
        window_transmittance: Annotated[
            Any,
            Field(description="Window transmittance 0-1 (target/list/float)."),
        ] = None,
        avg_month: Annotated[
            bool,
            Field(description="Monthly running-mean flag."),
        ] = True,
        outdoor_temperature: Annotated[
            Any,
            Field(description="Outdoor temp C (target/list/float)."),
        ] = None,
        max_clo: Annotated[
            float,
            Field(description="Max clo (clo_schiavon)."),
        ] = 1.0,
        max_clo_temp: Annotated[
            float,
            Field(description="Temp C at max_clo."),
        ] = -5.0,
        min_clo: Annotated[
            float,
            Field(description="Min clo (clo_schiavon)."),
        ] = 0.46,
        min_clo_temp: Annotated[
            float,
            Field(description="Temp C at min_clo."),
        ] = 26.0,
        local_discomfort_type: Annotated[
            str,
            Field(description="radiant_asymmetry_ppd or ankle_draft_ppd."),
        ] = "radiant_asymmetry_ppd",
        radiant_temperature_difference: Annotated[
            Any,
            Field(description="Asymmetry temp diff C (target/list/float)."),
        ] = None,
        asymmetry_type: Annotated[
            Any,
            Field(description="0/warm_ceiling..3/warm_wall."),
        ] = 0,
        predicted_mean_vote: Annotated[
            Any,
            Field(description="PMV (target/list/float)."),
        ] = None,
        air_speed_at_ankle: Annotated[
            Any,
            Field(description="Ankle air speed m/s (target/list/float)."),
        ] = None,
        heat_stress_index: Annotated[
            str,
            Field(description="wbgt, hi, humidex, wc, wc_temp, wc_index, at, di."),
        ] = "wbgt",
        dew_point_temperature_target: Annotated[
            Any,
            Field(description="Dew-point C target (humidex)."),
        ] = None,
        output_metrics: Annotated[
            Any,
            Field(description="Extra output metrics list (e.g. ['pmv','ppd','set'])."),
        ] = None,
        air_temperature_target: Annotated[
            Any,
            Field(description="Air temp C target (optional w/ EPW shortcut)."),
        ] = None,
        relative_humidity_target: Annotated[
            Any,
            Field(description="Relative humidity % target."),
        ] = None,
        mean_radiant_temperature_target: Annotated[
            Any,
            Field(description="Mean radiant temp C target (def air temp)."),
        ] = None,
        wind_speed_target: Annotated[
            Any,
            Field(description="Wind speed m/s target (def 0.5)."),
        ] = None,
        outdoor_temperature_target: Annotated[
            Any,
            Field(description="Outdoor temp C target (adaptive/night_flush)."),
        ] = None,
        operative_temperature_target: Annotated[
            Any,
            Field(description="Operative temp C target (adaptive)."),
        ] = None,
        air_speed_target: Annotated[
            Any,
            Field(description="Indoor air speed m/s target."),
        ] = None,
        air_speed: Annotated[
            Any,
            Field(description="Air speed m/s (target/list/float; def 0.1)."),
        ] = None,
        met_rate: Annotated[
            Any,
            Field(description="Metabolic rate met (target/list/float; def 1.1)."),
        ] = None,
        clo_value: Annotated[
            Any,
            Field(description="Clothing clo (target/list/float; def 0.7)."),
        ] = None,
        external_work: Annotated[
            Any,
            Field(description="External work met (target/list/float; def 0)."),
        ] = None,
        barometric_pressure: Annotated[
            Any,
            Field(description="Pressure Pa (target/float; def 101325)."),
        ] = None,
        strategies: Annotated[
            Any,
            Field(description="Passive strategies list (evaporative_cooling, night_flush, fan_use, internal_heat, passive_solar)."),
        ] = None,
        passive_strategy_parameters: Annotated[
            Any,
            Field(description="PassiveStrategyParameters dict."),
        ] = None,
        incident_irradiance_target: Annotated[
            Any,
            Field(description="Incident irradiance target (passive_solar)."),
        ] = None,
        merge_polygons: Annotated[
            bool,
            Field(description="Merge PMV polygons (passive_strategy)."),
        ] = True,
        solar_altitude: Annotated[
            Any,
            Field(description="Solar altitude deg (-90..90, scalar SolarCal)."),
        ] = None,
        direct_normal_solar: Annotated[
            Any,
            Field(description="Direct normal solar W/m2 (scalar SolarCal)."),
        ] = None,
        diffuse_horizontal_solar: Annotated[
            Any,
            Field(description="Diffuse horiz solar W/m2 (scalar SolarCal)."),
        ] = None,
        horizontal_infrared: Annotated[
            Any,
            Field(description="Horiz IR W/m2 (scalar outdoor SolarCal)."),
        ] = None,
        human_position: Annotated[
            Any,
            Field(description="Occupant Point3D ([x,y,z]/dict) for ray-tracing."),
        ] = None,
        human_height: Annotated[
            float,
            Field(description="Standing height m (def 1.8)."),
        ] = 1.8,
        human_point_count: Annotated[
            int,
            Field(description="Sample count along human_height (def 1)."),
        ] = 1,
        context_geometry: Annotated[
            Any,
            Field(description="Context Face3D/Mesh3D dicts."),
        ] = None,
        model_target: Annotated[
            Any,
            Field(description="Honeybee Model shading target."),
        ] = None,
        north_angle: Annotated[
            float,
            Field(description="North angle deg (CCW)."),
        ] = 0.0,
        sun_up_hours_path: Annotated[
            Any,
            Field(description="Sun-up-hours.txt path (map SolarCal)."),
        ] = None,
        indirect_ill_path: Annotated[
            Any,
            Field(description="indirect.ill or total.ill path (map SolarCal)."),
        ] = None,
        direct_ill_path: Annotated[
            Any,
            Field(description="direct.ill path (map SolarCal)."),
        ] = None,
        reflected_ill_path: Annotated[
            Any,
            Field(description="reflected.ill path (map SolarCal)."),
        ] = None,
        indirect_is_total: Annotated[
            bool,
            Field(description="indirect_ill_path contains total irradiance."),
        ] = False,
        comfort_parameter: Annotated[
            Any,
            Field(description="ComfortParameter dict."),
        ] = None,
        identifier: Annotated[
            Any,
            Field(description="Result identifier."),
        ] = None,
        return_data_collection: Annotated[
            bool,
            Field(description="Return full DataCollection JSON."),
        ] = False,
    ) -> MutationResultModel:
        """Calculate and persist PMV, Adaptive, UTCI, PET, SolarCal, PassiveStrategy, and thermal comfort indices."""
        from garden.comfort import calculate_comfort as service

        normalized = normalize_comfort_inputs(
            {
                "garden_root": garden_root,
                "model": model,
                "weather_target": weather_target,
                "epw_path": epw_path,
                "include_wind": include_wind,
                "include_sun": include_sun,
                "location": location,
                "solarcal_type": solarcal_type,
                "direct_normal_solar_target": direct_normal_solar_target,
                "diffuse_horizontal_solar_target": diffuse_horizontal_solar_target,
                "direct_horizontal_solar_target": direct_horizontal_solar_target,
                "reflected_horizontal_solar_target": reflected_horizontal_solar_target,
                "horizontal_infrared_target": horizontal_infrared_target,
                "surface_temperatures": surface_temperatures,
                "longwave_mrt": longwave_mrt,
                "fraction_body_exposed": fraction_body_exposed,
                "sky_exposure": sky_exposure,
                "floor_reflectance": floor_reflectance,
                "window_transmittance": window_transmittance,
                "avg_month": avg_month,
                "outdoor_temperature": outdoor_temperature,
                "max_clo": max_clo,
                "max_clo_temp": max_clo_temp,
                "min_clo": min_clo,
                "min_clo_temp": min_clo_temp,
                "local_discomfort_type": local_discomfort_type,
                "radiant_temperature_difference": radiant_temperature_difference,
                "asymmetry_type": asymmetry_type,
                "predicted_mean_vote": predicted_mean_vote,
                "air_speed_at_ankle": air_speed_at_ankle,
                "heat_stress_index": heat_stress_index,
                "dew_point_temperature_target": dew_point_temperature_target,
                "output_metrics": output_metrics,
                "air_temperature_target": air_temperature_target,
                "relative_humidity_target": relative_humidity_target,
                "mean_radiant_temperature_target": mean_radiant_temperature_target,
                "wind_speed_target": wind_speed_target,
                "outdoor_temperature_target": outdoor_temperature_target,
                "operative_temperature_target": operative_temperature_target,
                "air_speed_target": air_speed_target,
                "air_speed": air_speed,
                "met_rate": met_rate,
                "clo_value": clo_value,
                "external_work": external_work,
                "barometric_pressure": barometric_pressure,
                "strategies": strategies,
                "passive_strategy_parameters": passive_strategy_parameters,
                "incident_irradiance_target": incident_irradiance_target,
                "merge_polygons": merge_polygons,
                "solar_altitude": solar_altitude,
                "direct_normal_solar": direct_normal_solar,
                "diffuse_horizontal_solar": diffuse_horizontal_solar,
                "horizontal_infrared": horizontal_infrared,
                "human_position": human_position,
                "human_height": human_height,
                "human_point_count": human_point_count,
                "context_geometry": context_geometry,
                "model_target": model_target,
                "north_angle": north_angle,
                "sun_up_hours_path": sun_up_hours_path,
                "indirect_ill_path": indirect_ill_path,
                "direct_ill_path": direct_ill_path,
                "reflected_ill_path": reflected_ill_path,
                "indirect_is_total": indirect_is_total,
                "comfort_parameter": comfort_parameter,
                "identifier": identifier,
                "return_data_collection": return_data_collection,
            }
        )
        return validate_output(MutationResultModel, service(**normalized))

    @mcp.tool(
        name="LB_Analyze_Data_Collection",
        description=(
            "Import, create, inspect, filter, aggregate, or run math/degree_days on Garden DataCollections "
            "(action='degree_days' or operation='degree_days' under aggregate/math)."
        ),
        tags={"ladybug", "comfort", "data-collection", "degree-days"},
    )
    def analyze_data_collection(
        garden_root: Annotated[
            str,
            Field(description="Garden root directory."),
        ],
        action: Annotated[
            DataCollectionAction,
            Field(description="Operation category."),
        ],
        data_collection: Annotated[
            Any,
            Field(description="Inline DataCollection dict."),
        ] = None,
        data_collection_target: Annotated[
            Any,
            Field(description="DataCollection target dict."),
        ] = None,
        data_collections: Annotated[
            Any,
            Field(description="List of DataCollection dicts."),
        ] = None,
        data_collection_targets: Annotated[
            Any,
            Field(description="List of DataCollection targets."),
        ] = None,
        source_path: Annotated[
            Any,
            Field(description="Import path."),
        ] = None,
        values: Annotated[
            Any,
            Field(description="Values list."),
        ] = None,
        collection_type: Annotated[
            str,
            Field(description="HourlyContinuous, Daily, Monthly, MonthlyPerHour, etc."),
        ] = "HourlyContinuous",
        header: Annotated[
            Any,
            Field(description="Header dict."),
        ] = None,
        data_type: Annotated[
            Any,
            Field(description="DataType name."),
        ] = None,
        unit: Annotated[
            Any,
            Field(description="Unit string."),
        ] = None,
        analysis_period: Annotated[
            Any,
            Field(description="AnalysisPeriod."),
        ] = None,
        metadata: Annotated[
            Any,
            Field(description="Metadata dict."),
        ] = None,
        datetimes: Annotated[
            Any,
            Field(description="DateTime list."),
        ] = None,
        percentiles: Annotated[
            Any,
            Field(description="Percentiles 0-100."),
        ] = None,
        histogram_bins: Annotated[
            int,
            Field(description="Histogram bins."),
        ] = 10,
        include_values: Annotated[
            bool,
            Field(description="Include values."),
        ] = False,
        max_values: Annotated[
            int,
            Field(description="Max samples."),
        ] = 24,
        filter_type: Annotated[
            Any,
            Field(description="analysis_period, hoys, range, conditional_statement, pattern."),
        ] = None,
        hoys: Annotated[
            Any,
            Field(description="HOYs list."),
        ] = None,
        greater_than: Annotated[
            Any,
            Field(description="Lower bound."),
        ] = None,
        less_than: Annotated[
            Any,
            Field(description="Upper bound."),
        ] = None,
        conditional_statement: Annotated[
            Any,
            Field(description="Condition expr."),
        ] = None,
        pattern: Annotated[
            Any,
            Field(description="Bool/0-1 mask."),
        ] = None,
        operation: Annotated[
            Any,
            Field(description="Operation (incl. degree_days)."),
        ] = None,
        aggregation_method: Annotated[
            str,
            Field(description="average, avg, total, percentile."),
        ] = "average",
        percentile_value: Annotated[
            float,
            Field(description="Percentile 0-100."),
        ] = 50.0,
        timestep: Annotated[
            int,
            Field(description="Timestep/hr."),
        ] = 1,
        cumulative: Annotated[
            Any,
            Field(description="Cumulative bool."),
        ] = None,
        area: Annotated[
            Any,
            Field(description="Area divisor >0."),
        ] = None,
        area_unit: Annotated[
            str,
            Field(description="m2 or ft2."),
        ] = "m2",
        target_unit: Annotated[
            Any,
            Field(description="Target unit."),
        ] = None,
        scalar: Annotated[
            Any,
            Field(description="Scalar operand."),
        ] = None,
        other_data_collection: Annotated[
            Any,
            Field(description="Second DataCollection."),
        ] = None,
        other_data_collection_target: Annotated[
            Any,
            Field(description="Second target."),
        ] = None,
        base_temperature: Annotated[
            Any,
            Field(description="Single balance C."),
        ] = None,
        heating_base_temperature: Annotated[
            float,
            Field(description="Heating balance C."),
        ] = 18.0,
        cooling_base_temperature: Annotated[
            float,
            Field(description="Cooling balance C."),
        ] = 23.0,
        degree_day_type: Annotated[
            str,
            Field(description="heating, cooling, both."),
        ] = "both",
        identifier: Annotated[
            Any,
            Field(description="Identifier prefix."),
        ] = None,
        return_data_collection: Annotated[
            bool,
            Field(description="Return DataCollection."),
        ] = False,
    ) -> MutationResultModel:
        """Run DataCollection import, creation, inspection, filtering, aggregation, math, or degree_days."""
        from garden.data_collection import analyze_data_collection as service

        normalized = normalize_data_collection_inputs(
            {
                "garden_root": garden_root,
                "action": action,
                "data_collection": data_collection,
                "data_collection_target": data_collection_target,
                "data_collections": data_collections,
                "data_collection_targets": data_collection_targets,
                "source_path": source_path,
                "values": values,
                "collection_type": collection_type,
                "header": header,
                "data_type": data_type,
                "unit": unit,
                "analysis_period": analysis_period,
                "metadata": metadata,
                "datetimes": datetimes,
                "percentiles": percentiles,
                "histogram_bins": histogram_bins,
                "include_values": include_values,
                "max_values": max_values,
                "filter_type": filter_type,
                "hoys": hoys,
                "greater_than": greater_than,
                "less_than": less_than,
                "conditional_statement": conditional_statement,
                "pattern": pattern,
                "operation": operation,
                "aggregation_method": aggregation_method,
                "percentile_value": percentile_value,
                "timestep": timestep,
                "cumulative": cumulative,
                "area": area,
                "area_unit": area_unit,
                "target_unit": target_unit,
                "scalar": scalar,
                "other_data_collection": other_data_collection,
                "other_data_collection_target": other_data_collection_target,
                "base_temperature": base_temperature,
                "heating_base_temperature": heating_base_temperature,
                "cooling_base_temperature": cooling_base_temperature,
                "degree_day_type": degree_day_type,
                "identifier": identifier,
                "return_data_collection": return_data_collection,
            }
        )
        return validate_output(MutationResultModel, service(**normalized))

    @mcp.tool(
        name="LB_Climate_Calc",
        description=(
            "Pure-Python Ladybug weather, sunpath, psychrometrics, sky radiation estimation, "
            "wind profile, and magnetic declination calculations."
        ),
        tags={"ladybug", "comfort", "weather", "climate", "psychrometrics", "sunpath", "wind"},
    )
    def climate_calc(
        garden_root: Annotated[
            str,
            Field(description="Root directory of the project Garden."),
        ],
        action: Annotated[
            Literal[
                "inspect_weather",
                "translate_weather",
                "write_epw",
                "write_ddy",
                "sunpath",
                "psychrometrics",
                "skymodel",
                "wind_profile",
                "magnetic_north",
            ],
            Field(
                description=(
                    "Climate calculation action: 'inspect_weather', 'translate_weather', 'write_epw', "
                    "'write_ddy', 'sunpath', 'psychrometrics', 'skymodel', 'wind_profile', or 'magnetic_north'."
                )
            ),
        ],
        weather_target: Annotated[
            WeatherTargetRef | None,
            Field(description="Garden weather target dictionary referencing an EPW."),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(description="Path to EPW weather file."),
        ] = None,
        stat_path: Annotated[
            str | None,
            Field(description="Path to STAT weather summary file."),
        ] = None,
        ddy_path: Annotated[
            str | None,
            Field(description="Path to DDY design day file."),
        ] = None,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Ladybug Location dictionary."),
        ] = None,
        translation_type: Annotated[
            Literal[
                "epw_to_ddy",
                "epw_to_ddy_monthly_cooling",
                "epw_to_wea",
                "epw_to_mos",
                "stat_to_ddy",
                "stat_to_wea",
                "wea_from_stat",
                "wea_from_clear_sky",
                "wea_from_ashrae_revised_clear_sky",
                "ashrae_revised_clear_sky_wea",
                "wea_from_zhang_huang",
                "wea_from_zhang_huang_solar",
                "zhang_huang_solar_wea",
            ]
            | None,
            Field(
                description=(
                    "Weather translation mode: epw_to_ddy, epw_to_ddy_monthly_cooling, epw_to_wea, "
                    "epw_to_mos, stat_to_ddy, stat_to_wea, wea_from_stat, wea_from_clear_sky, "
                    "ashrae_revised_clear_sky_wea, or zhang_huang_solar_wea."
                )
            ),
        ] = None,
        percentile: Annotated[
            float,
            Field(ge=0.0, le=100.0, description="Percentile threshold for EPW-to-DDY translation (0.4 or 2.0)."),
        ] = 0.4,
        annual_percentile: Annotated[
            float,
            Field(ge=0.0, le=100.0, description="Annual heating/cooling percentile for monthly cooling DDY."),
        ] = 0.4,
        monthly_percentile: Annotated[
            float,
            Field(ge=0.0, le=100.0, description="Monthly percentile for epw_to_ddy_monthly_cooling."),
        ] = 5.0,
        hoys: Annotated[
            list[float] | None,
            Field(description="Optional hours of the year list for sunpath or WEA generation."),
        ] = None,
        timestep: Annotated[
            int,
            Field(ge=1, description="Timestep per hour for WEA or sunpath calculations."),
        ] = 1,
        is_leap_year: Annotated[
            bool,
            Field(description="Whether calculations apply to a leap year."),
        ] = False,
        use_2017: Annotated[
            bool,
            Field(description="Use ASHRAE 2017 optical depth table when generating clear-sky WEA."),
        ] = False,
        monthly_tau_beam: Annotated[
            list[float] | None,
            Field(description="12 monthly beam optical depth values for ASHRAE revised clear sky."),
        ] = None,
        monthly_tau_diffuse: Annotated[
            list[float] | None,
            Field(description="12 monthly diffuse optical depth values for ASHRAE revised clear sky."),
        ] = None,
        cloud_cover_target: Annotated[
            DataCollectionTargetRef | None,
            Field(description="Garden target for total sky cover (tenths) for Zhang-Huang."),
        ] = None,
        relative_humidity_target: Annotated[
            DataCollectionTargetRef | None,
            Field(description="Garden target for relative humidity (%) for Zhang-Huang/skymodel."),
        ] = None,
        dry_bulb_temperature_target: Annotated[
            DataCollectionTargetRef | None,
            Field(description="Garden target for dry-bulb temperature (C) for Zhang-Huang/skymodel."),
        ] = None,
        wind_speed_target: Annotated[
            DataCollectionTargetRef | None,
            Field(description="Garden target for wind speed (m/s) for Zhang-Huang."),
        ] = None,
        atmospheric_pressure_target: Annotated[
            DataCollectionTargetRef | None,
            Field(description="Garden target for barometric pressure (Pa) for skymodel."),
        ] = None,
        use_disc: Annotated[
            bool,
            Field(description="Use DISC instead of DIRINT for Zhang-Huang WEA direct/diffuse splitting."),
        ] = False,
        field_updates: Annotated[
            dict[str, Any] | None,
            Field(description="Mapping of EPW field name -> scalar or 8760 values list for action='write_epw'."),
        ] = None,
        comments_1: Annotated[
            str | None,
            Field(description="EPW header comments line 1 override for action='write_epw'."),
        ] = None,
        comments_2: Annotated[
            str | None,
            Field(description="EPW header comments line 2 override for action='write_epw'."),
        ] = None,
        register_weather_target: Annotated[
            bool,
            Field(description="Register newly written EPW in Garden weather registry."),
        ] = True,
        design_days: Annotated[
            list[dict[str, Any]] | None,
            Field(description="List of DesignDay dictionaries for action='write_ddy'."),
        ] = None,
        filter_keyword: Annotated[
            str | None,
            Field(description="Optional substring filter on design day names for action='write_ddy'."),
        ] = None,
        north_angle: Annotated[
            float,
            Field(description="Clockwise north rotation angle in degrees (-360 to 360) for sunpath."),
        ] = 0.0,
        analysis_period: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional AnalysisPeriod dict/string for sunpath calculation."),
        ] = None,
        month: Annotated[
            int | None,
            Field(ge=1, le=12, description="Month (1-12) for single-instant sunpath calculation."),
        ] = None,
        day: Annotated[
            int | None,
            Field(ge=1, le=31, description="Day of month (1-31) for single-instant sunpath calculation."),
        ] = None,
        hour: Annotated[
            float | None,
            Field(ge=0.0, le=24.0, description="Hour (0-24) for single-instant sunpath calculation."),
        ] = None,
        solar_time: Annotated[
            bool,
            Field(description="Interpret hours as true solar time instead of local standard time."),
        ] = False,
        depression: Annotated[
            float,
            Field(description="Solar depression angle (degrees) for sunrise/sunset calculation."),
        ] = 0.5334,
        operation: Annotated[
            str | None,
            Field(description="Specific function/operation name for psychrometrics or skymodel."),
        ] = None,
        inputs: Annotated[
            dict[str, Any] | None,
            Field(description="Input dictionary (scalars, lists, or Garden targets) for psychrometrics/skymodel."),
        ] = None,
        terrain: Annotated[
            Literal["city", "suburban", "country", "water", "City", "Suburban", "Country", "Water"],
            Field(description="Site terrain class for wind_profile ('city', 'suburban', 'country', 'water')."),
        ] = "city",
        meteorological_terrain: Annotated[
            Literal["city", "suburban", "country", "water", "City", "Suburban", "Country", "Water"],
            Field(description="Reference weather station terrain class for wind_profile."),
        ] = "country",
        meteorological_height: Annotated[
            float,
            Field(gt=0.0, description="Reference anemometer height (m) for wind_profile."),
        ] = 10.0,
        log_law: Annotated[
            bool,
            Field(description="Use logarithmic wind profile law instead of power law."),
        ] = False,
        wind_speed: Annotated[
            DataCollectionTargetRef | list[float] | float | None,
            Field(description="Input meteorological wind speed (scalar, list, or DataCollection/target) for wind_profile."),
        ] = None,
        height: Annotated[
            float,
            Field(gt=0.0, description="Target height above ground (m) for wind_profile."),
        ] = 1.0,
        heights: Annotated[
            list[float] | None,
            Field(description="List of heights (m) for vertical wind profile evaluation."),
        ] = None,
        latitude: Annotated[
            float | None,
            Field(ge=-90.0, le=90.0, description="Site latitude (degrees) for magnetic_north or skymodel."),
        ] = None,
        longitude: Annotated[
            float | None,
            Field(ge=-180.0, le=180.0, description="Site longitude (degrees) for magnetic_north or skymodel."),
        ] = None,
        elevation: Annotated[
            float,
            Field(description="Site elevation (m) for magnetic_north."),
        ] = 0.0,
        magnetic_north: Annotated[
            float,
            Field(description="Measured magnetic north orientation (degrees) for magnetic_north."),
        ] = 0.0,
        year: Annotated[
            float,
            Field(description="Decimal year for World Magnetic Model epoch."),
        ] = 2025.0,
        identifier: Annotated[
            str | None,
            Field(description="Optional identifier prefix for output files/targets."),
        ] = None,
        output_subdir: Annotated[
            str,
            Field(description="Relative Garden subdirectory for generated weather artifacts."),
        ] = "artifacts/weather",
        return_data_collection: Annotated[
            bool,
            Field(description="Include full serialized DataCollection payloads when applicable."),
        ] = False,
    ) -> ArtifactResultModel:
        """Run pure-Python climate, sunpath, psychrometrics, skymodel, wind, or magnetic calculations."""
        from garden.climate_calc import climate_calc as service

        result = service(
            garden_root=garden_root,
            action=action,
            weather_target=dump_target(weather_target),
            epw_path=epw_path,
            stat_path=stat_path,
            ddy_path=ddy_path,
            location=location,
            translation_type=translation_type,
            percentile=percentile,
            annual_percentile=annual_percentile,
            monthly_percentile=monthly_percentile,
            hoys=hoys,
            timestep=timestep,
            is_leap_year=is_leap_year,
            use_2017=use_2017,
            monthly_tau_beam=monthly_tau_beam,
            monthly_tau_diffuse=monthly_tau_diffuse,
            cloud_cover_target=dump_target(cloud_cover_target),
            relative_humidity_target=dump_target(relative_humidity_target),
            dry_bulb_temperature_target=dump_target(dry_bulb_temperature_target),
            wind_speed_target=dump_target(wind_speed_target),
            atmospheric_pressure_target=dump_target(atmospheric_pressure_target),
            use_disc=use_disc,
            field_updates=dump_input(field_updates),
            comments_1=comments_1,
            comments_2=comments_2,
            register_weather_target=register_weather_target,
            design_days=design_days,
            filter_keyword=filter_keyword,
            north_angle=north_angle,
            analysis_period=dump_input(analysis_period),
            month=month,
            day=day,
            hour=hour,
            solar_time=solar_time,
            depression=depression,
            operation=operation,
            inputs=dump_input(inputs),
            terrain=terrain,
            meteorological_terrain=meteorological_terrain,
            meteorological_height=meteorological_height,
            log_law=log_law,
            wind_speed=dump_input(wind_speed),
            height=height,
            heights=heights,
            latitude=latitude,
            longitude=longitude,
            elevation=elevation,
            magnetic_north=magnetic_north,
            year=year,
            identifier=identifier,
            output_subdir=output_subdir,
            return_data_collection=return_data_collection,
        )
        return validate_output(ArtifactResultModel, result)
