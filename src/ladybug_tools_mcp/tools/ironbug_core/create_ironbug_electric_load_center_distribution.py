'MCP tool for detailed_hvac_electric_load_center_distribution.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_electric_load_center_distribution tool.'

    @mcp.tool(
        name='electric_load_center_distribution',
        description=(
            'Create IB_ElectricLoadCenterDistribution, an EnergyPlus/OpenStudio ElectricLoadCenter:Distribution load-center subpanel for dispatching on-site generators and electrical storage. Use it to reference generator, inverter, storage, transformer, and storage-converter targets in an Ironbug DetailedHVAC model. This tool authors load-center distribution input only; it does not create PV arrays, generators, batteries, transformers, utility tariffs, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'electric', 'electric-equipment', 'load-center', 'distribution', 'inverter', 'storage', 'transformer', 'author'},
        timeout=20,
    )
    def create_ironbug_electric_load_center_distribution(
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
            Field(description="Stable identifier for the new IB_ElectricLoadCenterDistribution object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        generators_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_Generator targets or same-model identifiers for the generators connected to this ElectricLoadCenter:Distribution."
            ),
        ] = None,
        inverter_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ElecInverter target used when the electrical buss type requires an inverter."
                )
            ),
        ] = None,
        transformer_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ElectricLoadCenterTransformer target for load-center power conditioning."
                )
            ),
        ] = None,
        electrical_storage_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ElecStorage target for electrical storage connected to this load center."
                )
            ),
        ] = None,
        storage_converter_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ElectricLoadCenterStorageConverter target describing AC-to-DC charging performance for DC storage."
                )
            ),
        ] = None,
        generator_operation_scheme_type: Annotated[
            str | None,
            Field(description='Generator dispatch scheme for on-site generators; maps to Ironbug field GeneratorOperationSchemeType.'),
        ] = None,
        demand_limit_scheme_purchased_electric_demand_limit: Annotated[
            float | None,
            Field(description='Purchased-electric demand limit in W for demand-limit dispatch; maps to Ironbug field DemandLimitSchemePurchasedElectricDemandLimit.'),
        ] = None,
        track_schedule_scheme_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for scheduled generator dispatch; maps to Ironbug field TrackScheduleSchemeSchedule.'),
        ] = None,
        track_meter_scheme_meter_name: Annotated[
            str | None,
            Field(description='EnergyPlus meter name tracked by meter-based generator dispatch; maps to Ironbug field TrackMeterSchemeMeterName.'),
        ] = None,
        electrical_buss_type: Annotated[
            str | None,
            Field(description='Electrical buss type for AC, DC, inverter, and storage configuration; maps to Ironbug field ElectricalBussType.'),
        ] = None,
        storage_operation_scheme: Annotated[
            str | None,
            Field(description='Electrical storage dispatch scheme; maps to Ironbug field StorageOperationScheme.'),
        ] = None,
        storage_control_track_meter_name: Annotated[
            str | None,
            Field(description='EnergyPlus meter name used by storage control; maps to Ironbug field StorageControlTrackMeterName.'),
        ] = None,
        maximum_storage_stateof_charge_fraction: Annotated[
            float | None,
            Field(description='Upper allowed storage state-of-charge fraction; maps to Ironbug field MaximumStorageStateofChargeFraction.'),
        ] = None,
        minimum_storage_stateof_charge_fraction: Annotated[
            float | None,
            Field(description='Lower allowed storage state-of-charge fraction; maps to Ironbug field MinimumStorageStateofChargeFraction.'),
        ] = None,
        design_storage_control_charge_power: Annotated[
            float | None,
            Field(description='Design storage charging power in W; maps to Ironbug field DesignStorageControlChargePower.'),
        ] = None,
        storage_charge_power_fraction_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for storage charge-power fraction; maps to Ironbug field StorageChargePowerFractionSchedule.'),
        ] = None,
        design_storage_control_discharge_power: Annotated[
            float | None,
            Field(description='Design storage discharging power in W; maps to Ironbug field DesignStorageControlDischargePower.'),
        ] = None,
        storage_discharge_power_fraction_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for storage discharge-power fraction; maps to Ironbug field StorageDischargePowerFractionSchedule.'),
        ] = None,
        storage_control_utility_demand_target: Annotated[
            float | None,
            Field(description='Utility demand target in W for storage demand-leveling control; maps to Ironbug field StorageControlUtilityDemandTarget.'),
        ] = None,
        storage_control_utility_demand_target_fraction_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for utility-demand target fraction; maps to Ironbug field StorageControlUtilityDemandTargetFractionSchedule.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio ElectricLoadCenter:Distribution object name; defaults to the identifier when omitted.'),
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
        """Create IB_ElectricLoadCenterDistribution as reviewed load-center distribution data."""

        child_targets = [
            inverter_target,
            electrical_storage_target,
            storage_converter_target,
            transformer_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if generator_operation_scheme_type is not None:
            source_fields['GeneratorOperationSchemeType'] = generator_operation_scheme_type
        if demand_limit_scheme_purchased_electric_demand_limit is not None:
            source_fields['DemandLimitSchemePurchasedElectricDemandLimit'] = demand_limit_scheme_purchased_electric_demand_limit
        if track_schedule_scheme_schedule_target is not None:
            source_field_targets['TrackScheduleSchemeSchedule'] = track_schedule_scheme_schedule_target
        if track_meter_scheme_meter_name is not None:
            source_fields['TrackMeterSchemeMeterName'] = track_meter_scheme_meter_name
        if electrical_buss_type is not None:
            source_fields['ElectricalBussType'] = electrical_buss_type
        if storage_operation_scheme is not None:
            source_fields['StorageOperationScheme'] = storage_operation_scheme
        if storage_control_track_meter_name is not None:
            source_fields['StorageControlTrackMeterName'] = storage_control_track_meter_name
        if maximum_storage_stateof_charge_fraction is not None:
            source_fields['MaximumStorageStateofChargeFraction'] = maximum_storage_stateof_charge_fraction
        if minimum_storage_stateof_charge_fraction is not None:
            source_fields['MinimumStorageStateofChargeFraction'] = minimum_storage_stateof_charge_fraction
        if design_storage_control_charge_power is not None:
            source_fields['DesignStorageControlChargePower'] = design_storage_control_charge_power
        if storage_charge_power_fraction_schedule_target is not None:
            source_field_targets['StorageChargePowerFractionSchedule'] = storage_charge_power_fraction_schedule_target
        if design_storage_control_discharge_power is not None:
            source_fields['DesignStorageControlDischargePower'] = design_storage_control_discharge_power
        if storage_discharge_power_fraction_schedule_target is not None:
            source_field_targets['StorageDischargePowerFractionSchedule'] = storage_discharge_power_fraction_schedule_target
        if storage_control_utility_demand_target is not None:
            source_fields['StorageControlUtilityDemandTarget'] = storage_control_utility_demand_target
        if storage_control_utility_demand_target_fraction_schedule_target is not None:
            source_field_targets['StorageControlUtilityDemandTargetFractionSchedule'] = storage_control_utility_demand_target_fraction_schedule_target
        if generators_targets is not None:
            source_property_targets['Generators'] = generators_targets
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ElectricLoadCenterDistribution',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            source_property_targets=source_property_targets or None,
            child_targets=child_targets if any(item is not None for item in child_targets) else None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
