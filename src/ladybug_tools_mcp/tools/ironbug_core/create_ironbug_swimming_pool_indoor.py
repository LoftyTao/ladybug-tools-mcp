'MCP tool for detailed_hvac_swimming_pool_indoor.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from ladybug_tools_mcp.tools.ironbug_core.target_identifiers import target_identifier



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_swimming_pool_indoor tool.'

    @mcp.tool(
        name='swimming_pool_indoor',
        description=(
            'Create IB_SwimmingPoolIndoor, the Ironbug and EnergyPlus SwimmingPool:Indoor plant-loop component linked to a floor surface. It models indoor pool water depth, schedules, cover factors, people load, and heating water flow; it does not create pool geometry, surfaces, or Energy result data. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'plant-component', 'plant-loop', 'water-use', 'pool', 'swimming-pool', 'schedule', 'surface', 'author', 'component'},
        timeout=20,
    )
    def create_ironbug_swimming_pool_indoor(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json for the Ironbug model."),
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
            Field(description="Stable identifier for the new IB_SwimmingPoolIndoor object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        average_depth: Annotated[
            float | None,
            Field(description='Optional average pool water depth in meters.'),
        ] = None,
        activity_factor_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for pool activity factor.'),
        ] = None,
        makeup_water_supply_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for MakeupWaterSupplySchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_SwimmingPoolIndoor field MakeupWaterSupplySchedule (IB_Schedule).'),
        ] = None,
        cover_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for CoverSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_SwimmingPoolIndoor field CoverSchedule (IB_Schedule).'),
        ] = None,
        cover_evaporation_factor: Annotated[
            float | None,
            Field(description='Optional CoverEvaporationFactor value; maps to Ironbug IB_SwimmingPoolIndoor field CoverEvaporationFactor.'),
        ] = None,
        cover_convection_factor: Annotated[
            float | None,
            Field(description='Optional CoverConvectionFactor value; maps to Ironbug IB_SwimmingPoolIndoor field CoverConvectionFactor.'),
        ] = None,
        cover_short_wavelength_radiation_factor: Annotated[
            float | None,
            Field(description='Optional CoverShortWavelengthRadiationFactor value; maps to Ironbug IB_SwimmingPoolIndoor field CoverShortWavelengthRadiationFactor.'),
        ] = None,
        cover_long_wavelength_radiation_factor: Annotated[
            float | None,
            Field(description='Optional CoverLongWavelengthRadiationFactor value; maps to Ironbug IB_SwimmingPoolIndoor field CoverLongWavelengthRadiationFactor.'),
        ] = None,
        pool_heating_system_maximum_water_flow_rate: Annotated[
            float | None,
            Field(description='Optional PoolHeatingSystemMaximumWaterFlowRate value; maps to Ironbug IB_SwimmingPoolIndoor field PoolHeatingSystemMaximumWaterFlowRate.'),
        ] = None,
        pool_miscellaneous_equipment_power: Annotated[
            float | None,
            Field(description='Optional PoolMiscellaneousEquipmentPower value; maps to Ironbug IB_SwimmingPoolIndoor field PoolMiscellaneousEquipmentPower.'),
        ] = None,
        setpoint_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for pool water setpoint temperature.'),
        ] = None,
        maximum_numberof_people: Annotated[
            float | None,
            Field(description='Optional MaximumNumberofPeople value; maps to Ironbug IB_SwimmingPoolIndoor field MaximumNumberofPeople.'),
        ] = None,
        people_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for PeopleSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_SwimmingPoolIndoor field PeopleSchedule (IB_Schedule).'),
        ] = None,
        people_heat_gain_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for PeopleHeatGainSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_SwimmingPoolIndoor field PeopleHeatGainSchedule (IB_Schedule).'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_SwimmingPoolIndoor field Name.'),
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
        pool_surface_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Honeybee floor Face target or EnergyPlus floor surface identifier "
                    "for the pool water surface; the pool is assumed to cover that floor surface."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug indoor swimming-pool plant component."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        ib_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if pool_surface_target is not None:
            ib_properties['_surfaceID'] = target_identifier(
                pool_surface_target,
                parameter_name="pool_surface_target",
            )
        if average_depth is not None:
            source_fields['AverageDepth'] = average_depth
        if activity_factor_schedule_target is not None:
            source_field_targets['ActivityFactorSchedule'] = activity_factor_schedule_target
        if makeup_water_supply_schedule_target is not None:
            source_field_targets['MakeupWaterSupplySchedule'] = makeup_water_supply_schedule_target
        if cover_schedule_target is not None:
            source_field_targets['CoverSchedule'] = cover_schedule_target
        if cover_evaporation_factor is not None:
            source_fields['CoverEvaporationFactor'] = cover_evaporation_factor
        if cover_convection_factor is not None:
            source_fields['CoverConvectionFactor'] = cover_convection_factor
        if cover_short_wavelength_radiation_factor is not None:
            source_fields['CoverShortWavelengthRadiationFactor'] = cover_short_wavelength_radiation_factor
        if cover_long_wavelength_radiation_factor is not None:
            source_fields['CoverLongWavelengthRadiationFactor'] = cover_long_wavelength_radiation_factor
        if pool_heating_system_maximum_water_flow_rate is not None:
            source_fields['PoolHeatingSystemMaximumWaterFlowRate'] = pool_heating_system_maximum_water_flow_rate
        if pool_miscellaneous_equipment_power is not None:
            source_fields['PoolMiscellaneousEquipmentPower'] = pool_miscellaneous_equipment_power
        if setpoint_temperature_schedule_target is not None:
            source_field_targets['SetpointTemperatureSchedule'] = setpoint_temperature_schedule_target
        if maximum_numberof_people is not None:
            source_fields['MaximumNumberofPeople'] = maximum_numberof_people
        if people_schedule_target is not None:
            source_field_targets['PeopleSchedule'] = people_schedule_target
        if people_heat_gain_schedule_target is not None:
            source_field_targets['PeopleHeatGainSchedule'] = people_heat_gain_schedule_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SwimmingPoolIndoor',
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
