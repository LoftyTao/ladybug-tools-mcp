"""ironbug MCP tools."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from ladybug_tools_mcp.contracts import (
    BuildingModelTargetRef,
    BuildingObjectTargetRef,
    IronbugModelTargetRef,
    MappingReadMixin,
    MutationResultModel,
    PersistenceReceiptModel,
    ToolResultModel,
    ValidationResultModel,
    dump_models,
    dump_target,
    validate_output,
)

IronbugTemplateName = Literal[
    "vav_chiller_boiler",
    "doas_fcu",
    "vrf_doas",
    "wshp",
]


class IronbugToolResult(ToolResultModel):
    """Shared base output model accommodating blocked runtime diagnostics and extra keys."""

    blocked: bool | None = None
    missing: list[str] | None = None
    details: dict[str, Any] | None = None


class IronbugComponentCatalogItem(MappingReadMixin, BaseModel):
    """Summary entry for a single official Ironbug.HVAC class."""

    model_config = ConfigDict(extra="allow")

    type_name: str
    category: str
    base_type: str | None = None
    summary: str = ""


class ListComponentsResult(IronbugToolResult):
    """Output schema for IB_List_Components."""

    matches: list[IronbugComponentCatalogItem] | None = None
    categories: dict[str, int] | None = None
    total_catalog_types: int | None = None
    total_matched: int | None = None
    offset: int | None = None
    truncated: bool | None = None
    expanded_query: str | None = None
    unknown_category: str | None = None
    valid_categories: list[str] | None = None


class DescribedComponentSchema(MappingReadMixin, BaseModel):
    """Full schema inspection payload for one Ironbug.HVAC class."""

    model_config = ConfigDict(extra="allow")

    type_name: str
    instantiable: bool = True
    category: str
    base_type: str | None = None
    summary: str = ""
    constructors: list[dict[str, Any]] = Field(default_factory=list)
    wiring_methods: list[dict[str, Any]] = Field(default_factory=list)
    core_fields: list[dict[str, Any]] = Field(default_factory=list)
    advanced_field_count: int = 0
    advanced_fields: list[dict[str, Any]] | None = None
    concrete_subclasses: list[str] | None = None


class DescribeComponentsResult(IronbugToolResult):
    """Output schema for IB_Describe_Component."""

    components: list[DescribedComponentSchema] | None = None
    not_found: list[str] | None = None


class IronbugSystemSummary(MappingReadMixin, BaseModel):
    """High-level summary of a serialized IB_HVACSystem."""

    model_config = ConfigDict(extra="allow")

    display_name: str | None = None
    ib_version: str | None = None
    thermal_zones: list[str] = Field(default_factory=list)
    air_loop_count: int = 0
    no_air_loop_count: int = 0
    plant_loop_count: int = 0
    vrf_count: int = 0


class ValidationIssueModel(MappingReadMixin, BaseModel):
    """Blocking precondition or compilation issue."""

    model_config = ConfigDict(extra="allow")

    code: str
    message: str
    room_identifier: str | None = None


class RoomPreconditionCheck(MappingReadMixin, BaseModel):
    """Result of checking Honeybee Room or Dragonfly Room2D readiness against an Ironbug system."""

    model_config = ConfigDict(extra="allow")

    checked_rooms: list[str] = Field(default_factory=list)
    ready: bool = False
    issues: list[ValidationIssueModel] = Field(default_factory=list)


class ForwardTranslatorSummary(MappingReadMixin, BaseModel):
    """Summary of OpenStudio EnergyPlusForwardTranslator dry-run diagnostics."""

    model_config = ConfigDict(extra="allow")

    ran: bool | None = None
    error_count: int | None = None
    warning_count: int | None = None
    errors: list[str] | None = None
    warnings: list[str] | None = None
    reason: str | None = None


class IronbugSystemMutationResult(MutationResultModel):
    """Output schema for IB_Create_System, IB_Upsert_Components, and IB_Configure_Loops."""

    target: IronbugModelTargetRef | None = None
    ironbug_model_target: IronbugModelTargetRef | None = None
    persistence_receipt: PersistenceReceiptModel | None = None
    blocked: bool | None = None
    missing: list[str] | None = None
    details: dict[str, Any] | None = None


class InspectSystemResult(IronbugToolResult):
    """Output schema for IB_Inspect_System."""

    target: IronbugModelTargetRef | None = None
    ironbug_model_target: IronbugModelTargetRef | None = None
    draft: dict[str, Any] | None = None


class ValidateSystemResult(ValidationResultModel):
    """Output schema for IB_Validate_System."""

    valid: bool | None = None
    ready: bool | None = None
    target: IronbugModelTargetRef | None = None
    ironbug_model_target: IronbugModelTargetRef | None = None
    errors: list[str] | None = None
    warnings: list[str] | None = None
    blocking_issues: list[ValidationIssueModel] | None = None
    thermal_zones: list[str] | None = None
    openstudio_summary: dict[str, int] | None = None
    system_summary: IronbugSystemSummary | None = None
    room_check: RoomPreconditionCheck | None = None
    forward_translator: ForwardTranslatorSummary | None = None
    blocked: bool | None = None
    missing: list[str] | None = None
    details: dict[str, Any] | None = None


class ApplyToModelResult(MutationResultModel):
    """Output schema for IB_Apply_To_Model."""

    target: BuildingModelTargetRef | None = None
    updated_model_target: BuildingModelTargetRef | None = None
    updated_model_targets: list[BuildingModelTargetRef] | None = None
    honeybee_model_target: BuildingModelTargetRef | None = None
    dragonfly_model_target: BuildingModelTargetRef | None = None
    ironbug_model_target: IronbugModelTargetRef | None = None
    detailed_hvac_identifier: str | None = None
    persistence_receipt: PersistenceReceiptModel | None = None
    blocked: bool | None = None
    missing: list[str] | None = None
    details: dict[str, Any] | None = None


def register(mcp: FastMCP) -> None:
    """Register ironbug tools."""

    @mcp.tool(
        name="IB_Apply_To_Model",
        description=(
            "Attach a validated official Ironbug IB_HVACSystem as DetailedHVAC on selected "
            "Honeybee Rooms (or Dragonfly Room2D/Story/Building hosts) and persist the updated model. "
            "For Honeybee, omitting room selectors automatically binds to rooms matching the "
            "system's thermal_zones."
        ),
        tags={"ironbug", "detailed-hvac", "hvac", "energy", "apply", "edit"},
        annotations={"read_only_hint": False, "destructive_hint": False},
        timeout=60,
    )
    def ib_apply_to_model(
        garden_root: Annotated[
            str,
            Field(min_length=1, description="Required Garden root path containing garden.json."),
        ],
        ironbug_model_target: Annotated[
            IronbugModelTargetRef | None,
            Field(description="Target returned by IB_Create_System. Optional when only one Ironbug system exists."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional Ironbug system identifier when ironbug_model_target is omitted."),
        ] = None,
        model_family: Annotated[
            Literal["honeybee", "dragonfly"],
            Field(description="Target building model family: 'honeybee' (default) or 'dragonfly'."),
        ] = "honeybee",
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Optional Honeybee or Dragonfly model target; defaults to the Garden base model."),
        ] = None,
        room_targets: Annotated[
            list[BuildingObjectTargetRef] | None,
            Field(description="Optional Honeybee Room targets from HB_Search_Model_Objects."),
        ] = None,
        room_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional Honeybee Room identifiers to assign this DetailedHVAC to."),
        ] = None,
        apply_to_all_rooms: Annotated[
            bool,
            Field(description="Assign this DetailedHVAC to all Rooms in the target Honeybee model."),
        ] = False,
        host_target: Annotated[
            BuildingObjectTargetRef | None,
            Field(description="Optional Dragonfly Room2D, Story, or Building target when model_family='dragonfly'."),
        ] = None,
        conditioned_only: Annotated[
            bool,
            Field(description="For Dragonfly Story/Building hosts, apply only to conditioned Room2Ds."),
        ] = True,
        detailed_hvac_identifier: Annotated[
            str | None,
            Field(description="Optional DetailedHVAC identifier stored in the model."),
        ] = None,
    ) -> ApplyToModelResult:
        """Apply an Ironbug DetailedHVAC system to a Honeybee or Dragonfly model."""
        from garden.ironbug.service import apply_ironbug_to_model

        return validate_output(
            ApplyToModelResult,
            apply_ironbug_to_model(
                garden_root=garden_root,
                ironbug_model_target=dump_target(ironbug_model_target),
                identifier=identifier,
                model_family=model_family,
                model_target=dump_target(model_target),
                room_targets=dump_models(room_targets),
                room_identifiers=room_identifiers,
                apply_to_all_rooms=apply_to_all_rooms,
                host_target=dump_target(host_target),
                conditioned_only=conditioned_only,
                detailed_hvac_identifier=detailed_hvac_identifier,
            ),
        )

    @mcp.tool(
        name="IB_Configure_Loops",
        description=(
            "Wire Ironbug components into thermal_zones, air_loops, plant_loops, "
            "vrf_systems, energy_management_system, and electric_load_center, then serialize "
            "the IB_HVACSystem. Zones omitted from air_loops use IB_NoAirLoop; parallel "
            "plant branches use nested lists such as [['coil1'], ['coil2']]."
        ),
        tags={"ironbug", "detailed-hvac", "hvac", "author", "edit"},
        annotations={"read_only_hint": False, "destructive_hint": False},
        timeout=30,
    )
    def ib_configure_loops(
        garden_root: Annotated[
            str,
            Field(min_length=1, description="Required Garden root path containing garden.json."),
        ],
        ironbug_model_target: Annotated[
            IronbugModelTargetRef | None,
            Field(description="Target returned by IB_Create_System. Optional when only one Ironbug system exists."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional Ironbug system identifier when ironbug_model_target is omitted."),
        ] = None,
        thermal_zones: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Optional list of thermal zone config dicts. Supported keys: room_name (required), "
                    "air_terminal (str ID), zone_equipments (list[str] IDs), sizing_zone (str ID), "
                    "allow_multi_air_loops (bool), is_air_terminal_before_zone_equipments (bool), "
                    "supply_plenum (str), return_plenum (str), fields (dict), wiring (dict), "
                    "output_variables (list[str | {variable_name, reporting_frequency}]), "
                    "ems_sensors / ems_internal_variables / ems_actuators (list[str | dict]), "
                    "equipment_list_priorities (dict e.g. {'fcu': {'cooling_priority': 1, 'heating_priority': 2}} or ordered list). "
                    "Example: [{'room_name': 'Room1', 'air_terminal': 'vav1', 'zone_equipments': ['fcu1']}]."
                )
            ),
        ] = None,
        air_loops: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Optional list of AirLoopHVAC config dicts. Supported keys: name (str), "
                    "sizing_system (str ID), availability_managers (list[str | component dict]), "
                    "fields (dict), wiring (dict), supply (ordered list[str] IDs), "
                    "supply_branches (list[list[str]]), return_path (plenum room, ID list, or "
                    "{return_plenum, return_fan, components, relief_stream_objs}), "
                    "demand_zones (list[str] room names), demand_branches (list[list[str]]), "
                    "output_variables, ems_sensors, ems_internal_variables, ems_actuators. "
                    "Example: [{'name': 'VAV_AHU', 'supply': ['oa_sys', 'cc', 'hc', 'fan', 'spm'], 'demand_zones': ['Room1']}]."
                )
            ),
        ] = None,
        plant_loops: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Optional list of PlantLoop config dicts. Supported keys: name (str), "
                    "loop_type ('Cooling' | 'Heating' | 'Condenser' | 'Both'), "
                    "design_loop_exit_temperature (float C), loop_design_temperature_difference (float > 0 K), "
                    "sizing_plant (str ID), operation_scheme (str ID), "
                    "availability_managers (list[str | component dict]), fields (dict), wiring (dict), "
                    "supply (list[str | list[list[str]]]), supply_branches (nested parallel branches e.g. [['chiller']] or [['boiler1'], ['boiler2']]), "
                    "supply_setpoint (float C), supply_setpoint_manager (str ID), "
                    "demand (list[str | list[list[str]]]), demand_branches (nested parallel branches e.g. [['coil1'], ['coil2']]), "
                    "bypass_pipes (bool, 'both'/'supply'/'demand', ID(s), or {'supply': true|id|null, 'demand': true|id|null}), "
                    "output_variables, ems_sensors, ems_internal_variables, ems_actuators. "
                    "Example: [{'name': 'CHWLoop', 'loop_type': 'Cooling', 'supply': ['chw_pump'], 'supply_branches': [['chiller']], 'bypass_pipes': true, 'supply_setpoint': 6.7, 'demand_branches': [['cc1']]}]."
                )
            ),
        ] = None,
        vrf_systems: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Optional list of VRF outdoor unit to terminal binding dicts. Supported keys: "
                    "vrf (required VRF outdoor unit component ID), terminals (list[str] terminal IDs). "
                    "Example: [{'vrf': 'vrf_outdoor', 'terminals': ['vrf_term_1']}]."
                )
            ),
        ] = None,
        energy_management_system: Annotated[
            str | None,
            Field(
                description=(
                    "Optional IB_EnergyManagementSystem component ID to attach on IB_HVACSystem; "
                    "pass '' to clear."
                )
            ),
        ] = None,
        electric_load_center: Annotated[
            str | None,
            Field(
                description=(
                    "Optional IB_ElectricLoadCenter component ID to attach on IB_HVACSystem; "
                    "pass '' to clear."
                )
            ),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional updated DisplayName on IB_HVACSystem."),
        ] = None,
        replace: Annotated[
            bool,
            Field(
                description=(
                    "If true, reset existing loop/system bindings (or replace an imported-only "
                    "specification) before applying provided configurations."
                )
            ),
        ] = False,
    ) -> IronbugSystemMutationResult:
        """Configure loops and thermal zone bindings on an Ironbug system."""
        from garden.ironbug.service import configure_ironbug_loops

        return validate_output(
            IronbugSystemMutationResult,
            configure_ironbug_loops(
                garden_root=garden_root,
                ironbug_model_target=dump_target(ironbug_model_target),
                identifier=identifier,
                thermal_zones=thermal_zones,
                air_loops=air_loops,
                plant_loops=plant_loops,
                vrf_systems=vrf_systems,
                energy_management_system=energy_management_system,
                electric_load_center=electric_load_center,
                display_name=display_name,
                replace=replace,
            ),
        )

    @mcp.tool(
        name="IB_Create_System",
        description=(
            "Initialize a new Garden-managed official Ironbug IB_HVACSystem specification under "
            "models/ironbug/<identifier>.json, instantiate a starter HVAC template "
            "('vav_chiller_boiler', 'doas_fcu', 'vrf_doas', 'wshp'), or import an existing "
            "official IB_HVACSystem JSON (pass editable=true to reverse-parse it into an "
            "editable draft). Use the returned ironbug_model_target with IB_Upsert_Components "
            "and IB_Configure_Loops."
        ),
        tags={"ironbug", "detailed-hvac", "hvac", "author"},
        annotations={"read_only_hint": False, "destructive_hint": False},
        timeout=20,
    )
    def ib_create_system(
        garden_root: Annotated[
            str,
            Field(min_length=1, description="Required Garden root path containing garden.json."),
        ],
        identifier: Annotated[
            str,
            Field(min_length=1, description="Unique identifier for this Ironbug HVAC system inside the Garden."),
        ],
        display_name: Annotated[
            str | None,
            Field(description="Optional human-readable DisplayName stored on IB_HVACSystem."),
        ] = None,
        specification: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional existing official IB_HVACSystem JSON dict or JSON string to import "
                    "(preserves $type, DisplayName, TrackingID, AirLoops, PlantLoops, etc.)."
                )
            ),
        ] = None,
        template: Annotated[
            IronbugTemplateName | None,
            Field(
                description=(
                    "Optional starter HVAC template preset producing an editable draft: "
                    "'vav_chiller_boiler', 'doas_fcu', 'vrf_doas', or 'wshp'."
                )
            ),
        ] = None,
        editable: Annotated[
            bool,
            Field(
                description=(
                    "When importing an existing official specification, reverse-parse it via "
                    "IB_HVACSystem.FromJson into an editable draft (default: false preserves "
                    "imported-only overwrite protection)."
                )
            ),
        ] = False,
        room_names: Annotated[
            list[str] | None,
            Field(
                description=(
                    "Optional list of Honeybee Room / thermal zone identifiers used when "
                    "instantiating a template preset (defaults to ['Zone1'])."
                )
            ),
        ] = None,
        overwrite: Annotated[
            bool,
            Field(description="Replace an existing Ironbug system with the same identifier."),
        ] = False,
    ) -> IronbugSystemMutationResult:
        """Create an Ironbug HVAC system in a Garden."""
        from garden.ironbug.service import create_ironbug_system

        return validate_output(
            IronbugSystemMutationResult,
            create_ironbug_system(
                garden_root=garden_root,
                identifier=identifier,
                display_name=display_name,
                specification=specification,
                template=template,
                editable=editable,
                room_names=room_names,
                overwrite=overwrite,
            ),
        )

    @mcp.tool(
        name="IB_Describe_Component",
        description=(
            "Inspect official C# Ironbug IB_* component classes, returning constructor "
            "signatures, child wiring slots, and EnergyPlus FieldSet metadata with units, "
            "defaults, and choices. Set include_advanced=true for curve and advanced fields."
        ),
        tags={"ironbug", "detailed-hvac", "hvac", "inspect"},
        annotations={"read_only_hint": True, "destructive_hint": False, "idempotent_hint": True},
        timeout=20,
    )
    def ib_describe_component(
        type_names: Annotated[
            list[str] | str,
            Field(
                description=(
                    "One IB_* type name, comma-separated string, or list, "
                    "e.g. ['IB_ChillerElectricEIR']."
                )
            ),
        ],
        include_advanced: Annotated[
            bool,
            Field(description="Include all advanced *_FieldSet fields beyond the core fields."),
        ] = False,
    ) -> DescribeComponentsResult:
        """Describe official Ironbug component schemas."""
        from garden.ironbug.service import describe_ironbug_components

        return validate_output(
            DescribeComponentsResult,
            describe_ironbug_components(
                type_names=type_names,
                include_advanced=include_advanced,
            ),
        )

    @mcp.tool(
        name="IB_Inspect_System",
        description=(
            "Inspect a Garden-managed Ironbug IB_HVACSystem summary, loop counts, "
            "and components. Set include_draft=true to also include the editable "
            "component and loop draft JSON."
        ),
        tags={"ironbug", "detailed-hvac", "hvac", "inspect"},
        annotations={"read_only_hint": True, "destructive_hint": False, "idempotent_hint": True},
        timeout=20,
    )
    def ib_inspect_system(
        garden_root: Annotated[
            str,
            Field(min_length=1, description="Required Garden root path containing garden.json."),
        ],
        ironbug_model_target: Annotated[
            IronbugModelTargetRef | None,
            Field(description="Target returned by IB_Create_System. Optional when only one Ironbug system exists."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional Ironbug system identifier when ironbug_model_target is omitted."),
        ] = None,
        include_draft: Annotated[
            bool,
            Field(description="Include the editable component and loop draft JSON."),
        ] = False,
    ) -> InspectSystemResult:
        """Inspect an Ironbug HVAC system in a Garden."""
        from garden.ironbug.service import inspect_ironbug_system

        return validate_output(
            InspectSystemResult,
            inspect_ironbug_system(
                garden_root=garden_root,
                ironbug_model_target=dump_target(ironbug_model_target),
                identifier=identifier,
                include_draft=include_draft,
            ),
        )

    @mcp.tool(
        name="IB_List_Components",
        description=(
            "Search or browse official C# Ironbug.HVAC component classes by category or "
            "keyword, including English and common Chinese HVAC terms. Use discovered "
            "IB_* type names with IB_Describe_Component."
        ),
        tags={"ironbug", "detailed-hvac", "hvac", "search"},
        annotations={"read_only_hint": True, "destructive_hint": False, "idempotent_hint": True},
        timeout=20,
    )
    def ib_list_components(
        category: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Ironbug component category filter (case-insensitive). Valid categories: "
                    "'air_loop', 'air_terminal', 'availability_manager', 'coil_cooling', 'coil_dx', "
                    "'coil_heating', 'controller', 'curve', 'ems', 'fan', 'generator_electric', "
                    "'plant_equipment', 'plant_loop', 'pump', 'schedule', 'setpoint_manager', "
                    "'sizing', 'thermal_zone', 'vrf', 'zone_equipment', or 'other'."
                )
            ),
        ] = None,
        query: Annotated[
            str | None,
            Field(
                description=(
                    "Optional keyword or IB_* type name query, e.g. 'chiller', "
                    "'vav', or '冷机'."
                )
            ),
        ] = None,
        limit: Annotated[
            int,
            Field(ge=1, le=100, description="Maximum number of matching component types per page (1-100)."),
        ] = 25,
        offset: Annotated[
            int,
            Field(ge=0, description="Zero-based pagination offset into matched component types (default: 0)."),
        ] = 0,
    ) -> ListComponentsResult:
        """List official Ironbug component classes."""
        from garden.ironbug.service import list_ironbug_components

        return validate_output(
            ListComponentsResult,
            list_ironbug_components(
                category=category,
                query=query,
                limit=limit,
                offset=offset,
            ),
        )

    @mcp.tool(
        name="IB_Upsert_Components",
        description=(
            "Add, update, or remove typed Ironbug components in a system draft and "
            "serialize through C# Ironbug.HVAC. Reference child component IDs in "
            "ctor_args, fields, or wiring; reusing an ID across loops links it via "
            "TrackingID."
        ),
        tags={"ironbug", "detailed-hvac", "hvac", "author", "edit"},
        annotations={"read_only_hint": False, "destructive_hint": False},
        timeout=30,
    )
    def ib_upsert_components(
        garden_root: Annotated[
            str,
            Field(min_length=1, description="Required Garden root path containing garden.json."),
        ],
        components: Annotated[
            dict[str, dict[str, Any]] | list[dict[str, Any]] | None,
            Field(
                description=(
                    "Mapping of component_id -> spec dict, or list of spec dicts (each requiring 'id'), "
                    "using IB_* class names from IB_Describe_Component (leave unset when removing via remove_ids). "
                    "Supported spec fields: type (required IB_* class), ctor_args (list or dict; pass child objects as IDs), "
                    "fields (dict), wiring (dict of slot_alias or Set*/Add* -> ID(s)), output_variables (list of names or "
                    "{variable_name, reporting_frequency}), ems_sensors, ems_internal_variables, ems_actuators "
                    "(IDs or inline dicts), children (ordered ID list), ib_properties (dict), tracking_id (str)."
                )
            ),
        ] = None,
        ironbug_model_target: Annotated[
            IronbugModelTargetRef | None,
            Field(description="Target returned by IB_Create_System. Optional when only one Ironbug system exists in the Garden."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional Ironbug system identifier when ironbug_model_target is unset."),
        ] = None,
        remove_ids: Annotated[
            list[str] | None,
            Field(description="Optional list of component IDs to delete from the draft."),
        ] = None,
        replace: Annotated[
            bool,
            Field(description="If true, replace all existing components; if false, merge into existing components."),
        ] = False,
    ) -> IronbugSystemMutationResult:
        """Add or update typed components in an Ironbug system."""
        from garden.ironbug.service import upsert_ironbug_components

        return validate_output(
            IronbugSystemMutationResult,
            upsert_ironbug_components(
                garden_root=garden_root,
                components=components,
                ironbug_model_target=dump_target(ironbug_model_target),
                identifier=identifier,
                remove_ids=remove_ids,
                replace=replace,
            ),
        )

    @mcp.tool(
        name="IB_Validate_System",
        description=(
            "Compile and validate an Ironbug IB_HVACSystem in-memory via official C# "
            "SaveHVAC against OpenStudio. When a Honeybee model_target is provided (or base "
            "model exists), exports it to a temporary OSM via model_to_osm and runs SaveHVAC "
            "plus an OpenStudio EnergyPlusForwardTranslator dry-run alongside room precondition checks. "
            "Run this before IB_Apply_To_Model."
        ),
        tags={"ironbug", "detailed-hvac", "hvac", "validate"},
        annotations={"read_only_hint": True, "destructive_hint": False, "idempotent_hint": True},
        timeout=60,
    )
    def ib_validate_system(
        garden_root: Annotated[
            str,
            Field(min_length=1, description="Required Garden root path containing garden.json."),
        ],
        ironbug_model_target: Annotated[
            IronbugModelTargetRef | None,
            Field(description="Target returned by IB_Create_System. Optional when only one Ironbug system exists."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Optional Ironbug system identifier when ironbug_model_target is omitted."),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Optional Honeybee or Dragonfly model target to validate OSM compilation and room preconditions against."),
        ] = None,
        model_family: Annotated[
            Literal["honeybee", "dragonfly"],
            Field(description="Model family for room precondition checks (default: 'honeybee')."),
        ] = "honeybee",
        room_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional explicit room identifiers to verify against the system's thermal zones."),
        ] = None,
        run_forward_translator: Annotated[
            bool | None,
            Field(description="Optional override to run OpenStudio EnergyPlusForwardTranslator dry-run (defaults to true when a Honeybee OSM is translated)."),
        ] = None,
    ) -> ValidateSystemResult:
        """Validate an Ironbug system against OpenStudio and model rooms."""
        from garden.ironbug.service import validate_ironbug_system

        return validate_output(
            ValidateSystemResult,
            validate_ironbug_system(
                garden_root=garden_root,
                ironbug_model_target=dump_target(ironbug_model_target),
                identifier=identifier,
                model_target=dump_target(model_target),
                model_family=model_family,
                room_identifiers=room_identifiers,
                run_forward_translator=run_forward_translator,
            ),
        )
