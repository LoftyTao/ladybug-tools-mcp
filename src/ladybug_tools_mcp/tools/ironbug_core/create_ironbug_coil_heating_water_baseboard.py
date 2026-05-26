'MCP tool for detailed_hvac_coil_heating_water_baseboard.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_heating_water_baseboard tool.'

    @mcp.tool(
        name='coil_heating_water_baseboard',
        description=(
            'Create IB_CoilHeatingWaterBaseboard, the hot-water coil child for IB_ZoneHVACBaseboardConvectiveWater / EnergyPlus ZoneHVAC:Baseboard:Convective:Water equipment. Use it to define baseboard design capacity, UA, maximum hot-water flow, and convergence tolerance; connect its water side to a hot-water loop demand branch and use the parent baseboard zone-equipment tool for thermal-zone placement. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'heating', 'hot-water', 'baseboard', 'convective', 'zone-equipment', 'plant-loop', 'thermal-zone', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_heating_water_baseboard(
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
            Field(description="Stable identifier for the new IB_CoilHeatingWaterBaseboard object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        heating_design_capacity_method: Annotated[
            str | None,
            Field(description='Optional scalable sizing method for the hot-water baseboard, such as HeatingDesignCapacity, CapacityPerFloorArea, or FractionOfAutosizedHeatingCapacity. Maps to Ironbug IB_CoilHeatingWaterBaseboard field HeatingDesignCapacityMethod.'),
        ] = None,
        heating_design_capacity: Annotated[
            float | str | None,
            Field(description='Optional baseboard design heating capacity in W, or an autosize-style value accepted by Ironbug. Maps to Ironbug IB_CoilHeatingWaterBaseboard field HeatingDesignCapacity.'),
        ] = None,
        heating_design_capacity_per_floor_area: Annotated[
            float | None,
            Field(description='Optional baseboard heating capacity per floor area for the CapacityPerFloorArea sizing method. Maps to Ironbug IB_CoilHeatingWaterBaseboard field HeatingDesignCapacityPerFloorArea.'),
        ] = None,
        fractionof_autosized_heating_design_capacity: Annotated[
            float | None,
            Field(description='Optional fraction of autosized baseboard heating capacity for the FractionOfAutosizedHeatingCapacity sizing method. Maps to Ironbug IB_CoilHeatingWaterBaseboard field FractionofAutosizedHeatingDesignCapacity.'),
        ] = None,
        u_factor_times_area_value: Annotated[
            float | str | None,
            Field(description='Optional UA value for the convective hot-water baseboard heat transfer calculation, in W/K or an autosize-style value accepted by Ironbug. Maps to Ironbug IB_CoilHeatingWaterBaseboard field UFactorTimesAreaValue.'),
        ] = None,
        maximum_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional maximum hot-water volumetric flow rate through the baseboard coil, or an autosize-style value accepted by Ironbug. Maps to Ironbug IB_CoilHeatingWaterBaseboard field MaximumWaterFlowRate.'),
        ] = None,
        convergence_tolerance: Annotated[
            float | None,
            Field(description='Optional tolerance for matching convective baseboard output to zone heating demand. Maps to Ironbug IB_CoilHeatingWaterBaseboard field ConvergenceTolerance.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilHeatingWaterBaseboard field Name.'),
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
        """Create IB_CoilHeatingWaterBaseboard as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if heating_design_capacity_method is not None:
            source_fields['HeatingDesignCapacityMethod'] = heating_design_capacity_method
        if heating_design_capacity is not None:
            source_fields['HeatingDesignCapacity'] = heating_design_capacity
        if heating_design_capacity_per_floor_area is not None:
            source_fields['HeatingDesignCapacityPerFloorArea'] = heating_design_capacity_per_floor_area
        if fractionof_autosized_heating_design_capacity is not None:
            source_fields['FractionofAutosizedHeatingDesignCapacity'] = fractionof_autosized_heating_design_capacity
        if u_factor_times_area_value is not None:
            source_fields['UFactorTimesAreaValue'] = u_factor_times_area_value
        if maximum_water_flow_rate is not None:
            source_fields['MaximumWaterFlowRate'] = maximum_water_flow_rate
        if convergence_tolerance is not None:
            source_fields['ConvergenceTolerance'] = convergence_tolerance
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilHeatingWaterBaseboard',
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
