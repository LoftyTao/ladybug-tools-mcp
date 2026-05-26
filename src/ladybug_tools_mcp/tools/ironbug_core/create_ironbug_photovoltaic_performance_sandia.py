'MCP tool for detailed_hvac_photovoltaic_performance_sandia.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_photovoltaic_performance_sandia tool.'

    @mcp.tool(
        name='photovoltaic_performance_sandia',
        description=(
            'Create IB_PhotovoltaicPerformanceSandia, an OpenStudio/EnergyPlus PhotovoltaicPerformance:Sandia child for Generator:Photovoltaic. Use it for Sandia PV module coefficients, cell strings, current/voltage points, temperature coefficients, and irradiance modifiers. Use separate generator, PVWatts, inverter, or Energy simulation tools for those workflows. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'electric', 'electric-equipment', 'photovoltaic', 'pv', 'performance', 'sandia', 'author'},
        timeout=20,
    )
    def create_ironbug_photovoltaic_performance_sandia(
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
            Field(description="Stable identifier for the new IB_PhotovoltaicPerformanceSandia object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        active_area: Annotated[
            float | None,
            Field(description='Optional active photovoltaic cell area in m2 for the Sandia performance model.'),
        ] = None,
        numberof_cellsin_series: Annotated[
            int | None,
            Field(description='Optional NumberofCellsinSeries value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field NumberofCellsinSeries.'),
        ] = None,
        numberof_cellsin_parallel: Annotated[
            int | None,
            Field(description='Optional NumberofCellsinParallel value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field NumberofCellsinParallel.'),
        ] = None,
        short_circuit_current: Annotated[
            float | None,
            Field(description='Optional Sandia module short-circuit current at reference conditions.'),
        ] = None,
        open_circuit_voltage: Annotated[
            float | None,
            Field(description='Optional Sandia module open-circuit voltage at reference conditions.'),
        ] = None,
        currentat_maximum_power_point: Annotated[
            float | None,
            Field(description='Optional CurrentatMaximumPowerPoint value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field CurrentatMaximumPowerPoint.'),
        ] = None,
        voltageat_maximum_power_point: Annotated[
            float | None,
            Field(description='Optional VoltageatMaximumPowerPoint value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field VoltageatMaximumPowerPoint.'),
        ] = None,
        sandia_database_parametera_isc: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameteraIsc value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameteraIsc.'),
        ] = None,
        sandia_database_parametera_imp: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameteraImp value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameteraImp.'),
        ] = None,
        sandia_database_parameterc0: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterc0 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterc0.'),
        ] = None,
        sandia_database_parameterc1: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterc1 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterc1.'),
        ] = None,
        sandia_database_parameter_b_voc0: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterBVoc0 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterBVoc0.'),
        ] = None,
        sandia_database_parameterm_b_voc: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParametermBVoc value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParametermBVoc.'),
        ] = None,
        sandia_database_parameter_b_vmp0: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterBVmp0 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterBVmp0.'),
        ] = None,
        sandia_database_parameterm_b_vmp: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParametermBVmp value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParametermBVmp.'),
        ] = None,
        diode_factor: Annotated[
            float | None,
            Field(description='Optional DiodeFactor value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field DiodeFactor.'),
        ] = None,
        sandia_database_parameterc2: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterc2 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterc2.'),
        ] = None,
        sandia_database_parameterc3: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterc3 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterc3.'),
        ] = None,
        sandia_database_parametera0: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParametera0 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParametera0.'),
        ] = None,
        sandia_database_parametera1: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParametera1 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParametera1.'),
        ] = None,
        sandia_database_parametera2: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParametera2 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParametera2.'),
        ] = None,
        sandia_database_parametera3: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParametera3 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParametera3.'),
        ] = None,
        sandia_database_parametera4: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParametera4 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParametera4.'),
        ] = None,
        sandia_database_parameterb0: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterb0 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterb0.'),
        ] = None,
        sandia_database_parameterb1: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterb1 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterb1.'),
        ] = None,
        sandia_database_parameterb2: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterb2 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterb2.'),
        ] = None,
        sandia_database_parameterb3: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterb3 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterb3.'),
        ] = None,
        sandia_database_parameterb4: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterb4 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterb4.'),
        ] = None,
        sandia_database_parameterb5: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterb5 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterb5.'),
        ] = None,
        sandia_database_parameter_delta_tc: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterDeltaTc value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterDeltaTc.'),
        ] = None,
        sandia_database_parameterfd: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterfd value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterfd.'),
        ] = None,
        sandia_database_parametera: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParametera value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParametera.'),
        ] = None,
        sandia_database_parameterb: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterb value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterb.'),
        ] = None,
        sandia_database_parameterc4: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterc4 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterc4.'),
        ] = None,
        sandia_database_parameterc5: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterc5 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterc5.'),
        ] = None,
        sandia_database_parameter_ix0: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterIx0 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterIx0.'),
        ] = None,
        sandia_database_parameter_ixx0: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterIxx0 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterIxx0.'),
        ] = None,
        sandia_database_parameterc6: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterc6 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterc6.'),
        ] = None,
        sandia_database_parameterc7: Annotated[
            float | None,
            Field(description='Optional SandiaDatabaseParameterc7 value; maps to Ironbug IB_PhotovoltaicPerformanceSandia field SandiaDatabaseParameterc7.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio name for the Sandia photovoltaic performance object.'),
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
        """Create IB_PhotovoltaicPerformanceSandia as a reviewed Ironbug Electrical authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if active_area is not None:
            source_fields['ActiveArea'] = active_area
        if numberof_cellsin_series is not None:
            source_fields['NumberofCellsinSeries'] = numberof_cellsin_series
        if numberof_cellsin_parallel is not None:
            source_fields['NumberofCellsinParallel'] = numberof_cellsin_parallel
        if short_circuit_current is not None:
            source_fields['ShortCircuitCurrent'] = short_circuit_current
        if open_circuit_voltage is not None:
            source_fields['OpenCircuitVoltage'] = open_circuit_voltage
        if currentat_maximum_power_point is not None:
            source_fields['CurrentatMaximumPowerPoint'] = currentat_maximum_power_point
        if voltageat_maximum_power_point is not None:
            source_fields['VoltageatMaximumPowerPoint'] = voltageat_maximum_power_point
        if sandia_database_parametera_isc is not None:
            source_fields['SandiaDatabaseParameteraIsc'] = sandia_database_parametera_isc
        if sandia_database_parametera_imp is not None:
            source_fields['SandiaDatabaseParameteraImp'] = sandia_database_parametera_imp
        if sandia_database_parameterc0 is not None:
            source_fields['SandiaDatabaseParameterc0'] = sandia_database_parameterc0
        if sandia_database_parameterc1 is not None:
            source_fields['SandiaDatabaseParameterc1'] = sandia_database_parameterc1
        if sandia_database_parameter_b_voc0 is not None:
            source_fields['SandiaDatabaseParameterBVoc0'] = sandia_database_parameter_b_voc0
        if sandia_database_parameterm_b_voc is not None:
            source_fields['SandiaDatabaseParametermBVoc'] = sandia_database_parameterm_b_voc
        if sandia_database_parameter_b_vmp0 is not None:
            source_fields['SandiaDatabaseParameterBVmp0'] = sandia_database_parameter_b_vmp0
        if sandia_database_parameterm_b_vmp is not None:
            source_fields['SandiaDatabaseParametermBVmp'] = sandia_database_parameterm_b_vmp
        if diode_factor is not None:
            source_fields['DiodeFactor'] = diode_factor
        if sandia_database_parameterc2 is not None:
            source_fields['SandiaDatabaseParameterc2'] = sandia_database_parameterc2
        if sandia_database_parameterc3 is not None:
            source_fields['SandiaDatabaseParameterc3'] = sandia_database_parameterc3
        if sandia_database_parametera0 is not None:
            source_fields['SandiaDatabaseParametera0'] = sandia_database_parametera0
        if sandia_database_parametera1 is not None:
            source_fields['SandiaDatabaseParametera1'] = sandia_database_parametera1
        if sandia_database_parametera2 is not None:
            source_fields['SandiaDatabaseParametera2'] = sandia_database_parametera2
        if sandia_database_parametera3 is not None:
            source_fields['SandiaDatabaseParametera3'] = sandia_database_parametera3
        if sandia_database_parametera4 is not None:
            source_fields['SandiaDatabaseParametera4'] = sandia_database_parametera4
        if sandia_database_parameterb0 is not None:
            source_fields['SandiaDatabaseParameterb0'] = sandia_database_parameterb0
        if sandia_database_parameterb1 is not None:
            source_fields['SandiaDatabaseParameterb1'] = sandia_database_parameterb1
        if sandia_database_parameterb2 is not None:
            source_fields['SandiaDatabaseParameterb2'] = sandia_database_parameterb2
        if sandia_database_parameterb3 is not None:
            source_fields['SandiaDatabaseParameterb3'] = sandia_database_parameterb3
        if sandia_database_parameterb4 is not None:
            source_fields['SandiaDatabaseParameterb4'] = sandia_database_parameterb4
        if sandia_database_parameterb5 is not None:
            source_fields['SandiaDatabaseParameterb5'] = sandia_database_parameterb5
        if sandia_database_parameter_delta_tc is not None:
            source_fields['SandiaDatabaseParameterDeltaTc'] = sandia_database_parameter_delta_tc
        if sandia_database_parameterfd is not None:
            source_fields['SandiaDatabaseParameterfd'] = sandia_database_parameterfd
        if sandia_database_parametera is not None:
            source_fields['SandiaDatabaseParametera'] = sandia_database_parametera
        if sandia_database_parameterb is not None:
            source_fields['SandiaDatabaseParameterb'] = sandia_database_parameterb
        if sandia_database_parameterc4 is not None:
            source_fields['SandiaDatabaseParameterc4'] = sandia_database_parameterc4
        if sandia_database_parameterc5 is not None:
            source_fields['SandiaDatabaseParameterc5'] = sandia_database_parameterc5
        if sandia_database_parameter_ix0 is not None:
            source_fields['SandiaDatabaseParameterIx0'] = sandia_database_parameter_ix0
        if sandia_database_parameter_ixx0 is not None:
            source_fields['SandiaDatabaseParameterIxx0'] = sandia_database_parameter_ixx0
        if sandia_database_parameterc6 is not None:
            source_fields['SandiaDatabaseParameterc6'] = sandia_database_parameterc6
        if sandia_database_parameterc7 is not None:
            source_fields['SandiaDatabaseParameterc7'] = sandia_database_parameterc7
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_PhotovoltaicPerformanceSandia',
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
