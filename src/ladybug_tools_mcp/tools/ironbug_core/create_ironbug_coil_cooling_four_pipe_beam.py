'MCP tool for detailed_hvac_coil_cooling_four_pipe_beam.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_coil_cooling_four_pipe_beam tool.'

    @mcp.tool(
        name='coil_cooling_four_pipe_beam',
        description=(
            'Create IB_CoilCoolingFourPipeBeam, an Ironbug chilled-water '
            'cooling coil child for four-pipe beam terminals that maps to '
            'OpenStudio CoilCoolingFourPipeBeam and EnergyPlus four-pipe beam '
            'cooling fields. Use the returned target as the CoolingCoil child '
            'for detailed_hvac_air_terminal_single_duct_constant_volume_four_pipe_beam. '
            'This is not zone equipment and not a Honeybee Energy HVAC '
            'template. Returns target, summary_view, persistence_receipt, and '
            'report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'coil', 'cooling', 'chilled-water', 'beam', 'four-pipe', 'plant-loop', 'air-terminal', 'curve', 'author'},
        timeout=20,
    )
    def create_ironbug_coil_cooling_four_pipe_beam(
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
            Field(description="Stable identifier for the new IB_CoilCoolingFourPipeBeam object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        beam_rated_cooling_capacityper_beam_length: Annotated[
            float | None,
            Field(description='Optional BeamRatedCoolingCapacityperBeamLength in W/m for sensible cooling capacity at the rating point.'),
        ] = None,
        beam_rated_cooling_room_air_chilled_water_temperature_difference: Annotated[
            float | None,
            Field(description='Optional BeamRatedCoolingRoomAirChilledWaterTemperatureDifference in deltaC between room air and entering chilled water.'),
        ] = None,
        beam_rated_chilled_water_volume_flow_rateper_beam_length: Annotated[
            float | None,
            Field(description='Optional BeamRatedChilledWaterVolumeFlowRateperBeamLength in m3/s-m for chilled-water flow normalized by beam length.'),
        ] = None,
        beam_cooling_capacity_temperature_difference_modification_factor_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for BeamCoolingCapacityTemperatureDifferenceModificationFactorCurve; pass a target dict from a compatible detailed_hvac curve tool or a same-model identifier.'),
        ] = None,
        beam_cooling_capacity_air_flow_modification_factor_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for BeamCoolingCapacityAirFlowModificationFactorCurve; pass a target dict from a compatible detailed_hvac curve tool or a same-model identifier.'),
        ] = None,
        beam_cooling_capacity_chilled_water_flow_modification_factor_curve_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Curve target for BeamCoolingCapacityChilledWaterFlowModificationFactorCurve; pass a target dict from a compatible detailed_hvac curve tool or a same-model identifier.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_CoilCoolingFourPipeBeam field Name.'),
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
        """Create IB_CoilCoolingFourPipeBeam as a reviewed four-pipe beam cooling coil child."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if beam_rated_cooling_capacityper_beam_length is not None:
            source_fields['BeamRatedCoolingCapacityperBeamLength'] = beam_rated_cooling_capacityper_beam_length
        if beam_rated_cooling_room_air_chilled_water_temperature_difference is not None:
            source_fields['BeamRatedCoolingRoomAirChilledWaterTemperatureDifference'] = beam_rated_cooling_room_air_chilled_water_temperature_difference
        if beam_rated_chilled_water_volume_flow_rateper_beam_length is not None:
            source_fields['BeamRatedChilledWaterVolumeFlowRateperBeamLength'] = beam_rated_chilled_water_volume_flow_rateper_beam_length
        if beam_cooling_capacity_temperature_difference_modification_factor_curve_target is not None:
            source_field_targets['BeamCoolingCapacityTemperatureDifferenceModificationFactorCurve'] = beam_cooling_capacity_temperature_difference_modification_factor_curve_target
        if beam_cooling_capacity_air_flow_modification_factor_curve_target is not None:
            source_field_targets['BeamCoolingCapacityAirFlowModificationFactorCurve'] = beam_cooling_capacity_air_flow_modification_factor_curve_target
        if beam_cooling_capacity_chilled_water_flow_modification_factor_curve_target is not None:
            source_field_targets['BeamCoolingCapacityChilledWaterFlowModificationFactorCurve'] = beam_cooling_capacity_chilled_water_flow_modification_factor_curve_target
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_CoilCoolingFourPipeBeam',
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
