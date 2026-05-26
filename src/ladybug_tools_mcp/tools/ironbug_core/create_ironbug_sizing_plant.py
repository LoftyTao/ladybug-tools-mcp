'MCP tool for detailed_hvac_sizing_plant.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_sizing_plant tool.'

    @mcp.tool(
        name='sizing_plant',
        description=(
            'Create IB_SizingPlant, the Ironbug and EnergyPlus Sizing:Plant object for plant or condenser loop autosizing inputs. It sets loop type, design loop exit temperature, and loop design temperature difference for downstream PlantLoop sizing; it does not create plant equipment, run sizing calculations, or read simulation results. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'sizing', 'plant-loop', 'condenser-water', 'hot-water', 'chilled-water', 'author', 'component'},
        timeout=20,
    )
    def create_ironbug_sizing_plant(
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
            Field(description="Stable identifier for the new IB_SizingPlant object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        loop_type: Annotated[
            str | None,
            Field(
                description="Optional Sizing:Plant loop type, such as Heating, Cooling, Condenser, or Steam."
            ),
        ] = None,
        design_loop_exit_temperature: Annotated[
            float | None,
            Field(
                description="Optional plant or condenser loop design exit temperature in deg C."
            ),
        ] = None,
        loop_design_temperature_difference: Annotated[
            float | None,
            Field(
                description="Optional plant or condenser loop design temperature difference in deltaC."
            ),
        ] = None,
        sizing_option: Annotated[
            str | None,
            Field(description='Optional SizingOption value; maps to Ironbug IB_SizingPlant field SizingOption.'),
        ] = None,
        zone_timestepsin_averaging_window: Annotated[
            int | None,
            Field(description='Optional ZoneTimestepsinAveragingWindow value; maps to Ironbug IB_SizingPlant field ZoneTimestepsinAveragingWindow.'),
        ] = None,
        coincident_sizing_factor_mode: Annotated[
            str | None,
            Field(description='Optional CoincidentSizingFactorMode value; maps to Ironbug IB_SizingPlant field CoincidentSizingFactorMode.'),
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
        """Create Ironbug plant-loop sizing inputs."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if loop_type is not None:
            source_fields['LoopType'] = loop_type
        if design_loop_exit_temperature is not None:
            source_fields['DesignLoopExitTemperature'] = design_loop_exit_temperature
        if loop_design_temperature_difference is not None:
            source_fields['LoopDesignTemperatureDifference'] = loop_design_temperature_difference
        source_properties: dict[str, Any] = {}
        if sizing_option is not None:
            source_fields['SizingOption'] = sizing_option
        if zone_timestepsin_averaging_window is not None:
            source_fields['ZoneTimestepsinAveragingWindow'] = zone_timestepsin_averaging_window
        if coincident_sizing_factor_mode is not None:
            source_fields['CoincidentSizingFactorMode'] = coincident_sizing_factor_mode
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_SizingPlant',
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
