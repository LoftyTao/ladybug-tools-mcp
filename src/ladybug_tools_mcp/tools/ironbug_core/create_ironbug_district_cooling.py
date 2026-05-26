'MCP tool for detailed_hvac_district_cooling.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_district_cooling tool.'

    @mcp.tool(
        name='district_cooling',
        description=(
            'Create IB_DistrictCooling, an EnergyPlus/OpenStudio DistrictCooling purchased chilled-water plant component. Use it as a plant-loop supply component when a centralized chilled-water source or purchased cooling replaces an explicit chiller. This authors Ironbug DetailedHVAC input only; it does not create a chiller, cooling tower, district-scale simulation, or Energy run. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'plant-loop',
            'plant-component',
            'district-energy',
            'purchased-energy',
            'chilled-water',
            'cooling',
            'schedule',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_district_cooling(
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
            Field(description="Stable DetailedHVAC object identifier for this purchased chilled-water component."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional display label shown in Ironbug/Garden summaries."),
        ] = None,
        name: Annotated[
            str | None,
            Field(
                description="Optional EnergyPlus/OpenStudio DistrictCooling object name; defaults to the identifier when omitted."
            ),
        ] = None,
        nominal_capacity: Annotated[
            float | str | None,
            Field(
                description="Nominal purchased cooling demand in W; autosize-compatible inputs accepted by Ironbug/OpenStudio are also valid."
            ),
        ] = None,
        capacity_fraction_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for non-negative capacity fraction over time; omit for a constant 1.0 fraction.'),
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
        """Create IB_DistrictCooling as reviewed purchased chilled-water plant data."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if nominal_capacity is not None:
            source_fields['NominalCapacity'] = nominal_capacity
        source_properties: dict[str, Any] = {}
        if capacity_fraction_schedule_target is not None:
            source_field_targets['CapacityFractionSchedule'] = capacity_fraction_schedule_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_DistrictCooling',
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
