'MCP tool for detailed_hvac_availability_manager_hybrid_ventilation.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_availability_manager_hybrid_ventilation tool.'

    @mcp.tool(
        name='availability_manager_hybrid_ventilation',
        description=(
            'Create IB_AvailabilityManagerHybridVentilation, an OpenStudio availability manager that coordinates HVAC operation with natural ventilation controls for a named control zone. Use the returned target in an AirLoopHVAC or AvailabilityManagerList availability-manager slot when the DetailedHVAC graph includes hybrid ventilation logic. This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
        ),
        tags={'ironbug', 'detailed-hvac', 'availability-manager', 'control', 'ventilation', 'natural-ventilation', 'airflow-network', 'thermal-zone', 'air-loop', 'hvac', 'author'},
        timeout=20,
    )
    def create_ironbug_availability_manager_hybrid_ventilation(
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
            Field(description="Stable identifier for the new IB_AvailabilityManagerHybridVentilation object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        ventilation_control_mode_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for VentilationControlModeSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AvailabilityManagerHybridVentilation field VentilationControlModeSchedule (IB_Schedule).'),
        ] = None,
        use_weather_file_rain_indicators: Annotated[
            bool | str | None,
            Field(description='Optional UseWeatherFileRainIndicators value; maps to Ironbug IB_AvailabilityManagerHybridVentilation field UseWeatherFileRainIndicators.'),
        ] = None,
        maximum_wind_speed: Annotated[
            float | None,
            Field(description='Optional MaximumWindSpeed value; maps to Ironbug IB_AvailabilityManagerHybridVentilation field MaximumWindSpeed.'),
        ] = None,
        minimum_outdoor_temperature: Annotated[
            float | None,
            Field(description='Optional MinimumOutdoorTemperature value; maps to Ironbug IB_AvailabilityManagerHybridVentilation field MinimumOutdoorTemperature.'),
        ] = None,
        maximum_outdoor_temperature: Annotated[
            float | None,
            Field(description='Optional MaximumOutdoorTemperature value; maps to Ironbug IB_AvailabilityManagerHybridVentilation field MaximumOutdoorTemperature.'),
        ] = None,
        minimum_outdoor_enthalpy: Annotated[
            float | None,
            Field(description='Optional MinimumOutdoorEnthalpy value; maps to Ironbug IB_AvailabilityManagerHybridVentilation field MinimumOutdoorEnthalpy.'),
        ] = None,
        maximum_outdoor_enthalpy: Annotated[
            float | None,
            Field(description='Optional MaximumOutdoorEnthalpy value; maps to Ironbug IB_AvailabilityManagerHybridVentilation field MaximumOutdoorEnthalpy.'),
        ] = None,
        minimum_outdoor_dewpoint: Annotated[
            float | None,
            Field(description='Optional MinimumOutdoorDewpoint value; maps to Ironbug IB_AvailabilityManagerHybridVentilation field MinimumOutdoorDewpoint.'),
        ] = None,
        maximum_outdoor_dewpoint: Annotated[
            float | None,
            Field(description='Optional MaximumOutdoorDewpoint value; maps to Ironbug IB_AvailabilityManagerHybridVentilation field MaximumOutdoorDewpoint.'),
        ] = None,
        minimum_outdoor_ventilation_air_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for MinimumOutdoorVentilationAirSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AvailabilityManagerHybridVentilation field MinimumOutdoorVentilationAirSchedule (IB_Schedule).'),
        ] = None,
        opening_factor_functionof_wind_speed_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for OpeningFactorFunctionofWindSpeedCurve; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AvailabilityManagerHybridVentilation field OpeningFactorFunctionofWindSpeedCurve (IB_Curve).'),
        ] = None,
        minimum_hvac_operation_time: Annotated[
            float | None,
            Field(description='Optional MinimumHVACOperationTime value; maps to Ironbug IB_AvailabilityManagerHybridVentilation field MinimumHVACOperationTime.'),
        ] = None,
        minimum_ventilation_time: Annotated[
            float | None,
            Field(description='Optional MinimumVentilationTime value; maps to Ironbug IB_AvailabilityManagerHybridVentilation field MinimumVentilationTime.'),
        ] = None,
        airflow_network_control_type_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for AirflowNetworkControlTypeSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AvailabilityManagerHybridVentilation field AirflowNetworkControlTypeSchedule (IB_Schedule).'),
        ] = None,
        simple_airflow_control_type_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for SimpleAirflowControlTypeSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_AvailabilityManagerHybridVentilation field SimpleAirflowControlTypeSchedule (IB_Schedule).'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_AvailabilityManagerHybridVentilation field Name.'),
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
                    "Optional control-zone name used by Ironbug to resolve the OpenStudio ThermalZone for hybrid ventilation control."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_AvailabilityManagerHybridVentilation as a reviewed Ironbug AvailabilityManagers authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if ventilation_control_mode_schedule_target is not None:
            source_field_targets['VentilationControlModeSchedule'] = ventilation_control_mode_schedule_target
        if use_weather_file_rain_indicators is not None:
            source_fields['UseWeatherFileRainIndicators'] = use_weather_file_rain_indicators
        if maximum_wind_speed is not None:
            source_fields['MaximumWindSpeed'] = maximum_wind_speed
        if minimum_outdoor_temperature is not None:
            source_fields['MinimumOutdoorTemperature'] = minimum_outdoor_temperature
        if maximum_outdoor_temperature is not None:
            source_fields['MaximumOutdoorTemperature'] = maximum_outdoor_temperature
        if minimum_outdoor_enthalpy is not None:
            source_fields['MinimumOutdoorEnthalpy'] = minimum_outdoor_enthalpy
        if maximum_outdoor_enthalpy is not None:
            source_fields['MaximumOutdoorEnthalpy'] = maximum_outdoor_enthalpy
        if minimum_outdoor_dewpoint is not None:
            source_fields['MinimumOutdoorDewpoint'] = minimum_outdoor_dewpoint
        if maximum_outdoor_dewpoint is not None:
            source_fields['MaximumOutdoorDewpoint'] = maximum_outdoor_dewpoint
        if minimum_outdoor_ventilation_air_schedule_target is not None:
            source_field_targets['MinimumOutdoorVentilationAirSchedule'] = minimum_outdoor_ventilation_air_schedule_target
        if opening_factor_functionof_wind_speed_curve_target is not None:
            source_field_targets['OpeningFactorFunctionofWindSpeedCurve'] = opening_factor_functionof_wind_speed_curve_target
        if minimum_hvac_operation_time is not None:
            source_fields['MinimumHVACOperationTime'] = minimum_hvac_operation_time
        if minimum_ventilation_time is not None:
            source_fields['MinimumVentilationTime'] = minimum_ventilation_time
        if airflow_network_control_type_schedule_target is not None:
            source_field_targets['AirflowNetworkControlTypeSchedule'] = airflow_network_control_type_schedule_target
        if simple_airflow_control_type_schedule_target is not None:
            source_field_targets['SimpleAirflowControlTypeSchedule'] = simple_airflow_control_type_schedule_target
        ib_properties: dict[str, Any] = {}
        if control_zone is not None:
            ib_properties['_controlZoneName'] = control_zone
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_AvailabilityManagerHybridVentilation',
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
