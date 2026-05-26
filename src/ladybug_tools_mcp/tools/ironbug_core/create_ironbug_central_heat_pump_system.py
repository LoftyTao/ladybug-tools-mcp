'MCP tool for detailed_hvac_central_heat_pump_system.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_central_heat_pump_system tool.'

    @mcp.tool(
        name='central_heat_pump_system',
        description=(
            'Create IB_CentralHeatPumpSystem, the Ironbug and EnergyPlus CentralHeatPumpSystem chiller-heater bank for central plants that can serve chilled-water, hot-water, and condenser/source-water loops. Use it to group ChillerHeaterPerformance:Electric:EIR or CentralHeatPumpSystemModule objects and control cooling-only, heating-only, or simultaneous heating/cooling operation; this is DetailedHVAC plant equipment, not Pump:* hardware and not an Energy HVAC template. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'central-system',
            'heat-pump',
            'chiller-heater',
            'plant-loop',
            'plant-component',
            'chilled-water',
            'hot-water',
            'condenser-water',
            'heating',
            'cooling',
            'control',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_central_heat_pump_system(
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
            Field(description="Stable identifier for the new IB_CentralHeatPumpSystem object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        chiller_heaters_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional Ironbug target list for CentralHeatPumpSystem Modules; pass IB_CentralHeatPumpSystemModule or compatible ChillerHeaterPerformance:Electric:EIR targets or same-model identifiers."
            ),
        ] = None,
        control_method: Annotated[
            str | None,
            Field(description='Optional EnergyPlus CentralHeatPumpSystem control method such as SmartMixing; maps to ControlMethod.'),
        ] = None,
        ancillary_power: Annotated[
            float | None,
            Field(description='Optional central heat pump system ancillary electric power in W; maps to AncillaryPower.'),
        ] = None,
        ancillary_operation_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for AncillaryOperationSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_CentralHeatPumpSystem field AncillaryOperationSchedule (IB_Schedule).'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CentralHeatPumpSystem field Name.'),
        ] = None,
        modules_identifiers: Annotated[
            list[str] | None,
            Field(description='Optional inline IB_CentralHeatPumpSystemModule identifiers for IB_CentralHeatPumpSystem.Modules.'),
        ] = None,
        modules_name_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline Name value for IB_CentralHeatPumpSystemModule; maps to Ironbug IB_CentralHeatPumpSystem.Modules child field Name.'),
        ] = None,
        modules_chiller_heater_modules_control_schedule_targets: Annotated[
            list[dict[str, Any] | str | None] | None,
            Field(description='Optional inline Ironbug schedule targets for each module ChillerHeaterModulesControlSchedule; pass target dicts from compatible create_ironbug_* tools or same-model identifiers.'),
        ] = None,
        modules_numberof_chiller_heater_modules_values: Annotated[
            list[int | None] | None,
            Field(description='Optional inline module counts for IB_CentralHeatPumpSystemModule children; maps to NumberofChillerHeaterModules.'),
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
        """Create IB_CentralHeatPumpSystem as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        inline_source_property_children: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if control_method is not None:
            source_fields['ControlMethod'] = control_method
        if ancillary_power is not None:
            source_fields['AncillaryPower'] = ancillary_power
        if ancillary_operation_schedule_target is not None:
            source_field_targets['AncillaryOperationSchedule'] = ancillary_operation_schedule_target
        if chiller_heaters_targets is not None:
            source_property_targets['Modules'] = chiller_heaters_targets
        inline_modules_fields: dict[str, Any] = {}
        inline_modules_field_targets: dict[str, Any] = {}
        if modules_name_values is not None:
            inline_modules_fields['Name'] = modules_name_values
        if modules_chiller_heater_modules_control_schedule_targets is not None:
            inline_modules_field_targets['ChillerHeaterModulesControlSchedule'] = modules_chiller_heater_modules_control_schedule_targets
        if modules_numberof_chiller_heater_modules_values is not None:
            inline_modules_fields['NumberofChillerHeaterModules'] = modules_numberof_chiller_heater_modules_values
        if modules_identifiers is not None or inline_modules_fields or inline_modules_field_targets:
            if chiller_heaters_targets is not None:
                raise ValueError("Provide either chiller_heaters_targets or inline modules_* parameters, not both.")
            inline_source_property_children['Modules'] = {
                'source_class': 'IB_CentralHeatPumpSystemModule',
                'is_list': True,
                'identifiers': modules_identifiers,
                'source_fields': inline_modules_fields,
                'source_field_targets': inline_modules_field_targets,
            }
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CentralHeatPumpSystem',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            source_property_targets=source_property_targets or None,
            inline_source_property_children=inline_source_property_children or None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
