"""Pydantic validation schemas for Ironbug HVAC authoring and system drafts."""

from __future__ import annotations

from collections.abc import Iterable
import json
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

PlantLoopType = Literal["Cooling", "Heating", "Condenser", "Both"]

IronbugTemplateName = Literal[
    "vav_chiller_boiler",
    "doas_fcu",
    "vrf_doas",
    "wshp",
]

ReportingFrequency = Literal[
    "Detailed",
    "Timestep",
    "Hourly",
    "Daily",
    "Monthly",
    "RunPeriod",
    "Annual",
]


def _require_non_empty_str(value: str, *, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} is required and must not be empty.")
    return value


def _coerce_mapping(value: Any, *, error_message: str) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(exclude_unset=True)
    if isinstance(value, dict):
        return dict(value)
    raise ValueError(error_message)


def _format_loc(loc: tuple[Any, ...]) -> str:
    return ".".join(str(part) for part in loc) if loc else "input"


def _format_validation_error(
    exc: ValidationError,
    *,
    prefix: str,
    accepted_fields: Iterable[str] | None = None,
) -> ValueError:
    unsupported: list[str] = []
    missing: list[str] = []
    invalid: list[str] = []
    for err in exc.errors():
        err_type = err.get("type", "")
        loc = err.get("loc", ())
        field_name = _format_loc(loc)
        if err_type == "extra_forbidden":
            unsupported.append(field_name)
        elif err_type == "missing":
            missing.append(field_name)
        else:
            msg = err.get("msg", "invalid value")
            invalid.append(f"{field_name} ({msg})" if loc else msg)

    parts: list[str] = []
    if unsupported:
        parts.append(f"unsupported field(s): {', '.join(sorted(set(unsupported)))}")
    if missing:
        parts.append(f"missing required field(s): {', '.join(missing)}")
    if invalid:
        parts.append(f"invalid field(s): {'; '.join(invalid)}")
    detail = "; ".join(parts) if parts else str(exc)
    if accepted_fields is not None and (unsupported or missing):
        accepted = ", ".join(sorted(accepted_fields))
        return ValueError(f"{prefix}: {detail}. Accepted fields: {accepted}.")
    return ValueError(f"{prefix}: {detail}.")


class IronbugOutputVariableSpec(BaseModel):
    """EnergyPlus Output:Variable attachment on an Ironbug component."""

    model_config = ConfigDict(extra="forbid")

    variable_name: str = Field(
        ...,
        min_length=1,
        description="Exact EnergyPlus output variable name.",
    )
    reporting_frequency: ReportingFrequency = Field(
        default="Hourly",
        description="EnergyPlus reporting frequency (default: 'Hourly').",
    )

    @field_validator("variable_name")
    @classmethod
    def _validate_variable_name(cls, value: str) -> str:
        return _require_non_empty_str(value, field_name="variable_name")


