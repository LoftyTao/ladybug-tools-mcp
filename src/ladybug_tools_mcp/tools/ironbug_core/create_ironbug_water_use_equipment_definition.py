'MCP tool for detailed_hvac_water_use_equipment_definition.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_water_use_equipment_definition tool.'

    @mcp.tool(
        name='water_use_equipment_definition',
        description=(
            'Create IB_WaterUseEquipmentDefinition, the Ironbug WaterUse:Equipment definition/load target that stores peak flow rate plus target-temperature, sensible, and latent fraction schedules for a WaterUse:Equipment fixture. Use it as fixture load data, not as a plant-loop connection, water heater, or result reader. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'load', 'water-use', 'service-hot-water', 'schedule', 'author', 'component'},
        timeout=20,
    )
    def create_ironbug_water_use_equipment_definition(
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
            Field(description="Stable identifier for the new IB_WaterUseEquipmentDefinition object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        peak_flow_rate: Annotated[
            float | None,
            Field(
                description="Optional peak fixture water flow rate in m3/s."
            ),
        ] = None,
        end_use_subcategory: Annotated[
            str | None,
            Field(description='Optional EndUseSubcategory value; maps to Ironbug IB_WaterUseEquipmentDefinition field EndUseSubcategory.'),
        ] = None,
        target_temperature_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for TargetTemperatureSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_WaterUseEquipmentDefinition field TargetTemperatureSchedule (IB_Schedule).'),
        ] = None,
        sensible_fraction_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for SensibleFractionSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_WaterUseEquipmentDefinition field SensibleFractionSchedule (IB_Schedule).'),
        ] = None,
        latent_fraction_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional Ironbug object target for LatentFractionSchedule; pass a target dict from a compatible create_ironbug_* tool or a same-model identifier. Maps to Ironbug IB_WaterUseEquipmentDefinition field LatentFractionSchedule (IB_Schedule).'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_WaterUseEquipmentDefinition field Name.'),
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
        """Create Ironbug water-use fixture load data."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        if peak_flow_rate is not None:
            source_fields['PeakFlowRate'] = peak_flow_rate
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if end_use_subcategory is not None:
            source_fields['EndUseSubcategory'] = end_use_subcategory
        if target_temperature_schedule_target is not None:
            source_field_targets['TargetTemperatureSchedule'] = target_temperature_schedule_target
        if sensible_fraction_schedule_target is not None:
            source_field_targets['SensibleFractionSchedule'] = sensible_fraction_schedule_target
        if latent_fraction_schedule_target is not None:
            source_field_targets['LatentFractionSchedule'] = latent_fraction_schedule_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_WaterUseEquipmentDefinition',
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
