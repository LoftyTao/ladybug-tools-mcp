"""energy MCP tools."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.contracts import (
    BuildingModelTargetRef,
    BuildingObjectTargetRef,
    LibraryObjectTargetRef,
    MutationResultModel,
    dump_input,
    dump_target,
    dump_targets,
    validate_output,
)


MaterialType = Literal[
    "opaque",
    "opaque_no_mass",
    "vegetation",
    "simple_glazing",
    "window_glazing",
    "window_gas",
    "window_gas_mixture",
    "window_gas_custom",
    "window_shade",
    "window_blind",
    "window_frame",
]
ConstructionType = Literal[
    "opaque",
    "window",
    "window_shade",
    "window_dynamic",
    "shade",
    "air_boundary",
]
DetailLevel = Literal["summary", "full"]
LoadType = Literal[
    "people",
    "lighting",
    "electric_equipment",
    "gas_equipment",
    "service_hot_water",
    "infiltration",
    "ventilation",
    "setpoint",
    "zone_ventilation_fan",
    "process",
    "exhaust_air",
    "internal_mass",
    "shw_system",
]
ScheduleMode = Literal["ruleset", "fixed_interval", "type_limit"]
NumericType = Literal["Continuous", "Discrete", "continuous", "discrete"]
PVOrLoadCenterType = Literal["pv_properties", "electric_load_center"]
RoomEnergyControlType = Literal[
    "simple_ventilation",
    "airflow_network",
    "daylighting_control",
]


def register(mcp: FastMCP) -> None:
    """Register energy tools."""

    @mcp.tool(
        name="EP_Create_Material",
        description=(
            "Create any Honeybee Energy material layer dispatched by material_type: opaque, "
            "opaque_no_mass, vegetation, simple_glazing, window_glazing, window_gas, "
            "window_gas_mixture, window_gas_custom, window_shade, window_blind, or window_frame. "
            "Pass material-specific fields inside params (for example thickness, conductivity, "
            "density, specific_heat for opaque; r_value for opaque_no_mass; u_factor, shgc, vt "
            "for simple_glazing; width, conductance for window_frame). Returns object_dict plus "
            "summary_view, or a Garden Properties Library target plus persistence_receipt when "
            "garden_root is provided and return_object_dict=false."
        ),
        tags={
            "energy",
            "construction",
            "material",
            "author",
        },
        timeout=20,
    )
    def create_material(
        material_type: Annotated[
            MaterialType,
            Field(
                description=(
                    "Material family: opaque, opaque_no_mass, vegetation, simple_glazing, "
                    "window_glazing, window_gas, window_gas_mixture, window_gas_custom, "
                    "window_shade, window_blind, or window_frame."
                )
            ),
        ],
        identifier: Annotated[str, Field(description="Material identifier.")],
        params: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Material-specific parameter dictionary matching the selected material_type "
                    "(for example thickness/conductivity/density/specific_heat for opaque, "
                    "r_value for opaque_no_mass, u_factor/shgc/vt for simple_glazing, "
                    "gas_type/thickness for window_gas, or width/conductance for window_frame)."
                )
            ),
        ] = None,
        return_detail: Annotated[
            DetailLevel,
            Field(
                description=(
                    "summary returns key material values; full also includes a property_matrix "
                    "with SDK property rows."
                )
            ),
        ] = "summary",
        garden_root: Annotated[
            str | None,
            Field(
                description=(
                    "Garden root path containing garden.json, usually GD_Create['garden_root']; "
                    "required when saving or reading Garden targets."
                )
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description=(
                    "Return the full material object_dict. Set false with garden_root to return "
                    "only target/summary/receipt."
                )
            ),
        ] = True,
    ) -> MutationResultModel:
        """Create a Honeybee Energy material layer."""
        from garden.energy.constructionsets import create_material as service

        return validate_output(
            MutationResultModel,
            service(
                material_type=material_type,
                identifier=identifier,
                params=dump_input(params),
                return_detail=return_detail,
                garden_root=garden_root,
                return_object_dict=return_object_dict,
            ),
        )

    @mcp.tool(
        name="EP_Create_Construction",
        description=(
            "Create a Honeybee Energy construction dispatched by construction_type: opaque, "
            "window, window_shade, window_dynamic, shade, or air_boundary. For opaque constructions "
            "pass ordered material layers in materials; for window constructions either pass "
            "glazing/gas layers in materials (with optional frame) or omit materials and pass "
            "u_factor, shgc, and vt for a SimpleGlazSys window construction; for window_shade pass "
            "window_construction and shade_material (plus optional shade_location, control_type, "
            "setpoint, schedule) in params; for window_dynamic pass constructions and schedule in "
            "params; for shade or air_boundary pass optional settings in params "
            "(solar_reflectance/visible_reflectance/is_specular or "
            "air_mixing_per_area/air_mixing_schedule). Returns object_dict plus summary_view, or "
            "a saved Garden target plus persistence_receipt when garden_root is provided and "
            "return_object_dict=false."
        ),
        tags={
            "energy",
            "construction",
            "material",
            "window",
            "opaque",
            "shade",
            "air-boundary",
            "author",
        },
        timeout=20,
    )
    def create_construction(
        construction_type: Annotated[
            ConstructionType,
            Field(
                description=(
                    "Construction family: opaque, window, window_shade, window_dynamic, "
                    "shade, or air_boundary."
                )
            ),
        ],
        identifier: Annotated[str, Field(description="Construction identifier.")],
        materials: Annotated[
            list[LibraryObjectTargetRef | dict[str, Any] | str] | None,
            Field(
                description=(
                    "Ordered material layers from outside to inside for opaque or layered window "
                    "constructions; each item may be an object_dict, Garden target, or standards "
                    "library identifier. Omit for window simple-parameter mode (u_factor/shgc/vt), "
                    "window_shade, window_dynamic, shade, or air_boundary."
                )
            ),
        ] = None,
        u_factor: Annotated[
            float | None,
            Field(
                ge=0.0,
                le=12.0,
                description=(
                    "Window system U-factor in W/m2-K when construction_type='window' and "
                    "materials is omitted."
                ),
            ),
        ] = None,
        shgc: Annotated[
            float | None,
            Field(
                ge=0.0,
                le=1.0,
                description=(
                    "Solar heat gain coefficient when construction_type='window' and materials is "
                    "omitted."
                ),
            ),
        ] = None,
        vt: Annotated[
            float,
            Field(
                ge=0.0,
                le=1.0,
                description=(
                    "Visible transmittance when construction_type='window' and materials is "
                    "omitted."
                ),
            ),
        ] = 0.6,
        frame: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional EnergyWindowFrame object_dict, Garden target, or identifier for "
                    "layered window constructions."
                )
            ),
        ] = None,
        params: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional type-specific parameter dict (for window_shade: window_construction, "
                    "shade_material, shade_location, control_type, setpoint, schedule; for "
                    "window_dynamic: constructions, schedule; for shade: solar_reflectance, "
                    "visible_reflectance, is_specular; for air_boundary: air_mixing_per_area, "
                    "air_mixing_schedule)."
                )
            ),
        ] = None,
        return_detail: Annotated[
            DetailLevel,
            Field(
                description=(
                    "summary returns key property values; full also returns a layer_matrix for "
                    "layered constructions."
                )
            ),
        ] = "summary",
        garden_root: Annotated[
            str | None,
            Field(
                description=(
                    "Garden root path containing garden.json, usually GD_Create['garden_root']; "
                    "required when saving or reading Garden targets."
                )
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description=(
                    "Return the full construction object_dict. Set false with garden_root to "
                    "return only target/summary/receipt."
                )
            ),
        ] = True,
    ) -> MutationResultModel:
        """Create a Honeybee Energy construction."""
        from garden.energy.constructionsets import create_construction as service

        return validate_output(
            MutationResultModel,
            service(
                construction_type=construction_type,
                identifier=identifier,
                materials=dump_input(materials),
                u_factor=u_factor,
                shgc=shgc,
                vt=vt,
                frame=dump_input(frame),
                params=dump_input(params),
                return_detail=return_detail,
                garden_root=garden_root,
                return_object_dict=return_object_dict,
            ),
        )

    @mcp.tool(
        name="EP_Create_Construction_Set",
        description=(
            "Create a saved Honeybee Energy ConstructionSet, the envelope default set for wall, "
            "floor, roof/ceiling, aperture, door, shade, and air-boundary constructions. Start "
            "from an optional base_construction_set, then override wall_set, floor_set, "
            "roof_ceiling_set, aperture_set, or door_set using either inline subset dicts (such as "
            "{'exterior_construction': ..., 'interior_construction': ..., 'ground_construction': "
            "...}, {'window_construction': ..., 'skylight_construction': ...}, or "
            "{'exterior_construction': ..., 'exterior_glass_construction': ...}) or a single "
            "construction identifier, Garden target, or inline construction dict (such as "
            "{'u_factor': 1.4, 'shgc': 0.35} or {'materials': [...]}). Returns object_dict plus "
            "summary_view, or saved target plus persistence_receipt when garden_root is provided "
            "and return_object_dict=false."
        ),
        tags={
            "energy",
            "construction-set",
            "construction",
            "envelope",
            "author",
        },
        timeout=20,
    )
    def create_construction_set(
        identifier: Annotated[str, Field(description="ConstructionSet identifier.")],
        base_construction_set: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional base ConstructionSet object_dict, Garden target, or standards-library "
                    "identifier."
                )
            ),
        ] = None,
        wall_set: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional WallConstructionSet dict, inline slot dict "
                    "(exterior_construction/interior_construction/ground_construction), or single "
                    "OpaqueConstruction identifier/target/inline dict."
                )
            ),
        ] = None,
        floor_set: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional FloorConstructionSet dict, inline slot dict "
                    "(exterior_construction/interior_construction/ground_construction), or single "
                    "OpaqueConstruction identifier/target/inline dict."
                )
            ),
        ] = None,
        roof_ceiling_set: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional RoofCeilingConstructionSet dict, inline slot dict "
                    "(exterior_construction/interior_construction/ground_construction), or single "
                    "OpaqueConstruction identifier/target/inline dict."
                )
            ),
        ] = None,
        aperture_set: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional ApertureConstructionSet dict, inline slot dict "
                    "(window_construction/interior_construction/skylight_construction/"
                    "operable_construction), or single WindowConstruction identifier/target/inline dict."
                )
            ),
        ] = None,
        door_set: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional DoorConstructionSet dict, inline slot dict "
                    "(exterior_construction/interior_construction/exterior_glass_construction/"
                    "interior_glass_construction/overhead_construction), or single opaque door "
                    "construction identifier/target/inline dict."
                )
            ),
        ] = None,
        shade_construction: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | str | None,
            Field(
                description="Optional ShadeConstruction dict, Garden target, inline dict, or library identifier."
            ),
        ] = None,
        air_boundary_construction: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | str | None,
            Field(
                description="Optional AirBoundaryConstruction or OpaqueConstruction dict, Garden target, inline dict, or library identifier."
            ),
        ] = None,
        return_detail: Annotated[
            DetailLevel,
            Field(
                description="summary returns key slot identifiers and counts; full also returns slot_matrix and material_matrix rows."
            ),
        ] = "summary",
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Return the full ConstructionSet object_dict. Set false with garden_root to return only target/summary/receipt."
            ),
        ] = True,
    ) -> MutationResultModel:
        """Create a Honeybee Energy ConstructionSet object."""
        from garden.energy.constructionsets import create_construction_set as service

        return validate_output(
            MutationResultModel,
            service(
                identifier=identifier,
                base_construction_set=dump_input(base_construction_set),
                wall_set=dump_input(wall_set),
                floor_set=dump_input(floor_set),
                roof_ceiling_set=dump_input(roof_ceiling_set),
                aperture_set=dump_input(aperture_set),
                door_set=dump_input(door_set),
                shade_construction=dump_input(shade_construction),
                air_boundary_construction=dump_input(air_boundary_construction),
                return_detail=return_detail,
                garden_root=garden_root,
                return_object_dict=return_object_dict,
            ),
        )

    @mcp.tool(
        name="EP_Create_Load",
        description=(
            "Create any Honeybee Energy internal-gain load, outdoor-air/infiltration load, "
            "thermostat/humidistat Setpoint, VentilationFan, Process load, ExhaustAir (when "
            "honeybee-energy>=1.125), InternalMass, or SHWSystem dispatched by load_type: people, "
            "lighting, electric_equipment, gas_equipment, service_hot_water, infiltration, "
            "ventilation, setpoint, zone_ventilation_fan, process, exhaust_air, internal_mass, "
            "or shw_system. Pass load-specific arguments in params. Use garden_root and "
            "return_object_dict=false to save a compact Garden Properties Library target for "
            "EP_Create_Program_Type or HB_Edit_Objects."
        ),
        tags={
            "author",
            "energy",
            "load",
            "program-type",
            "setpoint",
            "ventilation",
            "infiltration",
        },
        timeout=20,
    )
    def create_load(
        load_type: Annotated[
            LoadType,
            Field(
                description=(
                    "Load family: people, lighting, electric_equipment, gas_equipment, "
                    "service_hot_water, infiltration, ventilation, setpoint, zone_ventilation_fan, "
                    "process, exhaust_air, internal_mass, or shw_system."
                )
            ),
        ],
        identifier: Annotated[str, Field(description="Load object identifier.")],
        params: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Load-specific parameter dict (for example people_per_area/occupancy_schedule "
                    "for people; watts_per_area/schedule for lighting or equipment; "
                    "flow_per_area/target_temperature for service_hot_water; "
                    "flow_per_exterior_area for infiltration; flow_per_person/flow_per_area/"
                    "air_changes_per_hour/method for ventilation; heating_setpoint/cooling_setpoint "
                    "or heating_schedule/cooling_schedule for setpoint; flow_rate/ventilation_type "
                    "for zone_ventilation_fan; watts/schedule/fuel_type/end_use_category for "
                    "process; construction/area for internal_mass; equipment_type/heater_efficiency/"
                    "ambient_condition/ambient_loss_coefficient for shw_system)."
                )
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Return the full load object_dict. Set false with garden_root to return only target/summary/receipt."
            ),
        ] = True,
    ) -> MutationResultModel:
        """Create a Honeybee Energy load, setpoint, or zone ventilation fan."""
        from garden.energy.programtypes import create_load as service

        return validate_output(
            MutationResultModel,
            service(
                load_type=load_type,
                identifier=identifier,
                params=dump_input(params),
                garden_root=garden_root,
                return_object_dict=return_object_dict,
            ),
        )

    @mcp.tool(
        name="EP_Create_Program_Type",
        description=(
            "Create a Honeybee Energy ProgramType, the room program bundle for occupancy, "
            "lighting, equipment, service hot water, infiltration, ventilation, and setpoints. "
            "Each load slot accepts a Garden Properties Library load target, a full object_dict, "
            "or a clean inline shorthand dict (such as {'people_per_area': 0.05}, "
            "{'watts_per_area': 8.5}, {'flow_per_exterior_area': 0.0002}, "
            "{'flow_per_person': 0.0025, 'flow_per_area': 0.0003}, or "
            "{'heating_setpoint': 20, 'cooling_setpoint': 24}). Returns object_dict, or target "
            "plus persistence_receipt when saved with garden_root."
        ),
        tags={
            "energy",
            "program-type",
            "load",
            "occupancy",
            "schedule",
            "author",
        },
        timeout=20,
    )
    def create_program_type(
        identifier: Annotated[str, Field(description="ProgramType identifier.")],
        base_program_type: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | str | None,
            Field(
                description="Optional base ProgramType dict, Garden Properties Library target, or ProgramType library identifier."
            ),
        ] = None,
        people: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | None,
            Field(
                description="Optional People object_dict, Garden load target, or shorthand dict ({'people_per_area': ...})."
            ),
        ] = None,
        lighting: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | None,
            Field(
                description="Optional Lighting object_dict, Garden load target, or shorthand dict ({'watts_per_area': ...})."
            ),
        ] = None,
        electric_equipment: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | None,
            Field(
                description="Optional ElectricEquipment object_dict, Garden load target, or shorthand dict ({'watts_per_area': ...})."
            ),
        ] = None,
        gas_equipment: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | None,
            Field(
                description="Optional GasEquipment object_dict, Garden load target, or shorthand dict ({'watts_per_area': ...})."
            ),
        ] = None,
        service_hot_water: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | None,
            Field(
                description="Optional ServiceHotWater object_dict, Garden load target, or shorthand dict ({'flow_per_area': ...})."
            ),
        ] = None,
        infiltration: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | None,
            Field(
                description="Optional Infiltration object_dict, Garden load target, or shorthand dict ({'flow_per_exterior_area': ...})."
            ),
        ] = None,
        ventilation: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | None,
            Field(
                description="Optional Ventilation object_dict, Garden load target, or shorthand dict ({'flow_per_person': ..., 'flow_per_area': ..., 'flow_per_zone': ..., 'air_changes_per_hour': ...})."
            ),
        ] = None,
        setpoint: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | None,
            Field(
                description="Optional Setpoint object_dict, Garden load target, or shorthand dict ({'heating_setpoint': ..., 'cooling_setpoint': ...})."
            ),
        ] = None,
        exhaust: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | None,
            Field(
                description="Optional ExhaustAir object_dict or Garden target (supported only when honeybee-energy>=1.125 is installed)."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Return the full ProgramType object_dict. Set false with garden_root to return only target/summary/receipt."
            ),
        ] = True,
    ) -> MutationResultModel:
        """Create a Honeybee Energy ProgramType object."""
        from garden.energy.programtypes import create_program_type as service

        return validate_output(
            MutationResultModel,
            service(
                identifier=identifier,
                base_program_type=dump_input(base_program_type),
                people=dump_input(people),
                lighting=dump_input(lighting),
                electric_equipment=dump_input(electric_equipment),
                gas_equipment=dump_input(gas_equipment),
                service_hot_water=dump_input(service_hot_water),
                infiltration=dump_input(infiltration),
                ventilation=dump_input(ventilation),
                setpoint=dump_input(setpoint),
                exhaust=dump_input(exhaust),
                garden_root=garden_root,
                return_object_dict=return_object_dict,
            ),
        )

    @mcp.tool(
        name="EP_Create_Schedule_Ruleset",
        description=(
            "Create a Honeybee Energy schedule resource dispatched by schedule_type: 'ruleset' "
            "(ScheduleRuleset, default), 'fixed_interval' (ScheduleFixedInterval), or 'type_limit' "
            "(ScheduleTypeLimit). For ruleset mode, assemble from a default_day_schedule (or "
            "default_value) plus optional schedule_rules or interval shorthand rules (supporting "
            "per-rule 'start_date' and 'end_date'), holiday, and design-day schedules. For "
            "fixed_interval mode, pass values plus optional timestep, start_date, "
            "placeholder_value, interpolate, and schedule_type_limit. For type_limit mode, pass "
            "optional lower_limit, upper_limit, numeric_type, and unit_type. Returns object_dict, "
            "summary_view, and optional data; with garden_root also returns target and "
            "persistence_receipt."
        ),
        tags={
            "energy",
            "schedule",
            "ruleset",
            "schedule-type-limit",
            "holiday",
            "design-day",
            "author",
        },
        timeout=20,
    )
    def create_schedule_ruleset(
        identifier: Annotated[str, Field(description="Schedule or ScheduleTypeLimit identifier.")],
        schedule_type: Annotated[
            ScheduleMode,
            Field(
                description="Schedule resource mode: ruleset (default), fixed_interval, or type_limit."
            ),
        ] = "ruleset",
        default_day_schedule: Annotated[
            dict[str, Any] | list[float] | None,
            Field(
                description=(
                    "For ruleset mode: default ScheduleDay object_dict, inline day dict ({'values': "
                    "[...], 'times': [...], 'interpolate': false}), or 24-value hourly list[float] "
                    "(or omit and pass default_value)."
                )
            ),
        ] = None,
        schedule_rules: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "For ruleset mode: optional ScheduleRule rows ordered from highest to lowest "
                    "priority; each row may be an SDK ScheduleRule dict or an inline rule dict "
                    "({'schedule_day': ..., 'apply_monday': true, ...} or {'day': ..., 'weekdays': "
                    "[...], 'start_date': ..., 'end_date': ...})."
                )
            ),
        ] = None,
        rules: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "For ruleset mode: optional interval shorthand rows ({'start_time', 'end_time', "
                    "'value', 'days', optional 'start_date', optional 'end_date'}) or inline rule "
                    "dicts. Mutually exclusive with schedule_rules."
                )
            ),
        ] = None,
        schedule_type_limit: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | str | None,
            Field(
                description=(
                    "Optional ScheduleTypeLimit dict, Garden Properties Library target/identifier, "
                    "or standards-library identifier that constrains values and units (ruleset or "
                    "fixed_interval mode)."
                )
            ),
        ] = None,
        default_value: Annotated[
            float | None,
            Field(
                description="For ruleset mode: constant all-day default value used when default_day_schedule is omitted."
            ),
        ] = None,
        summer_designday_schedule: Annotated[
            dict[str, Any] | list[float] | None,
            Field(description="For ruleset mode: optional summer design-day ScheduleDay dict, inline day dict, or 24-value list."),
        ] = None,
        winter_designday_schedule: Annotated[
            dict[str, Any] | list[float] | None,
            Field(description="For ruleset mode: optional winter design-day ScheduleDay dict, inline day dict, or 24-value list."),
        ] = None,
        holiday_schedule: Annotated[
            dict[str, Any] | list[float] | None,
            Field(description="For ruleset mode: optional holiday ScheduleDay dict, inline day dict, or 24-value list."),
        ] = None,
        values: Annotated[
            list[float] | None,
            Field(
                description=(
                    "For fixed_interval mode: list of numeric schedule values (24 to 8760*timestep "
                    "values)."
                )
            ),
        ] = None,
        timestep: Annotated[
            int | None,
            Field(
                ge=1,
                le=60,
                description=(
                    "For fixed_interval mode: steps per hour (1, 2, 3, 4, 5, 6, 10, 12, 15, 20, "
                    "30, or 60; default 1)."
                ),
            ),
        ] = None,
        start_date: Annotated[
            dict[str, Any] | list[Any] | str | None,
            Field(
                description=(
                    "For fixed_interval mode: optional start date as Ladybug Date dict, "
                    "[month, day], or date string (default Jan 1)."
                )
            ),
        ] = None,
        placeholder_value: Annotated[
            float | None,
            Field(
                description="For fixed_interval mode: placeholder value outside schedule dates (default 0.0)."
            ),
        ] = None,
        interpolate: Annotated[
            bool | None,
            Field(
                description="For fixed_interval mode: whether to linearly interpolate between values (default false)."
            ),
        ] = None,
        lower_limit: Annotated[
            float | str | None,
            Field(
                description="For type_limit mode: lower bound number or 'no_limit' (default no_limit)."
            ),
        ] = None,
        upper_limit: Annotated[
            float | str | None,
            Field(
                description="For type_limit mode: upper bound number or 'no_limit' (default no_limit)."
            ),
        ] = None,
        numeric_type: Annotated[
            NumericType | None,
            Field(
                description="For type_limit mode: 'Continuous' (default) or 'Discrete'."
            ),
        ] = None,
        unit_type: Annotated[
            str | None,
            Field(
                description=(
                    "For type_limit mode: EnergyPlus schedule unit type such as 'Dimensionless', "
                    "'Temperature', 'Availability', 'Percent', 'Control', 'Mode', etc."
                )
            ),
        ] = None,
        include_data: Annotated[
            bool,
            Field(
                description="Whether to generate Ladybug DataCollection schedule data for summary, target persistence, or optional return as data."
            ),
        ] = True,
        return_data: Annotated[
            bool,
            Field(
                description="Return the full Ladybug DataCollection dict in data (set false with garden_root to persist data_target/data_persistence_receipt)."
            ),
        ] = True,
        data_analysis_period: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Ladybug AnalysisPeriod dict or string for generated data."
            ),
        ] = None,
        data_timestep: Annotated[
            int,
            Field(
                ge=1,
                le=60,
                description="DataCollection timestep, in steps per hour. Ignored when data_analysis_period is provided.",
            ),
        ] = 1,
        data_start_date: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional DataCollection start date as Ladybug Date dict or string."),
        ] = None,
        data_end_date: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional DataCollection end date as Ladybug Date dict or string."),
        ] = None,
        data_start_dow: Annotated[
            str, Field(description="Day of week for the start date. Default: Sunday.")
        ] = "Sunday",
        data_holidays: Annotated[
            list[dict[str, Any] | str] | None,
            Field(description="Optional holiday dates as Ladybug Date dicts or strings."),
        ] = None,
        data_leap_year: Annotated[
            bool, Field(description="Whether generated data should use a leap year.")
        ] = False,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Return the full schedule object_dict. Set false with garden_root to return only target/summary/receipt."
            ),
        ] = True,
    ) -> MutationResultModel:
        """Create a Honeybee Energy ScheduleRuleset, ScheduleFixedInterval, or ScheduleTypeLimit."""
        from garden.energy.schedules import create_schedule_ruleset as service

        return validate_output(
            MutationResultModel,
            service(
                identifier=identifier,
                schedule_type=schedule_type,
                default_day_schedule=dump_input(default_day_schedule),
                schedule_rules=dump_input(schedule_rules),
                rules=dump_input(rules),
                schedule_type_limit=dump_input(schedule_type_limit),
                default_value=default_value,
                summer_designday_schedule=dump_input(summer_designday_schedule),
                winter_designday_schedule=dump_input(winter_designday_schedule),
                holiday_schedule=dump_input(holiday_schedule),
                values=values,
                timestep=timestep,
                start_date=dump_input(start_date),
                placeholder_value=placeholder_value,
                interpolate=interpolate,
                lower_limit=lower_limit,
                upper_limit=upper_limit,
                numeric_type=numeric_type,
                unit_type=unit_type,
                include_data=include_data,
                data_analysis_period=dump_input(data_analysis_period),
                data_timestep=data_timestep,
                data_start_date=dump_input(data_start_date),
                data_end_date=dump_input(data_end_date),
                data_start_dow=data_start_dow,
                data_holidays=dump_input(data_holidays),
                data_leap_year=data_leap_year,
                garden_root=garden_root,
                return_data=return_data,
                return_object_dict=return_object_dict,
            ),
        )

    @mcp.tool(
        name="EP_Create_HVAC_Template",
        description=(
            "Search Honeybee Energy HVAC templates (when return_object=false or identifier is "
            "omitted) or create an IdealAirSystem, SHWSystem, or standards-template HVAC (allair, "
            "doas, heatcool). Pass system_type='IdealAirSystem' for IdealAirSystem, "
            "system_type='SHWSystem' for Service Hot Water systems (with optional equipment_type, "
            "heater_efficiency, ambient_condition, ambient_loss_coefficient), or pass a standards "
            "template such as PSZ, VAV, PTAC, FCUwithDOAS, Radiant, or VRF. Returns object_dict or "
            "a Garden Properties Library target for HB_Edit_Objects."
        ),
        tags={
            "energy",
            "hvac-template",
            "hvac",
            "ideal-air",
            "search",
            "standards",
            "author",
        },
        timeout=20,
    )
    def create_hvac_template(
        query: Annotated[
            str | None,
            Field(
                description="Optional search text such as 'ideal air', 'psz packaged single zone', 'vav', 'radiant doas', 'vrf', or 'shw'."
            ),
        ] = None,
        system_type: Annotated[
            str | None,
            Field(
                description="Optional exact HVAC/SHW type such as IdealAirSystem, SHWSystem, PSZ, VAV, PTAC, FCUwithDOAS, Radiant, or VRF."
            ),
        ] = None,
        family: Annotated[
            str | None,
            Field(description="Optional family filter: all, allair, doas, heatcool, ideal-air, or shw."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(
                description="Optional HVAC identifier. When provided with return_object=true and a unique template, creates the HVAC object."
            ),
        ] = None,
        vintage: Annotated[
            str | None,
            Field(description="Optional standards template vintage, such as ASHRAE_2019."),
        ] = None,
        equipment_type: Annotated[
            str | None,
            Field(description="Optional standards equipment_type for the selected HVAC template."),
        ] = None,
        economizer_type: Annotated[
            str | None,
            Field(description="Optional economizer type (for IdealAirSystem: NoEconomizer, DifferentialDryBulb, or DifferentialEnthalpy)."),
        ] = None,
        sensible_heat_recovery: Annotated[
            float | None,
            Field(ge=0.0, le=1.0, description="Optional sensible heat recovery effectiveness from 0 to 1."),
        ] = None,
        latent_heat_recovery: Annotated[
            float | None,
            Field(ge=0.0, le=1.0, description="Optional latent heat recovery effectiveness from 0 to 1."),
        ] = None,
        demand_controlled_ventilation: Annotated[
            bool | None,
            Field(description="Optional demand controlled ventilation flag."),
        ] = None,
        doas_availability_schedule: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | str | None,
            Field(description="Optional DOAS availability schedule dict, Garden target, or library identifier."),
        ] = None,
        radiant_type: Annotated[
            str | None,
            Field(description="Optional radiant type for radiant templates, such as Floor or Ceiling."),
        ] = None,
        minimum_operation_time: Annotated[
            float | None,
            Field(ge=0.0, description="Optional radiant minimum operation time in hours."),
        ] = None,
        switch_over_time: Annotated[
            float | None,
            Field(ge=0.0, description="Optional radiant switch-over time in hours."),
        ] = None,
        heating_air_temperature: Annotated[
            float | None,
            Field(description="Optional IdealAirSystem maximum heating supply air temperature in C (> cooling_air_temperature; omit for simple HVAC)."),
        ] = None,
        cooling_air_temperature: Annotated[
            float | None,
            Field(description="Optional IdealAirSystem minimum cooling supply air temperature in C (< heating_air_temperature; omit for simple HVAC)."),
        ] = None,
        heating_limit: Annotated[
            float | str | None,
            Field(description="Optional IdealAirSystem heating capacity in W, 'autosize', or 'no_limit'."),
        ] = None,
        cooling_limit: Annotated[
            float | str | None,
            Field(description="Optional IdealAirSystem cooling capacity in W, 'autosize', or 'no_limit'."),
        ] = None,
        heating_availability: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | str | None,
            Field(description="Optional IdealAirSystem heating availability schedule dict, Garden target, or library identifier."),
        ] = None,
        cooling_availability: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | str | None,
            Field(description="Optional IdealAirSystem cooling availability schedule dict, Garden target, or library identifier."),
        ] = None,
        heater_efficiency: Annotated[
            float | str | None,
            Field(description="Optional SHWSystem heater efficiency/COP or 'autocalculate' when system_type='SHWSystem'."),
        ] = None,
        ambient_condition: Annotated[
            float | str | None,
            Field(description="Optional SHWSystem ambient temperature [C] or Room identifier when system_type='SHWSystem'."),
        ] = None,
        ambient_loss_coefficient: Annotated[
            float | None,
            Field(ge=0.0, description="Optional SHWSystem tank ambient loss coefficient [W/K] when system_type='SHWSystem'."),
        ] = None,
        return_object: Annotated[
            bool,
            Field(description="Set false to search templates without creating an object even when identifier is supplied."),
        ] = True,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="Include the full SDK object_dict in the response (set false with garden_root for compact target responses)."),
        ] = True,
        limit: Annotated[
            int,
            Field(ge=1, description="Maximum number of template search matches to return."),
        ] = 10,
    ) -> MutationResultModel:
        """Search HVAC templates or create IdealAirSystem, SHWSystem, or standards HVAC."""
        from garden.energy.hvac import create_hvac_template as service

        return validate_output(
            MutationResultModel,
            service(
                query=query,
                system_type=system_type,
                family=family,
                identifier=identifier,
                vintage=vintage,
                equipment_type=equipment_type,
                economizer_type=economizer_type,
                sensible_heat_recovery=sensible_heat_recovery,
                latent_heat_recovery=latent_heat_recovery,
                demand_controlled_ventilation=demand_controlled_ventilation,
                doas_availability_schedule=dump_input(doas_availability_schedule),
                radiant_type=radiant_type,
                minimum_operation_time=minimum_operation_time,
                switch_over_time=switch_over_time,
                heating_air_temperature=heating_air_temperature,
                cooling_air_temperature=cooling_air_temperature,
                heating_limit=heating_limit,
                cooling_limit=cooling_limit,
                heating_availability=dump_input(heating_availability),
                cooling_availability=dump_input(cooling_availability),
                heater_efficiency=heater_efficiency,
                ambient_condition=ambient_condition,
                ambient_loss_coefficient=ambient_loss_coefficient,
                return_object=return_object,
                garden_root=garden_root,
                return_object_dict=return_object_dict,
                limit=limit,
            ),
        )

    @mcp.tool(
        name="EP_Create_PV_Or_Load_Center",
        description=(
            "Create Honeybee Energy PVProperties (for shade-attached photovoltaic generation via "
            "HB_Edit_Objects (pv_properties) or ElectricLoadCenter (for model-level inverter "
            "efficiency and DC-to-AC sizing via HB_Edit_Model.electric_load_center). Pass "
            "object_type='pv_properties' or 'electric_load_center' and optional settings in "
            "params."
        ),
        tags={
            "energy",
            "model",
            "pv",
            "load-center",
            "author",
        },
        timeout=20,
    )
    def create_pv_or_load_center(
        object_type: Annotated[
            PVOrLoadCenterType,
            Field(description="Target object family: pv_properties or electric_load_center."),
        ],
        identifier: Annotated[
            str | None,
            Field(
                description="Identifier for the object or Garden Properties Library target (required for pv_properties; defaults to 'electric_load_center' for electric_load_center)."
            ),
        ] = None,
        params: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Object-specific settings (for pv_properties: rated_efficiency, "
                    "active_area_fraction, module_type, mounting_type, system_loss_fraction, "
                    "tracking_ground_coverage_ratio; for electric_load_center: inverter_efficiency, "
                    "inverter_dc_to_ac_size_ratio)."
                )
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="When garden_root is provided, set false to return only compact target and summary."),
        ] = True,
    ) -> MutationResultModel:
        """Create Honeybee Energy PVProperties or ElectricLoadCenter."""
        from garden.energy.ventilation import create_pv_or_load_center as service

        return validate_output(
            MutationResultModel,
            service(
                object_type=object_type,
                identifier=identifier,
                params=dump_input(params),
                garden_root=garden_root,
                return_object_dict=return_object_dict,
            ),
        )

    @mcp.tool(
        name="EP_Setup_Room_Energy_Controls",
        description=(
            "Configure or clear room-level Honeybee Energy controls on a Garden model via "
            "control_type: simple_ventilation (operable-window/door VentilationOpening and "
            "window_vent_control, with optional aperture/door filtering and schedule), "
            "airflow_network (EnergyPlus AirflowNetwork cracks and openings), or "
            "daylighting_control (EnergyPlus DaylightingControl reference sensors at room center "
            "or custom sensor_position). Pass control-specific options in params or set clear=true "
            "to remove the selected controls. Returns the updated Honeybee model target in target "
            "and summary_view.target plus persistence_receipt and report."
        ),
        tags={
            "energy",
            "edit",
            "room",
            "ventilation",
            "airflow-network",
            "daylighting-control",
        },
        timeout=30,
    )
    def setup_room_energy_controls(
        control_type: Annotated[
            RoomEnergyControlType,
            Field(
                description="Control family: simple_ventilation, airflow_network, or daylighting_control."
            ),
        ],
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Optional Honeybee model target. Defaults to the Garden base model."),
        ] = None,
        room_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional room identifiers to update (mutually exclusive with room_targets). Omit both to target all Rooms."),
        ] = None,
        room_targets: Annotated[
            list[BuildingObjectTargetRef] | None,
            Field(description="Optional Honeybee Room typed targets from HB_Search_Model_Objects (mutually exclusive with room_identifiers)."),
        ] = None,
        clear: Annotated[
            bool,
            Field(
                description=(
                    "When true, clear the selected control_type properties (window_vent_control/"
                    "vent_opening for simple_ventilation; ventilation_simulation_control/vent_crack "
                    "for airflow_network; daylighting_control for daylighting_control)."
                )
            ),
        ] = False,
        params: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Control-specific parameters (for simple_ventilation: aperture_identifiers, "
                    "aperture_targets, door_identifiers, door_targets, fraction_area_operable, "
                    "fraction_height_operable, discharge_coefficient, wind_cross_vent, temperature "
                    "thresholds, schedule; for airflow_network: vent_control_type, leakage_type, "
                    "use_room_infiltration, reference conditions, building_type; for "
                    "daylighting_control: sensor_position ([x, y, z] or {x, y, z}), "
                    "distance_from_floor, illuminance_setpoint, control_fraction, min_power_input, "
                    "min_light_output, off_at_minimum, tolerance)."
                )
            ),
        ] = None,
    ) -> MutationResultModel:
        """Configure or clear room-level ventilation, AirflowNetwork, or daylighting controls."""
        from garden.energy.ventilation import setup_room_energy_controls as service

        return validate_output(
            MutationResultModel,
            service(
                control_type=control_type,
                garden_root=garden_root,
                model_target=dump_target(model_target),
                room_identifiers=room_identifiers,
                room_targets=dump_targets(room_targets),
                clear=clear,
                params=dump_input(params),
            ),
        )
