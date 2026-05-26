'MCP tool for detailed_hvac_photovoltaic_performance_equivalent_one_diode.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_photovoltaic_performance_equivalent_one_diode tool.'

    @mcp.tool(
        name='photovoltaic_performance_equivalent_one_diode',
        description=(
            'Create IB_PhotovoltaicPerformanceEquivalentOneDiode, an OpenStudio/EnergyPlus PhotovoltaicPerformance:EquivalentOne-Diode child for Generator:Photovoltaic. Use it for PV module electrical and thermal coefficients such as cell type, active area, short/open-circuit values, reference insolation, NOCT, heat loss, and heat capacity. Use separate generator, PVWatts, inverter, or Energy simulation tools for those workflows. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'electric', 'electric-equipment', 'photovoltaic', 'pv', 'performance', 'one-diode', 'author'},
        timeout=20,
    )
    def create_ironbug_photovoltaic_performance_equivalent_one_diode(
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
            Field(description="Stable identifier for the new IB_PhotovoltaicPerformanceEquivalentOneDiode object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        celltype: Annotated[
            str | None,
            Field(description='Optional PV cell type for the equivalent one-diode performance model.'),
        ] = None,
        numberof_cellsin_series: Annotated[
            int | None,
            Field(description='Optional NumberofCellsinSeries value; maps to Ironbug IB_PhotovoltaicPerformanceEquivalentOneDiode field NumberofCellsinSeries.'),
        ] = None,
        active_area: Annotated[
            float | None,
            Field(description='Optional active photovoltaic cell area in m2 for the one-diode model.'),
        ] = None,
        transmittance_absorptance_product: Annotated[
            float | None,
            Field(description='Optional TransmittanceAbsorptanceProduct value; maps to Ironbug IB_PhotovoltaicPerformanceEquivalentOneDiode field TransmittanceAbsorptanceProduct.'),
        ] = None,
        semiconductor_bandgap: Annotated[
            float | None,
            Field(description='Optional SemiconductorBandgap value; maps to Ironbug IB_PhotovoltaicPerformanceEquivalentOneDiode field SemiconductorBandgap.'),
        ] = None,
        shunt_resistance: Annotated[
            float | None,
            Field(description='Optional ShuntResistance value; maps to Ironbug IB_PhotovoltaicPerformanceEquivalentOneDiode field ShuntResistance.'),
        ] = None,
        short_circuit_current: Annotated[
            float | None,
            Field(description='Optional short-circuit current for the PV module at reference conditions.'),
        ] = None,
        open_circuit_voltage: Annotated[
            float | None,
            Field(description='Optional open-circuit voltage for the PV module at reference conditions.'),
        ] = None,
        reference_temperature: Annotated[
            float | None,
            Field(description='Optional ReferenceTemperature value; maps to Ironbug IB_PhotovoltaicPerformanceEquivalentOneDiode field ReferenceTemperature.'),
        ] = None,
        reference_insolation: Annotated[
            float | None,
            Field(description='Optional ReferenceInsolation value; maps to Ironbug IB_PhotovoltaicPerformanceEquivalentOneDiode field ReferenceInsolation.'),
        ] = None,
        module_currentat_maximum_power: Annotated[
            float | None,
            Field(description='Optional ModuleCurrentatMaximumPower value; maps to Ironbug IB_PhotovoltaicPerformanceEquivalentOneDiode field ModuleCurrentatMaximumPower.'),
        ] = None,
        module_voltageat_maximum_power: Annotated[
            float | None,
            Field(description='Optional ModuleVoltageatMaximumPower value; maps to Ironbug IB_PhotovoltaicPerformanceEquivalentOneDiode field ModuleVoltageatMaximumPower.'),
        ] = None,
        temperature_coefficientof_short_circuit_current: Annotated[
            float | None,
            Field(description='Optional TemperatureCoefficientofShortCircuitCurrent value; maps to Ironbug IB_PhotovoltaicPerformanceEquivalentOneDiode field TemperatureCoefficientofShortCircuitCurrent.'),
        ] = None,
        temperature_coefficientof_open_circuit_voltage: Annotated[
            float | None,
            Field(description='Optional TemperatureCoefficientofOpenCircuitVoltage value; maps to Ironbug IB_PhotovoltaicPerformanceEquivalentOneDiode field TemperatureCoefficientofOpenCircuitVoltage.'),
        ] = None,
        nominal_operating_cell_temperature_test_ambient_temperature: Annotated[
            float | None,
            Field(description='Optional NominalOperatingCellTemperatureTestAmbientTemperature value; maps to Ironbug IB_PhotovoltaicPerformanceEquivalentOneDiode field NominalOperatingCellTemperatureTestAmbientTemperature.'),
        ] = None,
        nominal_operating_cell_temperature_test_cell_temperature: Annotated[
            float | None,
            Field(description='Optional NominalOperatingCellTemperatureTestCellTemperature value; maps to Ironbug IB_PhotovoltaicPerformanceEquivalentOneDiode field NominalOperatingCellTemperatureTestCellTemperature.'),
        ] = None,
        nominal_operating_cell_temperature_test_insolation: Annotated[
            float | None,
            Field(description='Optional NominalOperatingCellTemperatureTestInsolation value; maps to Ironbug IB_PhotovoltaicPerformanceEquivalentOneDiode field NominalOperatingCellTemperatureTestInsolation.'),
        ] = None,
        module_heat_loss_coefficient: Annotated[
            float | None,
            Field(description='Optional ModuleHeatLossCoefficient value; maps to Ironbug IB_PhotovoltaicPerformanceEquivalentOneDiode field ModuleHeatLossCoefficient.'),
        ] = None,
        total_heat_capacity: Annotated[
            float | None,
            Field(description='Optional TotalHeatCapacity value; maps to Ironbug IB_PhotovoltaicPerformanceEquivalentOneDiode field TotalHeatCapacity.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio name for the equivalent one-diode photovoltaic performance object.'),
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
        """Create IB_PhotovoltaicPerformanceEquivalentOneDiode as a reviewed Ironbug Electrical authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if celltype is not None:
            source_fields['Celltype'] = celltype
        if numberof_cellsin_series is not None:
            source_fields['NumberofCellsinSeries'] = numberof_cellsin_series
        if active_area is not None:
            source_fields['ActiveArea'] = active_area
        if transmittance_absorptance_product is not None:
            source_fields['TransmittanceAbsorptanceProduct'] = transmittance_absorptance_product
        if semiconductor_bandgap is not None:
            source_fields['SemiconductorBandgap'] = semiconductor_bandgap
        if shunt_resistance is not None:
            source_fields['ShuntResistance'] = shunt_resistance
        if short_circuit_current is not None:
            source_fields['ShortCircuitCurrent'] = short_circuit_current
        if open_circuit_voltage is not None:
            source_fields['OpenCircuitVoltage'] = open_circuit_voltage
        if reference_temperature is not None:
            source_fields['ReferenceTemperature'] = reference_temperature
        if reference_insolation is not None:
            source_fields['ReferenceInsolation'] = reference_insolation
        if module_currentat_maximum_power is not None:
            source_fields['ModuleCurrentatMaximumPower'] = module_currentat_maximum_power
        if module_voltageat_maximum_power is not None:
            source_fields['ModuleVoltageatMaximumPower'] = module_voltageat_maximum_power
        if temperature_coefficientof_short_circuit_current is not None:
            source_fields['TemperatureCoefficientofShortCircuitCurrent'] = temperature_coefficientof_short_circuit_current
        if temperature_coefficientof_open_circuit_voltage is not None:
            source_fields['TemperatureCoefficientofOpenCircuitVoltage'] = temperature_coefficientof_open_circuit_voltage
        if nominal_operating_cell_temperature_test_ambient_temperature is not None:
            source_fields['NominalOperatingCellTemperatureTestAmbientTemperature'] = nominal_operating_cell_temperature_test_ambient_temperature
        if nominal_operating_cell_temperature_test_cell_temperature is not None:
            source_fields['NominalOperatingCellTemperatureTestCellTemperature'] = nominal_operating_cell_temperature_test_cell_temperature
        if nominal_operating_cell_temperature_test_insolation is not None:
            source_fields['NominalOperatingCellTemperatureTestInsolation'] = nominal_operating_cell_temperature_test_insolation
        if module_heat_loss_coefficient is not None:
            source_fields['ModuleHeatLossCoefficient'] = module_heat_loss_coefficient
        if total_heat_capacity is not None:
            source_fields['TotalHeatCapacity'] = total_heat_capacity
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_PhotovoltaicPerformanceEquivalentOneDiode',
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
