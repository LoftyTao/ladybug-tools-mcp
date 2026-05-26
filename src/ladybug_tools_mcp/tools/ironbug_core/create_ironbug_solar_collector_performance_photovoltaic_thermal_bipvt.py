'MCP tool for detailed_hvac_solar_collector_performance_photovoltaic_thermal_bipvt.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_solar_collector_performance_photovoltaic_thermal_bipvt tool.'

    @mcp.tool(
        name='solar_collector_performance_photovoltaic_thermal_bipvt',
        description=(
            'Create IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT, the Ironbug and EnergyPlus SolarCollectorPerformance:PhotovoltaicThermal:BIPVT object for building-integrated PVT thermal performance. Use it as a performance child for a photovoltaic-thermal solar collector, not as the collector surface, PV generator, load center, or Energy result reader. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'performance', 'solar-collector', 'photovoltaic-thermal', 'photovoltaic', 'pv', 'bipvt', 'schedule', 'author'},
        timeout=20,
    )
    def create_ironbug_solar_collector_performance_photovoltaic_thermal_bipvt(
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
            Field(description="Stable identifier for the new IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target controlling BIPVT collector availability; pass a schedule target dict or same-model identifier.'),
        ] = None,
        effective_plenum_gap_thickness_behind_pv_modules: Annotated[
            float | None,
            Field(description='Optional EffectivePlenumGapThicknessBehindPVModules value; maps to Ironbug IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT field EffectivePlenumGapThicknessBehindPVModules.'),
        ] = None,
        pv_cell_normal_transmittance_absorptance_product: Annotated[
            float | None,
            Field(description='Optional PVCellNormalTransmittanceAbsorptanceProduct value; maps to Ironbug IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT field PVCellNormalTransmittanceAbsorptanceProduct.'),
        ] = None,
        backing_material_normal_transmittance_absorptance_product: Annotated[
            float | None,
            Field(description='Optional BackingMaterialNormalTransmittanceAbsorptanceProduct value; maps to Ironbug IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT field BackingMaterialNormalTransmittanceAbsorptanceProduct.'),
        ] = None,
        cladding_normal_transmittance_absorptance_product: Annotated[
            float | None,
            Field(description='Optional CladdingNormalTransmittanceAbsorptanceProduct value; maps to Ironbug IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT field CladdingNormalTransmittanceAbsorptanceProduct.'),
        ] = None,
        fractionof_collector_gross_area_coveredby_pv_module: Annotated[
            float | None,
            Field(description='Optional FractionofCollectorGrossAreaCoveredbyPVModule value; maps to Ironbug IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT field FractionofCollectorGrossAreaCoveredbyPVModule.'),
        ] = None,
        fractionof_pv_cell_areato_pv_module_area: Annotated[
            float | None,
            Field(description='Optional FractionofPVCellAreatoPVModuleArea value; maps to Ironbug IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT field FractionofPVCellAreatoPVModuleArea.'),
        ] = None,
        pv_module_top_thermal_resistance: Annotated[
            float | None,
            Field(description='Optional PVModuleTopThermalResistance value; maps to Ironbug IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT field PVModuleTopThermalResistance.'),
        ] = None,
        pv_module_bottom_thermal_resistance: Annotated[
            float | None,
            Field(description='Optional PVModuleBottomThermalResistance value; maps to Ironbug IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT field PVModuleBottomThermalResistance.'),
        ] = None,
        pv_module_front_longwave_emissivity: Annotated[
            float | None,
            Field(description='Optional PVModuleFrontLongwaveEmissivity value; maps to Ironbug IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT field PVModuleFrontLongwaveEmissivity.'),
        ] = None,
        pv_module_back_longwave_emissivity: Annotated[
            float | None,
            Field(description='Optional PVModuleBackLongwaveEmissivity value; maps to Ironbug IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT field PVModuleBackLongwaveEmissivity.'),
        ] = None,
        glass_thickness: Annotated[
            float | None,
            Field(description='Optional GlassThickness value; maps to Ironbug IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT field GlassThickness.'),
        ] = None,
        glass_refraction_index: Annotated[
            float | None,
            Field(description='Optional GlassRefractionIndex value; maps to Ironbug IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT field GlassRefractionIndex.'),
        ] = None,
        glass_extinction_coefficient: Annotated[
            float | None,
            Field(description='Optional GlassExtinctionCoefficient value; maps to Ironbug IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT field GlassExtinctionCoefficient.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT field Name.'),
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
        """Create BIPVT photovoltaic-thermal performance data."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if effective_plenum_gap_thickness_behind_pv_modules is not None:
            source_fields['EffectivePlenumGapThicknessBehindPVModules'] = effective_plenum_gap_thickness_behind_pv_modules
        if pv_cell_normal_transmittance_absorptance_product is not None:
            source_fields['PVCellNormalTransmittanceAbsorptanceProduct'] = pv_cell_normal_transmittance_absorptance_product
        if backing_material_normal_transmittance_absorptance_product is not None:
            source_fields['BackingMaterialNormalTransmittanceAbsorptanceProduct'] = backing_material_normal_transmittance_absorptance_product
        if cladding_normal_transmittance_absorptance_product is not None:
            source_fields['CladdingNormalTransmittanceAbsorptanceProduct'] = cladding_normal_transmittance_absorptance_product
        if fractionof_collector_gross_area_coveredby_pv_module is not None:
            source_fields['FractionofCollectorGrossAreaCoveredbyPVModule'] = fractionof_collector_gross_area_coveredby_pv_module
        if fractionof_pv_cell_areato_pv_module_area is not None:
            source_fields['FractionofPVCellAreatoPVModuleArea'] = fractionof_pv_cell_areato_pv_module_area
        if pv_module_top_thermal_resistance is not None:
            source_fields['PVModuleTopThermalResistance'] = pv_module_top_thermal_resistance
        if pv_module_bottom_thermal_resistance is not None:
            source_fields['PVModuleBottomThermalResistance'] = pv_module_bottom_thermal_resistance
        if pv_module_front_longwave_emissivity is not None:
            source_fields['PVModuleFrontLongwaveEmissivity'] = pv_module_front_longwave_emissivity
        if pv_module_back_longwave_emissivity is not None:
            source_fields['PVModuleBackLongwaveEmissivity'] = pv_module_back_longwave_emissivity
        if glass_thickness is not None:
            source_fields['GlassThickness'] = glass_thickness
        if glass_refraction_index is not None:
            source_fields['GlassRefractionIndex'] = glass_refraction_index
        if glass_extinction_coefficient is not None:
            source_fields['GlassExtinctionCoefficient'] = glass_extinction_coefficient
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SolarCollectorPerformancePhotovoltaicThermalBIPVT',
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
