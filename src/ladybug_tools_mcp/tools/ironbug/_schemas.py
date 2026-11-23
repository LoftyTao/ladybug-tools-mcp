"""Pydantic v2 input/output schemas for the 8 Ironbug DetailedHVAC MCP tools."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def dump_input(value: Any) -> Any:
    """Recursively dump Pydantic models to plain dicts while dropping None fields."""
    if isinstance(value, BaseModel):
        return value.model_dump(exclude_none=True)
    if isinstance(value, (list, tuple)):
        return [dump_input(item) for item in value]
    if isinstance(value, dict):
        return {key: dump_input(item) for key, item in value.items()}
    return value


def dump_target(target: BaseModel | dict[str, Any] | None) -> dict[str, Any] | None:
    """Convert an optional target ref model or dict into a plain dict."""
    if target is None:
        return None
    if isinstance(target, BaseModel):
        return target.model_dump(exclude_none=True)
    return dump_input(target)


class GardenTargetRef(BaseModel):
    """Base typed reference for Garden-managed targets and artifacts."""

    model_config = ConfigDict(extra="allow")

    target_type: str | None = None
    garden_id: str | None = None
    id: str | None = None
    identifier: str | None = None
    domain: str | None = None
    path: str | None = None


class ToolReportModel(BaseModel):
    """Compact tool report returned alongside structured payloads."""

    model_config = ConfigDict(extra="allow")

    status: str = "ok"
    message: str = ""
    warnings: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)

IronbugCategory = Literal[
    "air_loop",
    "air_terminal",
    "availability_manager",
    "coil_cooling",
    "coil_dx",
    "coil_heating",
    "controller",
    "curve",
    "ems",
    "fan",
    "generator_electric",
    "other",
    "plant_equipment",
    "plant_loop",
    "pump",
    "schedule",
    "setpoint_manager",
    "sizing",
    "thermal_zone",
    "vrf",
    "zone_equipment",
]

PlantLoopType = Literal["Cooling", "Heating", "Condenser", "Both"]

ReportingFrequency = Literal[
    "Detailed",
    "Timestep",
    "Hourly",
    "Daily",
    "Monthly",
    "RunPeriod",
    "Annual",
]


class IronbugModelTargetRef(GardenTargetRef):
    """Target pointing to a Garden-managed Ironbug IB_HVACSystem asset."""

    root_type: str | None = Field(default=None, description="C# root class name, typically 'IB_HVACSystem'.")


class BuildingModelTargetRef(GardenTargetRef):
    """Target pointing to a Garden-managed Honeybee or Dragonfly building model."""

    model_identifier: str | None = Field(default=None, description="Building model identifier in the Garden.")


class BuildingObjectTargetRef(GardenTargetRef):
    """Target pointing to a Room, Room2D, Story, or Building object inside a model."""

    model_identifier: str | None = Field(default=None, description="Owning building model identifier.")
    object_type: str | None = Field(default=None, description="Object type such as 'room', 'room2d', 'story', or 'building'.")
    object_identifier: str | None = Field(default=None, description="Identifier of the referenced object.")


class IronbugOutputVariableSpec(BaseModel):
    """EnergyPlus Output:Variable attachment on an Ironbug component."""

    model_config = ConfigDict(extra="forbid")

    variable_name: str = Field(..., min_length=1, description="Exact EnergyPlus output variable name.")
    reporting_frequency: ReportingFrequency = Field(
        default="Hourly",
        description="EnergyPlus reporting frequency (default: 'Hourly').",
    )


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
        description="Exact official Ironbug.HVAC class name from IB_list_components / IB_describe_component.",
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
    tracking_id: str | None = Field(
        default=None,
        description="Optional explicit TrackingID override (defaults to component ID when reused across loops).",
    )


class NamedIronbugComponentSpec(IronbugComponentSpec):
    """List-form component specification carrying its explicit component identifier."""

    id: str = Field(..., min_length=1, description="Unique component identifier referenced by wiring and loops.")


class ThermalZoneConfig(BaseModel):
    """Binding between a Honeybee Room / thermal zone name and Ironbug zone equipment."""

    model_config = ConfigDict(extra="forbid")

    room_name: str = Field(..., min_length=1, description="Exact Honeybee Room identifier represented by this zone.")
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
    supply_plenum: str | None = Field(default=None, description="Optional supply plenum zone/component ID.")
    return_plenum: str | None = Field(default=None, description="Optional return plenum zone/component ID.")


class AirLoopConfig(BaseModel):
    """Configuration for a central OpenStudio AirLoopHVAC."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="AirLoop display/object name.")
    sizing_system: str | None = Field(default=None, description="Optional IB_SizingSystem component ID.")
    supply: list[str] | None = Field(
        default=None,
        description="Ordered list of supply-side component IDs (e.g. OA system, coils, fan, setpoint manager).",
    )
    demand_zones: list[str] | None = Field(
        default=None,
        description="Convenience list of room_name strings (placed on parallel demand branches).",
    )
    demand_branches: list[list[str]] | None = Field(
        default=None,
        description="Explicit demand branches as nested lists of room names or thermal zone IDs.",
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


class VrfSystemConfig(BaseModel):
    """Binding between a VRF outdoor unit and its zone terminals."""

    model_config = ConfigDict(extra="forbid")

    vrf: str = Field(..., min_length=1, description="Component ID of the VRF outdoor unit (e.g. IB_AirConditionerVariableRefrigerantFlow).")
    terminals: list[str] = Field(
        default_factory=list,
        description="List of VRF zone terminal unit component IDs served by this outdoor unit.",
    )


class IronbugToolResult(BaseModel):
    """Shared base output model accommodating blocked runtime diagnostics and extra keys."""

    model_config = ConfigDict(extra="allow")

    blocked: bool = False
    missing: list[str] | None = None
    details: dict[str, Any] | None = None
    report: ToolReportModel | None = None


class IronbugComponentCatalogItem(BaseModel):
    """Summary entry for a single official Ironbug.HVAC class."""

    model_config = ConfigDict(extra="allow")

    type_name: str
    category: str
    base_type: str | None = None
    summary: str = ""


class ListComponentsResult(IronbugToolResult):
    """Output schema for IB_list_components."""

    matches: list[IronbugComponentCatalogItem] = Field(default_factory=list)
    categories: dict[str, int] = Field(default_factory=dict)
    total_catalog_types: int = 0
    total_matched: int = 0
    offset: int = 0
    truncated: bool = False
    expanded_query: str | None = None
    unknown_category: str | None = None
    valid_categories: list[str] | None = None


class ComponentParameterSchema(BaseModel):
    """Constructor or wiring method parameter metadata."""

    model_config = ConfigDict(extra="allow")

    name: str | None = None
    type: str
    required: bool | None = None
    default: Any = None


class ComponentConstructorSchema(BaseModel):
    """Public constructor overload metadata."""

    model_config = ConfigDict(extra="allow")

    parameters: list[ComponentParameterSchema] = Field(default_factory=list)


class ComponentWiringSlotSchema(BaseModel):
    """Public Set*/Add* child wiring method metadata."""

    model_config = ConfigDict(extra="allow")

    method: str
    slot_alias: str
    parameters: list[ComponentParameterSchema] = Field(default_factory=list)


class ComponentFieldSchema(BaseModel):
    """FieldSet / EPDoc field metadata."""

    model_config = ConfigDict(extra="allow")

    name: str
    type: str
    nick_name: str | None = None
    unit: str | None = None
    default: str | None = None
    choices: list[str] | None = None
    description: str | None = None


class DescribedComponentSchema(BaseModel):
    """Full schema inspection payload for one Ironbug.HVAC class."""

    model_config = ConfigDict(extra="allow")

    type_name: str
    instantiable: bool = True
    category: str
    base_type: str | None = None
    summary: str = ""
    constructors: list[ComponentConstructorSchema] = Field(default_factory=list)
    wiring_methods: list[ComponentWiringSlotSchema] = Field(default_factory=list)
    core_fields: list[ComponentFieldSchema] = Field(default_factory=list)
    advanced_field_count: int = 0
    advanced_fields: list[ComponentFieldSchema] | None = None
    concrete_subclasses: list[str] | None = None


class DescribeComponentsResult(IronbugToolResult):
    """Output schema for IB_describe_component."""

    components: list[DescribedComponentSchema] = Field(default_factory=list)
    not_found: list[str] = Field(default_factory=list)


class OpenStudioSummary(BaseModel):
    """Counts of translated OpenStudio HVAC objects produced by SaveHVAC."""

    model_config = ConfigDict(extra="allow")

    thermal_zones: int = 0
    air_loops: int = 0
    plant_loops: int = 0
    vrf_systems: int = 0
    zone_hvac_four_pipe_fan_coils: int = 0
    zone_hvac_ptacs: int = 0
    zone_hvac_pthps: int = 0
    chillers_electric_eir: int = 0
    boilers_hot_water: int = 0
    cooling_towers_variable_speed: int = 0
    coil_cooling_waters: int = 0
    coil_heating_waters: int = 0
    air_terminals_vav_reheat: int = 0
    pumps_constant_speed: int = 0
    pumps_variable_speed: int = 0
    fans_on_off: int = 0
    fans_constant_volume: int = 0
    fans_variable_volume: int = 0


class IronbugSystemSummary(BaseModel):
    """High-level summary of a serialized IB_HVACSystem."""

    model_config = ConfigDict(extra="allow")

    display_name: str | None = None
    ib_version: str | None = None
    thermal_zones: list[str] = Field(default_factory=list)
    air_loop_count: int = 0
    no_air_loop_count: int = 0
    plant_loop_count: int = 0
    vrf_count: int = 0


class ValidationIssueModel(BaseModel):
    """Blocking precondition or compilation issue."""

    model_config = ConfigDict(extra="allow")

    code: str
    message: str
    room_identifier: str | None = None


class RoomPreconditionCheck(BaseModel):
    """Result of checking Honeybee Room or Dragonfly Room2D readiness against an Ironbug system."""

    model_config = ConfigDict(extra="allow")

    checked_rooms: list[str] = Field(default_factory=list)
    ready: bool = False
    issues: list[ValidationIssueModel] = Field(default_factory=list)


class IronbugSystemMutationResult(IronbugToolResult):
    """Output schema for IB_create_system, IB_upsert_components, and IB_configure_loops."""

    target: IronbugModelTargetRef | None = None
    ironbug_model_target: IronbugModelTargetRef | None = None
    summary_view: dict[str, Any] = Field(default_factory=dict)
    persistence_receipt: dict[str, Any] | None = None


class InspectSystemResult(IronbugToolResult):
    """Output schema for IB_inspect_system."""

    target: IronbugModelTargetRef | None = None
    ironbug_model_target: IronbugModelTargetRef | None = None
    summary_view: dict[str, Any] = Field(default_factory=dict)
    draft: dict[str, Any] | None = None


class ValidateSystemResult(IronbugToolResult):
    """Output schema for IB_validate_system."""

    valid: bool = False
    ready: bool = False
    target: IronbugModelTargetRef | None = None
    ironbug_model_target: IronbugModelTargetRef | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocking_issues: list[ValidationIssueModel] = Field(default_factory=list)
    thermal_zones: list[str] = Field(default_factory=list)
    openstudio_summary: OpenStudioSummary = Field(default_factory=OpenStudioSummary)
    system_summary: IronbugSystemSummary = Field(default_factory=IronbugSystemSummary)
    room_check: RoomPreconditionCheck | None = None
    summary_view: dict[str, Any] = Field(default_factory=dict)


class ApplyToModelResult(IronbugToolResult):
    """Output schema for IB_apply_to_model."""

    target: BuildingModelTargetRef | None = None
    updated_model_target: BuildingModelTargetRef | None = None
    updated_model_targets: list[BuildingModelTargetRef] = Field(default_factory=list)
    honeybee_model_target: BuildingModelTargetRef | None = None
    dragonfly_model_target: BuildingModelTargetRef | None = None
    ironbug_model_target: IronbugModelTargetRef | None = None
    detailed_hvac_identifier: str | None = None
    summary_view: dict[str, Any] = Field(default_factory=dict)
    persistence_receipt: dict[str, Any] | None = None


def dump_models(items: list[Any] | None) -> list[dict[str, Any]] | None:
    """Convert a list of Pydantic config models to plain dicts for the service layer."""
    if items is None:
        return None
    return [
        item.model_dump(exclude_none=True) if isinstance(item, BaseModel) else dict(item)
        for item in items
    ]


def dump_components(
    components: dict[str, IronbugComponentSpec] | list[NamedIronbugComponentSpec] | None,
) -> dict[str, dict[str, Any]] | list[dict[str, Any]] | None:
    """Convert typed component specs to plain dict/list payloads for the service layer."""
    if components is None:
        return None
    if isinstance(components, dict):
        return {
            comp_id: (spec.model_dump(exclude_none=True) if isinstance(spec, BaseModel) else dict(spec))
            for comp_id, spec in components.items()
        }
    return [
        spec.model_dump(exclude_none=True) if isinstance(spec, BaseModel) else dict(spec)
        for spec in components
    ]


__all__ = [
    "AirLoopConfig",
    "ApplyToModelResult",
    "BuildingModelTargetRef",
    "BuildingObjectTargetRef",
    "ComponentConstructorSchema",
    "ComponentFieldSchema",
    "ComponentParameterSchema",
    "ComponentWiringSlotSchema",
    "DescribeComponentsResult",
    "DescribedComponentSchema",
    "GardenTargetRef",
    "InspectSystemResult",
    "IronbugCategory",
    "IronbugComponentCatalogItem",
    "IronbugComponentSpec",
    "IronbugModelTargetRef",
    "IronbugOutputVariableSpec",
    "IronbugSystemMutationResult",
    "IronbugSystemSpecDict",
    "IronbugSystemSummary",
    "IronbugToolResult",
    "ListComponentsResult",
    "NamedIronbugComponentSpec",
    "OpenStudioSummary",
    "PlantLoopConfig",
    "PlantLoopType",
    "ReportingFrequency",
    "RoomPreconditionCheck",
    "ThermalZoneConfig",
    "ToolReportModel",
    "ValidateSystemResult",
    "ValidationIssueModel",
    "VrfSystemConfig",
    "dump_components",
    "dump_models",
    "dump_target",
]
