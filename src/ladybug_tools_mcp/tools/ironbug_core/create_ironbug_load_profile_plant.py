'MCP tool for detailed_hvac_load_profile_plant.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_load_profile_plant tool.'

    @mcp.tool(
        name='load_profile_plant',
        description=(
            'Create IB_LoadProfilePlant, an EnergyPlus LoadProfile:Plant demand-side plant component for a scheduled heating or cooling load when the building load is already known. Use it with a load schedule, peak flow rate, optional flow-fraction schedule, plant fluid type, and steam subcooling fields; this is not a boiler, chiller, zone load, or Energy run. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'plant-loop',
            'plant-component',
            'load',
            'load-profile',
            'schedule',
            'heating',
            'cooling',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_load_profile_plant(
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
            Field(description="Stable identifier for the new IB_LoadProfilePlant object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        load_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier whose values define the plant heating/cooling load in W; maps to LoadSchedule.'),
        ] = None,
        peak_flow_rate: Annotated[
            float | None,
            Field(description='Optional peak demanded plant loop flow rate in m3/s for the scheduled load profile; maps to PeakFlowRate.'),
        ] = None,
        flow_rate_fraction_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier that scales peak flow over time; maps to FlowRateFractionSchedule.'),
        ] = None,
        plant_loop_fluid_type: Annotated[
            str | None,
            Field(description='Optional plant loop fluid type for the load profile, such as Water or Steam; maps to PlantLoopFluidType.'),
        ] = None,
        degreeof_sub_cooling: Annotated[
            float | None,
            Field(description='Optional steam loop subcooling value for the scheduled plant load profile; maps to DegreeofSubCooling.'),
        ] = None,
        degreeof_loop_sub_cooling: Annotated[
            float | None,
            Field(description='Optional loop subcooling value for the scheduled plant load profile; maps to DegreeofLoopSubCooling.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus object name for this LoadProfile:Plant demand component; maps to Name.'),
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
        """Create IB_LoadProfilePlant as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if load_schedule_target is not None:
            source_field_targets['LoadSchedule'] = load_schedule_target
        if peak_flow_rate is not None:
            source_fields['PeakFlowRate'] = peak_flow_rate
        if flow_rate_fraction_schedule_target is not None:
            source_field_targets['FlowRateFractionSchedule'] = flow_rate_fraction_schedule_target
        if plant_loop_fluid_type is not None:
            source_fields['PlantLoopFluidType'] = plant_loop_fluid_type
        if degreeof_sub_cooling is not None:
            source_fields['DegreeofSubCooling'] = degreeof_sub_cooling
        if degreeof_loop_sub_cooling is not None:
            source_fields['DegreeofLoopSubCooling'] = degreeof_loop_sub_cooling
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_LoadProfilePlant',
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
