'MCP tool for detailed_hvac_coil_heating_dx_multi_speed_stage_data.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_heating_dx_multi_speed_stage_data tool.'

    @mcp.tool(
        name='coil_heating_dx_multi_speed_stage_data',
        description=(
            'Create IB_CoilHeatingDXMultiSpeedStageData, the per-speed performance data object used by IB_CoilHeatingDXMultiSpeed. Use the returned target as a stage in detailed_hvac_coil_heating_dx_multi_speed, or provide equivalent inline stage fields there. It carries performance data for one DX heating coil speed and belongs under a multi-speed coil. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'heating', 'dx', 'multi-speed', 'stage-data', 'performance', 'curve', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_heating_dx_multi_speed_stage_data(
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
            Field(description="Stable identifier for the new IB_CoilHeatingDXMultiSpeedStageData object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        gross_rated_heating_capacity: Annotated[
            float | str | None,
            Field(description='Optional gross rated heating capacity in watts for this DX heating speed. Maps to Ironbug IB_CoilHeatingDXMultiSpeedStageData field GrossRatedHeatingCapacity.'),
        ] = None,
        gross_rated_heating_cop: Annotated[
            float | None,
            Field(description='Optional gross rated COP for this DX heating speed. Maps to Ironbug IB_CoilHeatingDXMultiSpeedStageData field GrossRatedHeatingCOP.'),
        ] = None,
        rated_air_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional rated air flow rate across this DX heating speed. Maps to Ironbug IB_CoilHeatingDXMultiSpeedStageData field RatedAirFlowRate.'),
        ] = None,
        rated_supply_air_fan_power_per_volume_flow_rate2017: Annotated[
            float | None,
            Field(description='Optional 2017 standard-rating supply air fan power per volume flow rate for HSPF calculations. Maps to Ironbug IB_CoilHeatingDXMultiSpeedStageData field RatedSupplyAirFanPowerPerVolumeFlowRate2017.'),
        ] = None,
        rated_supply_air_fan_power_per_volume_flow_rate2023: Annotated[
            float | None,
            Field(description='Optional 2023 standard-rating supply air fan power per volume flow rate for HSPF2 calculations. Maps to Ironbug IB_CoilHeatingDXMultiSpeedStageData field RatedSupplyAirFanPowerPerVolumeFlowRate2023.'),
        ] = None,
        heating_capacity_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for heating capacity as a function of temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilHeatingDXMultiSpeedStageData field HeatingCapacityFunctionofTemperatureCurve.'),
        ] = None,
        heating_capacity_functionof_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for heating capacity as a function of air flow fraction; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilHeatingDXMultiSpeedStageData field HeatingCapacityFunctionofFlowFractionCurve.'),
        ] = None,
        energy_input_ratio_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for energy input ratio as a function of temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilHeatingDXMultiSpeedStageData field EnergyInputRatioFunctionofTemperatureCurve.'),
        ] = None,
        energy_input_ratio_functionof_flow_fraction_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for energy input ratio as a function of air flow fraction; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilHeatingDXMultiSpeedStageData field EnergyInputRatioFunctionofFlowFractionCurve.'),
        ] = None,
        part_load_fraction_correlation_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for part-load fraction correlation at this speed; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilHeatingDXMultiSpeedStageData field PartLoadFractionCorrelationCurve.'),
        ] = None,
        rated_waste_heat_fractionof_power_input: Annotated[
            float | None,
            Field(description='Optional rated recoverable waste heat fraction of power input for this speed. Maps to Ironbug IB_CoilHeatingDXMultiSpeedStageData field RatedWasteHeatFractionofPowerInput.'),
        ] = None,
        waste_heat_functionof_temperature_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for recoverable waste heat as a function of temperature; pass a target dict or same-model identifier. Maps to Ironbug IB_CoilHeatingDXMultiSpeedStageData field WasteHeatFunctionofTemperatureCurve.'),
        ] = None,
        rated_supply_air_fan_power_per_volume_flow_rate: Annotated[
            str | float | int | bool | None,
            Field(description='Optional legacy rated supply air fan power per volume flow rate for standard rating calculations. Maps to Ironbug IB_CoilHeatingDXMultiSpeedStageData field RatedSupplyAirFanPowerPerVolumeFlowRate.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilHeatingDXMultiSpeedStageData field Name.'),
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
        """Create IB_CoilHeatingDXMultiSpeedStageData as a reviewed Ironbug Loop Objs authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if rated_supply_air_fan_power_per_volume_flow_rate is not None:
            source_fields['RatedSupplyAirFanPowerPerVolumeFlowRate'] = rated_supply_air_fan_power_per_volume_flow_rate
        if gross_rated_heating_capacity is not None:
            source_fields['GrossRatedHeatingCapacity'] = gross_rated_heating_capacity
        if gross_rated_heating_cop is not None:
            source_fields['GrossRatedHeatingCOP'] = gross_rated_heating_cop
        if rated_air_flow_rate is not None:
            source_fields['RatedAirFlowRate'] = rated_air_flow_rate
        if rated_supply_air_fan_power_per_volume_flow_rate2017 is not None:
            source_fields['RatedSupplyAirFanPowerPerVolumeFlowRate2017'] = rated_supply_air_fan_power_per_volume_flow_rate2017
        if rated_supply_air_fan_power_per_volume_flow_rate2023 is not None:
            source_fields['RatedSupplyAirFanPowerPerVolumeFlowRate2023'] = rated_supply_air_fan_power_per_volume_flow_rate2023
        if heating_capacity_functionof_temperature_curve_target is not None:
            source_field_targets['HeatingCapacityFunctionofTemperatureCurve'] = heating_capacity_functionof_temperature_curve_target
        if heating_capacity_functionof_flow_fraction_curve_target is not None:
            source_field_targets['HeatingCapacityFunctionofFlowFractionCurve'] = heating_capacity_functionof_flow_fraction_curve_target
        if energy_input_ratio_functionof_temperature_curve_target is not None:
            source_field_targets['EnergyInputRatioFunctionofTemperatureCurve'] = energy_input_ratio_functionof_temperature_curve_target
        if energy_input_ratio_functionof_flow_fraction_curve_target is not None:
            source_field_targets['EnergyInputRatioFunctionofFlowFractionCurve'] = energy_input_ratio_functionof_flow_fraction_curve_target
        if part_load_fraction_correlation_curve_target is not None:
            source_field_targets['PartLoadFractionCorrelationCurve'] = part_load_fraction_correlation_curve_target
        if rated_waste_heat_fractionof_power_input is not None:
            source_fields['RatedWasteHeatFractionofPowerInput'] = rated_waste_heat_fractionof_power_input
        if waste_heat_functionof_temperature_curve_target is not None:
            source_field_targets['WasteHeatFunctionofTemperatureCurve'] = waste_heat_functionof_temperature_curve_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilHeatingDXMultiSpeedStageData',
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
