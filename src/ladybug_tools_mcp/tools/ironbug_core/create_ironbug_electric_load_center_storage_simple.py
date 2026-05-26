'MCP tool for detailed_hvac_electric_load_center_storage_simple.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_electric_load_center_storage_simple tool.'

    @mcp.tool(
        name='electric_load_center_storage_simple',
        description=(
            'Create IB_ElectricLoadCenterStorageSimple, an EnergyPlus/OpenStudio ElectricLoadCenter:Storage:Simple object for simplified electrical storage or battery behavior. Use it as the electrical storage target on ElectricLoadCenter:Distribution; the AC/DC role depends on the distribution buss type. This tool authors simple electrical storage input only; it does not create distribution panels, converters, inverters, or run simulation. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'electric', 'electric-equipment', 'load-center', 'storage', 'battery', 'author'},
        timeout=20,
    )
    def create_ironbug_electric_load_center_storage_simple(
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
            Field(description="Stable identifier for the new IB_ElectricLoadCenterStorageSimple object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier controlling simple storage availability; maps to Ironbug field AvailabilitySchedule.'),
        ] = None,
        radiative_fractionfor_zone_heat_gains: Annotated[
            float | None,
            Field(description='Fraction of storage losses released as zone radiative heat gain; maps to Ironbug field RadiativeFractionforZoneHeatGains.'),
        ] = None,
        nominal_energetic_efficiencyfor_charging: Annotated[
            float | None,
            Field(description='Nominal charging efficiency fraction for simple electrical storage; maps to Ironbug field NominalEnergeticEfficiencyforCharging.'),
        ] = None,
        nominal_discharging_energetic_efficiency: Annotated[
            float | None,
            Field(description='Nominal discharging efficiency fraction for simple electrical storage; maps to Ironbug field NominalDischargingEnergeticEfficiency.'),
        ] = None,
        maximum_storage_capacity: Annotated[
            float | None,
            Field(description='Maximum electrical storage capacity in J; maps to Ironbug field MaximumStorageCapacity.'),
        ] = None,
        maximum_powerfor_discharging: Annotated[
            float | None,
            Field(description='Maximum storage discharging power in W; maps to Ironbug field MaximumPowerforDischarging.'),
        ] = None,
        maximum_powerfor_charging: Annotated[
            float | None,
            Field(description='Maximum storage charging power in W; maps to Ironbug field MaximumPowerforCharging.'),
        ] = None,
        initial_stateof_charge: Annotated[
            float | None,
            Field(description='Initial storage state of charge in J; maps to Ironbug field InitialStateofCharge.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio ElectricLoadCenter:Storage:Simple object name; defaults to the identifier when omitted.'),
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
        """Create IB_ElectricLoadCenterStorageSimple as reviewed simple electrical storage data."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if radiative_fractionfor_zone_heat_gains is not None:
            source_fields['RadiativeFractionforZoneHeatGains'] = radiative_fractionfor_zone_heat_gains
        if nominal_energetic_efficiencyfor_charging is not None:
            source_fields['NominalEnergeticEfficiencyforCharging'] = nominal_energetic_efficiencyfor_charging
        if nominal_discharging_energetic_efficiency is not None:
            source_fields['NominalDischargingEnergeticEfficiency'] = nominal_discharging_energetic_efficiency
        if maximum_storage_capacity is not None:
            source_fields['MaximumStorageCapacity'] = maximum_storage_capacity
        if maximum_powerfor_discharging is not None:
            source_fields['MaximumPowerforDischarging'] = maximum_powerfor_discharging
        if maximum_powerfor_charging is not None:
            source_fields['MaximumPowerforCharging'] = maximum_powerfor_charging
        if initial_stateof_charge is not None:
            source_fields['InitialStateofCharge'] = initial_stateof_charge
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ElectricLoadCenterStorageSimple',
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
