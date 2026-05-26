'MCP tool for detailed_hvac_availability_manager_optimum_start.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_availability_manager_optimum_start tool.'

    @mcp.tool(
        name='availability_manager_optimum_start',
        description=(
            'Create IB_AvailabilityManagerOptimumStart, an OpenStudio availability manager that starts an air loop early enough to meet zone setpoint goals at occupancy. Use the returned target in an AirLoopHVAC or AvailabilityManagerList availability-manager slot with a named control zone. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={'ironbug', 'detailed-hvac', 'availability-manager', 'control', 'optimum-start', 'schedule', 'thermal-zone', 'air-loop', 'hvac', 'author'},
        timeout=20,
    )
    def create_ironbug_availability_manager_optimum_start(
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
            Field(description="Stable identifier for the new IB_AvailabilityManagerOptimumStart object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        applicability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for ApplicabilitySchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AvailabilityManagerOptimumStart field ApplicabilitySchedule (IB_Schedule).'),
        ] = None,
        control_type: Annotated[
            str | None,
            Field(description='Optional ControlType value; maps to Ironbug IB_AvailabilityManagerOptimumStart field ControlType.'),
        ] = None,
        maximum_valuefor_optimum_start_time: Annotated[
            float | None,
            Field(description='Optional MaximumValueforOptimumStartTime value; maps to Ironbug IB_AvailabilityManagerOptimumStart field MaximumValueforOptimumStartTime.'),
        ] = None,
        control_algorithm: Annotated[
            str | None,
            Field(description='Optional ControlAlgorithm value; maps to Ironbug IB_AvailabilityManagerOptimumStart field ControlAlgorithm.'),
        ] = None,
        constant_temperature_gradientduring_cooling: Annotated[
            float | None,
            Field(description='Optional ConstantTemperatureGradientduringCooling value; maps to Ironbug IB_AvailabilityManagerOptimumStart field ConstantTemperatureGradientduringCooling.'),
        ] = None,
        constant_temperature_gradientduring_heating: Annotated[
            float | None,
            Field(description='Optional ConstantTemperatureGradientduringHeating value; maps to Ironbug IB_AvailabilityManagerOptimumStart field ConstantTemperatureGradientduringHeating.'),
        ] = None,
        initial_temperature_gradientduring_cooling: Annotated[
            float | None,
            Field(description='Optional InitialTemperatureGradientduringCooling value; maps to Ironbug IB_AvailabilityManagerOptimumStart field InitialTemperatureGradientduringCooling.'),
        ] = None,
        initial_temperature_gradientduring_heating: Annotated[
            float | None,
            Field(description='Optional InitialTemperatureGradientduringHeating value; maps to Ironbug IB_AvailabilityManagerOptimumStart field InitialTemperatureGradientduringHeating.'),
        ] = None,
        constant_start_time: Annotated[
            float | None,
            Field(description='Optional ConstantStartTime value; maps to Ironbug IB_AvailabilityManagerOptimumStart field ConstantStartTime.'),
        ] = None,
        numberof_previous_days: Annotated[
            int | None,
            Field(description='Optional NumberofPreviousDays value; maps to Ironbug IB_AvailabilityManagerOptimumStart field NumberofPreviousDays.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_AvailabilityManagerOptimumStart field Name.'),
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
        control_zone: Annotated[
            str | None,
            Field(
                description=(
                    "Optional control-zone name used by Ironbug to resolve the OpenStudio ThermalZone for optimum-start control."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_AvailabilityManagerOptimumStart as a reviewed Ironbug AvailabilityManagers authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if applicability_schedule_target is not None:
            source_field_targets['ApplicabilitySchedule'] = applicability_schedule_target
        if control_type is not None:
            source_fields['ControlType'] = control_type
        if maximum_valuefor_optimum_start_time is not None:
            source_fields['MaximumValueforOptimumStartTime'] = maximum_valuefor_optimum_start_time
        if control_algorithm is not None:
            source_fields['ControlAlgorithm'] = control_algorithm
        if constant_temperature_gradientduring_cooling is not None:
            source_fields['ConstantTemperatureGradientduringCooling'] = constant_temperature_gradientduring_cooling
        if constant_temperature_gradientduring_heating is not None:
            source_fields['ConstantTemperatureGradientduringHeating'] = constant_temperature_gradientduring_heating
        if initial_temperature_gradientduring_cooling is not None:
            source_fields['InitialTemperatureGradientduringCooling'] = initial_temperature_gradientduring_cooling
        if initial_temperature_gradientduring_heating is not None:
            source_fields['InitialTemperatureGradientduringHeating'] = initial_temperature_gradientduring_heating
        if constant_start_time is not None:
            source_fields['ConstantStartTime'] = constant_start_time
        if numberof_previous_days is not None:
            source_fields['NumberofPreviousDays'] = numberof_previous_days
        ib_properties: dict[str, Any] = {}
        if control_zone is not None:
            ib_properties['_controlZoneName'] = control_zone
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_AvailabilityManagerOptimumStart',
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
