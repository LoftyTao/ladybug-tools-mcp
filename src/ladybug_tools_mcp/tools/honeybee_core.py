"""honeybee_core MCP tools."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from ladybug_tools_mcp.contracts import (
    ArtifactTargetRef,
    BuildingModelTargetRef,
    BuildingObjectTargetRef,
    LibraryObjectTargetRef,
    MutationResultModel,
    QueryResultModel,
    ValidationResultModel,
    dump_input,
    dump_target,
    dump_targets,
    validate_output,
)

PostprocessStrategy = Literal[
    "none",
    "suggest_validate",
    "auto_validate",
    "auto_relate_existing_geometry",
    "auto_relate_intersect_clone_single",
]


def register(mcp: FastMCP) -> None:
    """Register the 13 consolidated honeybee_core tools."""

    @mcp.tool(
        name="HB_Create_Model",
        description=(
            "Create a new Honeybee Model or import a Garden-local model file "
            "(.hbjson, .osm, .idf, .gbxml, .inp, .hbpkl, .stl) and register it in the Garden."
        ),
        tags={"author", "garden", "hbjson", "honeybee", "import", "model"},
        timeout=60,
    )
    def create_honeybee_model(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        identifier: Annotated[
            str | None,
            Field(description="Model ID (required for new models; optional override on import)."),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional human-readable display name."),
        ] = None,
        import_file_path: Annotated[
            str | None,
            Field(description="Garden-relative model file path (.hbjson/.osm/.idf/.gbxml/.inp/.hbpkl/.stl) to import."),
        ] = None,
        units: Annotated[
            str, Field(description="Model length units (e.g. Meters).")
        ] = "Meters",
        unit_system: Annotated[
            str | None,
            Field(description="Preset unit system: Metric (Meters) or Imperial (Feet)."),
        ] = None,
        tolerance: Annotated[
            float | None, Field(gt=0, description="Model geometric tolerance.")
        ] = None,
        angle_tolerance: Annotated[
            float, Field(gt=0, description="Model angle tolerance in degrees.")
        ] = 1.0,
        geometry_to_faces: Annotated[
            bool,
            Field(description="For .stl imports: convert geometry to Faces instead of ShadeMeshes."),
        ] = False,
        reset_properties: Annotated[
            bool,
            Field(description="For .osm/.idf/.gbxml imports: reset energy properties to defaults."),
        ] = False,
        save_back: Annotated[
            bool,
            Field(description="Persist newly created model to the Garden."),
        ] = True,
        set_base: Annotated[
            bool,
            Field(description="Set as Garden base Honeybee model."),
        ] = True,
        include_body: Annotated[
            bool,
            Field(description="Return full HBJSON dict when save_back is false."),
        ] = False,
        add_objects: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Optional Honeybee Room/Face/Aperture/Door/Shade dicts to include at creation."),
        ] = None,
        postprocess_strategy: Annotated[
            PostprocessStrategy | None,
            Field(description="Postprocess strategy override."),
        ] = None,
    ) -> MutationResultModel:
        """Create or import a Honeybee Model."""
        if unit_system is not None:
            normalized_unit_system = unit_system.strip().lower()
            if normalized_unit_system in {"metric", "si"}:
                units = "Meters"
            elif normalized_unit_system in {"imperial", "ip"}:
                units = "Feet"
            else:
                units = unit_system

        if import_file_path is not None:
            from pathlib import Path

            if (
                Path(import_file_path).suffix.lower() == ".hbjson"
                and not geometry_to_faces
                and not reset_properties
            ):
                from garden.honeybee_core.creation import (
                    import_honeybee_model_with_postprocess as import_service,
                )

                return validate_output(
                    MutationResultModel,
                    import_service(
                        garden_root=garden_root,
                        file_path=import_file_path,
                        identifier=identifier,
                        display_name=display_name,
                        set_base=set_base,
                        postprocess_strategy=postprocess_strategy,
                    ),
                )
            from garden.honeybee_core.model_io import (
                import_honeybee_model_file,
                load_honeybee_model,
                resolve_model_target,
                save_honeybee_model,
            )
            from garden.honeybee_core.postprocess import (
                apply_honeybee_postprocess,
                attach_postprocess_result,
            )

            imported = import_honeybee_model_file(
                garden_root=garden_root,
                file_path=import_file_path,
                identifier=identifier,
                set_base=set_base,
                geometry_to_faces=geometry_to_faces,
                units=units,
                tolerance=tolerance,
                angle_tolerance=angle_tolerance,
                reset_properties=reset_properties,
            )
            if (postprocess_strategy is None or postprocess_strategy == "none") and display_name is None:
                return validate_output(MutationResultModel, imported)
            garden_root_path = Path(garden_root).expanduser().resolve()
            manifest, resolved_target = resolve_model_target(
                garden_root_path,
                imported["model_target"],
            )
            loaded = load_honeybee_model(garden_root_path, resolved_target)
            if display_name is not None:
                loaded.display_name = display_name
                imported.setdefault("summary_view", {})["display_name"] = display_name
            postprocess: dict[str, Any] = {}
            if postprocess_strategy is not None and postprocess_strategy != "none":
                loaded, postprocess = apply_honeybee_postprocess(
                    model=loaded,
                    garden_id=manifest.garden_id,
                    model_identifier=str(resolved_target["model_identifier"]),
                    operation="import_honeybee_model_file",
                    target=resolved_target,
                    object_type="model",
                    strategy=postprocess_strategy,
                )
            if display_name is not None or postprocess_strategy in {
                "auto_relate_existing_geometry",
                "auto_relate_intersect_clone_single",
            }:
                updated_target, persisted_path = save_honeybee_model(
                    garden_root_path,
                    manifest,
                    loaded,
                    name=str(resolved_target["model_identifier"]),
                    set_base=set_base,
                    set_default_base=False,
                )
                imported["target"] = updated_target
                imported["model_target"] = updated_target
                imported["persistence_receipt"]["model_target"] = updated_target
                imported["persistence_receipt"]["persisted_path"] = persisted_path
            return validate_output(
                MutationResultModel,
                attach_postprocess_result(imported, postprocess),
            )

        if not identifier or not identifier.strip():
            raise ValueError(
                "identifier is required when creating a new Honeybee Model without import_file_path."
            )

        from garden.honeybee_core.creation import create_honeybee_model as service

        return validate_output(
            MutationResultModel,
            service(
                garden_root=garden_root,
                identifier=identifier,
                display_name=display_name,
                units=units,
                tolerance=tolerance,
                angle_tolerance=angle_tolerance,
                save_back=save_back,
                set_base=set_base,
                include_body=include_body,
                add_objects=dump_input(add_objects),
                postprocess_strategy=postprocess_strategy,
            ),
        )

    @mcp.tool(
        name="HB_Create_Objects",
        description=(
            "Create one or a batch of Honeybee Rooms, orphaned Faces, or Doors in one Garden save. "
            "Pass single-object kwargs (identifier) or batch items=[{...}, ...]. Use postprocess_strategy='none' "
            "on intermediate batches and run HB_Relate_Model once when done."
        ),
        tags={"author", "batch", "door", "face", "geometry", "honeybee", "room"},
        timeout=30,
    )
    def create_honeybee_objects(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        object_type: Annotated[
            Literal["room", "face", "door"],
            Field(description="Object type: room, face, or door."),
        ],
        items: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Batch item dicts (each with identifier, optional display_name, and room/face/door fields). Mutually exclusive with identifier."
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="Object ID for single-object mode (omit with items)."),
        ] = None,
        display_name: Annotated[
            str | None,
            Field(description="Optional human-readable display name."),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Honeybee model target (defaults to Garden base model)."),
        ] = None,
        faces: Annotated[
            list[dict[str, Any]] | None,
            Field(description="For room: list of Face dicts (shorthand accepted without type/properties/boundary_condition)."),
        ] = None,
        room_geometry: Annotated[
            dict[str, Any] | None,
            Field(description="For room: Polyface3D envelope dict."),
        ] = None,
        x_dim: Annotated[
            float | None,
            Field(gt=0, description="For room: box width (with y_dim, height)."),
        ] = None,
        y_dim: Annotated[
            float | None,
            Field(gt=0, description="For room: box depth (with x_dim, height)."),
        ] = None,
        height: Annotated[
            float | None,
            Field(gt=0, description="For room: box height (with x_dim, y_dim)."),
        ] = None,
        origin: Annotated[
            list[float] | dict[str, Any] | None,
            Field(description="For room: box origin [x, y, z] or {x, y, z}."),
        ] = None,
        geometry: Annotated[
            dict[str, Any] | None,
            Field(description="For face (required) or door (optional explicit Face3D dict)."),
        ] = None,
        host_target: Annotated[
            BuildingObjectTargetRef | None,
            Field(description="For door: host Face target from HB_Search_Model_Objects."),
        ] = None,
        door_width: Annotated[
            float | None,
            Field(gt=0, description="For door: rectangular width (default 0.9) when geometry omitted."),
        ] = None,
        door_height: Annotated[
            float,
            Field(gt=0, description="For door: rectangular height when geometry omitted."),
        ] = 2.1,
        sill_height: Annotated[
            float,
            Field(ge=0, description="For door: sill offset above wall base."),
        ] = 0.05,
        placement: Annotated[
            Literal["auto", "left", "right", "center"],
            Field(description="For door: placement when generating rectangular geometry."),
        ] = "auto",
        is_glass: Annotated[
            bool, Field(description="For door: glass door flag.")
        ] = False,
        postprocess_strategy: Annotated[
            PostprocessStrategy | None,
            Field(description="Postprocess override (default auto_relate_intersect_clone_single)."),
        ] = None,
    ) -> MutationResultModel:
        """Create one or more Honeybee Rooms, Faces, or Doors."""
        raw_model_target = dump_target(model_target)
        raw_host_target = dump_target(host_target)
        if items is not None:
            if identifier is not None:
                raise ValueError("Provide either identifier (single) or items (batch), not both.")
            from garden.honeybee_core.creation import create_honeybee_objects_batch

            return validate_output(
                MutationResultModel,
                create_honeybee_objects_batch(
                    garden_root=garden_root,
                    object_type=object_type,
                    items=dump_input(items),
                    model_target=raw_model_target,
                    default_host_target=raw_host_target,
                    default_display_name=display_name,
                    postprocess_strategy=postprocess_strategy,
                ),
            )

        if not identifier or not identifier.strip():
            raise ValueError(
                "identifier is required when creating a single object without items."
            )

        if object_type == "room":
            from garden.honeybee_core.creation import create_honeybee_room

            return validate_output(
                MutationResultModel,
                create_honeybee_room(
                    garden_root=garden_root,
                    identifier=identifier,
                    display_name=display_name,
                    faces=dump_input(faces),
                    room_geometry=dump_input(room_geometry),
                    x_dim=x_dim,
                    y_dim=y_dim,
                    height=height,
                    origin=dump_input(origin),
                    model_target=raw_model_target,
                    postprocess_strategy=postprocess_strategy,
                ),
            )
        if object_type == "face":
            if geometry is None:
                raise ValueError("geometry is required when object_type is 'face'.")
            from garden.honeybee_core.creation import create_honeybee_face

            return validate_output(
                MutationResultModel,
                create_honeybee_face(
                    garden_root=garden_root,
                    identifier=identifier,
                    geometry=dump_input(geometry),
                    display_name=display_name,
                    model_target=raw_model_target,
                    postprocess_strategy=postprocess_strategy,
                ),
            )
        if raw_host_target is None:
            raise ValueError("host_target is required when object_type is 'door'.")
        from garden.honeybee_core.creation import create_honeybee_door

        return validate_output(
            MutationResultModel,
            create_honeybee_door(
                garden_root=garden_root,
                identifier=identifier,
                host_target=raw_host_target,
                geometry=dump_input(geometry),
                display_name=display_name,
                model_target=raw_model_target,
                is_glass=is_glass,
                door_width=door_width,
                door_height=door_height,
                sill_height=sill_height,
                placement=placement,
                postprocess_strategy=postprocess_strategy,
            ),
        )

    @mcp.tool(
        name="HB_Create_Apertures",
        description="Create Honeybee Apertures on host Face targets via parameters (ratio or width/height), skylight_ratio, guide_surface, or geometry (single or batch).",
        tags={
            "aperture",
            "author",
            "batch",
            "geometry",
            "guide-surface",
            "honeybee",
            "skylight",
            "window",
            "wwr",
        },
        timeout=30,
    )
    def create_honeybee_apertures(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        mode: Annotated[
            Literal["geometry", "parameters", "guide_surface", "skylight_ratio"],
            Field(
                description="Aperture creation mode: parameters (default), skylight_ratio, guide_surface, or geometry."
            ),
        ] = "parameters",
        host_target: Annotated[
            BuildingObjectTargetRef | None,
            Field(
                description="Single host Honeybee Face typed target from HB_Search_Model_Objects."
            ),
        ] = None,
        host_targets: Annotated[
            list[BuildingObjectTargetRef] | None,
            Field(
                description="Batch list of host Honeybee Face typed targets sharing top-level parameters."
            ),
        ] = None,
        items: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Batch list of per-host/per-aperture specification dicts (each overriding host_target and mode fields)."
            ),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Honeybee Model target (defaults to base model)."),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="For mode='geometry': required Honeybee aperture identifier."),
        ] = None,
        geometry: Annotated[
            dict[str, Any] | None,
            Field(
                description="For mode='geometry': required Ladybug Geometry Face3D dict inside the host face."
            ),
        ] = None,
        is_operable: Annotated[
            bool, Field(description="For mode='geometry': whether the aperture is operable.")
        ] = False,
        generation_mode: Annotated[
            Literal["by_ratio", "by_width_height"],
            Field(
                description="For mode='parameters': by_ratio or by_width_height (auto-inferred when aperture_width & aperture_height are given without ratio)."
            ),
        ] = "by_ratio",
        ratio: Annotated[
            float | None,
            Field(
                gt=0,
                lt=1,
                description="Aperture-to-face area ratio between 0 and 1 (for mode='parameters' with by_ratio, or mode='skylight_ratio').",
            ),
        ] = None,
        aperture_width: Annotated[
            float | None,
            Field(gt=0, description="For mode='parameters' + by_width_height: aperture width in model units."),
        ] = None,
        aperture_height: Annotated[
            float | None,
            Field(gt=0, description="For mode='parameters' + by_width_height: aperture height in model units."),
        ] = None,
        sill_height: Annotated[
            float,
            Field(ge=0, description="For mode='parameters' + by_width_height: sill height in model units."),
        ] = 1.0,
        aperture_identifier: Annotated[
            str | None,
            Field(description="Optional aperture identifier for by_width_height mode."),
        ] = None,
        identifier_prefix: Annotated[
            str | None,
            Field(
                description="Optional prefix for generated aperture identifiers in parameters, skylight_ratio, or guide_surface mode."
            ),
        ] = None,
        tolerance: Annotated[
            float,
            Field(gt=0, description="Geometry and ratio matching tolerance."),
        ] = 0.01,
        rect_split: Annotated[
            bool,
            Field(description="Whether by_ratio should split apertures into rectangles when needed."),
        ] = True,
        guide_surfaces: Annotated[
            list[dict[str, Any]] | None,
            Field(description="For mode='guide_surface': list of Ladybug Geometry Face3D guide surface dicts."),
        ] = None,
        postprocess_strategy: Annotated[
            PostprocessStrategy | None,
            Field(
                description="Optional postprocess strategy override; defaults to auto_relate_intersect_clone_single for apertures."
            ),
        ] = None,
    ) -> MutationResultModel:
        """Create Honeybee Apertures on one or more host Faces."""
        raw_host_target = dump_target(host_target)
        raw_host_targets = dump_targets(host_targets)
        raw_model_target = dump_target(model_target)
        if raw_host_targets is not None or items is not None:
            from garden.honeybee_core.creation import create_honeybee_apertures_batch

            return validate_output(
                MutationResultModel,
                create_honeybee_apertures_batch(
                    garden_root=garden_root,
                    mode=mode,
                    host_target=raw_host_target,
                    host_targets=raw_host_targets,
                    items=dump_input(items),
                    model_target=raw_model_target,
                    generation_mode=generation_mode,
                    ratio=ratio,
                    aperture_width=aperture_width,
                    aperture_height=aperture_height,
                    sill_height=sill_height,
                    aperture_identifier=aperture_identifier,
                    identifier_prefix=identifier_prefix,
                    tolerance=tolerance,
                    rect_split=rect_split,
                    guide_surfaces=dump_input(guide_surfaces),
                    is_operable=is_operable,
                    postprocess_strategy=postprocess_strategy,
                ),
            )

        if raw_host_target is None:
            raise ValueError(
                "host_target is required for single-host aperture creation (or pass host_targets/items)."
            )

        if mode == "geometry":
            if not identifier or not identifier.strip():
                raise ValueError("identifier is required when mode is 'geometry'.")
            if geometry is None:
                raise ValueError("geometry is required when mode is 'geometry'.")
            from garden.honeybee_core.creation import create_honeybee_aperture

            return validate_output(
                MutationResultModel,
                create_honeybee_aperture(
                    garden_root=garden_root,
                    identifier=identifier,
                    geometry=dump_input(geometry),
                    host_target=raw_host_target,
                    model_target=raw_model_target,
                    is_operable=is_operable,
                    postprocess_strategy=postprocess_strategy,
                ),
            )
        if mode == "parameters":
            from garden.honeybee_core.creation import (
                create_honeybee_apertures_by_parameters,
            )

            return validate_output(
                MutationResultModel,
                create_honeybee_apertures_by_parameters(
                    garden_root=garden_root,
                    host_target=raw_host_target,
                    generation_mode=generation_mode,
                    model_target=raw_model_target,
                    ratio=ratio,
                    aperture_width=aperture_width,
                    aperture_height=aperture_height,
                    sill_height=sill_height,
                    aperture_identifier=aperture_identifier,
                    identifier_prefix=identifier_prefix,
                    tolerance=tolerance,
                    rect_split=rect_split,
                    postprocess_strategy=postprocess_strategy,
                ),
            )
        if mode == "skylight_ratio":
            if ratio is None:
                raise ValueError("ratio is required when mode is 'skylight_ratio'.")
            from garden.honeybee_core.creation import create_honeybee_skylights_by_ratio

            return validate_output(
                MutationResultModel,
                create_honeybee_skylights_by_ratio(
                    garden_root=garden_root,
                    host_target=raw_host_target,
                    ratio=ratio,
                    model_target=raw_model_target,
                    tolerance=tolerance,
                    identifier_prefix=identifier_prefix,
                    postprocess_strategy=postprocess_strategy,
                ),
            )
        if not guide_surfaces:
            raise ValueError("guide_surfaces is required when mode is 'guide_surface'.")
        from garden.honeybee_core.guide_openings import (
            create_honeybee_apertures_by_guide_surface,
        )

        return validate_output(
            MutationResultModel,
            create_honeybee_apertures_by_guide_surface(
                garden_root=garden_root,
                host_target=raw_host_target,
                guide_surfaces=dump_input(guide_surfaces),
                model_target=raw_model_target,
                tolerance=tolerance,
                identifier_prefix=identifier_prefix,
                postprocess_strategy=postprocess_strategy,
            ),
        )

    @mcp.tool(
        name="HB_Create_Shades",
        description="Create orphaned or hosted Honeybee Shades via geometry or parametric louvers/extruded borders (single or batch).",
        tags={
            "aperture",
            "author",
            "batch",
            "extruded-border",
            "geometry",
            "honeybee",
            "louver",
            "shade",
        },
        timeout=30,
    )
    def create_honeybee_shades(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        mode: Annotated[
            Literal["geometry", "parameters"],
            Field(description="Shade creation mode: geometry (default) or parameters."),
        ] = "geometry",
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Honeybee Model target (defaults to base model)."),
        ] = None,
        host_target: Annotated[
            BuildingObjectTargetRef | None,
            Field(
                description="Optional host Room/Face/Aperture/Door typed target (required for mode='parameters'; omit for orphaned geometry shades)."
            ),
        ] = None,
        host_targets: Annotated[
            list[BuildingObjectTargetRef] | None,
            Field(
                description="Batch list of Face/Aperture typed targets for mode='parameters'."
            ),
        ] = None,
        items: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Batch list of shade specification dicts (identifier + geometry for geometry mode, or host_target + generation_mode + parameters for parameters mode)."
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(description="For single mode='geometry': required unique Honeybee shade identifier."),
        ] = None,
        geometry: Annotated[
            dict[str, Any] | None,
            Field(description="For single mode='geometry': required Ladybug Geometry Face3D dict."),
        ] = None,
        attach_side: Annotated[
            str,
            Field(
                description="For mode='geometry' hosted shades: outdoor or indoor."
            ),
        ] = "outdoor",
        is_detached: Annotated[
            bool, Field(description="For mode='geometry': whether the shade is detached.")
        ] = False,
        generation_mode: Annotated[
            Literal["louver_by_count", "louver_by_distance_between", "extruded_border"]
            | None,
            Field(
                description="For mode='parameters': louver_by_count, louver_by_distance_between, or extruded_border."
            ),
        ] = None,
        parameters: Annotated[
            dict[str, Any] | None,
            Field(
                description="For mode='parameters': parameter object such as {'depth':0.35,'louver_count':2} or {'depth':0.2}."
            ),
        ] = None,
        postprocess_strategy: Annotated[
            PostprocessStrategy | None,
            Field(
                description="Optional postprocess strategy override; defaults to suggest_validate for shades."
            ),
        ] = None,
    ) -> MutationResultModel:
        """Create one or more Honeybee Shades."""
        raw_model_target = dump_target(model_target)
        raw_host_target = dump_target(host_target)
        raw_host_targets = dump_targets(host_targets)
        if raw_host_targets is not None or items is not None:
            from garden.honeybee_core.creation import create_honeybee_shades_batch

            return validate_output(
                MutationResultModel,
                create_honeybee_shades_batch(
                    garden_root=garden_root,
                    mode=mode,
                    host_target=raw_host_target,
                    host_targets=raw_host_targets,
                    items=dump_input(items),
                    model_target=raw_model_target,
                    attach_side=attach_side,
                    is_detached=is_detached,
                    generation_mode=generation_mode,
                    parameters=dump_input(parameters),
                    postprocess_strategy=postprocess_strategy,
                ),
            )

        if mode == "geometry":
            if not identifier or not identifier.strip():
                raise ValueError("identifier is required when mode is 'geometry'.")
            if geometry is None:
                raise ValueError("geometry is required when mode is 'geometry'.")
            from garden.honeybee_core.creation import create_honeybee_shade

            return validate_output(
                MutationResultModel,
                create_honeybee_shade(
                    garden_root=garden_root,
                    identifier=identifier,
                    geometry=dump_input(geometry),
                    model_target=raw_model_target,
                    host_target=raw_host_target,
                    attach_side=attach_side,
                    is_detached=is_detached,
                    postprocess_strategy=postprocess_strategy,
                ),
            )

        if raw_host_target is None:
            raise ValueError("host_target is required when mode is 'parameters'.")
        if not generation_mode:
            raise ValueError("generation_mode is required when mode is 'parameters'.")
        if parameters is None:
            raise ValueError("parameters is required when mode is 'parameters'.")
        from garden.honeybee_core.creation import create_honeybee_shades_by_parameters

        return validate_output(
            MutationResultModel,
            create_honeybee_shades_by_parameters(
                garden_root=garden_root,
                host_target=raw_host_target,
                generation_mode=generation_mode,
                parameters=dump_input(parameters),
                model_target=raw_model_target,
                postprocess_strategy=postprocess_strategy,
            ),
        )

    @mcp.tool(
        name="HB_Edit_Model",
        description=(
            "Edit a Honeybee Model's metadata, units, tolerances, ElectricLoadCenter, object additions/removals, "
            "or Radiance SensorGrid/View attachments."
        ),
        tags={
            "edit",
            "energy",
            "honeybee",
            "model",
            "radiance",
            "remove",
            "sensor-grid",
            "view",
        },
        timeout=30,
    )
    def edit_honeybee_model(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Honeybee model target dict (or pass model_target)."),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Alias for target (Honeybee model target dict)."),
        ] = None,
        display_name: Annotated[
            str | None, Field(description="Updated display name.")
        ] = None,
        user_data: Annotated[
            dict[str, Any] | None,
            Field(description="Replacement user_data dictionary."),
        ] = None,
        units: Annotated[
            str | None, Field(description="Updated Honeybee model units.")
        ] = None,
        convert_geometry: Annotated[
            bool,
            Field(description="Scale geometry and tolerance when changing units (default true)."),
        ] = True,
        tolerance: Annotated[
            float | None, Field(gt=0, description="Updated model tolerance.")
        ] = None,
        angle_tolerance: Annotated[
            float | None, Field(gt=0, description="Updated model angle tolerance.")
        ] = None,
        electric_load_center: Annotated[
            LibraryObjectTargetRef | dict[str, Any] | None,
            Field(description="ElectricLoadCenter dict or Garden library target."),
        ] = None,
        add_objects: Annotated[
            list[dict[str, Any]] | None,
            Field(description="Honeybee Room, Face, Aperture, Door, or Shade dicts to append."),
        ] = None,
        add_sensor_grids: Annotated[
            list[ArtifactTargetRef] | None,
            Field(description="List of radiance_sensor_grid targets to attach."),
        ] = None,
        radiance_sensor_grid_target: Annotated[
            ArtifactTargetRef | None,
            Field(description="Single radiance_sensor_grid target to attach."),
        ] = None,
        add_radiance_views: Annotated[
            list[ArtifactTargetRef] | None,
            Field(description="List of radiance_view targets to attach."),
        ] = None,
        radiance_view_target: Annotated[
            ArtifactTargetRef | None,
            Field(description="Single radiance_view target to attach."),
        ] = None,
        remove_targets: Annotated[
            list[BuildingObjectTargetRef] | None,
            Field(description="Top-level Room or orphaned object targets to remove."),
        ] = None,
        postprocess_strategy: Annotated[
            PostprocessStrategy | None,
            Field(description="Postprocess override (default auto_validate)."),
        ] = None,
    ) -> MutationResultModel:
        """Edit a Honeybee Model."""
        from garden.honeybee_core.edit import edit_honeybee_model as service
        from garden.radiance.assets import (
            attach_radiance_sensor_grids_to_model,
            attach_radiance_views_to_model,
        )

        dumped_target = dump_target(target)
        dumped_model_target = dump_target(model_target)
        if (
            dumped_target is not None
            and dumped_model_target is not None
            and dumped_target != dumped_model_target
        ):
            raise ValueError("Provide either target or model_target, not conflicting targets.")
        raw_target = dumped_target if dumped_target is not None else dumped_model_target
        if not raw_target:
            raise ValueError("HB_Edit_Model requires target or model_target.")
        raw_sensor_grids = dump_targets(add_sensor_grids)
        if raw_sensor_grids is None and radiance_sensor_grid_target is not None:
            dumped_grid = dump_target(radiance_sensor_grid_target)
            if dumped_grid is not None:
                raw_sensor_grids = [dumped_grid]
        raw_radiance_views = dump_targets(add_radiance_views)
        if raw_radiance_views is None and radiance_view_target is not None:
            dumped_view = dump_target(radiance_view_target)
            if dumped_view is not None:
                raw_radiance_views = [dumped_view]
        has_core_edits = any(
            value is not None
            for value in (
                display_name,
                user_data,
                units,
                tolerance,
                angle_tolerance,
                electric_load_center,
                add_objects,
                remove_targets,
            )
        )
        if not has_core_edits and not raw_sensor_grids and not raw_radiance_views:
            raise ValueError(
                "HB_Edit_Model requires at least one model edit, add_sensor_grids, or add_radiance_views input."
            )

        result: dict[str, Any]
        if has_core_edits:
            result = service(
                garden_root=garden_root,
                target=raw_target,
                display_name=display_name,
                user_data=user_data,
                units=units,
                convert_geometry=convert_geometry,
                tolerance=tolerance,
                angle_tolerance=angle_tolerance,
                electric_load_center=dump_input(electric_load_center),
                add_objects=dump_input(add_objects),
                remove_targets=dump_targets(remove_targets),
                postprocess_strategy=postprocess_strategy,
            )
            raw_target = result.get("target") or result.get("model_target") or raw_target
        else:
            result = {
                "target": raw_target,
                "model_target": raw_target,
                "summary_view": {"model_identifier": raw_target.get("identifier")},
            }
        if raw_sensor_grids:
            attachment = attach_radiance_sensor_grids_to_model(
                garden_root=garden_root,
                model_target=raw_target,
                sensor_grid_targets=raw_sensor_grids,
            )
            result["target"] = attachment["target"]
            result["model_target"] = attachment["model_target"]
            result["radiance_sensor_grid_attachment"] = attachment
            result.setdefault("summary_view", {}).update(
                attachment.get("summary_view", {})
            )
            raw_target = attachment["model_target"]
        if raw_radiance_views:
            attachment = attach_radiance_views_to_model(
                garden_root=garden_root,
                model_target=raw_target,
                view_targets=raw_radiance_views,
            )
            result["target"] = attachment["target"]
            result["model_target"] = attachment["model_target"]
            result["radiance_view_attachment"] = attachment
            result.setdefault("summary_view", {}).update(
                attachment.get("summary_view", {})
            )
        return validate_output(MutationResultModel, result)

    @mcp.tool(
        name="HB_Edit_Objects",
        description=(
            "Edit one or multiple Honeybee Rooms, Faces, Apertures, Doors, or Shades in one save. "
            "Select via target, targets=[...], or room_identifiers=[...]."
        ),
        tags={
            "aperture",
            "batch",
            "construction-set",
            "door",
            "edit",
            "energy",
            "face",
            "honeybee",
            "program-type",
            "radiance",
            "room",
            "shade",
        },
        timeout=30,
    )
    def edit_honeybee_objects(
        garden_root: Annotated[
            str,
            Field(description="Garden root path."),
        ],
        target: Annotated[
            BuildingObjectTargetRef | str | None,
            Field(description="Object target or room ID (mutually exclusive with targets/room_identifiers)."),
        ] = None,
        targets: Annotated[
            list[BuildingObjectTargetRef] | None,
            Field(description="Batch object targets."),
        ] = None,
        room_identifiers: Annotated[
            list[str] | None,
            Field(description="Batch Room IDs."),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Model target (defaults to Garden base model)."),
        ] = None,
        display_name: Annotated[
            str | None, Field(description="Updated display name.")
        ] = None,
        user_data: Annotated[
            Any,
            Field(description="Replacement user_data dict."),
        ] = None,
        geometry: Annotated[
            Any,
            Field(description="Face3D dict for Face/sub-face/Shade."),
        ] = None,
        multiplier: Annotated[
            int | None,
            Field(ge=1, description="Room multiplier >= 1."),
        ] = None,
        zone: Annotated[
            str | None, Field(description="Room zone name.")
        ] = None,
        story: Annotated[
            str | None, Field(description="Room story name.")
        ] = None,
        exclude_floor_area: Annotated[
            bool | None,
            Field(description="Room exclude_floor_area flag."),
        ] = None,
        energy_properties: Annotated[
            Any,
            Field(description="Room Energy properties dict."),
        ] = None,
        program_type: Annotated[
            Any,
            Field(description="ProgramType dict/target/ID."),
        ] = None,
        construction_set: Annotated[
            Any,
            Field(description="ConstructionSet dict/target/ID."),
        ] = None,
        hvac: Annotated[
            Any,
            Field(description="HVAC dict/target/library ID."),
        ] = None,
        people: Annotated[
            Any,
            Field(description="People load."),
        ] = None,
        lighting: Annotated[
            Any,
            Field(description="Lighting load."),
        ] = None,
        electric_equipment: Annotated[
            Any,
            Field(description="ElectricEquipment load."),
        ] = None,
        gas_equipment: Annotated[
            Any,
            Field(description="GasEquipment load."),
        ] = None,
        service_hot_water: Annotated[
            Any,
            Field(description="ServiceHotWater load."),
        ] = None,
        infiltration: Annotated[
            Any,
            Field(description="Infiltration load."),
        ] = None,
        ventilation: Annotated[
            Any,
            Field(description="Ventilation load."),
        ] = None,
        exhaust: Annotated[
            Any,
            Field(description="ExhaustAir load."),
        ] = None,
        zone_ventilation_fans: Annotated[
            Any,
            Field(description="ZoneVentilation fans."),
        ] = None,
        process_loads: Annotated[
            Any,
            Field(description="Process loads."),
        ] = None,
        internal_masses: Annotated[
            Any,
            Field(description="InternalMass list/ops."),
        ] = None,
        shw: Annotated[
            Any,
            Field(description="SHWSystem."),
        ] = None,
        window_vent_control: Annotated[
            Any,
            Field(description="Window vent control."),
        ] = None,
        daylighting_control: Annotated[
            Any,
            Field(description="DaylightingControl."),
        ] = None,
        make_plenum: Annotated[
            Any,
            Field(description="Make room plenum."),
        ] = None,
        make_ground: Annotated[
            Any,
            Field(description="Make room ground."),
        ] = None,
        reset_fields: Annotated[
            list[str] | None,
            Field(description="Fields to reset."),
        ] = None,
        setpoint: Annotated[
            Any,
            Field(description="Setpoint."),
        ] = None,
        modifier_set: Annotated[
            Any,
            Field(description="ModifierSet."),
        ] = None,
        face_type: Annotated[
            Any,
            Field(description="Face type name or dict."),
        ] = None,
        boundary_condition: Annotated[
            Any,
            Field(description="Boundary condition."),
        ] = None,
        vent_crack: Annotated[
            Any,
            Field(description="Face AFNCrack dict."),
        ] = None,
        is_operable: Annotated[
            bool | None,
            Field(description="Aperture operable flag."),
        ] = None,
        is_glass: Annotated[
            bool | None,
            Field(description="Door glass flag."),
        ] = None,
        is_detached: Annotated[
            bool | None,
            Field(description="Orphaned Shade detached flag."),
        ] = None,
        construction: Annotated[
            Any,
            Field(description="Construction dict/target/ID."),
        ] = None,
        vent_opening: Annotated[
            Any,
            Field(description="VentilationOpening."),
        ] = None,
        transmittance_schedule: Annotated[
            Any,
            Field(description="Transmittance schedule."),
        ] = None,
        pv_properties: Annotated[
            Any,
            Field(description="PVProperties."),
        ] = None,
        modifier: Annotated[
            Any,
            Field(description="Modifier."),
        ] = None,
        modifier_blk: Annotated[
            Any,
            Field(description="Back modifier."),
        ] = None,
        dynamic_group_identifier: Annotated[
            str | None,
            Field(description="Dynamic group ID."),
        ] = None,
        states: Annotated[
            Any,
            Field(description="Radiance states."),
        ] = None,
        postprocess_strategy: Annotated[
            str | None,
            Field(description="Postprocess strategy override."),
        ] = None,
    ) -> MutationResultModel:
        """Edit one or multiple Honeybee objects in one atomic save."""
        from garden.honeybee_core.edit import edit_honeybee_objects as service

        return validate_output(
            MutationResultModel,
            service(
                garden_root=garden_root,
                target=dump_input(target),
                targets=dump_targets(targets),
                room_identifiers=room_identifiers,
                model_target=dump_target(model_target),
                display_name=display_name,
                user_data=user_data,
                geometry=dump_input(geometry),
                multiplier=multiplier,
                zone=zone,
                story=story,
                exclude_floor_area=exclude_floor_area,
                energy_properties=dump_input(energy_properties),
                program_type=dump_input(program_type),
                construction_set=dump_input(construction_set),
                hvac=dump_input(hvac),
                people=dump_input(people),
                lighting=dump_input(lighting),
                electric_equipment=dump_input(electric_equipment),
                gas_equipment=dump_input(gas_equipment),
                service_hot_water=dump_input(service_hot_water),
                infiltration=dump_input(infiltration),
                ventilation=dump_input(ventilation),
                exhaust=dump_input(exhaust),
                zone_ventilation_fans=dump_input(zone_ventilation_fans),
                process_loads=dump_input(process_loads),
                internal_masses=dump_input(internal_masses),
                shw=dump_input(shw),
                window_vent_control=dump_input(window_vent_control),
                daylighting_control=dump_input(daylighting_control),
                make_plenum=dump_input(make_plenum),
                make_ground=dump_input(make_ground),
                reset_fields=reset_fields,
                setpoint=dump_input(setpoint),
                modifier_set=dump_input(modifier_set),
                face_type=dump_input(face_type),
                boundary_condition=dump_input(boundary_condition),
                vent_crack=dump_input(vent_crack),
                is_operable=is_operable,
                is_glass=is_glass,
                is_detached=is_detached,
                construction=dump_input(construction),
                vent_opening=dump_input(vent_opening),
                transmittance_schedule=dump_input(transmittance_schedule),
                pv_properties=dump_input(pv_properties),
                modifier=dump_input(modifier),
                modifier_blk=dump_input(modifier_blk),
                dynamic_group_identifier=dynamic_group_identifier,
                states=dump_input(states),
                postprocess_strategy=postprocess_strategy,
            ),
        )

    @mcp.tool(
        name="HB_Transform_Objects",
        description="Move, rotate, scale, or mirror one or a batch of Honeybee Model or object targets in one atomic save.",
        tags={
            "batch",
            "edit",
            "geometry",
            "honeybee",
            "mirror",
            "model",
            "move",
            "rotate",
            "scale",
            "transform",
        },
        timeout=30,
    )
    def transform_objects(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        operation: Annotated[
            Literal["move", "rotate", "scale", "mirror"],
            Field(description="Required geometric transform operation: move, rotate, scale, or mirror."),
        ],
        target: Annotated[
            BuildingObjectTargetRef | BuildingModelTargetRef | None,
            Field(
                description="Single Honeybee model target or object typed target. Mutually exclusive with targets."
            ),
        ] = None,
        targets: Annotated[
            list[BuildingObjectTargetRef | BuildingModelTargetRef] | None,
            Field(
                description="Batch list of Honeybee model or object typed targets to transform in one save."
            ),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(
                description="Optional Honeybee model target dict; defaults to the Garden base Honeybee Model unless target is a model target."
            ),
        ] = None,
        vector: Annotated[
            dict[str, Any] | list[float] | None,
            Field(
                description="Required for operation='move': Ladybug Vector3D dict ({'x':dx,'y':dy,'z':dz}) or [dx, dy, dz]."
            ),
        ] = None,
        axis: Annotated[
            dict[str, Any] | list[float] | None,
            Field(
                description="Required for operation='rotate': Ladybug Vector3D axis dict or [x, y, z]."
            ),
        ] = None,
        angle_degrees: Annotated[
            float | None,
            Field(description="Required for operation='rotate': rotation angle in degrees."),
        ] = None,
        origin: Annotated[
            dict[str, Any] | list[float] | None,
            Field(
                description="Point3D dict or [x, y, z] origin (required for rotate, optional for scale)."
            ),
        ] = None,
        factor: Annotated[
            float | None,
            Field(gt=0, description="Required for operation='scale': positive scale factor."),
        ] = None,
        plane: Annotated[
            dict[str, Any] | None,
            Field(
                description="Required for operation='mirror': Ladybug Plane dict with origin 'o' and normal 'n'."
            ),
        ] = None,
        postprocess_strategy: Annotated[
            PostprocessStrategy | None,
            Field(description="Postprocess strategy override."),
        ] = None,
    ) -> MutationResultModel:
        """Move, rotate, scale, or mirror Honeybee targets."""
        from garden.honeybee_core.transform import transform_objects as service

        return validate_output(
            MutationResultModel,
            service(
                garden_root=garden_root,
                operation=operation,
                target=dump_target(target),
                targets=dump_targets(targets),
                model_target=dump_target(model_target),
                vector=dump_input(vector),
                axis=dump_input(axis),
                angle_degrees=angle_degrees,
                origin=dump_input(origin),
                factor=factor,
                plane=dump_input(plane),
                postprocess_strategy=postprocess_strategy,
            ),
        )

    @mcp.tool(
        name="HB_Remove_Objects",
        description="Remove one or more Honeybee Rooms, orphaned Faces, Apertures, Doors, or Shades in one atomic save.",
        tags={
            "aperture",
            "batch",
            "door",
            "edit",
            "face",
            "honeybee",
            "remove",
            "room",
            "shade",
        },
        timeout=30,
    )
    def remove_honeybee_objects(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        target: Annotated[
            BuildingObjectTargetRef | None,
            Field(
                description="Single Honeybee object typed target from HB_Search_Model_Objects. Mutually exclusive with targets."
            ),
        ] = None,
        targets: Annotated[
            list[BuildingObjectTargetRef] | None,
            Field(
                description="Batch list of Honeybee object typed targets to remove in one save."
            ),
        ] = None,
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Honeybee Model target (defaults to base model)."),
        ] = None,
        postprocess_strategy: Annotated[
            PostprocessStrategy | None,
            Field(description="Postprocess strategy override."),
        ] = None,
    ) -> MutationResultModel:
        """Remove one or more Honeybee objects by typed target."""
        from garden.honeybee_core.removal import remove_honeybee_objects as service

        return validate_output(
            MutationResultModel,
            service(
                garden_root=garden_root,
                target=dump_target(target),
                targets=dump_targets(targets),
                model_target=dump_target(model_target),
                postprocess_strategy=postprocess_strategy,
            ),
        )

    @mcp.tool(
        name="HB_Relate_Model",
        description="Solve Honeybee room adjacencies, Surface boundary conditions, optional intersection, coplanar merge, and AirBoundary/adiabatic settings. Use explicit_relate_full only for explicit cleanup/mismatch repair.", 
        tags={
            "adjacency",
            "boundary",
            "cleanup",
            "edit",
            "geometry",
            "honeybee",
            "model",
            "repair",
            "validate",
        },
        timeout=30,
    )
    def relate_honeybee_model(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Honeybee Model target (defaults to base model)."),
        ] = None,
        relation_mode: Annotated[
            Literal["solve_adjacency", "explicit_relate_full"],
            Field(
                description="Relation mode: solve_adjacency or explicit_relate_full. explicit_relate_full enables high-risk overwrite, cleanup, remove_mismatched_subfaces, and clone_missing Aperture/Door repair defaults."
            ),
        ] = "solve_adjacency",
        solve_adjacency: Annotated[
            bool | None,
            Field(
                description="Optional solve-adjacency flag. Passing true is equivalent to relation_mode='solve_adjacency'."
            ),
        ] = None,
        intersect: Annotated[
            bool,
            Field(
                description="Whether to intersect Room Faces before solving adjacency. Defaults to true for the standard relate flow."
            ),
        ] = True,
        merge_coplanar: Annotated[
            bool,
            Field(
                description="Whether to merge coplanar Room Faces before solving adjacency."
            ),
        ] = False,
        overwrite: Annotated[
            bool,
            Field(
                description="Whether existing Surface boundary conditions should be overwritten."
            ),
        ] = False,
        remove_mismatched_sub_faces: Annotated[
            bool,
            Field(
                description="Whether mismatched adjacent sub-faces should be removed. Defaults to false; prefer subface_mismatch_policy."
            ),
        ] = False,
        subface_mismatch_policy: Annotated[
            Literal["none", "clone_single", "clone_missing"],
            Field(
                description="How to handle one-sided Aperture/Door sub-face mismatches before solving adjacency: clone_single, clone_missing, or none."
            ),
        ] = "clone_single",
        air_boundary: Annotated[
            bool,
            Field(
                description="Whether solved wall adjacencies should become AirBoundary faces."
            ),
        ] = False,
        adiabatic: Annotated[
            bool,
            Field(
                description="Whether solved adjacencies should become adiabatic when supported."
            ),
        ] = False,
        relationship_cleanup: Annotated[
            bool,
            Field(
                description="Whether to clear existing Surface boundary conditions before solving. explicit_relate_full enables this automatically."
            ),
        ] = False,
        tolerance: Annotated[
            float | None,
            Field(
                gt=0,
                description="Optional distance tolerance. Defaults to model tolerance.",
            ),
        ] = None,
        angle_tolerance: Annotated[
            float | None,
            Field(
                gt=0,
                description="Optional angle tolerance in degrees. Defaults to model angle tolerance.",
            ),
        ] = None,
    ) -> MutationResultModel:
        """Solve Honeybee model relationships with the SDK."""
        from garden.honeybee_core.relate import relate_honeybee_model as service

        if solve_adjacency is True:
            relation_mode = "solve_adjacency"
        return validate_output(
            MutationResultModel,
            service(
                garden_root=garden_root,
                model_target=dump_target(model_target),
                relation_mode=relation_mode,
                intersect=intersect,
                merge_coplanar=merge_coplanar,
                overwrite=overwrite,
                remove_mismatched_sub_faces=remove_mismatched_sub_faces,
                subface_mismatch_policy=subface_mismatch_policy,
                air_boundary=air_boundary,
                adiabatic=adiabatic,
                relationship_cleanup=relationship_cleanup,
                tolerance=tolerance,
                angle_tolerance=angle_tolerance,
            ),
        )

    @mcp.tool(
        name="HB_Search_Model_Objects",
        description=(
            "Search Honeybee Rooms, Faces, Apertures, Doors, and Shades by object_type, identifier, "
            "query, room_identifier, face_identifier, face_type, boundary_condition, orientation, "
            "story, zone, min_area, max_area, or parent_target/children_scope (typed parent target dict, "
            "NOT 'direct'/'all'/'faces')."
        ),
        tags={
            "aperture",
            "children",
            "door",
            "face",
            "honeybee",
            "model",
            "orientation",
            "room",
            "search",
            "shade",
            "target",
            "wall",
            "window",
        },
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def search_honeybee_model_objects(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        model_target: Annotated[
            BuildingModelTargetRef | BuildingObjectTargetRef | None,
            Field(description="Honeybee Model target (defaults to base model)."),
        ] = None,
        object_type: Annotated[
            Literal["all", "room", "face", "aperture", "door", "shade"],
            Field(
                description="Object type to return: all, room, face, aperture, door, or shade."
            ),
        ] = "all",
        identifier: Annotated[
            str | None,
            Field(
                description="Optional exact Honeybee object identifier or display name filter."
            ),
        ] = None,
        room_identifier: Annotated[
            str | None,
            Field(
                description="Optional parent room identifier filter for faces, apertures, doors, or shades."
            ),
        ] = None,
        face_identifier: Annotated[
            str | None,
            Field(
                description="Optional parent face identifier filter for apertures, doors, or shades (or face identifier when object_type=face)."
            ),
        ] = None,
        query: Annotated[
            str | None,
            Field(
                description="Optional identifier/display-name/metadata substring query."
            ),
        ] = None,
        face_type: Annotated[
            str | None,
            Field(
                description="Optional face type filter, for example Wall, Floor, RoofCeiling, or AirBoundary."
            ),
        ] = None,
        boundary_condition: Annotated[
            str | dict[str, Any] | None,
            Field(
                description="Optional boundary condition filter, for example Outdoors or {type: Outdoors}."
            ),
        ] = None,
        children_scope: Annotated[
            BuildingObjectTargetRef | None,
            Field(
                description="Typed Honeybee parent target dict (room, face, aperture, or door; alias: parent_target) to filter child objects — do NOT pass strings like 'direct', 'all', or 'faces' (use object_type instead)."
            ),
        ] = None,
        parent_target: Annotated[
            BuildingObjectTargetRef | None,
            Field(
                description="Alias for children_scope: typed Honeybee parent target dict (room, face, aperture, or door) to filter child objects."
            ),
        ] = None,
        orientation: Annotated[
            Literal[
                "N",
                "NE",
                "E",
                "SE",
                "S",
                "SW",
                "W",
                "NW",
                "horizontal_up",
                "horizontal_down",
            ]
            | None,
            Field(
                description="Optional orientation filter derived from surface normal (N=(0,1,0), E=(1,0,0), S=(0,-1,0), W=(-1,0,0), z>=0.7 horizontal_up, z<=-0.7 horizontal_down)."
            ),
        ] = None,
        story: Annotated[
            str | None,
            Field(description="Optional Room story filter (also matches children of rooms on that story)."),
        ] = None,
        zone: Annotated[
            str | None,
            Field(description="Optional Room zone filter (also matches children of rooms in that zone)."),
        ] = None,
        min_area: Annotated[
            float | None,
            Field(ge=0, description="Optional minimum area filter in model area units (floor_area for Rooms, face area for Faces/sub-faces/Shades)."),
        ] = None,
        max_area: Annotated[
            float | None,
            Field(ge=0, description="Optional maximum area filter in model area units."),
        ] = None,
        limit: Annotated[
            int | None,
            Field(ge=1, description="Optional maximum number of object matches to return."),
        ] = None,
    ) -> QueryResultModel:
        """Search Honeybee objects and return typed targets."""
        from garden.honeybee_core.search import (
            search_honeybee_model_objects as service,
        )

        for scope_name, raw_scope in (("children_scope", children_scope), ("parent_target", parent_target)):
            if isinstance(raw_scope, str):
                raise ValueError(
                    f"{scope_name} must be a typed Honeybee parent target dict (room, face, aperture, or door), "
                    f"not string {raw_scope!r}. Filter by object_type, room_identifier, or face_identifier instead."
                )
        dumped_scope = dump_target(children_scope)
        dumped_parent = dump_target(parent_target)
        if (
            dumped_scope is not None
            and dumped_parent is not None
            and dumped_scope != dumped_parent
        ):
            raise ValueError("Provide either children_scope or parent_target, not conflicting targets.")
        resolved_scope = dumped_parent if dumped_parent is not None else dumped_scope

        return validate_output(
            QueryResultModel,
            service(
                garden_root=garden_root,
                model_target=dump_target(model_target),
                object_type=object_type,
                identifier=identifier,
                room_identifier=room_identifier,
                face_identifier=face_identifier,
                query=query,
                face_type=face_type,
                boundary_condition=dump_input(boundary_condition),
                children_scope=resolved_scope,
                orientation=orientation,
                story=story,
                zone=zone,
                min_area=min_area,
                max_area=max_area,
                limit=limit,
            ),
        )

    @mcp.tool(
        name="HB_Get_Model_Summary",
        description="Return a read-only summary of a Honeybee Model (counts, areas, WWR, stories/zones, Energy/Radiance coverage).",
        tags={"energy", "honeybee", "model", "radiance", "summary", "wwr"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_honeybee_model_summary(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Honeybee Model target (defaults to base model)."),
        ] = None,
    ) -> QueryResultModel:
        """Summarize Honeybee model geometry, WWR, and Energy/Radiance coverage."""
        from garden.honeybee_core.search import (
            get_honeybee_model_summary as service,
        )

        return validate_output(
            QueryResultModel,
            service(garden_root=garden_root, model_target=dump_target(model_target)),
        )

    @mcp.tool(
        name="HB_Validate_Model",
        description=(
            "Validate an existing Honeybee model in a Garden using Honeybee Model.check_all "
            "(read-only). Returns is_valid/valid, issues, summary_view, and report."
        ),
        tags={
            "check",
            "honeybee",
            "issues",
            "model",
            "summary",
            "validate",
            "validation-report",
        },
        annotations={"readOnlyHint": True},
        timeout=30,
    )
    def validate_honeybee_model(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Honeybee Model target (defaults to base model)."),
        ] = None,
    ) -> ValidationResultModel:
        """Validate a Honeybee model and return structured issues."""
        from garden.honeybee_core.model_io import (
            validate_honeybee_model as service,
        )

        return validate_output(
            ValidationResultModel,
            service(garden_root=garden_root, model_target=dump_target(model_target)),
        )

    @mcp.tool(
        name="HB_Repair_Model",
        description="Repair, clean, merge (add_model), or compare (comparison_report) Honeybee models in a Garden.",
        tags={
            "cleanup",
            "compare",
            "geometry",
            "honeybee",
            "merge",
            "model",
            "repair",
            "story",
        },
        timeout=60,
    )
    def repair_honeybee_model(
        garden_root: Annotated[
            str,
            Field(description="Garden root path containing garden.json."),
        ],
        action: Annotated[
            Literal[
                "remove_degenerate_geometry",
                "triangulate_non_planar_quads",
                "clean_irrational_geometry",
                "split_rooms_through_holes",
                "rooms_to_extrusions",
                "reset_coordinate_system",
                "clean_envelope",
                "fix_invalid_sub_faces",
                "missing_adjacencies_to_adiabatic",
                "assign_stories_by_floor_height",
                "add_model",
                "comparison_report",
            ],
            Field(description="Repair, cleanup, merge, or comparison action to execute."),
        ],
        model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(description="Honeybee Model target (defaults to base model)."),
        ] = None,
        other_model_target: Annotated[
            BuildingModelTargetRef | None,
            Field(
                description="Required for action='add_model' or 'comparison_report': second Honeybee model target dict."
            ),
        ] = None,
        other_model_prefix: Annotated[
            str | None,
            Field(
                description="Optional identifier prefix applied to other_model_target before merging in action='add_model'."
            ),
        ] = None,
        tolerance: Annotated[
            float | None,
            Field(gt=0, description="Optional geometric tolerance override (defaults to model tolerance)."),
        ] = None,
        angle_tolerance: Annotated[
            float | None,
            Field(gt=0, description="Optional angle tolerance override in degrees (defaults to model angle_tolerance)."),
        ] = None,
        new_origin: Annotated[
            dict[str, Any] | list[float] | None,
            Field(description="For action='reset_coordinate_system': optional Point3D dict or [x, y, z] origin."),
        ] = None,
        trim_with_parent: Annotated[
            bool,
            Field(description="For action='fix_invalid_sub_faces': trim sub-faces extending past parent face."),
        ] = True,
        union_overlaps: Annotated[
            bool,
            Field(description="For action='fix_invalid_sub_faces': union overlapping or touching sub-faces."),
        ] = True,
        offset_distance: Annotated[
            float,
            Field(ge=0, description="For action='fix_invalid_sub_faces': inward edge offset distance after trimming."),
        ] = 0.05,
        include_surface_faces: Annotated[
            bool,
            Field(description="For action='fix_invalid_sub_faces': also process Surface-adjacent faces (default false)."),
        ] = False,
        min_difference: Annotated[
            float,
            Field(gt=0, description="For action='assign_stories_by_floor_height': minimum elevation difference between distinct stories."),
        ] = 2.0,
        overwrite: Annotated[
            bool,
            Field(description="For action='assign_stories_by_floor_height': overwrite existing room story assignments."),
        ] = False,
        ignore_deleted: Annotated[
            bool,
            Field(description="For action='comparison_report': omit deleted_objects from the report."),
        ] = False,
        ignore_added: Annotated[
            bool,
            Field(description="For action='comparison_report': omit added_objects from the report."),
        ] = False,
        postprocess_strategy: Annotated[
            PostprocessStrategy | None,
            Field(description="Optional postprocess strategy override for mutating repair actions."),
        ] = None,
    ) -> MutationResultModel:
        """Run Honeybee Model repair, cleanup, merge, or comparison diagnostics."""
        from garden.honeybee_core.repair import repair_honeybee_model as service

        return validate_output(
            MutationResultModel,
            service(
                garden_root=garden_root,
                action=action,
                model_target=dump_target(model_target),
                other_model_target=dump_target(other_model_target),
                other_model_prefix=other_model_prefix,
                tolerance=tolerance,
                angle_tolerance=angle_tolerance,
                new_origin=dump_input(new_origin),
                trim_with_parent=trim_with_parent,
                union_overlaps=union_overlaps,
                offset_distance=offset_distance,
                include_surface_faces=include_surface_faces,
                min_difference=min_difference,
                overwrite=overwrite,
                ignore_deleted=ignore_deleted,
                ignore_added=ignore_added,
                postprocess_strategy=postprocess_strategy,
            ),
        )
