'MCP tool for detailed_hvac_coil_heating_gas_multi_stage.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_heating_gas_multi_stage tool.'

    @mcp.tool(
        name='coil_heating_gas_multi_stage',
        description=(
            'Create IB_CoilHeatingGasMultiStage, an OpenStudio/EnergyPlus Coil:Heating:Gas:MultiStage fuel-fired air heating coil with per-stage burner efficiency and capacity data. Provide IB_CoilHeatingGasMultiStageStageData targets or inline stages_* fields for the gas heating stages; supported unitary or multi-speed heat-pump assemblies use this parent coil. Use water coil tools for hydronic plant-loop equipment. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'heating', 'gas', 'fuel', 'gas-equipment', 'multi-stage', 'stage-data', 'air-loop', 'unitary', 'curve', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_heating_gas_multi_stage(
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
            Field(description="Stable identifier for the new IB_CoilHeatingGasMultiStage object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        stages_targets: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional IB_CoilHeatingGasMultiStageStageData targets or same-model identifiers for the multi-stage gas coil stages. Use this instead of inline stages_* fields when stage objects already exist."
            ),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for the multi-stage gas coil availability schedule. Maps to Ironbug IB_CoilHeatingGasMultiStage field AvailabilitySchedule.'),
        ] = None,
        part_load_fraction_correlation_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target or same-model identifier for the part-load fraction correlation curve used to model fuel-consumption losses during cycling. Maps to Ironbug IB_CoilHeatingGasMultiStage field PartLoadFractionCorrelationCurve.'),
        ] = None,
        parasitic_gas_load: Annotated[
            str | float | int | bool | None,
            Field(description='Optional parasitic gas load for the multi-stage heating coil. Maps to Ironbug IB_CoilHeatingGasMultiStage field ParasiticGasLoad.'),
        ] = None,
        off_cycle_parasitic_gas_load: Annotated[
            float | None,
            Field(description='Optional off-cycle parasitic gas load, such as a standing pilot light. Maps to Ironbug IB_CoilHeatingGasMultiStage field OffCycleParasiticGasLoad.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilHeatingGasMultiStage field Name.'),
        ] = None,
        stages_identifiers: Annotated[
            list[str] | None,
            Field(description='Optional inline identifiers for generated IB_CoilHeatingGasMultiStageStageData children in IB_CoilHeatingGasMultiStage.Stages.'),
        ] = None,
        stages_name_values: Annotated[
            list[str | None] | None,
            Field(description='Optional inline Name values for generated gas multi-stage stage-data children. Maps to Ironbug IB_CoilHeatingGasMultiStage.Stages child field Name.'),
        ] = None,
        stages_gas_burner_efficiency_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline per-stage gas burner efficiency values as decimal fractions. Maps to Ironbug IB_CoilHeatingGasMultiStage.Stages child field GasBurnerEfficiency.'),
        ] = None,
        stages_nominal_capacity_values: Annotated[
            list[float | str | None] | None,
            Field(description='Optional inline per-stage nominal heating capacities in W, or autosize-style values accepted by Ironbug. Maps to Ironbug IB_CoilHeatingGasMultiStage.Stages child field NominalCapacity.'),
        ] = None,
        stages_parasitic_electric_load_values: Annotated[
            list[str | float | int | bool | None] | None,
            Field(description='Optional inline per-stage parasitic electric load values for generated stage-data children. Maps to Ironbug IB_CoilHeatingGasMultiStage.Stages child field ParasiticElectricLoad.'),
        ] = None,
        stages_on_cycle_parasitic_electric_load_values: Annotated[
            list[float | None] | None,
            Field(description='Optional inline per-stage on-cycle parasitic electric load values. Maps to Ironbug IB_CoilHeatingGasMultiStage.Stages child field OnCycleParasiticElectricLoad.'),
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
        """Create IB_CoilHeatingGasMultiStage as a reviewed Ironbug Loop Objs authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        source_property_targets: dict[str, Any] = {}
        inline_source_property_children: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if part_load_fraction_correlation_curve_target is not None:
            source_field_targets['PartLoadFractionCorrelationCurve'] = part_load_fraction_correlation_curve_target
        if parasitic_gas_load is not None:
            source_fields['ParasiticGasLoad'] = parasitic_gas_load
        if off_cycle_parasitic_gas_load is not None:
            source_fields['OffCycleParasiticGasLoad'] = off_cycle_parasitic_gas_load
        if stages_targets is not None:
            source_property_targets['Stages'] = stages_targets
        inline_stages_fields: dict[str, Any] = {}
        inline_stages_field_targets: dict[str, Any] = {}
        if stages_name_values is not None:
            inline_stages_fields['Name'] = stages_name_values
        if stages_gas_burner_efficiency_values is not None:
            inline_stages_fields['GasBurnerEfficiency'] = stages_gas_burner_efficiency_values
        if stages_nominal_capacity_values is not None:
            inline_stages_fields['NominalCapacity'] = stages_nominal_capacity_values
        if stages_parasitic_electric_load_values is not None:
            inline_stages_fields['ParasiticElectricLoad'] = stages_parasitic_electric_load_values
        if stages_on_cycle_parasitic_electric_load_values is not None:
            inline_stages_fields['OnCycleParasiticElectricLoad'] = stages_on_cycle_parasitic_electric_load_values
        if stages_identifiers is not None or inline_stages_fields or inline_stages_field_targets:
            if stages_targets is not None:
                raise ValueError("Provide either stages_targets or inline stages_* parameters, not both.")
            inline_source_property_children['Stages'] = {
                'source_class': 'IB_CoilHeatingGasMultiStageStageData',
                'is_list': True,
                'identifiers': stages_identifiers,
                'source_fields': inline_stages_fields,
                'source_field_targets': inline_stages_field_targets,
            }
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilHeatingGasMultiStage',
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
