'MCP tool for detailed_hvac_coil_cooling_cooled_beam.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_cooling_cooled_beam tool.'

    @mcp.tool(
        name='coil_cooling_cooled_beam',
        description=(
            'Create IB_CoilCoolingCooledBeam, an Ironbug chilled-water cooled '
            'beam coil child that maps to OpenStudio CoilCoolingCooledBeam and '
            'feeds EnergyPlus cooled-beam terminal fields. Use the returned '
            'target as the CoolingCoil child for '
            'detailed_hvac_air_terminal_single_duct_constant_volume_cooled_beam. '
            'This is not zone equipment and not a Honeybee Energy HVAC '
            'template. Returns target, summary_view, persistence_receipt, and '
            'report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'cooling', 'chilled-water', 'beam', 'cooled-beam', 'plant-loop', 'air-terminal', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_cooling_cooled_beam(
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
            Field(description="Stable identifier for the new IB_CoilCoolingCooledBeam object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        coil_surface_areaper_coil_length: Annotated[
            float | None,
            Field(description='Optional CoilSurfaceAreaperCoilLength in m2/m for the cooled-beam coil surface area normalized by coil length.'),
        ] = None,
        model_parametera: Annotated[
            float | None,
            Field(description='Optional dimensionless cooled-beam model parameter a.'),
        ] = None,
        model_parametern1: Annotated[
            float | None,
            Field(description='Optional dimensionless cooled-beam model exponent n1.'),
        ] = None,
        model_parametern2: Annotated[
            float | None,
            Field(description='Optional dimensionless cooled-beam model exponent n2.'),
        ] = None,
        model_parametern3: Annotated[
            float | None,
            Field(description='Optional dimensionless cooled-beam model exponent n3.'),
        ] = None,
        model_parametera0: Annotated[
            float | None,
            Field(description='Optional ModelParametera0 in m2/m for free coil area per unit beam length.'),
        ] = None,
        model_parameter_k1: Annotated[
            float | None,
            Field(description='Optional dimensionless cooled-beam model parameter K1.'),
        ] = None,
        model_parametern: Annotated[
            float | None,
            Field(description='Optional dimensionless cooled-beam model exponent n.'),
        ] = None,
        leaving_pipe_inside_diameter: Annotated[
            float | None,
            Field(description='Optional LeavingPipeInsideDiameter in meters for the cooled-beam water pipe.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilCoolingCooledBeam field Name.'),
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
        """Create IB_CoilCoolingCooledBeam as a reviewed cooled-beam coil child."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if coil_surface_areaper_coil_length is not None:
            source_fields['CoilSurfaceAreaperCoilLength'] = coil_surface_areaper_coil_length
        if model_parametera is not None:
            source_fields['ModelParametera'] = model_parametera
        if model_parametern1 is not None:
            source_fields['ModelParametern1'] = model_parametern1
        if model_parametern2 is not None:
            source_fields['ModelParametern2'] = model_parametern2
        if model_parametern3 is not None:
            source_fields['ModelParametern3'] = model_parametern3
        if model_parametera0 is not None:
            source_fields['ModelParametera0'] = model_parametera0
        if model_parameter_k1 is not None:
            source_fields['ModelParameterK1'] = model_parameter_k1
        if model_parametern is not None:
            source_fields['ModelParametern'] = model_parametern
        if leaving_pipe_inside_diameter is not None:
            source_fields['LeavingPipeInsideDiameter'] = leaving_pipe_inside_diameter
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilCoolingCooledBeam',
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
