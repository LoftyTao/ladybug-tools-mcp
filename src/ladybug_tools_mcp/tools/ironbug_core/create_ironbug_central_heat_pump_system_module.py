'MCP tool for detailed_hvac_central_heat_pump_system_module.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_central_heat_pump_system_module tool.'

    @mcp.tool(
        name='central_heat_pump_system_module',
        description=(
            'Create IB_CentralHeatPumpSystemModule, the Ironbug module entry used inside a CentralHeatPumpSystem chiller-heater bank. Use it to reference a chiller-heater object and set how many identical modules are controlled by the central system schedule; it belongs to DetailedHVAC central plant assembly, not Pump:* hardware and not an Energy HVAC template. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'central-system',
            'heat-pump',
            'chiller-heater',
            'module',
            'control',
            'component',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_central_heat_pump_system_module(
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
            Field(description="Stable identifier for the new IB_CentralHeatPumpSystemModule object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        number_of_chiller_heater_modules: Annotated[
            int | None,
            Field(
                description="Optional Ironbug property NumberOfChillerHeaterModules as an integer count of identical chiller-heater modules in this entry."
            ),
        ] = None,
        chiller_heater_modules_control_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for ChillerHeaterModulesControlSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_CentralHeatPumpSystemModule field ChillerHeaterModulesControlSchedule (IB_Schedule).'),
        ] = None,
        numberof_chiller_heater_modules: Annotated[
            int | None,
            Field(description='Optional EnergyPlus field value for the number of chiller-heater modules represented by this module entry.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CentralHeatPumpSystemModule field Name.'),
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
        chiller_heater_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Ironbug target for component Parameter 'Chiller-heater' "
                    "on IB_CentralHeatPumpSystemModule, typically a ChillerHeaterPerformance:Electric:EIR object."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_CentralHeatPumpSystemModule as a reviewed Ironbug Loop Objs authoring object."""

        child_targets = [
            chiller_heater_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if chiller_heater_modules_control_schedule_target is not None:
            source_field_targets['ChillerHeaterModulesControlSchedule'] = chiller_heater_modules_control_schedule_target
        if numberof_chiller_heater_modules is not None:
            source_fields['NumberofChillerHeaterModules'] = numberof_chiller_heater_modules
        if number_of_chiller_heater_modules is not None:
            source_properties['NumberOfChillerHeaterModules'] = number_of_chiller_heater_modules
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CentralHeatPumpSystemModule',
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
