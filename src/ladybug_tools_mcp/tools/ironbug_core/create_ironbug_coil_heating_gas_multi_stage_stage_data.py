'MCP tool for detailed_hvac_coil_heating_gas_multi_stage_stage_data.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_heating_gas_multi_stage_stage_data tool.'

    @mcp.tool(
        name='coil_heating_gas_multi_stage_stage_data',
        description=(
            'Create IB_CoilHeatingGasMultiStageStageData, the per-stage performance child object for an IB_CoilHeatingGasMultiStage / EnergyPlus Coil:Heating:Gas:MultiStage coil. Use it to define one gas heating stage burner efficiency, nominal capacity, and parasitic electric loads; attach it to coil_heating_gas_multi_stage instead of using it as parent equipment. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'heating', 'gas', 'fuel', 'multi-stage', 'stage-data', 'performance', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_heating_gas_multi_stage_stage_data(
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
            Field(description="Stable identifier for the new IB_CoilHeatingGasMultiStageStageData object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        gas_burner_efficiency: Annotated[
            float | None,
            Field(description='Optional gas burner efficiency for this multi-stage heating coil stage, as a decimal fraction. Maps to Ironbug IB_CoilHeatingGasMultiStageStageData field GasBurnerEfficiency.'),
        ] = None,
        nominal_capacity: Annotated[
            float | str | None,
            Field(description='Optional nominal heating capacity for this stage in W, or an autosize-style value accepted by Ironbug. Maps to Ironbug IB_CoilHeatingGasMultiStageStageData field NominalCapacity.'),
        ] = None,
        parasitic_electric_load: Annotated[
            str | float | int | bool | None,
            Field(description='Optional parasitic electric load for this gas heating stage. Maps to Ironbug IB_CoilHeatingGasMultiStageStageData field ParasiticElectricLoad.'),
        ] = None,
        on_cycle_parasitic_electric_load: Annotated[
            float | None,
            Field(description='Optional on-cycle parasitic electric load for this gas heating stage. Maps to Ironbug IB_CoilHeatingGasMultiStageStageData field OnCycleParasiticElectricLoad.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilHeatingGasMultiStageStageData field Name.'),
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
        """Create IB_CoilHeatingGasMultiStageStageData as a reviewed Ironbug Loop Objs authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if gas_burner_efficiency is not None:
            source_fields['GasBurnerEfficiency'] = gas_burner_efficiency
        if nominal_capacity is not None:
            source_fields['NominalCapacity'] = nominal_capacity
        if parasitic_electric_load is not None:
            source_fields['ParasiticElectricLoad'] = parasitic_electric_load
        if on_cycle_parasitic_electric_load is not None:
            source_fields['OnCycleParasiticElectricLoad'] = on_cycle_parasitic_electric_load
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilHeatingGasMultiStageStageData',
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
