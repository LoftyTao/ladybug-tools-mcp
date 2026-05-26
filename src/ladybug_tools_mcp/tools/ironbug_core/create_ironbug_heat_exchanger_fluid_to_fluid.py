'MCP tool for detailed_hvac_heat_exchanger_fluid_to_fluid.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_heat_exchanger_fluid_to_fluid tool.'

    @mcp.tool(
        name='heat_exchanger_fluid_to_fluid',
        description=(
            'Create IB_HeatExchangerFluidToFluid, an EnergyPlus HeatExchanger:FluidToFluid dual-loop hydronic plant heat exchanger that couples one loop supply side to another loop demand side. Use it for waterside economizer, plate/hydronic, primary-secondary, condenser-water, or ground-source loop exchange with model type, UA, control mode, and temperature limits; this is not an air-side or ground-geometry exchanger. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'plant-loop',
            'plant-component',
            'heat-exchanger',
            'fluid-to-fluid',
            'hydronic',
            'waterside-economizer',
            'chilled-water',
            'condenser-water',
            'control',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_heat_exchanger_fluid_to_fluid(
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
            Field(description="Stable identifier for the new IB_HeatExchangerFluidToFluid object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for AvailabilitySchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_HeatExchangerFluidToFluid field AvailabilitySchedule (IB_Schedule).'),
        ] = None,
        loop_demand_side_design_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional hydronic design flow rate in m3/s, or autosize string, for the loop demand side of the heat exchanger; maps to LoopDemandSideDesignFlowRate.'),
        ] = None,
        loop_supply_side_design_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional hydronic design flow rate in m3/s, or autosize string, for the loop supply side being conditioned; maps to LoopSupplySideDesignFlowRate.'),
        ] = None,
        heat_exchange_model_type: Annotated[
            str | None,
            Field(description='Optional fluid-to-fluid model type such as CounterFlow, ParallelFlow, CrossFlow, or Ideal; maps to HeatExchangeModelType.'),
        ] = None,
        heat_exchanger_u_factor_times_area_value: Annotated[
            float | str | None,
            Field(description='Optional heat exchanger UA value in W/K, or autosize string, used by the selected fluid-to-fluid model; maps to HeatExchangerUFactorTimesAreaValue.'),
        ] = None,
        control_type: Annotated[
            str | None,
            Field(description='Optional control mode such as CoolingDifferentialOnOff, setpoint control, operation-scheme control, or component override; maps to ControlType.'),
        ] = None,
        minimum_temperature_differenceto_activate_heat_exchanger: Annotated[
            float | None,
            Field(description='Optional temperature difference threshold in C used before the hydronic heat exchanger can operate; maps to MinimumTemperatureDifferencetoActivateHeatExchanger.'),
        ] = None,
        heat_transfer_metering_end_use_type: Annotated[
            str | None,
            Field(description='Optional HeatTransferMeteringEndUseType value; maps to Ironbug IB_HeatExchangerFluidToFluid field HeatTransferMeteringEndUseType.'),
        ] = None,
        component_override_cooling_control_temperature_mode: Annotated[
            str | None,
            Field(description='Optional temperature signal for CoolingSetpointOnOffWithComponentOverride control, such as Loop, WetBulbTemperature, or DryBulbTemperature; maps to ComponentOverrideCoolingControlTemperatureMode.'),
        ] = None,
        sizing_factor: Annotated[
            float | None,
            Field(description='Optional SizingFactor value; maps to Ironbug IB_HeatExchangerFluidToFluid field SizingFactor.'),
        ] = None,
        operation_minimum_temperature_limit: Annotated[
            float | None,
            Field(description='Optional OperationMinimumTemperatureLimit value; maps to Ironbug IB_HeatExchangerFluidToFluid field OperationMinimumTemperatureLimit.'),
        ] = None,
        operation_maximum_temperature_limit: Annotated[
            float | None,
            Field(description='Optional OperationMaximumTemperatureLimit value; maps to Ironbug IB_HeatExchangerFluidToFluid field OperationMaximumTemperatureLimit.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus object name for this fluid-to-fluid plant heat exchanger; maps to Name.'),
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
        """Create IB_HeatExchangerFluidToFluid as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if loop_demand_side_design_flow_rate is not None:
            source_fields['LoopDemandSideDesignFlowRate'] = loop_demand_side_design_flow_rate
        if loop_supply_side_design_flow_rate is not None:
            source_fields['LoopSupplySideDesignFlowRate'] = loop_supply_side_design_flow_rate
        if heat_exchange_model_type is not None:
            source_fields['HeatExchangeModelType'] = heat_exchange_model_type
        if heat_exchanger_u_factor_times_area_value is not None:
            source_fields['HeatExchangerUFactorTimesAreaValue'] = heat_exchanger_u_factor_times_area_value
        if control_type is not None:
            source_fields['ControlType'] = control_type
        if minimum_temperature_differenceto_activate_heat_exchanger is not None:
            source_fields['MinimumTemperatureDifferencetoActivateHeatExchanger'] = minimum_temperature_differenceto_activate_heat_exchanger
        if heat_transfer_metering_end_use_type is not None:
            source_fields['HeatTransferMeteringEndUseType'] = heat_transfer_metering_end_use_type
        if component_override_cooling_control_temperature_mode is not None:
            source_fields['ComponentOverrideCoolingControlTemperatureMode'] = component_override_cooling_control_temperature_mode
        if sizing_factor is not None:
            source_fields['SizingFactor'] = sizing_factor
        if operation_minimum_temperature_limit is not None:
            source_fields['OperationMinimumTemperatureLimit'] = operation_minimum_temperature_limit
        if operation_maximum_temperature_limit is not None:
            source_fields['OperationMaximumTemperatureLimit'] = operation_maximum_temperature_limit
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_HeatExchangerFluidToFluid',
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
