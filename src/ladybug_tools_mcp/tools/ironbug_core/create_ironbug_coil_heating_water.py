'MCP tool for detailed_hvac_coil_heating_water.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_heating_water tool.'

    @mcp.tool(
        name='coil_heating_water',
        description=(
            'Create IB_CoilHeatingWater, an Ironbug hot-water heating coil component '
            'that maps downstream to EnergyPlus Coil:Heating:Water and OpenStudio '
            'CoilHeatingWater. Use it as an FCU heating coil, reheat coil, unit-heater '
            'coil, or water-side coil target that must later be placed in valid '
            'air-side equipment and connected to a hot-water PlantLoop. This authors '
            'Ironbug DetailedHVAC input, not a Honeybee Energy HVAC template. Returns '
            'target, summary_view, persistence_receipt, and report for downstream '
            'DetailedHVAC assembly. Energy-ready UFactorTimesAreaAndDesignWaterFlowRate '
            'coils need numeric UA and maximum-water-flow inputs; readiness reports a '
            'repair issue before EnergyPlus if they are left as Autosize or omitted. '
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'coil',
            'hot-water',
            'plant-loop',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_coil_heating_water(
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
            Field(description="Stable identifier for the new IB_CoilHeatingWater object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="Optional EnergyPlus/OpenStudio coil name stored on Ironbug field Name."
            ),
        ] = None,
        rated_inlet_water_temperature: Annotated[
            float | None,
            Field(
                description="Optional rated entering hot-water temperature in Celsius for Coil:Heating:Water sizing."
            ),
        ] = None,
        rated_inlet_air_temperature: Annotated[
            float | None,
            Field(
                description="Optional rated entering air temperature in Celsius for Coil:Heating:Water sizing."
            ),
        ] = None,
        rated_outlet_water_temperature: Annotated[
            float | None,
            Field(
                description="Optional rated leaving hot-water temperature in Celsius for Coil:Heating:Water sizing."
            ),
        ] = None,
        rated_outlet_air_temperature: Annotated[
            float | None,
            Field(
                description="Optional rated leaving air temperature in Celsius for Coil:Heating:Water sizing."
            ),
        ] = None,
        u_factor_times_area_value: Annotated[
            float | str | None,
            Field(
                description=(
                    "Optional UA value in W/K. Use a numeric value for Energy-ready "
                    "UFactorTimesAreaAndDesignWaterFlowRate coils; Autosize can fail "
                    "EnergyPlus readiness in FCU, reheat, and unit-heater paths."
                )
            ),
        ] = None,
        maximum_water_flow_rate: Annotated[
            float | str | None,
            Field(
                description=(
                    "Optional maximum hot-water flow rate in m3/s. Use a numeric "
                    "value for Energy-ready UFactorTimesAreaAndDesignWaterFlowRate "
                    "coils; Autosize is rejected by readiness for this path."
                )
            ),
        ] = None,
        rated_ratio_for_air_and_water_convection: Annotated[
            float | None,
            Field(
                description="Sets Ironbug field RatedRatioForAirAndWaterConvection for IB_CoilHeatingWater."
            ),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for AvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Schedule values above zero make the heating coil available.'),
        ] = None,
        available_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional legacy AvailableSchedule target for Ironbug/OpenStudio source compatibility; prefer availability_schedule_target when both are available.'),
        ] = None,
        performance_input_method: Annotated[
            str | None,
            Field(description='Optional heating coil performance input method, commonly UFactorTimesAreaAndDesignWaterFlowRate or NominalCapacity.'),
        ] = None,
        rated_capacity: Annotated[
            float | str | None,
            Field(description='Optional RatedCapacity value; maps to Ironbug IB_CoilHeatingWater field RatedCapacity.'),
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
        controller_water_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ControllerWaterCoil target or same-model identifier. "
                    "Controllers are applied when this hot-water coil is added to a valid loop node."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_CoilHeatingWater as a reviewed hot-water coil component."""

        child_targets = [
            controller_water_coil_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if rated_inlet_water_temperature is not None:
            source_fields['RatedInletWaterTemperature'] = rated_inlet_water_temperature
        if rated_inlet_air_temperature is not None:
            source_fields['RatedInletAirTemperature'] = rated_inlet_air_temperature
        if rated_outlet_water_temperature is not None:
            source_fields['RatedOutletWaterTemperature'] = rated_outlet_water_temperature
        if rated_outlet_air_temperature is not None:
            source_fields['RatedOutletAirTemperature'] = rated_outlet_air_temperature
        if u_factor_times_area_value is not None:
            source_fields['UFactorTimesAreaValue'] = u_factor_times_area_value
        if maximum_water_flow_rate is not None:
            source_fields['MaximumWaterFlowRate'] = maximum_water_flow_rate
        if rated_ratio_for_air_and_water_convection is not None:
            source_fields['RatedRatioForAirAndWaterConvection'] = rated_ratio_for_air_and_water_convection
        source_properties: dict[str, Any] = {}
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if available_schedule_target is not None:
            source_field_targets['AvailableSchedule'] = available_schedule_target
        if performance_input_method is not None:
            source_fields['PerformanceInputMethod'] = performance_input_method
        if rated_capacity is not None:
            source_fields['RatedCapacity'] = rated_capacity
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilHeatingWater',
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
