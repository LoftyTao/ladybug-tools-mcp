'MCP tool for detailed_hvac_air_terminal_single_duct_inlet_side_mixer.'

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from garden.ironbug_core.create_tools import create_source_backed_ironbug_object
from garden.ironbug_core.relationships import (
    add_ironbug_child,
    set_ironbug_thermal_zone_air_terminal,
)


def _coalesce_zone_equipment_target(
    *,
    direct_target: dict[str, Any] | str | None,
    parameter_target: dict[str, Any] | str | None,
) -> dict[str, Any] | str | None:
    if direct_target is not None and parameter_target is not None and direct_target != parameter_target:
        raise ValueError(
            "Pass either zone_equipment_child_target or zone_equipment_target, "
            "not conflicting targets."
        )
    return direct_target if direct_target is not None else parameter_target



def register(mcp: FastMCP) -> None:
    'Register the detailed_hvac_air_terminal_single_duct_inlet_side_mixer tool.'

    @mcp.tool(
        name='air_terminal_single_duct_inlet_side_mixer',
        description=(
            'Create IB_AirTerminalSingleDuctInletSideMixer, an Ironbug '
            'inlet-side air terminal mixer for dedicated outdoor air (DOAS) '
            'or central primary air serving a ZoneHVAC child. It maps to the '
            'EnergyPlus/OpenStudio AirTerminal:SingleDuct:Mixer family through '
            'the inlet-side path. Use zone_equipment_child_target for the '
            'mixed ZoneHVAC equipment, and bind the mixer to an IB_ThermalZone '
            'through thermal_zone_target or the ThermalZone tool. This is not '
            'an air-loop root object and not a Honeybee Energy HVAC template. '
            'Returns target, summary_view, persistence_receipt, and report for '
            'downstream DetailedHVAC assembly.'
            'This tool authors Ironbug DetailedHVAC input only; run Energy simulation with the standard Ladybug Tools MCP Energy workflow after DetailedHVAC is applied. '
        ),
        tags={'ironbug', 'detailed-hvac', 'hvac', 'component', 'air-terminal', 'mixer', 'doas', 'ventilation', 'zone-equipment', 'thermal-zone', 'author'},
        timeout=20,
    )
    def create_ironbug_air_terminal_single_duct_inlet_side_mixer(
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
            Field(description="Stable identifier for the new IB_AirTerminalSingleDuctInletSideMixer object."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing Ironbug DisplayName."),
        ] = None,
        control_for_outdoor_air: Annotated[
            bool | str | None,
            Field(description='Optional ControlForOutdoorAir setting for outdoor-air control behavior on the mixer; this is not a DesignSpecification:OutdoorAir target.'),
        ] = None,
        per_person_ventilation_rate_mode: Annotated[
            str | None,
            Field(description="Optional PerPersonVentilationRateMode, typically 'CurrentOccupancy' or 'DesignOccupancy' for demand-controlled ventilation behavior."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description='Optional Name value; maps to Ironbug IB_AirTerminalSingleDuctInletSideMixer field Name.'),
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
        zone_equipment_child_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ZoneEquipment target or same-model identifier "
                    "to attach as this inlet-side mixer's MixedZoneEquip child. "
                    "Use a detailed_hvac_zone_equipment_* target such as FCU, "
                    "PTAC, PTHP, unit ventilator, VRF terminal, or supported "
                    "unitary equipment; do not pass another air terminal."
                )
            ),
        ] = None,
        thermal_zone_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional IB_ThermalZone target or same-model identifier to "
                    "bind this inlet-side mixer air terminal to after creation; "
                    "this does not create Honeybee Room geometry."
                )
            ),
        ] = None,
        zone_equipment_target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional source child target for the Ironbug component "
                    "Parameter 'ZoneEquipment' on IB_AirTerminalSingleDuctInletSideMixer; "
                    "prefer zone_equipment_child_target for reviewed binding."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing object with the same identifier."),
        ] = False,
    ) -> dict[str, Any]:
        """Create IB_AirTerminalSingleDuctInletSideMixer as a reviewed inlet-side mixer."""

        effective_zone_equipment_target = _coalesce_zone_equipment_target(
            direct_target=zone_equipment_child_target,
            parameter_target=zone_equipment_target,
        )
        source_fields: dict[str, Any] = {}
        source_field_targets: dict[str, Any] = {}
        source_properties: dict[str, Any] = {}
        if name is not None:
            source_fields['Name'] = name
        if control_for_outdoor_air is not None:
            source_fields['ControlForOutdoorAir'] = control_for_outdoor_air
        if per_person_ventilation_rate_mode is not None:
            source_fields['PerPersonVentilationRateMode'] = per_person_ventilation_rate_mode
        created = create_source_backed_ironbug_object(
            garden_root=garden_root,
            ironbug_model_target=ironbug_model_target,
            source_class='IB_AirTerminalSingleDuctInletSideMixer',
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
        latest_model_target = created["updated_model_target"]
        binding_summary: dict[str, Any] = {}
        if effective_zone_equipment_target is not None:
            child = add_ironbug_child(
                garden_root=garden_root,
                ironbug_model_target=latest_model_target,
                parent_target=created["target"],
                child_target=effective_zone_equipment_target,
            )
            latest_model_target = child["updated_model_target"]
            created["target"] = child["target"]
            binding_summary["zone_equipment_child_bound"] = True
            binding_summary["zone_equipment_child_identifier"] = child["summary_view"][
                "child_identifier"
            ]
        else:
            binding_summary["zone_equipment_child_bound"] = False
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
