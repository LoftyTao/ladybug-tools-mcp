'MCP tool for detailed_hvac_electric_load_center_storage_converter.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_electric_load_center_storage_converter tool.'

    @mcp.tool(
        name='electric_load_center_storage_converter',
        description=(
            'Create IB_ElectricLoadCenterStorageConverter, an EnergyPlus/OpenStudio ElectricLoadCenter:Storage:Converter object for AC-to-DC conversion while charging DC storage from grid supply. Use it as the storage converter target on ElectricLoadCenter:Distribution when DC storage charging requires separate converter performance. This tool authors storage-converter input only; it is not an inverter, storage device, transformer, or simulation runner. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'electric', 'electric-equipment', 'load-center', 'storage', 'converter', 'performance', 'author'},
        timeout=20,
    )
    def create_ironbug_electric_load_center_storage_converter(
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
            Field(description="Stable identifier for the new IB_ElectricLoadCenterStorageConverter object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier controlling storage-converter availability; maps to Ironbug field AvailabilitySchedule.'),
        ] = None,
        simple_fixed_efficiency: Annotated[
            float | None,
            Field(description='Fixed AC-to-DC converter efficiency fraction; maps to Ironbug field SimpleFixedEfficiency.'),
        ] = None,
        design_maximum_continuous_input_power: Annotated[
            float | None,
            Field(description='Design maximum continuous converter input power in W; maps to Ironbug field DesignMaximumContinuousInputPower.'),
        ] = None,
        efficiency_functionof_power_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target or same-model identifier for converter efficiency as a function of power; maps to Ironbug field EfficiencyFunctionofPowerCurve.'),
        ] = None,
        ancillary_power_consumed_in_standby: Annotated[
            float | None,
            Field(description='Ancillary standby power in W consumed by the converter; maps to Ironbug field AncillaryPowerConsumedInStandby.'),
        ] = None,
        radiative_fraction: Annotated[
            float | None,
            Field(description='Fraction of converter losses released as zone radiative heat gain; maps to Ironbug field RadiativeFraction.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio ElectricLoadCenter:Storage:Converter object name; defaults to the identifier when omitted.'),
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
        """Create IB_ElectricLoadCenterStorageConverter as reviewed storage-converter data."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if simple_fixed_efficiency is not None:
            source_fields['SimpleFixedEfficiency'] = simple_fixed_efficiency
        if design_maximum_continuous_input_power is not None:
            source_fields['DesignMaximumContinuousInputPower'] = design_maximum_continuous_input_power
        if efficiency_functionof_power_curve_target is not None:
            source_field_targets['EfficiencyFunctionofPowerCurve'] = efficiency_functionof_power_curve_target
        if ancillary_power_consumed_in_standby is not None:
            source_fields['AncillaryPowerConsumedInStandby'] = ancillary_power_consumed_in_standby
        if radiative_fraction is not None:
            source_fields['RadiativeFraction'] = radiative_fraction
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ElectricLoadCenterStorageConverter',
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
