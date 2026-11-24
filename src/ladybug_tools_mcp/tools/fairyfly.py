"""fairyfly MCP tools."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.contracts import (
    ArtifactResultModel,
    ArtifactTargetRef,
    BuildingModelTargetRef,
    MutationResultModel,
    QueryResultModel,
    RunResultModel,
    RunTargetRef,
    ValidationResultModel,
    dump_input,
    dump_target,
    validate_output,
)


def _as_spec_list(value: list[dict[str, Any]] | dict[str, Any] | None) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    return list(value)


_HYGROTHERMAL_MATERIAL_KEYS = (
    "moisture_storage_function",
    "liquid_transport_suction",
    "liquid_transport_redistribution",
    "conductivity_moisture_dependent",
    "conductivity_temperature_dependent",
    "diffusion_moisture_dependent",
    "enthalpy_temperature_dependent",
    "reference_water_content",
    "free_water_saturation",
    "water_absorption_coefficient",
    "drying_factor",
    "typical_built_in_moisture",
)


def _resolve_fairyfly_material(material: Any) -> dict[str, Any]:
    if isinstance(material, str):
        from garden.fairyfly.model import coerce_fairyfly_material

        return dict(coerce_fairyfly_material(material).to_dict())
    if not isinstance(material, dict):
        raise ValueError("Each shape's material must be a dictionary or material name string.")
    if isinstance(material.get("object_dict"), dict):
        material = material["object_dict"]
    if material.get("type") and material.get("identifier"):
        return material
    if (
        "material_name" in material
        or "cavity_model" in material
        or material.get("kind") in {"cavity", "hygrothermal"}
        or material.get("type") == "HygrothermalMaterial"
        or any(material.get(k) is not None for k in _HYGROTHERMAL_MATERIAL_KEYS)
        or "energy_material" in material
        or "hb_material_name" in material
        or "hb_material_target" in material
    ):
        return material
    if "conductivity" not in material:
        raise ValueError(
            "Inline Fairyfly shape material requires a Fairyfly material dict, material_name, "
            "'conductivity' (SolidMaterial), 'cavity_model' (CavityMaterial), or HB-Energy source."
        )
    from garden.fairyfly.model import create_fairyfly_solid_material

    created = create_fairyfly_solid_material(
        name=str(material.get("name") or material.get("display_name") or "SolidMaterial"),
        conductivity=float(material["conductivity"]),
        emissivity=float(material.get("emissivity", 0.9)),
        emissivity_back=(
            float(material["emissivity_back"])
            if material.get("emissivity_back") is not None
            else None
        ),
        density=(
            float(material["density"])
            if material.get("density") is not None
            else None
        ),
        porosity=(
            float(material["porosity"])
            if material.get("porosity") is not None
            else None
        ),
        specific_heat=(
            float(material["specific_heat"])
            if material.get("specific_heat") is not None
            else None
        ),
        vapor_diffusion_resistance=(
            float(material["vapor_diffusion_resistance"])
            if material.get("vapor_diffusion_resistance") is not None
            else None
        ),
        reflectance=(
            float(material["reflectance"])
            if material.get("reflectance") is not None
            else None
        ),
        transmittance=(
            float(material["transmittance"])
            if material.get("transmittance") is not None
            else None
        ),
        rgb_color=material.get("rgb_color"),
    )
    return dict(created["object_dict"])


def register(mcp: FastMCP) -> None:
    """Register fairyfly tools."""

    @mcp.tool(
        name="FF_Create_Model",
        description=(
            "Create a Fairyfly two-dimensional heat-transfer model in a Garden (empty, from 1D "
            "layers via Model.from_layers, or imported from FFJSON/FFpkl) and optionally set it as "
            "the base Fairyfly model. Use this before editing with FF_Edit_Model, writing THMZ, or "
            "running THERM with FF_Start_Simulation. Returns target and model_target."
        ),
        tags={"fairyfly", "therm", "model", "author", "2d"},
        timeout=20,
    )
    def create_fairyfly_model(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        identifier: Annotated[
            str,
            Field(
                description="Required stable Garden Fairyfly model identifier used for the FFJSON file name."
            ),
        ],
        units: Annotated[
            str,
            Field(description="Fairyfly model units string, for example Millimeters."),
        ] = "Millimeters",
        tolerance: Annotated[
            float | None,
            Field(description="Optional Fairyfly model tolerance.", gt=0),
        ] = None,
        angle_tolerance: Annotated[
            float,
            Field(description="Fairyfly model angle tolerance.", gt=0),
        ] = 1.0,
        display_name: Annotated[
            str | None,
            Field(description="Optional user-facing model display name."),
        ] = None,
        plane: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional 3D Plane spec ({origin: [x,y,z], normal: [x,y,z], x_axis?: [x,y,z]}) "
                    "used as base_plane when creating from layers."
                )
            ),
        ] = None,
        layers: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Optional list of layer dicts ({thickness, material, name?, rgb_color?}) "
                    "to build a stratified wall/roof section via Model.from_layers."
                )
            ),
        ] = None,
        layer_height: Annotated[
            float,
            Field(description="Height of extruded layer section when layers is supplied.", gt=0),
        ] = 200.0,
        source_file: Annotated[
            str | None,
            Field(description="Optional path to an existing FFJSON or FFpkl file to import."),
        ] = None,
        file_format: Annotated[
            Literal["auto", "ffjson", "ffpkl"],
            Field(description="Format of source_file ('auto', 'ffjson', or 'ffpkl')."),
        ] = "auto",
        save_back: Annotated[
            bool,
            Field(description="Whether to save the Fairyfly Model into the Garden and return a Fairyfly model target."),
        ] = True,
        set_base: Annotated[
            bool,
            Field(description="Whether to set as Garden base Fairyfly model."),
        ] = True,
        include_body: Annotated[
            bool,
            Field(description="Whether to return full model body if not saved."),
        ] = False,
    ) -> MutationResultModel:
        """Create a Fairyfly Model."""
        from garden.fairyfly.model import create_fairyfly_model as service

        return validate_output(
            MutationResultModel,
            service(
                garden_root=garden_root,
                identifier=identifier,
                units=units,
                tolerance=tolerance,
                angle_tolerance=angle_tolerance,
                display_name=display_name,
                plane=dump_input(plane),
                layers=dump_input(layers),
                layer_height=layer_height,
                source_file=source_file,
                file_format=file_format,
                save_back=save_back,
                set_base=set_base,
                include_body=include_body,
            ),
        )

    @mcp.tool(
        name="FF_Edit_Model",
        description=(
            "Edit a Garden-backed Fairyfly Model: add or modify Shapes (supporting SolidMaterial, "
            "HygrothermalMaterial, CavityMaterial with CEN/NFRC/ISO15099/ISO15099Ventilated and Gas/PureGas, "
            "built-in library names, HB-Energy material conversion) and Boundaries (SteadyState or "
            "Transient boundary conditions), delete shapes/boundaries, intersect adjacencies, transform "
            "(move/rotate/rotate_xy/scale), convert units, import THERM XML libraries, or export "
            "FFJSON/FFpkl/THERM XML."
        ),
        tags={"fairyfly", "therm", "model", "geometry", "shape", "boundary", "material", "2d"},
        timeout=30,
    )
    def edit_fairyfly_model(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(
                description=(
                    "Optional Fairyfly Model target dict, usually FF_Create_Model['target']; "
                    "defaults to the Garden base Fairyfly Model."
                )
            ),
        ] = None,
        shapes: Annotated[
            list[dict[str, Any]] | dict[str, Any] | None,
            Field(
                description=(
                    "Shape spec or list of shape specs to add. Each needs vertices_2d and material "
                    "(Fairyfly dict, material_name, conductivity, cavity_model+gas, or "
                    "energy_material/hb_material_name), plus optional name, holes_2d, plane, rgb_color."
                )
            ),
        ] = None,
        boundaries: Annotated[
            list[dict[str, Any]] | dict[str, Any] | None,
            Field(
                description=(
                    "Boundary spec or list of boundary specs to add. Each needs line_segments_2d "
                    "and either (temperature + film_coefficient), condition_name, or condition dict."
                )
            ),
        ] = None,
        edit_shapes: Annotated[
            list[dict[str, Any]] | dict[str, Any] | None,
            Field(
                description=(
                    "Existing shape updates ({identifier or name, new_name?, material?, "
                    "vertices_2d?, holes_2d?, plane?, rgb_color?})."
                )
            ),
        ] = None,
        edit_boundaries: Annotated[
            list[dict[str, Any]] | dict[str, Any] | None,
            Field(
                description=(
                    "Existing boundary updates ({identifier or name, new_name?, condition_name?, "
                    "temperature?, film_coefficient?, u_factor_tag?, line_segments_2d?, plane?})."
                )
            ),
        ] = None,
        remove_shape_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional list of Shape identifiers or display_names to remove."),
        ] = None,
        remove_boundary_identifiers: Annotated[
            list[str] | None,
            Field(description="Optional list of Boundary identifiers or display_names to remove."),
        ] = None,
        intersect_adjacency: Annotated[
            bool | dict[str, Any],
            Field(description="Intersect adjacent shapes (pass true or {tolerance, plane?})."),
        ] = False,
        transforms: Annotated[
            list[dict[str, Any]] | dict[str, Any] | None,
            Field(description="Optional model transforms: move, rotate, rotate_xy, or scale."),
        ] = None,
        convert_units: Annotated[
            str | None,
            Field(description="Optional target unit string to convert model geometry via convert_to_units."),
        ] = None,
        plane: Annotated[
            dict[str, Any] | None,
            Field(description="Optional default 3D Plane applied to new/edited 2D shapes & boundaries."),
        ] = None,
        import_therm_xml_path: Annotated[
            str | None,
            Field(description="Optional THERM XML path to extract materials, gases, and conditions from."),
        ] = None,
        export_format: Annotated[
            Literal["ffjson", "ffpkl", "therm_xml"] | None,
            Field(description="Optional format ('ffjson', 'ffpkl', or 'therm_xml') to export the model."),
        ] = None,
        export_path: Annotated[
            str | None,
            Field(description="Optional Garden-relative output path when export_format is set."),
        ] = None,
        export_name: Annotated[
            str | None,
            Field(description="Optional output stem when export_format is set."),
        ] = None,
    ) -> MutationResultModel:
        """Edit Shapes, Boundaries, geometry, units, XML materials, or export a Fairyfly model."""
        dumped_model_target = dump_target(model_target)
        dumped_plane = dump_input(plane)
        dumped_intersect_adjacency = dump_input(intersect_adjacency)
        shape_specs = _as_spec_list(dump_input(shapes))
        boundary_specs = _as_spec_list(dump_input(boundaries))
        edit_shape_specs = _as_spec_list(dump_input(edit_shapes))
        edit_boundary_specs = _as_spec_list(dump_input(edit_boundaries))
        transform_specs = _as_spec_list(dump_input(transforms))
        has_model_edits = any(
            [
                shape_specs,
                boundary_specs,
                edit_shape_specs,
                edit_boundary_specs,
                remove_shape_identifiers,
                remove_boundary_identifiers,
                bool(dumped_intersect_adjacency),
                transform_specs,
                bool(convert_units),
            ]
        )
        if not has_model_edits and not import_therm_xml_path and not export_format:
            raise ValueError(
                "Provide model edits (shapes, boundaries, edits, removals, intersect_adjacency, "
                "transforms, convert_units), import_therm_xml_path, or export_format."
            )

        from garden.fairyfly.model import (
            edit_fairyfly_model_entities,
            export_fairyfly_model_file,
            import_fairyfly_therm_xml,
        )

        resolved_shapes: list[dict[str, Any]] = []
        for spec in shape_specs:
            if not isinstance(spec, dict):
                raise ValueError("Each shape entry must be a dictionary.")
            copied = dict(spec)
            copied["material"] = _resolve_fairyfly_material(spec["material"])
            resolved_shapes.append(copied)

        resolved_edit_shapes: list[dict[str, Any]] = []
        for spec in edit_shape_specs:
            if not isinstance(spec, dict):
                raise ValueError("Each edit_shapes entry must be a dictionary.")
            copied = dict(spec)
            if spec.get("material") is not None:
                copied["material"] = _resolve_fairyfly_material(spec["material"])
            resolved_edit_shapes.append(copied)

        result: dict[str, Any] | None = None
        if has_model_edits:
            result = edit_fairyfly_model_entities(
                garden_root=garden_root,
                model_target=dumped_model_target,
                shapes=resolved_shapes or None,
                boundaries=boundary_specs or None,
                edit_shapes=resolved_edit_shapes or None,
                edit_boundaries=edit_boundary_specs or None,
                remove_shape_identifiers=remove_shape_identifiers,
                remove_boundary_identifiers=remove_boundary_identifiers,
                intersect_adjacency=dumped_intersect_adjacency,
                transforms=transform_specs or None,
                convert_units=convert_units,
                plane=dumped_plane,
            )

        current_target = result["model_target"] if result is not None else dumped_model_target
        if import_therm_xml_path:
            imported = import_fairyfly_therm_xml(
                garden_root=garden_root,
                xml_path=import_therm_xml_path,
                include_objects=True,
            )
            if result is None:
                return validate_output(MutationResultModel, imported)
            result["imported_therm_xml"] = imported
            result["summary_view"]["imported_therm_xml"] = imported["summary_view"]

        if export_format:
            exported = export_fairyfly_model_file(
                garden_root=garden_root,
                model_target=current_target,
                file_format=export_format,
                output_path=export_path,
                name=export_name,
            )
            if result is None:
                return validate_output(MutationResultModel, exported)
            result["export"] = exported
            result["summary_view"]["exported_file"] = exported["summary_view"]

        assert result is not None
        return validate_output(MutationResultModel, result)

    @mcp.tool(
        name="FF_Validate_Model",
        description=(
            "Validate a Garden-backed Fairyfly Model with Fairyfly SDK checks. Returns "
            "validation_status through summary_view/report, compact issues, object counts, and "
            "report."
        ),
        tags={"fairyfly", "therm", "model", "validate", "check"},
        timeout=20,
    )
    def validate_fairyfly_model(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(
                description=(
                    "Optional Fairyfly Model target dict, usually FF_Create_Model['target']; "
                    "defaults to the Garden base Fairyfly Model."
                )
            ),
        ] = None,
    ) -> ValidationResultModel:
        """Validate a Fairyfly model."""
        from garden.fairyfly.model import validate_fairyfly_model as service

        return validate_output(
            ValidationResultModel,
            service(garden_root=garden_root, model_target=dump_target(model_target)),
        )

    @mcp.tool(
        name="FF_Start_Simulation",
        description=(
            "Start an asynchronous Fairyfly 2D simulation using the bundled cross-platform "
            "pyHygroThermFEM-Fairyfly solver and headless Gmsh Q4 mesher (or set export_only=true "
            "to write a THMZ artifact with optional include_mesh=true). Supports steady-state, dry "
            "transient, and coupled hygrothermal simulations from a Garden Fairyfly model or "
            "direct solving of premeshed/unmeshed THMZ files via thmz_target or thmz_path. Returns "
            "run_target (or thmz_target when export_only=true), runtime_status, poll_next "
            "(GD_Poll_Run), and report."
        ),
        tags={"fairyfly", "therm", "simulate", "u-factor", "transient", "hygrothermal", "thmz"},
        timeout=330,
    )
    def start_fairyfly_therm_run(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Fairyfly Model target dict, usually FF_Create_Model['target']; "
                    "defaults to the Garden base Fairyfly Model when thmz_target/thmz_path are omitted."
                )
            ),
        ] = None,
        thmz_target: Annotated[
            ArtifactTargetRef | None,
            Field(
                description=(
                    "Optional fairyfly_thmz target (premeshed or unmeshed) to solve directly without "
                    "re-exporting from a model."
                )
            ),
        ] = None,
        thmz_path: Annotated[
            str | None,
            Field(
                description=(
                    "Optional Garden-relative or absolute path to an existing .thmz file (premeshed "
                    "or unmeshed) to solve directly."
                )
            ),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional stable THERM run or THMZ export identifier. Omit to generate one."),
        ] = None,
        silent: Annotated[
            bool,
            Field(description="Suppress solver console output during simulation."),
        ] = True,
        export_only: Annotated[
            bool,
            Field(description="If true, write the .thmz artifact without running pyHygroThermFEM."),
        ] = False,
        include_mesh: Annotated[
            bool,
            Field(description="When export_only=true, also generate Mesh.xml via headless Gmsh."),
        ] = False,
        name: Annotated[
            str | None,
            Field(description="Optional THMZ file stem when export_only=true (defaults to model)."),
        ] = None,
        simulation_parameter: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional SimulationParameter dict ({mesh: {mesh_type, parameter, "
                    "run_error_estimator, max_error_percent, max_iterations}, exposure: "
                    "{model_type, cross_section_type, gravity_orientation, wind_orientation}, "
                    "transient?: {time_range, timestep, number_of_timesteps, initial_temperature, "
                    "initial_humidity, methodology, simulate_moisture, convergence_tolerance, "
                    "relaxation_parameter, modeling_options}})."
                )
            ),
        ] = None,
        wait_seconds: Annotated[
            float | None,
            Field(description="Optional blocking wait (seconds, up to 300) for async completion.", ge=0),
        ] = None,
        poll_interval: Annotated[
            float,
            Field(description="Polling interval in seconds when wait_seconds is specified.", gt=0),
        ] = 2.0,
    ) -> RunResultModel:
        """Start a Fairyfly pyHygroThermFEM run or export a THMZ file."""
        from garden.fairyfly.therm import start_fairyfly_therm_run as service

        return validate_output(
            RunResultModel,
            service(
                garden_root=garden_root,
                model_target=dump_target(model_target),
                thmz_target=dump_target(thmz_target),
                thmz_path=thmz_path,
                run_id=run_id,
                silent=silent,
                export_only=export_only,
                include_mesh=include_mesh,
                name=name,
                simulation_parameter=dump_input(simulation_parameter),
                wait_seconds=wait_seconds,
                poll_interval=poll_interval,
            ),
        )

    @mcp.tool(
        name="FF_Read_Results",
        description=(
            "Read steady-state or transient Fairyfly/pyHygroThermFEM results from a THMZ file: "
            "U-Factor summaries, temperature, heat-flux magnitudes/vectors, relative humidity, "
            "water content, condensation risk (min surface temperature, dew point, f_Rsi, RH margin), "
            "thermal-bridge Psi-factor, transient_summary, or transient_series time histories. "
            "Poll GD_Poll_Run after FF_Start_Simulation before reading from a run_target."
        ),
        tags={"fairyfly", "therm", "result", "u-factor", "temperature", "humidity", "transient"},
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def read_fairyfly_results(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        thmz_target: Annotated[
            ArtifactTargetRef | None,
            Field(description="Optional fairyfly_thmz target returned by FF_Start_Simulation(export_only=true)."),
        ] = None,
        run_target: Annotated[
            RunTargetRef | None,
            Field(description="Optional completed fairyfly_therm_run target returned by FF_Start_Simulation. Poll GD_Poll_Run before reading."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="Optional run identifier when thmz_target/run_target are omitted."),
        ] = None,
        data_type: Annotated[
            Literal[
                "temperature",
                "heat_flux",
                "heat_flux_vectors",
                "humidity",
                "water_content",
                "u_factor",
                "condensation_risk",
                "psi_factor",
                "transient_summary",
                "transient_series",
            ],
            Field(
                description=(
                    "Result data type: 'u_factor' (default), 'temperature', 'heat_flux', "
                    "'heat_flux_vectors', 'humidity', 'water_content', 'condensation_risk', "
                    "'psi_factor', 'transient_summary', or 'transient_series'."
                )
            ),
        ] = "u_factor",
        timestep_index: Annotated[
            int | None,
            Field(
                description=(
                    "Optional 0-based transient output frame index (defaults to final step when omitted) "
                    "for transient temperature/heat_flux/humidity/water_content/condensation_risk or "
                    "transient_series."
                )
            ),
        ] = None,
        field: Annotated[
            str,
            Field(
                description=(
                    "For transient_series: CSV table name ('temperatures', 'humidities', "
                    "'water_content', 'heat_flux', 'water_flux', 'heat_flux_edges', "
                    "'water_flux_edges', 'heat_flux_step_exchange', 'water_flux_step_exchange')."
                )
            ),
        ] = "temperatures",
        entity_ids: Annotated[
            list[int] | None,
            Field(description="For transient_series: optional Geometry.xml node/edge entity IDs to slice."),
        ] = None,
        include_values: Annotated[
            bool,
            Field(description="For field or transient_series queries: include raw arrays in response."),
        ] = False,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional Fairyfly model target for boundary-aware condensation_risk analysis."),
        ] = None,
        interior_temp_c: Annotated[
            float | None,
            Field(description="For condensation_risk: interior air dry-bulb temperature (C)."),
        ] = None,
        interior_rh: Annotated[
            float | None,
            Field(description="For condensation_risk: interior relative humidity (0..1 fraction or 0..100%).", ge=0, le=100),
        ] = None,
        exterior_temp_c: Annotated[
            float | None,
            Field(description="For condensation_risk: exterior boundary temperature (C)."),
        ] = None,
        interior_surface_temp_c: Annotated[
            float | None,
            Field(description="For condensation_risk: optional explicit interior surface temperature (C)."),
        ] = None,
        clear_field_u_values: Annotated[
            list[dict[str, Any]] | None,
            Field(description="For psi_factor: clear-field segments [{u_value, length, name?}]."),
        ] = None,
        u_factor_name: Annotated[
            str | None,
            Field(description="For psi_factor: optional U-factor tag name to select."),
        ] = None,
        projection: Annotated[
            Literal["total", "projected_x", "projected_y", "projected_in_glass_plane", "custom_rotation", "auto"],
            Field(description="For psi_factor: UFactor projection used to compute L_2D."),
        ] = "total",
        l_2d_w_per_mk: Annotated[
            float | None,
            Field(description="For psi_factor: optional explicit L_2D coupling coefficient (W/m-K)."),
        ] = None,
        length_unit: Annotated[
            str,
            Field(description="For psi_factor: unit of clear_field_u_values lengths (default Meters)."),
        ] = "Meters",
        therm_length_unit: Annotated[
            str,
            Field(description="For psi_factor: unit of THERM UFactor lengths (default Millimeters)."),
        ] = "Millimeters",
    ) -> QueryResultModel:
        """Read Fairyfly steady-state or transient/hygrothermal results."""
        dumped_thmz_target = dump_target(thmz_target)
        dumped_run_target = dump_target(run_target)
        if data_type == "u_factor":
            from garden.fairyfly.therm import read_fairyfly_u_factor_result as service

            return validate_output(
                QueryResultModel,
                service(
                    garden_root=garden_root,
                    thmz_target=dumped_thmz_target,
                    run_target=dumped_run_target,
                    run_id=run_id,
                ),
            )
        if data_type == "condensation_risk":
            from garden.fairyfly.therm import read_fairyfly_condensation_risk as service

            return validate_output(
                QueryResultModel,
                service(
                    garden_root=garden_root,
                    thmz_target=dumped_thmz_target,
                    run_target=dumped_run_target,
                    run_id=run_id,
                    model_target=dump_target(model_target),
                    interior_temp_c=interior_temp_c,
                    interior_rh=interior_rh,
                    exterior_temp_c=exterior_temp_c,
                    interior_surface_temp_c=interior_surface_temp_c,
                    timestep_index=timestep_index,
                ),
            )
        if data_type == "psi_factor":
            from garden.fairyfly.therm import read_fairyfly_psi_factor as service

            return validate_output(
                QueryResultModel,
                service(
                    garden_root=garden_root,
                    thmz_target=dumped_thmz_target,
                    run_target=dumped_run_target,
                    run_id=run_id,
                    clear_field_u_values=dump_input(clear_field_u_values) or [],
                    u_factor_name=u_factor_name,
                    projection=projection,
                    l_2d_w_per_mk=l_2d_w_per_mk,
                    length_unit=length_unit,
                    therm_length_unit=therm_length_unit,
                ),
            )
        if data_type == "transient_summary":
            from garden.fairyfly.therm import read_fairyfly_transient_summary as service

            return validate_output(
                QueryResultModel,
                service(
                    garden_root=garden_root,
                    thmz_target=dumped_thmz_target,
                    run_target=dumped_run_target,
                    run_id=run_id,
                ),
            )
        if data_type == "transient_series":
            from garden.fairyfly.therm import read_fairyfly_transient_series as service

            return validate_output(
                QueryResultModel,
                service(
                    garden_root=garden_root,
                    thmz_target=dumped_thmz_target,
                    run_target=dumped_run_target,
                    run_id=run_id,
                    field=field,
                    entity_ids=entity_ids,
                    timestep_index=timestep_index,
                    include_values=include_values,
                ),
            )
        from garden.fairyfly.therm import read_fairyfly_therm_result as service

        return validate_output(
            QueryResultModel,
            service(
                garden_root=garden_root,
                thmz_target=dumped_thmz_target,
                run_target=dumped_run_target,
                run_id=run_id,
                data_type=data_type,
                timestep_index=timestep_index,
                include_values=include_values,
            ),
        )

    @mcp.tool(
        name="FF_To_Visualization_Set",
        description=(
            "Create a Ladybug Display VisualizationSet from a Garden Fairyfly model "
            "(source_kind='model') or completed steady-state/transient temperature, heat-flux, "
            "relative humidity, or water-content results (source_kind='result'). Poll GD_Poll_Run "
            "before visualizing results from a run_target. Set return_visualization_set=false to "
            "save a compact visualization_set_target for LB_Export_Visualization_Set."
        ),
        tags={"fairyfly", "therm", "visualization-set", "model", "result", "visualize", "preview"},
        timeout=60,
    )
    def fairyfly_to_visualization_set(
        garden_root: Annotated[
            str,
            Field(description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."),
        ],
        source_kind: Annotated[
            Literal["model", "result"],
            Field(description="Visualization source: 'model' (default) or 'result'."),
        ] = "model",
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "For source_kind='model': optional Fairyfly Model target dict, usually "
                    "FF_Create_Model['target']; defaults to the Garden base Fairyfly Model."
                )
            ),
        ] = None,
        color_by: Annotated[
            Literal["material", "none"],
            Field(description="For source_kind='model': coloring mode ('material' or 'none')."),
        ] = "material",
        include_boundaries: Annotated[
            bool,
            Field(description="For source_kind='model': whether to include Fairyfly Boundary line geometry."),
        ] = True,
        thmz_target: Annotated[
            ArtifactTargetRef | None,
            Field(description="For source_kind='result': optional fairyfly_thmz target."),
        ] = None,
        run_target: Annotated[
            RunTargetRef | None,
            Field(description="For source_kind='result': optional completed fairyfly_therm_run target."),
        ] = None,
        run_id: Annotated[
            str | None,
            Field(description="For source_kind='result': optional run identifier when targets are omitted."),
        ] = None,
        data_type: Annotated[
            Literal["temperature", "heat_flux", "humidity", "water_content"],
            Field(
                description=(
                    "For source_kind='result': result field to visualize ('temperature', "
                    "'heat_flux', 'humidity', or 'water_content')."
                )
            ),
        ] = "temperature",
        timestep_index: Annotated[
            int | None,
            Field(description="For transient source_kind='result': optional 0-based frame index (default final step)."),
        ] = None,
        name: Annotated[
            str | None,
            Field(description="Optional VisualizationSet identifier and artifact name."),
        ] = None,
        return_visualization_set: Annotated[
            bool,
            Field(
                description=(
                    "Return the full VisualizationSet dict. Set false to save and return a compact "
                    "visualization_set_target for LB_Export_Visualization_Set."
                )
            ),
        ] = True,
    ) -> ArtifactResultModel:
        """Create a VisualizationSet from a Fairyfly model or THERM result."""
        if source_kind == "result":
            from garden.fairyfly.model import (
                fairyfly_therm_result_to_visualization_set as service,
            )

            return validate_output(
                ArtifactResultModel,
                service(
                    garden_root=garden_root,
                    thmz_target=dump_target(thmz_target),
                    run_target=dump_target(run_target),
                    run_id=run_id,
                    data_type=data_type,
                    timestep_index=timestep_index,
                    name=name,
                    return_visualization_set=return_visualization_set,
                ),
            )
        from garden.fairyfly.model import fairyfly_model_to_visualization_set as service

        return validate_output(
            ArtifactResultModel,
            service(
                garden_root=garden_root,
                model_target=dump_target(model_target),
                color_by=color_by,
                include_boundaries=include_boundaries,
                name=name,
                return_visualization_set=return_visualization_set,
            ),
        )
