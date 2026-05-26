'MCP tool for detailed_hvac_humidifier_steam_electric.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_humidifier_steam_electric tool.'

    @mcp.tool(
        name='humidifier_steam_electric',
        description=(
            'Create IB_HumidifierSteamElectric, an EnergyPlus Humidifier:Steam:Electric air-loop component that injects electrically generated steam into the supply air stream. Use it with a humidity-ratio setpoint on the outlet node and fields for availability, rated water-addition capacity, rated electric power, fan power, and standby power; this is not a gas humidifier, water-use tank, zone humidistat, desiccant heat exchanger, or Energy run. Returns target, summary_view, persistence_receipt, and report.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={
            'ironbug',
            'detailed-hvac',
            'hvac',
            'component',
            'air-loop',
            'humidifier',
            'humidity-control',
            'steam',
            'electric',
            'author',
        },
        timeout=20,
    )
    def create_ironbug_humidifier_steam_electric(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, for example garden_create['garden_root']."),
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
            Field(description="Stable identifier for the new IB_HumidifierSteamElectric object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target or same-model identifier controlling when the electric steam humidifier can run; maps to AvailabilitySchedule.'),
        ] = None,
        rated_capacity: Annotated[
            float | str | None,
            Field(description='Optional nominal water-addition rate in m3/s, or autosize string, for the electric steam humidifier; maps to RatedCapacity.'),
        ] = None,
        rated_power: Annotated[
            float | str | None,
            Field(description='Optional full-output electric power in W, excluding blower fan and standby power, or autosize string; maps to RatedPower.'),
        ] = None,
        rated_fan_power: Annotated[
            float | None,
            Field(description='Optional blower fan electric power in W for steam injection; maps to RatedFanPower.'),
        ] = None,
        standby_power: Annotated[
            float | None,
            Field(description='Optional standby electric power in W consumed when the humidifier is available; maps to StandbyPower.'),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional EnergyPlus object name for this Humidifier:Steam:Electric; maps to Name.'),
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
        """Create IB_HumidifierSteamElectric as a reviewed Ironbug LoopObjs / AirLoopObjects authoring object."""

        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if rated_capacity is not None:
            source_fields['RatedCapacity'] = rated_capacity
        if rated_power is not None:
            source_fields['RatedPower'] = rated_power
        if rated_fan_power is not None:
            source_fields['RatedFanPower'] = rated_fan_power
        if standby_power is not None:
            source_fields['StandbyPower'] = standby_power
        return create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_HumidifierSteamElectric',
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
