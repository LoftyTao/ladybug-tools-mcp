'MCP tool for detailed_hvac_coil_heating_water_baseboard_radiant.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_heating_water_baseboard_radiant tool.'

    @mcp.tool(
        name='coil_heating_water_baseboard_radiant',
        description=(
            'Create IB_CoilHeatingWaterBaseboardRadiant, the hot-water coil child for IB_ZoneHVACBaseboardRadiantConvectiveWater / EnergyPlus ZoneHVAC:Baseboard:RadiantConvective:Water equipment. Use it to define rated water temperature, rated water mass flow, heating capacity, and maximum water flow; connect its water side to a hot-water loop demand branch and use the parent baseboard zone-equipment tool for thermal-zone placement and radiant distribution. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'heating', 'hot-water', 'baseboard', 'radiant', 'convective', 'thermal-comfort', 'zone-equipment', 'plant-loop', 'thermal-zone', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_heating_water_baseboard_radiant(
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
            Field(description="Stable identifier for the new IB_CoilHeatingWaterBaseboardRadiant object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        rated_average_water_temperature: Annotated[
            float | None,
            Field(description='Optional rated average water temperature for the radiant-convective baseboard coil, in degrees C. Maps to Ironbug IB_CoilHeatingWaterBaseboardRadiant field RatedAverageWaterTemperature.'),
        ] = None,
        rated_water_mass_flow_rate: Annotated[
            float | None,
            Field(description='Optional rated hot-water mass flow rate for the radiant-convective baseboard coil, in kg/s. Maps to Ironbug IB_CoilHeatingWaterBaseboardRadiant field RatedWaterMassFlowRate.'),
        ] = None,
        heating_design_capacity_method: Annotated[
            str | None,
            Field(description='Optional scalable sizing method for the radiant-convective water baseboard, such as HeatingDesignCapacity, CapacityPerFloorArea, or FractionOfAutosizedHeatingCapacity. Maps to Ironbug IB_CoilHeatingWaterBaseboardRadiant field HeatingDesignCapacityMethod.'),
        ] = None,
        heating_design_capacity: Annotated[
            float | str | None,
            Field(description='Optional rated heating capacity in W for the radiant-convective baseboard coil, or an autosize-style value accepted by Ironbug. Maps to Ironbug IB_CoilHeatingWaterBaseboardRadiant field HeatingDesignCapacity.'),
        ] = None,
        heating_design_capacity_per_floor_area: Annotated[
            float | None,
            Field(description='Optional radiant-convective baseboard heating capacity per floor area for scalable sizing. Maps to Ironbug IB_CoilHeatingWaterBaseboardRadiant field HeatingDesignCapacityPerFloorArea.'),
        ] = None,
        fractionof_autosized_heating_design_capacity: Annotated[
            float | None,
            Field(description='Optional fraction of autosized heating capacity for the radiant-convective baseboard coil. Maps to Ironbug IB_CoilHeatingWaterBaseboardRadiant field FractionofAutosizedHeatingDesignCapacity.'),
        ] = None,
        maximum_water_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional maximum hot-water volumetric flow rate through the radiant-convective baseboard coil, or an autosize-style value accepted by Ironbug. Maps to Ironbug IB_CoilHeatingWaterBaseboardRadiant field MaximumWaterFlowRate.'),
        ] = None,
        convergence_tolerance: Annotated[
            float | None,
            Field(description='Optional tolerance used when the radiant-convective baseboard coil output is matched to zone heating demand. Maps to Ironbug IB_CoilHeatingWaterBaseboardRadiant field ConvergenceTolerance.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilHeatingWaterBaseboardRadiant field Name.'),
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
        """Create IB_CoilHeatingWaterBaseboardRadiant as a reviewed Ironbug LoopObjs / PlantLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if rated_average_water_temperature is not None:
            source_fields['RatedAverageWaterTemperature'] = rated_average_water_temperature
        if rated_water_mass_flow_rate is not None:
            source_fields['RatedWaterMassFlowRate'] = rated_water_mass_flow_rate
        if heating_design_capacity_method is not None:
            source_fields['HeatingDesignCapacityMethod'] = heating_design_capacity_method
        if heating_design_capacity is not None:
            source_fields['HeatingDesignCapacity'] = heating_design_capacity
        if heating_design_capacity_per_floor_area is not None:
            source_fields['HeatingDesignCapacityPerFloorArea'] = heating_design_capacity_per_floor_area
        if fractionof_autosized_heating_design_capacity is not None:
            source_fields['FractionofAutosizedHeatingDesignCapacity'] = fractionof_autosized_heating_design_capacity
        if maximum_water_flow_rate is not None:
            source_fields['MaximumWaterFlowRate'] = maximum_water_flow_rate
        if convergence_tolerance is not None:
            source_fields['ConvergenceTolerance'] = convergence_tolerance
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilHeatingWaterBaseboardRadiant',
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
