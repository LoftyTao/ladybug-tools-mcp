'MCP tool for detailed_hvac_electric_load_center.'

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_electric_load_center tool.'

    @mcp.tool(
        name='electric_load_center',
        description=(
            'Create IB_ElectricLoadCenter, the Ironbug root container for ElectricLoadCenter:Distribution subpanels plus optional grid input and grid export transformers. Use it to group reviewed load-center distribution targets, PowerInFromGrid transformers, and PowerOutToGrid transformers inside an Ironbug DetailedHVAC model. This tool authors load-center assembly input only; it does not create PV arrays, generator models, tariffs, facility meters, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'electric', 'electric-equipment', 'electric-load-center', 'load-center', 'distribution', 'transformer', 'author'},
        timeout=20,
    )
    def create_ironbug_electric_load_center(
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
            Field(description="Stable identifier for the new IB_ElectricLoadCenter object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        sub_panels_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_ElectricLoadCenterDistribution targets or same-model identifiers for load-center subpanels."
            ),
        ] = None,
        power_in_transformer_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional IB_ElectricLoadCenterTransformer target or same-model identifier for grid-to-building power input, normally TransformerUsage PowerInFromGrid."
            ),
        ] = None,
        power_out_transformer_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional IB_ElectricLoadCenterTransformer target or same-model identifier for building-to-grid power export, normally TransformerUsage PowerOutToGrid."
            ),
        ] = None,
        power_in_transformer_identifier: Annotated[
            str | None,
            Field(description='Identifier for an inline PowerInTransformer child used for grid-to-building power input.'),
        ] = None,
        power_in_transformer_name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio object name for the inline PowerInTransformer child.'),
        ] = None,
        power_in_transformer_availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier controlling inline PowerInTransformer availability.'),
        ] = None,
        power_in_transformer_transformer_usage: Annotated[
            str | None,
            Field(description='TransformerUsage for the inline PowerInTransformer child, normally PowerInFromGrid.'),
        ] = None,
        power_in_transformer_radiative_fraction: Annotated[
            float | None,
            Field(description='Fraction of inline PowerInTransformer losses released as zone radiative heat gain.'),
        ] = None,
        power_in_transformer_rated_capacity: Annotated[
            float | None,
            Field(description='Rated capacity in VA for the inline PowerInTransformer child.'),
        ] = None,
        power_in_transformer_phase: Annotated[
            str | None,
            Field(description='Transformer phase selection for the inline PowerInTransformer child.'),
        ] = None,
        power_in_transformer_conductor_material: Annotated[
            str | None,
            Field(description='Conductor material for the inline PowerInTransformer child.'),
        ] = None,
        power_in_transformer_full_load_temperature_rise: Annotated[
            float | None,
            Field(description='Full-load temperature rise in K for the inline PowerInTransformer child.'),
        ] = None,
        power_in_transformer_fractionof_eddy_current_losses: Annotated[
            float | None,
            Field(description='Fraction of inline PowerInTransformer losses assigned to eddy-current losses.'),
        ] = None,
        power_in_transformer_performance_input_method: Annotated[
            str | None,
            Field(description='Performance input method for the inline PowerInTransformer child.'),
        ] = None,
        power_in_transformer_rated_no_load_loss: Annotated[
            float | None,
            Field(description='Rated no-load loss in W for the inline PowerInTransformer child.'),
        ] = None,
        power_in_transformer_rated_load_loss: Annotated[
            float | None,
            Field(description='Rated load loss in W for the inline PowerInTransformer child.'),
        ] = None,
        power_in_transformer_nameplate_efficiency: Annotated[
            float | None,
            Field(description='Nameplate efficiency fraction for the inline PowerInTransformer child.'),
        ] = None,
        power_in_transformer_per_unit_loadfor_nameplate_efficiency: Annotated[
            float | None,
            Field(description='Per-unit load at which inline PowerInTransformer nameplate efficiency applies.'),
        ] = None,
        power_in_transformer_reference_temperaturefor_nameplate_efficiency: Annotated[
            float | None,
            Field(description='Reference temperature in C for inline PowerInTransformer nameplate efficiency.'),
        ] = None,
        power_in_transformer_per_unit_loadfor_maximum_efficiency: Annotated[
            float | None,
            Field(description='Per-unit load at which inline PowerInTransformer efficiency is maximum.'),
        ] = None,
        power_in_transformer_consider_transformer_lossfor_utility_cost: Annotated[
            bool | str | None,
            Field(description='Whether inline PowerInTransformer losses are considered in utility-cost calculations.'),
        ] = None,
        power_out_transformer_identifier: Annotated[
            str | None,
            Field(description='Identifier for an inline PowerOutTransformer child used for building-to-grid power export.'),
        ] = None,
        power_out_transformer_name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio object name for the inline PowerOutTransformer child.'),
        ] = None,
        power_out_transformer_availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier controlling inline PowerOutTransformer availability.'),
        ] = None,
        power_out_transformer_transformer_usage: Annotated[
            str | None,
            Field(description='TransformerUsage for the inline PowerOutTransformer child, normally PowerOutToGrid.'),
        ] = None,
        power_out_transformer_radiative_fraction: Annotated[
            float | None,
            Field(description='Fraction of inline PowerOutTransformer losses released as zone radiative heat gain.'),
        ] = None,
        power_out_transformer_rated_capacity: Annotated[
            float | None,
            Field(description='Rated capacity in VA for the inline PowerOutTransformer child.'),
        ] = None,
        power_out_transformer_phase: Annotated[
            str | None,
            Field(description='Transformer phase selection for the inline PowerOutTransformer child.'),
        ] = None,
        power_out_transformer_conductor_material: Annotated[
            str | None,
            Field(description='Conductor material for the inline PowerOutTransformer child.'),
        ] = None,
        power_out_transformer_full_load_temperature_rise: Annotated[
            float | None,
            Field(description='Full-load temperature rise in K for the inline PowerOutTransformer child.'),
        ] = None,
        power_out_transformer_fractionof_eddy_current_losses: Annotated[
            float | None,
            Field(description='Fraction of inline PowerOutTransformer losses assigned to eddy-current losses.'),
        ] = None,
        power_out_transformer_performance_input_method: Annotated[
            str | None,
            Field(description='Performance input method for the inline PowerOutTransformer child.'),
        ] = None,
        power_out_transformer_rated_no_load_loss: Annotated[
            float | None,
            Field(description='Rated no-load loss in W for the inline PowerOutTransformer child.'),
        ] = None,
        power_out_transformer_rated_load_loss: Annotated[
            float | None,
            Field(description='Rated load loss in W for the inline PowerOutTransformer child.'),
        ] = None,
        power_out_transformer_nameplate_efficiency: Annotated[
            float | None,
            Field(description='Nameplate efficiency fraction for the inline PowerOutTransformer child.'),
        ] = None,
        power_out_transformer_per_unit_loadfor_nameplate_efficiency: Annotated[
            float | None,
            Field(description='Per-unit load at which inline PowerOutTransformer nameplate efficiency applies.'),
        ] = None,
        power_out_transformer_reference_temperaturefor_nameplate_efficiency: Annotated[
            float | None,
            Field(description='Reference temperature in C for inline PowerOutTransformer nameplate efficiency.'),
        ] = None,
        power_out_transformer_per_unit_loadfor_maximum_efficiency: Annotated[
            float | None,
            Field(description='Per-unit load at which inline PowerOutTransformer efficiency is maximum.'),
        ] = None,
        power_out_transformer_consider_transformer_lossfor_utility_cost: Annotated[
            bool | str | None,
            Field(description='Whether inline PowerOutTransformer losses are considered in utility-cost calculations.'),
        ] = None,
        sub_panels_identifiers: Annotated[
            list[str] | None,
            Field(description='Identifiers for inline ElectricLoadCenter:Distribution subpanel children.'),
        ] = None,
        sub_panels_name_values: Annotated[
            list[str | None] | None,
            Field(description='Optional EnergyPlus/OpenStudio object names for inline ElectricLoadCenter:Distribution subpanel children.'),
        ] = None,
        sub_panels_generator_operation_scheme_type_values: Annotated[
            list[str | None] | None,
            Field(description='Generator dispatch scheme values for inline subpanel children.'),
        ] = None,
        sub_panels_demand_limit_scheme_purchased_electric_demand_limit_values: Annotated[
            list[float | None] | None,
            Field(description='Purchased-electric demand limits in W for inline subpanel demand-limit dispatch.'),
        ] = None,
        sub_panels_track_schedule_scheme_schedule_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional IB_Schedule targets or same-model identifiers for inline subpanel scheduled generator dispatch.'),
        ] = None,
        sub_panels_track_meter_scheme_meter_name_values: Annotated[
            list[str | None] | None,
            Field(description='EnergyPlus meter names tracked by inline subpanel meter-based generator dispatch.'),
        ] = None,
        sub_panels_electrical_buss_type_values: Annotated[
            list[str | None] | None,
            Field(description='Electrical buss type values for inline subpanel AC, DC, inverter, and storage configuration.'),
        ] = None,
        sub_panels_storage_operation_scheme_values: Annotated[
            list[str | None] | None,
            Field(description='Electrical storage dispatch scheme values for inline subpanel children.'),
        ] = None,
        sub_panels_storage_control_track_meter_name_values: Annotated[
            list[str | None] | None,
            Field(description='EnergyPlus meter names used by inline subpanel storage control.'),
        ] = None,
        sub_panels_maximum_storage_stateof_charge_fraction_values: Annotated[
            list[float | None] | None,
            Field(description='Upper storage state-of-charge fractions for inline subpanel children.'),
        ] = None,
        sub_panels_minimum_storage_stateof_charge_fraction_values: Annotated[
            list[float | None] | None,
            Field(description='Lower storage state-of-charge fractions for inline subpanel children.'),
        ] = None,
        sub_panels_design_storage_control_charge_power_values: Annotated[
            list[float | None] | None,
            Field(description='Design storage charging power values in W for inline subpanel children.'),
        ] = None,
        sub_panels_storage_charge_power_fraction_schedule_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional IB_Schedule targets or same-model identifiers for inline subpanel storage charge-power fraction.'),
        ] = None,
        sub_panels_design_storage_control_discharge_power_values: Annotated[
            list[float | None] | None,
            Field(description='Design storage discharging power values in W for inline subpanel children.'),
        ] = None,
        sub_panels_storage_discharge_power_fraction_schedule_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional IB_Schedule targets or same-model identifiers for inline subpanel storage discharge-power fraction.'),
        ] = None,
        sub_panels_storage_control_utility_demand_target_values: Annotated[
            list[float | None] | None,
            Field(description='Utility demand target values in W for inline subpanel storage demand-leveling control.'),
        ] = None,
        sub_panels_storage_control_utility_demand_target_fraction_schedule_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional IB_Schedule targets or same-model identifiers for inline subpanel utility-demand target fraction.'),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_ElectricLoadCenter as reviewed load-center assembly data."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        inline_source_property_children: dict[str, Any] = {}
        if sub_panels_targets is not None:
            source_property_targets['SubPanels'] = sub_panels_targets
        if power_in_transformer_target is not None:
            source_property_targets['PowerInTransformer'] = power_in_transformer_target
        if power_out_transformer_target is not None:
            source_property_targets['PowerOutTransformer'] = power_out_transformer_target
        inline_power_in_transformer_fields: dict[str, Any] = {}
        inline_power_in_transformer_field_targets: dict[str, Any] = {}
        if power_in_transformer_name is not None:
            inline_power_in_transformer_fields['Name'] = power_in_transformer_name
        if power_in_transformer_availability_schedule_target is not None:
            inline_power_in_transformer_field_targets['AvailabilitySchedule'] = power_in_transformer_availability_schedule_target
        if power_in_transformer_transformer_usage is not None:
            inline_power_in_transformer_fields['TransformerUsage'] = power_in_transformer_transformer_usage
        if power_in_transformer_radiative_fraction is not None:
            inline_power_in_transformer_fields['RadiativeFraction'] = power_in_transformer_radiative_fraction
        if power_in_transformer_rated_capacity is not None:
            inline_power_in_transformer_fields['RatedCapacity'] = power_in_transformer_rated_capacity
        if power_in_transformer_phase is not None:
            inline_power_in_transformer_fields['Phase'] = power_in_transformer_phase
        if power_in_transformer_conductor_material is not None:
            inline_power_in_transformer_fields['ConductorMaterial'] = power_in_transformer_conductor_material
        if power_in_transformer_full_load_temperature_rise is not None:
            inline_power_in_transformer_fields['FullLoadTemperatureRise'] = power_in_transformer_full_load_temperature_rise
        if power_in_transformer_fractionof_eddy_current_losses is not None:
            inline_power_in_transformer_fields['FractionofEddyCurrentLosses'] = power_in_transformer_fractionof_eddy_current_losses
        if power_in_transformer_performance_input_method is not None:
            inline_power_in_transformer_fields['PerformanceInputMethod'] = power_in_transformer_performance_input_method
        if power_in_transformer_rated_no_load_loss is not None:
            inline_power_in_transformer_fields['RatedNoLoadLoss'] = power_in_transformer_rated_no_load_loss
        if power_in_transformer_rated_load_loss is not None:
            inline_power_in_transformer_fields['RatedLoadLoss'] = power_in_transformer_rated_load_loss
        if power_in_transformer_nameplate_efficiency is not None:
            inline_power_in_transformer_fields['NameplateEfficiency'] = power_in_transformer_nameplate_efficiency
        if power_in_transformer_per_unit_loadfor_nameplate_efficiency is not None:
            inline_power_in_transformer_fields['PerUnitLoadforNameplateEfficiency'] = power_in_transformer_per_unit_loadfor_nameplate_efficiency
        if power_in_transformer_reference_temperaturefor_nameplate_efficiency is not None:
            inline_power_in_transformer_fields['ReferenceTemperatureforNameplateEfficiency'] = power_in_transformer_reference_temperaturefor_nameplate_efficiency
        if power_in_transformer_per_unit_loadfor_maximum_efficiency is not None:
            inline_power_in_transformer_fields['PerUnitLoadforMaximumEfficiency'] = power_in_transformer_per_unit_loadfor_maximum_efficiency
        if power_in_transformer_consider_transformer_lossfor_utility_cost is not None:
            inline_power_in_transformer_fields['ConsiderTransformerLossforUtilityCost'] = power_in_transformer_consider_transformer_lossfor_utility_cost
        if power_in_transformer_identifier is not None or inline_power_in_transformer_fields or inline_power_in_transformer_field_targets:
            if power_in_transformer_target is not None:
                raise ValueError("Provide either power_in_transformer_target or inline power_in_transformer_* parameters, not both.")
            inline_source_property_children['PowerInTransformer'] = {
                'source_class': 'IB_ElectricLoadCenterTransformer',
                'is_list': False,
                'identifiers': power_in_transformer_identifier,
                'source_fields': inline_power_in_transformer_fields,
                'source_field_targets': inline_power_in_transformer_field_targets,
            }
        inline_power_out_transformer_fields: dict[str, Any] = {}
        inline_power_out_transformer_field_targets: dict[str, Any] = {}
        if power_out_transformer_name is not None:
            inline_power_out_transformer_fields['Name'] = power_out_transformer_name
        if power_out_transformer_availability_schedule_target is not None:
            inline_power_out_transformer_field_targets['AvailabilitySchedule'] = power_out_transformer_availability_schedule_target
        if power_out_transformer_transformer_usage is not None:
            inline_power_out_transformer_fields['TransformerUsage'] = power_out_transformer_transformer_usage
        if power_out_transformer_radiative_fraction is not None:
            inline_power_out_transformer_fields['RadiativeFraction'] = power_out_transformer_radiative_fraction
        if power_out_transformer_rated_capacity is not None:
            inline_power_out_transformer_fields['RatedCapacity'] = power_out_transformer_rated_capacity
        if power_out_transformer_phase is not None:
            inline_power_out_transformer_fields['Phase'] = power_out_transformer_phase
        if power_out_transformer_conductor_material is not None:
            inline_power_out_transformer_fields['ConductorMaterial'] = power_out_transformer_conductor_material
        if power_out_transformer_full_load_temperature_rise is not None:
            inline_power_out_transformer_fields['FullLoadTemperatureRise'] = power_out_transformer_full_load_temperature_rise
        if power_out_transformer_fractionof_eddy_current_losses is not None:
            inline_power_out_transformer_fields['FractionofEddyCurrentLosses'] = power_out_transformer_fractionof_eddy_current_losses
        if power_out_transformer_performance_input_method is not None:
            inline_power_out_transformer_fields['PerformanceInputMethod'] = power_out_transformer_performance_input_method
        if power_out_transformer_rated_no_load_loss is not None:
            inline_power_out_transformer_fields['RatedNoLoadLoss'] = power_out_transformer_rated_no_load_loss
        if power_out_transformer_rated_load_loss is not None:
            inline_power_out_transformer_fields['RatedLoadLoss'] = power_out_transformer_rated_load_loss
        if power_out_transformer_nameplate_efficiency is not None:
            inline_power_out_transformer_fields['NameplateEfficiency'] = power_out_transformer_nameplate_efficiency
        if power_out_transformer_per_unit_loadfor_nameplate_efficiency is not None:
            inline_power_out_transformer_fields['PerUnitLoadforNameplateEfficiency'] = power_out_transformer_per_unit_loadfor_nameplate_efficiency
        if power_out_transformer_reference_temperaturefor_nameplate_efficiency is not None:
            inline_power_out_transformer_fields['ReferenceTemperatureforNameplateEfficiency'] = power_out_transformer_reference_temperaturefor_nameplate_efficiency
        if power_out_transformer_per_unit_loadfor_maximum_efficiency is not None:
            inline_power_out_transformer_fields['PerUnitLoadforMaximumEfficiency'] = power_out_transformer_per_unit_loadfor_maximum_efficiency
        if power_out_transformer_consider_transformer_lossfor_utility_cost is not None:
            inline_power_out_transformer_fields['ConsiderTransformerLossforUtilityCost'] = power_out_transformer_consider_transformer_lossfor_utility_cost
        if power_out_transformer_identifier is not None or inline_power_out_transformer_fields or inline_power_out_transformer_field_targets:
            if power_out_transformer_target is not None:
                raise ValueError("Provide either power_out_transformer_target or inline power_out_transformer_* parameters, not both.")
            inline_source_property_children['PowerOutTransformer'] = {
                'source_class': 'IB_ElectricLoadCenterTransformer',
                'is_list': False,
                'identifiers': power_out_transformer_identifier,
                'source_fields': inline_power_out_transformer_fields,
                'source_field_targets': inline_power_out_transformer_field_targets,
            }
        inline_sub_panels_fields: dict[str, Any] = {}
        inline_sub_panels_field_targets: dict[str, Any] = {}
        if sub_panels_name_values is not None:
            inline_sub_panels_fields['Name'] = sub_panels_name_values
        if sub_panels_generator_operation_scheme_type_values is not None:
            inline_sub_panels_fields['GeneratorOperationSchemeType'] = sub_panels_generator_operation_scheme_type_values
        if sub_panels_demand_limit_scheme_purchased_electric_demand_limit_values is not None:
            inline_sub_panels_fields['DemandLimitSchemePurchasedElectricDemandLimit'] = sub_panels_demand_limit_scheme_purchased_electric_demand_limit_values
        if sub_panels_track_schedule_scheme_schedule_targets is not None:
            inline_sub_panels_field_targets['TrackScheduleSchemeSchedule'] = sub_panels_track_schedule_scheme_schedule_targets
        if sub_panels_track_meter_scheme_meter_name_values is not None:
            inline_sub_panels_fields['TrackMeterSchemeMeterName'] = sub_panels_track_meter_scheme_meter_name_values
        if sub_panels_electrical_buss_type_values is not None:
            inline_sub_panels_fields['ElectricalBussType'] = sub_panels_electrical_buss_type_values
        if sub_panels_storage_operation_scheme_values is not None:
            inline_sub_panels_fields['StorageOperationScheme'] = sub_panels_storage_operation_scheme_values
        if sub_panels_storage_control_track_meter_name_values is not None:
            inline_sub_panels_fields['StorageControlTrackMeterName'] = sub_panels_storage_control_track_meter_name_values
        if sub_panels_maximum_storage_stateof_charge_fraction_values is not None:
            inline_sub_panels_fields['MaximumStorageStateofChargeFraction'] = sub_panels_maximum_storage_stateof_charge_fraction_values
        if sub_panels_minimum_storage_stateof_charge_fraction_values is not None:
            inline_sub_panels_fields['MinimumStorageStateofChargeFraction'] = sub_panels_minimum_storage_stateof_charge_fraction_values
        if sub_panels_design_storage_control_charge_power_values is not None:
            inline_sub_panels_fields['DesignStorageControlChargePower'] = sub_panels_design_storage_control_charge_power_values
        if sub_panels_storage_charge_power_fraction_schedule_targets is not None:
            inline_sub_panels_field_targets['StorageChargePowerFractionSchedule'] = sub_panels_storage_charge_power_fraction_schedule_targets
        if sub_panels_design_storage_control_discharge_power_values is not None:
            inline_sub_panels_fields['DesignStorageControlDischargePower'] = sub_panels_design_storage_control_discharge_power_values
        if sub_panels_storage_discharge_power_fraction_schedule_targets is not None:
            inline_sub_panels_field_targets['StorageDischargePowerFractionSchedule'] = sub_panels_storage_discharge_power_fraction_schedule_targets
        if sub_panels_storage_control_utility_demand_target_values is not None:
            inline_sub_panels_fields['StorageControlUtilityDemandTarget'] = sub_panels_storage_control_utility_demand_target_values
        if sub_panels_storage_control_utility_demand_target_fraction_schedule_targets is not None:
            inline_sub_panels_field_targets['StorageControlUtilityDemandTargetFractionSchedule'] = sub_panels_storage_control_utility_demand_target_fraction_schedule_targets
        if sub_panels_identifiers is not None or inline_sub_panels_fields or inline_sub_panels_field_targets:
            if sub_panels_targets is not None:
                raise ValueError("Provide either sub_panels_targets or inline sub_panels_* parameters, not both.")
            inline_source_property_children['SubPanels'] = {
                'source_class': 'IB_ElectricLoadCenterDistribution',
                'is_list': True,
                'identifiers': sub_panels_identifiers,
                'source_fields': inline_sub_panels_fields,
                'source_field_targets': inline_sub_panels_field_targets,
            }
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ElectricLoadCenter',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            source_property_targets=source_property_targets or None,
            inline_source_property_children=inline_source_property_children or None,
            overwrite=overwrite,
        )
