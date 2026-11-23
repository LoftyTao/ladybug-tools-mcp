"""run_energy MCP tools."""

from __future__ import annotations

import time

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register run_energy tools."""

    @mcp.tool(
        name="EP_Create_Output_Request",
        description=(
            'Create a Garden energy_output_request target for EnergyPlus outputs before an energy '
            'run. Use it for hourly zone loads, HVAC energy use, unmet hours, surface '
            'temperatures, custom Output:Variable names, summary reports, or later result '
            'visualization. Pass the returned target to EP_Start_Simulation or '
            'EP_Run_Simulation_Wait as output_request_target. This tool prepares requests.'
        ),
        tags={
            "energy",
            "result",
            "sql",
            "author",
            "report",
        },
        timeout=20,
    )
    def create_energy_output_request(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for this energy_output_request target."),
        ],
        presets: Annotated[
            list[str] | None,
            Field(
                description="Optional named output presets such as zone_energy_use, hvac_energy_use, unmet_hours, surface_temperature, surface_energy_flow, glazing_solar, comfort_metrics, energy_balance, gains_and_losses, or electricity_generation."
            ),
        ] = None,
        custom_outputs: Annotated[
            list[str] | None,
            Field(
                description="Optional exact EnergyPlus Output:Variable names to request, for example Facility Total HVAC Electricity Demand Rate."
            ),
        ] = None,
        summary_reports: Annotated[
            list[str] | None,
            Field(
                description="Optional EnergyPlus summary reports, for example AllSummary or AnnualBuildingUtilityPerformanceSummary."
            ),
        ] = None,
        reporting_frequency: Annotated[
            str,
            Field(
                description="EnergyPlus reporting frequency for output variables: Annual, Monthly, Daily, Hourly, or Timestep."
            ),
        ] = "Hourly",
        include_sqlite: Annotated[
            bool,
            Field(
                description="Whether the simulation should write a SQLite result file for DataCollection result reading."
            ),
        ] = True,
        include_html: Annotated[
            bool,
            Field(description="Whether the simulation should write an HTML summary report."),
        ] = True,
        unmet_setpoint_tolerance: Annotated[
            float,
            Field(description="Unmet setpoint tolerance in degrees Celsius."),
        ] = 1.11,
    ) -> dict[str, Any]:
        """Create an Energy output request target."""
        from garden.run_energy.output_requests import (
            create_energy_output_request as service,
        )

        return service(
            garden_root=garden_root,
            identifier=identifier,
            presets=presets,
            custom_outputs=custom_outputs,
            summary_reports=summary_reports,
            reporting_frequency=reporting_frequency,
            include_sqlite=include_sqlite,
            include_html=include_html,
            unmet_setpoint_tolerance=unmet_setpoint_tolerance,
        )

    @mcp.tool(
        name="EP_Create_Simulation_Parameter",
        description=(
            "Create and persist a reusable Honeybee Energy SimulationParameter "
            "target for later EP_Start_Simulation or EP_Run_Simulation_Wait calls. "
            "Use task-level run_period, design_days strategies, sizing factors, "
            "shadow_calculation settings, and an optional output_request_target; "
            "design-day strategies are resolved from the selected weather DDY "
            "when weather_target is supplied here or at simulation start. Returns "
            "simulation_parameter_target, compact summary_view, "
            "persistence_receipt, and report, without returning the full SDK body "
            "unless include_body=true."
        ),
        tags={"energy", "energyplus", "author", "parameter", "simulation"},
        timeout=20,
    )
    def create_simulation_parameter(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']."
                )
            ),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Optional stable identifier for the saved parameter target."),
        ] = None,
        run_period: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional task-level period with start_month, start_day, "
                    "end_month, end_day, and optional start_day_of_week/leap_year."
                )
            ),
        ] = None,
        design_days: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional DDY strategies: all, heating, cooling, "
                    "heating_99.6, heating_99, cooling_0.4, cooling_1, "
                    "99.6/0.4, or 99/1."
                )
            ),
        ] = None,
        sizing: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional sizing settings such as heating_factor, cooling_factor, "
                    "efficiency_standard, climate_zone, building_type, and "
                    "bypass_efficiency_sizing."
                )
            ),
        ] = None,
        shadow_calculation: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional EnergyPlus shadow settings such as solar_distribution, "
                    "calculation_method, calculation_update_method, "
                    "calculation_frequency, and maximum_figures."
                )
            ),
        ] = None,
        output_request_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional energy_output_request target returned by "
                    "EP_Create_Output_Request."
                )
            ),
        ] = None,
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional weather_file target with ddy_path; when supplied, "
                    "design_days strategies are resolved during creation."
                )
            ),
        ] = None,
        include_body: Annotated[
            bool,
            Field(description="Return the full SDK SimulationParameter dictionary."),
        ] = False,
    ) -> dict[str, Any]:
        """Create a reusable Energy SimulationParameter target."""
        from garden.run_energy.parameters import (
            create_simulation_parameter as service,
        )

        return service(
            garden_root=garden_root,
            identifier=identifier,
            run_period=run_period,
            design_days=design_days,
            sizing=sizing,
            shadow_calculation=shadow_calculation,
            output_request_target=output_request_target,
            weather_target=weather_target,
            include_body=include_body,
        )

    @mcp.tool(
        name="EP_Result_Hourly_Plot_To_HTML",
        description="Create a ready-to-open Garden HTML artifact from one hourly EnergyPlus SQL DataCollection using Ladybug HourlyPlot. Use only when the requested result is an HTML file, not for EUI summaries or raw SQL DataCollection targets. Returns artifact_receipt, summary_view.artifact, summary_view.data_collection, and report; pass artifact_receipt.artifact_path or summary_view.artifact.path to preview/export flows.",
        tags={
            "energy",
            "result",
            "sql",
            "visualize",
            "hourly-plot",
            "artifact",
        },
        timeout=90,
    )
    def energy_result_hourly_plot_to_html(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        output_name: Annotated[
            str,
            Field(description="Exact EnergyPlus SQL output name to plot; choose it from EP_List_Run_Outputs or EP_Read_Result_Data inventory."),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Energy run target returned by EP_Start_Simulation; pass run_target for polling unless you provide run_id.'
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        collection_index: Annotated[
            int,
            Field(
                description="Which DataCollection returned for the output_name to plot."
            ),
        ] = 0,
        name: Annotated[
            str,
            Field(description="HTML artifact file name without extension."),
        ] = "energy_result_hourly_plot",
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative artifact output directory."),
        ] = "artifacts/energy/results/html",
    ) -> dict[str, Any]:
        """Export one Energy result DataCollection to an HourlyPlot HTML artifact."""
        from garden.run_energy.results import (
            energy_result_hourly_plot_to_html as service,
        )

        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            output_name=output_name,
            collection_index=collection_index,
            name=name,
            output_subdir=output_subdir,
        )

    @mcp.tool(
        name="EP_Result_Monthly_Chart_To_HTML",
        description="Create a ready-to-open Garden HTML artifact from one or more EnergyPlus SQL DataCollections using Ladybug MonthlyChart. Each series item uses output_name plus optional collection_index, run_period_index, and label metadata. Returns artifact_receipt, summary_view.artifact, summary_view.series, and report; pass artifact_receipt.artifact_path or summary_view.artifact.path to preview/export flows.",
        tags={
            "energy",
            "result",
            "sql",
            "visualize",
            "monthly-chart",
            "artifact",
        },
        timeout=90,
    )
    def energy_result_monthly_chart_to_html(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        series: Annotated[
            list[dict[str, Any]],
            Field(
                description="One or more chart series. Each item requires output_name and may include collection_index, run_period_index, and label. The label is written to DataCollection header metadata for the legend."
            ),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Energy run target returned by EP_Start_Simulation; pass run_target for polling unless you provide run_id.'
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        time_interval: Annotated[
            str,
            Field(
                description="How to use/aggregate DataCollections before charting: as_is, hourly, daily, monthly, monthly_per_hour, total_daily, total_monthly, or total_monthly_per_hour."
            ),
        ] = "as_is",
        chart_title: Annotated[
            str | None,
            Field(description="Optional global title for the chart."),
        ] = None,
        y_axis_title: Annotated[
            str | None,
            Field(description="Optional Y-axis title for the chart."),
        ] = None,
        stack: Annotated[
            bool,
            Field(
                description="Whether cumulative series should be stacked by MonthlyChart."
            ),
        ] = False,
        percentile: Annotated[
            float,
            Field(
                description="Percentile spread used by MonthlyChart for hourly data."
            ),
        ] = 34,
        time_marks: Annotated[
            bool,
            Field(
                description="Whether month labels are replaced with time-of-day marks."
            ),
        ] = False,
        name: Annotated[
            str,
            Field(description="HTML artifact file name without extension."),
        ] = "energy_result_monthly_chart",
        output_subdir: Annotated[
            str,
            Field(description="Garden-relative artifact output directory."),
        ] = "artifacts/energy/results/html",
    ) -> dict[str, Any]:
        """Export Energy result DataCollections to a MonthlyChart HTML artifact."""
        from garden.run_energy.results import (
            energy_result_monthly_chart_to_html as service,
        )

        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            series=series,
            time_interval=time_interval,
            chart_title=chart_title,
            y_axis_title=y_axis_title,
            stack=stack,
            percentile=percentile,
            time_marks=time_marks,
            name=name,
            output_subdir=output_subdir,
        )

    @mcp.tool(
        name="EP_Poll_Simulation",
        description=(
            'Get one Garden energy_run record by run_target or run_id without returning large '
            'result files. Use after EP_Start_Simulation. When the user asks to wait, pass '
            'wait_seconds instead of repeated immediate polling; this waits in the wrapper and '
            'does not change the EnergyPlus engine timeout. Returns status through '
            'summary_view.status, summary_view.run, result_evidence, and report.'
        ),
        tags={
            "energy",
            "simulate",
            "poll",
            "run",
        },
        annotations={"readOnlyHint": True},
        timeout=180,
    )
    def get_energy_run(
        garden_root: Annotated[
            str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='Energy run target returned by EP_Start_Simulation; pass run_target for polling unless you provide run_id.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        wait_seconds: Annotated[
            int | float | None,
            Field(
                description="Optional wrapper-side polling duration in seconds before returning; does not change the EnergyPlus/OpenStudio simulation timeout."
            ),
        ] = None,
        poll_interval: Annotated[
            int | float | None,
            Field(description="Optional wrapper-side polling interval in seconds when wait_seconds is supplied."),
        ] = None,
    ) -> dict[str, Any]:
        """Get one Energy simulation run."""
        from garden.run_energy.annual import get_energy_run as service

        requested_wait = max(float(wait_seconds or 0), 0.0)
        applied_wait = min(requested_wait, 150.0)
        interval = max(float(poll_interval or 1.0), 0.2)
        deadline = time.monotonic() + applied_wait
        result = service(garden_root=garden_root, run_target=run_target, run_id=run_id)
        while applied_wait and time.monotonic() < deadline:
            status = (
                result.get("summary_view", {})
                .get("run", {})
                .get("status")
            )
            if status not in {"queued", "running"}:
                break
            time.sleep(min(interval, max(deadline - time.monotonic(), 0.0)))
            result = service(garden_root=garden_root, run_target=run_target, run_id=run_id)
        if requested_wait:
            result.setdefault("summary_view", {})["wait_seconds_requested"] = wait_seconds
            result.setdefault("summary_view", {})["wait_seconds_applied"] = applied_wait
        return result

    @mcp.tool(
        name="EP_Import_Local_Weather",
        description=(
            'Copy bundled or local EPW/DDY/STAT weather files into a Garden imports/weather '
            'directory and register it as a weather_file target. Use weather://files/<station> '
            'for a bundled FastMCP weather resource, or provide an absolute local file/folder '
            'path. Use weather://catalog to list bundled stations before EP_Search_Weather_Files, '
            'UWG, URBANopt, EnergyPlus, or Radiance weather handoffs. For other locations, obtain '
            'an archive from https://climate.onebuilding.org/, extract it locally, and import it '
            'here.'
        ),
        tags={"energy", "weather", "epw", "offline", "garden"},
        timeout=60,
    )
    def import_local_weather(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        source_path: Annotated[
            str,
            Field(
                description=(
                    "Bundled weather resource URI weather://files/<station>, or an "
                    "absolute local .epw file path or folder containing EPW/DDY/STAT files."
                ),
            ),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Optional stable weather identifier for the Garden target."),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Overwrite an existing imported weather folder with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Import local weather files and return a weather_file target."""
        from garden.run_energy.config import import_local_weather_folder as service

        return service(
            garden_root=garden_root,
            source_path=source_path,
            identifier=identifier,
            overwrite=overwrite,
        )

    @mcp.tool(
        name="EP_List_Run_Outputs",
        description=(
            "List indexed output files for one Garden energy_run, including EUI "
            "JSON, ERR, SQL, HTML reports, and ZSZ when present. The same list "
            "is returned as matches, outputs, and files for easy result scanning. "
            "Use matches[i].name/path/exists to choose EP_Read_EUI, "
            "EP_Read_Errors, EP_Read_Result_Data, or chart export."
        ),
        tags={
            "energy",
            "result",
            "outputs",
            "search",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_energy_run_outputs(
        garden_root: Annotated[
            str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='Energy run target returned by EP_Start_Simulation; pass run_target unless you provide run_id.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
    ) -> dict[str, Any]:
        """List Energy simulation run outputs."""
        from garden.run_energy.annual import list_energy_run_outputs as service

        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)

    @mcp.tool(
        name="EP_List_Runs",
        description=(
            'List annual energy-use simulation runs recorded in a Garden run ledger. Use this to '
            'find run_id, run_target, status, or run folder metadata before polling or reading '
            'results. Returns matches, summary_view, and report.'
        ),
        tags={
            "energy",
            "simulate",
            "poll",
            "ledger",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def list_energy_runs(
        garden_root: Annotated[
            str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")
        ],
        status: Annotated[
            str | None,
            Field(
                description="Optional runtime_status filter for Garden Energy run ledger records, such as running, completed, failed, or cancelled."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """List Energy simulation runs."""
        from garden.run_energy.annual import list_energy_runs as service

        return service(garden_root=garden_root, status=status)

    @mcp.tool(
        name="EP_Read_Errors",
        description=(
            "Read a bounded EnergyPlus ERR text output for one Garden energy_run "
            "target and summarize warning/severe/fatal counts. If the ERR "
            "contains Severe or Fatal errors, the response returns report.status "
            "blocked with energy_blocker, last_severe_error, severe_errors, and "
            "fatal_errors so the caller can report a precise EnergyPlus blocker. "
            "If the ERR file is missing, this returns a missing_err_output blocker "
            "instead of raising, with recommended_next_tools for run/status checks."
        ),
        tags={
            "energy",
            "result",
            "err",
            "diagnostics",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def read_energy_errors(
        garden_root: Annotated[
            str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='Energy run target returned by EP_Start_Simulation; pass run_target unless you provide run_id.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        max_chars: Annotated[
            int, Field(description="Maximum ERR text characters to return.")
        ] = 12000,
    ) -> dict[str, Any]:
        """Read Energy ERR output."""
        from garden.run_energy.annual import read_energy_errors as service

        return service(
            garden_root=garden_root,
            run_target=run_target,
            run_id=run_id,
            max_chars=max_chars,
        )

    @mcp.tool(
        name="EP_Read_EUI",
        description=(
            'Read EUI / energy use intensity JSON for one Garden energy_run after runtime_status '
            'is finished. Use after EP_Poll_Simulation or EP_List_Run_Outputs confirms result '
            'artifacts exist; reads the lightweight annual summary. Returns eui, result_evidence, '
            'summary_view, and report; if EUI is missing, returns energy_blocker with '
            'recommended_next_tools.'
        ),
        tags={
            "energy",
            "result",
            "eui",
            "summary",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def read_energy_eui(
        garden_root: Annotated[
            str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(description='Energy run target returned by EP_Start_Simulation; pass run_target unless you provide run_id.'),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
    ) -> dict[str, Any]:
        """Read Energy EUI summary."""
        from garden.run_energy.annual import read_energy_eui as service

        return service(garden_root=garden_root, run_target=run_target, run_id=run_id)

    @mcp.tool(
        name="EP_Read_Result_Data",
        description=(
            'Read EnergyPlus SQL results from a completed Garden energy_run as compact Ladybug '
            'DataCollection summaries with result_context provenance. Use output names from '
            'EP_List_Run_Outputs or SQL output inventory filters. Without '
            'output_name/output_names/filters, returns available_outputs only. With '
            'save_data_collections=true, returns data_collection_targets and '
            'summary_view.first_data_collection_target for visualization tools.'
        ),
        tags={
            "energy",
            "result",
            "sql",
            "data-collection",
        },
        timeout=60,
    )
    def read_energy_result_data(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        run_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Energy run target returned by EP_Start_Simulation; pass run_target unless you provide run_id.'
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when run_target is omitted."),
        ] = None,
        output_name: Annotated[
            str | None,
            Field(
                description="Optional exact EnergyPlus SQL output name to read as DataCollections. Omit to list or filter available SQL outputs."
            ),
        ] = None,
        output_names: Annotated[
            list[str] | None,
            Field(
                description="Optional exact EnergyPlus SQL output names to read in one call for multi-series charts. Provide only one of output_name or output_names."
            ),
        ] = None,
        output_query: Annotated[
            str | None,
            Field(
                description="Optional case-insensitive substring query for SQL output names, used when output_name and output_names are omitted."
            ),
        ] = None,
        unit: Annotated[
            str | None,
            Field(
                description="Optional exact unit filter for SQL outputs, for example kWh, kW, C, or %."
            ),
        ] = None,
        data_type: Annotated[
            str | None,
            Field(
                description="Optional exact Ladybug data_type filter for SQL outputs, for example Energy, Power, Temperature, or Fraction."
            ),
        ] = None,
        object_type: Annotated[
            str | None,
            Field(
                description="Optional case-insensitive object_type filter from SQL output metadata, for example Zone or System."
            ),
        ] = None,
        run_period_index: Annotated[
            int | None,
            Field(description="Optional EnergyPlus run period index."),
        ] = None,
        include_values: Annotated[
            bool,
            Field(
                description=(
                    'Whether to include bounded raw values from each DataCollection. Default '
                    'false for compact responses.'
                )
            ),
        ] = False,
        max_values: Annotated[
            int,
            Field(
                description="Maximum values per DataCollection when include_values is true."
            ),
        ] = 24,
        max_collections: Annotated[
            int,
            Field(description="Maximum DataCollection summaries to return."),
        ] = 10,
        max_outputs: Annotated[
            int,
            Field(
                description="Maximum SQL outputs selected by output_query/unit/data_type/object_type filters."
            ),
        ] = 25,
        save_data_collections: Annotated[
            bool,
            Field(
                description="Persist each returned DataCollection as a Garden ladybug_data_collection target and return data_collection_targets. Keep false for inventory-only reads; set true with include_values=false before passing targets into generic visualize tools."
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Read Energy result DataCollection summaries."""
        from garden.run_energy.results import read_energy_result_data as service

        return service(
            garden_root=garden_root,
            run_target=run_target,
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
        )

    @mcp.tool(
        name="EP_Read_Sizing",
        description="Read compact zone peak loads and HVAC component sizing from a completed Garden Energy run. Filter by zone, component, or sizing category; it never returns raw SQL tables.",
        tags={"energy", "energyplus", "result", "sizing", "zone", "hvac"},
        timeout=30,
    )
    def read_energy_sizing(
        garden_root: Annotated[str, Field(description="Garden root path containing the completed Energy run.")],
        run_target: Annotated[dict[str, Any] | None, Field(description="Completed Energy run target.")] = None,
        run_id: Annotated[str | None, Field(description="Completed Energy run identifier.")] = None,
        zone: Annotated[str | None, Field(description="Optional zone-name substring filter.")] = None,
        component: Annotated[str | None, Field(description="Optional component-name substring filter.")] = None,
        sizing_category: Annotated[str | None, Field(description="Optional result category: zone, component, heating, or cooling.")] = None,
        max_results: Annotated[int, Field(description="Maximum compact sizing records to return.")] = 50,
    ) -> dict[str, Any]:
        """Read compact sizing results."""
        from garden.run_energy.results import read_energy_sizing as service
        return service(garden_root=garden_root, run_target=run_target, run_id=run_id, zone=zone, component=component, sizing_category=sizing_category, max_results=max_results)

    @mcp.tool(
        name="EP_Read_Weather_File_Data",
        description=(
            "Read a Garden-managed EPW weather_file, including UWG morphed "
            "EPW outputs, into a Ladybug DataCollection target with the "
            "Ladybug SDK EPW interface. Use this for weather comparisons such "
            "as dry bulb temperature, relative humidity, wind speed, wind "
            "direction, direct normal radiation, diffuse horizontal radiation, "
            "and global horizontal radiation. This reads weather data, not "
            "EnergyPlus SQL or simulation result data. Provide exactly one of "
            "weather_target or epw_path; epw_path must stay inside the Garden."
        ),
        tags={
            "energy",
            "weather",
            "epw",
            "result",
            "data-collection",
        },
        timeout=60,
    )
    def read_weather_file_data(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Optional Garden weather_file target returned by EP_Import_Local_Weather, EP_Search_Weather_Files, DF_UWG_Run_Simulation_Wait, or DF_UWG_Poll_Simulation. Provide exactly one of weather_target or epw_path.'
            ),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(
                description="Optional Garden-relative or absolute Garden-contained .epw path. Provide exactly one of weather_target or epw_path."
            ),
        ] = None,
        data_type: Annotated[
            str,
            Field(
                description="EPW data field. Examples: dry_bulb_temperature, relative_humidity, wind_speed, wind_direction, direct_normal_radiation, diffuse_horizontal_radiation, global_horizontal_radiation, dew_point_temperature, atmospheric_station_pressure."
            ),
        ] = "dry_bulb_temperature",
        analysis_period: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Ladybug AnalysisPeriod dict or string used to filter the EPW DataCollection before saving, for example '7/21 to 7/21 between 0 and 23 @1'."
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(
                description="Optional identifier for the saved ladybug_data_collection target. Defaults to weather identifier plus EPW data_type."
            ),
        ] = None,
        include_values: Annotated[
            bool,
            Field(
                description=(
                    'Whether to include bounded raw values in the compact summary. Default false '
                    'for compact responses.'
                )
            ),
        ] = False,
        max_values: Annotated[
            int,
            Field(description="Maximum weather DataCollection values returned in summary when include_values is true."),
        ] = 24,
        return_data_collection: Annotated[
            bool,
            Field(
                description="Return the full Ladybug DataCollection dict. Keep false for chart workflows and pass data_collection_target downstream."
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Read EPW weather data as a Ladybug DataCollection target."""
        from garden.run_energy.weather_data import read_weather_file_data as service

        return service(
            garden_root=garden_root,
            weather_target=weather_target,
            epw_path=epw_path,
            data_type=data_type,
            analysis_period=analysis_period,
            identifier=identifier,
            include_values=include_values,
            max_values=max_values,
            return_data_collection=return_data_collection,
        )

    @mcp.tool(
        name="EP_Run_Simulation_Wait",
        description=(
            "Run the blocking Honeybee Energy annual-energy-use recipe for a "
            "Garden Honeybee model with Garden-managed EPW/DDY weather. Use "
            "EP_Start_Simulation plus EP_Poll_Simulation for "
            "the normal nonblocking workflow. Advanced users can pass "
            "a reusable simulation_parameter_target or the inline sim_par "
            "escape hatch (choose one), and can pass "
            "Garden-local additional_idf_path, inline additional_idf_text, or "
            "measures_path. This tool writes native OpenStudio contents under "
            "runs/energy/<model display name>/openstudio, records an "
            "energy_run target, and returns runtime_status through "
            "summary_view.status plus a lightweight output index. Treat failed "
            "runtime_status as requiring report review."
        ),
        tags={
            "energy",
            "simulate",
            "epw",
            "poll",
            "blocking",
        },
        timeout=3600,
    )
    def run_energy(
        garden_root: Annotated[
            str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")
        ],
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Garden weather file target returned by EP_Import_Local_Weather or EP_Search_Weather_Files, or a Garden-relative EPW path.'
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target. Defaults to the Garden base model."
            ),
        ] = None,
        sim_par: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy SimulationParameter dictionary. Saved to the run inputs folder."
            ),
        ] = None,
        simulation_parameter_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Optional reusable simulation_parameter target returned by '
                    'EP_Create_Simulation_Parameter. Mutually exclusive with sim_par.'
                )
            ),
        ] = None,
        output_request_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Optional parameter named exactly output_request_target. Pass the energy_output_request target returned by EP_Create_Output_Request. It is merged into the SimulationParameter output section and recorded in the run ledger.'
            ),
        ] = None,
        additional_idf_path: Annotated[
            str | None,
            Field(
                description="Optional Garden-relative path to an additional EnergyPlus .idf file. Advanced users can use this to append supported EnergyPlus objects before simulation; the file must stay inside the Garden."
            ),
        ] = None,
        additional_idf_text: Annotated[
            str | None,
            Field(
                description=(
                    'Optional inline additional EnergyPlus IDF text. Advanced users can pass '
                    'small complete EnergyPlus objects such as EMS snippets; the service saves '
                    'the text into the run inputs folder and passes it as recipe additional-idf. '
                    'Mutually exclusive with additional_idf_path.'
                )
            ),
        ] = None,
        measures_path: Annotated[
            str | None,
            Field(
                description="Optional Garden-relative path to an OpenStudio measures folder for the annual-energy-use recipe. The folder must stay inside the Garden and contain the OSW JSON plus referenced measures."
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier. Omit to generate one."),
        ] = None,
        units: Annotated[
            str, Field(description="EUI units for EnergyPlus result summaries: si or ip.")
        ] = "si",
        workers: Annotated[
            int | None, Field(description="Optional recipe worker count.")
        ] = None,
        reload_old: Annotated[
            bool,
            Field(
                description="Reload existing recipe results for the run folder when available."
            ),
        ] = False,
        silent: Annotated[
            bool, Field(description="Run OpenStudio/EnergyPlus silently.")
        ] = True,
        validate_weather: Annotated[
            bool,
            Field(
                description="Validate EPW/DDY with the Ladybug SDK before launching the long recipe."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Run annual energy-use simulation and register an energy_run target."""
        from garden.run_energy.annual import run_energy as service

        return service(
            garden_root=garden_root,
            weather_target=weather_target,
            model_target=model_target,
            sim_par=sim_par,
            simulation_parameter_target=simulation_parameter_target,
            output_request_target=output_request_target,
            additional_idf_path=additional_idf_path,
            additional_idf_text=additional_idf_text,
            measures_path=measures_path,
            run_id=run_id,
            units=units,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            validate_weather=validate_weather,
        )

    @mcp.tool(
        name="EP_Run_IDF_File",
        description=(
            'Run a user-edited EnergyPlus IDF file inside a Garden with the Ladybug Tools '
            'Grasshopper file-run pattern. Use this after a user edits IDF algorithms, EMS, HVAC '
            'templates, or other EnergyPlus objects. Runs in blocking mode. Returns run_target, '
            'energy_run_target, runtime_status through summary_view.status, and report.'
        ),
        tags={
            "energy",
            "simulate",
            "idf",
            "file",
            "blocking",
        },
        timeout=3600,
    )
    def run_idf_file(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        idf_path: Annotated[
            str,
            Field(
                description=(
                    "Garden-relative or Garden-contained absolute path to the "
                    "edited .idf file."
                )
            ),
        ],
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Optional Garden weather_file target returned by '
                    'EP_Import_Local_Weather or EP_Search_Weather_Files. '
                    'Use instead of epw_path.'
                )
            ),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Garden-relative EPW path. Omit only for "
                    "design-day-only IDF simulations."
                )
            ),
        ] = None,
        expand_objects: Annotated[
            bool,
            Field(
                description=(
                    "Expand EnergyPlus HVAC Template objects before simulation."
                )
            ),
        ] = True,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable EnergyPlus IDF run identifier. Omit to generate one."),
        ] = None,
        silent: Annotated[
            bool,
            Field(description="Run EnergyPlus silently."),
        ] = True,
    ) -> dict[str, Any]:
        """Run an IDF file and register an energy_run target."""
        from garden.run_energy.files import run_idf_file as service

        return service(
            garden_root=garden_root,
            idf_path=idf_path,
            weather_target=weather_target,
            epw_path=epw_path,
            expand_objects=expand_objects,
            run_id=run_id,
            silent=silent,
        )

    @mcp.tool(
        name="EP_Run_OSM_File",
        description=(
            'Run a user-edited OpenStudio OSM file inside a Garden by creating or updating '
            'workflow.osw beside the OSM file. Use this after OpenStudio-level HVAC or measure '
            'edits. Runs in blocking mode. Returns run_target, energy_run_target, runtime_status '
            'through summary_view.status, and report.'
        ),
        tags={
            "energy",
            "simulate",
            "openstudio",
            "osm",
            "blocking",
        },
        timeout=3600,
    )
    def run_osm_file(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        osm_path: Annotated[
            str,
            Field(
                description=(
                    "Garden-relative or Garden-contained absolute path to the "
                    "edited .osm file."
                )
            ),
        ],
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Optional Garden weather_file target returned by '
                    'EP_Import_Local_Weather or EP_Search_Weather_Files. '
                    'Use instead of epw_path.'
                )
            ),
        ] = None,
        epw_path: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Garden-relative EPW path. Use instead of weather_target."
                )
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable OpenStudio OSM run identifier. Omit to generate one."),
        ] = None,
        silent: Annotated[
            bool,
            Field(description="Run OpenStudio/EnergyPlus silently."),
        ] = True,
    ) -> dict[str, Any]:
        """Run an OSM file and register an energy_run target."""
        from garden.run_energy.files import run_osm_file as service

        return service(
            garden_root=garden_root,
            osm_path=osm_path,
            weather_target=weather_target,
            epw_path=epw_path,
            run_id=run_id,
            silent=silent,
        )

    @mcp.tool(
        name="EP_Search_Weather_Files",
        description=(
            'Search weather_file targets already managed by a Garden under imports/weather and '
            'registered in garden.json. Import a bundled station from weather://catalog with '
            'EP_Import_Local_Weather, or obtain another EPW archive from '
            'https://climate.onebuilding.org/.'
        ),
        tags={
            "energy",
            "weather",
            "epw",
            "search",
            "garden",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_weather_files(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        query: Annotated[
            str | None,
            Field(
                description="Optional substring query against Garden weather identifiers, station names, station ids, source, host, and EPW paths."
            ),
        ] = None,
        max_results: Annotated[
            int, Field(description="Maximum number of Garden EPW matches to return.")
        ] = 10,
        require_ddy: Annotated[
            bool,
            Field(description="Only return EPW files that have a sibling DDY file."),
        ] = False,
    ) -> dict[str, Any]:
        """Search weather files and return weather_file targets."""
        from garden.run_energy.config import search_weather_files as service

        return service(
            garden_root=garden_root,
            query=query,
            max_results=max_results,
            require_ddy=require_ddy,
        )

    @mcp.tool(
        name="EP_Start_Simulation",
        description=(
            "Start a nonblocking annual Honeybee Energy annual-energy-use "
            "simulation for a Garden Honeybee model with Garden-managed "
            "EPW/DDY weather. Pass weather_target from "
            "EP_Import_Local_Weather or EP_Search_Weather_Files "
            "plus an optional Honeybee "
            "model target. Returns run_target, energy_run_target, "
            "and accepts either simulation_parameter_target from "
            "EP_Create_Simulation_Parameter or the advanced inline sim_par, "
            "runtime_status through summary_view.status, poll_next, and "
            "report. Poll with EP_Poll_Simulation before reading "
            "result artifacts. Treat failed runtime_status as requiring "
            "report review."
        ),
        tags={
            "energy",
            "simulate",
            "epw",
            "poll",
            "start",
        },
        timeout=60,
    )
    def start_energy_run(
        garden_root: Annotated[
            str, Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets.")
        ],
        weather_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Garden weather file target returned by EP_Import_Local_Weather or EP_Search_Weather_Files, or a Garden-relative EPW path. Keep the full target with epw_path and ddy_path when possible; registered identifier/path-only targets can be rehydrated from garden.json.'
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target with target_type=honeybee_model. Defaults to the Garden base model."
            ),
        ] = None,
        sim_par: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy SimulationParameter dictionary. Saved to the run inputs folder."
            ),
        ] = None,
        simulation_parameter_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Optional reusable simulation_parameter target returned by '
                    'EP_Create_Simulation_Parameter. Mutually exclusive with sim_par.'
                )
            ),
        ] = None,
        output_request_target: Annotated[
            dict[str, Any] | None,
            Field(
                description='Optional parameter named exactly output_request_target. Pass the energy_output_request target returned by EP_Create_Output_Request. It is merged into the SimulationParameter output section and recorded in the run ledger.'
            ),
        ] = None,
        additional_idf_path: Annotated[
            str | None,
            Field(
                description="Optional Garden-relative path to an additional EnergyPlus .idf file. Advanced users can use this to append supported EnergyPlus objects before simulation; the file must stay inside the Garden."
            ),
        ] = None,
        additional_idf_text: Annotated[
            str | None,
            Field(
                description=(
                    'Optional inline additional EnergyPlus IDF text. Advanced users can pass '
                    'small complete EnergyPlus objects such as EMS snippets; the service saves '
                    'the text into the run inputs folder and passes it as recipe additional-idf. '
                    'Mutually exclusive with additional_idf_path.'
                )
            ),
        ] = None,
        measures_path: Annotated[
            str | None,
            Field(
                description="Optional Garden-relative path to an OpenStudio measures folder for the annual-energy-use recipe. The folder must stay inside the Garden and contain the OSW JSON plus referenced measures."
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable run identifier. Omit to generate one."),
        ] = None,
        units: Annotated[
            str, Field(description="EUI units for EnergyPlus result summaries: si or ip.")
        ] = "si",
        workers: Annotated[
            int | None, Field(description="Optional recipe worker count.")
        ] = None,
        reload_old: Annotated[
            bool,
            Field(
                description="Reload existing recipe results for the run folder when available. With a finished Garden run ledger and matching run_id, return the existing energy_run target without starting a new background run."
            ),
        ] = False,
        silent: Annotated[
            bool, Field(description="Run OpenStudio/EnergyPlus silently.")
        ] = True,
        validate_weather: Annotated[
            bool,
            Field(
                description="Validate EPW/DDY with the Ladybug SDK before launching the background recipe."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Start annual energy-use simulation and return an energy_run target."""
        from garden.run_energy.annual import start_energy_run as service

        return service(
            garden_root=garden_root,
            weather_target=weather_target,
            model_target=model_target,
            sim_par=sim_par,
            simulation_parameter_target=simulation_parameter_target,
            output_request_target=output_request_target,
            additional_idf_path=additional_idf_path,
            additional_idf_text=additional_idf_text,
            measures_path=measures_path,
            run_id=run_id,
            units=units,
            workers=workers,
            reload_old=reload_old,
            silent=silent,
            validate_weather=validate_weather,
        )

    @mcp.tool(
        name="EP_Summarize_Results",
        description=(
            "Summarize one completed Garden energy_run by intent. Use "
            "summary_kind=energy_use, loads, or peaks; the tool reads existing "
            "EUI, SQL, and sizing outputs, returns compact metrics with units, "
            "period, scope, aggregation, conversion, and source provenance, "
            "and never starts a run. If outputs are insufficient, inspect "
            "energy_blocker.output_request_suggestion and use the suggested "
            "EP_Create_Output_Request before the next EP_Start_Simulation. "
            "Use EP_Read_Result_Data for expert-level raw SQL/DataCollection "
            "access."
        ),
        tags={"energy", "result", "summary", "loads", "peaks", "eui"},
        annotations={"readOnlyHint": True},
        timeout=60,
    )
    def summarize_energy_results(
        garden_root: Annotated[
            str,
            Field(
                description="Garden root path containing garden.json and the energy_run target."
            ),
        ],
        summary_kind: Annotated[
            str,
            Field(
                description="Summary intent: energy_use for EUI/end uses, loads for annual or monthly end-use loads, or peaks for heating/cooling sizing peaks."
            ),
        ],
        energy_run_target: Annotated[
            dict[str, Any],
            Field(
                description="Energy run target returned by EP_Start_Simulation or another Energy run tool."
            ),
        ],
        scope: Annotated[
            str | dict[str, Any] | None,
            Field(
                description="Optional zone or identifier substring scope. For energy_use, the EUI remains whole-building and the scope is recorded but not applied."
            ),
        ] = None,
        period: Annotated[
            str,
            Field(description="Requested time range: annual or monthly."),
        ] = "annual",
        unit_preference: Annotated[
            str | None,
            Field(
                description="Optional target unit such as kWh, MWh, W, or kW. Unsupported conversions retain the source unit and return a warning."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Return a compact intent-driven Energy result summary."""
        from garden.run_energy.summary import summarize_energy_results as service

        return service(
            garden_root=garden_root,
            energy_run_target=energy_run_target,
            summary_kind=summary_kind,
            scope=scope,
            period=period,
            unit_preference=unit_preference,
        )

    @mcp.tool(
        name="LB_Weather_Download",
        description=(
            "Search and download one EPW or ZIP weather file into a Garden and "
            "register a reusable weather_file target. The tool checks the public "
            "epwapi service first; search uses GET /v1/files, and known files "
            "prefer the direct epwfile OSS object URL. If epwapi or its search "
            "fails, it lists epwfile/ with OSS ListObjectsV2 pagination and "
            "matches the file name. Pass the returned weather_file target to "
            "EP_Start_Simulation, EP_Read_Weather_File_Data, UWG, or URBANopt. "
            "Use a specific query, region/country/admin_region, file_name, "
            "file_id, object_key, or file_target; ambiguous matches are rejected. "
            "No token or cloud credentials are required."
        ),
        tags={"ladybug", "weather", "epw", "download", "energy", "garden"},
        timeout=360,
    )
    def weather_download(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        query: Annotated[
            str | None,
            Field(
                description=(
                    "Case-insensitive EPW file, station, WMO number, region, "
                    "country, or admin-region query."
                )
            ),
        ] = None,
        file_id: Annotated[
            str | None,
            Field(description="Opaque id returned by epwapi /v1/files; pass it unchanged."),
        ] = None,
        file_name: Annotated[
            str | None,
            Field(description="Exact EPW or ZIP file name when using the epwfile fallback."),
        ] = None,
        object_key: Annotated[
            str | None,
            Field(description="Known epwfile object key beginning with epwfile/."),
        ] = None,
        file_target: Annotated[
            dict[str, Any] | None,
            Field(description="One file item returned by epwapi /v1/files, including id/name and directory fields."),
        ] = None,
        region: Annotated[
            str | None,
            Field(description="Exact epwapi region name, for example WMO_Region_2_Asia."),
        ] = None,
        country: Annotated[
            str | None,
            Field(description="Exact epwapi country name, for example CHN_China."),
        ] = None,
        admin_region: Annotated[
            str | None,
            Field(description="Exact epwapi administrative-region name, for example SD_Shandong."),
        ] = None,
        format: Annotated[
            str,
            Field(
                description=(
                    "File format filter matching epwapi /v1/files: epw or zip. "
                    "ZIP is the default so sibling DDY/STAT files can be "
                    "registered when present."
                )
            ),
        ] = "zip",
        page_size: Annotated[
            int,
            Field(description="epwapi page_size from 1 to 200."),
        ] = 20,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing Garden weather folder with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Download one public EPW weather file and register it in the Garden."""
        from garden.run_energy.weather_download import download_weather as service

        return service(
            garden_root=garden_root,
            query=query,
            file_id=file_id,
            file_name=file_name,
            object_key=object_key,
            file_target=file_target,
            region=region,
            country=country,
            admin_region=admin_region,
            file_format=format,
            page_size=page_size,
            overwrite=overwrite,
        )
