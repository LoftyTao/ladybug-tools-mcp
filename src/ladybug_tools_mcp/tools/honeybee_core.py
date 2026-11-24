"""honeybee_core MCP tools."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

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
            "Create a new empty Honeybee Model or import a Garden-local model file "
            "(.hbjson, .osm, .idf, .gbxml, .inp, .hbpkl, .stl when import_file_path is provided) "
            "and register it in the Garden. Typically followed by HB_Create_Objects for "
            "rooms/faces/doors. Returns target, model_target, summary_view, persistence_receipt, "
            "and report."
        ),
        tags={"author", "garden", "hbjson", "honeybee", "import", "model"},
        timeout=60,
    )
    def create_honeybee_model(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        identifier: Annotated[
            str | None,
            Field(
                description="Honeybee model identifier (required when creating a new model; optional override when importing from import_file_path)."
            ),
        ] = None,
        import_file_path: Annotated[
            str | None,
            Field(
                description="Optional Garden-relative .hbjson, .osm, .idf, .gbxml, .inp, .hbpkl, or .stl file path to import instead of creating an empty model."
            ),
        ] = None,
        units: Annotated[
            str, Field(description="Honeybee model units string, for example Meters.")
        ] = "Meters",
        unit_system: Annotated[
            str | None,
            Field(
                description="Optional unit system such as Metric or Imperial. Metric maps to Meters; Imperial maps to Feet."
            ),
        ] = None,
        tolerance: Annotated[
            float | None, Field(description="Optional model tolerance.")
        ] = None,
        angle_tolerance: Annotated[
            float, Field(description="Model angle tolerance.")
        ] = 1.0,
        geometry_to_faces: Annotated[
            bool,
            Field(
                description="For .stl imports: import geometry as Honeybee Faces instead of ShadeMeshes (default false)."
            ),
        ] = False,
        reset_properties: Annotated[
            bool,
            Field(
                description="For .osm/.idf/.gbxml imports: reset energy properties to defaults instead of importing OpenStudio assignments (default false)."
            ),
        ] = False,
        save_back: Annotated[
            bool,
            Field(
                description="Whether to persist a newly created Honeybee Model to the Garden."
            ),
        ] = True,
        set_base: Annotated[
            bool,
            Field(description="Whether to set as the Garden base Honeybee model."),
        ] = True,
        include_body: Annotated[
            bool,
            Field(
                description="Whether to return the full Honeybee Model body when save_back is false."
            ),
        ] = False,
        add_objects: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Optional complete Honeybee Room, Face, Aperture, Door, or Shade object "
                    "dictionaries to include at creation (for typical modeling, omit and call "
                    "HB_Create_Objects next)."
                )
            ),
        ] = None,
        postprocess_strategy: Annotated[
            PostprocessStrategy | None,
            Field(
                description="Optional postprocess strategy override (none, suggest_validate, auto_validate, auto_relate_existing_geometry, auto_relate_intersect_clone_single)."
            ),
        ] = None,
    ) -> dict[str, Any]:
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

                return import_service(
                    garden_root=garden_root,
                    file_path=import_file_path,
                    identifier=identifier,
                    set_base=set_base,
                    postprocess_strategy=postprocess_strategy,
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
            if postprocess_strategy is None or postprocess_strategy == "none":
                return imported
            garden_root_path = Path(garden_root).expanduser().resolve()
            manifest, resolved_target = resolve_model_target(
                garden_root_path,
                imported["model_target"],
            )
            loaded = load_honeybee_model(garden_root_path, resolved_target)
            loaded, postprocess = apply_honeybee_postprocess(
                model=loaded,
                garden_id=manifest.garden_id,
                model_identifier=str(resolved_target["model_identifier"]),
                operation="import_honeybee_model_file",
                target=resolved_target,
                object_type="model",
                strategy=postprocess_strategy,
            )
            if postprocess_strategy in {
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
            return attach_postprocess_result(imported, postprocess)

        if not identifier or not identifier.strip():
            raise ValueError(
                "identifier is required when creating a new Honeybee Model without import_file_path."
            )

        from garden.honeybee_core.creation import create_honeybee_model as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            units=units,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
            save_back=save_back,
            set_base=set_base,
            include_body=include_body,
            add_objects=add_objects,
            postprocess_strategy=postprocess_strategy,
        )

    @mcp.tool(
        name="HB_Create_Objects",
        description=(
            "Create one or a batch of Honeybee Rooms, orphaned Faces, or Doors in a single "
            "Garden save. Set object_type to 'room', 'face', or 'door'. Pass single-object "
            "kwargs (with identifier) or a batch list in items=[{...}, ...] to build multiple "
            "objects with deferred postprocess_strategy (pass postprocess_strategy='none' on "
            "intermediate batch steps and run HB_Relate_Model once when done)."
        ),
        tags={"author", "batch", "door", "face", "geometry", "honeybee", "room"},
        timeout=30,
    )
    def create_honeybee_objects(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        object_type: Annotated[
            Literal["room", "face", "door"],
            Field(description="Required object type to create: room, face, or door."),
        ],
        items: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    "Optional batch list of item specification dicts (each with identifier and "
                    "type-specific fields such as x_dim/y_dim/height/origin/faces/room_geometry "
                    "for room, geometry for face, or host_target/geometry/door_width/door_height "
                    "for door). Mutually exclusive with single-object identifier."
                )
            ),
        ] = None,
        identifier: Annotated[
            str | None,
            Field(
                description="Required object identifier for single-object mode (omit when using items)."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
        faces: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="For object_type='room': optional list of complete Honeybee Face dicts."
            ),
        ] = None,
        room_geometry: Annotated[
            dict[str, Any] | None,
            Field(
                description="For object_type='room': optional Ladybug Geometry Polyface3D envelope dict."
            ),
        ] = None,
        x_dim: Annotated[
            float | None,
            Field(description="For object_type='room': box width (with y_dim and height)."),
        ] = None,
        y_dim: Annotated[
            float | None,
            Field(description="For object_type='room': box depth (with x_dim and height)."),
        ] = None,
        height: Annotated[
            float | None,
            Field(description="For object_type='room': box height (with x_dim and y_dim)."),
        ] = None,
        origin: Annotated[
            list[float] | dict[str, Any] | None,
            Field(
                description="For object_type='room': optional box origin as [x, y, z] or {x, y, z}."
            ),
        ] = None,
        geometry: Annotated[
            dict[str, Any] | None,
            Field(
                description="For object_type='face' (required) or 'door' (optional explicit Face3D dict)."
            ),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="For object_type='door': Honeybee Face typed target dict from HB_Search_Model_Objects."
            ),
        ] = None,
        door_width: Annotated[
            float | None,
            Field(
                description="For object_type='door': optional rectangular door width when geometry is omitted (defaults to 0.9)."
            ),
        ] = None,
        door_height: Annotated[
            float,
            Field(
                description="For object_type='door': optional rectangular door height when geometry is omitted."
            ),
        ] = 2.1,
        sill_height: Annotated[
            float,
            Field(
                description="For object_type='door': optional sill offset above host wall base."
            ),
        ] = 0.05,
        placement: Annotated[
            Literal["auto", "left", "right", "center"],
            Field(
                description="For object_type='door': placement preference for generated rectangular doors."
            ),
        ] = "auto",
        is_glass: Annotated[
            bool, Field(description="For object_type='door': whether the door is glass.")
        ] = False,
        postprocess_strategy: Annotated[
            PostprocessStrategy | None,
            Field(
                description="Optional postprocess strategy override; defaults to auto_relate_intersect_clone_single for room/face/door."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create one or more Honeybee Rooms, Faces, or Doors."""
        if items is not None:
            if identifier is not None:
                raise ValueError("Provide either identifier (single) or items (batch), not both.")
            from garden.honeybee_core.creation import create_honeybee_objects_batch

            return create_honeybee_objects_batch(
                garden_root=garden_root,
                object_type=object_type,
                items=items,
                model_target=model_target,
                default_host_target=host_target,
                postprocess_strategy=postprocess_strategy,
            )

        if not identifier or not identifier.strip():
            raise ValueError(
                "identifier is required when creating a single object without items."
            )

        if object_type == "room":
            from garden.honeybee_core.creation import create_honeybee_room

            return create_honeybee_room(
                garden_root=garden_root,
                identifier=identifier,
                faces=faces,
                room_geometry=room_geometry,
                x_dim=x_dim,
                y_dim=y_dim,
                height=height,
                origin=origin,
                model_target=model_target,
                postprocess_strategy=postprocess_strategy,
            )
        if object_type == "face":
            if geometry is None:
                raise ValueError("geometry is required when object_type is 'face'.")
            from garden.honeybee_core.creation import create_honeybee_face

            return create_honeybee_face(
                garden_root=garden_root,
                identifier=identifier,
                geometry=geometry,
                model_target=model_target,
                postprocess_strategy=postprocess_strategy,
            )
        if host_target is None:
            raise ValueError("host_target is required when object_type is 'door'.")
        from garden.honeybee_core.creation import create_honeybee_door

        return create_honeybee_door(
            garden_root=garden_root,
            identifier=identifier,
            host_target=host_target,
            geometry=geometry,
            model_target=model_target,
            is_glass=is_glass,
            door_width=door_width,
            door_height=door_height,
            sill_height=sill_height,
            placement=placement,
            postprocess_strategy=postprocess_strategy,
        )

    @mcp.tool(
        name="HB_Create_Apertures",
        description=(
            "Create Honeybee Apertures (windows or skylights) on one or more host Face targets. "
            "Supports mode='parameters' (WWR ratio or width/height), mode='skylight_ratio' "
            "(RoofCeiling/Floor skylights by ratio), mode='guide_surface' (Face3D guide surfaces), "
            "and mode='geometry' (explicit Face3D aperture). Pass host_target for a single face, "
            "or host_targets / items to batch across multiple faces in one load/postprocess/save."
        ),
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
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        mode: Annotated[
            Literal["geometry", "parameters", "guide_surface", "skylight_ratio"],
            Field(
                description="Aperture creation mode: parameters (default), skylight_ratio, guide_surface, or geometry."
            ),
        ] = "parameters",
        host_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Single host Honeybee Face typed target from HB_Search_Model_Objects."
            ),
        ] = None,
        host_targets: Annotated[
            list[dict[str, Any]] | None,
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
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict; defaults to the Garden base Honeybee Model."
            ),
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
                description="For mode='parameters': by_ratio (requires ratio) or by_width_height (requires aperture_width and aperture_height)."
            ),
        ] = "by_ratio",
        ratio: Annotated[
            float | None,
            Field(
                description="Aperture-to-face area ratio between 0 and 1 (for mode='parameters' with by_ratio, or mode='skylight_ratio')."
            ),
        ] = None,
        aperture_width: Annotated[
            float | None,
            Field(description="For mode='parameters' + by_width_height: aperture width in model units."),
        ] = None,
        aperture_height: Annotated[
            float | None,
            Field(description="For mode='parameters' + by_width_height: aperture height in model units."),
        ] = None,
        sill_height: Annotated[
            float,
            Field(description="For mode='parameters' + by_width_height: sill height in model units."),
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
            Field(description="Geometry and ratio matching tolerance."),
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
    ) -> dict[str, Any]:
        """Create Honeybee Apertures on one or more host Faces."""
        if host_targets is not None or items is not None:
            from garden.honeybee_core.creation import create_honeybee_apertures_batch

            return create_honeybee_apertures_batch(
                garden_root=garden_root,
                mode=mode,
                host_target=host_target,
                host_targets=host_targets,
                items=items,
                model_target=model_target,
                generation_mode=generation_mode,
                ratio=ratio,
                aperture_width=aperture_width,
                aperture_height=aperture_height,
                sill_height=sill_height,
                aperture_identifier=aperture_identifier,
                identifier_prefix=identifier_prefix,
                tolerance=tolerance,
                rect_split=rect_split,
                guide_surfaces=guide_surfaces,
                is_operable=is_operable,
                postprocess_strategy=postprocess_strategy,
            )

        if host_target is None:
            raise ValueError(
                "host_target is required for single-host aperture creation (or pass host_targets/items)."
            )

        if mode == "geometry":
            if not identifier or not identifier.strip():
                raise ValueError("identifier is required when mode is 'geometry'.")
            if geometry is None:
                raise ValueError("geometry is required when mode is 'geometry'.")
            from garden.honeybee_core.creation import create_honeybee_aperture

            return create_honeybee_aperture(
                garden_root=garden_root,
                identifier=identifier,
                geometry=geometry,
                host_target=host_target,
                model_target=model_target,
                is_operable=is_operable,
                postprocess_strategy=postprocess_strategy,
            )
        if mode == "parameters":
            from garden.honeybee_core.creation import (
                create_honeybee_apertures_by_parameters,
            )

            return create_honeybee_apertures_by_parameters(
                garden_root=garden_root,
                host_target=host_target,
                generation_mode=generation_mode,
                model_target=model_target,
                ratio=ratio,
                aperture_width=aperture_width,
                aperture_height=aperture_height,
                sill_height=sill_height,
                aperture_identifier=aperture_identifier,
                identifier_prefix=identifier_prefix,
                tolerance=tolerance,
                rect_split=rect_split,
                postprocess_strategy=postprocess_strategy,
            )
        if mode == "skylight_ratio":
            if ratio is None:
                raise ValueError("ratio is required when mode is 'skylight_ratio'.")
            from garden.honeybee_core.creation import create_honeybee_skylights_by_ratio

            return create_honeybee_skylights_by_ratio(
                garden_root=garden_root,
                host_target=host_target,
                ratio=ratio,
                model_target=model_target,
                tolerance=tolerance,
                identifier_prefix=identifier_prefix,
                postprocess_strategy=postprocess_strategy,
            )
        if not guide_surfaces:
            raise ValueError("guide_surfaces is required when mode is 'guide_surface'.")
        from garden.honeybee_core.guide_openings import (
            create_honeybee_apertures_by_guide_surface,
        )

        return create_honeybee_apertures_by_guide_surface(
            garden_root=garden_root,
            host_target=host_target,
            guide_surfaces=guide_surfaces,
            model_target=model_target,
            tolerance=tolerance,
            identifier_prefix=identifier_prefix,
            postprocess_strategy=postprocess_strategy,
        )

    @mcp.tool(
        name="HB_Create_Shades",
        description=(
            "Create orphaned or hosted Honeybee Shades by explicit Face3D geometry "
            "(mode='geometry') or parametric louvers / aperture extruded borders "
            "(mode='parameters' with louver_by_count, louver_by_distance_between, or "
            "extruded_border). Supports single host_target or batch host_targets / items "
            "in one save with optional postprocess_strategy."
        ),
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
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        mode: Annotated[
            Literal["geometry", "parameters"],
            Field(description="Shade creation mode: geometry (default) or parameters."),
        ] = "geometry",
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional host Room/Face/Aperture/Door typed target (required for mode='parameters'; omit for orphaned geometry shades)."
            ),
        ] = None,
        host_targets: Annotated[
            list[dict[str, Any]] | None,
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
    ) -> dict[str, Any]:
        """Create one or more Honeybee Shades."""
        if host_targets is not None or items is not None:
            from garden.honeybee_core.creation import create_honeybee_shades_batch

            return create_honeybee_shades_batch(
                garden_root=garden_root,
                mode=mode,
                host_target=host_target,
                host_targets=host_targets,
                items=items,
                model_target=model_target,
                attach_side=attach_side,
                is_detached=is_detached,
                generation_mode=generation_mode,
                parameters=parameters,
                postprocess_strategy=postprocess_strategy,
            )

        if mode == "geometry":
            if not identifier or not identifier.strip():
                raise ValueError("identifier is required when mode is 'geometry'.")
            if geometry is None:
                raise ValueError("geometry is required when mode is 'geometry'.")
            from garden.honeybee_core.creation import create_honeybee_shade

            return create_honeybee_shade(
                garden_root=garden_root,
                identifier=identifier,
                geometry=geometry,
                model_target=model_target,
                host_target=host_target,
                attach_side=attach_side,
                is_detached=is_detached,
                postprocess_strategy=postprocess_strategy,
            )

        if host_target is None:
            raise ValueError("host_target is required when mode is 'parameters'.")
        if not generation_mode:
            raise ValueError("generation_mode is required when mode is 'parameters'.")
        if parameters is None:
            raise ValueError("parameters is required when mode is 'parameters'.")
        from garden.honeybee_core.creation import create_honeybee_shades_by_parameters

        return create_honeybee_shades_by_parameters(
            garden_root=garden_root,
            host_target=host_target,
            generation_mode=generation_mode,
            parameters=parameters,
            model_target=model_target,
            postprocess_strategy=postprocess_strategy,
        )

    @mcp.tool(
        name="HB_Edit_Model",
        description=(
            "Edit a Honeybee Model display name, user data, units, tolerances, model-level Energy "
            "electric load center, complete object-dict additions/removals, and existing Radiance "
            "SensorGrid/View attachments while preserving its Garden persistence path. Requires "
            "garden_root and a Honeybee model target; pass complete Honeybee object dictionaries "
            "to add_objects (rooms from HB_Create_Objects are already attached). Returns target, "
            "model_target, summary_view, persistence_receipt, report, and optional radiance "
            "attachment summaries."
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
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required Honeybee model target dict from HB_Create_Model, "
                    "GD_Manage_Base_Model, or GD_List_Models."
                )
            ),
        ],
        display_name: Annotated[
            str | None, Field(description="Optional updated display name.")
        ] = None,
        user_data: Annotated[
            dict[str, Any] | None,
            Field(description="Optional replacement user_data dictionary."),
        ] = None,
        units: Annotated[
            str | None, Field(description="Optional updated Honeybee model units.")
        ] = None,
        convert_geometry: Annotated[
            bool,
            Field(
                description="When units is provided, scale model geometry and tolerance using Model.convert_to_units (default true)."
            ),
        ] = True,
        tolerance: Annotated[
            float | None, Field(description="Optional updated model tolerance.")
        ] = None,
        angle_tolerance: Annotated[
            float | None, Field(description="Optional updated model angle tolerance.")
        ] = None,
        electric_load_center: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy ElectricLoadCenter dict or Garden Properties Library electric_load_center target from EP_Create_PV_Or_Load_Center."
            ),
        ] = None,
        add_objects: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Optional complete Honeybee Room, Face, Aperture, Door, or Shade object dictionaries to append to the model."
            ),
        ] = None,
        add_sensor_grids: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Optional list of existing radiance_sensor_grid target dicts to attach to Honeybee Model Radiance properties."
            ),
        ] = None,
        radiance_sensor_grid_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional single radiance_sensor_grid target dict; converted into add_sensor_grids=[target]."
            ),
        ] = None,
        add_radiance_views: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Optional list of existing radiance_view target dicts to attach to Honeybee Model Radiance properties."
            ),
        ] = None,
        radiance_view_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional single radiance_view target dict; converted into add_radiance_views=[target]."
            ),
        ] = None,
        remove_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Optional Honeybee typed targets from HB_Search_Model_Objects to remove from the model (top-level Room and orphaned objects)."
            ),
        ] = None,
        postprocess_strategy: Annotated[
            PostprocessStrategy | None,
            Field(
                description="Optional postprocess strategy override; defaults to auto_validate for model edits."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Edit a Honeybee Model."""
        from garden.honeybee_core.edit import edit_honeybee_model as service
        from garden.radiance.assets import (
            attach_radiance_sensor_grids_to_model,
            attach_radiance_views_to_model,
        )

        if add_sensor_grids is None and radiance_sensor_grid_target is not None:
            add_sensor_grids = [radiance_sensor_grid_target]
        if add_radiance_views is None and radiance_view_target is not None:
            add_radiance_views = [radiance_view_target]
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
        if not has_core_edits and not add_sensor_grids and not add_radiance_views:
            raise ValueError(
                "HB_Edit_Model requires at least one model edit, add_sensor_grids, or add_radiance_views input."
            )

        result: dict[str, Any]
        if has_core_edits:
            result = service(
                garden_root=garden_root,
                target=target,
                display_name=display_name,
                user_data=user_data,
                units=units,
                convert_geometry=convert_geometry,
                tolerance=tolerance,
                angle_tolerance=angle_tolerance,
                electric_load_center=electric_load_center,
                add_objects=add_objects,
                remove_targets=remove_targets,
                postprocess_strategy=postprocess_strategy,
            )
            target = result.get("target") or result.get("model_target") or target
        else:
            result = {
                "target": target,
                "model_target": target,
                "summary_view": {"model_identifier": target.get("identifier")},
            }
        if add_sensor_grids:
            attachment = attach_radiance_sensor_grids_to_model(
                garden_root=garden_root,
                model_target=target,
                sensor_grid_targets=add_sensor_grids,
            )
            result["target"] = attachment["target"]
            result["model_target"] = attachment["model_target"]
            result["radiance_sensor_grid_attachment"] = attachment
            result.setdefault("summary_view", {}).update(
                attachment.get("summary_view", {})
            )
        if add_radiance_views:
            attachment = attach_radiance_views_to_model(
                garden_root=garden_root,
                model_target=target,
                view_targets=add_radiance_views,
            )
            result["target"] = attachment["target"]
            result["model_target"] = attachment["model_target"]
            result["radiance_view_attachment"] = attachment
            result.setdefault("summary_view", {}).update(
                attachment.get("summary_view", {})
            )
        return result

    @mcp.tool(
        name="HB_Edit_Objects",
        description=(
            "Edit one or multiple Honeybee Room, Face, Aperture, Door, or Shade objects in one "
            "atomic Garden save. Pass a single target (typed target or room identifier string "
            "with model_target), batch targets=[...], or batch room_identifiers=[...]. Supports "
            "metadata (display_name, user_data), geometry, Room properties (story, zone, "
            "multiplier, exclude_floor_area, energy_properties, program_type, construction_set, "
            "hvac, ventilation, zone_ventilation_fans, setpoint, modifier_set), Face properties "
            "(face_type, boundary_condition, construction, vent_crack), Aperture/Door properties "
            "(is_operable, is_glass, construction, vent_opening), Shade properties (is_detached, "
            "construction, transmittance_schedule, pv_properties), and Radiance modifiers/states."
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
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="Single Honeybee typed target from HB_Search_Model_Objects (or exact room identifier string with model_target). Mutually exclusive with targets and room_identifiers."
            ),
        ] = None,
        targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Batch list of Honeybee object typed targets to update atomically in one save."
            ),
        ] = None,
        room_identifiers: Annotated[
            list[str] | None,
            Field(
                description="Batch list of exact Room identifiers in the selected Honeybee Model."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
        display_name: Annotated[
            str | None, Field(description="Optional updated display name.")
        ] = None,
        user_data: Annotated[
            dict[str, Any] | None,
            Field(description="Optional replacement user_data dictionary."),
        ] = None,
        geometry: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Ladybug Geometry Face3D dict for supported Face/Aperture/Door/Shade edits."
            ),
        ] = None,
        multiplier: Annotated[
            int | None,
            Field(description="For Rooms: optional multiplier >= 1."),
        ] = None,
        zone: Annotated[
            str | None, Field(description="For Rooms: optional Honeybee Room zone name.")
        ] = None,
        story: Annotated[
            str | None, Field(description="For Rooms: optional story name.")
        ] = None,
        exclude_floor_area: Annotated[
            bool | None,
            Field(description="For Rooms: optional exclude_floor_area flag."),
        ] = None,
        energy_properties: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "For Rooms: optional shared Room Energy properties dict supporting "
                    "program_type, construction_set, hvac, people, lighting, electric_equipment, "
                    "gas_equipment, service_hot_water, infiltration, ventilation, exhaust, "
                    "setpoint, zone_ventilation_fans, process_loads, internal_masses, shw, "
                    "window_vent_control, daylighting_control, make_plenum, make_ground, and reset_fields."
                )
            ),
        ] = None,
        program_type: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="For Rooms: optional ProgramType dict, Garden target, or standards identifier."
            ),
        ] = None,
        construction_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="For Rooms: optional ConstructionSet dict, Garden target, or standards identifier."
            ),
        ] = None,
        hvac: Annotated[
            dict[str, Any] | None,
            Field(
                description="For Rooms: optional Honeybee Energy HVAC dict or Garden target."
            ),
        ] = None,
        people: Annotated[
            dict[str, Any] | None,
            Field(description="For Rooms: optional People load dict, shorthand, or Garden load target."),
        ] = None,
        lighting: Annotated[
            dict[str, Any] | None,
            Field(description="For Rooms: optional Lighting load dict, shorthand, or Garden load target."),
        ] = None,
        electric_equipment: Annotated[
            dict[str, Any] | None,
            Field(description="For Rooms: optional ElectricEquipment load dict, shorthand, or Garden load target."),
        ] = None,
        gas_equipment: Annotated[
            dict[str, Any] | None,
            Field(description="For Rooms: optional GasEquipment load dict, shorthand, or Garden load target."),
        ] = None,
        service_hot_water: Annotated[
            dict[str, Any] | None,
            Field(description="For Rooms: optional ServiceHotWater load dict, shorthand, or Garden load target."),
        ] = None,
        infiltration: Annotated[
            dict[str, Any] | None,
            Field(description="For Rooms: optional Infiltration load dict, shorthand, or Garden load target."),
        ] = None,
        ventilation: Annotated[
            dict[str, Any] | None,
            Field(
                description="For Rooms: optional Honeybee Energy Ventilation dict or Garden load target."
            ),
        ] = None,
        exhaust: Annotated[
            dict[str, Any] | None,
            Field(description="For Rooms: optional ExhaustAir dict or Garden target (requires honeybee-energy>=1.125)."),
        ] = None,
        zone_ventilation_fans: Annotated[
            dict[str, Any] | list[dict[str, Any]] | None,
            Field(
                description="For Rooms: optional fan target, list, or {operation: replace_all|add|clear, fans:[...]}."
            ),
        ] = None,
        process_loads: Annotated[
            dict[str, Any] | list[dict[str, Any]] | None,
            Field(
                description="For Rooms: optional Process load dict/target, list, or {operation: replace_all|add|clear, process_loads:[...]}."
            ),
        ] = None,
        internal_masses: Annotated[
            dict[str, Any] | list[dict[str, Any]] | None,
            Field(
                description="For Rooms: optional InternalMass dict/target, list, or {operation: replace_all|add|clear, internal_masses:[...]}."
            ),
        ] = None,
        shw: Annotated[
            dict[str, Any] | None,
            Field(description="For Rooms: optional SHWSystem dict, shorthand, or Garden shw_system target."),
        ] = None,
        window_vent_control: Annotated[
            dict[str, Any] | None,
            Field(description="For Rooms: optional VentilationControl dict or shorthand for room natural ventilation."),
        ] = None,
        daylighting_control: Annotated[
            dict[str, Any] | None,
            Field(description="For Rooms: optional DaylightingControl dict or shorthand with sensor_position."),
        ] = None,
        make_plenum: Annotated[
            bool | dict[str, Any] | None,
            Field(description="For Rooms: true or {conditioned, remove_infiltration, include_floor_area} to convert room into a plenum."),
        ] = None,
        make_ground: Annotated[
            dict[str, Any] | str | None,
            Field(description="For Rooms: soil OpaqueConstruction (dict/target/identifier) or {soil_construction, include_floor_area} to convert room into ground."),
        ] = None,
        reset_fields: Annotated[
            list[str] | None,
            Field(description="List of field names to clear back to None / program defaults (e.g. ['lighting', 'loads', 'hvac'])."),
        ] = None,
        setpoint: Annotated[
            dict[str, Any] | None,
            Field(
                description="For Rooms: optional Honeybee Energy Setpoint dict or Garden target."
            ),
        ] = None,
        modifier_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="For Rooms: optional Honeybee Radiance ModifierSet dict, Garden target, or standards identifier."
            ),
        ] = None,
        face_type: Annotated[
            str | dict[str, Any] | None,
            Field(description="For Faces: optional updated Honeybee Face type name or dict."),
        ] = None,
        boundary_condition: Annotated[
            str | dict[str, Any] | None,
            Field(
                description="For Faces: optional updated non-Surface boundary condition name or dict. Use HB_Relate_Model for Surface adjacency."
            ),
        ] = None,
        vent_crack: Annotated[
            dict[str, Any] | None,
            Field(description="For Faces: optional Honeybee Energy AFNCrack dict."),
        ] = None,
        is_operable: Annotated[
            bool | None,
            Field(description="For Apertures: optional is_operable flag."),
        ] = None,
        is_glass: Annotated[
            bool | None,
            Field(description="For Doors: optional is_glass flag."),
        ] = None,
        is_detached: Annotated[
            bool | None,
            Field(description="For orphaned Shades: optional is_detached flag."),
        ] = None,
        construction: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="For Faces/Apertures/Doors/Shades: optional Honeybee Energy construction dict, Garden target, or standards identifier."
            ),
        ] = None,
        vent_opening: Annotated[
            dict[str, Any] | None,
            Field(
                description="For Apertures/Doors: optional Honeybee Energy VentilationOpening dict."
            ),
        ] = None,
        transmittance_schedule: Annotated[
            dict[str, Any] | None,
            Field(
                description="For Shades: optional Honeybee Energy schedule dict or Garden target."
            ),
        ] = None,
        pv_properties: Annotated[
            dict[str, Any] | None,
            Field(
                description="For Shades: optional Honeybee Energy PVProperties dict or Garden target."
            ),
        ] = None,
        modifier: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="For Faces/Apertures/Doors/Shades: optional Radiance modifier dict, Garden target, or identifier."
            ),
        ] = None,
        modifier_blk: Annotated[
            dict[str, Any] | str | None,
            Field(
                description="For Faces/Apertures/Doors/Shades: optional Radiance black modifier dict, Garden target, or identifier."
            ),
        ] = None,
        dynamic_group_identifier: Annotated[
            str | None,
            Field(
                description="For Apertures/Doors/Shades: optional Radiance dynamic group identifier."
            ),
        ] = None,
        states: Annotated[
            dict[str, Any] | list[dict[str, Any]] | None,
            Field(
                description="For Apertures/Doors/Shades: optional Radiance state update list or {operation, states}."
            ),
        ] = None,
        postprocess_strategy: Annotated[
            PostprocessStrategy | None,
            Field(
                description="Optional postprocess strategy override (none, suggest_validate, auto_validate, auto_relate_existing_geometry, auto_relate_intersect_clone_single)."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Edit one or multiple Honeybee objects in one atomic save."""
        from garden.honeybee_core.edit import edit_honeybee_objects as service

        return service(
            garden_root=garden_root,
            target=target,
            targets=targets,
            room_identifiers=room_identifiers,
            model_target=model_target,
            display_name=display_name,
            user_data=user_data,
            geometry=geometry,
            multiplier=multiplier,
            zone=zone,
            story=story,
            exclude_floor_area=exclude_floor_area,
            energy_properties=energy_properties,
            program_type=program_type,
            construction_set=construction_set,
            hvac=hvac,
            people=people,
            lighting=lighting,
            electric_equipment=electric_equipment,
            gas_equipment=gas_equipment,
            service_hot_water=service_hot_water,
            infiltration=infiltration,
            ventilation=ventilation,
            exhaust=exhaust,
            zone_ventilation_fans=zone_ventilation_fans,
            process_loads=process_loads,
            internal_masses=internal_masses,
            shw=shw,
            window_vent_control=window_vent_control,
            daylighting_control=daylighting_control,
            make_plenum=make_plenum,
            make_ground=make_ground,
            reset_fields=reset_fields,
            setpoint=setpoint,
            modifier_set=modifier_set,
            face_type=face_type,
            boundary_condition=boundary_condition,
            vent_crack=vent_crack,
            is_operable=is_operable,
            is_glass=is_glass,
            is_detached=is_detached,
            construction=construction,
            vent_opening=vent_opening,
            transmittance_schedule=transmittance_schedule,
            pv_properties=pv_properties,
            modifier=modifier,
            modifier_blk=modifier_blk,
            dynamic_group_identifier=dynamic_group_identifier,
            states=states,
            postprocess_strategy=postprocess_strategy,
        )

    @mcp.tool(
        name="HB_Transform_Objects",
        description=(
            "Transform one or a batch of Honeybee Model, Room, Face, Aperture, Door, or Shade "
            "targets using operation='move', 'rotate', 'scale', or 'mirror' in a single load, "
            "postprocess, and save. Pass target for a single object or targets=[...] for batch. "
            "Run HB_Search_Model_Objects, HB_Relate_Model, or HB_Validate_Model after partial "
            "object transforms when relationships matter."
        ),
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
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        operation: Annotated[
            Literal["move", "rotate", "scale", "mirror"],
            Field(description="Required geometric transform operation: move, rotate, scale, or mirror."),
        ],
        target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Single Honeybee model target or object typed target. Mutually exclusive with targets."
            ),
        ] = None,
        targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Batch list of Honeybee model or object typed targets to transform in one save."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
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
            Field(description="Required for operation='scale': positive scale factor."),
        ] = None,
        plane: Annotated[
            dict[str, Any] | None,
            Field(
                description="Required for operation='mirror': Ladybug Plane dict with origin 'o' and normal 'n'."
            ),
        ] = None,
        postprocess_strategy: Annotated[
            PostprocessStrategy | None,
            Field(
                description="Optional postprocess strategy override (none, suggest_validate, auto_validate, auto_relate_existing_geometry, auto_relate_intersect_clone_single)."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Move, rotate, scale, or mirror Honeybee targets."""
        from garden.honeybee_core.transform import transform_objects as service

        return service(
            garden_root=garden_root,
            operation=operation,
            target=target,
            targets=targets,
            model_target=model_target,
            vector=vector,
            axis=axis,
            angle_degrees=angle_degrees,
            origin=origin,
            factor=factor,
            plane=plane,
            postprocess_strategy=postprocess_strategy,
        )

    @mcp.tool(
        name="HB_Remove_Objects",
        description=(
            "Remove one or a batch of Honeybee Room, orphaned Face, Aperture, Door, or Shade "
            "objects from a Garden model in one atomic save. Pass target for a single object or "
            "targets=[...] for batch removal. Paired Surface interior sub-faces and stale room "
            "Surface references are cleaned up automatically; room-hosted faces are rejected."
        ),
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
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Single Honeybee object typed target from HB_Search_Model_Objects. Mutually exclusive with targets."
            ),
        ] = None,
        targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description="Batch list of Honeybee object typed targets to remove in one save."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
        postprocess_strategy: Annotated[
            PostprocessStrategy | None,
            Field(
                description="Optional postprocess strategy override (none, suggest_validate, auto_validate, auto_relate_existing_geometry, auto_relate_intersect_clone_single)."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Remove one or more Honeybee objects by typed target."""
        from garden.honeybee_core.removal import remove_honeybee_objects as service

        return service(
            garden_root=garden_root,
            target=target,
            targets=targets,
            model_target=model_target,
            postprocess_strategy=postprocess_strategy,
        )

    @mcp.tool(
        name="HB_Relate_Model",
        description="Run SDK-backed Honeybee model relationship processing for solve_adjacency, Surface boundary relationships, optional room-face intersection, coplanar merge, AirBoundary/adiabatic settings, and explicit high-risk cleanup or missing sub-face repair. explicit_relate_full enables overwrite, relationship_cleanup, mismatched sub-face deletion, and clone_missing Aperture/Door repair, so use it only when the user asks for repair/overwrite/delete mismatch cleanup. Returns summary_view.model_target, persistence_receipt, and report for validation or export calls; there is no top-level target.",
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
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
        relation_mode: Annotated[
            str,
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
                description="Optional distance tolerance. Defaults to model tolerance."
            ),
        ] = None,
        angle_tolerance: Annotated[
            float | None,
            Field(
                description="Optional angle tolerance in degrees. Defaults to model angle tolerance."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Solve Honeybee model relationships with the SDK."""
        from garden.honeybee_core.relate import relate_honeybee_model as service

        if solve_adjacency is True:
            relation_mode = "solve_adjacency"
        return service(
            garden_root=garden_root,
            model_target=model_target,
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
        )

    @mcp.tool(
        name="HB_Search_Model_Objects",
        description=(
            "Search Honeybee Room, Face, Aperture/window, Door, and Shade objects in the Garden "
            "base model or an explicit model_target. Narrow results with object_type, identifier, "
            "query, room_identifier, face_identifier, face_type, boundary_condition, "
            "children_scope, orientation (N/NE/E/SE/S/SW/W/NW/horizontal_up/horizontal_down), "
            "story, zone, min_area, or max_area. Pass matches[i].target to HB_Create_Objects / "
            "HB_Create_Apertures / HB_Create_Shades / HB_Edit_Objects / HB_Transform_Objects / "
            "HB_Remove_Objects."
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
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
            ),
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
            dict[str, Any] | None,
            Field(
                description="Optional typed Honeybee parent target dict (room, face, aperture, or door) to filter returned child objects."
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
            Field(description="Optional minimum area filter in model area units (floor_area for Rooms, face area for Faces/sub-faces/Shades)."),
        ] = None,
        max_area: Annotated[
            float | None,
            Field(description="Optional maximum area filter in model area units."),
        ] = None,
        limit: Annotated[
            int | None,
            Field(description="Optional maximum number of object matches to return."),
        ] = None,
    ) -> dict[str, Any]:
        """Search Honeybee objects and return typed targets."""
        from garden.honeybee_core.search import (
            search_honeybee_model_objects as service,
        )

        return service(
            garden_root=garden_root,
            model_target=model_target,
            object_type=object_type,
            identifier=identifier,
            room_identifier=room_identifier,
            face_identifier=face_identifier,
            query=query,
            face_type=face_type,
            boundary_condition=boundary_condition,
            children_scope=children_scope,
            orientation=orientation,
            story=story,
            zone=zone,
            min_area=min_area,
            max_area=max_area,
            limit=limit,
        )

    @mcp.tool(
        name="HB_Get_Model_Summary",
        description=(
            "Return a compact read-only summary of a Honeybee Model: object counts (rooms, faces, "
            "apertures, doors, shades, orphaned_faces), total floor area, volume, exterior wall area, "
            "exterior aperture area, overall WWR and per-orientation (N/E/S/W/Other) WWR, stories, "
            "zones, Energy coverage (program_types, construction_sets, hvacs, setpoints, "
            "conditioned_room_count), and Radiance coverage (modifier_sets, sensor_grids, views)."
        ),
        tags={"energy", "honeybee", "model", "radiance", "summary", "wwr"},
        annotations={"readOnlyHint": True},
        timeout=20,
    )
    def get_honeybee_model_summary(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Summarize Honeybee model geometry, WWR, and Energy/Radiance coverage."""
        from garden.honeybee_core.search import (
            get_honeybee_model_summary as service,
        )

        return service(garden_root=garden_root, model_target=model_target)

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
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Honeybee model target dict, usually HB_Create_Model['target']; "
                    "defaults to the Garden base Honeybee Model."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Validate a Honeybee model and return structured issues."""
        from garden.honeybee_core.model_io import (
            validate_honeybee_model as service,
        )

        return service(garden_root=garden_root, model_target=model_target)

    @mcp.tool(
        name="HB_Repair_Model",
        description=(
            "Repair, clean, merge, or compare Honeybee models in a Garden. Supported actions: "
            "remove_degenerate_geometry, triangulate_non_planar_quads, clean_irrational_geometry, "
            "split_rooms_through_holes, rooms_to_extrusions, reset_coordinate_system, "
            "clean_envelope, fix_invalid_sub_faces, missing_adjacencies_to_adiabatic, "
            "assign_stories_by_floor_height, add_model (merge other_model_target), and "
            "comparison_report (read-only diff against other_model_target)."
        ),
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
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
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
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
        other_model_target: Annotated[
            dict[str, Any] | None,
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
            Field(description="Optional geometric tolerance override (defaults to model tolerance)."),
        ] = None,
        angle_tolerance: Annotated[
            float | None,
            Field(description="Optional angle tolerance override in degrees (defaults to model angle_tolerance)."),
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
            Field(description="For action='fix_invalid_sub_faces': inward edge offset distance after trimming."),
        ] = 0.05,
        include_surface_faces: Annotated[
            bool,
            Field(description="For action='fix_invalid_sub_faces': also process Surface-adjacent faces (default false)."),
        ] = False,
        min_difference: Annotated[
            float,
            Field(description="For action='assign_stories_by_floor_height': minimum elevation difference between distinct stories."),
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
    ) -> dict[str, Any]:
        """Run Honeybee Model repair, cleanup, merge, or comparison diagnostics."""
        from garden.honeybee_core.repair import repair_honeybee_model as service

        return service(
            garden_root=garden_root,
            action=action,
            model_target=model_target,
            other_model_target=other_model_target,
            other_model_prefix=other_model_prefix,
            tolerance=tolerance,
            angle_tolerance=angle_tolerance,
            new_origin=new_origin,
            trim_with_parent=trim_with_parent,
            union_overlaps=union_overlaps,
            offset_distance=offset_distance,
            include_surface_faces=include_surface_faces,
            min_difference=min_difference,
            overwrite=overwrite,
            ignore_deleted=ignore_deleted,
            ignore_added=ignore_added,
            postprocess_strategy=postprocess_strategy,
        )
