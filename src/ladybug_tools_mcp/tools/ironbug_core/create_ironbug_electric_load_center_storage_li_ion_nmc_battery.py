'MCP tool for detailed_hvac_electric_load_center_storage_li_ion_nmc_battery.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_electric_load_center_storage_li_ion_nmc_battery tool.'

    @mcp.tool(
        name='electric_load_center_storage_li_ion_nmc_battery',
        description=(
            'Create IB_ElectricLoadCenterStorageLiIonNMCBattery, an EnergyPlus/OpenStudio ElectricLoadCenter:Storage:LiIonNMCBattery object for detailed lithium-ion NMC battery storage. Use it as the electrical storage target on ElectricLoadCenter:Distribution when cell/string, voltage, capacity, thermal, and internal-resistance inputs are known. This tool authors battery storage input only; it does not create distribution panels, converters, inverters, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'electric', 'electric-equipment', 'load-center', 'storage', 'battery', 'author'},
        timeout=20,
    )
    def create_ironbug_electric_load_center_storage_li_ion_nmc_battery(
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
            Field(description="Stable identifier for the new IB_ElectricLoadCenterStorageLiIonNMCBattery object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier controlling lithium-ion battery availability; maps to Ironbug field AvailabilitySchedule.'),
        ] = None,
        radiative_fraction: Annotated[
            float | None,
            Field(description='Fraction of battery losses released as zone radiative heat gain; maps to Ironbug field RadiativeFraction.'),
        ] = None,
        lifetime_model: Annotated[
            str | None,
            Field(description='Battery lifetime model selection for lithium-ion NMC storage; maps to Ironbug field LifetimeModel.'),
        ] = None,
        numberof_cellsin_series: Annotated[
            int | None,
            Field(description='Number of battery cells connected in series; maps to Ironbug field NumberofCellsinSeries.'),
        ] = None,
        numberof_stringsin_parallel: Annotated[
            int | None,
            Field(description='Number of battery strings connected in parallel; maps to Ironbug field NumberofStringsinParallel.'),
        ] = None,
        initial_fractional_stateof_charge: Annotated[
            float | None,
            Field(description='Initial fractional state of charge for the battery; maps to Ironbug field InitialFractionalStateofCharge.'),
        ] = None,
        d_cto_dc_charging_efficiency: Annotated[
            float | None,
            Field(description='DC-to-DC charging efficiency fraction; maps to Ironbug field DCtoDCChargingEfficiency.'),
        ] = None,
        battery_mass: Annotated[
            float | None,
            Field(description='Battery mass for the thermal model in kg; maps to Ironbug field BatteryMass.'),
        ] = None,
        battery_surface_area: Annotated[
            float | None,
            Field(description='Battery surface area for heat transfer in m2; maps to Ironbug field BatterySurfaceArea.'),
        ] = None,
        battery_specific_heat_capacity: Annotated[
            float | None,
            Field(description='Battery specific heat capacity in J/kg-K; maps to Ironbug field BatterySpecificHeatCapacity.'),
        ] = None,
        heat_transfer_coefficient_between_batteryand_ambient: Annotated[
            float | None,
            Field(description='Heat transfer coefficient between battery and ambient conditions in W/m2-K; maps to Ironbug field HeatTransferCoefficientBetweenBatteryandAmbient.'),
        ] = None,
        fully_charged_cell_voltage: Annotated[
            float | None,
            Field(description='Fully charged cell voltage in V; maps to Ironbug field FullyChargedCellVoltage.'),
        ] = None,
        cell_voltageat_endof_exponential_zone: Annotated[
            float | None,
            Field(description='Cell voltage at the end of the exponential zone in V; maps to Ironbug field CellVoltageatEndofExponentialZone.'),
        ] = None,
        cell_voltageat_endof_nominal_zone: Annotated[
            float | None,
            Field(description='Cell voltage at the end of the nominal zone in V; maps to Ironbug field CellVoltageatEndofNominalZone.'),
        ] = None,
        default_nominal_cell_voltage: Annotated[
            float | None,
            Field(description='Default nominal cell voltage in V; maps to Ironbug field DefaultNominalCellVoltage.'),
        ] = None,
        fully_charged_cell_capacity: Annotated[
            float | None,
            Field(description='Fully charged cell capacity; maps to Ironbug field FullyChargedCellCapacity.'),
        ] = None,
        fractionof_cell_capacity_removedatthe_endof_exponential_zone: Annotated[
            float | None,
            Field(description='Fraction of cell capacity removed at the end of the exponential zone; maps to Ironbug field FractionofCellCapacityRemovedattheEndofExponentialZone.'),
        ] = None,
        fractionof_cell_capacity_removedatthe_endof_nominal_zone: Annotated[
            float | None,
            Field(description='Fraction of cell capacity removed at the end of the nominal zone; maps to Ironbug field FractionofCellCapacityRemovedattheEndofNominalZone.'),
        ] = None,
        charge_rateat_which_voltagevs_capacity_curve_was_generated_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target or same-model identifier for the charge-rate curve used to generate voltage-vs-capacity data; maps to Ironbug field ChargeRateatWhichVoltagevsCapacityCurveWasGenerated.'),
        ] = None,
        battery_cell_internal_electrical_resistance: Annotated[
            float | None,
            Field(description='Battery cell internal electrical resistance in ohms; maps to Ironbug field BatteryCellInternalElectricalResistance.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio ElectricLoadCenter:Storage:LiIonNMCBattery object name; defaults to the identifier when omitted.'),
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
        """Create IB_ElectricLoadCenterStorageLiIonNMCBattery as reviewed lithium-ion NMC battery data."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if radiative_fraction is not None:
            source_fields['RadiativeFraction'] = radiative_fraction
        if lifetime_model is not None:
            source_fields['LifetimeModel'] = lifetime_model
        if numberof_cellsin_series is not None:
            source_fields['NumberofCellsinSeries'] = numberof_cellsin_series
        if numberof_stringsin_parallel is not None:
            source_fields['NumberofStringsinParallel'] = numberof_stringsin_parallel
        if initial_fractional_stateof_charge is not None:
            source_fields['InitialFractionalStateofCharge'] = initial_fractional_stateof_charge
        if d_cto_dc_charging_efficiency is not None:
            source_fields['DCtoDCChargingEfficiency'] = d_cto_dc_charging_efficiency
        if battery_mass is not None:
            source_fields['BatteryMass'] = battery_mass
        if battery_surface_area is not None:
            source_fields['BatterySurfaceArea'] = battery_surface_area
        if battery_specific_heat_capacity is not None:
            source_fields['BatterySpecificHeatCapacity'] = battery_specific_heat_capacity
        if heat_transfer_coefficient_between_batteryand_ambient is not None:
            source_fields['HeatTransferCoefficientBetweenBatteryandAmbient'] = heat_transfer_coefficient_between_batteryand_ambient
        if fully_charged_cell_voltage is not None:
            source_fields['FullyChargedCellVoltage'] = fully_charged_cell_voltage
        if cell_voltageat_endof_exponential_zone is not None:
            source_fields['CellVoltageatEndofExponentialZone'] = cell_voltageat_endof_exponential_zone
        if cell_voltageat_endof_nominal_zone is not None:
            source_fields['CellVoltageatEndofNominalZone'] = cell_voltageat_endof_nominal_zone
        if default_nominal_cell_voltage is not None:
            source_fields['DefaultNominalCellVoltage'] = default_nominal_cell_voltage
        if fully_charged_cell_capacity is not None:
            source_fields['FullyChargedCellCapacity'] = fully_charged_cell_capacity
        if fractionof_cell_capacity_removedatthe_endof_exponential_zone is not None:
            source_fields['FractionofCellCapacityRemovedattheEndofExponentialZone'] = fractionof_cell_capacity_removedatthe_endof_exponential_zone
        if fractionof_cell_capacity_removedatthe_endof_nominal_zone is not None:
            source_fields['FractionofCellCapacityRemovedattheEndofNominalZone'] = fractionof_cell_capacity_removedatthe_endof_nominal_zone
        if charge_rateat_which_voltagevs_capacity_curve_was_generated_target is not None:
            source_field_targets['ChargeRateatWhichVoltagevsCapacityCurveWasGenerated'] = charge_rateat_which_voltagevs_capacity_curve_was_generated_target
        if battery_cell_internal_electrical_resistance is not None:
            source_fields['BatteryCellInternalElectricalResistance'] = battery_cell_internal_electrical_resistance
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ElectricLoadCenterStorageLiIonNMCBattery',
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