class _NonEmptyEmsInlineSpec(BaseModel):
    """Shared base for inline EMS attachment specs disallowing empty {} payloads."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _reject_empty_spec(self) -> _NonEmptyEmsInlineSpec:
        if all(getattr(self, field_name) is None for field_name in type(self).model_fields):
            raise ValueError(
                f"{type(self).__name__} cannot be empty; provide at least one field."
            )
        return self


class IronbugEmsSensorSpec(_NonEmptyEmsInlineSpec):
    """Component-level EMS Sensor attachment (AddEMSSensors)."""

    name: str | None = Field(default=None, description="Optional EMS sensor variable name.")
    key_name: str | None = Field(
        default=None,
        description="EnergyPlus KeyName (e.g. '*', zone, or component key).",
    )
    output_variable: str | None = Field(
        default=None,
        description="EnergyPlus Output:Variable or meter name.",
    )
    output_variable_or_meter_name: str | None = Field(
        default=None,
        description="Alias for output_variable matching IB_EnergyManagementSystemSensor FieldSet.",
    )
    fields: dict[str, Any] | None = Field(
        default=None,
        description="Optional additional IB_EnergyManagementSystemSensor fields.",
    )
    tracking_id: str | None = Field(default=None, description="Optional TrackingID override.")


class IronbugEmsInternalVariableSpec(_NonEmptyEmsInlineSpec):
    """Component-level EMS InternalVariable attachment (AddEMSInternalVariables)."""

    name: str | None = Field(default=None, description="Optional EMS internal variable name.")
    internal_data_type: str | None = Field(
        default=None,
        description="EnergyPlus internal variable data type.",
    )
    data_type: str | None = Field(
        default=None,
        description="Alias for internal_data_type.",
    )
    host_obj: str | None = Field(default=None, description="Optional host component ID.")
    fields: dict[str, Any] | None = Field(
        default=None,
        description="Optional additional IB_EnergyManagementSystemInternalVariable fields.",
    )
    tracking_id: str | None = Field(default=None, description="Optional TrackingID override.")


class IronbugEmsActuatorSpec(_NonEmptyEmsInlineSpec):
    """Component-level EMS Actuator attachment (AddEMSActuators)."""

    name: str | None = Field(default=None, description="Optional EMS actuator variable name.")
    actuated_component_type: str | None = Field(
        default=None,
        description="EnergyPlus actuated component type.",
    )
    component_type: str | None = Field(
        default=None,
        description="Alias for actuated_component_type.",
    )
    actuated_component_control_type: str | None = Field(
        default=None,
        description="EnergyPlus actuated control type.",
    )
    control_type: str | None = Field(
        default=None,
        description="Alias for actuated_component_control_type.",
    )
    actuated_obj: str | None = Field(
        default=None,
        description="Optional actuated component ID or object name.",
    )
    fields: dict[str, Any] | None = Field(
        default=None,
        description="Optional additional IB_EnergyManagementSystemActuator fields.",
    )
    tracking_id: str | None = Field(default=None, description="Optional TrackingID override.")


class IronbugSystemSpecDict(BaseModel):
    """Official Ironbug IB_HVACSystem JSON specification dictionary."""

    model_config = ConfigDict(extra="allow")

    DisplayName: str | None = Field(
        default=None,
        description="Optional HVAC system display name.",
    )
    TrackingID: str | None = Field(
        default=None,
        description="Optional Ironbug root TrackingID.",
    )


class IronbugComponentSpec(BaseModel):
    """Declarative specification for one official C# Ironbug.HVAC component instance."""

    model_config = ConfigDict(extra="forbid")

    type: str = Field(
        ...,
        min_length=1,
        description="Exact official Ironbug.HVAC class name from IB_List_Components / IB_Describe_Component.",
    )
    ctor_args: list[Any] | dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional constructor args (positional list or named dict); pass child "
            "components as string IDs."
        ),
    )
    fields: dict[str, Any] | None = Field(
        default=None,
        description="Optional EnergyPlus FieldSet field values keyed by exact field name or nick_name.",
    )
    wiring: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional child wiring keyed by slot_alias or Set*/Add* method; values "
            "are component ID(s)."
        ),
    )
    output_variables: list[str | IronbugOutputVariableSpec] | None = Field(
        default=None,
        description="Optional EnergyPlus Output:Variable names or {variable_name, reporting_frequency} objects.",
    )
    ems_sensors: list[str | IronbugEmsSensorSpec] | None = Field(
        default=None,
        description="Optional component-level EMS sensor IDs or inline specs (AddEMSSensors).",
    )
    ems_internal_variables: list[str | IronbugEmsInternalVariableSpec] | None = Field(
        default=None,
        description="Optional component-level EMS internal variable IDs or inline specs (AddEMSInternalVariables).",
    )
    ems_actuators: list[str | IronbugEmsActuatorSpec] | None = Field(
        default=None,
        description="Optional component-level EMS actuator IDs or inline specs (AddEMSActuators).",
    )
    children: list[str] | None = Field(
        default=None,
        description="Optional explicit ordered IB_Children component IDs (used when reverse-parsing complex imported specs).",
    )
    ib_properties: dict[str, Any] | None = Field(
        default=None,
        description="Optional explicit IBProperties dictionary entries.",
    )
    tracking_id: str | None = Field(
        default=None,
        description="Optional explicit TrackingID override (defaults to component ID when reused across loops).",
    )

    @field_validator("type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        return _require_non_empty_str(value, field_name="type")


class NamedIronbugComponentSpec(IronbugComponentSpec):
    """List-form component specification carrying its explicit component identifier."""

    id: str = Field(
        ...,
        min_length=1,
        description="Unique component identifier referenced by wiring and loops.",
    )

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return _require_non_empty_str(value, field_name="id")


class ThermalZoneConfig(BaseModel):
    """Binding between a Honeybee Room / thermal zone name and Ironbug zone equipment."""

    model_config = ConfigDict(extra="forbid")

    room_name: str = Field(
        ...,
        min_length=1,
        description="Exact Honeybee Room identifier represented by this zone.",
    )
    air_terminal: str | None = Field(
        default=None,
        description="Component ID of the zone air terminal (required when served by an AirLoop).",
    )
    zone_equipments: list[str] | None = Field(
        default=None,
        description="List of zone equipment component IDs (e.g. PTAC, FCU, VRF terminal, radiant unit).",
    )
    sizing_zone: str | None = Field(default=None, description="Optional IB_SizingZone component ID.")
    allow_multi_air_loops: bool | None = Field(
        default=None,
        description="Allow connecting this thermal zone to multiple AirLoops.",
    )
    is_air_terminal_before_zone_equipments: bool | None = Field(
        default=None,
        description="Order air terminal ahead of zone equipment in ZoneHVACEquipmentList.",
    )
    supply_plenum: str | None = Field(default=None, description="Optional supply plenum zone/component ID.")
    return_plenum: str | None = Field(default=None, description="Optional return plenum zone/component ID.")
    fields: dict[str, Any] | None = Field(
        default=None,
        description="Optional IB_ThermalZone FieldSet properties (e.g. Multiplier, LoadDistributionScheme).",
    )
    wiring: dict[str, Any] | None = Field(
        default=None,
        description="Optional IB_ThermalZone wiring method overrides.",
    )
    output_variables: list[str | IronbugOutputVariableSpec] | None = Field(
        default=None,
        description="Optional zone Output:Variable attachments.",
    )
    ems_sensors: list[str | IronbugEmsSensorSpec] | None = Field(
        default=None,
        description="Optional zone-level EMS sensors.",
    )
    ems_internal_variables: list[str | IronbugEmsInternalVariableSpec] | None = Field(
        default=None,
        description="Optional zone-level EMS internal variables.",
    )
    ems_actuators: list[str | IronbugEmsActuatorSpec] | None = Field(
        default=None,
        description="Optional zone-level EMS actuators.",
    )
    equipment_list_priorities: dict[str, int | dict[str, int]] | list[str | dict[str, Any]] | None = Field(
        default=None,
        description=(
            "Optional cooling/heating priority mapping by component ID "
            "(e.g. {'fcu': {'cooling_priority': 1, 'heating_priority': 2}}) or ordered component list."
        ),
    )

    @field_validator("room_name")
    @classmethod
    def _validate_room_name(cls, value: str) -> str:
        return _require_non_empty_str(value, field_name="room_name")


class AirLoopConfig(BaseModel):
    """Configuration for a central OpenStudio AirLoopHVAC."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="AirLoop display/object name.")
    sizing_system: str | None = Field(default=None, description="Optional IB_SizingSystem component ID.")
    availability_managers: list[str | IronbugComponentSpec] | None = Field(
        default=None,
        description="Optional IB_AvailabilityManager component IDs or inline specs.",
    )
    fields: dict[str, Any] | None = Field(
        default=None,
        description="Optional IB_AirLoopHVAC FieldSet properties (e.g. NightCycleControlType, DesignSupplyAirFlowRate).",
    )
    wiring: dict[str, Any] | None = Field(
        default=None,
        description="Optional IB_AirLoopHVAC wiring method overrides.",
    )
    supply: list[str] | None = Field(
        default=None,
        description="Ordered list of supply-side component IDs (e.g. OA system, coils, fan, setpoint manager).",
    )
    supply_branches: list[list[str]] | None = Field(
        default=None,
        description="Optional grouped supply component branch lists added sequentially to the air loop supply side.",
    )
    return_path: str | list[str] | dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional return-path configuration: return plenum room name, return-fan/component IDs, "
            "or {return_plenum, return_fan, components, relief_stream_objs}."
        ),
    )
    demand_zones: list[str] | None = Field(
        default=None,
        description="Convenience list of room_name strings (placed on parallel demand branches).",
    )
    demand_branches: list[list[str]] | None = Field(
        default=None,
        description="Explicit demand branches as nested lists of room names or thermal zone IDs.",
    )
    output_variables: list[str | IronbugOutputVariableSpec] | None = Field(
        default=None,
        description="Optional air loop Output:Variable attachments.",
    )
    ems_sensors: list[str | IronbugEmsSensorSpec] | None = Field(
        default=None,
        description="Optional air loop EMS sensors.",
    )
    ems_internal_variables: list[str | IronbugEmsInternalVariableSpec] | None = Field(
        default=None,
        description="Optional air loop EMS internal variables.",
    )
    ems_actuators: list[str | IronbugEmsActuatorSpec] | None = Field(
        default=None,
        description="Optional air loop EMS actuators.",
    )


class PlantLoopConfig(BaseModel):
    """Configuration for an OpenStudio hydronic PlantLoop."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="PlantLoop display/object name.")
    loop_type: PlantLoopType | None = Field(
        default=None,
        description="Hydronic loop sizing type: 'Cooling', 'Heating', 'Condenser', or 'Both'.",
    )
    design_loop_exit_temperature: float | None = Field(
        default=None,
        description="Design loop exit temperature in degrees Celsius.",
    )
    loop_design_temperature_difference: float | None = Field(
        default=None,
        gt=0,
        description="Design loop temperature difference (delta-T) in Kelvin (> 0).",
    )
    sizing_plant: str | None = Field(default=None, description="Optional explicit IB_SizingPlant component ID.")
    operation_scheme: str | None = Field(default=None, description="Optional PlantEquipmentOperation scheme component ID.")
    availability_managers: list[str | IronbugComponentSpec] | None = Field(
        default=None,
        description="Optional IB_AvailabilityManager component IDs or inline specs.",
    )
    fields: dict[str, Any] | None = Field(
        default=None,
        description="Optional IB_PlantLoop FieldSet properties (e.g. FluidType, CommonPipeSimulation, LoadDistributionScheme).",
    )
    wiring: dict[str, Any] | None = Field(
        default=None,
        description="Optional IB_PlantLoop wiring method overrides.",
    )
    supply: list[str | list[list[str]]] | None = Field(
        default=None,
        description="Ordered supply-side component IDs (e.g. pump before supply_branches, setpoint manager after).",
    )
    supply_branches: list[list[str]] | None = Field(
        default=None,
        description="Parallel supply branches as nested lists, e.g. [['chiller']] or [['boiler1'], ['boiler2']].",
    )
    supply_setpoint: float | None = Field(
        default=None,
        description="Constant loop outlet setpoint temperature in degrees Celsius (creates IB_SetpointManagerScheduled).",
    )
    supply_setpoint_manager: str | None = Field(
        default=None,
        description="Optional explicit SetpointManager component ID placed at loop outlet.",
    )
    demand: list[str | list[list[str]]] | None = Field(
        default=None,
        description="Ordered demand-side component IDs or nested parallel branch groups.",
    )
    demand_branches: list[list[str]] | None = Field(
        default=None,
        description="Parallel demand branches as nested lists, e.g. [['cool_coil']] or [['coil_1'], ['coil_2']].",
    )
    bypass_pipes: bool | str | list[str] | dict[str, bool | str | None] | None = Field(
        default=None,
        description=(
            "Optional bypass pipe configuration (IB_PipeAdiabatic parallel branch): "
            "true/'both'/'supply'/'demand', component ID(s), or {'supply': true|id|null, 'demand': true|id|null}."
        ),
    )
    output_variables: list[str | IronbugOutputVariableSpec] | None = Field(
        default=None,
        description="Optional plant loop Output:Variable attachments.",
    )
    ems_sensors: list[str | IronbugEmsSensorSpec] | None = Field(
        default=None,
        description="Optional plant loop EMS sensors.",
    )
    ems_internal_variables: list[str | IronbugEmsInternalVariableSpec] | None = Field(
        default=None,
        description="Optional plant loop EMS internal variables.",
    )
    ems_actuators: list[str | IronbugEmsActuatorSpec] | None = Field(
        default=None,
        description="Optional plant loop EMS actuators.",
    )


class VrfSystemConfig(BaseModel):
    """Binding between a VRF outdoor unit and its zone terminals."""

    model_config = ConfigDict(extra="forbid")

    vrf: str = Field(
        ...,
        min_length=1,
        description="Component ID of the VRF outdoor unit (e.g. IB_AirConditionerVariableRefrigerantFlow).",
    )
    terminals: list[str] = Field(
        default_factory=list,
        description="List of VRF zone terminal unit component IDs served by this outdoor unit.",
    )

    @field_validator("vrf")
    @classmethod
    def _validate_vrf(cls, value: str) -> str:
        return _require_non_empty_str(value, field_name="vrf")


def validate_ironbug_components(components: Any) -> dict[str, dict[str, Any]]:
    """Validate and normalize Ironbug component definitions into id -> spec dicts."""
    if components is None:
        return {}
    if isinstance(components, dict):
        normalized: dict[str, dict[str, Any]] = {}
        for comp_id, raw_spec in components.items():
            if not isinstance(comp_id, str) or not comp_id.strip():
                raise ValueError("Component id must be a non-empty string.")
            key = comp_id.strip()
            spec_dict = _coerce_mapping(
                raw_spec,
                error_message=f"Component '{key}' specification must be a dictionary.",
            )
            try:
                validated = IronbugComponentSpec.model_validate(spec_dict)
            except ValidationError as exc:
                raise _format_validation_error(
                    exc,
                    prefix=f"Invalid Ironbug component '{key}'",
                    accepted_fields=IronbugComponentSpec.model_fields,
                ) from exc
            normalized[key] = validated.model_dump(exclude_none=True)
        return normalized
    if isinstance(components, list):
        normalized = {}
        for index, raw_item in enumerate(components):
            item_dict = _coerce_mapping(
                raw_item,
                error_message=f"components[{index}] must be a dictionary with 'id' and 'type'.",
            )
            try:
                validated = NamedIronbugComponentSpec.model_validate(item_dict)
            except ValidationError as exc:
                raise _format_validation_error(
                    exc,
                    prefix=f"Invalid Ironbug components[{index}]",
                    accepted_fields=NamedIronbugComponentSpec.model_fields,
                ) from exc
            dumped = validated.model_dump(exclude_none=True)
            key = str(dumped.pop("id")).strip()
            normalized[key] = dumped
        return normalized
    raise ValueError("components must be a dict mapping id -> spec, or a list of dicts with 'id'.")


def _validate_config_list(
    items: Any,
    *,
    model_cls: type[BaseModel],
    context: str,
) -> list[dict[str, Any]] | None:
    if items is None:
        return None
    if not isinstance(items, list):
        raise ValueError(f"{context} must be a list of dictionaries.")
    validated_items: list[dict[str, Any]] = []
    for index, raw_item in enumerate(items):
        item_dict = _coerce_mapping(
            raw_item,
            error_message=f"{context}[{index}] must be a dictionary.",
        )
        try:
            validated = model_cls.model_validate(item_dict)
        except ValidationError as exc:
            raise _format_validation_error(
                exc,
                prefix=f"Invalid {context}[{index}]",
                accepted_fields=model_cls.model_fields,
            ) from exc
        validated_items.append(validated.model_dump(exclude_none=True))
    return validated_items


def validate_thermal_zones(items: Any) -> list[dict[str, Any]] | None:
    """Validate thermal_zones configuration dictionaries."""
    return _validate_config_list(items, model_cls=ThermalZoneConfig, context="thermal_zones")


def validate_air_loops(items: Any) -> list[dict[str, Any]] | None:
    """Validate air_loops configuration dictionaries."""
    return _validate_config_list(items, model_cls=AirLoopConfig, context="air_loops")


def validate_plant_loops(items: Any) -> list[dict[str, Any]] | None:
    """Validate plant_loops configuration dictionaries."""
    return _validate_config_list(items, model_cls=PlantLoopConfig, context="plant_loops")


def validate_vrf_systems(items: Any) -> list[dict[str, Any]] | None:
    """Validate vrf_systems configuration dictionaries."""
    return _validate_config_list(items, model_cls=VrfSystemConfig, context="vrf_systems")


def validate_ironbug_specification(specification: Any) -> dict[str, Any] | str | None:
    """Validate an official Ironbug IB_HVACSystem specification dict or JSON string."""
    if specification is None:
        return None
    if isinstance(specification, str):
        if not specification.strip():
            raise ValueError("specification JSON string must not be empty.")
        try:
            parsed = json.loads(specification)
        except json.JSONDecodeError as exc:
            raise ValueError(f"specification must be valid JSON: {exc.msg}.") from exc
        if not isinstance(parsed, dict):
            raise ValueError("specification JSON string must decode to an object dictionary.")
        try:
            IronbugSystemSpecDict.model_validate(parsed)
        except ValidationError as exc:
            raise _format_validation_error(
                exc,
                prefix="Invalid Ironbug specification",
                accepted_fields=IronbugSystemSpecDict.model_fields,
            ) from exc
        return specification

    raw_spec = _coerce_mapping(
        specification,
        error_message="specification must be a dictionary or JSON string.",
    )
    try:
        validated = IronbugSystemSpecDict.model_validate(raw_spec)
    except ValidationError as exc:
        raise _format_validation_error(
            exc,
            prefix="Invalid Ironbug specification",
            accepted_fields=IronbugSystemSpecDict.model_fields,
        ) from exc
    return validated.model_dump(exclude_unset=True)


__all__ = [
    "AirLoopConfig",
    "IronbugComponentSpec",
    "IronbugEmsActuatorSpec",
    "IronbugEmsInternalVariableSpec",
    "IronbugEmsSensorSpec",
    "IronbugOutputVariableSpec",
    "IronbugSystemSpecDict",
    "IronbugTemplateName",
    "NamedIronbugComponentSpec",
    "PlantLoopConfig",
    "PlantLoopType",
    "ReportingFrequency",
    "ThermalZoneConfig",
    "VrfSystemConfig",
    "validate_air_loops",
    "validate_ironbug_components",
    "validate_ironbug_specification",
    "validate_plant_loops",
    "validate_thermal_zones",
    "validate_vrf_systems",
]
