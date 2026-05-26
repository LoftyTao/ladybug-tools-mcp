'MCP tool for detailed_hvac_generator_pv_watts.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from ladybug_tools_mcp.tools.ironbug_core.target_identifiers import target_identifier



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_generator_pv_watts tool.'

    @mcp.tool(
        name='generator_pv_watts',
        description=(
            'Create IB_GeneratorPVWatts, an OpenStudio/EnergyPlus Generator:PVWatts object placed on an OpenStudio shading surface. Use it for first-pass grid-connected PV production with DC capacity, module/array type, losses, tilt, azimuth, and ground coverage ratio; pair it with an ElectricLoadCenter:Inverter:PVWatts rather than a generic PV inverter. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'electric', 'electric-equipment', 'generator', 'photovoltaic', 'pv', 'pvwatts', 'shade', 'author'},
        timeout=20,
    )
    def create_ironbug_generator_pv_watts(
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
            Field(description="Stable identifier for the new IB_GeneratorPVWatts object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        dc_system_capacity: Annotated[
            float | None,
            Field(description='Optional PVWatts DC system capacity in W.'),
        ] = None,
        module_type: Annotated[
            str | None,
            Field(description='Optional PVWatts module type such as standard, premium, or thin-film.'),
        ] = None,
        array_type: Annotated[
            str | None,
            Field(description='Optional PVWatts array type, such as fixed open rack, roof mount, one-axis, or two-axis tracking.'),
        ] = None,
        system_losses: Annotated[
            float | None,
            Field(description='Optional PVWatts total system losses as a fraction or percent value accepted by OpenStudio.'),
        ] = None,
        tilt_angle: Annotated[
            float | None,
            Field(description='Optional PV array tilt angle in degrees.'),
        ] = None,
        azimuth_angle: Annotated[
            float | None,
            Field(description='Optional PV array azimuth angle in degrees.'),
        ] = None,
        ground_coverage_ratio: Annotated[
            float | None,
            Field(description='Optional PVWatts ground coverage ratio for array row spacing.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio name for the PVWatts generator object.'),
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
        shade_surface_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Honeybee Shade target or OpenStudio shading surface identifier where the PVWatts generator is mounted."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_GeneratorPVWatts as a reviewed Ironbug Electrical authoring object."""

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
        if dc_system_capacity is not None:
            source_fields['DCSystemCapacity'] = dc_system_capacity
        if module_type is not None:
            source_fields['ModuleType'] = module_type
        if array_type is not None:
            source_fields['ArrayType'] = array_type
        if system_losses is not None:
            source_fields['SystemLosses'] = system_losses
        if tilt_angle is not None:
            source_fields['TiltAngle'] = tilt_angle
        if azimuth_angle is not None:
            source_fields['AzimuthAngle'] = azimuth_angle
        if ground_coverage_ratio is not None:
            source_fields['GroundCoverageRatio'] = ground_coverage_ratio
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_GeneratorPVWatts',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            source_data_members=source_data_members or None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
