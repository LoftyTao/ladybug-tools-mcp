'MCP tool for detailed_hvac_electric_load_center_transformer.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_electric_load_center_transformer tool.'

    @mcp.tool(
        name='electric_load_center_transformer',
        description=(
            'Create IB_ElectricLoadCenterTransformer, an EnergyPlus/OpenStudio ElectricLoadCenter:Transformer object for grid input, grid export, or load-center power conditioning. Use TransformerUsage values such as PowerInFromGrid, PowerOutToGrid, or LoadCenterPowerConditioning; only the load-center conditioning transformer is referenced by ElectricLoadCenter:Distribution. This tool authors transformer input only; it is not a distribution panel, inverter, storage device, or simulation runner. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'electric', 'electric-equipment', 'load-center', 'transformer', 'author'},
        timeout=20,
    )
    def create_ironbug_electric_load_center_transformer(
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
            Field(description="Stable identifier for the new IB_ElectricLoadCenterTransformer object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier controlling transformer availability; maps to Ironbug field AvailabilitySchedule.'),
        ] = None,
        transformer_usage: Annotated[
            str | None,
            Field(description='Transformer application type, such as PowerInFromGrid, PowerOutToGrid, or LoadCenterPowerConditioning; maps to Ironbug field TransformerUsage.'),
        ] = None,
        radiative_fraction: Annotated[
            float | None,
            Field(description='Fraction of transformer losses released as zone radiative heat gain; maps to Ironbug field RadiativeFraction.'),
        ] = None,
        rated_capacity: Annotated[
            float | None,
            Field(description='Transformer rated capacity in VA; maps to Ironbug field RatedCapacity.'),
        ] = None,
        phase: Annotated[
            str | None,
            Field(description='Transformer phase selection; maps to Ironbug field Phase.'),
        ] = None,
        conductor_material: Annotated[
            str | None,
            Field(description='Transformer conductor material; maps to Ironbug field ConductorMaterial.'),
        ] = None,
        full_load_temperature_rise: Annotated[
            float | None,
            Field(description='Full-load transformer temperature rise in K; maps to Ironbug field FullLoadTemperatureRise.'),
        ] = None,
        fractionof_eddy_current_losses: Annotated[
            float | None,
            Field(description='Fraction of transformer losses assigned to eddy-current losses; maps to Ironbug field FractionofEddyCurrentLosses.'),
        ] = None,
        performance_input_method: Annotated[
            str | None,
            Field(description='Transformer performance input method; maps to Ironbug field PerformanceInputMethod.'),
        ] = None,
        rated_no_load_loss: Annotated[
            float | None,
            Field(description='Rated no-load transformer loss in W; maps to Ironbug field RatedNoLoadLoss.'),
        ] = None,
        rated_load_loss: Annotated[
            float | None,
            Field(description='Rated load transformer loss in W; maps to Ironbug field RatedLoadLoss.'),
        ] = None,
        nameplate_efficiency: Annotated[
            float | None,
            Field(description='Transformer nameplate efficiency fraction; maps to Ironbug field NameplateEfficiency.'),
        ] = None,
        per_unit_loadfor_nameplate_efficiency: Annotated[
            float | None,
            Field(description='Per-unit load at which nameplate efficiency applies; maps to Ironbug field PerUnitLoadforNameplateEfficiency.'),
        ] = None,
        reference_temperaturefor_nameplate_efficiency: Annotated[
            float | None,
            Field(description='Reference temperature for nameplate efficiency in C; maps to Ironbug field ReferenceTemperatureforNameplateEfficiency.'),
        ] = None,
        per_unit_loadfor_maximum_efficiency: Annotated[
            float | None,
            Field(description='Per-unit load at which transformer efficiency is maximum; maps to Ironbug field PerUnitLoadforMaximumEfficiency.'),
        ] = None,
        consider_transformer_lossfor_utility_cost: Annotated[
            bool | str | None,
            Field(description='Whether transformer losses are considered in utility-cost calculations; maps to Ironbug field ConsiderTransformerLossforUtilityCost.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus/OpenStudio ElectricLoadCenter:Transformer object name; defaults to the identifier when omitted.'),
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
        """Create IB_ElectricLoadCenterTransformer as reviewed load-center transformer data."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if transformer_usage is not None:
            source_fields['TransformerUsage'] = transformer_usage
        if radiative_fraction is not None:
            source_fields['RadiativeFraction'] = radiative_fraction
        if rated_capacity is not None:
            source_fields['RatedCapacity'] = rated_capacity
        if phase is not None:
            source_fields['Phase'] = phase
        if conductor_material is not None:
            source_fields['ConductorMaterial'] = conductor_material
        if full_load_temperature_rise is not None:
            source_fields['FullLoadTemperatureRise'] = full_load_temperature_rise
        if fractionof_eddy_current_losses is not None:
            source_fields['FractionofEddyCurrentLosses'] = fractionof_eddy_current_losses
        if performance_input_method is not None:
            source_fields['PerformanceInputMethod'] = performance_input_method
        if rated_no_load_loss is not None:
            source_fields['RatedNoLoadLoss'] = rated_no_load_loss
        if rated_load_loss is not None:
            source_fields['RatedLoadLoss'] = rated_load_loss
        if nameplate_efficiency is not None:
            source_fields['NameplateEfficiency'] = nameplate_efficiency
        if per_unit_loadfor_nameplate_efficiency is not None:
            source_fields['PerUnitLoadforNameplateEfficiency'] = per_unit_loadfor_nameplate_efficiency
        if reference_temperaturefor_nameplate_efficiency is not None:
            source_fields['ReferenceTemperatureforNameplateEfficiency'] = reference_temperaturefor_nameplate_efficiency
        if per_unit_loadfor_maximum_efficiency is not None:
            source_fields['PerUnitLoadforMaximumEfficiency'] = per_unit_loadfor_maximum_efficiency
        if consider_transformer_lossfor_utility_cost is not None:
            source_fields['ConsiderTransformerLossforUtilityCost'] = consider_transformer_lossfor_utility_cost
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_ElectricLoadCenterTransformer',
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
