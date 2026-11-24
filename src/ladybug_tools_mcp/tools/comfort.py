"""comfort MCP tools."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register comfort tools."""

    @mcp.tool(
        name="LB_Calculate_Comfort",
        description=(
            "Calculate PMV, Adaptive, UTCI, PET, SolarCal (indoor/outdoor solar MRT), "
            "passive strategy comfort coverage, prevailing temperature, Schiavon clothing, "
            "local discomfort, or heat stress from Garden-backed Ladybug DataCollection targets. "
            "Select model='pmv', 'adaptive', 'utci', 'pet', 'solarcal', 'indoor_solar_mrt', "
            "'outdoor_solar_mrt', 'passive_strategy', 'prevailing_temperature', 'clo_schiavon', "
            "'local_discomfort', or 'heat_stress'."
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
            Field(description="Garden root path containing garden.json."),
        ],
        model: Annotated[
            Literal[
                "pmv",
                "adaptive",
                "utci",
                "pet",
                "solarcal",
                "passive_strategy",
                "indoor_solar_mrt",
                "outdoor_solar_mrt",
                "prevailing_temperature",
                "clo_schiavon",
                "local_discomfort",
                "heat_stress",
            ],
            Field(
                description=(
                    "Thermal comfort model or index to compute: 'pmv', 'adaptive', 'utci', 'pet', "
                    "'solarcal', 'passive_strategy', 'indoor_solar_mrt', 'outdoor_solar_mrt', "
                    "'prevailing_temperature', 'clo_schiavon', 'local_discomfort', or 'heat_stress'."
                )
            ),
        ],
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden weather target shortcut for PMV, UTCI, or PET from EPW."),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(description="Optional EPW file path shortcut for PMV, UTCI, or PET from EPW."),
        ] = None,
        include_wind: Annotated[
            bool,
            Field(description="Include EPW wind speed when computing UTCI/PET from an EPW shortcut."),
        ] = True,
        include_sun: Annotated[
            bool,
            Field(description="Include SolarCal solar MRT delta when computing UTCI/PET from an EPW shortcut."),
        ] = True,
        location: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Ladybug Location dictionary for SolarCal sun-position calculations."),
        ] = None,
        solarcal_type: Annotated[
            Literal["outdoor", "indoor", "horizontal", "horizontal_ref"],
            Field(description="SolarCal geometry variant when model='solarcal'."),
        ] = "outdoor",
        direct_normal_solar_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden target for direct normal solar irradiance (W/m2)."),
        ] = None,
        diffuse_horizontal_solar_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden target for diffuse horizontal solar irradiance (W/m2)."),
        ] = None,
        direct_horizontal_solar_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden target for direct horizontal solar irradiance (W/m2)."),
        ] = None,
        reflected_horizontal_solar_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden target for reflected horizontal solar irradiance (W/m2)."),
        ] = None,
        horizontal_infrared_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden target for horizontal infrared radiation (W/m2)."),
        ] = None,
        surface_temperatures: Annotated[
            dict[str, Any] | list[float] | float | None,
            Field(description="Longwave MRT or surrounding surface temperature(s) in C for SolarCal."),
        ] = None,
        longwave_mrt: Annotated[
            dict[str, Any] | list[float] | float | None,
            Field(description="Alias for longwave mean radiant temperature in C for SolarCal."),
        ] = None,
        fraction_body_exposed: Annotated[
            dict[str, Any] | list[float] | float | None,
            Field(description="Fraction of body exposed to direct sun (0-1) for SolarCal."),
        ] = None,
        sky_exposure: Annotated[
            dict[str, Any] | list[float] | float | None,
            Field(description="Fraction of sky dome visible to occupant (0-1) for SolarCal."),
        ] = None,
        floor_reflectance: Annotated[
            dict[str, Any] | list[float] | float | None,
            Field(description="Floor reflectance (0-1) for SolarCal."),
        ] = None,
        window_transmittance: Annotated[
            dict[str, Any] | list[float] | float | None,
            Field(description="Window transmittance (0-1) for indoor SolarCal."),
        ] = None,
        avg_month: Annotated[
            bool,
            Field(description="Use monthly running-mean averaging for prevailing_temperature model."),
        ] = True,
        outdoor_temperature: Annotated[
            float | list[float] | dict[str, Any] | None,
            Field(description="Outdoor dry-bulb temperature(s) for clo_schiavon or scalar models."),
        ] = None,
        max_clo: Annotated[
            float,
            Field(description="Maximum clothing insulation (clo) for clo_schiavon."),
        ] = 1.0,
        max_clo_temp: Annotated[
            float,
            Field(description="Temperature threshold (C) for max_clo in clo_schiavon."),
        ] = -5.0,
        min_clo: Annotated[
            float,
            Field(description="Minimum clothing insulation (clo) for clo_schiavon."),
        ] = 0.46,
        min_clo_temp: Annotated[
            float,
            Field(description="Temperature threshold (C) for min_clo in clo_schiavon."),
        ] = 26.0,
        local_discomfort_type: Annotated[
            Literal["radiant_asymmetry_ppd", "ankle_draft_ppd"],
            Field(description="Local discomfort metric when model='local_discomfort'."),
        ] = "radiant_asymmetry_ppd",
        radiant_temperature_difference: Annotated[
            float | list[float] | dict[str, Any] | None,
            Field(description="Radiant temperature asymmetry difference (C) for radiant_asymmetry_ppd."),
        ] = None,
        asymmetry_type: Annotated[
            int | str,
            Field(description="Radiant asymmetry direction (0/warm_ceiling, 1/cool_wall, 2/cool_ceiling, 3/warm_wall)."),
        ] = 0,
        predicted_mean_vote: Annotated[
            float | list[float] | dict[str, Any] | None,
            Field(description="PMV value(s) or target for ankle_draft_ppd."),
        ] = None,
        air_speed_at_ankle: Annotated[
            float | list[float] | dict[str, Any] | None,
            Field(description="Air speed at ankle height (m/s) for ankle_draft_ppd."),
        ] = None,
        heat_stress_index: Annotated[
            Literal["wbgt", "hi", "humidex", "wc", "at", "di"],
            Field(description="Heat stress index variant when model='heat_stress'."),
        ] = "wbgt",
        dew_point_temperature_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden target for dew-point temperature (C) for heat_stress humidex."),
        ] = None,
        output_metrics: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional extra output metric keys to compute and persist alongside the primary result "
                    "(e.g., ['pmv', 'ppd', 'set', 'operative_temperature', 'is_comfortable', "
                    "'thermal_condition', 'discomfort_reason', 'cooling_effect'] or SolarCal delta metrics)."
                )
            ),
        ] = None,
        air_temperature_target: Annotated[
            dict[str, Any] | None,
            Field(description="Garden ladybug_data_collection target for air temperature in C (required for pmv and utci)."),
        ] = None,
        relative_humidity_target: Annotated[
            dict[str, Any] | None,
            Field(description="Garden ladybug_data_collection target for relative humidity in % (required for pmv and utci)."),
        ] = None,
        mean_radiant_temperature_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden target for mean radiant temperature in C (pmv and utci); defaults to air temperature."),
        ] = None,
        wind_speed_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden target for meteorological wind speed in m/s (utci); defaults to 0.5 m/s."),
        ] = None,
        outdoor_temperature_target: Annotated[
            dict[str, Any] | None,
            Field(description="Garden ladybug_data_collection target for annual/prevailing outdoor temperature in C (required for adaptive)."),
        ] = None,
        operative_temperature_target: Annotated[
            dict[str, Any] | None,
            Field(description="Garden ladybug_data_collection target for operative temperature in C (required for adaptive)."),
        ] = None,
        air_speed_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden ladybug_data_collection target for indoor air speed in m/s (adaptive or pmv)."),
        ] = None,
        air_speed: Annotated[
            dict[str, Any] | list[float] | float | int | None,
            Field(description="Optional indoor air speed in m/s as a scalar, list, or Garden DataCollection target (pmv/passive_strategy); defaults to 0.1 m/s."),
        ] = None,
        met_rate: Annotated[
            dict[str, Any] | list[float] | float | int | None,
            Field(description="Optional metabolic rate in met as a scalar, list, or Garden DataCollection target (pmv/passive_strategy); defaults to 1.1 met."),
        ] = None,
        clo_value: Annotated[
            dict[str, Any] | list[float] | float | int | None,
            Field(description="Optional clothing insulation in clo as a scalar, list, or Garden DataCollection target (pmv/passive_strategy); defaults to 0.7 clo."),
        ] = None,
        external_work: Annotated[
            dict[str, Any] | list[float] | float | int | None,
            Field(description="Optional external work in met as a scalar, list, or Garden DataCollection target (pmv/passive_strategy); defaults to 0 met."),
        ] = None,
        barometric_pressure: Annotated[
            dict[str, Any] | float | int | None,
            Field(description="Optional barometric pressure in Pa (pet or passive_strategy); defaults to 101325 Pa."),
        ] = None,
        strategies: Annotated[
            list[str] | dict[str, Any] | None,
            Field(description="Passive strategies for model='passive_strategy': evaporative_cooling, night_flush, fan_use, internal_heat, passive_solar (or Grasshopper display names)."),
        ] = None,
        passive_strategy_parameters: Annotated[
            dict[str, Any] | None,
            Field(description="Optional PassiveStrategyParameters dict (day_above_comfort, night_below_comfort, fan_air_speed, balance_temperature, solar_heat_capacity, time_constant)."),
        ] = None,
        incident_irradiance_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Garden DataCollection target for incident irradiance/radiation (W/m2 or Wh/m2) used by passive_solar."),
        ] = None,
        merge_polygons: Annotated[
            bool,
            Field(description="Merge multiple PMV comfort polygons in model='passive_strategy'."),
        ] = True,
        solar_altitude: Annotated[
            float | None,
            Field(description="Optional sun altitude (0-90 deg) for scalar indoor_solar_mrt / outdoor_solar_mrt calculations."),
        ] = None,
        direct_normal_solar: Annotated[
            float | None,
            Field(description="Optional scalar direct normal irradiance (W/m2) for scalar indoor_solar_mrt / outdoor_solar_mrt."),
        ] = None,
        diffuse_horizontal_solar: Annotated[
            float | None,
            Field(description="Optional scalar diffuse horizontal irradiance (W/m2) for scalar indoor_solar_mrt / outdoor_solar_mrt."),
        ] = None,
        horizontal_infrared: Annotated[
            float | None,
            Field(description="Optional scalar horizontal infrared radiation (W/m2) for scalar outdoor_solar_mrt."),
        ] = None,
        human_position: Annotated[
            dict[str, Any] | list[float] | None,
            Field(description="Optional occupant foot Point3D ([x,y,z] or dict) to auto-compute fraction_body_exposed and sky_exposure with context_geometry/model_target."),
        ] = None,
        human_height: Annotated[
            float,
            Field(description="Standing human height (m) for human_position sky/sun relation; defaults to 1.8 m."),
        ] = 1.8,
        human_point_count: Annotated[
            int,
            Field(description="Number of sample points along human_height; defaults to 1."),
        ] = 1,
        context_geometry: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional Face3D/Mesh3D context dicts for human_position shading in indoor_solar_mrt / outdoor_solar_mrt."),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee Model target providing shading context for human_position in indoor_solar_mrt / outdoor_solar_mrt."),
        ] = None,
        north_angle: Annotated[
            float,
            Field(description="Counterclockwise north angle (degrees) for human_position sunpath calculation."),
        ] = 0.0,
        sun_up_hours_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative path to sun-up-hours.txt for Radiance map Solar MRT."),
        ] = None,
        indirect_ill_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative path to indirect.ill (or total.ill if indirect_is_total=True) for map Solar MRT."),
        ] = None,
        direct_ill_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative path to direct.ill for map Solar MRT."),
        ] = None,
        reflected_ill_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative path to reflected.ill for map Solar MRT."),
        ] = None,
        indirect_is_total: Annotated[
            bool,
            Field(description="Set True when indirect_ill_path contains total irradiance so direct_ill_path is subtracted."),
        ] = False,
        comfort_parameter: Annotated[
            dict[str, Any] | None,
            Field(description="Optional PMVParameter, AdaptiveParameter, UTCIParameter, PETParameter, or SolarCalParameter dictionary."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional stable identifier for the persisted comfort result target."),
        ] = None,
        return_data_collection: Annotated[
            bool,
            Field(description="Return the full comfort DataCollection dictionary in addition to the compact target; default false."),
        ] = False,
    ) -> dict[str, Any]:
        """Calculate and persist PMV, Adaptive, UTCI, PET, SolarCal, PassiveStrategy, and thermal comfort indices."""
        from garden.comfort import calculate_comfort as service

        return service(
            garden_root=garden_root,
            weather_target=weather_target,
            epw_path=epw_path,
            include_wind=include_wind,
            include_sun=include_sun,
            location=location,
            solarcal_type=solarcal_type,
            direct_normal_solar_target=direct_normal_solar_target,
            diffuse_horizontal_solar_target=diffuse_horizontal_solar_target,
            direct_horizontal_solar_target=direct_horizontal_solar_target,
            reflected_horizontal_solar_target=reflected_horizontal_solar_target,
            horizontal_infrared_target=horizontal_infrared_target,
            surface_temperatures=surface_temperatures,
            longwave_mrt=longwave_mrt,
            fraction_body_exposed=fraction_body_exposed,
            sky_exposure=sky_exposure,
            floor_reflectance=floor_reflectance,
            window_transmittance=window_transmittance,
            avg_month=avg_month,
            outdoor_temperature=outdoor_temperature,
            max_clo=max_clo,
            max_clo_temp=max_clo_temp,
            min_clo=min_clo,
            min_clo_temp=min_clo_temp,
            local_discomfort_type=local_discomfort_type,
            radiant_temperature_difference=radiant_temperature_difference,
            asymmetry_type=asymmetry_type,
            predicted_mean_vote=predicted_mean_vote,
            air_speed_at_ankle=air_speed_at_ankle,
            heat_stress_index=heat_stress_index,
            dew_point_temperature_target=dew_point_temperature_target,
            output_metrics=output_metrics,
            model=model,
            air_temperature_target=air_temperature_target,
            relative_humidity_target=relative_humidity_target,
            mean_radiant_temperature_target=mean_radiant_temperature_target,
            wind_speed_target=wind_speed_target,
            outdoor_temperature_target=outdoor_temperature_target,
            operative_temperature_target=operative_temperature_target,
            air_speed_target=air_speed_target,
            air_speed=air_speed,
            met_rate=met_rate,
            clo_value=clo_value,
            external_work=external_work,
            barometric_pressure=barometric_pressure,
            strategies=strategies,
            passive_strategy_parameters=passive_strategy_parameters,
            incident_irradiance_target=incident_irradiance_target,
            merge_polygons=merge_polygons,
            solar_altitude=solar_altitude,
            direct_normal_solar=direct_normal_solar,
            diffuse_horizontal_solar=diffuse_horizontal_solar,
            horizontal_infrared=horizontal_infrared,
            human_position=human_position,
            human_height=human_height,
            human_point_count=human_point_count,
            context_geometry=context_geometry,
            model_target=model_target,
            north_angle=north_angle,
            sun_up_hours_path=sun_up_hours_path,
            indirect_ill_path=indirect_ill_path,
            direct_ill_path=direct_ill_path,
            reflected_ill_path=reflected_ill_path,
            indirect_is_total=indirect_is_total,
            comfort_parameter=comfort_parameter,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )

    @mcp.tool(
        name="LB_Analyze_Data_Collection",
        description=(
            "Import, create, inspect, filter, aggregate, or perform math and degree-day "
            "calculations on Garden-backed Ladybug DataCollections."
        ),
    )
    def analyze_data_collection(
        garden_root: Annotated[
            str,
            Field(description="Root directory of the project Garden."),
        ],
        action: Annotated[
            Literal["import", "create", "inspect", "filter", "aggregate", "math"],
            Field(description="Operation category: 'import', 'create', 'inspect', 'filter', 'aggregate', or 'math'."),
        ],
        data_collection: Annotated[
            dict[str, Any] | None,
            Field(description="Inline Ladybug DataCollection dictionary."),
        ] = None,
        data_collection_target: Annotated[
            dict[str, Any] | None,
            Field(description="Garden target dictionary pointing to a persisted DataCollection."),
        ] = None,
        data_collections: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional list of inline Ladybug DataCollection dicts for batch/multi-collection operations."),
        ] = None,
        data_collection_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional list of Garden target dicts for multi-collection filtering or math."),
        ] = None,
        source_path: Annotated[
            str | None,
            Field(description="Path to CSV, JSON, or PKL data collection file for action='import'."),
        ] = None,
        values: Annotated[
            list[float] | None,
            Field(description="Numeric values list for action='create'."),
        ] = None,
        collection_type: Annotated[
            str,
            Field(description="Collection type for action='create': HourlyContinuous, HourlyDiscontinuous, Daily, Monthly, MonthlyPerHour."),
        ] = "HourlyContinuous",
        header: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Ladybug Header dictionary for action='create'."),
        ] = None,
        data_type: Annotated[
            str | None,
            Field(description="DataType name/class string for action='create' when header is omitted."),
        ] = None,
        unit: Annotated[
            str | None,
            Field(description="Unit string for action='create' when header is omitted."),
        ] = None,
        analysis_period: Annotated[
            dict[str, Any] | str | None,
            Field(description="AnalysisPeriod dict or string (e.g., '1/1 to 12/31 between 0 and 23 @1')."),
        ] = None,
        metadata: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Header metadata dictionary for action='create'."),
        ] = None,
        datetimes: Annotated[
            list[str | dict[str, Any]] | None,
            Field(description="DateTime list for discontinuous/daily/monthly collections in action='create'."),
        ] = None,
        percentiles: Annotated[
            list[float] | None,
            Field(description="Percentiles (0-100) to compute in action='inspect'."),
        ] = None,
        histogram_bins: Annotated[
            int,
            Field(description="Number of histogram bins in action='inspect'."),
        ] = 10,
        include_values: Annotated[
            bool,
            Field(description="Include sampled/truncated values in action='inspect'."),
        ] = False,
        max_values: Annotated[
            int,
            Field(description="Maximum sample values returned when include_values=True."),
        ] = 24,
        filter_type: Annotated[
            str | None,
            Field(description="Filter kind for action='filter': analysis_period, hoys, range, conditional_statement, pattern, or statement."),
        ] = None,
        hoys: Annotated[
            list[float] | None,
            Field(description="Hours of the year for filter_type='hoys'."),
        ] = None,
        greater_than: Annotated[
            float | None,
            Field(description="Lower threshold for range/conditional filters."),
        ] = None,
        less_than: Annotated[
            float | None,
            Field(description="Upper threshold for range/conditional filters."),
        ] = None,
        conditional_statement: Annotated[
            str | None,
            Field(description="Ladybug conditional statement (e.g., 'a > 20 and b < 80')."),
        ] = None,
        pattern: Annotated[
            list[bool | int] | None,
            Field(description="Boolean/0-1 mask list for filter_type='pattern'."),
        ] = None,
        operation: Annotated[
            str | None,
            Field(description="Operation name for action='aggregate' or action='math'."),
        ] = None,
        aggregation_method: Annotated[
            str,
            Field(description="Aggregation statistic: average, total, percentile, minimum, maximum."),
        ] = "average",
        percentile_value: Annotated[
            float,
            Field(description="Percentile (0-100) when aggregation_method='percentile'."),
        ] = 50.0,
        timestep: Annotated[
            int,
            Field(description="Target timestep per hour for timestep resampling in action='aggregate'."),
        ] = 1,
        cumulative: Annotated[
            bool | None,
            Field(description="Override cumulative flag during time aggregation or area normalization."),
        ] = None,
        area: Annotated[
            float | None,
            Field(description="Area divisor for normalize_by_area in action='aggregate'."),
        ] = None,
        area_unit: Annotated[
            str,
            Field(description="Area unit string ('m2' or 'ft2') for normalize_by_area."),
        ] = "m2",
        target_unit: Annotated[
            str | None,
            Field(description="Destination unit string for math operation='to_unit'."),
        ] = None,
        scalar: Annotated[
            float | None,
            Field(description="Scalar operand for math arithmetic (+, -, *, /)."),
        ] = None,
        other_data_collection: Annotated[
            dict[str, Any] | None,
            Field(description="Second inline DataCollection for aligned arithmetic in action='math'."),
        ] = None,
        other_data_collection_target: Annotated[
            dict[str, Any] | None,
            Field(description="Second Garden DataCollection target for aligned arithmetic in action='math'."),
        ] = None,
        base_temperature: Annotated[
            float | None,
            Field(description="Optional single base temperature (C) overriding heating/cooling base temperatures."),
        ] = None,
        heating_base_temperature: Annotated[
            float,
            Field(description="Heating balance temperature (C) for degree_days calculation."),
        ] = 18.0,
        cooling_base_temperature: Annotated[
            float,
            Field(description="Cooling balance temperature (C) for degree_days calculation."),
        ] = 23.0,
        degree_day_type: Annotated[
            Literal["heating", "cooling", "both"],
            Field(description="Degree-day series to compute when operation='degree_days'."),
        ] = "both",
        identifier: Annotated[
            str | None,
            Field(description="Optional identifier prefix for persisted output targets."),
        ] = None,
        return_data_collection: Annotated[
            bool,
            Field(description="Include full DataCollection JSON in response payload."),
        ] = False,
    ) -> dict[str, Any]:
        """Run DataCollection import, creation, inspection, filtering, aggregation, or math."""
        from garden.data_collection import analyze_data_collection as service

        return service(
            garden_root=garden_root,
            action=action,
            data_collection=data_collection,
            data_collection_target=data_collection_target,
            data_collections=data_collections,
            data_collection_targets=data_collection_targets,
            source_path=source_path,
            values=values,
            collection_type=collection_type,
            header=header,
            data_type=data_type,
            unit=unit,
            analysis_period=analysis_period,
            metadata=metadata,
            datetimes=datetimes,
            percentiles=percentiles,
            histogram_bins=histogram_bins,
            include_values=include_values,
            max_values=max_values,
            filter_type=filter_type,
            hoys=hoys,
            greater_than=greater_than,
            less_than=less_than,
            conditional_statement=conditional_statement,
            pattern=pattern,
            operation=operation,
            aggregation_method=aggregation_method,
            percentile_value=percentile_value,
            timestep=timestep,
            cumulative=cumulative,
            area=area,
            area_unit=area_unit,
            target_unit=target_unit,
            scalar=scalar,
            other_data_collection=other_data_collection,
            other_data_collection_target=other_data_collection_target,
            base_temperature=base_temperature,
            heating_base_temperature=heating_base_temperature,
            cooling_base_temperature=cooling_base_temperature,
            degree_day_type=degree_day_type,
            identifier=identifier,
            return_data_collection=return_data_collection,
        )

    @mcp.tool(
        name="LB_Climate_Calc",
        description=(
            "Pure-Python Ladybug weather, sunpath, psychrometrics, sky radiation estimation, "
            "wind profile, and magnetic declination calculations."
        ),
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
            dict[str, Any] | None,
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
            str | None,
            Field(
                description=(
                    "Weather translation mode: epw_to_ddy, epw_to_ddy_monthly_cooling, epw_to_wea, "
                    "epw_to_mos, stat_to_ddy, wea_from_stat, wea_from_clear_sky, or wea_from_zhang_huang."
                )
            ),
        ] = None,
        percentile: Annotated[
            float,
            Field(description="Percentile threshold for EPW-to-DDY translation (0.4 or 2.0)."),
        ] = 0.4,
        annual_percentile: Annotated[
            float,
            Field(description="Annual heating/cooling percentile for monthly cooling DDY."),
        ] = 0.4,
        monthly_percentile: Annotated[
            float,
            Field(description="Monthly percentile for epw_to_ddy_monthly_cooling."),
        ] = 5.0,
        hoys: Annotated[
            list[float] | None,
            Field(description="Optional hours of the year list for sunpath or WEA generation."),
        ] = None,
        timestep: Annotated[
            int,
            Field(description="Timestep per hour for WEA or sunpath calculations."),
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
            dict[str, Any] | None,
            Field(description="Garden target for total sky cover (tenths) for Zhang-Huang."),
        ] = None,
        relative_humidity_target: Annotated[
            dict[str, Any] | None,
            Field(description="Garden target for relative humidity (%) for Zhang-Huang/skymodel."),
        ] = None,
        dry_bulb_temperature_target: Annotated[
            dict[str, Any] | None,
            Field(description="Garden target for dry-bulb temperature (C) for Zhang-Huang/skymodel."),
        ] = None,
        wind_speed_target: Annotated[
            dict[str, Any] | None,
            Field(description="Garden target for wind speed (m/s) for Zhang-Huang."),
        ] = None,
        atmospheric_pressure_target: Annotated[
            dict[str, Any] | None,
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
            Field(description="Month (1-12) for single-instant sunpath calculation."),
        ] = None,
        day: Annotated[
            int | None,
            Field(description="Day of month (1-31) for single-instant sunpath calculation."),
        ] = None,
        hour: Annotated[
            float | None,
            Field(description="Hour (0-24) for single-instant sunpath calculation."),
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
            str,
            Field(description="Site terrain class for wind_profile ('city', 'suburban', 'country', 'ocean')."),
        ] = "city",
        meteorological_terrain: Annotated[
            str,
            Field(description="Reference weather station terrain class for wind_profile."),
        ] = "country",
        meteorological_height: Annotated[
            float,
            Field(description="Reference anemometer height (m) for wind_profile."),
        ] = 10.0,
        log_law: Annotated[
            bool,
            Field(description="Use logarithmic wind profile law instead of power law."),
        ] = False,
        wind_speed: Annotated[
            float | list[float] | dict[str, Any] | None,
            Field(description="Input meteorological wind speed (scalar, list, or DataCollection/target) for wind_profile."),
        ] = None,
        height: Annotated[
            float,
            Field(description="Target height above ground (m) for wind_profile."),
        ] = 1.0,
        heights: Annotated[
            list[float] | None,
            Field(description="List of heights (m) for vertical wind profile evaluation."),
        ] = None,
        latitude: Annotated[
            float | None,
            Field(description="Site latitude (degrees) for magnetic_north or skymodel."),
        ] = None,
        longitude: Annotated[
            float | None,
            Field(description="Site longitude (degrees) for magnetic_north or skymodel."),
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
    ) -> dict[str, Any]:
        """Run pure-Python climate, sunpath, psychrometrics, skymodel, wind, or magnetic calculations."""
        from garden.climate_calc import climate_calc as service

        return service(
            garden_root=garden_root,
            action=action,
            weather_target=weather_target,
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
            cloud_cover_target=cloud_cover_target,
            relative_humidity_target=relative_humidity_target,
            dry_bulb_temperature_target=dry_bulb_temperature_target,
            wind_speed_target=wind_speed_target,
            atmospheric_pressure_target=atmospheric_pressure_target,
            use_disc=use_disc,
            field_updates=field_updates,
            comments_1=comments_1,
            comments_2=comments_2,
            register_weather_target=register_weather_target,
            design_days=design_days,
            filter_keyword=filter_keyword,
            north_angle=north_angle,
            analysis_period=analysis_period,
            month=month,
            day=day,
            hour=hour,
            solar_time=solar_time,
            depression=depression,
            operation=operation,
            inputs=inputs,
            terrain=terrain,
            meteorological_terrain=meteorological_terrain,
            meteorological_height=meteorological_height,
            log_law=log_law,
            wind_speed=wind_speed,
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
