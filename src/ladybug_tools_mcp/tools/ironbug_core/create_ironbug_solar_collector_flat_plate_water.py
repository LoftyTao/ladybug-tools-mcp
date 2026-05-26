'MCP tool for detailed_hvac_solar_collector_flat_plate_water.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from ladybug_tools_mcp.tools.ironbug_core.target_identifiers import target_identifier



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_solar_collector_flat_plate_water tool.'

    @mcp.tool(
        name='solar_collector_flat_plate_water',
        description=(
            'Create IB_SolarCollectorFlatPlateWater, the Ironbug and EnergyPlus SolarCollector:FlatPlate:Water plant-loop component. It combines a flat-plate thermal performance target with a shading or building surface target whose tilt, azimuth, and area define the collector. Use it for water-side solar thermal collectors, not PVT collectors, PV generators, water heaters, or Energy result reading. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'plant-component', 'plant-loop', 'solar-collector', 'solar-thermal', 'shading', 'surface', 'author', 'component'},
        timeout=20,
    )
    def create_ironbug_solar_collector_flat_plate_water(
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
            Field(description="Stable identifier for the new IB_SolarCollectorFlatPlateWater object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        maximum_flow_rate: Annotated[
            float | None,
            Field(description='Optional maximum collector water flow rate in m3/s.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_SolarCollectorFlatPlateWater field Name.'),
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
        solar_collector_performance_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_SolarCollectorPerformanceFlatPlate target with SRCC-style "
                    "thermal and optical performance coefficients."
                )
            ),
        ] = None,
        shade_surface_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ShadingSurface, Honeybee Shade target, or OpenStudio shading "
                    "surface identifier used as the collector surface."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug flat-plate water solar collector."""

        child_targets = [
            solar_collector_performance_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        source_data_members: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if maximum_flow_rate is not None:
            source_fields['MaximumFlowRate'] = maximum_flow_rate
        if shade_surface_target is not None:
            source_data_members['SurfaceID'] = target_identifier(
                shade_surface_target,
                parameter_name="shade_surface_target",
            )
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SolarCollectorFlatPlateWater',
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
