'MCP tool for detailed_hvac_coil_heating_desuperheater.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_heating_desuperheater tool.'

    @mcp.tool(
        name='coil_heating_desuperheater',
        description=(
            'Create IB_CoilHeatingDesuperheater, an OpenStudio/EnergyPlus Coil:Heating:Desuperheater air heating coil that reclaims heat from superheated refrigerant gas from a DX cooling source. Pass heating_source_target as an IB_CoilCoolingDXSingleSpeed or IB_CoilCoolingDXTwoSpeed target. Use gas heating coil or hydronic water coil tools for burner or water-loop systems. Returns target, summary_view, persistence_receipt, and report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'heating', 'desuperheater', 'heat-reclaim', 'refrigeration', 'dx', 'air-loop', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_heating_desuperheater(
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
            Field(description="Stable identifier for the new IB_CoilHeatingDesuperheater object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier for the desuperheater availability schedule; schedule values above 0 allow heat reclaim. Maps to Ironbug IB_CoilHeatingDesuperheater field AvailabilitySchedule.'),
        ] = None,
        heat_reclaim_recovery_efficiency: Annotated[
            float | None,
            Field(description='Optional heat reclaim recovery efficiency fraction for superheated refrigerant heat recovery. Maps to Ironbug IB_CoilHeatingDesuperheater field HeatReclaimRecoveryEfficiency.'),
        ] = None,
        parasitic_electric_load: Annotated[
            str | float | int | bool | None,
            Field(description='Optional parasitic electric load for desuperheater operation, in W or an autosize-style value accepted by Ironbug. Maps to Ironbug IB_CoilHeatingDesuperheater field ParasiticElectricLoad.'),
        ] = None,
        on_cycle_parasitic_electric_load: Annotated[
            float | None,
            Field(description='Optional on-cycle parasitic electric load for the heat-reclaim coil. Maps to Ironbug IB_CoilHeatingDesuperheater field OnCycleParasiticElectricLoad.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilHeatingDesuperheater field Name.'),
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
        heating_source_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional Ironbug DX cooling source target for recovered superheat. Use "
                    "IB_CoilCoolingDXSingleSpeed or IB_CoilCoolingDXTwoSpeed. Maps to the "
                    "Grasshopper HeatingSource input on IB_CoilHeatingDesuperheater."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_CoilHeatingDesuperheater as a reviewed Ironbug Loop Objs authoring object."""

        child_targets = [
            heating_source_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if heat_reclaim_recovery_efficiency is not None:
            source_fields['HeatReclaimRecoveryEfficiency'] = heat_reclaim_recovery_efficiency
        if parasitic_electric_load is not None:
            source_fields['ParasiticElectricLoad'] = parasitic_electric_load
        if on_cycle_parasitic_electric_load is not None:
            source_fields['OnCycleParasiticElectricLoad'] = on_cycle_parasitic_electric_load
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilHeatingDesuperheater',
            identifier=identifier,
            display_name=display_name,
            source_fields=source_fields or None,
            source_field_targets=source_field_targets or None,
            source_properties=source_properties or None,
            child_targets=child_targets if any(item is not None for item in child_targets) else None,
            output_variable_names=output_variable_names,
            output_reporting_frequency=output_reporting_frequency,
            ems_sensor_targets=ems_sensor_targets,
            ems_actuator_targets=ems_actuator_targets,
            ems_internal_variable_targets=ems_internal_variable_targets,
            overwrite=overwrite,
        )
