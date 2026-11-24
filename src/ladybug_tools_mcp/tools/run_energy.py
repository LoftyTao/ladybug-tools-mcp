"""run_energy MCP tools."""

from __future__ import annotations

import time
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.contracts import (
    ArtifactTargetRef,
    BuildingModelTargetRef,
    MutationResultModel,
    QueryResultModel,
    RunResultModel,
    RunTargetRef,
    WeatherTargetRef,
    dump_input,
    dump_target,
    make_report,
    validate_output,
)


WeatherAction = Literal["search", "import", "download", "read_data"]
SimulationParameterMode = Literal["simulation_parameter", "output_request", "inspect_measures"]
SimulationFileType = Literal["auto", "idf", "osm"]
WeatherFormat = Literal["epw", "zip", "EPW", "ZIP"]
TerrainType = Literal[
    "Ocean",
    "Country",
    "Suburbs",
    "Urban",
    "City",
    "ocean",
    "country",
    "suburbs",
    "urban",
    "city",
]
ReportingFrequency = Literal[
    "Annual",
    "Monthly",
    "Daily",
    "Hourly",
    "Timestep",
    "annual",
    "monthly",
    "daily",
    "hourly",
    "timestep",
]
SimulationUnits = Literal["si", "ip", "SI", "IP"]
SummaryPeriod = Literal["annual", "monthly", "Annual", "Monthly"]
SummaryKind = Literal[
    "energy_use",
    "loads",
    "peaks",
    "sizing",
    "load_balance",
    "unmet_hours",
    "tabular",
    "emissions",
    "generation",
    "zsz",
    "rdd",
    "osw",
]
ResultMatchMode = Literal["none", "rooms", "faces", "auto"]


