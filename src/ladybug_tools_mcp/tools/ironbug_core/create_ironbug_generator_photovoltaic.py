'MCP tool for detailed_hvac_generator_photovoltaic.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from ladybug_tools_mcp.tools.ironbug_core.target_identifiers import target_identifier



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_generator_photovoltaic tool.'

    @mcp.tool(
        name='generator_photovoltaic',
        description=(
            'Create IB_GeneratorPhotovoltaic, an OpenStudio/EnergyPlus Generator:Photovoltaic object placed on an OpenStudio shading surface. Use it with a PhotovoltaicPerformance child target for simple, Sandia, or equivalent one-diode PV performance; this is not PVWatts, an inverter, a load-center distribution, or an Energy simulation runner. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'electric', 'electric-equipment', 'generator', 'photovoltaic', 'pv', 'shade', 'performance', 'author'},
        timeout=20,
    )
    def create_ironbug_generator_photovoltaic(
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
            Field(description="Stable identifier for the new IB_GeneratorPhotovoltaic object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        heat_transfer_integration_mode: Annotated[
            str | None,
            Field(description='Optional Generator:Photovoltaic heat-transfer integration mode for coupling PV performance with the host surface.'),
        ] = None,
        number_of_modules_in_parallel: Annotated[
            float | None,
            Field(description='Optional number of photovoltaic modules in parallel for the detailed PV generator.'),
        ] = None,
        number_of_modules_in_series: Annotated[
            float | None,
            Field(description='Optional number of photovoltaic modules in series for the detailed PV generator.'),
        ] = None,
        rated_electric_power_output: Annotated[
            float | None,
            Field(description='Optional rated electric power output in W for the detailed PV generator.'),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target controlling when the photovoltaic generator is available.'),
        ] = None,
        performance_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_PhotovoltaicPerformance target for the Generator:Photovoltaic performance child slot."
                )
            ),
        ] = None,
        shade_surface_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Honeybee Shade target or OpenStudio shading surface identifier where the PV generator is mounted."
                )
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio name for the photovoltaic generator object.'),
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
        """Create IB_GeneratorPhotovoltaic as a reviewed Ironbug Electrical authoring object."""

        child_targets = [
            performance_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        source_data_members: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if shade_surface_target is not None:
            source_data_members['SurfaceID'] = target_identifier(
                shade_surface_target,
                parameter_name="shade_surface_target",
            )
        if heat_transfer_integration_mode is not None:
            source_fields['HeatTransferIntegrationMode'] = heat_transfer_integration_mode
        if number_of_modules_in_parallel is not None:
            source_fields['NumberOfModulesInParallel'] = number_of_modules_in_parallel
        if number_of_modules_in_series is not None:
            source_fields['NumberOfModulesInSeries'] = number_of_modules_in_series
        if rated_electric_power_output is not None:
            source_fields['RatedElectricPowerOutput'] = rated_electric_power_output
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_GeneratorPhotovoltaic',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            source_data_members=source_data_members or None,
            child_targets=child_targets if any(item is not None for item in child_targets) else None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
