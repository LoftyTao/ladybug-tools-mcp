'MCP tool for detailed_hvac_solar_collector_performance_photovoltaic_thermal_simple.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_solar_collector_performance_photovoltaic_thermal_simple tool.'

    @mcp.tool(
        name='solar_collector_performance_photovoltaic_thermal_simple',
        description=(
            'Create IB_SolarCollectorPerformancePhotovoltaicThermalSimple, the Ironbug and EnergyPlus SolarCollectorPerformance:PhotovoltaicThermal:Simple object for fixed or scheduled PVT thermal conversion efficiency. Use it as a performance child for a photovoltaic-thermal solar collector, not as the collector surface, PV generator, load center, or Energy result reader. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'performance', 'solar-collector', 'photovoltaic-thermal', 'photovoltaic', 'pv', 'schedule', 'author'},
        timeout=20,
    )
    def create_ironbug_solar_collector_performance_photovoltaic_thermal_simple(
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
            Field(description="Stable identifier for the new IB_SolarCollectorPerformancePhotovoltaicThermalSimple object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        fraction_of_surface_area_with_active_thermal_collector: Annotated[
            float | None,
            Field(description='Optional fraction of collector surface area with active thermal collector, from 0 to 1.'),
        ] = None,
        thermal_conversion_efficiency: Annotated[
            str | float | int | bool | None,
            Field(description='Optional fixed thermal conversion efficiency value, or source-supported text for the efficiency input mode.'),
        ] = None,
        thermal_conversion_efficiency_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for scheduled thermal conversion efficiency.'),
        ] = None,
        front_surface_emittance: Annotated[
            float | None,
            Field(description='Optional front surface longwave emittance, greater than 0 and less than 1.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_SolarCollectorPerformancePhotovoltaicThermalSimple field Name.'),
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
        """Create simple photovoltaic-thermal performance data."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if fraction_of_surface_area_with_active_thermal_collector is not None:
            source_fields['FractionOfSurfaceAreaWithActiveThermalCollector'] = fraction_of_surface_area_with_active_thermal_collector
        if thermal_conversion_efficiency is not None:
            source_fields['ThermalConversionEfficiency'] = thermal_conversion_efficiency
        if thermal_conversion_efficiency_schedule_target is not None:
            source_field_targets['ThermalConversionEfficiencySchedule'] = thermal_conversion_efficiency_schedule_target
        if front_surface_emittance is not None:
            source_fields['FrontSurfaceEmittance'] = front_surface_emittance
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SolarCollectorPerformancePhotovoltaicThermalSimple',
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
