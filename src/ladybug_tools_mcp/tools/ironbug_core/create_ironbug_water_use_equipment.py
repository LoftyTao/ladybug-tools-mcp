'MCP tool for detailed_hvac_water_use_equipment.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from ladybug_tools_mcp.tools.ironbug_core.target_identifiers import target_identifier



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_water_use_equipment tool.'

    @mcp.tool(
        name='water_use_equipment',
        description=(
            'Create IB_WaterUseEquipment, the Ironbug and EnergyPlus WaterUse:Equipment fixture object for hot/cold water end uses and controlled mixing at the tap. It references a WaterUseEquipmentDefinition child, an optional flow-rate fraction schedule, and optional Honeybee Room/space placement; it is not a WaterUse:Connections group or water heater. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'water-use', 'service-hot-water', 'schedule', 'honeybee', 'room', 'author'},
        timeout=20,
    )
    def create_ironbug_water_use_equipment(
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
            Field(description="Stable identifier for the new IB_WaterUseEquipment object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        flow_rate_fraction_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for fixture flow-rate fraction over time.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_WaterUseEquipment field Name.'),
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
        water_use_load_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_WaterUseEquipmentDefinition target that supplies the peak "
                    "flow and heat-gain fractions for this fixture."
                )
            ),
        ] = None,
        hb_room_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Honeybee Room target or room identifier used to bind the "
                    "EnergyPlus WaterUse:Equipment object to a Space."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create Ironbug water-use equipment."""

        child_targets = [
            water_use_load_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        ib_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if flow_rate_fraction_schedule_target is not None:
            source_field_targets['FlowRateFractionSchedule'] = flow_rate_fraction_schedule_target
        if hb_room_target is not None:
            ib_properties['SpaceName'] = target_identifier(
                hb_room_target,
                parameter_name="hb_room_target",
            )
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_WaterUseEquipment',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            ib_properties=ib_properties or None,
            child_targets=child_targets if any(item is not None for item in child_targets) else None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
