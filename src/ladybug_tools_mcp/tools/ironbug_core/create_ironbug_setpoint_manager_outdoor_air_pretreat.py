'MCP tool for detailed_hvac_setpoint_manager_outdoor_air_pretreat.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_setpoint_manager_outdoor_air_pretreat tool.'

    @mcp.tool(
        name='setpoint_manager_outdoor_air_pretreat',
        description=(
            'Create IB_SetpointManagerOutdoorAirPretreat / EnergyPlus SetpointManager:OutdoorAirPretreat for outdoor-air stream temperature and humidity-ratio setpoints. Use it when an outdoor-air path needs pretreatment setpoints based on reference, mixed-air, outdoor-air, and return-air stream nodes supplied by the downstream assembly. This authors Ironbug DetailedHVAC input only; it is not an outdoor-air controller, economizer, weather reader, or Energy simulation runner. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'setpoint', 'control', 'temperature', 'humidity-control', 'humidity-ratio', 'outdoor-air', 'outdoor-air-pretreat', 'air-loop', 'author'},
        timeout=20,
    )
    def create_ironbug_setpoint_manager_outdoor_air_pretreat(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json; for example garden_create['garden_root']."),
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
            Field(description="Stable identifier for the new IB_SetpointManagerOutdoorAirPretreat object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        minimum_setpoint_temperature: Annotated[
            float | None,
            Field(description='Optional lower temperature setpoint limit in deg C for the outdoor-air pretreat manager; maps to Ironbug field MinimumSetpointTemperature.'),
        ] = None,
        maximum_setpoint_temperature: Annotated[
            float | None,
            Field(description='Optional upper temperature setpoint limit in deg C for the outdoor-air pretreat manager; maps to Ironbug field MaximumSetpointTemperature.'),
        ] = None,
        minimum_setpoint_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional lower humidity-ratio limit in kgWater/kgDryAir; maps to Ironbug field MinimumSetpointHumidityRatio.'),
        ] = None,
        maximum_setpoint_humidity_ratio: Annotated[
            float | None,
            Field(description='Optional upper humidity-ratio limit in kgWater/kgDryAir; maps to Ironbug field MaximumSetpointHumidityRatio.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio object name; maps to Ironbug IB_SetpointManagerOutdoorAirPretreat field Name.'),
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
        """Create an Ironbug SetpointManager:OutdoorAirPretreat target."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if minimum_setpoint_temperature is not None:
            source_fields['MinimumSetpointTemperature'] = minimum_setpoint_temperature
        if maximum_setpoint_temperature is not None:
            source_fields['MaximumSetpointTemperature'] = maximum_setpoint_temperature
        if minimum_setpoint_humidity_ratio is not None:
            source_fields['MinimumSetpointHumidityRatio'] = minimum_setpoint_humidity_ratio
        if maximum_setpoint_humidity_ratio is not None:
            source_fields['MaximumSetpointHumidityRatio'] = maximum_setpoint_humidity_ratio
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SetpointManagerOutdoorAirPretreat',
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
