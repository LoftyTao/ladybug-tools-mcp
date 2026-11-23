"""energy MCP tools."""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register energy tools."""

    @mcp.tool(
        name="EP_Create_Air_Boundary_Construction",
        description="Create a Honeybee Energy AirBoundaryConstruction for air-boundary Faces, the EnergyPlus-adjacent construction used for interior air mixing across a face instead of an opaque heat-transfer layer. Returns object_dict plus summary_view, or a Garden Properties Library target with persistence_receipt when garden_root is provided and return_object_dict=false.",
        tags={
            "energy",
            "construction",
            "air-boundary",
            "face",
            "author",
        },
        timeout=20,
    )
    def create_air_boundary_construction(
        identifier: Annotated[
            str, Field(description="AirBoundaryConstruction identifier.")
        ],
        air_mixing_per_area: Annotated[
            float, Field(description="Air mixing per area in m3/s-m2.")
        ] = 0.1,
        air_mixing_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional ScheduleRuleset dict, Garden Properties Library target, or standards library identifier controlling air mixing."),
        ] = None,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key property values; full keeps the same concise fields for this scalar construction."
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
                description="Return the full construction object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy AirBoundaryConstruction object."""
        from garden.energy.constructionsets import (
            create_air_boundary_construction as service,
        )

        return service(
            identifier=identifier,
            air_mixing_per_area=air_mixing_per_area,
            air_mixing_schedule=air_mixing_schedule,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Aperture_Construction_Set",
        description="Create a Honeybee Energy ApertureConstructionSet intermediate object for ConstructionSet aperture slots: fixed exterior windows, interior apertures, skylights, and operable windows. Pass WindowConstruction object_dict values, Garden Properties Library targets, or standards identifiers. Returns object_dict plus summary_view slot values; this subset is not saved as its own Garden target, so pass the returned object_dict into EP_Create_Construction_Set.aperture_set.",
        tags={
            "energy",
            "construction-set",
            "construction",
            "aperture",
            "window",
            "skylight",
            "operable-window",
            "author",
        },
        timeout=20,
    )
    def create_aperture_construction_set(
        window_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="WindowConstruction dict, Garden target, or standards identifier for fixed exterior windows in wall apertures."
            ),
        ] = None,
        interior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="WindowConstruction dict, Garden target, or standards identifier for interior apertures with Surface boundary conditions."
            ),
        ] = None,
        skylight_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="WindowConstruction dict, Garden target, or standards identifier for skylights in roof/ceiling or floor parent faces."
            ),
        ] = None,
        operable_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="WindowConstruction dict, Garden target, or standards identifier for operable exterior windows."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually GD_Create['garden_root']; used only to resolve Garden construction targets in the slot inputs."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy ApertureConstructionSet object."""
        from garden.energy.constructionsets import (
            create_aperture_construction_set as service,
        )

        return service(
            window_construction=window_construction,
            interior_construction=interior_construction,
            skylight_construction=skylight_construction,
            operable_construction=operable_construction,
            garden_root=garden_root,
        )

    @mcp.tool(
        name="EP_Create_Construction_Set",
        description='Create a saved Honeybee Energy ConstructionSet, the envelope default set for wall, floor, roof/ceiling, aperture, door, shade, and air-boundary constructions. Start from a standards-library or Garden base ConstructionSet, then pass subset object_dict overrides or direct construction targets for common slots. Returns object_dict plus summary_view, or saved target plus persistence_receipt when garden_root and return_object_dict=false are supplied; use EP_Create_Window_Construction first for low-U, SHGC, or visible-transmittance window requests.',
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
            dict[str, Any] | str | None,
            Field(
                description="Optional base ConstructionSet object_dict, Garden target, or standards-library identifier such as a generic construction set."
            ),
        ] = None,
        wall_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional WallConstructionSet object_dict override, or OpaqueConstruction dict/Garden target/standards identifier to wrap as the exterior wall slot."
            ),
        ] = None,
        floor_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional FloorConstructionSet object_dict override, or OpaqueConstruction dict/Garden target/standards identifier to wrap as the exterior floor slot."
            ),
        ] = None,
        roof_ceiling_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional RoofCeilingConstructionSet object_dict override, or OpaqueConstruction dict/Garden target/standards identifier to wrap as the exterior roof slot."
            ),
        ] = None,
        aperture_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional ApertureConstructionSet object_dict override, or WindowConstruction dict, Garden target, or standards identifier to wrap as the exterior fixed-window slot."
            ),
        ] = None,
        door_set: Annotated[
            dict[str, Any] | None,
            Field(description="Optional DoorConstructionSet object_dict override; door subset tools return object_dict values rather than Garden targets."),
        ] = None,
        shade_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional ShadeConstruction dict, Garden target, or library identifier override."
            ),
        ] = None,
        air_boundary_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional AirBoundaryConstruction or OpaqueConstruction dict, Garden target, or library identifier override."
            ),
        ] = None,
        return_detail: Annotated[
            str,
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
                description="Return the full ConstructionSet object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy ConstructionSet object."""
        from garden.energy.constructionsets import create_construction_set as service

        return service(
            identifier=identifier,
            base_construction_set=base_construction_set,
            wall_set=wall_set,
            floor_set=floor_set,
            roof_ceiling_set=roof_ceiling_set,
            aperture_set=aperture_set,
            door_set=door_set,
            shade_construction=shade_construction,
            air_boundary_construction=air_boundary_construction,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Custom_Window_Gas_Material",
        description=(
            'Create a Honeybee Energy EnergyWindowMaterialGasCustom gap layer for window '
            'construction assemblies when built-in gas types are not enough. Returns object_dict '
            "plus summary_view; return_detail='full' also includes a material property matrix."
        ),
        tags={
            "energy",
            "construction",
            "material",
            "author",
            "window-layer",
        },
        timeout=20,
    )
    def create_custom_window_gas_material(
        identifier: Annotated[
            str, Field(description="Custom EnergyWindowMaterialGasCustom identifier for a window gas gap layer.")
        ],
        thickness: Annotated[float, Field(description="Gas gap thickness in meters.")],
        conductivity_coeff_a: Annotated[
            float, Field(description="Conductivity A coefficient.")
        ],
        viscosity_coeff_a: Annotated[
            float, Field(description="Viscosity A coefficient.")
        ],
        specific_heat_coeff_a: Annotated[
            float, Field(description="Specific heat A coefficient.")
        ],
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key material values; full also returns a property_matrix with SDK property rows."
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
                description="Return the full material object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy EnergyWindowMaterialGasCustom object."""
        from garden.energy.constructionsets import (
            create_custom_window_gas_material as service,
        )

        return service(
            identifier=identifier,
            thickness=thickness,
            conductivity_coeff_a=conductivity_coeff_a,
            viscosity_coeff_a=viscosity_coeff_a,
            specific_heat_coeff_a=specific_heat_coeff_a,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Door_Construction_Set",
        description="Create a Honeybee Energy DoorConstructionSet intermediate object for ConstructionSet door slots: exterior/interior opaque doors, exterior/interior glass doors, and overhead doors. Pass OpaqueConstruction or WindowConstruction object_dict values, Garden targets, or standards identifiers as appropriate. Returns object_dict plus summary_view slot values; this subset is not saved as its own Garden target, so pass the returned object_dict into EP_Create_Construction_Set.door_set.",
        tags={
            "energy",
            "construction-set",
            "construction",
            "door",
            "window",
            "author",
        },
        timeout=20,
    )
    def create_door_construction_set(
        exterior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for exterior opaque doors."
            ),
        ] = None,
        interior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for interior opaque doors."
            ),
        ] = None,
        exterior_glass_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="WindowConstruction dict, Garden target, or standards identifier for exterior glass doors."
            ),
        ] = None,
        interior_glass_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="WindowConstruction dict, Garden target, or standards identifier for interior glass doors."
            ),
        ] = None,
        overhead_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for overhead opaque doors in roof/ceiling or floor parent faces."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually GD_Create['garden_root']; used only to resolve Garden construction targets in the slot inputs."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy DoorConstructionSet object."""
        from garden.energy.constructionsets import (
            create_door_construction_set as service,
        )

        return service(
            exterior_construction=exterior_construction,
            interior_construction=interior_construction,
            exterior_glass_construction=exterior_glass_construction,
            interior_glass_construction=interior_glass_construction,
            overhead_construction=overhead_construction,
            garden_root=garden_root,
        )

    @mcp.tool(
        name="EP_Create_Electric_Equipment",
        description=(
            'Create a Honeybee Energy ElectricEquipment internal-gains load from equipment power '
            'density and an optional fractional schedule. The schedule accepts an object_dict, '
            'Garden schedule target, or standards identifier. Use garden_root to save a Garden '
            'Properties Library load target and pass target to '
            'EP_Create_Program_Type.electric_equipment; set return_object_dict=false for a '
            'compact target/summary/receipt response.'
        ),
        tags={
            "author",
            "energy",
            "electric-equipment",
            "electric",
            "internal-gains",
            "program-type",
            "load",
        },
        timeout=20,
    )
    def create_electric_equipment(
        identifier: Annotated[
            str, Field(description="ElectricEquipment object identifier.")
        ],
        watts_per_area: Annotated[
            float, Field(description="Electric equipment power density in W/m2.")
        ],
        schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional fractional equipment schedule as a Honeybee Energy schedule object_dict, Garden schedule target, or standards-library identifier."
            ),
        ] = None,
        radiant_fraction: Annotated[
            float | None,
            Field(description="Optional 0-1 radiant fraction of equipment heat gain."),
        ] = None,
        latent_fraction: Annotated[
            float | None,
            Field(description="Optional 0-1 latent fraction of equipment heat gain."),
        ] = None,
        lost_fraction: Annotated[
            float | None,
            Field(
                description="Optional 0-1 fraction of equipment load lost outside the zone and HVAC system, such as directly exhausted heat."
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
                description="Return the full load object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy ElectricEquipment object."""
        from garden.energy.programtypes import create_electric_equipment as service

        return service(
            identifier=identifier,
            watts_per_area=watts_per_area,
            schedule=schedule,
            radiant_fraction=radiant_fraction,
            latent_fraction=latent_fraction,
            lost_fraction=lost_fraction,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Electric_Load_Center",
        description=(
            'Create Honeybee Energy ElectricLoadCenter model-level settings for photovoltaic '
            'inverter efficiency and DC-to-AC sizing. Use this with EP_Create_PV_Properties on '
            'Honeybee Shades, then assign the saved electric_load_center target through '
            'HB_Edit_Model.electric_load_center.'
        ),
        tags={
            "energy",
            "model",
            "author",
            "load-center",
        },
        timeout=20,
    )
    def create_electric_load_center(
        identifier: Annotated[
            str,
            Field(description="Identifier used for the Garden Properties Library target. The Honeybee ElectricLoadCenter object itself is model-level and has no identifier."),
        ] = "electric_load_center",
        inverter_efficiency: Annotated[
            float,
            Field(description="Inverter nominal DC-to-AC conversion efficiency from 0 to 1."),
        ] = 0.96,
        inverter_dc_to_ac_size_ratio: Annotated[
            float,
            Field(description="Ratio of inverter DC rated size to AC rated size."),
        ] = 1.1,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="When garden_root is provided, set false to return only compact target and summary."),
        ] = True,
    ) -> dict:
        """Create electric load center settings."""
        from garden.energy.ventilation import create_electric_load_center as service

        return service(
            identifier=identifier,
            inverter_efficiency=inverter_efficiency,
            inverter_dc_to_ac_size_ratio=inverter_dc_to_ac_size_ratio,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Floor_Construction_Set",
        description="Create a Honeybee Energy FloorConstructionSet intermediate object for ConstructionSet floor slots: exterior-exposed floors, interior floors, and ground-contact slabs. Pass OpaqueConstruction object_dict values, Garden targets, or standards identifiers. Returns object_dict plus summary_view slot values; this subset is not saved as its own Garden target, so pass the returned object_dict into EP_Create_Construction_Set.floor_set.",
        tags={
            "energy",
            "construction-set",
            "construction",
            "floor",
            "author",
        },
        timeout=20,
    )
    def create_floor_construction_set(
        exterior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for exterior-exposed floors."
            ),
        ] = None,
        interior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for interior floors."
            ),
        ] = None,
        ground_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for ground-contact floor slabs."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually GD_Create['garden_root']; used only to resolve Garden construction targets in the slot inputs."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy FloorConstructionSet object."""
        from garden.energy.constructionsets import (
            create_floor_construction_set as service,
        )

        return service(
            exterior_construction=exterior_construction,
            interior_construction=interior_construction,
            ground_construction=ground_construction,
            garden_root=garden_root,
        )

    @mcp.tool(
        name="EP_Create_Gas_Equipment",
        description=(
            'Create a Honeybee Energy GasEquipment internal-gains load from fuel equipment power '
            'density and an optional fractional schedule. The schedule accepts an object_dict, '
            'Garden schedule target, or standards identifier. Use garden_root to save a Garden '
            'Properties Library load target and pass target to '
            'EP_Create_Program_Type.gas_equipment; set return_object_dict=false for a compact '
            'target/summary/receipt response.'
        ),
        tags={
            "author",
            "energy",
            "gas-equipment",
            "internal-gains",
            "program-type",
            "load",
        },
        timeout=20,
    )
    def create_gas_equipment(
        identifier: Annotated[
            str, Field(description="GasEquipment object identifier.")
        ],
        watts_per_area: Annotated[
            float, Field(description="Gas equipment power density in W/m2.")
        ],
        schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional fractional gas equipment schedule as a Honeybee Energy schedule object_dict, Garden schedule target, or standards-library identifier."
            ),
        ] = None,
        radiant_fraction: Annotated[
            float | None,
            Field(description="Optional 0-1 radiant fraction of gas equipment heat gain."),
        ] = None,
        latent_fraction: Annotated[
            float | None,
            Field(description="Optional 0-1 latent fraction of gas equipment heat gain."),
        ] = None,
        lost_fraction: Annotated[
            float | None,
            Field(
                description="Optional 0-1 fraction of gas equipment load lost outside the zone and HVAC system, such as directly exhausted heat."
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
                description="Return the full load object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy GasEquipment object."""
        from garden.energy.programtypes import create_gas_equipment as service

        return service(
            identifier=identifier,
            watts_per_area=watts_per_area,
            schedule=schedule,
            radiant_fraction=radiant_fraction,
            latent_fraction=latent_fraction,
            lost_fraction=lost_fraction,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Ideal_Air_System",
        description=(
            'Create a Honeybee Energy IdealAirSystem HVAC object for simple ideal-loads '
            'conditioning and early-stage room energy properties. Returns a full object_dict, or '
            'saves to Garden Properties Library and returns a target plus persistence_receipt '
            'when garden_root is provided and return_object_dict=false. For simple HVAC, omit '
            'heating_air_temperature and cooling_air_temperature; they are supply air '
            'temperatures, not room setpoints.'
        ),
        tags={
            "energy",
            "hvac-template",
            "hvac",
            "ideal-air",
            "author",
        },
        timeout=20,
    )
    def create_ideal_air_system(
        identifier: Annotated[str, Field(description="IdealAirSystem identifier.")],
        economizer_type: Annotated[
            str | None,
            Field(
                description="Optional economizer type: NoEconomizer, DifferentialDryBulb, or DifferentialEnthalpy."
            ),
        ] = None,
        demand_controlled_ventilation: Annotated[
            bool | None,
            Field(description="Optional demand controlled ventilation flag."),
        ] = None,
        sensible_heat_recovery: Annotated[
            float | None,
            Field(
                description="Optional sensible heat recovery effectiveness from 0 to 1."
            ),
        ] = None,
        latent_heat_recovery: Annotated[
            float | None,
            Field(
                description="Optional latent heat recovery effectiveness from 0 to 1."
            ),
        ] = None,
        heating_air_temperature: Annotated[
            float | None,
            Field(
                description="Optional maximum heating supply air temperature in C. Must be greater than cooling_air_temperature_; omit for simple HVAC."
            ),
        ] = None,
        cooling_air_temperature: Annotated[
            float | None,
            Field(
                description="Optional minimum cooling supply air temperature in C. Must be less than heating_air_temperature_; omit for simple HVAC."
            ),
        ] = None,
        heating_limit: Annotated[
            float | str | None,
            Field(
                description="Optional heating capacity in W, 'autosize', or 'no_limit'."
            ),
        ] = None,
        cooling_limit: Annotated[
            float | str | None,
            Field(
                description="Optional cooling capacity in W, 'autosize', or 'no_limit'."
            ),
        ] = None,
        heating_availability: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional heating availability schedule dict or library identifier."
            ),
        ] = None,
        cooling_availability: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional cooling availability schedule dict or library identifier."
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
                description=(
                    'Include the full SDK object_dict in the response (set false for compact '
                    'target responses).'
                )
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy IdealAirSystem HVAC object."""
        from garden.energy.hvac import create_ideal_air_system as service

        return service(
            identifier=identifier,
            economizer_type=economizer_type,
            demand_controlled_ventilation=demand_controlled_ventilation,
            sensible_heat_recovery=sensible_heat_recovery,
            latent_heat_recovery=latent_heat_recovery,
            heating_air_temperature=heating_air_temperature,
            cooling_air_temperature=cooling_air_temperature,
            heating_limit=heating_limit,
            cooling_limit=cooling_limit,
            heating_availability=heating_availability,
            cooling_availability=cooling_availability,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Infiltration",
        description=(
            'Create a Honeybee Energy Infiltration load for uncontrolled outdoor air leakage '
            'through the envelope, using flow_per_exterior_area plus optional fractional schedule '
            'and EnergyPlus/BLAST/DOE2-style coefficients. The schedule accepts an object_dict, '
            'Garden schedule target, or standards identifier. Use garden_root to save a Garden '
            'Properties Library load target and pass target to '
            'EP_Create_Program_Type.infiltration; set return_object_dict=false for a compact '
            'target/summary/receipt response.'
        ),
        tags={
            "author",
            "energy",
            "envelope",
            "infiltration",
            "program-type",
            "load",
        },
        timeout=20,
    )
    def create_infiltration(
        identifier: Annotated[
            str, Field(description="Infiltration object identifier.")
        ],
        flow_per_exterior_area: Annotated[
            float,
            Field(
                description="Infiltration intensity in m3/s per exterior surface area."
            ),
        ],
        schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional fractional infiltration schedule as a Honeybee Energy schedule object_dict, Garden schedule target, or standards-library identifier."
            ),
        ] = None,
        constant_coefficient: Annotated[
            float | None,
            Field(description="Optional constant leakage coefficient; EnergyPlus default is 1 while BLAST/DOE2 use different reference coefficients."),
        ] = None,
        temperature_coefficient: Annotated[
            float | None,
            Field(description="Optional temperature-difference coefficient multiplied by indoor-outdoor delta C."),
        ] = None,
        velocity_coefficient: Annotated[
            float | None,
            Field(description="Optional wind velocity coefficient multiplied by exterior wind speed in m/s."),
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
                description="Return the full load object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy Infiltration object."""
        from garden.energy.programtypes import create_infiltration as service

        return service(
            identifier=identifier,
            flow_per_exterior_area=flow_per_exterior_area,
            schedule=schedule,
            constant_coefficient=constant_coefficient,
            temperature_coefficient=temperature_coefficient,
            velocity_coefficient=velocity_coefficient,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Lighting",
        description=(
            'Create a Honeybee Energy Lighting load object from lighting power density in '
            'watts_per_area and an optional schedule. Use garden_root and '
            'return_object_dict=false to save a load target for EP_Create_Program_Type.'
        ),
        tags={
            "energy",
            "program-type",
            "load",
            "lighting",
            "author",
        },
        timeout=20,
    )
    def create_lighting(
        identifier: Annotated[str, Field(description="Lighting object identifier.")],
        watts_per_area: Annotated[
            float, Field(description="Lighting power density in W/m2.")
        ],
        schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional lighting schedule dict or schedule library identifier."
            ),
        ] = None,
        return_air_fraction: Annotated[
            float | None,
            Field(description="Optional fraction of lighting load to zone return air."),
        ] = None,
        radiant_fraction: Annotated[
            float | None,
            Field(description="Optional radiant fraction of lighting load."),
        ] = None,
        visible_fraction: Annotated[
            float | None,
            Field(description="Optional visible fraction of lighting load."),
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
                description="Return the full load object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy Lighting object."""
        from garden.energy.programtypes import create_lighting as service

        return service(
            identifier=identifier,
            watts_per_area=watts_per_area,
            schedule=schedule,
            return_air_fraction=return_air_fraction,
            radiant_fraction=radiant_fraction,
            visible_fraction=visible_fraction,
            garden_root=garden_root if garden_root is not None else garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Opaque_Construction",
        description="Create a Honeybee Energy OpaqueConstruction, the complete layered assembly made from opaque thermal-mass or no-mass material layers ordered from outside to inside for walls, roofs, and floors. Material inputs can be object_dict values, Garden Properties Library targets, or Energy standards library identifiers. Use garden_root and return_object_dict=false to save a reusable construction target for ConstructionSet or Room energy assignments. Returns object_dict plus summary_view, or target plus persistence_receipt when saved.",
        tags={
            "energy",
            "construction",
            "material",
            "thermal-mass",
            "wall",
            "author",
        },
        timeout=20,
    )
    def create_opaque_construction(
        identifier: Annotated[str, Field(description="OpaqueConstruction identifier.")],
        materials: Annotated[
            list[dict[str, Any] | str],
            Field(
                description="Opaque material layers from outside to inside; each item may be a dict, Garden target, or standards library identifier."
            ),
        ],
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key property values; full also returns a layer_matrix with material rows."
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
                description="Return the full construction object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy OpaqueConstruction object."""
        from garden.energy.constructionsets import (
            create_opaque_construction as service,
        )

        return service(
            identifier=identifier,
            materials=materials,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Opaque_Material",
        description="Create a Honeybee Energy EnergyMaterial opaque material layer with thermal mass for OpaqueConstruction assemblies. Returns object_dict plus summary_view. Use return_detail='summary' for key thickness, conductivity, density, heat capacity, R-value, and U-value fields or 'full' for a matrix of material property values. Use garden_root and return_object_dict=false to save the material target for construction tools.",
        tags={
            "energy",
            "construction",
            "material",
            "thermal-mass",
            "author",
        },
        timeout=20,
    )
    def create_opaque_material(
        identifier: Annotated[str, Field(description="EnergyMaterial identifier.")],
        thickness: Annotated[float, Field(description="Layer thickness in meters.")],
        conductivity: Annotated[
            float, Field(description="Thermal conductivity in W/m-K.")
        ],
        density: Annotated[float, Field(description="Density in kg/m3.")],
        specific_heat: Annotated[float, Field(description="Specific heat in J/kg-K.")],
        roughness: Annotated[
            str, Field(description="EnergyPlus roughness label.")
        ] = "MediumRough",
        thermal_absorptance: Annotated[
            float, Field(description="Long-wave absorptance.")
        ] = 0.9,
        solar_absorptance: Annotated[
            float, Field(description="Solar absorptance.")
        ] = 0.7,
        visible_absorptance: Annotated[
            float | None, Field(description="Visible absorptance.")
        ] = None,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key material values; full also returns a property_matrix with SDK property rows."
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
                description="Return the full material object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy EnergyMaterial object."""
        from garden.energy.constructionsets import create_opaque_material as service

        return service(
            identifier=identifier,
            thickness=thickness,
            conductivity=conductivity,
            density=density,
            specific_heat=specific_heat,
            roughness=roughness,
            thermal_absorptance=thermal_absorptance,
            solar_absorptance=solar_absorptance,
            visible_absorptance=visible_absorptance,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Opaque_No_Mass_Material",
        description=(
            'Create a Honeybee Energy EnergyMaterialNoMass opaque material from an R-value for '
            'walls, roofs, floors, or other opaque construction layers. This returns a material '
            'layer for later use in an opaque construction. Returns object_dict plus '
            "summary_view; return_detail='full' also includes a material property matrix."
        ),
        tags={
            "energy",
            "construction",
            "material",
            "author",
            "opaque",
        },
        timeout=20,
    )
    def create_opaque_no_mass_material(
        identifier: Annotated[
            str, Field(description="Honeybee EnergyMaterialNoMass identifier for an opaque no-mass layer.")
        ],
        r_value: Annotated[float, Field(description="Thermal resistance in m2-K/W.")],
        roughness: Annotated[
            str, Field(description="EnergyPlus roughness label.")
        ] = "MediumRough",
        thermal_absorptance: Annotated[
            float, Field(description="Long-wave absorptance.")
        ] = 0.9,
        solar_absorptance: Annotated[
            float, Field(description="Solar absorptance.")
        ] = 0.7,
        visible_absorptance: Annotated[
            float | None, Field(description="Visible absorptance.")
        ] = None,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key material values; full also returns a property_matrix with SDK property rows."
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
                description="Return the full material object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy EnergyMaterialNoMass object."""
        from garden.energy.constructionsets import (
            create_opaque_no_mass_material as service,
        )

        return service(
            identifier=identifier,
            r_value=r_value,
            roughness=roughness,
            thermal_absorptance=thermal_absorptance,
            solar_absorptance=solar_absorptance,
            visible_absorptance=visible_absorptance,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_People",
        description=(
            'Create a Honeybee Energy People occupancy load object from people_per_area and '
            'optional occupancy/activity schedules. Occupancy schedules use Fractional type; '
            'activity_schedule accepts an Activity Level schedule in W/person (omit for default '
            'seated activity). Use garden_root and return_object_dict=false to save a load target '
            'for EP_Create_Program_Type.'
        ),
        tags={
            "energy",
            "program-type",
            "load",
            "occupancy",
            "author",
        },
        timeout=20,
    )
    def create_people(
        identifier: Annotated[str, Field(description="People object identifier.")],
        people_per_area: Annotated[
            float, Field(description="People density in people per square meter.")
        ],
        occupancy_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional occupancy schedule dict or schedule library identifier."
            ),
        ] = None,
        activity_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    'Optional Activity Level schedule dict or library identifier in W/person; '
                    'omit for default seated activity.'
                )
            ),
        ] = None,
        radiant_fraction: Annotated[
            float | None,
            Field(description="Optional radiant fraction of sensible heat."),
        ] = None,
        latent_fraction: Annotated[
            float | None,
            Field(
                description="Optional latent heat fraction. Omit to use SDK autocalculate."
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
                description="Return the full load object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy People object."""
        from garden.energy.programtypes import create_people as service

        return service(
            identifier=identifier,
            people_per_area=people_per_area,
            occupancy_schedule=occupancy_schedule,
            activity_schedule=activity_schedule,
            radiant_fraction=radiant_fraction,
            latent_fraction=latent_fraction,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Program_Type",
        description=(
            'Create a Honeybee Energy ProgramType, the room program bundle for occupancy, '
            'lighting, equipment, service hot water, infiltration, ventilation, and setpoints. '
            'ProgramType is an upstream Honeybee Energy abstraction that later expands to '
            'multiple EnergyPlus loads and schedules. Prefer Garden Properties Library targets '
            'from load creation tools with garden_root and return_object_dict=false. Returns '
            'object_dict, or target plus persistence_receipt when saved.'
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
            dict[str, Any] | str | None,
            Field(
                description="Optional base ProgramType dict, Garden Properties Library target, or ProgramType library identifier."
            ),
        ] = None,
        people: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional People object_dict or Garden Properties Library load target."
            ),
        ] = None,
        lighting: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Lighting object_dict or Garden Properties Library load target."
            ),
        ] = None,
        electric_equipment: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional ElectricEquipment object_dict or Garden Properties Library load target."
            ),
        ] = None,
        gas_equipment: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional GasEquipment object_dict or Garden Properties Library load target."
            ),
        ] = None,
        service_hot_water: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional ServiceHotWater object_dict or Garden Properties Library load target."
            ),
        ] = None,
        infiltration: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Infiltration object_dict or Garden Properties Library load target."
            ),
        ] = None,
        ventilation: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Ventilation object_dict or Garden Properties Library load target."
            ),
        ] = None,
        setpoint: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Setpoint object_dict or Garden Properties Library load target."
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
                description="Return the full ProgramType object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy ProgramType object."""
        from garden.energy.programtypes import create_program_type as service

        return service(
            identifier=identifier,
            base_program_type=base_program_type,
            people=people,
            lighting=lighting,
            electric_equipment=electric_equipment,
            gas_equipment=gas_equipment,
            service_hot_water=service_hot_water,
            infiltration=infiltration,
            ventilation=ventilation,
            setpoint=setpoint,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_PV_Properties",
        description=(
            "Create Honeybee Energy PVProperties for shade-attached "
            "photovoltaic electricity generation on Honeybee Shades. Use this "
            "for rated efficiency, active area fraction, mounting_type, and "
            "PVWatts-style shade generation; mounting_type must be "
            "FixedOpenRack, FixedRoofMounted, OneAxis, OneAxisBacktracking, or "
            "TwoAxis. Save the target for HB_Edit_Shade.pv_properties. "
            "Inverter efficiency and DC-to-AC sizing belong in "
            "EP_Create_Electric_Load_Center. Ironbug photovoltaic "
            "generators use the Ironbug (IB_*) tools."
        ),
        tags={
            "energy",
            "model",
            "author",
            "pv",
            "properties",
        },
        timeout=20,
    )
    def create_pv_properties(
        identifier: Annotated[
            str,
            Field(description="Unique Honeybee Energy PVProperties identifier for assigning photovoltaics to Shades."),
        ],
        rated_efficiency: Annotated[
            float,
            Field(description="PV module rated efficiency from 0 to 1."),
        ] = 0.15,
        active_area_fraction: Annotated[
            float,
            Field(description="Fraction of parent Shade area covered by active PV cells."),
        ] = 0.9,
        module_type: Annotated[
            str | None,
            Field(description="Optional module type: Standard, Premium, or ThinFilm. If omitted, SDK infers from efficiency."),
        ] = None,
        mounting_type: Annotated[
            str,
            Field(description=(
                'PV mounting type, for example FixedOpenRack, FixedRoofMounted, OneAxis, '
                'OneAxisBacktracking, or TwoAxis. Use FixedRoofMounted for roof-mounted PV.'
            )),
        ] = "FixedOpenRack",
        system_loss_fraction: Annotated[
            float,
            Field(description="Fraction of electricity output lost to soiling, wiring, mismatch, availability, age, and related losses."),
        ] = 0.14,
        tracking_ground_coverage_ratio: Annotated[
            float,
            Field(description="Ground coverage ratio for one-axis tracking PV arrays."),
        ] = 0.4,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="When garden_root is provided, set false to return only compact target and summary."),
        ] = True,
    ) -> dict:
        """Create PV properties."""
        from garden.energy.ventilation import create_pv_properties as service

        return service(
            identifier=identifier,
            rated_efficiency=rated_efficiency,
            active_area_fraction=active_area_fraction,
            module_type=module_type,
            mounting_type=mounting_type,
            system_loss_fraction=system_loss_fraction,
            tracking_ground_coverage_ratio=tracking_ground_coverage_ratio,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Roof_Ceiling_Construction_Set",
        description="Create a Honeybee Energy RoofCeilingConstructionSet intermediate object for ConstructionSet roof and ceiling slots: exterior roofs, interior ceilings, and underground roofs. Pass OpaqueConstruction object_dict values, Garden targets, or standards identifiers. Returns object_dict plus summary_view slot values; this subset is not saved as its own Garden target, so pass the returned object_dict into EP_Create_Construction_Set.roof_ceiling_set.",
        tags={
            "energy",
            "construction-set",
            "construction",
            "roof",
            "author",
        },
        timeout=20,
    )
    def create_roof_ceiling_construction_set(
        exterior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for exterior roofs."
            ),
        ] = None,
        interior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for interior ceilings."
            ),
        ] = None,
        ground_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for underground roofs."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually GD_Create['garden_root']; used only to resolve Garden construction targets in the slot inputs."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy RoofCeilingConstructionSet object."""
        from garden.energy.constructionsets import (
            create_roof_ceiling_construction_set as service,
        )

        return service(
            exterior_construction=exterior_construction,
            interior_construction=interior_construction,
            ground_construction=ground_construction,
            garden_root=garden_root,
        )

    @mcp.tool(
        name="EP_Create_Schedule_Day",
        description='Create a Honeybee Energy ScheduleDay, the single-day profile used inside ScheduleRule or ScheduleRuleset objects. If times is omitted, values must contain exactly one all-day constant value. If times is provided, values and times must have the same length and each time is the Ladybug value-begins-at time, not the EnergyPlus time-until convention. Returns object_dict plus summary_view only; this lightweight day schedule is not saved to Garden and has no target.',
        tags={
            "energy",
            "schedule",
            "schedule-day",
            "author",
        },
        timeout=20,
    )
    def create_schedule_day(
        identifier: Annotated[str, Field(description="ScheduleDay identifier.")],
        values: Annotated[
            list[float],
            Field(
                description="Numeric values for one day. Use one value when times is omitted; otherwise provide exactly one value for each value-begins-at time."
            ),
        ],
        times: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional Ladybug Time dictionaries or strings for value start times such as '09:00'. These are value-begins-at times, not EnergyPlus Schedule:Day time-until values."
            ),
        ] = None,
        interpolate: Annotated[
            bool,
            Field(
                description="Whether to linearly interpolate between schedule values."
            ),
        ] = False,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy ScheduleDay."""
        from garden.energy.schedules import create_schedule_day as service

        return service(
            identifier=identifier, values=values, times=times, interpolate=interpolate
        )

    @mcp.tool(
        name="EP_Create_Schedule_Rule",
        description='Create a Honeybee Energy ScheduleRule that applies one ScheduleDay to selected weekdays and optional Ladybug Date bounds. Use this for weekday/weekend, seasonal, or exception rules before assembling a ScheduleRuleset. Returns object_dict and summary_view for EP_Create_Schedule_Ruleset.schedule_rules; this rule is not saved as its own Garden target.',
        tags={
            "energy",
            "schedule",
            "schedule-rule",
            "weekday",
            "weekend",
            "author",
        },
        timeout=20,
    )
    def create_schedule_rule(
        schedule_day: Annotated[
            dict[str, Any],
            Field(
                description='ScheduleDay object_dict, usually returned by EP_Create_Schedule_Day; ScheduleRule cannot consume a saved target because ScheduleDay is not persisted separately.'
            ),
        ],
        apply_sunday: Annotated[
            bool, Field(description="Apply rule on Sunday.")
        ] = False,
        apply_monday: Annotated[
            bool, Field(description="Apply rule on Monday.")
        ] = False,
        apply_tuesday: Annotated[
            bool, Field(description="Apply rule on Tuesday.")
        ] = False,
        apply_wednesday: Annotated[
            bool, Field(description="Apply rule on Wednesday.")
        ] = False,
        apply_thursday: Annotated[
            bool, Field(description="Apply rule on Thursday.")
        ] = False,
        apply_friday: Annotated[
            bool, Field(description="Apply rule on Friday.")
        ] = False,
        apply_saturday: Annotated[
            bool, Field(description="Apply rule on Saturday.")
        ] = False,
        start_date: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Ladybug Date dict or string for the first date when this rule can apply."
            ),
        ] = None,
        end_date: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Ladybug Date dict or string for the last date when this rule can apply."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy ScheduleRule."""
        from garden.energy.schedules import create_schedule_rule as service

        return service(
            schedule_day=schedule_day,
            apply_sunday=apply_sunday,
            apply_monday=apply_monday,
            apply_tuesday=apply_tuesday,
            apply_wednesday=apply_wednesday,
            apply_thursday=apply_thursday,
            apply_friday=apply_friday,
            apply_saturday=apply_saturday,
            start_date=start_date,
            end_date=end_date,
        )

    @mcp.tool(
        name="EP_Create_Schedule_Ruleset",
        description="Create a Honeybee Energy ScheduleRuleset, the saved annual schedule resource assembled from a default ScheduleDay plus optional ScheduleRules, holiday, and design-day schedules. Use this for occupancy, lighting, equipment, setpoint, transmittance, or other annual schedules before ProgramType/load/Room property assignment. Returns object_dict, summary_view, and optional data; with garden_root it also returns target, persistence_receipt, and when include_data=true a data_target plus data_persistence_receipt.",
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
        identifier: Annotated[str, Field(description="ScheduleRuleset identifier.")],
        default_day_schedule: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Default ScheduleDay object_dict from EP_Create_Schedule_Day (or omit and '
                    'pass default_value).'
                )
            ),
        ] = None,
        schedule_rules: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    'Optional ScheduleRule object_dict rows ordered from highest to lowest '
                    'priority from EP_Create_Schedule_Rule (use rules for interval shorthand).'
                )
            ),
        ] = None,
        rules: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    'Optional interval shorthand rows. Each row must include start_time, '
                    "end_time, value, and a day filter such as days='weekdays', "
                    "weekdays='weekday', or apply_days as seven booleans Sunday through Saturday. "
                    'Converted into a real Honeybee ScheduleRule.'
                )
            ),
        ] = None,
        schedule_type_limit: Annotated[
            dict[str, Any] | str | None,
            Field(description="Optional ScheduleTypeLimit dict or standards-library identifier that constrains values and units."),
        ] = None,
        default_value: Annotated[
            float | None,
            Field(
                description=(
                    'Constant all-day default value used when default_day_schedule is omitted, '
                    'for example 0.0 for unoccupied hours.'
                )
            ),
        ] = None,
        summer_designday_schedule: Annotated[
            dict[str, Any] | None,
            Field(description="Optional summer design-day ScheduleDay object_dict."),
        ] = None,
        winter_designday_schedule: Annotated[
            dict[str, Any] | None,
            Field(description="Optional winter design-day ScheduleDay object_dict."),
        ] = None,
        holiday_schedule: Annotated[
            dict[str, Any] | None,
            Field(description="Optional holiday ScheduleDay object_dict."),
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
                description=(
                    'Return the full Ladybug DataCollection dict in data (set false with '
                    'garden_root to persist data_target/data_persistence_receipt).'
                )
            ),
        ] = True,
        data_analysis_period: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional Ladybug AnalysisPeriod dict or string for generated data. When provided, schedule data is generated at its timestep and filtered with Ladybug DataCollection.filter_by_analysis_period. It supplies timestep, date/time range, and leap-year settings."
            ),
        ] = None,
        data_timestep: Annotated[
            int,
            Field(
                description="DataCollection timestep, in steps per hour. Ignored when data_analysis_period is provided."
            ),
        ] = 1,
        data_start_date: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional DataCollection start date as Ladybug Date dict or string."
            ),
        ] = None,
        data_end_date: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional DataCollection end date as Ladybug Date dict or string."
            ),
        ] = None,
        data_start_dow: Annotated[
            str, Field(description="Day of week for the start date. Default: Sunday.")
        ] = "Sunday",
        data_holidays: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Optional holiday dates as Ladybug Date dicts or strings."
            ),
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
                description="Return the full ScheduleRuleset object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a complete Honeybee Energy ScheduleRuleset."""
        from garden.energy.schedules import create_schedule_ruleset as service

        return service(
            identifier=identifier,
            default_day_schedule=default_day_schedule,
            schedule_rules=schedule_rules,
            rules=rules,
            schedule_type_limit=schedule_type_limit,
            default_value=default_value,
            summer_designday_schedule=summer_designday_schedule,
            winter_designday_schedule=winter_designday_schedule,
            holiday_schedule=holiday_schedule,
            include_data=include_data,
            data_analysis_period=data_analysis_period,
            data_timestep=data_timestep,
            data_start_date=data_start_date,
            data_end_date=data_end_date,
            data_start_dow=data_start_dow,
            data_holidays=data_holidays,
            data_leap_year=data_leap_year,
            garden_root=garden_root,
            return_data=return_data,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Service_Hot_Water",
        description=(
            'Create a Honeybee Energy ServiceHotWater demand load from floor-area hot water use, '
            'optional fractional schedule, tap target temperature, and sensible/latent fractions. '
            'Use it as the program-type domestic hot water demand companion to ventilation, '
            'infiltration, thermostat, and humidistat loads. The schedule accepts an object_dict, '
            'Garden schedule target, or standards identifier. Use garden_root to save a Garden '
            'Properties Library load target and pass target to '
            'EP_Create_Program_Type.service_hot_water; set return_object_dict=false for a compact '
            'target/summary/receipt response.'
        ),
        tags={
            "author",
            "energy",
            "hot-water",
            "program-type",
            "load",
            "service-hot-water",
        },
        timeout=20,
    )
    def create_service_hot_water(
        identifier: Annotated[
            str, Field(description="ServiceHotWater object identifier.")
        ],
        flow_per_area: Annotated[
            float, Field(description="Hot water flow per floor area in L/h-m2.")
        ],
        schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional fractional hot water use schedule as a Honeybee Energy schedule object_dict, Garden schedule target, or standards-library identifier."
            ),
        ] = None,
        target_temperature: Annotated[
            float | None,
            Field(description="Optional target tap water temperature in Celsius after mixing with mains water."),
        ] = None,
        sensible_fraction: Annotated[
            float | None,
            Field(description="Optional 0-1 fraction of hot water load released as sensible heat in the zone."),
        ] = None,
        latent_fraction: Annotated[
            float | None,
            Field(description="Optional 0-1 fraction of hot water load released as latent heat in the zone."),
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
                description="Return the full load object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy ServiceHotWater object."""
        from garden.energy.programtypes import create_service_hot_water as service

        return service(
            identifier=identifier,
            flow_per_area=flow_per_area,
            schedule=schedule,
            target_temperature=target_temperature,
            sensible_fraction=sensible_fraction,
            latent_fraction=latent_fraction,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Setpoint",
        description=(
            'Create a Honeybee Energy Setpoint thermostat/humidistat resource from heating and '
            'cooling schedules, or from numeric Celsius heating_setpoint and cooling_setpoint '
            'values that become constant schedules. Use it as the program-type thermostat '
            'companion to ventilation, infiltration, and service hot water demand loads. '
            'Schedules accept object_dicts, Garden schedule targets, or standards identifiers. '
            'Use garden_root to save a Garden Properties Library load target and pass target to '
            'EP_Create_Program_Type.setpoint or HB_Edit_Room.setpoint; set '
            'return_object_dict=false for a compact target/summary/receipt response.'
        ),
        tags={
            "author",
            "energy",
            "humidistat",
            "program-type",
            "setpoint",
            "thermostat",
        },
        timeout=20,
    )
    def create_setpoint(
        identifier: Annotated[
            str,
            Field(
                description="Setpoint object identifier (defaults to 'agent_setpoint')."
            ),
        ] = "agent_setpoint",
        heating_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Heating setpoint schedule as a Honeybee Energy schedule object_dict, Garden schedule target, or standards-library identifier. Optional when heating_setpoint is provided."
            ),
        ] = None,
        cooling_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Cooling setpoint schedule as a Honeybee Energy schedule object_dict, Garden schedule target, or standards-library identifier. Optional when cooling_setpoint is provided."
            ),
        ] = None,
        humidifying_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional humidifying setpoint schedule as a Honeybee Energy schedule object_dict, Garden schedule target, or standards-library identifier."
            ),
        ] = None,
        dehumidifying_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional dehumidifying setpoint schedule as a Honeybee Energy schedule object_dict, Garden schedule target, or standards-library identifier."
            ),
        ] = None,
        heating_setpoint: Annotated[
            float | None,
            Field(
                description="Optional constant heating thermostat setpoint in Celsius. When provided without heating_schedule, the tool creates a constant ScheduleRuleset."
            ),
        ] = None,
        cooling_setpoint: Annotated[
            float | None,
            Field(
                description="Optional constant cooling thermostat setpoint in Celsius. When provided without cooling_schedule, the tool creates a constant ScheduleRuleset."
            ),
        ] = None,
        setpoint_cutout_difference: Annotated[
            float,
            Field(
                description="Optional positive Celsius temperature difference between thermostat setpoint and cutout for throttling range control."
            ),
        ] = 0,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description=(
                    'Include the full SDK object_dict in the response (set false for compact '
                    'target responses).'
                )
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy Setpoint object."""
        from garden.energy.programtypes import create_setpoint as service

        return service(
            identifier=identifier,
            heating_schedule=heating_schedule,
            cooling_schedule=cooling_schedule,
            humidifying_schedule=humidifying_schedule,
            dehumidifying_schedule=dehumidifying_schedule,
            heating_setpoint=heating_setpoint,
            cooling_setpoint=cooling_setpoint,
            setpoint_cutout_difference=setpoint_cutout_difference,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Shade_Construction",
        description=(
            'Create a Honeybee Energy ShadeConstruction for outdoor Honeybee Shade energy '
            'properties. This sets reflectance and specular behavior for an energy construction. '
            'Returns object_dict plus summary_view with the scalar property values.'
        ),
        tags={
            "energy",
            "construction",
            "material",
            "author",
            "shade",
        },
        timeout=20,
    )
    def create_shade_construction(
        identifier: Annotated[str, Field(description="Honeybee ShadeConstruction identifier for an Energy shade surface.")],
        solar_reflectance: Annotated[
            float, Field(description="Solar reflectance.")
        ] = 0.2,
        visible_reflectance: Annotated[
            float, Field(description="Visible reflectance.")
        ] = 0.2,
        is_specular: Annotated[
            bool, Field(description="Whether reflection is specular.")
        ] = False,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key property values; full keeps the same concise fields for this scalar construction."
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
                description="Return the full construction object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy ShadeConstruction object."""
        from garden.energy.constructionsets import (
            create_shade_construction as service,
        )

        return service(
            identifier=identifier,
            solar_reflectance=solar_reflectance,
            visible_reflectance=visible_reflectance,
            is_specular=is_specular,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Simple_Glazing_Material",
        description="Create a Honeybee Energy EnergyWindowMaterialSimpleGlazSys material for a full simplified glazing system using U-factor, SHGC, and visible transmittance. It must be the only layer in a WindowConstruction; use EP_Create_Window_Construction with u_factor, shgc, and vt when the user wants a complete reusable window construction target. Returns object_dict plus summary_view, or a saved material target when garden_root is provided and return_object_dict=false.",
        tags={
            "energy",
            "construction",
            "material",
            "window",
            "glazing",
            "u-factor",
            "shgc",
            "author",
        },
        timeout=20,
    )
    def create_simple_glazing_material(
        identifier: Annotated[
            str, Field(description="Simple glazing material identifier.")
        ],
        u_factor: Annotated[
            float | None, Field(description="Glazing system U-factor in W/m2-K.")
        ] = None,
        shgc: Annotated[
            float | None, Field(description="Solar heat gain coefficient.")
        ] = None,
        vt: Annotated[float, Field(description="Visible transmittance.")] = 0.6,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key material values; full also returns a property_matrix with SDK property rows."
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
                description="Return the full material object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy EnergyWindowMaterialSimpleGlazSys object."""
        from garden.energy.constructionsets import (
            create_simple_glazing_material as service,
        )

        if u_factor is None:
            raise ValueError("u_factor is required.")
        if shgc is None:
            raise ValueError("shgc is required.")
        return service(
            identifier=identifier,
            u_factor=u_factor,
            shgc=shgc,
            vt=vt,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Vegetation_Material",
        description=(
            'Create a Honeybee Energy EnergyMaterialVegetation green-roof material layer for roof '
            'constructions. This describes roof soil and plant thermal properties. Returns '
            "object_dict plus summary_view; return_detail='full' also includes a material "
            'property matrix.'
        ),
        tags={
            "energy",
            "construction",
            "material",
            "author",
            "vegetation",
        },
        timeout=20,
    )
    def create_vegetation_material(
        identifier: Annotated[
            str, Field(description="Honeybee EnergyMaterialVegetation identifier for a vegetated roof layer.")
        ],
        thickness: Annotated[
            float,
            Field(
                ge=0.1,
                description=(
                    "Soil thickness in meters. OpenStudio RoofVegetation "
                    "requires at least 0.1 m."
                ),
            ),
        ] = 0.1,
        conductivity: Annotated[
            float, Field(description="Dry soil conductivity in W/m-K.")
        ] = 0.35,
        density: Annotated[
            float, Field(description="Dry soil density in kg/m3.")
        ] = 1100,
        specific_heat: Annotated[
            float, Field(description="Dry soil specific heat in J/kg-K.")
        ] = 1200,
        plant_height: Annotated[
            float, Field(description="Plant height in meters.")
        ] = 0.2,
        leaf_area_index: Annotated[float, Field(description="Leaf area index.")] = 1.0,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key material values; full also returns a property_matrix with SDK property rows."
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
                description="Return the full material object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy EnergyMaterialVegetation object."""
        from garden.energy.constructionsets import (
            create_vegetation_material as service,
        )

        return service(
            identifier=identifier,
            thickness=thickness,
            conductivity=conductivity,
            density=density,
            specific_heat=specific_heat,
            plant_height=plant_height,
            leaf_area_index=leaf_area_index,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Ventilation",
        description=(
            'Create a Honeybee Energy Ventilation load for purposeful design outdoor air using '
            'flow_per_person, flow_per_area, flow_per_zone, ACH, fractional schedule, and Sum/Max '
            'reconciliation. The schedule accepts an object_dict, Garden schedule target, or '
            'standards identifier. Use garden_root to save a Garden Properties Library load '
            'target and pass target to EP_Create_Program_Type.ventilation or '
            'HB_Edit_Room.ventilation; set return_object_dict=false for a compact '
            'target/summary/receipt response.'
        ),
        tags={
            "author",
            "energy",
            "outdoor-air",
            "program-type",
            "load",
            "ventilation",
        },
        timeout=20,
    )
    def create_ventilation(
        identifier: Annotated[str, Field(description="Ventilation object identifier.")],
        flow_per_person: Annotated[
            float, Field(description="Ventilation rate in m3/s per person.")
        ] = 0,
        flow_per_area: Annotated[
            float, Field(description="Ventilation rate in m3/s per floor area.")
        ] = 0,
        flow_per_zone: Annotated[
            float, Field(description="Whole-zone ventilation rate in m3/s.")
        ] = 0,
        air_changes_per_hour: Annotated[
            float, Field(description="Whole-zone ventilation rate in ACH.")
        ] = 0,
        schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional fractional ventilation schedule as a Honeybee Energy schedule object_dict, Garden schedule target, or standards-library identifier; use an occupancy schedule to mimic demand-controlled ventilation."
            ),
        ] = None,
        method: Annotated[
            str, Field(description="Ventilation reconciliation method for the four design criteria: Sum adds them; Max uses the largest.")
        ] = "Sum",
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description="Return the full load object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy Ventilation object."""
        from garden.energy.programtypes import create_ventilation as service

        return service(
            identifier=identifier,
            flow_per_person=flow_per_person,
            flow_per_area=flow_per_area,
            flow_per_zone=flow_per_zone,
            air_changes_per_hour=air_changes_per_hour,
            schedule=schedule,
            method=method,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Wall_Construction_Set",
        description="Create a Honeybee Energy WallConstructionSet intermediate object for ConstructionSet wall slots: exterior walls, interior walls, and ground-contact walls. Pass OpaqueConstruction object_dict values, Garden targets, or standards identifiers. Returns object_dict plus summary_view slot values; this subset is not saved as its own Garden target, so pass the returned object_dict into EP_Create_Construction_Set.wall_set.",
        tags={
            "energy",
            "construction-set",
            "construction",
            "wall",
            "author",
        },
        timeout=20,
    )
    def create_wall_construction_set(
        exterior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for exterior walls."
            ),
        ] = None,
        interior_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for interior walls."
            ),
        ] = None,
        ground_construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="OpaqueConstruction dict, Garden target, or standards identifier for ground-contact walls."
            ),
        ] = None,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually GD_Create['garden_root']; used only to resolve Garden construction targets in the slot inputs."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy WallConstructionSet object."""
        from garden.energy.constructionsets import (
            create_wall_construction_set as service,
        )

        return service(
            exterior_construction=exterior_construction,
            interior_construction=interior_construction,
            ground_construction=ground_construction,
            garden_root=garden_root,
        )

    @mcp.tool(
        name="EP_Create_Window_Blind_Material",
        description=(
            'Create a Honeybee Energy EnergyWindowMaterialBlind layer for window constructions '
            'with blinds. This returns a window material layer for later construction assembly. '
            "Returns object_dict plus summary_view; return_detail='full' also includes a material "
            'property matrix.'
        ),
        tags={
            "energy",
            "construction",
            "material",
            "author",
            "blind",
        },
        timeout=20,
    )
    def create_window_blind_material(
        identifier: Annotated[
            str, Field(description="Honeybee EnergyWindowMaterialBlind identifier for a window blind layer.")
        ],
        slat_orientation: Annotated[
            str, Field(description="Horizontal or Vertical.")
        ] = "Horizontal",
        slat_width: Annotated[
            float, Field(description="Slat width in meters.")
        ] = 0.025,
        slat_separation: Annotated[
            float, Field(description="Slat separation in meters.")
        ] = 0.01875,
        slat_angle: Annotated[float, Field(description="Slat angle in degrees.")] = 45,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key material values; full also returns a property_matrix with SDK property rows."
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
                description="Return the full material object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy EnergyWindowMaterialBlind object."""
        from garden.energy.constructionsets import (
            create_window_blind_material as service,
        )

        return service(
            identifier=identifier,
            slat_orientation=slat_orientation,
            slat_width=slat_width,
            slat_separation=slat_separation,
            slat_angle=slat_angle,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Window_Construction",
        description=(
            'Create a Honeybee Energy WindowConstruction from glazing/gas layers ordered from '
            'outside to inside, with an optional frame. For natural requests like a low-U window, '
            'low U-value glazing, U-factor, SHGC, visible transmittance, simple window '
            'construction, or simple glazing system, omit materials and pass u_factor, shgc, and '
            'vt to create a SDK SimpleGlazSys construction directly. With garden_root and '
            'return_object_dict=false, saves a reusable Garden target for '
            'EP_Create_Construction_Set.aperture_set. Returns object_dict plus summary_view, or '
            'target plus persistence_receipt when saved.'
        ),
        tags={
            "energy",
            "construction",
            "material",
            "window",
            "glazing",
            "u-factor",
            "shgc",
            "author",
        },
        timeout=20,
    )
    def create_window_construction(
        identifier: Annotated[str, Field(description="WindowConstruction identifier.")],
        materials: Annotated[
            list[dict[str, Any] | str] | None,
            Field(
                description="Window material layers from outside to inside. Omit when using u_factor, shgc, and vt simple-parameter creation."
            ),
        ] = None,
        u_factor: Annotated[
            float | None,
            Field(
                description="U-factor in W/m2-K for SDK simple-parameter window construction. Use the exact argument name u_factor when the user asks for a low-U window and has not supplied material layers."
            ),
        ] = None,
        shgc: Annotated[
            float | None,
            Field(
                description="Solar heat gain coefficient for SDK simple-parameter window construction."
            ),
        ] = None,
        vt: Annotated[
            float,
            Field(
                description="Visible transmittance for SDK simple-parameter window construction."
            ),
        ] = 0.6,
        frame: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional EnergyWindowFrame object_dict or library identifier."
            ),
        ] = None,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key property values; full also returns a layer_matrix with material rows."
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
                description=(
                    'Return the full construction object_dict (set false with garden_root for a '
                    'compact target/summary/receipt).'
                )
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy WindowConstruction object."""
        from garden.energy.constructionsets import (
            create_window_construction as service,
        )

        return service(
            identifier=identifier,
            materials=materials,
            u_factor=u_factor,
            shgc=shgc,
            vt=vt,
            frame=frame,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Window_Frame_Material",
        description=(
            'Create a Honeybee Energy EnergyWindowFrame that can be attached to a '
            "WindowConstruction. Returns object_dict plus summary_view; return_detail='full' also "
            'includes a material property matrix.'
        ),
        tags={
            "energy",
            "construction",
            "material",
            "author",
            "frame",
        },
        timeout=20,
    )
    def create_window_frame_material(
        identifier: Annotated[str, Field(description="Honeybee EnergyWindowFrame identifier for frame and divider properties.")],
        width: Annotated[float, Field(description="Frame width in meters.")],
        conductance: Annotated[
            float, Field(description="Frame conductance in W/m2-K.")
        ],
        edge_to_center_ratio: Annotated[
            float, Field(description="Edge-to-center glass conductance ratio.")
        ] = 1,
        outside_projection: Annotated[
            float, Field(description="Outside frame projection in meters.")
        ] = 0,
        inside_projection: Annotated[
            float, Field(description="Inside frame projection in meters.")
        ] = 0,
        thermal_absorptance: Annotated[
            float, Field(description="Long-wave absorptance.")
        ] = 0.9,
        solar_absorptance: Annotated[
            float, Field(description="Solar absorptance.")
        ] = 0.7,
        visible_absorptance: Annotated[
            float | None, Field(description="Visible absorptance.")
        ] = None,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key material values; full also returns a property_matrix with SDK property rows."
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
                description="Return the full material object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy EnergyWindowFrame object."""
        from garden.energy.constructionsets import (
            create_window_frame_material as service,
        )

        return service(
            identifier=identifier,
            width=width,
            conductance=conductance,
            edge_to_center_ratio=edge_to_center_ratio,
            outside_projection=outside_projection,
            inside_projection=inside_projection,
            thermal_absorptance=thermal_absorptance,
            solar_absorptance=solar_absorptance,
            visible_absorptance=visible_absorptance,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Window_Gas_Material",
        description=(
            'Create a Honeybee Energy EnergyWindowMaterialGas gap layer for WindowConstruction '
            "assemblies. Returns object_dict plus summary_view; return_detail='full' also "
            'includes a material property matrix.'
        ),
        tags={
            "energy",
            "construction",
            "material",
            "author",
            "window-layer",
        },
        timeout=20,
    )
    def create_window_gas_material(
        identifier: Annotated[str, Field(description="Honeybee EnergyWindowMaterialGas identifier for a window gas gap layer.")],
        thickness: Annotated[
            float, Field(description="Gas gap thickness in meters.")
        ] = 0.0125,
        gas_type: Annotated[
            str, Field(description="Gas type: Air, Argon, Krypton, or Xenon.")
        ] = "Air",
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key material values; full also returns a property_matrix with SDK property rows."
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
                description="Return the full material object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy EnergyWindowMaterialGas object."""
        from garden.energy.constructionsets import (
            create_window_gas_material as service,
        )

        return service(
            identifier=identifier,
            thickness=thickness,
            gas_type=gas_type,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Window_Gas_Mixture_Material",
        description=(
            'Create a Honeybee Energy EnergyWindowMaterialGasMixture gap layer from gas types and '
            'fractions for WindowConstruction assemblies. Returns object_dict plus summary_view; '
            "return_detail='full' also includes a material property matrix."
        ),
        tags={
            "energy",
            "construction",
            "material",
            "author",
            "window-layer",
        },
        timeout=20,
    )
    def create_window_gas_mixture_material(
        identifier: Annotated[
            str, Field(description="Honeybee EnergyWindowMaterialGasMixture identifier for a window gas mixture layer.")
        ],
        thickness: Annotated[
            float, Field(description="Gas gap thickness in meters.")
        ] = 0.0125,
        gas_types: Annotated[
            list[str] | None, Field(description="Gas type list.")
        ] = None,
        gas_fractions: Annotated[
            list[float] | None, Field(description="Gas fraction list summing to 1.")
        ] = None,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key material values; full also returns a property_matrix with SDK property rows."
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
                description="Return the full material object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy EnergyWindowMaterialGasMixture object."""
        from garden.energy.constructionsets import (
            create_window_gas_mixture_material as service,
        )

        return service(
            identifier=identifier,
            thickness=thickness,
            gas_types=gas_types,
            gas_fractions=gas_fractions,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Window_Glazing_Material",
        description=(
            'Create a Honeybee Energy EnergyWindowMaterialGlazing pane layer for detailed '
            'WindowConstruction assemblies. Returns object_dict plus summary_view, or a saved '
            'material target when garden_root is provided and return_object_dict=false. Use '
            "return_detail='summary' for key optical and thermal values or 'full' for a matrix of "
            'material property values.'
        ),
        tags={
            "energy",
            "construction",
            "material",
            "window",
            "glazing",
            "author",
        },
        timeout=20,
    )
    def create_window_glazing_material(
        identifier: Annotated[str, Field(description="Glazing material identifier.")],
        thickness: Annotated[
            float, Field(description="Glass thickness in meters.")
        ] = 0.003,
        solar_transmittance: Annotated[
            float, Field(description="Solar transmittance.")
        ] = 0.85,
        solar_reflectance: Annotated[
            float, Field(description="Solar reflectance.")
        ] = 0.075,
        visible_transmittance: Annotated[
            float, Field(description="Visible transmittance.")
        ] = 0.9,
        visible_reflectance: Annotated[
            float, Field(description="Visible reflectance.")
        ] = 0.075,
        infrared_transmittance: Annotated[
            float, Field(description="Infrared transmittance.")
        ] = 0,
        emissivity: Annotated[
            float, Field(description="Front-side emissivity.")
        ] = 0.84,
        emissivity_back: Annotated[
            float, Field(description="Back-side emissivity.")
        ] = 0.84,
        conductivity: Annotated[
            float, Field(description="Glass conductivity in W/m-K.")
        ] = 0.9,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key material values; full also returns a property_matrix with SDK property rows."
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
                description="Return the full material object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy EnergyWindowMaterialGlazing object."""
        from garden.energy.constructionsets import (
            create_window_glazing_material as service,
        )

        return service(
            identifier=identifier,
            thickness=thickness,
            solar_transmittance=solar_transmittance,
            solar_reflectance=solar_reflectance,
            visible_transmittance=visible_transmittance,
            visible_reflectance=visible_reflectance,
            infrared_transmittance=infrared_transmittance,
            emissivity=emissivity,
            emissivity_back=emissivity_back,
            conductivity=conductivity,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Window_Shade_Material",
        description=(
            'Create a Honeybee Energy EnergyWindowMaterialShade layer for window constructions '
            'with interior or exterior shades. This returns a construction layer for later '
            "assembly. Returns object_dict plus summary_view; return_detail='full' also includes "
            'a material property matrix.'
        ),
        tags={
            "energy",
            "construction",
            "material",
            "author",
            "shade",
        },
        timeout=20,
    )
    def create_window_shade_material(
        identifier: Annotated[
            str, Field(description="Honeybee EnergyWindowMaterialShade identifier for a window shade layer.")
        ],
        thickness: Annotated[
            float, Field(description="Shade thickness in meters.")
        ] = 0.005,
        solar_transmittance: Annotated[
            float, Field(description="Solar transmittance.")
        ] = 0.4,
        solar_reflectance: Annotated[
            float, Field(description="Solar reflectance.")
        ] = 0.5,
        visible_transmittance: Annotated[
            float, Field(description="Visible transmittance.")
        ] = 0.4,
        visible_reflectance: Annotated[
            float, Field(description="Visible reflectance.")
        ] = 0.4,
        return_detail: Annotated[
            str,
            Field(
                description="summary returns key material values; full also returns a property_matrix with SDK property rows."
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
                description="Return the full material object_dict. Set false with garden_root to pass only target/summary/receipt."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create a Honeybee Energy EnergyWindowMaterialShade object."""
        from garden.energy.constructionsets import (
            create_window_shade_material as service,
        )

        return service(
            identifier=identifier,
            thickness=thickness,
            solar_transmittance=solar_transmittance,
            solar_reflectance=solar_reflectance,
            visible_transmittance=visible_transmittance,
            visible_reflectance=visible_reflectance,
            return_detail=return_detail,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Create_Zone_Ventilation_Fan",
        description=(
            'Create a Honeybee Energy VentilationFan for fan-assisted zone ventilation or '
            'ventilative cooling with Exhaust, Intake, or Balanced outdoor-air flow. Use '
            'garden_root to save a zone_ventilation_fan target for '
            'HB_Edit_Room.zone_ventilation_fans; set return_object_dict=false only when you want '
            'a compact target/summary/receipt response. Exports to EnergyPlus '
            'ZoneVentilation:DesignFlowRate.'
        ),
        tags={
            "author",
            "energy",
            "fan",
            "outdoor-air",
            "ventilation",
            "ventilation-fan",
            "ventilative-cooling",
            "zone-exhaust",
        },
        timeout=20,
    )
    def create_zone_ventilation_fan(
        identifier: Annotated[
            str,
            Field(description="Unique VentilationFan identifier."),
        ],
        flow_rate: Annotated[
            float,
            Field(description="Fan air flow rate in m3/s."),
        ],
        ventilation_type: Annotated[
            str,
            Field(description="Zone ventilation type: Exhaust, Intake, or Balanced."),
        ] = "Balanced",
        pressure_rise: Annotated[
            float | None,
            Field(description="Optional fan pressure rise in Pascals. If omitted, SDK estimates from flow rate."),
        ] = None,
        efficiency: Annotated[
            float | None,
            Field(description="Optional total fan efficiency from 0 to 1. If omitted, SDK estimates from flow and pressure."),
        ] = None,
        control: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee Energy VentilationControl object_dict for fan operation; omit it to build a control from the temperature threshold fields."),
        ] = None,
        min_indoor_temperature: Annotated[
            float,
            Field(description="Minimum indoor temperature in Celsius at which the fan can operate."),
        ] = -100,
        max_indoor_temperature: Annotated[
            float,
            Field(description="Maximum indoor temperature in Celsius at which the fan can operate."),
        ] = 100,
        min_outdoor_temperature: Annotated[
            float,
            Field(description="Minimum outdoor temperature in Celsius at which the fan can operate."),
        ] = -100,
        max_outdoor_temperature: Annotated[
            float,
            Field(description="Maximum outdoor temperature in Celsius at which the fan can operate."),
        ] = 100,
        delta_temperature: Annotated[
            float,
            Field(description="Indoor minus outdoor temperature threshold in Celsius for fan operation."),
        ] = -100,
        garden_root: Annotated[
            str | None,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(description="When garden_root is provided, set false to omit object_dict and return only compact target, summary_view, persistence_receipt, and report."),
        ] = True,
    ) -> dict[str, Any]:
        """Create a zone ventilation fan."""
        from garden.energy.ventilation import create_zone_ventilation_fan as service

        return service(
            identifier=identifier,
            flow_rate=flow_rate,
            ventilation_type=ventilation_type,
            pressure_rise=pressure_rise,
            efficiency=efficiency,
            control=control,
            min_indoor_temperature=min_indoor_temperature,
            max_indoor_temperature=max_indoor_temperature,
            min_outdoor_temperature=min_outdoor_temperature,
            max_outdoor_temperature=max_outdoor_temperature,
            delta_temperature=delta_temperature,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
        )

    @mcp.tool(
        name="EP_Search_Energy_Library_Objects",
        description=(
            'Search Honeybee Energy standards library identifiers for schedules, program types, '
            'materials, constructions, and construction sets. Use returned identifiers in Energy '
            'authoring tools. Searches built-in Energy standards libraries. For thermostat '
            'setpoints use EP_Create_Setpoint. Returns matches, identifiers, summary_view, and '
            'report.'
        ),
        tags={
            "energy",
            "library",
            "search",
            "standards",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_energy_library_objects(
        query: Annotated[
            str,
            Field(
                description="Search text for Honeybee Energy standards identifiers, such as 'generic office lighting' or 'fractional'."
            ),
        ],
        object_family: Annotated[
            str | None,
            Field(
                description=(
                    'Optional family filter: schedule, schedule_type_limit, program_type, '
                    'opaque_material, window_material, opaque_construction, window_construction, '
                    'shade_construction, construction_set, or all (use EP_Create_Setpoint for '
                    'thermostat setpoints).'
                )
            ),
        ] = None,
        limit: Annotated[
            int, Field(description="Maximum number of identifiers to return.")
        ] = 10,
    ) -> dict[str, Any]:
        """Search Honeybee Energy standards library identifiers."""
        from garden.energy.libraries import search_energy_library_objects as service

        return service(
            query=query,
            object_family=object_family,
            limit=limit,
        )

    @mcp.tool(
        name="EP_Search_HVAC_Templates",
        description=(
            'Search Honeybee Energy SDK HVAC templates and, when identifier is provided with a '
            'unique template selection, return a ready-to-use HVAC object_dict or Garden '
            'Properties Library target for HB_Edit_Room hvac. Supports all-air, DOAS, and '
            'heat-cool template HVAC systems. Use IB_* tools for custom Ironbug DetailedHVAC '
            'component graphs.'
        ),
        tags={
            "energy",
            "hvac-template",
            "hvac",
            "search",
            "standards",
        },
        timeout=20,
    )
    def search_hvac_templates(
        query: Annotated[
            str | None,
            Field(
                description="Optional search text such as 'psz packaged single zone', 'vav', 'radiant doas', or 'vrf'."
            ),
        ] = None,
        system_type: Annotated[
            str | None,
            Field(
                description="Optional exact SDK HVAC template type, such as PSZ, VAV, PTAC, FCUwithDOAS, Radiant, or VRF."
            ),
        ] = None,
        family: Annotated[
            str | None,
            Field(
                description="Optional family filter: allair, doas, heatcool, or all."
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(
                description="Optional identifier. When provided with a unique template, the tool creates an HVAC object_dict."
            ),
        ] = None,
        vintage: Annotated[
            str | None,
            Field(description="Optional Honeybee HVAC template vintage, such as ASHRAE_2019."),
        ] = None,
        equipment_type: Annotated[
            str | None,
            Field(
                description="Optional SDK equipment_type for the selected HVAC template."
            ),
        ] = None,
        economizer_type: Annotated[
            str | None,
            Field(
                description="Optional economizer type for templates that support it."
            ),
        ] = None,
        sensible_heat_recovery: Annotated[
            float | None,
            Field(
                description="Optional sensible heat recovery effectiveness from 0 to 1."
            ),
        ] = None,
        latent_heat_recovery: Annotated[
            float | None,
            Field(
                description="Optional latent heat recovery effectiveness from 0 to 1."
            ),
        ] = None,
        demand_controlled_ventilation: Annotated[
            bool | None,
            Field(description="Optional demand controlled ventilation flag."),
        ] = None,
        doas_availability_schedule: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Optional DOAS availability schedule dict or library identifier for DOAS templates."
            ),
        ] = None,
        radiant_type: Annotated[
            str | None,
            Field(
                description="Optional radiant type for radiant templates, such as Floor or Ceiling."
            ),
        ] = None,
        minimum_operation_time: Annotated[
            float | None,
            Field(description="Optional radiant minimum operation time in hours."),
        ] = None,
        switch_over_time: Annotated[
            float | None,
            Field(description="Optional radiant switch-over time in hours."),
        ] = None,
        return_object: Annotated[
            bool,
            Field(
                description="Whether to create object_dict when identifier and a unique template are available."
            ),
        ] = True,
        garden_root: Annotated[
            str | None,
            Field(
                description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."
            ),
        ] = None,
        return_object_dict: Annotated[
            bool,
            Field(
                description=(
                    'Include the full SDK object_dict in the response (set false for compact '
                    'target responses).'
                )
            ),
        ] = True,
        limit: Annotated[
            int, Field(description="Maximum number of template matches to return.")
        ] = 10,
    ) -> dict[str, Any]:
        """Search Honeybee Energy HVAC templates and optionally create one."""
        from garden.energy.hvac import search_hvac_templates as service

        return service(
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
            doas_availability_schedule=doas_availability_schedule,
            radiant_type=radiant_type,
            minimum_operation_time=minimum_operation_time,
            switch_over_time=switch_over_time,
            return_object=return_object,
            garden_root=garden_root,
            return_object_dict=return_object_dict,
            limit=limit,
        )

    @mcp.tool(
        name="EP_Setup_Airflow_Network",
        description=(
            'Generate EnergyPlus AirflowNetwork properties for selected Honeybee Rooms using the '
            'Honeybee Energy AFN generator. Use this for pressure-driven multizone airflow, Face '
            'vent_crack leakage, closed-opening leakage, and optional room-infiltration-derived '
            'exterior cracks. Returns the updated Honeybee model target in target and '
            'summary_view.target plus persistence_receipt and report.'
        ),
        tags={
            "airflow-network",
            "energy",
            "edit",
            "infiltration",
            "room",
            "ventilation",
            "ventilation-opening",
        },
        timeout=30,
    )
    def setup_airflow_network(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target. Defaults to the Garden base model."),
        ] = None,
        room_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional room identifiers that make up the AirflowNetwork. If omitted with room_targets, all model rooms are used."),
        ] = None,
        room_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description='Optional Honeybee Room typed targets from HB_Search_Model_Objects. Use this or room_identifiers; omit both to use all Rooms.'),
        ] = None,
        vent_control_type: Annotated[
            str,
            Field(description="Ventilation simulation type: SingleZone, MultiZoneWithDistribution, or MultiZoneWithoutDistribution."),
        ] = "MultiZoneWithoutDistribution",
        leakage_type: Annotated[
            str,
            Field(description="AirflowNetwork leakiness template for generated cracks: Excellent, Medium, or VeryPoor."),
        ] = "Medium",
        use_room_infiltration: Annotated[
            bool,
            Field(description="If true, exterior AFN leakage is derived from each Room's Honeybee Energy Infiltration load when available."),
        ] = True,
        atmospheric_pressure: Annotated[
            float,
            Field(description="Atmospheric pressure in Pascals used for dry-air density."),
        ] = 101325,
        delta_pressure: Annotated[
            float,
            Field(description="Reference pressure difference in Pascals for infiltration-derived cracks."),
        ] = 4,
        reference_temperature: Annotated[
            float,
            Field(description="AFN reference temperature in Celsius."),
        ] = 20,
        reference_pressure: Annotated[
            float,
            Field(description="AFN reference pressure in Pascals."),
        ] = 101325,
        reference_humidity_ratio: Annotated[
            float,
            Field(description="AFN reference humidity ratio in kgWater/kgDryAir."),
        ] = 0,
        building_type: Annotated[
            str,
            Field(description="AFN building type: LowRise or HighRise."),
        ] = "LowRise",
        long_axis_angle: Annotated[
            float,
            Field(description="Clockwise angle in degrees from true North for the building long axis."),
        ] = 0,
        aspect_ratio: Annotated[
            float,
            Field(description="Building footprint aspect ratio used by AFN wind pressure coefficients."),
        ] = 1,
        autocalculate_geometry_properties: Annotated[
            bool,
            Field(description="If true, derive AFN building geometry properties from the selected rooms."),
        ] = True,
    ) -> dict[str, Any]:
        """Generate AirflowNetwork properties."""
        from garden.energy.ventilation import setup_airflow_network as service

        return service(
            garden_root=garden_root,
            model_target=model_target,
            room_identifiers=room_identifiers,
            room_targets=room_targets,
            vent_control_type=vent_control_type,
            leakage_type=leakage_type,
            use_room_infiltration=use_room_infiltration,
            atmospheric_pressure=atmospheric_pressure,
            delta_pressure=delta_pressure,
            reference_temperature=reference_temperature,
            reference_pressure=reference_pressure,
            reference_humidity_ratio=reference_humidity_ratio,
            building_type=building_type,
            long_axis_angle=long_axis_angle,
            aspect_ratio=aspect_ratio,
            autocalculate_geometry_properties=autocalculate_geometry_properties,
        )

    @mcp.tool(
        name="EP_Setup_Daylighting_Control_To_Center",
        description=(
            'Assign Honeybee Energy DaylightingControl objects to selected Rooms by placing an '
            'EnergyPlus daylight reference sensor near each room center. Use this for electric '
            'lighting dimming and lighting-energy impact tests with existing apertures/windows '
            'and Lighting loads. Returns the updated Honeybee model target in target and '
            'summary_view.target plus persistence_receipt and report.'
        ),
        tags={
            "daylight",
            "daylighting-control",
            "dimming",
            "edit",
            "energy",
            "lighting",
            "room",
        },
        timeout=30,
    )
    def setup_daylighting_control_to_center(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target. Defaults to the Garden base model."),
        ] = None,
        room_identifiers: Annotated[
            list[str] | None,
            Field(description=(
                'Optional room_identifiers list to update (mutually exclusive with room_targets). '
                'If omitted with room_targets, all rooms are updated.'
            )),
        ] = None,
        room_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description=(
                'Optional room_targets list of Honeybee Room typed targets from '
                'HB_Search_Model_Objects (mutually exclusive with room_identifiers).'
            )),
        ] = None,
        distance_from_floor: Annotated[
            float,
            Field(description="Sensor height above room floor in meters, commonly 0.8 m."),
        ] = 0.8,
        illuminance_setpoint: Annotated[
            float,
            Field(description="Illuminance setpoint in lux above which electric lights dim."),
        ] = 300,
        control_fraction: Annotated[
            float,
            Field(description="Fraction of room lighting controlled by the daylight sensor, from 0 to 1."),
        ] = 1.0,
        min_power_input: Annotated[
            float,
            Field(description="Minimum dimmed lighting power fraction, from 0 to 1."),
        ] = 0.3,
        min_light_output: Annotated[
            float,
            Field(description="Minimum dimmed light output fraction, from 0 to 1."),
        ] = 0.2,
        off_at_minimum: Annotated[
            bool,
            Field(description="Whether lights switch fully off after reaching minimum power."),
        ] = False,
        tolerance: Annotated[
            float,
            Field(description="Geometry tolerance in model units for finding a valid room-center sensor point."),
        ] = 0.01,
    ) -> dict[str, Any]:
        """Assign daylighting controls to selected Rooms."""
        from garden.energy.ventilation import setup_daylighting_control_to_center as service

        return service(
            garden_root=garden_root,
            model_target=model_target,
            room_identifiers=room_identifiers,
            room_targets=room_targets,
            distance_from_floor=distance_from_floor,
            illuminance_setpoint=illuminance_setpoint,
            control_fraction=control_fraction,
            min_power_input=min_power_input,
            min_light_output=min_light_output,
            off_at_minimum=off_at_minimum,
            tolerance=tolerance,
        )

    @mcp.tool(
        name="EP_Setup_Simple_Ventilation_Properties",
        description=(
            'Apply simple operable-window natural ventilation properties to Honeybee Rooms in a '
            'Garden model. Use this for VentilationOpening, window_vent_control, operable '
            'windows, cross ventilation, and ventilative cooling controls. Returns the updated '
            'Honeybee model target in target and summary_view.target plus persistence_receipt and '
            'report.'
        ),
        tags={
            "cross-ventilation",
            "edit",
            "energy",
            "natural-ventilation",
            "operable-window",
            "room",
            "ventilation",
            "ventilation-opening",
            "ventilative-cooling",
        },
        timeout=30,
    )
    def setup_simple_ventilation_properties(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']; required when saving or reading Garden targets."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Honeybee model target. Defaults to the Garden base model."),
        ] = None,
        room_identifiers: Annotated[
            list[str] | None,
            Field(description=(
                'Optional room_identifiers list to update (mutually exclusive with room_targets). '
                'If omitted with room_targets, all model rooms are updated.'
            )),
        ] = None,
        room_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(description=(
                'Optional room_targets list of Honeybee Room typed targets from '
                'HB_Search_Model_Objects (mutually exclusive with room_identifiers).'
            )),
        ] = None,
        fraction_area_operable: Annotated[
            float,
            Field(description='Fraction of window area that is operable, from 0 to 1.'),
        ] = 0.5,
        fraction_height_operable: Annotated[
            float,
            Field(description="Fraction of window height that is operable, from 0 to 1."),
        ] = 1.0,
        discharge_coefficient: Annotated[
            float,
            Field(description="Opening discharge coefficient, commonly 0.45 with insect screens or 0.65 without screens."),
        ] = 0.45,
        wind_cross_vent: Annotated[
            bool,
            Field(description="Whether wind-driven cross ventilation is expected."),
        ] = False,
        flow_coefficient_closed: Annotated[
            float,
            Field(description="Closed-opening AirflowNetwork leakage coefficient. Keep 0 for the simple non-AFN ventilation path."),
        ] = 0,
        flow_exponent_closed: Annotated[
            float,
            Field(description="Closed-opening AirflowNetwork leakage exponent used only if the opening later participates in AFN."),
        ] = 0.65,
        two_way_threshold: Annotated[
            float,
            Field(description="AirflowNetwork two-way flow density threshold for openings, used only when AFN is enabled."),
        ] = 0.0001,
        min_indoor_temperature: Annotated[
            float,
            Field(description="Minimum indoor temperature in Celsius at which ventilation can occur."),
        ] = -100,
        max_indoor_temperature: Annotated[
            float,
            Field(description="Maximum indoor temperature in Celsius at which ventilation can occur."),
        ] = 100,
        min_outdoor_temperature: Annotated[
            float,
            Field(description="Minimum outdoor temperature in Celsius at which ventilation can occur."),
        ] = -100,
        max_outdoor_temperature: Annotated[
            float,
            Field(description="Maximum outdoor temperature in Celsius at which ventilation can occur."),
        ] = 100,
        delta_temperature: Annotated[
            float,
            Field(description="Indoor minus outdoor temperature threshold in Celsius for ventilative cooling."),
        ] = -100,
    ) -> dict[str, Any]:
        """Apply simple natural ventilation properties."""
        from garden.energy.ventilation import (
            setup_simple_ventilation_properties as service,
        )

        return service(
            garden_root=garden_root,
            model_target=model_target,
            room_identifiers=room_identifiers,
            room_targets=room_targets,
            fraction_area_operable=fraction_area_operable,
            fraction_height_operable=fraction_height_operable,
            discharge_coefficient=discharge_coefficient,
            wind_cross_vent=wind_cross_vent,
            flow_coefficient_closed=flow_coefficient_closed,
            flow_exponent_closed=flow_exponent_closed,
            two_way_threshold=two_way_threshold,
            min_indoor_temperature=min_indoor_temperature,
            max_indoor_temperature=max_indoor_temperature,
            min_outdoor_temperature=min_outdoor_temperature,
            max_outdoor_temperature=max_outdoor_temperature,
            delta_temperature=delta_temperature,
        )