def register(mcp: FastMCP) -> None:
    """Register run_energy tools."""

    @mcp.tool(
        name="LB_Manage_Weather",
        description=(
            "Manage Garden weather_file targets and EPW weather DataCollections via action: "
            "search (search registered Garden weather_file targets under imports/weather), import "
            "(copy local EPW/DDY/STAT files into the Garden "
            "and register a weather_file target), download (search and download one public EPW/ZIP "
            "weather file from epwapi/epwfile into the Garden), or read_data (read an EPW field "
            "such as dry_bulb_temperature, relative_humidity, wind_speed, or radiation into a "
            "saved Ladybug DataCollection target)."
        ),
        tags={"ladybug", "energy", "weather", "epw", "download", "search", "garden"},
        timeout=360,
    )
    def manage_weather(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        action: Annotated[
            WeatherAction,
            Field(description="Weather management action: search, import, download, or read_data."),
        ],
        query: Annotated[
            str | None,
            Field(description="Optional query string for search or download."),
        ] = None,
        source_path: Annotated[
            str | None,
            Field(
                description="For action='import': absolute local .epw file/folder path."
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional stable weather or DataCollection identifier."),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="For action='import' or 'download': overwrite an existing Garden weather folder with the same identifier."),
        ] = False,
        max_results: Annotated[
            int,
            Field(ge=1, description="For action='search': maximum number of Garden EPW matches to return."),
        ] = 10,
        require_ddy: Annotated[
            bool,
            Field(description="For action='search': only return EPW files that have a sibling DDY file."),
        ] = False,
        file_id: Annotated[
            str | None,
            Field(description="For action='download': opaque id returned by epwapi /v1/files."),
        ] = None,
        file_name: Annotated[
            str | None,
            Field(description="For action='download': exact EPW or ZIP file name."),
        ] = None,
        object_key: Annotated[
            str | None,
            Field(description="For action='download': known epwfile object key beginning with epwfile/."),
        ] = None,
        file_target: Annotated[
            dict[str, Any] | None,
            Field(description="For action='download': one file item returned by epwapi /v1/files."),
        ] = None,
        region: Annotated[
            str | None,
            Field(description="For action='download': exact epwapi region name, e.g. WMO_Region_2_Asia."),
        ] = None,
        country: Annotated[
            str | None,
            Field(description="For action='download': exact epwapi country name, e.g. CHN_China."),
        ] = None,
        admin_region: Annotated[
            str | None,
            Field(description="For action='download': exact epwapi administrative-region name."),
        ] = None,
        format: Annotated[
            WeatherFormat,
            Field(description="For action='download': archive format filter (epw or zip)."),
        ] = "zip",
        page_size: Annotated[
            int,
            Field(ge=1, le=200, description="For action='download': epwapi page_size from 1 to 200."),
        ] = 20,
        weather_target: Annotated[
            WeatherTargetRef | None,
            Field(description="For action='read_data': Garden weather_file target. Provide exactly one of weather_target or epw_path."),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(description="For action='read_data': Garden-relative or Garden-contained .epw path."),
        ] = None,
        data_type: Annotated[
            str | list[str],
            Field(
                description=(
                    "For action='read_data': EPW field string or list of field strings for batch "
                    "extraction, e.g. dry_bulb_temperature, wet_bulb_temperature, relative_humidity, "
                    "wind_speed, global_horizontal_radiation, years, present_weather_codes, "
                    "or present_weather_observation."
                )
            ),
        ] = "dry_bulb_temperature",
        analysis_period: Annotated[
            dict[str, Any] | str | None,
            Field(description="For action='read_data': optional Ladybug AnalysisPeriod dict or string."),
        ] = None,
        include_values: Annotated[
            bool,
            Field(description="For action='read_data': include bounded raw values in summary."),
        ] = False,
        max_values: Annotated[
            int,
            Field(ge=0, description="For action='read_data': maximum raw values returned in summary when include_values is true."),
        ] = 24,
        return_data_collection: Annotated[
            bool,
            Field(description="For action='read_data': return the full Ladybug DataCollection dict."),
        ] = False,
    ) -> MutationResultModel:
        """Search, import, download, or read EPW weather data in a Garden."""
        if action == "search":
            from garden.run_energy.config import search_weather_files as service

            return validate_output(
                MutationResultModel,
                service(
                    garden_root=garden_root,
                    query=query,
                    max_results=max_results,
                    require_ddy=require_ddy,
                ),
            )
        if action == "import":
            if not source_path:
                raise ValueError("source_path is required when action='import'.")
            from garden.run_energy.config import import_local_weather_folder as service

            return validate_output(
                MutationResultModel,
                service(
                    garden_root=garden_root,
                    source_path=source_path,
                    identifier=identifier,
                    overwrite=overwrite,
                ),
            )
        if action == "download":
            from garden.run_energy.weather_download import download_weather as service

            return validate_output(
                MutationResultModel,
                service(
                    garden_root=garden_root,
                    query=query,
                    file_id=file_id,
                    file_name=file_name,
                    object_key=object_key,
                    file_target=dump_input(file_target),
                    region=region,
                    country=country,
                    admin_region=admin_region,
                    file_format=format,
                    page_size=page_size,
                    overwrite=overwrite,
                ),
            )
        if action == "read_data":
            from garden.run_energy.weather_data import read_weather_file_data as service

            return validate_output(
                MutationResultModel,
                service(
                    garden_root=garden_root,
                    weather_target=dump_target(weather_target),
                    epw_path=epw_path,
                    data_type=data_type,
                    analysis_period=dump_input(analysis_period),
                    identifier=identifier,
                    include_values=include_values,
                    max_values=max_values,
                    return_data_collection=return_data_collection,
                ),
            )
        raise ValueError(f"Unsupported weather action: {action!r}.")

    @mcp.tool(
        name="EP_Create_Simulation_Parameter",
        description=(
            "Create and persist a reusable Honeybee Energy SimulationParameter target (or an "
            "energy_output_request target when mode='output_request', or inspect OpenStudio "
            "measures when mode='inspect_measures') for EP_Start_Simulation. Supports "
            "run_period, holidays, daylight_saving_time, timestep, north_angle, terrain_type, "
            "simulation_control, design_days (DDY strategies or DesignDay dicts), sizing "
            "factors, shadow_calculation settings, plus either an existing output_request_target "
            "or inline output request settings (14 SimulationOutput presets, custom_outputs, "
            "summary_reports, reporting_frequency, include_sqlite, include_html, "
            "unmet_setpoint_tolerance)."
        ),
        tags={"energy", "energyplus", "author", "parameter", "simulation", "report", "measures"},
        timeout=20,
    )
    def create_simulation_parameter(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        mode: Annotated[
            SimulationParameterMode,
            Field(description="Create a simulation_parameter target, an energy_output_request target, or inspect OpenStudio measures."),
        ] = "simulation_parameter",
        identifier: Annotated[
            str | None,
            Field(description="Stable identifier for the saved target (required when mode='output_request')."),
        ] = None,
        run_period: Annotated[
            dict[str, Any] | None,
            Field(description="Optional task-level period with start_month, start_day, end_month, end_day, and optional start_day_of_week/leap_year/holidays/daylight_saving_time."),
        ] = None,
        design_days: Annotated[
            list[str | dict[str, Any]] | str | dict[str, Any] | None,
            Field(description="Optional DDY strategies (all, heating, cooling, heating_99.6, heating_99, cooling_0.4, cooling_1, 99.6/0.4, 99/1) and/or direct Ladybug DesignDay dicts."),
        ] = None,
        sizing: Annotated[
            dict[str, Any] | None,
            Field(description="Optional sizing settings such as heating_factor, cooling_factor, efficiency_standard, climate_zone, building_type, and bypass_efficiency_sizing."),
        ] = None,
        shadow_calculation: Annotated[
            dict[str, Any] | None,
            Field(description="Optional EnergyPlus shadow settings such as solar_distribution, calculation_method, calculation_update_method, calculation_frequency, and maximum_figures."),
        ] = None,
        timestep: Annotated[
            int | None,
            Field(ge=1, le=60, description="Optional timesteps per hour (1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, or 60)."),
        ] = None,
        north_angle: Annotated[
            float | None,
            Field(ge=-360, le=360, description="Optional clockwise north rotation angle in degrees (-360 to 360)."),
        ] = None,
        terrain_type: Annotated[
            TerrainType | None,
            Field(description="Optional site terrain type: Ocean, Country, Suburbs, Urban, or City."),
        ] = None,
        simulation_control: Annotated[
            dict[str, Any] | None,
            Field(description="Optional SimulationControl dict (do_zone_sizing, do_system_sizing, do_plant_sizing, run_for_sizing_periods, run_for_run_periods)."),
        ] = None,
        holidays: Annotated[
            list[Any] | None,
            Field(description="Optional list of holiday dates as [month, day], {month, day}, or 'MM/DD'."),
        ] = None,
        daylight_saving_time: Annotated[
            dict[str, Any] | None,
            Field(description="Optional DaylightSavingTime dict with start_date/end_date ([month, day]) or start_month/start_day/end_month/end_day."),
        ] = None,
        measure_folder: Annotated[
            str | None,
            Field(description="For mode='inspect_measures': optional OpenStudio measure folder (or parent folder) inside Garden or LBT measures."),
        ] = None,
        measures_path: Annotated[
            str | None,
            Field(description="For mode='inspect_measures': optional alias for measure_folder."),
        ] = None,
        measures: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="For mode='inspect_measures': optional list of {folder, arguments} specs or folder strings to inspect and validate."),
        ] = None,
        output_request_target: Annotated[
            ArtifactTargetRef | None,
            Field(description="Optional existing energy_output_request target."),
        ] = None,
        output_request: Annotated[
            dict[str, Any] | None,
            Field(description="Optional inline output request dictionary with presets, custom_outputs, summary_reports, reporting_frequency, include_sqlite, include_html, and/or unmet_setpoint_tolerance."),
        ] = None,
        presets: Annotated[
            list[str] | None,
            Field(description="Optional named output presets: zone_energy_use, hvac_energy_use, unmet_hours, surface_temperature, surface_energy_flow, glazing_solar, comfort_metrics, energy_balance, gains_and_losses, electricity_generation, plant_temperatures, plant_variables, stratification, or comfort_map."),
        ] = None,
        custom_outputs: Annotated[
            list[str] | None,
            Field(description="Optional exact EnergyPlus Output:Variable names to request."),
        ] = None,
        summary_reports: Annotated[
            list[str] | None,
            Field(description="Optional EnergyPlus summary reports such as AllSummary or AnnualBuildingUtilityPerformanceSummary."),
        ] = None,
        reporting_frequency: Annotated[
            ReportingFrequency,
            Field(description="EnergyPlus reporting frequency for output variables: Annual, Monthly, Daily, Hourly, or Timestep."),
        ] = "Hourly",
        include_sqlite: Annotated[
            bool,
            Field(description="Whether the simulation should write a SQLite result file for DataCollection result reading."),
        ] = True,
        include_html: Annotated[
            bool,
            Field(description="Whether the simulation should write an HTML summary report."),
        ] = True,
        unmet_setpoint_tolerance: Annotated[
            float,
            Field(ge=0.0, le=10.0, description="Unmet setpoint tolerance in degrees Celsius."),
        ] = 1.11,
        weather_target: Annotated[
            WeatherTargetRef | None,
            Field(description="Optional weather_file target with ddy_path; when supplied, design_days strategies are resolved during creation."),
        ] = None,
        include_body: Annotated[
            bool,
            Field(description="Return the full SDK SimulationParameter dictionary when mode='simulation_parameter'."),
        ] = False,
    ) -> MutationResultModel:
        """Create a reusable Energy SimulationParameter, energy_output_request target, or inspect OpenStudio measures."""
        from garden.run_energy.annual import inspect_openstudio_measures
        from garden.run_energy.output_requests import (
            create_energy_output_request as output_request_service,
        )
        from garden.run_energy.parameters import (
            create_simulation_parameter as parameter_service,
        )

        if mode == "inspect_measures":
            return validate_output(
                MutationResultModel,
                inspect_openstudio_measures(
                    garden_root=garden_root,
                    measure_folder=measure_folder,
                    measures_path=measures_path,
                    measures=measures,
                ),
            )

        allowed_output_keys = {
            "identifier",
            "presets",
            "custom_outputs",
            "summary_reports",
            "reporting_frequency",
            "include_sqlite",
            "include_html",
            "unmet_setpoint_tolerance",
        }
        inline_output_kwargs: dict[str, Any] = {}
        if output_request is not None:
            if not isinstance(output_request, dict):
                raise ValueError("output_request must be a dictionary.")
            unknown = sorted(set(output_request) - allowed_output_keys)
            if unknown:
                raise ValueError(
                    f"output_request contains unsupported field(s): {', '.join(unknown)}."
                )
            if presets is not None or custom_outputs is not None or summary_reports is not None:
                raise ValueError(
                    "Pass output settings either inside output_request or as top-level presets/custom_outputs/summary_reports, not both."
                )
            inline_output_kwargs = dict(output_request)
        else:
            if presets is not None:
                inline_output_kwargs["presets"] = presets
            if custom_outputs is not None:
                inline_output_kwargs["custom_outputs"] = custom_outputs
            if summary_reports is not None:
                inline_output_kwargs["summary_reports"] = summary_reports
            if reporting_frequency != "Hourly":
                inline_output_kwargs["reporting_frequency"] = reporting_frequency
            if include_sqlite is not True:
                inline_output_kwargs["include_sqlite"] = include_sqlite
            if include_html is not True:
                inline_output_kwargs["include_html"] = include_html
            if abs(float(unmet_setpoint_tolerance) - 1.11) > 1e-9:
                inline_output_kwargs["unmet_setpoint_tolerance"] = unmet_setpoint_tolerance

        if mode == "output_request":
            if any(
                value is not None
                for value in (
                    run_period,
                    design_days,
                    sizing,
                    shadow_calculation,
                    timestep,
                    north_angle,
                    terrain_type,
                    simulation_control,
                    holidays,
                    daylight_saving_time,
                    measure_folder,
                    measures_path,
                    measures,
                    output_request_target,
                )
            ):
                raise ValueError(
                    "SimulationParameter and measure fields are not valid when mode='output_request'."
                )
            req_identifier = inline_output_kwargs.pop("identifier", None) or identifier
            if not req_identifier:
                raise ValueError("identifier is required when mode='output_request'.")
            return validate_output(
                MutationResultModel,
                output_request_service(
                    garden_root=garden_root,
                    identifier=str(req_identifier),
                    presets=inline_output_kwargs.get("presets"),
                    custom_outputs=inline_output_kwargs.get("custom_outputs"),
                    summary_reports=inline_output_kwargs.get("summary_reports"),
                    reporting_frequency=str(inline_output_kwargs.get("reporting_frequency", reporting_frequency)),
                    include_sqlite=bool(inline_output_kwargs.get("include_sqlite", include_sqlite)),
                    include_html=bool(inline_output_kwargs.get("include_html", include_html)),
                    unmet_setpoint_tolerance=float(
                        inline_output_kwargs.get("unmet_setpoint_tolerance", unmet_setpoint_tolerance)
                    ),
                ),
            )

        if any(value is not None for value in (measure_folder, measures_path, measures)):
            raise ValueError(
                "measure_folder, measures_path, and measures are only valid when mode='inspect_measures'."
            )

        resolved_output_request_target = dump_target(output_request_target)
        if inline_output_kwargs or output_request is not None:
            if resolved_output_request_target is not None:
                raise ValueError(
                    "Provide either output_request_target or inline output_request/output settings, not both."
                )
            req_identifier = (
                inline_output_kwargs.pop("identifier", None)
                or f"{identifier or 'simulation_parameter'}_outputs"
            )
            created_req = output_request_service(
                garden_root=garden_root,
                identifier=str(req_identifier),
                presets=inline_output_kwargs.get("presets"),
                custom_outputs=inline_output_kwargs.get("custom_outputs"),
                summary_reports=inline_output_kwargs.get("summary_reports"),
                reporting_frequency=str(inline_output_kwargs.get("reporting_frequency", reporting_frequency)),
                include_sqlite=bool(inline_output_kwargs.get("include_sqlite", include_sqlite)),
                include_html=bool(inline_output_kwargs.get("include_html", include_html)),
                unmet_setpoint_tolerance=float(
                    inline_output_kwargs.get("unmet_setpoint_tolerance", unmet_setpoint_tolerance)
                ),
            )
            resolved_output_request_target = created_req["target"]

        result = parameter_service(
            garden_root=garden_root,
            identifier=identifier,
            run_period=run_period,
            design_days=design_days,
            sizing=sizing,
            shadow_calculation=shadow_calculation,
            timestep=timestep,
            north_angle=north_angle,
            terrain_type=terrain_type,
            simulation_control=simulation_control,
            holidays=holidays,
            daylight_saving_time=daylight_saving_time,
            output_request_target=resolved_output_request_target,
            weather_target=dump_target(weather_target),
            include_body=include_body,
        )
        if resolved_output_request_target is not None:
            result["output_request_target"] = resolved_output_request_target
            result.setdefault("summary_view", {})["output_request_target"] = resolved_output_request_target
        return validate_output(MutationResultModel, result)

    @mcp.tool(
        name="EP_Start_Simulation",
        description=(
            "Start a Honeybee Energy annual-energy-use simulation for a Garden Honeybee model "
            "with Garden-managed EPW/DDY weather. By default starts asynchronously and returns "
            "run_target, energy_run_target, worker_pid, and poll_next (pointing to GD_Poll_Run). "
            "Pass wait_seconds > 0 to wait and poll up to wait_seconds before returning. Accepts "
            "either simulation_parameter_target from EP_Create_Simulation_Parameter or inline "
            "sim_par, optional output_request_target, additional_idf_path/additional_idf_text, "
            "and measures_path."
        ),
        tags={"energy", "simulate", "epw", "poll", "start"},
        timeout=3600,
    )
    def start_energy_run(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        weather_target: Annotated[
            WeatherTargetRef | None,
            Field(
                description="Garden weather file target returned by LB_Manage_Weather, or a Garden-relative EPW path."
            ),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Optional Honeybee model target with target_type=honeybee_model. Defaults to the Garden base model."),
        ] = None,
        sim_par: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee Energy SimulationParameter dictionary. Mutually exclusive with simulation_parameter_target."),
        ] = None,
        simulation_parameter_target: Annotated[
            ArtifactTargetRef | None,
            Field(description="Optional reusable simulation_parameter target returned by EP_Create_Simulation_Parameter. Mutually exclusive with sim_par."),
        ] = None,
        output_request_target: Annotated[
            ArtifactTargetRef | None,
            Field(description="Optional energy_output_request target returned by EP_Create_Simulation_Parameter(mode='output_request')."),
        ] = None,
        additional_idf_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative path to an additional EnergyPlus .idf file."),
        ] = None,
        additional_idf_text: Annotated[
            str | None,
            Field(description="Optional inline additional EnergyPlus IDF text. Mutually exclusive with additional_idf_path."),
        ] = None,
        measures_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative path to an OpenStudio measures folder (containing workflow.osw) for the annual-energy-use recipe."),
        ] = None,
        measures: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional ordered list of OpenStudio measures [{folder, arguments}] or measure folder strings built into workflow.osw."),
        ] = None,
        measures_only: Annotated[
            bool,
            Field(description="Run OpenStudio measures only (-m) without running EnergyPlus."),
        ] = False,
        inspect_measures: Annotated[
            bool,
            Field(description="When true, inspect measures/measures_path via honeybee_energy.measure.Measure and return metadata/arguments without starting a simulation."),
        ] = False,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier. Omit to generate one."),
        ] = None,
        units: Annotated[
            SimulationUnits,
            Field(description="EUI units for EnergyPlus result summaries: si or ip."),
        ] = "si",
        workers: Annotated[
            int | None,
            Field(ge=1, description="Optional recipe worker count."),
        ] = None,
        reload_old: Annotated[
            bool,
            Field(description="Reload existing completed run ledger entry for matching run_id without starting a new background run."),
        ] = False,
        silent: Annotated[
            bool,
            Field(description="Run OpenStudio/EnergyPlus silently."),
        ] = True,
        validate_weather: Annotated[
            bool,
            Field(description="Validate EPW/DDY with the Ladybug SDK before launching the background recipe."),
        ] = True,
        wait_seconds: Annotated[
            float | None,
            Field(description="Optional wrapper-side wait duration in seconds to poll until completion or timeout (omit or <= 0 for immediate nonblocking return)."),
        ] = None,
        poll_interval: Annotated[
            float,
            Field(gt=0, description="Wrapper-side polling interval in seconds when wait_seconds > 0."),
        ] = 2.0,
    ) -> RunResultModel:
        """Start annual energy-use simulation and optionally wait for completion."""
        from garden.run_energy.annual import (
            get_energy_run,
            inspect_openstudio_measures,
            start_energy_run as service,
        )

        if inspect_measures:
            return validate_output(
                RunResultModel,
                inspect_openstudio_measures(
                    garden_root=garden_root,
                    measures_path=measures_path,
                    measures=measures,
                ),
            )

        result = service(
            garden_root=garden_root,
            weather_target=dump_target(weather_target),
            model_target=dump_target(model_target),
            sim_par=dump_input(sim_par),
            simulation_parameter_target=dump_target(simulation_parameter_target),
            output_request_target=dump_target(output_request_target),
            additional_idf_path=additional_idf_path,
            additional_idf_text=additional_idf_text,
            measures_path=measures_path,
            measures=dump_input(measures),
            measures_only=measures_only,
            run_id=run_id,
            units=units,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            validate_weather=validate_weather,
        )
        requested_wait = max(float(wait_seconds or 0.0), 0.0)
        if requested_wait > 0.0:
            applied_wait = min(requested_wait, 3500.0)
            interval = max(float(poll_interval or 2.0), 0.2)
            deadline = time.monotonic() + applied_wait
            status = result.get("status") or result.get("summary_view", {}).get("status")
            while status in {"queued", "running"} and time.monotonic() < deadline:
                time.sleep(min(interval, max(deadline - time.monotonic(), 0.0)))
                polled = get_energy_run(
                    garden_root=garden_root,
                    run_target=result.get("run_target"),
                    run_id=result.get("run_id"),
                )
                status = polled.get("status")
                result["status"] = status
                result["outputs"] = polled.get("outputs")
                result["result_evidence"] = polled.get("result_evidence")
                result["final_answer_ready"] = polled.get("final_answer_ready")
                summary = result.setdefault("summary_view", {})
                summary["status"] = status
                summary["outputs"] = polled.get("summary_view", {}).get("run", {}).get("outputs") or summary.get("outputs")
                summary["result_evidence"] = polled.get("result_evidence")
                summary["final_answer_ready"] = polled.get("final_answer_ready")
                summary["recommended_next_tools"] = polled.get("summary_view", {}).get("recommended_next_tools")
                if status not in {"queued", "running"}:
                    result["report"] = make_report(
                        status="ok" if status == "completed" else "error",
                        message=(
                            "Annual energy-use simulation completed."
                            if status == "completed"
                            else f"Annual energy-use simulation ended with status: {status}."
                        ),
                    )
                    break
            summary = result.setdefault("summary_view", {})
            summary["wait_seconds_requested"] = wait_seconds
            summary["wait_seconds_applied"] = applied_wait
        return validate_output(RunResultModel, result)

    @mcp.tool(
        name="EP_Run_Simulation_File",
        description=(
            "Run a user-edited EnergyPlus .idf file or OpenStudio .osm file inside a Garden. "
            "When file_type='auto', the tool infers idf vs osm from file_path extension. Runs in "
            "blocking mode and records an energy_run target in the run ledger. Returns run_target, "
            "energy_run_target, runtime_status through summary_view.status, and report."
        ),
        tags={"energy", "simulate", "idf", "osm", "file", "blocking"},
        timeout=3600,
    )
    def run_simulation_file(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        file_path: Annotated[
            str,
            Field(description="Garden-relative or Garden-contained absolute path to the edited .idf or .osm file."),
        ],
        file_type: Annotated[
            SimulationFileType,
            Field(description="Simulation file type: auto (infer from extension), idf, or osm."),
        ] = "auto",
        weather_target: Annotated[
            WeatherTargetRef | None,
            Field(description="Optional Garden weather_file target returned by LB_Manage_Weather. Use instead of epw_path."),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative EPW path. Omit only for design-day-only IDF simulations."),
        ] = None,
        expand_objects: Annotated[
            bool,
            Field(description="For IDF files: expand EnergyPlus HVAC Template objects before simulation."),
        ] = True,
        measures: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="For OSM files: optional ordered list of OpenStudio measures [{folder, arguments}] or measure folder strings."),
        ] = None,
        measures_only: Annotated[
            bool,
            Field(description="For OSM files: run OpenStudio measures only (-m) without running EnergyPlus."),
        ] = False,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier. Omit to generate one."),
        ] = None,
        silent: Annotated[
            bool,
            Field(description="Run EnergyPlus/OpenStudio silently."),
        ] = True,
    ) -> RunResultModel:
        """Run an edited IDF or OSM file and register an energy_run target."""
        from garden.run_energy.files import run_simulation_file as service

        return validate_output(
            RunResultModel,
            service(
                garden_root=garden_root,
                file_path=file_path,
                file_type=file_type,
                weather_target=dump_target(weather_target),
                epw_path=epw_path,
                expand_objects=expand_objects,
                measures=dump_input(measures),
                measures_only=measures_only,
                run_id=run_id,
                silent=silent,
            ),
        )

    @mcp.tool(
        name="EP_Summarize_Results",
        description=(
            "Summarize one completed Garden energy_run by intent: energy_use (whole-building EUI "
            "from eui.json), loads (annual or monthly SQL end-use loads without double-counting), "
            "peaks (max zone design load plus coincident building peak from ZSZ/hourly SQL), "
            "sizing (compact zone and HVAC component sizing), load_balance (thermal LoadBalance), "
            "unmet_hours (SQL tabular + hourly), tabular (SQLiteResult tabular listing/read), "
            "emissions (operational carbon), generation (on-site PV/electricity), zsz (ZSZ profiles), "
            "rdd (discoverable RDD output variable names), or osw (OpenStudio measure workflow logs). "
            "Use EP_Read_Result_Data for raw SQL/DataCollection access and model geometry matching."
        ),
        tags={"energy", "result", "summary", "loads", "peaks", "eui", "sizing", "tabular"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def summarize_energy_results(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json and the energy_run target."),
        ],
        summary_kind: Annotated[
            SummaryKind,
            Field(description="Summary intent: energy_use, loads, peaks, sizing, load_balance, unmet_hours, tabular, emissions, generation, zsz, rdd, or osw."),
        ] = "energy_use",
        run_target: Annotated[
            RunTargetRef | None,
            Field(description="Energy run target returned by EP_Start_Simulation or EP_Run_Simulation_File."),
        ] = None,
        energy_run_target: Annotated[
            RunTargetRef | None,
            Field(description="Alias for run_target."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target and energy_run_target are omitted."),
        ] = None,
        scope: Annotated[
            str | dict[str, Any] | None,
            Field(description="Optional zone, room, table, or output-name substring scope."),
        ] = None,
        period: Annotated[
            SummaryPeriod,
            Field(description="Requested time range for time-series summaries: annual or monthly."),
        ] = "annual",
        unit_preference: Annotated[
            str | None,
            Field(description="Optional target unit such as kWh, MWh, W, or kW."),
        ] = None,
        zone: Annotated[
            str | None,
            Field(description="For sizing/unmet_hours/zsz: optional zone-name substring filter."),
        ] = None,
        component: Annotated[
            str | None,
            Field(description="For summary_kind='sizing': optional component-name substring filter."),
        ] = None,
        sizing_category: Annotated[
            str | None,
            Field(description="For summary_kind='sizing': optional category filter (zone, component, heating, or cooling)."),
        ] = None,
        max_results: Annotated[
            int,
            Field(ge=1, description="Maximum compact records/rows/outputs to return for sizing, tabular, rdd, or zsz."),
        ] = 50,
        table_name: Annotated[
            str | None,
            Field(description="For summary_kind='tabular': exact SQL summary table name (omit to list tables)."),
        ] = None,
        report_name: Annotated[
            str | None,
            Field(description="For summary_kind='tabular': optional EnergyPlus report name filter."),
        ] = None,
        j_to_kwh: Annotated[
            bool,
            Field(description="For summary_kind='tabular': convert MJ/GJ tabular cells to kWh."),
        ] = True,
        electricity_emissions: Annotated[
            float | None,
            Field(description="For summary_kind='emissions': electric grid emissions in kg CO2/MWh (auto-inferred for US locations when omitted)."),
        ] = None,
        emissions_year: Annotated[
            int,
            Field(ge=2020, le=2050, description="For summary_kind='emissions': future US eGrid year (even year 2020-2050) when electricity_emissions is omitted."),
        ] = 2030,
        include_values: Annotated[
            bool,
            Field(description="For summary_kind='zsz': include bounded hourly/sub-hourly profile values."),
        ] = False,
        max_values: Annotated[
            int,
            Field(ge=0, description="For summary_kind='zsz': maximum values per zone profile when include_values is true."),
        ] = 24,
    ) -> QueryResultModel:
        """Return a compact intent-driven Energy result summary."""
        from garden.run_energy.summary import summarize_energy_results as service

        return validate_output(
            QueryResultModel,
            service(
                garden_root=garden_root,
                run_target=dump_target(run_target),
                energy_run_target=dump_target(energy_run_target),
                run_id=run_id,
                summary_kind=summary_kind,
                scope=dump_input(scope),
                period=period,
                unit_preference=unit_preference,
                zone=zone,
                component=component,
                sizing_category=sizing_category,
                max_results=max_results,
                table_name=table_name,
                report_name=report_name,
                j_to_kwh=j_to_kwh,
                electricity_emissions=electricity_emissions,
                emissions_year=emissions_year,
                include_values=include_values,
                max_values=max_values,
            ),
        )

    @mcp.tool(
        name="EP_Read_Result_Data",
        description=(
            "Read EnergyPlus SQL results from a completed Garden energy_run as compact Ladybug "
            "DataCollection summaries with result_context provenance. Use output names from "
            "GD_Poll_Run (outputs) or SQL output inventory filters. Without "
            "output_name/output_names/filters, returns available_outputs only. With "
            "save_data_collections=true, returns data_collection_targets and "
            "summary_view.first_data_collection_target for visualization tools. Optionally pass "
            "match_to='rooms'|'faces'|'auto' to match DataCollections to Honeybee Model rooms/faces."
        ),
        tags={"energy", "result", "sql", "data-collection"},
        timeout=60,
    )
    def read_energy_result_data(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        run_target: Annotated[
            RunTargetRef | None,
            Field(description="Energy run target returned by EP_Start_Simulation; pass run_target unless you provide run_id."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        output_name: Annotated[
            str | None,
            Field(description="Optional exact EnergyPlus SQL output name to read as DataCollections. Omit to list or filter available SQL outputs."),
        ] = None,
        output_names: Annotated[
            list[str] | None,
            Field(description="Optional exact EnergyPlus SQL output names to read in one call for multi-series charts. Provide only one of output_name or output_names."),
        ] = None,
        output_query: Annotated[
            str | None,
            Field(description="Optional case-insensitive substring query for SQL output names, used when output_name and output_names are omitted."),
        ] = None,
        unit: Annotated[
            str | None,
            Field(description="Optional exact unit filter for SQL outputs, for example kWh, kW, C, or %."),
        ] = None,
        data_type: Annotated[
            str | None,
            Field(description="Optional exact Ladybug data_type filter for SQL outputs, for example Energy, Power, Temperature, or Fraction."),
        ] = None,
        object_type: Annotated[
            str | None,
            Field(description="Optional case-insensitive object_type filter from SQL output metadata, for example Zone or System."),
        ] = None,
        run_period_index: Annotated[
            int | None,
            Field(ge=0, description="Optional EnergyPlus run period index."),
        ] = None,
        include_values: Annotated[
            bool,
            Field(description="Whether to include bounded raw values from each DataCollection. Default false for compact responses."),
        ] = False,
        max_values: Annotated[
            int,
            Field(ge=0, description="Maximum values per DataCollection when include_values is true."),
        ] = 24,
        max_collections: Annotated[
            int,
            Field(ge=1, description="Maximum DataCollection summaries to return."),
        ] = 10,
        max_outputs: Annotated[
            int,
            Field(ge=1, description="Maximum SQL outputs selected by output_query/unit/data_type/object_type filters."),
        ] = 25,
        save_data_collections: Annotated[
            bool,
            Field(description="Persist each returned DataCollection as a Garden ladybug_data_collection target and return data_collection_targets. Keep false for inventory-only reads; set true with include_values=false before passing targets into generic visualize tools."),
        ] = False,
        match_to: Annotated[
            ResultMatchMode,
            Field(description="Optional Honeybee geometry matching via honeybee_energy.result.match: none, rooms, faces, or auto."),
        ] = "none",
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Optional Honeybee model_target used when match_to != 'none' (defaults to the run's model or Garden base model)."),
        ] = None,
        invert_multiplier: Annotated[
            bool,
            Field(description="For match_to='rooms': invert room multiplier handling in match_rooms_to_data."),
        ] = False,
        space_based: Annotated[
            bool,
            Field(description="For match_to='rooms': match EnergyPlus Space-level outputs instead of Zone-level."),
        ] = False,
        zone_correct_mult: Annotated[
            bool,
            Field(description="For match_to='rooms': divide multiplier by room count per zone when space_based is false."),
        ] = True,
    ) -> QueryResultModel:
        """Read Energy result DataCollection summaries."""
        from garden.run_energy.results import read_energy_result_data as service

        return validate_output(
            QueryResultModel,
            service(
                garden_root=garden_root,
                run_target=dump_target(run_target),
                run_id=run_id,
                output_name=output_name,
                output_names=output_names,
                output_query=output_query,
                unit=unit,
                data_type=data_type,
                object_type=object_type,
                run_period_index=run_period_index,
                include_values=include_values,
                max_values=max_values,
                max_collections=max_collections,
                max_outputs=max_outputs,
                save_data_collections=save_data_collections,
                match_to=match_to,
                model_target=dump_target(model_target),
                invert_multiplier=invert_multiplier,
                space_based=space_based,
                zone_correct_mult=zone_correct_mult,
            ),
        )

    @mcp.tool(
        name="EP_Read_Errors",
        description=(
            "Read a bounded EnergyPlus ERR text output for one Garden energy_run target and "
            "summarize warning/severe/fatal counts. If the ERR contains Severe or Fatal errors, "
            "returns report.status blocked with energy_blocker, last_severe_error, severe_errors, "
            "and fatal_errors. If the ERR file is missing, returns a missing_err_output blocker "
            "with recommended_next_tools (GD_Poll_Run, GD_Read_Run_Logs)."
        ),
        tags={"energy", "result", "err", "diagnostics"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def read_energy_errors(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        run_target: Annotated[
            RunTargetRef | None,
            Field(description="Energy run target returned by EP_Start_Simulation; pass run_target unless you provide run_id."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        max_chars: Annotated[
            int,
            Field(ge=1, description="Maximum ERR text characters to return."),
        ] = 12000,
    ) -> QueryResultModel:
        """Read Energy ERR output."""
        from garden.run_energy.annual import read_energy_errors as service

        return validate_output(
            QueryResultModel,
            service(
                garden_root=garden_root,
                run_target=dump_target(run_target),
                run_id=run_id,
                max_chars=max_chars,
            ),
        )
