'MCP tool for detailed_hvac_photovoltaic_performance_simple.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_photovoltaic_performance_simple tool.'

    @mcp.tool(
        name='photovoltaic_performance_simple',
        description=(
            'Create IB_PhotovoltaicPerformanceSimple, an OpenStudio/EnergyPlus PhotovoltaicPerformance:Simple child for Generator:Photovoltaic. Use it for early-phase PV performance with active solar-cell area fraction and fixed or scheduled conversion efficiency. Use separate generator, PVWatts, inverter, or Energy simulation tools for those workflows. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'electric', 'electric-equipment', 'photovoltaic', 'pv', 'performance', 'schedule', 'author'},
        timeout=20,
    )
    def create_ironbug_photovoltaic_performance_simple(
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
            Field(description="Stable identifier for the new IB_PhotovoltaicPerformanceSimple object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        fraction_of_surface_area_with_active_solar_cells: Annotated[
            float | None,
            Field(description='Optional fraction of the host PV surface area covered by active solar cells.'),
        ] = None,
        fixed_efficiency: Annotated[
            str | float | int | bool | None,
            Field(description='Optional fixed solar-to-electric conversion efficiency for PhotovoltaicPerformance:Simple.'),
        ] = None,
        efficiency_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for time-varying PV conversion efficiency.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio name for the simple photovoltaic performance object.'),
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
        """Create IB_PhotovoltaicPerformanceSimple as a reviewed Ironbug Electrical authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if fraction_of_surface_area_with_active_solar_cells is not None:
            source_fields['FractionOfSurfaceAreaWithActiveSolarCells'] = fraction_of_surface_area_with_active_solar_cells
        if fixed_efficiency is not None:
            source_fields['FixedEfficiency'] = fixed_efficiency
        if efficiency_schedule_target is not None:
            source_field_targets['EfficiencySchedule'] = efficiency_schedule_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_PhotovoltaicPerformanceSimple',
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
