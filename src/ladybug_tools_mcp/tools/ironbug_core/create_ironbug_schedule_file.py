'MCP tool for detailed_hvac_schedule_file.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_schedule_file tool.'

    @mcp.tool(
        name='schedule_file',
        description=(
            'Create IB_ScheduleFile, an EnergyPlus Schedule:File target that reads hourly or timestep values from a local CSV/text file for Ironbug DetailedHVAC controls. Use csv_file plus column, row-skip, separator, interpolation, daylight-savings, and ScheduleTypeLimits inputs; this does not download weather data, create a rule-based annual schedule, read simulation results, or run Energy. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'schedule', 'schedule-file', 'csv', 'schedule-type-limit', 'author'},
        timeout=20,
    )
    def create_ironbug_schedule_file(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, for example garden_create['garden_root']."),
        ],
        ironbug_model_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Required Ironbug model target returned by detailed_hvac_create_model; '
                    "pass result['target'], not the .ibjson file path."
                )
            ),
        ],
        identifier: Annotated[
            str,
            Field(description="Stable identifier for the new IB_ScheduleFile object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        schedule_type_limits_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional IB_ScheduleTypeLimits target or same-model identifier that constrains values read from the Schedule:File."
            ),
        ] = None,
        column_number: Annotated[
            int | None,
            Field(description='Optional 1-based file column number containing the schedule values; maps to ColumnNumber.'),
        ] = None,
        rowsto_skipat_top: Annotated[
            int | None,
            Field(description='Optional number of header rows to skip before reading schedule values; maps to RowstoSkipatTop.'),
        ] = None,
        numberof_hoursof_data: Annotated[
            float | None,
            Field(description='Optional number of hours of data in the file, commonly 8760 or 8784; maps to NumberofHoursofData.'),
        ] = None,
        column_separator: Annotated[
            str | None,
            Field(description='Optional column separator keyword or character for the CSV/text schedule file; maps to ColumnSeparator.'),
        ] = None,
        interpolateto_timestep: Annotated[
            bool | str | None,
            Field(description='Optional flag controlling interpolation from file interval to EnergyPlus timestep; maps to InterpolatetoTimestep.'),
        ] = None,
        minutesper_item: Annotated[
            str | None,
            Field(description='Optional minutes per file item for sub-hourly Schedule:File data; maps to MinutesperItem.'),
        ] = None,
        adjust_schedulefor_daylight_savings: Annotated[
            bool | str | None,
            Field(description='Optional daylight-savings adjustment flag for the file schedule; maps to AdjustScheduleforDaylightSavings.'),
        ] = None,
        translate_file_with_relative_path: Annotated[
            bool | str | None,
            Field(description='Optional flag for translating the file path as relative during export; maps to TranslateFileWithRelativePath.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus object name for this Schedule:File; maps to Name.'),
        ] = None,
        output_variable_names: Annotated[
            list[str] | None,
            Field(
                description="Optional explicit Ironbug output variable names for this object."
            ),
        ] = None,
        output_reporting_frequency: Annotated[
            Literal["Detail", "Hourly", "Daily", "Monthly", "RunPeriod"],
            Field(description="Reporting frequency used for output_variable_names."),
        ] = "Hourly",
        ems_sensor_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional IB_EnergyManagementSystemSensor targets for CustomSensors."),
        ] = None,
        ems_actuator_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional IB_EnergyManagementSystemActuator targets for CustomActuators."),
        ] = None,
        ems_internal_variable_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_EnergyManagementSystemInternalVariable targets for CustomInternalVariables."
            ),
        ] = None,
        csv_file: Annotated[
            str | None,
            Field(description='Optional local CSV/text file path used by IB_ScheduleFile; the file is embedded or copied during Ironbug export.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug Schedule:File target."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if schedule_type_limits_target is not None:
            source_field_targets['ScheduleTypeLimits'] = schedule_type_limits_target
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if column_number is not None:
            source_fields['ColumnNumber'] = column_number
        if rowsto_skipat_top is not None:
            source_fields['RowstoSkipatTop'] = rowsto_skipat_top
        if numberof_hoursof_data is not None:
            source_fields['NumberofHoursofData'] = numberof_hoursof_data
        if column_separator is not None:
            source_fields['ColumnSeparator'] = column_separator
        if interpolateto_timestep is not None:
            source_fields['InterpolatetoTimestep'] = interpolateto_timestep
        if minutesper_item is not None:
            source_fields['MinutesperItem'] = minutesper_item
        if adjust_schedulefor_daylight_savings is not None:
            source_fields['AdjustScheduleforDaylightSavings'] = adjust_schedulefor_daylight_savings
        if translate_file_with_relative_path is not None:
            source_fields['TranslateFileWithRelativePath'] = translate_file_with_relative_path
        ib_properties: dict[str, Any] = {}
        if csv_file is not None:
            ib_properties['_filePath'] = csv_file
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ScheduleFile',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            ib_properties=ib_properties or None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
