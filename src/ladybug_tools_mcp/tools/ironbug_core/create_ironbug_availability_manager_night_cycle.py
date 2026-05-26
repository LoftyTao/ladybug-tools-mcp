'MCP tool for detailed_hvac_availability_manager_night_cycle.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_availability_manager_night_cycle tool.'

    @mcp.tool(
        name='availability_manager_night_cycle',
        description=(
            'Create IB_AvailabilityManagerNightCycle, an OpenStudio availability manager that can cycle an air loop during unoccupied periods based on night-cycle control settings. Use the returned target in an AirLoopHVAC or AvailabilityManagerList availability-manager slot. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={'ironbug', 'detailed-hvac', 'availability-manager', 'control', 'night-cycle', 'schedule', 'thermostat', 'air-loop', 'hvac', 'author'},
        timeout=20,
    )
    def create_ironbug_availability_manager_night_cycle(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually garden_create['garden_root']."),
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
            Field(description="Stable identifier for the new IB_AvailabilityManagerNightCycle object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        applicability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for ApplicabilitySchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AvailabilityManagerNightCycle field ApplicabilitySchedule (IB_Schedule).'),
        ] = None,
        control_type: Annotated[
            str | None,
            Field(description='Optional ControlType value; maps to Ironbug IB_AvailabilityManagerNightCycle field ControlType.'),
        ] = None,
        thermostat_tolerance: Annotated[
            float | None,
            Field(description='Optional ThermostatTolerance value; maps to Ironbug IB_AvailabilityManagerNightCycle field ThermostatTolerance.'),
        ] = None,
        cycling_run_time: Annotated[
            float | None,
            Field(description='Optional CyclingRunTime value; maps to Ironbug IB_AvailabilityManagerNightCycle field CyclingRunTime.'),
        ] = None,
        cycling_run_time_control_type: Annotated[
            str | None,
            Field(description='Optional CyclingRunTimeControlType value; maps to Ironbug IB_AvailabilityManagerNightCycle field CyclingRunTimeControlType.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_AvailabilityManagerNightCycle field Name.'),
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
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_AvailabilityManagerNightCycle as a reviewed Ironbug AvailabilityManagers authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if applicability_schedule_target is not None:
            source_field_targets['ApplicabilitySchedule'] = applicability_schedule_target
        if control_type is not None:
            source_fields['ControlType'] = control_type
        if thermostat_tolerance is not None:
            source_fields['ThermostatTolerance'] = thermostat_tolerance
        if cycling_run_time is not None:
            source_fields['CyclingRunTime'] = cycling_run_time
        if cycling_run_time_control_type is not None:
            source_fields['CyclingRunTimeControlType'] = cycling_run_time_control_type
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_AvailabilityManagerNightCycle',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
