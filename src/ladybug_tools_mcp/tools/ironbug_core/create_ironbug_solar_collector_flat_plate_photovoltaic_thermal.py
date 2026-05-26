'MCP tool for detailed_hvac_solar_collector_flat_plate_photovoltaic_thermal.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_solar_collector_flat_plate_photovoltaic_thermal tool.'

    @mcp.tool(
        name='solar_collector_flat_plate_photovoltaic_thermal',
        description=(
            'Create IB_SolarCollectorFlatPlatePhotovoltaicThermal, the Ironbug and EnergyPlus SolarCollector:FlatPlate:PhotovoltaicThermal object for hybrid PVT collectors that produce electricity and useful heat. It uses a Generator:Photovoltaic child and an optional photovoltaic-thermal performance child, then exposes the collector as air-loop or plant-loop equipment. This is not a PV generator by itself, a flat-plate water-only collector, or a simulation result reader. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'plant-component', 'air-loop', 'plant-loop', 'solar-collector', 'solar-thermal', 'photovoltaic', 'photovoltaic-thermal', 'pv', 'author', 'component'},
        timeout=20,
    )
    def create_ironbug_solar_collector_flat_plate_photovoltaic_thermal(
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
            Field(description="Stable identifier for the new IB_SolarCollectorFlatPlatePhotovoltaicThermal object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        design_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional collector design flow rate in m3/s, or autosize/autocalculate text accepted by the source field.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_SolarCollectorFlatPlatePhotovoltaicThermal field Name.'),
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
        generator_pv_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_GeneratorPhotovoltaic target that supplies the PV generator "
                    "and associated surface for this PVT collector."
                )
            ),
        ] = None,
        solar_collector_performance_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional photovoltaic-thermal performance target, usually Simple or BIPVT, "
                    "for the collector thermal model."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create an Ironbug hybrid photovoltaic-thermal solar collector."""

        child_targets = [
            generator_pv_target,
            solar_collector_performance_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if design_flow_rate is not None:
            source_fields['DesignFlowRate'] = design_flow_rate
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SolarCollectorFlatPlatePhotovoltaicThermal',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            child_targets=child_targets if any(item is not None for item in child_targets) else None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
