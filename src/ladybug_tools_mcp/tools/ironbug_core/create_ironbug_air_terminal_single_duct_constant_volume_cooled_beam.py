'MCP tool for detailed_hvac_air_terminal_single_duct_constant_volume_cooled_beam.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    set_ironbug_thermal_zone_air_terminal,
)



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_air_terminal_single_duct_constant_volume_cooled_beam tool.'

    @mcp.tool(
        name='air_terminal_single_duct_constant_volume_cooled_beam',
        description=(
            'Create IB_AirTerminalSingleDuctConstantVolumeCooledBeam, an '
            'Ironbug single-duct constant-volume cooled beam air terminal '
            'that maps downstream to EnergyPlus/OpenStudio '
            'AirTerminal:SingleDuct:ConstantVolume:CooledBeam. Use the '
            'returned target as a cooled-beam terminal unit, attach an '
            'IB_CoilCoolingCooledBeam child when needed, and bind it to an '
            'IB_ThermalZone through thermal_zone_target or the ThermalZone '
            'tool. This is not zone equipment and not a Honeybee Energy HVAC '
            'template. Returns target, summary_view, persistence_receipt, and '
            'report for downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'air-terminal', 'terminal-unit', 'single-duct', 'constant-volume', 'beam', 'cooled-beam', 'cooling', 'chilled-water', 'thermal-zone', 'author'},
        timeout=20,
    )
    def create_ironbug_air_terminal_single_duct_constant_volume_cooled_beam(
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
            Field(description="Stable identifier for the new IB_AirTerminalSingleDuctConstantVolumeCooledBeam object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        availability_schedule_target: Annotated[
            dict[str, Any] | str | None,
            Field(description='Optional IB_Schedule target for AvailabilitySchedule; pass a target dict from a compatible detailed_hvac schedule tool or a same-model identifier. Schedule values above zero make the cooled beam terminal available.'),
        ] = None,
        cooled_beam_type: Annotated[
            str | None,
            Field(description="Optional CooledBeamType, typically 'Active' or 'Passive' for EnergyPlus/OpenStudio cooled beam terminals."),
        ] = None,
        supply_air_volumetric_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional SupplyAirVolumetricFlowRate in m3/s, or an EnergyPlus autosizable literal accepted by Ironbug.'),
        ] = None,
        maximum_total_chilled_water_volumetric_flow_rate: Annotated[
            float | str | None,
            Field(description='Optional MaximumTotalChilledWaterVolumetricFlowRate in m3/s for the cooled beam chilled-water circuit, or an autosizable literal accepted by Ironbug.'),
        ] = None,
        numberof_beams: Annotated[
            int | str | None,
            Field(description='Optional NumberofBeams, the count of individual beam units in the zone; Ironbug also accepts autosizable literals where supported.'),
        ] = None,
        beam_length: Annotated[
            float | str | None,
            Field(description='Optional BeamLength in meters for each cooled beam, or an EnergyPlus autosizable literal accepted by Ironbug.'),
        ] = None,
        design_inlet_water_temperature: Annotated[
            float | None,
            Field(description='Optional DesignInletWaterTemperature in degrees C for the chilled-water beam coil.'),
        ] = None,
        design_outlet_water_temperature: Annotated[
            float | None,
            Field(description='Optional DesignOutletWaterTemperature in degrees C for the chilled-water beam coil.'),
        ] = None,
        coefficientof_induction_kin: Annotated[
            float | None,
            Field(description='Optional CoefficientofInductionKin, a dimensionless cooled-beam induction coefficient; EnergyPlus also supports autocalculation.'),
        ] = None,
        thermal_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ThermalZone target or same-model identifier to "
                    "bind this cooled beam air terminal to after creation; "
                    "this does not create Honeybee Room geometry."
                )
            ),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_AirTerminalSingleDuctConstantVolumeCooledBeam field Name.'),
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
        cooling_coil_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_CoilCoolingCooledBeam child target or same-model "
                    "identifier for Parameter 'CoolingCoil'; use a "
                    "detailed_hvac_coil_cooling_cooled_beam target."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_AirTerminalSingleDuctConstantVolumeCooledBeam as a reviewed cooled beam terminal."""

        child_targets = [
            cooling_coil_target,
        ]
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if availability_schedule_target is not None:
            source_field_targets['AvailabilitySchedule'] = availability_schedule_target
        if cooled_beam_type is not None:
            source_fields['CooledBeamType'] = cooled_beam_type
        if supply_air_volumetric_flow_rate is not None:
            source_fields['SupplyAirVolumetricFlowRate'] = supply_air_volumetric_flow_rate
        if maximum_total_chilled_water_volumetric_flow_rate is not None:
            source_fields['MaximumTotalChilledWaterVolumetricFlowRate'] = maximum_total_chilled_water_volumetric_flow_rate
        if numberof_beams is not None:
            source_fields['NumberofBeams'] = numberof_beams
        if beam_length is not None:
            source_fields['BeamLength'] = beam_length
        if design_inlet_water_temperature is not None:
            source_fields['DesignInletWaterTemperature'] = design_inlet_water_temperature
        if design_outlet_water_temperature is not None:
            source_fields['DesignOutletWaterTemperature'] = design_outlet_water_temperature
        if coefficientof_induction_kin is not None:
            source_fields['CoefficientofInductionKin'] = coefficientof_induction_kin
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_AirTerminalSingleDuctConstantVolumeCooledBeam',
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
        latest_model_target = created["updated_model_target"]
        binding_summary: dict[str, Any] = {}
        if thermal_zone_target is not None:
            zone = set_ironbug_thermal_zone_air_terminal(
                garden_root=garden_root,
                ironbug_model_target=latest_model_target,
                thermal_zone_target=thermal_zone_target,
                air_terminal_target=created["target"],
            )
            latest_model_target = zone["updated_model_target"]
            created["target"]["model_target"] = latest_model_target
            binding_summary["thermal_zone_bound"] = True
            binding_summary["thermal_zone_identifier"] = zone["summary_view"][
                "thermal_zone_identifier"
            ]
        else:
            binding_summary["thermal_zone_bound"] = False
        created["updated_model_target"] = latest_model_target
        created["summary_view"] = {**created["summary_view"], **binding_summary}
        return created
