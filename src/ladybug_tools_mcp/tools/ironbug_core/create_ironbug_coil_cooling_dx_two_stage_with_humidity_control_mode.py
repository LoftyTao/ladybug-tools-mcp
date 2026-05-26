'MCP tool for detailed_hvac_coil_cooling_dx_two_stage_with_humidity_control_mode.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_cooling_dx_two_stage_with_humidity_control_mode tool.'

    @mcp.tool(
        name='coil_cooling_dx_two_stage_with_humidity_control_mode',
        description=(
            'Create IB_CoilCoolingDXTwoStageWithHumidityControlMode, an OpenStudio/EnergyPlus Coil:Cooling:DX:TwoStageWithHumidityControlMode object for staged DX cooling with optional enhanced dehumidification mode. Use IB_CoilPerformanceDXCooling targets for normal and dehumidification stage performance. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'cooling', 'dx', 'two-speed', 'humidity-control', 'dehumidification', 'performance', 'air-loop', 'doas', 'curve', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_cooling_dx_two_stage_with_humidity_control_mode(
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
            Field(description="Stable identifier for the new IB_CoilCoolingDXTwoStageWithHumidityControlMode object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for staged DX coil availability; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXTwoStageWithHumidityControlMode field AvailabilitySchedule.'),
        ] = None,
        crankcase_heater_capacity: Annotated[
            float | None,
            Field(description='Optional crankcase heater capacity in watts; maps to Ironbug IB_CoilCoolingDXTwoStageWithHumidityControlMode field CrankcaseHeaterCapacity.'),
        ] = None,
        crankcase_heater_capacity_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for crankcase heater capacity versus outdoor temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXTwoStageWithHumidityControlMode field CrankcaseHeaterCapacityFunctionofTemperatureCurve.'),
        ] = None,
        maximum_outdoor_dry_bulb_temperaturefor_crankcase_heater_operation: Annotated[
            float | None,
            Field(description='Optional MaximumOutdoorDryBulbTemperatureforCrankcaseHeaterOperation value; maps to Ironbug IB_CoilCoolingDXTwoStageWithHumidityControlMode field MaximumOutdoorDryBulbTemperatureforCrankcaseHeaterOperation.'),
        ] = None,
        numberof_capacity_stages: Annotated[
            int | None,
            Field(description='Optional number of normal capacity stages, usually 1 or 2; maps to Ironbug IB_CoilCoolingDXTwoStageWithHumidityControlMode field NumberofCapacityStages.'),
        ] = None,
        numberof_enhanced_dehumidification_modes: Annotated[
            int | None,
            Field(description='Optional number of enhanced dehumidification modes, usually 0 or 1; maps to Ironbug IB_CoilCoolingDXTwoStageWithHumidityControlMode field NumberofEnhancedDehumidificationModes.'),
        ] = None,
        basin_heater_capacity: Annotated[
            float | None,
            Field(description='Optional BasinHeaterCapacity value; maps to Ironbug IB_CoilCoolingDXTwoStageWithHumidityControlMode field BasinHeaterCapacity.'),
        ] = None,
        basin_heater_setpoint_temperature: Annotated[
            float | None,
            Field(description='Optional BasinHeaterSetpointTemperature value; maps to Ironbug IB_CoilCoolingDXTwoStageWithHumidityControlMode field BasinHeaterSetpointTemperature.'),
        ] = None,
        basin_heater_operating_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for evaporative-condenser basin heater operation; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilCoolingDXTwoStageWithHumidityControlMode field BasinHeaterOperatingSchedule.'),
        ] = None,
        minimum_outdoor_dry_bulb_temperaturefor_compressor_operation: Annotated[
            float | None,
            Field(description='Optional MinimumOutdoorDryBulbTemperatureforCompressorOperation value; maps to Ironbug IB_CoilCoolingDXTwoStageWithHumidityControlMode field MinimumOutdoorDryBulbTemperatureforCompressorOperation.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilCoolingDXTwoStageWithHumidityControlMode field Name.'),
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
        coil_performance_n1_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_CoilPerformanceDXCooling target for normal mode stage 1 "
                    "performance on IB_CoilCoolingDXTwoStageWithHumidityControlMode."
                )
            ),
        ] = None,
        coil_performance_n1_2_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_CoilPerformanceDXCooling target for normal mode stage 1+2 "
                    "performance on IB_CoilCoolingDXTwoStageWithHumidityControlMode."
                )
            ),
        ] = None,
        coil_performance_d1_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_CoilPerformanceDXCooling target for dehumidification mode stage 1 "
                    "performance on IB_CoilCoolingDXTwoStageWithHumidityControlMode."
                )
            ),
        ] = None,
        coil_performance_d1_2_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_CoilPerformanceDXCooling target for dehumidification mode stage 1+2 "
                    "performance on IB_CoilCoolingDXTwoStageWithHumidityControlMode."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_CoilCoolingDXTwoStageWithHumidityControlMode as a reviewed Ironbug Loop Objs authoring object."""

        child_targets = [
            coil_performance_n1_target,
            coil_performance_n1_2_target,
            coil_performance_d1_target,
            coil_performance_d1_2_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if crankcase_heater_capacity is not None:
            source_fields['CrankcaseHeaterCapacity'] = crankcase_heater_capacity
        if crankcase_heater_capacity_functionof_temperature_curve_target is not None:
            source_field_targets['CrankcaseHeaterCapacityFunctionofTemperatureCurve'] = crankcase_heater_capacity_functionof_temperature_curve_target
        if maximum_outdoor_dry_bulb_temperaturefor_crankcase_heater_operation is not None:
            source_fields['MaximumOutdoorDryBulbTemperatureforCrankcaseHeaterOperation'] = maximum_outdoor_dry_bulb_temperaturefor_crankcase_heater_operation
        if numberof_capacity_stages is not None:
            source_fields['NumberofCapacityStages'] = numberof_capacity_stages
        if numberof_enhanced_dehumidification_modes is not None:
            source_fields['NumberofEnhancedDehumidificationModes'] = numberof_enhanced_dehumidification_modes
        if basin_heater_capacity is not None:
            source_fields['BasinHeaterCapacity'] = basin_heater_capacity
        if basin_heater_setpoint_temperature is not None:
            source_fields['BasinHeaterSetpointTemperature'] = basin_heater_setpoint_temperature
        if basin_heater_operating_schedule_target is not None:
            source_field_targets['BasinHeaterOperatingSchedule'] = basin_heater_operating_schedule_target
        if minimum_outdoor_dry_bulb_temperaturefor_compressor_operation is not None:
            source_fields['MinimumOutdoorDryBulbTemperatureforCompressorOperation'] = minimum_outdoor_dry_bulb_temperaturefor_compressor_operation
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilCoolingDXTwoStageWithHumidityControlMode',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            child_targets=child_targets if any(item is not None for item in child_targets) else None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
